"""Configuración del asistente, informes y persistencia por variables de entorno. Ninguna clave se escribe en el repositorio."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Optional

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _float(env: Mapping[str, str], name: str, default: float, lo: float, hi: float) -> float:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return min(max(value, lo), hi)


@dataclass(frozen=True)
class Settings:
    db_path: str
    ai_provider: str          # "" (sin proveedor) | "openai_compatible"
    ai_base_url: str
    ai_model: str
    ai_api_key: str = field(default="", repr=False)   # nunca se muestra ni se envía al navegador
    ai_timeout: float = 30.0
    ai_max_tokens: int = 800
    dev_auth: bool = False    # identidad de DESARROLLO (cabecera); apagada por defecto


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    env = os.environ if env is None else env
    return Settings(
        db_path=(env.get("PACHAADAPT_DB_PATH") or env.get("PACHAADAPT_DB") or env.get("PACHAADAPT_I3_DB")
                 or str(_REPO_ROOT / "storage" / "integrante3.sqlite3")),
        ai_provider=(env.get("PACHAADAPT_AI_PROVIDER") or "").strip().lower(),
        ai_base_url=(env.get("PACHAADAPT_AI_BASE_URL") or "").strip().rstrip("/"),
        ai_model=(env.get("PACHAADAPT_AI_MODEL") or "").strip(),
        ai_api_key=env.get("PACHAADAPT_AI_API_KEY") or "",
        ai_timeout=_float(env, "PACHAADAPT_AI_TIMEOUT", 30.0, 1.0, 300.0),
        ai_max_tokens=int(_float(env, "PACHAADAPT_AI_MAX_TOKENS", 800, 16, 4000)),
        dev_auth=(env.get("PACHAADAPT_I3_DEV_AUTH") or "") == "1",
    )
