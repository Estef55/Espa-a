"""Descripciones textuales de imágenes (texto alternativo).

Límites explícitos:
- ``inspect_image`` es real y local: formato, dimensiones y tamaño, sin interpretar el contenido.
- ``describe_image`` necesita un proveedor de visión inyectado (``bytes, idioma -> texto``). PACHAADAPT no incluye
  un modelo de visión local; sin proveedor lanza ``ImageDescriptionUnavailable`` y NO inventa descripciones.
- Toda descripción queda marcada para revisión docente.
"""
from __future__ import annotations

import io
import re
import struct
from pathlib import Path
from typing import Callable, Optional, Union

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


# ---------------------------------------------------------------------------
# Notas de imágenes de un PDF (pies de figura y texto leído con OCR). No describe el contenido visual.
# ---------------------------------------------------------------------------
CAPTION_RE = re.compile(r"^\s*((?:Figura|Fig\.|Imagen|Ilustración|Gráfico|Esquema|Diagrama)\s*\d*\s*[.:\-–—]?\s*\S.*)$", re.I)
MAX_IMAGES = 60


def _captions_by_page(reader) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for index, page in enumerate(reader.pages, start=1):
        lines = [l.strip() for l in (page.extract_text() or "").splitlines()]
        found = []
        for n, l in enumerate(lines):
            m = CAPTION_RE.match(l)
            if not m:
                continue
            caption, k = m.group(1).strip(), n + 1
            # un pie de figura puede ocupar varias líneas: se une hasta cerrar la oración (máx. 3 líneas más)
            while not caption.endswith((".", "!", "?")) and k < len(lines) and k <= n + 3 and lines[k] and not CAPTION_RE.match(lines[k]):
                caption += " " + lines[k]; k += 1
            found.append(caption)
        if found:
            out[index] = found
    return out


def _ocr_image(data: bytes) -> str:
    try:
        import os
        import pytesseract
        from PIL import Image
        text = pytesseract.image_to_string(Image.open(io.BytesIO(data)), lang=os.getenv("PACHAADAPT_OCR_LANGS", "spa"))
        return re.sub(r"\s+", " ", text).strip()
    except Exception:
        return ""


def describe_pdf_images(source: Union[str, Path, bytes], use_ocr: bool = False, max_images: int = MAX_IMAGES) -> dict:
    from ai.document_processing.pdf_extractor import _open
    try:
        reader = _open(source)
        captions = _captions_by_page(reader)
        items, skipped = [], 0
        for page_no, page in enumerate(reader.pages, start=1):
            try:
                page_images = list(page.images)
            except Exception as exc:
                items.append({"page": page_no, "name": None, "format": None, "width": None, "height": None, "bytes": None,
                              "caption": None, "ocr_text": None, "description": None, "status": "unreadable",
                              "note": f"No se pudieron leer las imágenes de esta página ({exc.__class__.__name__})."})
                continue
            page_caps = captions.get(page_no, [])
            exact = len(page_caps) == len(page_images)
            for k, img in enumerate(page_images):
                if len(items) >= max_images:
                    skipped += 1
                    continue
                item = {"page": page_no, "name": getattr(img, "name", None), "format": None, "width": None, "height": None,
                        "bytes": None, "caption": None, "ocr_text": None, "description": None,
                        "status": "needs_teacher_description", "note": ""}
                data = b""
                try:
                    data = img.data
                    item["bytes"] = len(data)
                    item["format"] = (Path(item["name"] or "").suffix.lstrip(".") or "desconocido").lower()
                    try:
                        item["width"], item["height"] = img.image.size
                    except Exception:
                        pass
                except Exception as exc:
                    item.update(status="unreadable", note=f"No se pudo leer esta imagen ({exc.__class__.__name__}); puede faltar Pillow.")
                    items.append(item)
                    continue
                if page_caps and exact:
                    item["caption"] = page_caps[k]
                elif page_caps:
                    item["note"] = "La página tiene pies de figura, pero no se pueden asignar con seguridad a cada imagen: " + " | ".join(page_caps)
                if use_ocr and data:
                    item["ocr_text"] = _ocr_image(data) or None
                parts = [p for p in (item["caption"], f"Texto dentro de la imagen: {item['ocr_text']}" if item["ocr_text"] else None) if p]
                if parts:
                    item["description"] = " — ".join(parts)
                    item["status"] = "from_caption_or_ocr"
                items.append(item)
        return {"images": items, "total": len(items), "skipped_over_limit": skipped,
                "described": sum(1 for i in items if i["description"]),
                "visual_description_available": False, "method": "pdf_caption_and_ocr_only"}
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise ValueError(f"No se pudo leer el PDF: {exc}") from exc
