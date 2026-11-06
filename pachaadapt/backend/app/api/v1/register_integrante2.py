"""Registro aditivo de las rutas de adaptaciones guardadas del integrante 2.

Incluye ``/api/v1/materials/{id}/adaptations…`` (consulta, revisión docente, vínculos, exportación y audio).
No toca el procesador documental: ``main.py`` sigue conectando ``MaterialDocumentProcessor`` (texto extraído
sin transformar). ``MaterialProcessor`` (``services/material_processor.py``) queda disponible para conectarlo
con ``configure_integrations(processor=MaterialProcessor())`` si se quiere que ``/documents/import`` prefiera
la mejor adaptación guardada (lectura fácil → resumen → esquema).
"""
from __future__ import annotations

from app.api.v1 import adaptations_persisted


def register_integrante2(app) -> None:
    app.include_router(adaptations_persisted.router)
