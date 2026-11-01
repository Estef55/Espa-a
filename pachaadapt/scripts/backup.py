"""Copia consistente de SQLite y rotación de respaldos.

Uso desde la raíz del proyecto:
  python scripts/backup.py
  python scripts/backup.py --destination backups --keep 14
"""
import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = Path(os.getenv("PACHAADAPT_DB_PATH") or os.getenv("PACHAADAPT_DB")
                 or os.getenv("PACHAADAPT_I3_DB") or ROOT / "storage" / "integrante3.sqlite3")

def create_backup(source: Path, destination: Path, keep: int = 14) -> Path:
    if keep < 1:
        raise ValueError("keep debe ser al menos 1")
    if not source.exists():
        raise FileNotFoundError(f"No existe la base de datos: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    target = destination / f"pachaadapt_{stamp}.sqlite3"
    src = sqlite3.connect(str(source))
    try:
        dst = sqlite3.connect(str(target))
        try:
            src.backup(dst)
            check = dst.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise RuntimeError(f"La copia no pasó integrity_check: {check}")
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()
    backups = sorted(destination.glob("pachaadapt_*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[max(1, keep):]:
        old.unlink(missing_ok=True)
    return target

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crear copia de seguridad de PACHAADAPT")
    parser.add_argument("--source", type=Path, default=DEFAULT_DB)
    parser.add_argument("--destination", type=Path, default=ROOT / "backups")
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()
    result = create_backup(args.source, args.destination, args.keep)
    print(f"Copia creada: {result}")
