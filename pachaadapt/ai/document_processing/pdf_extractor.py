"""Extracción segura de texto de PDF; el original nunca se modifica."""
from pathlib import Path
from typing import Union

def _unlock(reader) -> None:
    """Abre PDF cifrados sin contraseña de usuario; si pide contraseña, lo informa (decrypt devuelve 0, no lanza)."""
    if reader.is_encrypted:
        try:
            ok = reader.decrypt("")
        except Exception as exc:
            raise ValueError("El PDF está protegido con contraseña.") from exc
        if not ok:
            raise ValueError("El PDF está protegido con contraseña.")


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
        _unlock(reader)
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


def _open(source):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("La extracción PDF requiere instalar 'pypdf'.") from exc
    import io
    reader = PdfReader(io.BytesIO(source) if isinstance(source, bytes) else str(source), strict=False)
    _unlock(reader)
    return reader


def inspect_pdf(source: Union[str, Path, bytes]) -> dict:
    """Describe un PDF sin modificarlo: páginas, páginas sin texto e imágenes incrustadas.
    Sirve para avisar cuando un PDF es escaneado o contiene imágenes que no se leen como texto."""
    try:
        reader = _open(source)
        with_text, without_text, images = [], [], 0
        for index, page in enumerate(reader.pages, start=1):
            (with_text if (page.extract_text() or "").strip() else without_text).append(index)
            try:
                images += len(page.images)
            except Exception:
                pass  # imágenes ilegibles: se informan al describirlas
        return {"page_count": len(reader.pages), "pages_with_text": with_text,
                "pages_without_text": without_text, "image_count": images}
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise ValueError(f"No se pudo leer el PDF: {exc}") from exc


def _layout_has_table(page) -> bool:
    import re
    try:
        lines = [l.strip() for l in (page.extract_text(extraction_mode="layout") or "").splitlines()]
    except Exception:
        return False
    run = 0
    for line in lines + [""]:
        if re.search(r"\S {3,}\S", line):
            run += 1
            if run >= 2:
                return True
        else:
            run = 0
    return False


def extract_pdf_text_with_tables(source: Union[str, Path, bytes]) -> tuple[str, list[int]]:
    """Como ``extract_pdf_text`` pero en las páginas con una posible tabla usa la disposición espacial para
    conservar filas y columnas. Devuelve (texto, páginas con tabla). Si el modo «layout» falla se usa el texto normal."""
    try:
        reader = _open(source)
        pages, table_pages = [], []
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text and _layout_has_table(page):
                try:
                    laid = "\n".join(l.strip() for l in page.extract_text(extraction_mode="layout").splitlines())
                    if laid.strip():
                        text = laid.strip(); table_pages.append(index)
                except Exception:
                    pass
            if text:
                pages.append(f"[Página {index}]\n{text}")
        return "\n\n".join(pages).strip(), table_pages
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise ValueError(f"No se pudo leer el PDF: {exc}") from exc
