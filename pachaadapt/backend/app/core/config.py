"""Configuración centralizada del servicio PACHAADAPT."""
from dataclasses import dataclass
import os
from pathlib import Path

from ai.settings import load_settings


@dataclass(frozen=True)
class Settings:
    app_name: str = "PACHAADAPT by YACHAY"
    app_version: str = "1.1.0"
    host: str = os.getenv("PACHAADAPT_HOST", "127.0.0.1")
    port: int = int(os.getenv("PACHAADAPT_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    database_path: str = load_settings().db_path
    cors_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if item.strip()
    )


settings = Settings()
