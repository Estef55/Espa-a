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


def ocr_status(languages: str | None = None) -> dict:
    """Informa si el OCR puede ejecutarse AHORA en este servidor y por qué no, si no puede."""
    import os
    import shutil
    languages = languages or os.getenv("PACHAADAPT_OCR_LANGS", "spa")
    try:
        import pytesseract
        import pdf2image  # noqa: F401
    except ImportError:
        return {"available": False, "languages": languages, "reason": "Faltan los paquetes Python pytesseract y pdf2image."}
    if not shutil.which("tesseract"):
        return {"available": False, "languages": languages, "reason": "No está instalado el programa Tesseract."}
    if not shutil.which("pdftoppm"):
        return {"available": False, "languages": languages, "reason": "No está instalado Poppler (pdftoppm)."}
    try:
        installed = set(pytesseract.get_languages(config=""))
    except Exception:
        installed = set()
    missing = [l for l in languages.split("+") if installed and l not in installed]
    if missing:
        return {"available": False, "languages": languages,
                "reason": f"Tesseract no tiene el idioma «{', '.join(missing)}» (instalados: {', '.join(sorted(installed))})."}
    return {"available": True, "languages": languages, "reason": None}
