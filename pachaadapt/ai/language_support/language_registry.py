"""Registro de idiomas y variedades lingüísticas.

Principios del proyecto (documento de definición, sección 5):
- El idioma de la interfaz es independiente del idioma de cada material.
- Primera etapa: español y quechua. La variedad de quechua NO se asume: debe
  identificarse en campo con la comunidad piloto, por eso queda como «por definir».
- Agregar un idioma es agregar un registro; no se rehace la estructura.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Optional

_CODE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


@dataclass(frozen=True)
class Language:
    code: str                       # código BCP-47 / ISO 639 (ej. "es", "qu")
    name: str                       # nombre en español
    native_name: str
    varieties: tuple = ()           # variedades conocidas (códigos o nombres)
    variety_confirmed: bool = False  # ¿la variedad fue definida con la comunidad?
    ui_available: bool = False      # ¿existe traducción de interfaz (frontend/src/i18n)?
    machine_translation_validated: bool = False  # ¿hay traducción automática validada?
    notes: str = ""


class LanguageRegistry:
    def __init__(self) -> None:
        self._langs: dict[str, Language] = {}

    def register(self, language: Language) -> Language:
        if not isinstance(language, Language) or not _CODE.match(language.code or ""):
            raise ValueError("Código de idioma inválido.")
        if not language.name.strip():
            raise ValueError("El idioma necesita un nombre.")
        self._langs[language.code.lower()] = language
        return language

    def get(self, code: str) -> Language:
        found = self._langs.get(self._base(code)) if code else None
        if found is None:
            raise KeyError(f"Idioma no registrado: {code!r}.")
        return found

    def is_supported(self, code: str) -> bool:
        return bool(code) and self._base(code) in self._langs

    def all(self) -> list[Language]:
        return sorted(self._langs.values(), key=lambda lang: lang.code)

    def confirm_variety(self, code: str, variety: str) -> Language:
        """Fija la variedad definida con la comunidad (decisión humana, no automática)."""
        lang = self.get(code)
        if not variety or not variety.strip():
            raise ValueError("Indique la variedad acordada con la comunidad.")
        updated = replace(lang, varieties=tuple(dict.fromkeys(lang.varieties + (variety.strip(),))),
                          variety_confirmed=True)
        self._langs[updated.code] = updated
        return updated

    @staticmethod
    def _base(code: str) -> str:
        return (code or "").strip().lower().split("-")[0]

    def describe(self) -> list[dict]:
        return [{
            "code": l.code, "name": l.name, "native_name": l.native_name, "varieties": list(l.varieties),
            "variety_confirmed": l.variety_confirmed, "ui_available": l.ui_available,
            "machine_translation_validated": l.machine_translation_validated, "notes": l.notes,
        } for l in self.all()]


def default_registry() -> LanguageRegistry:
    reg = LanguageRegistry()
    reg.register(Language("es", "Español", "Español", ("es-PE",), variety_confirmed=False, ui_available=True,
                          notes="Idioma inicial. La variedad regional se ajustará con la investigación de campo."))
    reg.register(Language("qu", "Quechua", "Runasimi", (), variety_confirmed=False, ui_available=True,
                          notes="Variedad por definir con la comunidad piloto. No se presenta ninguna variante como "
                                "universal. Todo contenido en quechua requiere validación de hablantes competentes."))
    return reg


REGISTRY = default_registry()
