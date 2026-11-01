"""Documentos editables: creación, consulta, archivado e importación desde el procesador documental.

- La versión 1 se crea con el contenido original, que además se conserva en
  ``original_content`` (nunca se actualiza). Nada se borra físicamente: solo se archiva.
- Todas las consultas validan que el documento pertenezca al docente; un documento ajeno
  responde NotFound para no revelar su existencia.
- Guarda texto editable; NO modifica PDFs ni reprocesa archivos (eso es del integrante 2).
- El historial de versiones (guardar/restaurar/consultar) está en ``revision_manager.py``.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional, Protocol

from ai.errors import IntegrationNotConfigured, NotFound, ValidationError
from ai.storage import Database, now_iso

MAX_CONTENT = 500_000
MAX_TITLE = 200
MAX_REASON = 500


# ---------- puerto hacia el procesador documental (integrante 2) ----------
@dataclass(frozen=True)
class AdaptedDocument:
    """Texto adaptado entregado por el procesador documental."""
    material_id: str
    title: str
    text: str


class DocumentProcessorPort(Protocol):
    def get_adapted_text(self, material_id: str, owner_id: str) -> AdaptedDocument:
        """Devuelve el texto adaptado de un material. DEBE verificar que ``owner_id``
        está autorizado a verlo (lanzar Forbidden/NotFound si no)."""


# ---------- validaciones y utilidades compartidas con revision_manager ----------
def check_content(content) -> str:
    if not isinstance(content, str) or not content.strip():
        raise ValidationError("El contenido debe ser texto no vacío.")
    if len(content) > MAX_CONTENT:
        raise ValidationError(f"El contenido supera el máximo de {MAX_CONTENT} caracteres.")
    return content


def check_title(title) -> str:
    if not isinstance(title, str) or not title.strip() or len(title) > MAX_TITLE:
        raise ValidationError(f"El título debe tener entre 1 y {MAX_TITLE} caracteres.")
    return title.strip()


def check_reason(reason) -> str:
    if reason is None:
        return ""
    if not isinstance(reason, str) or len(reason) > MAX_REASON:
        raise ValidationError(f"El motivo debe ser texto de hasta {MAX_REASON} caracteres.")
    return reason.strip()


def check_expected(expected) -> int:
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
        raise ValidationError("expected_version debe ser un entero >= 1.")
    return expected


def doc_dict(row) -> dict:
    return {
        "id": row["id"], "title": row["title"], "source_material_id": row["source_material_id"],
        "current_version": row["current_version"], "archived": bool(row["archived"]),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def load_owned(conn, document_id: str, owner_id: str):
    row = conn.execute("SELECT * FROM i3_documents WHERE id = ? AND owner_id = ?",
                       (document_id, owner_id)).fetchone()
    if row is None:
        raise NotFound("Documento no encontrado.")
    return row


class DocumentBuilder:
    def __init__(self, db: Database, processor: Optional[DocumentProcessorPort] = None):
        self.db = db
        self.processor = processor

    def set_processor(self, processor: Optional[DocumentProcessorPort]) -> None:
        self.processor = processor

    def create(self, owner_id: str, title: str, content: str,
               source_material_id: Optional[str] = None) -> dict:
        title, content = check_title(title), check_content(content)
        if source_material_id is not None and (not isinstance(source_material_id, str)
                                               or not 0 < len(source_material_id) <= 128):
            raise ValidationError("source_material_id inválido.")
        doc_id, ts = uuid.uuid4().hex, now_iso()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO i3_documents(id, owner_id, title, source_material_id, original_content, "
                "current_version, archived, created_at, updated_at) VALUES (?,?,?,?,?,1,0,?,?)",
                (doc_id, owner_id, title, source_material_id, content, ts, ts),
            )
            conn.execute(
                "INSERT INTO i3_document_versions(document_id, version, content, author_id, reason, "
                "restored_from, created_at) VALUES (?,1,?,?,?,NULL,?)",
                (doc_id, content, owner_id, "Versión inicial", ts),
            )
        return self.get(owner_id, doc_id)

    def import_from_processor(self, owner_id: str, material_id: str) -> dict:
        """Punto de conexión con el integrante 2: trae el texto adaptado y lo guarda como v1."""
        if self.processor is None:
            raise IntegrationNotConfigured(
                "El procesador documental (integrante 2) no está conectado.",
                pending="DocumentProcessorPort.get_adapted_text")
        if not isinstance(material_id, str) or not 0 < len(material_id) <= 128:
            raise ValidationError("material_id inválido.")
        adapted = self.processor.get_adapted_text(material_id, owner_id)
        return self.create(owner_id, adapted.title, adapted.text, source_material_id=adapted.material_id)

    def get(self, owner_id: str, document_id: str, with_content: bool = True) -> dict:
        with self.db.read() as conn:
            row = load_owned(conn, document_id, owner_id)
            out = doc_dict(row)
            if with_content:
                v = conn.execute("SELECT content FROM i3_document_versions WHERE document_id=? AND version=?",
                                 (document_id, row["current_version"])).fetchone()
                out["content"] = v["content"]
        return out

    def list(self, owner_id: str, include_archived: bool = False) -> list[dict]:
        sql = "SELECT * FROM i3_documents WHERE owner_id = ?"
        if not include_archived:
            sql += " AND archived = 0"
        with self.db.read() as conn:
            rows = conn.execute(sql + " ORDER BY updated_at DESC", (owner_id,)).fetchall()
        return [doc_dict(r) for r in rows]

    def archive(self, owner_id: str, document_id: str) -> dict:
        """Archivar es reversible y no borra nada (no existe eliminación física)."""
        with self.db.transaction() as conn:
            load_owned(conn, document_id, owner_id)
            conn.execute("UPDATE i3_documents SET archived=1, updated_at=? WHERE id=?", (now_iso(), document_id))
        return self.get(owner_id, document_id, with_content=False)
