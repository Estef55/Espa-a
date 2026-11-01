"""Catálogo de materiales del integrante 4 (URLs/recursos), separado de la carga de archivos."""
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.logging import log_event
from app.core.security import Actor, current_actor, require_roles
from app.db import connect, transaction

router = APIRouter(prefix="/material-library", tags=["material-library"])


class LibraryMaterialIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    resource_url: str = Field(min_length=1, max_length=2048)
    mime_type: str = Field(default="application/octet-stream", max_length=150)
    status: str = "published"

    @field_validator("resource_url")
    @classmethod
    def validate_resource_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if value.startswith("/") and not value.startswith("//"):
            return value
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return value
        raise ValueError("resource_url debe ser una ruta local o una URL HTTP/HTTPS")


@router.post("", status_code=201)
def create_material(data: LibraryMaterialIn, actor: Actor = Depends(current_actor)):
    require_roles(actor, "teacher", "admin")
    if data.status not in {"draft", "published"}:
        raise HTTPException(422, "Estado inválido")
    material_id = str(uuid4())
    with transaction() as con:
        con.execute(
            "INSERT INTO materials(id,title,description,resource_url,mime_type,created_by,status) VALUES(?,?,?,?,?,?,?)",
            (material_id, data.title.strip(), data.description, data.resource_url, data.mime_type, actor.id, data.status),
        )
        row = dict(con.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone())
        con.execute("INSERT INTO audit_log(actor_id,action,entity_type,entity_id) VALUES(?,?,?,?)",
                    (actor.id, "create", "material", material_id))
    log_event("material.created", actor_id=actor.id, material_id=material_id)
    return row


@router.get("")
def list_materials(actor: Actor = Depends(current_actor)):
    con = connect()
    try:
        if actor.role == "student":
            rows = con.execute("SELECT * FROM materials WHERE status='published' ORDER BY created_at DESC").fetchall()
        elif actor.role == "teacher":
            rows = con.execute("SELECT * FROM materials WHERE created_by=? ORDER BY created_at DESC", (actor.id,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM materials ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]
    finally:
        con.close()


@router.get("/{material_id}")
def get_material(material_id: str, actor: Actor = Depends(current_actor)):
    con = connect()
    try:
        row = con.execute("SELECT * FROM materials WHERE id=?", (material_id,)).fetchone()
    finally:
        con.close()
    if not row or (actor.role == "student" and row["status"] != "published"):
        raise HTTPException(404, "Material no encontrado")
    if actor.role == "teacher" and row["created_by"] != actor.id:
        raise HTTPException(403, "No puedes consultar materiales de otro docente")
    return dict(row)
