"""Registro de los routers del integrante 3 en la aplicación.

Para activarlos, añadir en ``backend/app/main.py`` (cambio aditivo, ver LEEME_INTEGRACION.md):

    from app.api.v1.register import register_integrante3
    register_integrante3(app)
"""
from __future__ import annotations

from app.api.v1 import ai_chat, documents, preferences, reports


def register_integrante3(app) -> None:
    for module in (preferences, documents, ai_chat, reports):
        app.include_router(module.router)
