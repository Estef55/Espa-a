"""Persistencia provisional y reemplazable (SQLite, librería estándar).

NO es una decisión de arquitectura: el proyecto aún no define motor de BD.
Todas las tablas llevan el prefijo ``i3_`` para no chocar con el esquema compartido
futuro. El resto del módulo solo usa ``Database.transaction()`` / ``Database.read()``
y SQL parametrizado, de modo que migrar a otro motor implique cambiar este archivo
y ``database/migrations/``.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "database" / "migrations"
_MIGRATION_RE = re.compile(r"^(\d{3}_[a-z0-9_]+)\.sql$")  # excluye *.down.sql


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class Database:
    def __init__(self, path: str):
        if str(path) == ":memory:":
            raise ValueError("Se requiere un archivo: ':memory:' no persiste entre conexiones.")
        self.path = str(path)
        self._ready = False
        self._lock = threading.Lock()

    def _open(self) -> sqlite3.Connection:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _ensure(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            self.migrate()
            self._ready = True

    def migrate(self) -> list[str]:
        """Aplica migraciones incrementales pendientes. Idempotente. Devuelve las aplicadas."""
        applied: list[str] = []
        conn = self._open()
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS i3_schema_migrations "
                "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            done = {r["version"] for r in conn.execute("SELECT version FROM i3_schema_migrations")}
            for f in sorted(MIGRATIONS_DIR.iterdir()):
                m = _MIGRATION_RE.match(f.name)
                if not m or m.group(1) in done:
                    continue
                version = m.group(1)  # validado por regex: seguro de interpolar
                script = (
                    "BEGIN;\n" + f.read_text(encoding="utf-8") + "\n"
                    f"INSERT INTO i3_schema_migrations(version, applied_at) VALUES ('{version}', '{now_iso()}');\n"
                    "COMMIT;"
                )
                try:
                    conn.executescript(script)
                except BaseException:
                    if conn.in_transaction:
                        conn.execute("ROLLBACK")
                    raise
                applied.append(version)
        finally:
            conn.close()
        return applied

    @contextmanager
    def transaction(self):
        """Transacción de escritura serializada (BEGIN IMMEDIATE); rollback ante cualquier error."""
        self._ensure()
        conn = self._open()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    @contextmanager
    def read(self):
        self._ensure()
        conn = self._open()
        try:
            yield conn
        finally:
            conn.close()
