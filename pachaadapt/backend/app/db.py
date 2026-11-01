"""SQLite compartida por módulos de PACHAADAPT y migraciones del integrante 4."""
from contextlib import closing, contextmanager
import sqlite3
from pathlib import Path

from app.core import paths  # noqa: F401 - añade la raíz del repositorio a sys.path
from ai.settings import load_settings
from ai.storage import Database

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "database" / "schema.sql"  # documento de referencia; las migraciones son ejecutables
MIGRATIONS_PATH = ROOT / "database" / "migrations" / "integrante4"


def database_path() -> str:
    return load_settings().db_path


# Alias legado para scripts externos; las conexiones leen la configuración actual.
DB_PATH = database_path()


def connect():
    path = database_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=30000")
    if path != ":memory:":
        con.execute("PRAGMA journal_mode=WAL")
    return con


@contextmanager
def transaction():
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    """Aplica las migraciones previas y las del integrante 4 a la misma base SQLite."""
    if database_path() == ":memory:":
        raise ValueError("PACHAADAPT requiere una base SQLite persistente en archivo.")
    Database(database_path()).migrate()
    with closing(connect()) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        con.commit()
        applied = {int(row[0]) for row in con.execute("SELECT version FROM schema_migrations")}
        for migration in sorted(MIGRATIONS_PATH.glob("[0-9][0-9][0-9]_*.sql")):
            version = int(migration.name.split("_", 1)[0])
            if version in applied:
                continue
            con.executescript(migration.read_text(encoding="utf-8"))
            con.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
            con.commit()
            applied.add(version)


def healthcheck():
    with closing(connect()) as con:
        con.execute("SELECT 1").fetchone()
    return {"database": "ok", "engine": "sqlite",
            "path": database_path() if __import__("os").getenv("PACHAADAPT_SHOW_DB_PATH") else "configured"}
