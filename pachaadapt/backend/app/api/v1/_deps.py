"""Utilidades comunes de los routers del integrante 3: identidad y traducción de errores."""
from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException, Request

from app.core import paths  # noqa: F401  (habilita "import ai")
from ai.errors import I3Error
from app.core.identity import Principal, require_teacher, resolve_principal


def run(fn: Callable, *args, **kwargs) -> Any:
    """Ejecuta un servicio y traduce los errores de dominio a HTTPException."""
    try:
        return fn(*args, **kwargs)
    except I3Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())


def principal(request: Request) -> Principal:
    """Dependencia FastAPI: docente autenticado (ver app/core/identity.py)."""
    return run(lambda: require_teacher(resolve_principal(dict(request.headers))))
