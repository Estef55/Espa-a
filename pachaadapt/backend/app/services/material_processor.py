"""Puerto del procesador documental (integrante 2) hacia los documentos editables (integrante 3).

Implementa ``DocumentProcessorPort.get_adapted_text`` de ``ai/assistant/document_builder.py``.
Contrato acordado con I3: devuelve el texto de la mejor adaptación TEXTUAL disponible del material
(lectura fácil → resumen → esquema); si no hay ninguna, el texto extraído y organizado. El título
indica de cuál se trata, de modo que nunca se presente texto sin adaptar como si lo estuviera.
Solo entrega materiales del docente dueño (otro docente recibe «no encontrado»).
"""
from __future__ import annotations

from app.core import paths  # noqa: F401
from ai.assistant.document_builder import AdaptedDocument
from ai.errors import NotFound, ValidationError
from app.services import material_service as ms

PREFERENCE = ("easy_read", "summary", "outline")


class MaterialProcessor:
    def get_adapted_text(self, material_id: str, owner_id: str) -> AdaptedDocument:
        try:
            meta = ms.get_material(material_id, owner_id)
        except (ValueError, FileNotFoundError):
            raise NotFound("Material no encontrado.")
        for kind in PREFERENCE:
            found = ms.list_adaptations(material_id, owner_id, kind)
            if found:
                best = found[0]
                return AdaptedDocument(material_id, f"{best['label']} — {meta['filename']}", best["text"])
        if meta["extracted_text"] is None or not meta["extracted_text"].strip():
            raise ValidationError("El material aún no tiene texto extraído ni adaptaciones. Extrae el texto o genera una adaptación primero.")
        from ai.document_processing.text_organizer import organize_text
        return AdaptedDocument(material_id, f"Texto extraído — {meta['filename']}", organize_text(meta["extracted_text"])["adapt_text"])
