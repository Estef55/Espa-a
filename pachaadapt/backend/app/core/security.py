"""Adaptador de identidad compartido por módulos previos y el integrante 4.

Las cabeceras X-User-Id/X-Role y X-Dev-Teacher-Id solo sirven cuando está activado
PACHAADAPT_I3_DEV_AUTH=1 o cuando el proyecto registra un resolvedor de identidad.
"""
from dataclasses import dataclass
from fastapi import Header, HTTPException

from ai.errors import I3Error
from app.core.identity import resolve_principal


@dataclass(frozen=True)
class Actor:
    id: str
    role: str


def current_actor(
    x_user_id: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
    x_dev_teacher_id: str | None = Header(default=None),
    x_dev_role: str | None = Header(default=None),
) -> Actor:
    headers = {}
    if x_user_id is not None:
        headers["x-user-id"] = x_user_id
    if x_role is not None:
        headers["x-role"] = x_role
    if x_dev_teacher_id is not None:
        headers["x-dev-teacher-id"] = x_dev_teacher_id
    if x_dev_role is not None:
        headers["x-dev-role"] = x_dev_role
    try:
        principal = resolve_principal(headers)
    except I3Error as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_dict()) from exc
    roles = {"docente": "teacher", "estudiante": "student", "administrador": "admin",
             "teacher": "teacher", "student": "student", "admin": "admin"}
    role = roles.get(principal.role)
    if role is None:
        raise HTTPException(403, "Rol no permitido")
    return Actor(principal.user_id, role)


def require_roles(actor: Actor, *roles: str) -> None:
    if actor.role not in roles:
        raise HTTPException(403, "No tienes permisos para esta operación")

