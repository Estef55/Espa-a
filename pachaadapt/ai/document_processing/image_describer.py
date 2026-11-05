"""Descripciones textuales de imágenes (texto alternativo).

Límites explícitos:
- ``inspect_image`` es real y local: formato, dimensiones y tamaño, sin interpretar el contenido.
- ``describe_image`` necesita un proveedor de visión inyectado (``bytes, idioma -> texto``). PACHAADAPT no incluye
  un modelo de visión local; sin proveedor lanza ``ImageDescriptionUnavailable`` y NO inventa descripciones.
- Toda descripción queda marcada para revisión docente.
"""
from __future__ import annotations

import struct
from typing import Callable, Optional

MAX_IMAGE_BYTES = 10 * 1024 * 1024
Provider = Callable[[bytes, str], str]


class ImageDescriptionUnavailable(RuntimeError):
    """No hay proveedor de visión configurado."""


def _sniff(data: bytes) -> tuple[str, Optional[int], Optional[int]]:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return "png", w, h
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        w, h = struct.unpack("<HH", data[6:10])
        return "gif", w, h
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return "jpeg", w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
        return "jpeg", None, None
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", None, None
    raise ValueError("Formato de imagen no reconocido. Se aceptan PNG, JPEG, GIF y WebP.")


def inspect_image(data: bytes) -> dict:
    if not data:
        raise ValueError("La imagen está vacía.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("La imagen supera el límite de 10 MB.")
    fmt, w, h = _sniff(data)
    return {"format": fmt, "width": w, "height": h, "bytes": len(data)}


def describe_image(data: bytes, language: str = "es", provider: Optional[Provider] = None,
                   requires_connection: bool = True) -> dict:
    info = inspect_image(data)
    if provider is None:
        raise ImageDescriptionUnavailable(
            "No hay un modelo de visión configurado. PACHAADAPT no inventa descripciones; "
            "escriba el texto alternativo manualmente o configure un proveedor.")
    description = provider(data, language)
    if not isinstance(description, str) or not description.strip():
        raise ImageDescriptionUnavailable("El proveedor no devolvió una descripción.")
    return {"alt_text": description.strip(), "language": language, "image": info,
            "requires_connection": bool(requires_connection), "review_required": True,
            "note": "Descripción automática: verifique que sea fiel y adecuada antes de publicarla."}


def alt_text_template(data: bytes, language: str = "es") -> dict:
    """Plantilla para que el docente redacte el texto alternativo (no es una descripción generada)."""
    info = inspect_image(data)
    return {"image": info, "alt_text": "", "language": language, "review_required": True,
            "guide": ["¿Qué muestra la imagen y por qué importa en este material?",
                      "Si contiene texto, transcríbalo.", "Sea breve: una o dos oraciones."]}
