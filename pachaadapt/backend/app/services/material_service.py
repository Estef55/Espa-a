"""Casos de uso de materiales. Binarios en disco; metadatos, texto y adaptaciones en la DB compartida.

Flujo: carga (original intacto) → extracción (texto + estado + errores) → adaptaciones persistidas,
siempre vinculadas a su material de origen (``i2_adaptations.material_id``) y, opcionalmente, a un
documento editable (I3) o a una actividad (I4) mediante ``i2_adaptation_links``.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.adaptations.errors import UNAVAILABLE_REASON, AdaptationUnavailable, ProcessingError  # noqa: F401
from ai.settings import load_settings
from ai.storage import Database

STORAGE_DIR = Path(os.getenv("PACHAADAPT_STORAGE_DIR", str(PROJECT_ROOT / "storage" / "materials"))).resolve()
MAX_UPLOAD_BYTES = int(os.getenv("PACHAADAPT_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_TEXT_CHARS = 500_000
KINDS = ("summary", "easy_read", "quiz", "outline", "image_notes", "audio")
KIND_LABEL = {"summary": "Resumen", "easy_read": "Lectura fácil", "quiz": "Preguntas de comprensión",
              "outline": "Esquema", "image_notes": "Imágenes del documento", "audio": "Audio"}
LINK_TYPES = ("document", "assignment")
_ID_RE = re.compile(r"[a-f0-9]{32}")


def _db() -> Database:
    return Database(load_settings().db_path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name).strip("._")
    return clean[:120] or "material"


def _check_id(value: str, what: str = "material") -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise ValueError(f"Identificador de {what} inválido.")
    return value


def _json(value: str | None, default):
    try:
        return json.loads(value) if value else default
    except ValueError:
        return default


# --------------------------------------------------------------------------- carga
def save_material(filename: str, content: bytes, owner_id: str, content_type: str = "application/octet-stream",
                  is_demo: bool = False) -> dict[str, Any]:
    if not owner_id or len(owner_id) > 64:
        raise ValueError("Propietario del material inválido.")
    if not content:
        raise ValueError("El archivo está vacío.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"El archivo supera el límite de {MAX_UPLOAD_BYTES} bytes.")
    name = _safe_name(filename)
    ext = Path(name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato no admitido. Se aceptan PDF y TXT.")
    if ext == ".pdf" and not content.startswith(b"%PDF"):
        raise ValueError("El archivo no parece ser un PDF válido.")
    if ext == ".txt" and b"\x00" in content[:8192]:
        raise ValueError("El archivo TXT no parece contener texto (tiene datos binarios).")
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    material_id = uuid.uuid4().hex
    original_path = STORAGE_DIR / f"{material_id}_{name}"
    created_at = _now()
    row = {
        "id": material_id, "owner_id": owner_id, "filename": name,
        "content_type": content_type, "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(), "original_path": str(original_path),
        "extracted_text": None, "extracted_at": None, "created_at": created_at,
    }
    original_path.write_bytes(content)
    try:
        with _db().transaction() as conn:
            conn.execute(
                "INSERT INTO i2_materials(id, owner_id, filename, content_type, size, sha256, original_path, extracted_text, extracted_at, created_at) "
                "VALUES (:id, :owner_id, :filename, :content_type, :size, :sha256, :original_path, :extracted_text, :extracted_at, :created_at)",
                row,
            )
            conn.execute("INSERT INTO i2_material_state(material_id, status, is_demo, updated_at) VALUES (?, 'uploaded', ?, ?)",
                         (material_id, 1 if is_demo else 0, created_at))
    except Exception:
        original_path.unlink(missing_ok=True)
        raise
    out = {k: v for k, v in row.items() if k != "original_path"}
    out.update(status="uploaded", is_demo=bool(is_demo))
    return out


def get_material(material_id: str, owner_id: str | None = None) -> dict[str, Any]:
    if not _ID_RE.fullmatch(material_id):
        raise ValueError("Identificador de material inválido.")
    with _db().read() as conn:
        row = conn.execute("SELECT * FROM i2_materials WHERE id = ?", (material_id,)).fetchone()
    if row is None or (owner_id is not None and row["owner_id"] != owner_id):
        raise FileNotFoundError("No se encontró el material.")
    return dict(row)


_SELECT = ("SELECT m.*, s.status AS st_status, s.method AS st_method, s.attempts AS st_attempts, s.error_code AS st_error_code, "
           "s.error_message AS st_error_message, s.page_count AS st_pages, s.image_count AS st_images, s.warnings_json AS st_warnings, "
           "s.is_demo AS st_demo, (SELECT COUNT(*) FROM i2_adaptations a WHERE a.material_id = m.id) AS n_adapt "
           "FROM i2_materials m LEFT JOIN i2_material_state s ON s.material_id = m.id ")


def _public(row) -> dict[str, Any]:
    """Vista pública (sin rutas del servidor ni texto) de una fila material + estado."""
    text = row["extracted_text"]
    status = row["st_status"] or ("uploaded" if text is None else "extracted" if text.strip() else "no_text")
    return {
        "id": row["id"], "filename": row["filename"], "content_type": row["content_type"], "size": row["size"],
        "sha256": row["sha256"], "extracted_at": row["extracted_at"], "created_at": row["created_at"],
        "status": status, "method": row["st_method"], "attempts": row["st_attempts"] or 0,
        "error": ({"code": row["st_error_code"], "message": row["st_error_message"]} if row["st_error_code"] else None),
        "page_count": row["st_pages"], "image_count": row["st_images"],
        "warnings": _json(row["st_warnings"], []), "is_demo": bool(row["st_demo"]),
        "adaptation_count": row["n_adapt"] or 0,
    }


def describe_material(material_id: str, owner_id: str) -> dict[str, Any]:
    get_material(material_id, owner_id)
    with _db().read() as conn:
        row = conn.execute(_SELECT + "WHERE m.id = ?", (material_id,)).fetchone()
    return _public(row)


def list_materials(owner_id: str) -> list[dict[str, Any]]:
    with _db().read() as conn:
        rows = conn.execute(_SELECT + "WHERE m.owner_id = ? ORDER BY m.created_at DESC", (owner_id,)).fetchall()
    return [_public(r) for r in rows]


def original_file(material_id: str, owner_id: str) -> tuple[Path, str, str]:
    """Ruta del original (solo dentro del almacenamiento), nombre y tipo. El original nunca se modifica."""
    meta = get_material(material_id, owner_id)
    path = Path(meta["original_path"]).resolve()
    if not path.is_file():
        raise FileNotFoundError("No se encontró el archivo original del material.")
    return path, meta["filename"], meta["content_type"]


# --------------------------------------------------------------------------- estado / extracción
def _record_state(material_id: str, **fields) -> None:
    data = {"status": "uploaded", "method": None, "error_code": None, "error_message": None, "page_count": None,
            "image_count": None, "warnings_json": "[]", **fields}
    with _db().transaction() as conn:
        if conn.execute("SELECT 1 FROM i2_material_state WHERE material_id = ?", (material_id,)).fetchone() is None:
            conn.execute("INSERT INTO i2_material_state(material_id, status, updated_at) VALUES (?, 'uploaded', ?)", (material_id, _now()))
        conn.execute(
            "UPDATE i2_material_state SET status=:status, method=:method, error_code=:error_code, error_message=:error_message, "
            "page_count=:page_count, image_count=:image_count, warnings_json=:warnings_json, attempts=attempts+1, updated_at=:now "
            "WHERE material_id=:id", {**data, "now": _now(), "id": material_id})


def _run_ocr(path: Path) -> str:
    from ai.document_processing.ocr_processor import extract_scanned_pdf_text, ocr_status
    status = ocr_status()
    if not status["available"]:
        raise RuntimeError("OCR no disponible: " + status["reason"])
    try:
        return extract_scanned_pdf_text(path, languages=status["languages"])
    except Exception as exc:  # Tesseract/Poppler pueden fallar con PDF dañados
        raise ProcessingError(f"El OCR falló: {exc}") from exc


def extract_material_text(material_id: str, use_ocr: bool = False, owner_id: str | None = None) -> dict[str, Any]:
    meta = get_material(material_id, owner_id)
    path = Path(meta["original_path"])
    if not path.is_file():
        _record_state(material_id, status="failed", error_code="original_missing",
                      error_message="No se encontró el archivo original del material.")
        raise FileNotFoundError("No se encontró el archivo original del material.")
    from ai.document_processing.text_organizer import organize_text
    ocr_attempted, method, info, warnings, tables_found = False, "txt", {}, [], False
    try:
        if path.suffix.lower() == ".txt":
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            from ai.document_processing.pdf_extractor import extract_pdf_text_with_tables, inspect_pdf
            info = inspect_pdf(path)
            text, table_pages = extract_pdf_text_with_tables(path)
            method = "pdf_text"
            if table_pages:
                tables_found = True
                warnings.append(f"Posible tabla en la(s) página(s) {', '.join(map(str, table_pages))}: se conservaron sus filas y columnas, "
                                "pero revisa el resultado contra el original.")
            if info["pages_without_text"] and text.strip() and not use_ocr:
                warnings.append(f"{len(info['pages_without_text'])} página(s) no tienen texto (posible contenido escaneado o solo imágenes): "
                                f"{', '.join(map(str, info['pages_without_text'][:10]))}. Activa OCR para intentar leerlas.")
            if use_ocr and info["pages_without_text"]:
                if not text.strip():
                    text = _run_ocr(path)
                    method = "ocr"
                else:
                    warnings.append("El PDF mezcla páginas con texto y páginas escaneadas; el OCR solo se aplica a PDF sin texto digital, "
                                    "así que las páginas escaneadas siguen sin leerse.")
                ocr_attempted = True
            if info["image_count"]:
                warnings.append(f"El documento tiene {info['image_count']} imagen(es). Su contenido visual no se convierte en texto; "
                                "usa «Imágenes del documento» para ver pies de figura y texto dentro de las imágenes.")
    except Exception as exc:
        code = ("invalid_document" if isinstance(exc, ValueError) else
                "engine_unavailable" if type(exc) is RuntimeError else "processing_error")
        _record_state(material_id, status="failed", error_code=code, error_message=str(exc))
        if code == "processing_error" and not isinstance(exc, ProcessingError):
            raise ProcessingError(f"Error al procesar el documento: {exc}") from exc
        raise
    organized = organize_text(text)
    warnings += [w for w in organized["warnings"] if not (tables_found and "tablas" in w)]
    if not text.strip():
        warnings.append("No se pudo extraer texto. Si el PDF es una imagen escaneada, activa OCR (requiere Tesseract y Poppler en el servidor).")
    status = "extracted" if text.strip() else "no_text"
    with _db().transaction() as conn:
        cur = conn.execute("UPDATE i2_materials SET extracted_text=?, extracted_at=? WHERE id=? AND owner_id=?",
                           (text, _now(), material_id, meta["owner_id"]))
        if cur.rowcount != 1:
            raise FileNotFoundError("No se encontró el material.")
    _record_state(material_id, status=status, method=method, page_count=info.get("page_count"),
                  image_count=info.get("image_count"), warnings_json=json.dumps(warnings, ensure_ascii=False))
    return {"material_id": material_id, "text": text, "characters": len(text), "ocr_used": ocr_attempted,
            "status": status, "method": method, "page_count": info.get("page_count"), "warnings": warnings}


def get_organized_text(material_id: str, owner_id: str) -> dict[str, Any]:
    meta = get_material(material_id, owner_id)
    if meta["extracted_text"] is None:
        raise ValueError("Aún no se extrajo el texto de este material. Usa «Extraer texto» primero.")
    from ai.document_processing.text_organizer import organize_text
    return {"material_id": material_id, "organized": organize_text(meta["extracted_text"]),
            "material": describe_material(material_id, owner_id)}


# --------------------------------------------------------------------------- adaptaciones
def _adaptation_dict(row, links: list[dict] | None = None) -> dict[str, Any]:
    return {
        "id": row["id"], "material_id": row["material_id"], "adaptation": row["kind"], "label": KIND_LABEL.get(row["kind"], row["kind"]),
        "status": row["status"], "result": _json(row["content_json"], None), "text": row["content_text"],
        "options": _json(row["options_json"], {}), "warnings": _json(row["warnings_json"], []),
        "source_origin": row["source_origin"], "source_sha256": row["source_sha256"], "generator": row["generator"],
        "review_required": row["review_status"] != "approved", "review_status": row["review_status"],
        "reviewed_at": row["reviewed_at"], "generated_at": row["created_at"], "persisted": True, "links": links or [],
    }


def _links_for(conn, ids: list[str]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {i: [] for i in ids}
    if ids:
        for r in conn.execute(f"SELECT * FROM i2_adaptation_links WHERE adaptation_id IN ({','.join('?' * len(ids))})", ids):
            out[r["adaptation_id"]].append({"target_type": r["target_type"], "target_id": r["target_id"], "created_at": r["created_at"]})
    return out


def _image_text(data: dict) -> str:
    return "\n".join(f"- Página {i['page']}: " + (i["description"] or i["note"] or "Sin descripción automática; requiere que el docente la escriba.")
                     for i in data["images"])


def _empty(material_id, adaptation, result, warnings, extra):
    return {"material_id": material_id, "adaptation": adaptation, "result": result, "review_required": True,
            "generated_at": _now(), "status": "empty", "persisted": False, "id": None,
            "warnings": warnings + extra, "links": []}


def adapt_material(material_id: str, adaptation: str, text: str | None = None,
                   options: dict | None = None, owner_id: str | None = None) -> dict[str, Any]:
    meta = get_material(material_id, owner_id)
    options = options or {}
    if adaptation == "translation":
        # La traducción de las adaptaciones guardadas no existe: se informa el motivo (HTTP 501), nunca se simula.
        # (Los puntos de enchufe de traducción de /adaptations siguen siendo independientes de este flujo.)
        raise AdaptationUnavailable(UNAVAILABLE_REASON)
    if adaptation not in KINDS:
        raise ValueError("Adaptación no reconocida. Opciones: " + ", ".join(KINDS) + ".")
    from ai.document_processing.text_organizer import organize_text
    origin = "edited" if text is not None else "extracted"
    warnings: list[str] = []
    status, generator, adaptation_id = "complete", "local_rules", uuid.uuid4().hex
    if adaptation == "image_notes":
        if meta["filename"].lower().endswith(".txt"):
            raise ValueError("Este material es un TXT: no contiene imágenes.")
        from ai.document_processing.image_describer import describe_pdf_images
        data = describe_pdf_images(Path(meta["original_path"]), use_ocr=bool(options.get("ocr", False)))
        if not data["total"]:
            return _empty(material_id, adaptation, data, warnings, ["El PDF no contiene imágenes legibles."])
        undescribed = [i for i in data["images"] if not i["description"]]
        if undescribed:
            status = "partial"
            warnings.append(f"{len(undescribed)} de {data['total']} imagen(es) no tienen descripción: el proyecto no incluye un modelo de visión. "
                            "Escribe la descripción a mano antes de usarlas con estudiantes.")
        if data["skipped_over_limit"]:
            status = "partial"
            warnings.append(f"Se omitieron {data['skipped_over_limit']} imagen(es) por superar el límite de procesamiento.")
        result, content_text = data, _image_text(data)
        source_text = json.dumps(data["images"], ensure_ascii=False, default=str)
    else:
        if adaptation == "audio" and options.get("from_adaptation"):
            src = get_adaptation(material_id, str(options["from_adaptation"]), owner_id or meta["owner_id"])
            if src["adaptation"] == "audio":
                raise ValueError("No se puede narrar un audio.")
            text, origin = src["text"], "edited"
        if text is None:
            text = meta.get("extracted_text")
            if text is None:
                text = extract_material_text(material_id, use_ocr=bool(options.get("ocr", False)), owner_id=owner_id)["text"]
        organized = organize_text(text)
        clean, body = organized["adapt_text"], organized["body_text"] or organized["adapt_text"]
        if not clean.strip():
            raise ValueError("No hay texto para adaptar. Verifique el PDF o active OCR para documentos escaneados.")
        if len(clean) > MAX_TEXT_CHARS:
            raise ValueError("El texto supera el límite de procesamiento (500 000 caracteres).")
        if organized["stats"]["tables"] and adaptation in ("summary", "quiz"):
            warnings.append("El documento tiene tablas: se muestran en el esquema y en lectura fácil, pero no se usan para el resumen ni las preguntas.")
        source_text = clean
        if adaptation == "summary":
            from ai.adaptations.summarizer import summarize_text
            result = content_text = summarize_text(body, int(options.get("max_sentences", 5)))
        elif adaptation == "easy_read":
            from ai.adaptations.easy_read import simplify_text
            result = content_text = simplify_text(clean, int(options.get("max_words", 22)))
        elif adaptation == "quiz":
            from ai.adaptations.quiz_generator import generate_quiz
            wanted = max(1, min(int(options.get("count", 5)), 20))
            result = generate_quiz(body, wanted)
            content_text = "\n\n".join(f"{q['id']}. {q['question']}" for q in result)
            if result and len(result) < wanted:
                status = "partial"
                warnings.append(f"El texto solo permitió {len(result)} pregunta(s) de las {wanted} pedidas.")
        elif adaptation == "outline":
            from ai.adaptations.organized_outline import build_outline, outline_to_text
            result = build_outline(organized)
            warnings += result["warnings"]
            content_text = outline_to_text(result)
            if not result["sections"]:
                result, content_text = [], ""
        else:  # audio
            from ai.adaptations.local_audio import synthesize
            audio = synthesize(clean, STORAGE_DIR / "adaptations" / f"{adaptation_id}.wav", "es")
            result = {**audio, "file": f"{adaptation_id}.wav"}
            content_text, generator = clean, "espeak_local"
            warnings.append("Voz sintética básica: sirve de apoyo de lectura, no sustituye la locución de un docente.")
    if result in ("", [], None):
        return _empty(material_id, adaptation, result, warnings,
                      ["El texto es demasiado corto o no tiene frases completas para este tipo de adaptación."])
    try:
        with _db().transaction() as conn:
            conn.execute(
                "INSERT INTO i2_adaptations(id, material_id, kind, status, options_json, content_json, content_text, warnings_json, "
                "source_sha256, source_origin, generator, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (adaptation_id, material_id, adaptation, status, json.dumps(options, ensure_ascii=False, default=str),
                 json.dumps(result, ensure_ascii=False, default=str), content_text, json.dumps(warnings, ensure_ascii=False),
                 hashlib.sha256(source_text.encode("utf-8")).hexdigest(), origin, generator, meta["owner_id"], _now()))
    except Exception:
        if adaptation == "audio":
            (STORAGE_DIR / "adaptations" / f"{adaptation_id}.wav").unlink(missing_ok=True)
        raise
    return get_adaptation(material_id, adaptation_id, meta["owner_id"])


def list_adaptations(material_id: str, owner_id: str, kind: str | None = None) -> list[dict[str, Any]]:
    get_material(material_id, owner_id)
    sql, args = "SELECT * FROM i2_adaptations WHERE material_id = ?", [material_id]
    if kind:
        sql += " AND kind = ?"
        args.append(kind)
    with _db().read() as conn:
        rows = conn.execute(sql + " ORDER BY created_at DESC", args).fetchall()
        links = _links_for(conn, [r["id"] for r in rows])
    return [_adaptation_dict(r, links[r["id"]]) for r in rows]


def get_adaptation(material_id: str, adaptation_id: str, owner_id: str) -> dict[str, Any]:
    get_material(material_id, owner_id)
    _check_id(adaptation_id, "adaptación")
    with _db().read() as conn:
        row = conn.execute("SELECT * FROM i2_adaptations WHERE id = ? AND material_id = ?", (adaptation_id, material_id)).fetchone()
        if row is None:
            raise FileNotFoundError("No se encontró la adaptación.")
        links = _links_for(conn, [adaptation_id])[adaptation_id]
    return _adaptation_dict(row, links)


def review_adaptation(material_id: str, adaptation_id: str, approved: bool, owner_id: str) -> dict[str, Any]:
    """Revisión humana explícita: solo el docente dueño marca una adaptación como revisada."""
    get_adaptation(material_id, adaptation_id, owner_id)
    with _db().transaction() as conn:
        if approved:
            conn.execute("UPDATE i2_adaptations SET review_status='approved', reviewed_by=?, reviewed_at=? WHERE id=?",
                         (owner_id, _now(), adaptation_id))
        else:
            conn.execute("UPDATE i2_adaptations SET review_status='pending', reviewed_by=NULL, reviewed_at=NULL WHERE id=?", (adaptation_id,))
    return get_adaptation(material_id, adaptation_id, owner_id)


def link_adaptation(material_id: str, adaptation_id: str, target_type: str, target_id: str, owner_id: str) -> dict[str, Any]:
    """Registra que una adaptación se convirtió en un documento editable (I3) o una actividad (I4)."""
    get_adaptation(material_id, adaptation_id, owner_id)
    if target_type not in LINK_TYPES:
        raise ValueError("target_type debe ser «document» o «assignment».")
    if not isinstance(target_id, str) or not 0 < len(target_id) <= 128:
        raise ValueError("target_id inválido.")
    table, owner_col = (("i3_documents", "owner_id") if target_type == "document" else ("assignments", "created_by"))
    try:
        with _db().transaction() as conn:
            if conn.execute(f"SELECT 1 FROM {table} WHERE id = ? AND {owner_col} = ?", (target_id, owner_id)).fetchone() is None:
                raise FileNotFoundError("No se encontró el destino, o no te pertenece.")
            conn.execute("INSERT OR IGNORE INTO i2_adaptation_links(adaptation_id, target_type, target_id, created_at) VALUES (?,?,?,?)",
                         (adaptation_id, target_type, target_id, _now()))
    except sqlite3.OperationalError as exc:
        raise ValueError("No se puede vincular: el módulo de destino no está inicializado en esta base de datos.") from exc
    return get_adaptation(material_id, adaptation_id, owner_id)


def export_adaptation(material_id: str, adaptation_id: str, fmt: str, owner_id: str) -> tuple[bytes, str, str]:
    from ai.adaptations.accessibility import render_html, render_text
    ad = get_adaptation(material_id, adaptation_id, owner_id)
    if ad["adaptation"] == "audio":
        raise ValueError("El audio se descarga con su propio enlace.")
    meta = get_material(material_id, owner_id)
    title, base = f"{ad['label']} — {meta['filename']}", Path(meta["filename"]).stem
    reviewed = ad["reviewed_at"] if ad["review_status"] == "approved" else None
    if fmt == "html":
        return (render_html(title, ad["text"], ad["label"], meta["filename"], reviewed).encode("utf-8"),
                "text/html; charset=utf-8", f"{base}_{ad['adaptation']}.html")
    if fmt == "txt":
        return (render_text(title, ad["text"], ad["label"], meta["filename"], reviewed).encode("utf-8"),
                "text/plain; charset=utf-8", f"{base}_{ad['adaptation']}.txt")
    raise ValueError("Formato de exportación no admitido. Usa html o txt. El braille no se exporta desde aquí: se pide en /adaptations/materials/{id}/accessible.")


def adaptation_audio_file(material_id: str, adaptation_id: str, owner_id: str) -> Path:
    ad = get_adaptation(material_id, adaptation_id, owner_id)
    if ad["adaptation"] != "audio":
        raise ValueError("Esta adaptación no es un audio.")
    folder = (STORAGE_DIR / "adaptations").resolve()
    path = (folder / f"{adaptation_id}.wav").resolve()
    if folder not in path.parents or not path.is_file():
        raise FileNotFoundError("No se encontró el archivo de audio.")
    return path


def capabilities() -> dict[str, Any]:
    """Qué puede hacer REALMENTE este servidor ahora. Ninguna capacidad usa servicios en línea."""
    from ai.adaptations.local_audio import audio_status
    from ai.document_processing.ocr_processor import ocr_status
    from ai.language_support.language_registry import list_languages
    try:
        import pypdf  # noqa: F401
        pdf = {"available": True, "reason": None}
    except ImportError:
        pdf = {"available": False, "reason": "Falta instalar pypdf."}
    try:
        import PIL  # noqa: F401
        pil = True
    except ImportError:
        pil = False
    local = {"available": True, "reason": None, "needs_internet": False}
    return {
        "formats": [".pdf", ".txt"], "max_upload_bytes": MAX_UPLOAD_BYTES,
        "features": {
            "text_extraction": {**pdf, "needs_internet": False},
            "ocr": {**ocr_status(), "needs_internet": False},
            "summary": local, "easy_read": local, "quiz": local, "outline": local,
            "image_notes": {**pdf, "needs_internet": False,
                            "limits": "Solo pies de figura y texto dentro de la imagen (con OCR); no describe el contenido visual."
                                      + ("" if pil else " Falta Pillow: algunas imágenes no se podrán leer.")},
            "audio": {**audio_status(), "needs_internet": False},
            "translation": {"available": False, "reason": UNAVAILABLE_REASON, "needs_internet": None},
            "braille": {"available": False, "reason": "No se exporta desde las adaptaciones guardadas. La transcripción Braille de grado 1 (que debe revisar una persona con formación en Braille) se pide en /adaptations/materials/{id}/accessible.", "needs_internet": None},
        },
        "languages": list_languages(),
        "offline_note": "Subir, extraer y adaptar necesitan conexión con el servidor de la escuela. Los materiales y adaptaciones ya "
                        "descargados en este dispositivo se pueden consultar sin conexión.",
    }
