"""Puertos de integración con servicios existentes de los demás módulos."""
from __future__ import annotations

from pathlib import Path

from ai.assistant.document_builder import AdaptedDocument
from ai.errors import NotFound, ValidationError
from app.services import material_service


class MaterialDocumentProcessor:
    """Expone el texto extraído de materiales propios para documentos editables.

    Reutiliza la API de materiales del integrante 2; no duplica archivos ni datos,
    no transforma el contenido y no inventa texto. Si aún no fue extraído, solicita
    la extracción existente (OCR no se activa implícitamente).
    """

    def get_adapted_text(self, material_id: str, owner_id: str) -> AdaptedDocument:
        try:
            material = material_service.get_material(material_id, owner_id=owner_id)
            text = material.get("extracted_text")
            if text is None:
                text = material_service.extract_material_text(material_id, owner_id=owner_id)["text"]
        except FileNotFoundError:
            raise NotFound("Material no encontrado.") from None
        except ValueError as exc:
            raise ValidationError(str(exc)) from None

        if not isinstance(text, str) or not text.strip():
            raise ValidationError(
                "El material no contiene texto extraíble. Si es un PDF escaneado, extraiga el texto con OCR desde Materiales.")
        title = Path(material["filename"]).stem.strip() or "Material educativo"
        return AdaptedDocument(material_id=material_id, title=title[:200], text=text)
