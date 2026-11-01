"""Pruebas de copia consistente, integridad y restauración segura."""
import sqlite3
from contextlib import closing
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from scripts.backup import create_backup
from scripts.restore import restore_backup


def _database(path: Path, value: str) -> None:
    with closing(sqlite3.connect(path)) as con:
        con.execute("CREATE TABLE IF NOT EXISTS sample (value TEXT NOT NULL)")
        con.execute("DELETE FROM sample")
        con.execute("INSERT INTO sample(value) VALUES (?)", (value,))
        con.commit()


def test_backup_integrity_and_restore_preserves_previous_database(tmp_path):
    source = tmp_path / "source.sqlite3"
    backup_dir = tmp_path / "backups"
    target = tmp_path / "restored.sqlite3"
    _database(source, "contenido respaldado")

    backup = create_backup(source, backup_dir, keep=3)
    assert backup.exists()
    with closing(sqlite3.connect(backup)) as con:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("SELECT value FROM sample").fetchone()[0] == "contenido respaldado"

    _database(target, "contenido anterior")
    restored = restore_backup(backup, target)
    assert restored == target
    assert target.with_suffix(".sqlite3.before-restore").exists()
    with closing(sqlite3.connect(target)) as con:
        assert con.execute("SELECT value FROM sample").fetchone()[0] == "contenido respaldado"


def test_restore_rejects_corrupt_backup(tmp_path):
    corrupt = tmp_path / "corrupt.sqlite3"
    corrupt.write_bytes(b"esto no es una base SQLite")
    target = tmp_path / "target.sqlite3"
    try:
        restore_backup(corrupt, target)
    except sqlite3.DatabaseError:
        pass
    else:
        raise AssertionError("Se esperaba rechazar una copia corrupta")
