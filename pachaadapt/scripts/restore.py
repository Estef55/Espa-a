"""Restauración explícita desde una copia SQLite.

Cierra primero el servidor. El archivo actual se conserva como .before-restore.
"""
import argparse
from contextlib import closing
import os
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path(os.getenv("PACHAADAPT_DB_PATH") or os.getenv("PACHAADAPT_DB")
                 or os.getenv("PACHAADAPT_I3_DB") or ROOT / "storage" / "integrante3.sqlite3")

def restore_backup(backup: Path, target: Path):
    if not backup.is_file():
        raise FileNotFoundError(f"No existe la copia: {backup}")
    with closing(sqlite3.connect(str(backup))) as con:
        result = con.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"La copia no pasó integrity_check: {result}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(target, target.with_suffix(target.suffix + ".before-restore"))
    temporary = target.with_suffix(target.suffix + ".restoring")
    try:
        shutil.copy2(backup, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restaurar copia de PACHAADAPT")
    parser.add_argument("backup", type=Path, help="Ruta al archivo .sqlite3")
    parser.add_argument("--target", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    print(f"Base restaurada en: {restore_backup(args.backup, args.target)}")
