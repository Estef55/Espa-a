"""Identidad del docente.

El proyecto aún no tiene autenticación (backend/app/core/security.py es TODO).
Este módulo NO inventa una: define el contrato mínimo (``Principal``) y un punto
de enchufe (``set_identity_resolver``). Cuando exista la autenticación compartida,
basta registrar su función aquí.

Mientras tanto existe un sustituto SOLO PARA DESARROLLO, apagado por defecto
(PACHAADAPT_I3_DEV_AUTH=1) que lee la cabecera ``X-Dev-Teacher-Id``.
NO es apto para producción: cualquiera puede suplantar a un docente.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Mapping, Optional

from app.core import paths  # noqa: F401  (habilita "import ai")
from ai.settings import load_settings
from ai.errors import AuthNotConfigured, Forbidden, Unauthorized

USER_ID_RE = re.compile(r"^[A-Za-z0-9_.@-]{1,64}$")


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str = "docente"


Resolver = Callable[[Mapping[str, str]], Principal]
_resolver: Optional[Resolver] = None


def set_identity_resolver(resolver: Optional[Resolver]) -> None:
    """Registra la autenticación compartida (recibe las cabeceras, devuelve Principal o lanza Unauthorized)."""
    global _resolver
    _resolver = resolver


def _dev_resolver(headers: Mapping[str, str]) -> Principal:
    """Acepta cabeceras de ambos contratos solo en modo de desarrollo explícito."""
    user = (headers.get("x-dev-teacher-id") or headers.get("x-user-id") or "").strip()
    if not USER_ID_RE.match(user):
        raise Unauthorized("Falta o es inválida la cabecera de usuario de desarrollo.")
    if headers.get("x-dev-teacher-id"):
        role = (headers.get("x-dev-role") or "docente").strip().lower()
    else:
        role = (headers.get("x-role") or "teacher").strip().lower()
        role = {"teacher": "docente", "student": "estudiante", "admin": "administrador"}.get(role, role)
    return Principal(user_id=user, role=role)


def resolve_principal(headers: Mapping[str, str]) -> Principal:
    lowered = {k.lower(): v for k, v in headers.items()}
    if _resolver is not None:
        principal = _resolver(lowered)
    elif load_settings().dev_auth:
        principal = _dev_resolver(lowered)
    else:
        raise AuthNotConfigured(
            "No hay autenticación configurada. Registre la autenticación compartida con "
            "set_identity_resolver() o active PACHAADAPT_I3_DEV_AUTH=1 solo en desarrollo."
        )
    if not isinstance(principal, Principal) or not USER_ID_RE.match(principal.user_id):
        raise Unauthorized("Identidad inválida.")
    return principal


def require_teacher(principal: Principal) -> Principal:
    if principal.role != "docente":
        raise Forbidden("Esta función es solo para docentes.")
    return principal
