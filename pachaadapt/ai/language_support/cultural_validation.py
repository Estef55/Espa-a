"""Validación cultural y lingüística de contenidos con la comunidad.

Este módulo NO valida nada por sí mismo: registra el estado de revisión humana.
Un contenido generado automáticamente (sobre todo traducciones al quechua) nace
«pendiente» y solo pasa a «aprobado» cuando una persona revisora lo declara.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

PENDING, APPROVED, REJECTED, CHANGES = "pending", "approved", "rejected", "changes_requested"
STATUSES = (PENDING, APPROVED, REJECTED, CHANGES)
REVIEWER_ROLES = ("teacher", "community_speaker", "linguist")


def content_fingerprint(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


@dataclass
class ValidationRecord:
    content_hash: str
    language: str
    status: str = PENDING
    reviewer_id: Optional[str] = None
    reviewer_role: Optional[str] = None
    comment: str = ""
    history: list = field(default_factory=list)

    @property
    def usable_in_class(self) -> bool:
        return self.status == APPROVED

    def to_dict(self) -> dict:
        return {"content_hash": self.content_hash, "language": self.language, "status": self.status,
                "reviewer_id": self.reviewer_id, "reviewer_role": self.reviewer_role, "comment": self.comment,
                "usable_in_class": self.usable_in_class, "history": list(self.history)}


def request_validation(text: str, language: str) -> ValidationRecord:
    if not text or not text.strip():
        raise ValueError("No hay contenido para validar.")
    if not language:
        raise ValueError("Indique el idioma del contenido.")
    return ValidationRecord(content_fingerprint(text), language.lower())


def review(record: ValidationRecord, text: str, reviewer_id: str, reviewer_role: str,
           status: str, comment: str = "") -> ValidationRecord:
    """Registra una decisión humana. Si el texto cambió desde la solicitud, no se puede aprobar."""
    if status not in (APPROVED, REJECTED, CHANGES):
        raise ValueError("Estado de revisión inválido.")
    if not reviewer_id or reviewer_role not in REVIEWER_ROLES:
        raise ValueError("Se requiere una persona revisora identificada y con un rol válido.")
    if content_fingerprint(text) != record.content_hash:
        raise ValueError("El contenido cambió después de solicitar la validación; solicite una nueva.")
    if status != APPROVED and not (comment or "").strip():
        raise ValueError("Explique el motivo cuando no se aprueba el contenido.")
    record.history.append({"status": record.status, "reviewer_id": record.reviewer_id,
                           "at": datetime.now(timezone.utc).isoformat()})
    record.status, record.reviewer_id, record.reviewer_role, record.comment = status, reviewer_id, reviewer_role, comment.strip()
    return record


# Avisos de validación humana que acompañan a los materiales adaptados.
GENERAL_NOTICE = ("Las adaptaciones se generan con reglas locales y no sustituyen la revisión docente. "
                  "Revisa fidelidad, nivel y pertinencia cultural antes de usarlas con estudiantes.")


def review_notice(language: str = "es") -> str:
    if language != "es":
        return GENERAL_NOTICE + " Los contenidos en otras lenguas deben validarse con hablantes competentes de la comunidad."
    return GENERAL_NOTICE
