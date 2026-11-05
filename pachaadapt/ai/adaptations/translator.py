"""Traducción y adaptación lingüística, con revisión humana obligatoria.

PACHAADAPT NO incluye un modelo de traducción local. Por eso este módulo:
- NO inventa traducciones: sin un proveedor configurado lanza ``TranslationUnavailable``.
- Acepta un proveedor inyectado (función ``(texto, origen, destino) -> texto``), que puede
  ser un servicio en línea o, a futuro, un modelo local. Esa dependencia se declara en
  ``requires_connection`` para que la interfaz no prometa uso sin Internet.
- Marca todo resultado como ``human_review_required`` (el quechua exige además validación
  de hablantes competentes; ver ``ai/language_support``).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Optional

from ai.language_support.cultural_validation import request_validation
from ai.language_support.language_registry import REGISTRY, LanguageRegistry

MAX_CHARS = 100_000
Provider = Callable[[str, str, str], str]


class TranslationUnavailable(RuntimeError):
    """No hay proveedor de traducción configurado (o el idioma no está registrado)."""


def translation_status(provider: Optional[Provider] = None, requires_connection: bool = True) -> dict:
    return {
        "available": provider is not None,
        "requires_connection": bool(requires_connection),
        "offline_capable": provider is not None and not requires_connection,
        "reason": None if provider is not None else
        "No hay proveedor de traducción configurado; no se generan traducciones simuladas.",
    }


def translate_text(text: str, source: str, target: str, provider: Optional[Provider] = None,
                   registry: LanguageRegistry = REGISTRY, requires_connection: bool = True) -> dict:
    if not text or not text.strip():
        raise ValueError("No hay texto para traducir.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"El texto supera el límite de traducción ({MAX_CHARS} caracteres).")
    for code in (source, target):
        if not registry.is_supported(code):
            raise TranslationUnavailable(f"Idioma no registrado: {code!r}.")
    src, dst = registry.get(source), registry.get(target)
    if src.code == dst.code:
        raise ValueError("El idioma de origen y destino son iguales.")
    if provider is None:
        raise TranslationUnavailable(
            "No hay un servicio ni un modelo de traducción configurado. PACHAADAPT no genera "
            "traducciones simuladas; configure un proveedor o traduzca manualmente.")
    translated = provider(text, src.code, dst.code)
    if not isinstance(translated, str) or not translated.strip():
        raise TranslationUnavailable("El proveedor de traducción no devolvió texto.")
    record = request_validation(translated, dst.code)
    return {
        "source_language": src.code, "target_language": dst.code, "text": translated,
        "human_review_required": True,
        "community_validation_required": dst.code != "es" or not dst.variety_confirmed,
        "variety_confirmed": dst.variety_confirmed,
        "requires_connection": bool(requires_connection),
        "validation": record.to_dict(),
        "warning": "Traducción automática: no garantiza corrección ni pertinencia cultural. Revise antes de usarla en clase.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
