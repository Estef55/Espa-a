"""Registro técnico JSON en consola y archivo con rotación."""
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

logger = logging.getLogger("pachaadapt")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
logger.propagate = False

if not logger.handlers:
    formatter = logging.Formatter("%(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    try:
        log_dir = Path(os.getenv("PACHAADAPT_LOG_DIR", Path(__file__).resolve().parents[3] / "storage" / "logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "pachaadapt.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # La consola sigue disponible si el entorno no permite escribir archivos.
        pass


def log_event(event: str, **fields):
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    logger.info(json.dumps(record, ensure_ascii=False, default=str))
