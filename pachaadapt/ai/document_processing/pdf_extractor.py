"""Extracción segura de texto de PDF; el original nunca se modifica."""
from pathlib import Path
from typing import Union

def extract_pdf_text(source: Union[str, Path, bytes]) -> str:
    """Extrae texto de un PDF digital. Acepta ruta o bytes; requiere pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("La extracción PDF requiere instalar 'pypdf'.") from exc
    import io
    stream = io.BytesIO(source) if isinstance(source, bytes) else str(source)
    try:
        reader = PdfReader(stream, strict=False)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:
                raise ValueError("El PDF está protegido con contraseña.") from exc
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                pages.append(f"[Página {index}]\n{text}")
        return "\n\n".join(pages).strip()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"No se pudo leer el PDF: {exc}") from exc
