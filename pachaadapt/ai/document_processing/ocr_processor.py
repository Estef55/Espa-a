"""OCR opcional para PDF escaneados; requiere Tesseract y dependencias del sistema."""
from pathlib import Path
from typing import Union

def extract_scanned_pdf_text(source: Union[str, Path, bytes], languages: str = "spa") -> str:
    try:
        import io
        import pytesseract
        from pdf2image import convert_from_bytes, convert_from_path
    except ImportError as exc:
        raise RuntimeError("OCR opcional: instale pytesseract y pdf2image; también Tesseract y Poppler.") from exc
    if isinstance(source, bytes):
        images = convert_from_bytes(source)
    else:
        images = convert_from_path(str(source))
    chunks = []
    for i, image in enumerate(images, 1):
        text = pytesseract.image_to_string(image, lang=languages).strip()
        if text:
            chunks.append(f"[Página {i}]\n{text}")
    return "\n\n".join(chunks).strip()
