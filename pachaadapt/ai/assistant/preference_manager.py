"""Preferencias del docente: validación, persistencia y aplicación.

Solo se admiten opciones que el módulo realmente usa (asistente y parámetros de
adaptación). No se guarda información personal.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from ai.errors import ValidationError
from ai.storage import Database, now_iso

ALLOWED: dict[str, tuple] = {
    "education_level": ("inicial", "primaria", "secundaria"),
    "complexity": ("basico", "intermedio", "avanzado"),
    "length": ("corta", "media", "larga"),
    "tone": ("formal", "cercano", "neutro"),
    "format": ("texto", "esquema", "lista"),
    "language": ("es", "qu"),
}
DEFAULTS: dict[str, Optional[str]] = {
    "education_level": None,   # None = no especificado (el nivel piloto aún no está validado)
    "complexity": "intermedio",
    "length": "media",
    "tone": "neutro",
    "format": "texto",
    "language": "es",
}

_LABELS = {
    "education_level": "nivel educativo",
    "complexity": "complejidad",
    "length": "extensión",
    "tone": "tono",
    "format": "formato de presentación",
    "language": "idioma de respuesta",
}


def validate_update(values: Any) -> dict:
    if not isinstance(values, dict) or not values:
        raise ValidationError("Se requiere un objeto con al menos una preferencia.")
    clean: dict[str, Optional[str]] = {}
    for key, value in values.items():
        if key not in ALLOWED:
            raise ValidationError(f"Preferencia desconocida: {key!r}.", allowed_keys=sorted(ALLOWED))
        if value is None and key == "education_level":
            clean[key] = None
            continue
        if not isinstance(value, str) or value not in ALLOWED[key]:
            raise ValidationError(f"Valor inválido para {key!r}.", allowed_values=list(ALLOWED[key]))
        clean[key] = value
    return clean


class PreferenceManager:
    def __init__(self, db: Database):
        self.db = db

    def get(self, teacher_id: str) -> dict:
        with self.db.read() as conn:
            row = conn.execute(
                "SELECT prefs_json, updated_at FROM i3_teacher_preferences WHERE teacher_id = ?",
                (teacher_id,),
            ).fetchone()
        if row is None:
            return {"preferences": dict(DEFAULTS), "is_default": True, "updated_at": None,
                    "allowed_values": {k: list(v) for k, v in ALLOWED.items()}}
        stored = json.loads(row["prefs_json"])
        merged = {**DEFAULTS, **{k: v for k, v in stored.items() if k in ALLOWED}}
        return {"preferences": merged, "is_default": False, "updated_at": row["updated_at"],
                "allowed_values": {k: list(v) for k, v in ALLOWED.items()}}

    def update(self, teacher_id: str, values: Any) -> dict:
        clean = validate_update(values)
        ts = now_iso()
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT prefs_json FROM i3_teacher_preferences WHERE teacher_id = ?", (teacher_id,)
            ).fetchone()
            current = json.loads(row["prefs_json"]) if row else {}
            current.update(clean)
            payload = json.dumps(current, ensure_ascii=False, sort_keys=True)
            if row:
                conn.execute(
                    "UPDATE i3_teacher_preferences SET prefs_json = ?, updated_at = ? WHERE teacher_id = ?",
                    (payload, ts, teacher_id),
                )
            else:
                conn.execute(
                    "INSERT INTO i3_teacher_preferences(teacher_id, prefs_json, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (teacher_id, payload, ts, ts),
                )
        return self.get(teacher_id)

    def clear(self, teacher_id: str) -> dict:
        """Elimina preferencias personalizadas; futuras respuestas usan los valores por defecto."""
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM i3_teacher_preferences WHERE teacher_id = ?", (teacher_id,))
        return self.get(teacher_id)


def prompt_fragment(prefs: dict) -> str:
    """Instrucciones para el asistente derivadas de las preferencias (en español)."""
    lines = []
    for key in ("education_level", "complexity", "length", "tone", "format", "language"):
        value = prefs.get(key)
        if value:
            lines.append(f"- {_LABELS[key]}: {value}")
    return "Preferencias del docente (aplícalas cuando sean pertinentes):\n" + "\n".join(lines)


def adaptation_params(prefs: dict) -> dict:
    """Parámetros PROPUESTOS para una solicitud de adaptación al procesador del integrante 2.
    El contrato real aún no existe: este mapeo es la propuesta a validar con el integrante 2."""
    return {k: prefs.get(k) for k in ALLOWED if prefs.get(k) is not None}
