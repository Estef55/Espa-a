"""Endpoints de documentos editables e historial de versiones. Prefijo: /api/v1/documents."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.v1._deps import principal, run
from app.core.identity import Principal
from app.services.container import get_container

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    title: str
    content: str
    source_material_id: Optional[str] = None


class DocumentImport(BaseModel):
    material_id: str


class DocumentSave(BaseModel):
    content: str
    expected_version: int
    reason: Optional[str] = None


class DocumentRestore(BaseModel):
    version: int
    expected_version: int
    reason: Optional[str] = None


@router.post("", status_code=201)
def create_document(body: DocumentCreate, p: Principal = Depends(principal)):
    return run(get_container().documents.create, p.user_id, body.title, body.content, body.source_material_id)


@router.post("/import", status_code=201)
def import_document(body: DocumentImport, p: Principal = Depends(principal)):
    """Importa el texto adaptado desde el procesador documental (503 si aún no está conectado)."""
    return run(get_container().documents.import_from_processor, p.user_id, body.material_id)


@router.get("")
def list_documents(include_archived: bool = False, p: Principal = Depends(principal)):
    return run(get_container().documents.list, p.user_id, include_archived)


@router.get("/{document_id}")
def get_document(document_id: str, p: Principal = Depends(principal)):
    return run(get_container().documents.get, p.user_id, document_id)


@router.put("/{document_id}")
def save_document(document_id: str, body: DocumentSave, p: Principal = Depends(principal)):
    return run(get_container().revisions.save, p.user_id, document_id, body.content,
               body.expected_version, body.reason)


@router.get("/{document_id}/versions")
def list_versions(document_id: str, p: Principal = Depends(principal)):
    return run(get_container().revisions.versions, p.user_id, document_id)


@router.get("/{document_id}/versions/{version}")
def get_version(document_id: str, version: int, p: Principal = Depends(principal)):
    return run(get_container().revisions.get_version, p.user_id, document_id, version)


@router.post("/{document_id}/restore")
def restore_document(document_id: str, body: DocumentRestore, p: Principal = Depends(principal)):
    return run(get_container().revisions.restore, p.user_id, document_id, body.version,
               body.expected_version, body.reason)


@router.post("/{document_id}/archive")
def archive_document(document_id: str, p: Principal = Depends(principal)):
    return run(get_container().documents.archive, p.user_id, document_id)
