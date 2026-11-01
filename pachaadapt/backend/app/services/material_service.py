"""Casos de uso de materiales. Binarios en disco; metadatos en la DB compartida."""
from __future__ import annotations

import hashlib
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.settings import load_settings
from ai.storage import Database

STORAGE_DIR = Path(os.getenv("PACHAADAPT_STORAGE_DIR", str(PROJECT_ROOT / "storage" / "materials"))).resolve()
MAX_UPLOAD_BYTES = int(os.getenv("PACHAADAPT_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {".pdf", ".txt"}


def _db() -> Database:
    return Database(load_settings().db_path)


def _safe_name(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name).strip("._")
    return clean[:120] or "material"


def _metadata(row) -> dict[str, Any]:
    return dict(row)


def save_material(filename: str, content: bytes, owner_id: str, content_type: str = "application/octet-stream") -> dict[str, Any]:
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
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    material_id = uuid.uuid4().hex
    original_path = STORAGE_DIR / f"{material_id}_{name}"
    created_at = datetime.now(timezone.utc).isoformat()
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
    except Exception:
        original_path.unlink(missing_ok=True)
        raise
    return {k: v for k, v in row.items() if k != "original_path"}


def get_material(material_id: str, owner_id: str | None = None) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{32}", material_id):
        raise ValueError("Identificador de material inválido.")
    with _db().read() as conn:
        row = conn.execute("SELECT * FROM i2_materials WHERE id = ?", (material_id,)).fetchone()
    if row is None or (owner_id is not None and row["owner_id"] != owner_id):
        raise FileNotFoundError("No se encontró el material.")
    return _metadata(row)


def extract_material_text(material_id: str, use_ocr: bool = False, owner_id: str | None = None) -> dict[str, Any]:
    meta = get_material(material_id, owner_id)
    path = Path(meta["original_path"])
    if not path.is_file():
        raise FileNotFoundError("No se encontró el archivo original del material.")
    ocr_attempted = False
    if path.suffix.lower() == ".txt":
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        from ai.document_processing.pdf_extractor import extract_pdf_text
        text = extract_pdf_text(path)
        if use_ocr and not text.strip():
            from ai.document_processing.ocr_processor import extract_scanned_pdf_text
            text = extract_scanned_pdf_text(path)
            ocr_attempted = True
    extracted_at = datetime.now(timezone.utc).isoformat()
    with _db().transaction() as conn:
        cur = conn.execute("UPDATE i2_materials SET extracted_text=?, extracted_at=? WHERE id=? AND owner_id=?",
                            (text, extracted_at, material_id, meta["owner_id"]))
        if cur.rowcount != 1:
            raise FileNotFoundError("No se encontró el material.")
    return {"material_id": material_id, "text": text, "characters": len(text), "ocr_used": ocr_attempted}


def adapt_material(material_id: str, adaptation: str, text: str | None = None,
                   options: dict | None = None, owner_id: str | None = None) -> dict[str, Any]:
    meta = get_material(material_id, owner_id)
    options = options or {}
    if text is None:
        text = meta.get("extracted_text")
        if text is None:
            text = extract_material_text(material_id, use_ocr=bool(options.get("ocr", False)), owner_id=owner_id)["text"]
    if not text or not text.strip():
        raise ValueError("No hay texto para adaptar. Verifique el PDF o active OCR para documentos escaneados.")
    if len(text) > 500_000:
        raise ValueError("El texto supera el límite de procesamiento (500 000 caracteres).")
    if adaptation == "summary":
        from ai.adaptations.summarizer import summarize_text
        result = summarize_text(text, int(options.get("max_sentences", 5)))
    elif adaptation == "easy_read":
        from ai.adaptations.easy_read import simplify_text
        result = simplify_text(text, int(options.get("max_words", 22)))
    elif adaptation == "quiz":
        from ai.adaptations.quiz_generator import generate_quiz
        result = generate_quiz(text, int(options.get("count", 5)))
    else:
        raise ValueError("Adaptación no reconocida. Opciones: summary, easy_read, quiz.")
    return {"material_id": material_id, "adaptation": adaptation, "result": result,
            "review_required": True, "generated_at": datetime.now(timezone.utc).isoformat()}
