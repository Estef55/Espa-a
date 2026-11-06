"""Narración con un motor de voz LOCAL (espeak-ng o espeak), si está instalado en el servidor.

No usa servicios en línea. Si no hay motor, la adaptación NO está disponible y se informa;
nunca se devuelve un audio simulado. La voz de espeak es sintética y básica: es un apoyo de
lectura, no una grabación en quechua ni una locución pedagógica.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ai.adaptations.errors import AdaptationUnavailable

MAX_CHARS = 20_000
ENGINES = ("espeak-ng", "espeak")


def detect_engine() -> str | None:
    for name in ENGINES:
        path = shutil.which(name)
        if path:
            return path
    return None


def audio_status() -> dict:
    engine = detect_engine()
    if engine:
        return {"available": True, "engine": Path(engine).name, "reason": None, "max_chars": MAX_CHARS}
    return {"available": False, "engine": None, "max_chars": MAX_CHARS,
            "reason": "No hay un motor de voz local instalado en el servidor (espeak-ng). Instálalo para generar audio; no se usa ningún servicio en línea."}


def synthesize(text: str, out_path: Path, lang: str = "es", timeout: int = 180) -> dict:
    engine = detect_engine()
    if engine is None:
        raise AdaptationUnavailable(audio_status()["reason"])
    text = (text or "").strip()
    if not text:
        raise ValueError("No hay texto para narrar.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"El texto supera {MAX_CHARS} caracteres. Genera el audio de un resumen o de un fragmento.")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as fh:
        fh.write(text)
        src = fh.name
    try:
        proc = subprocess.run([engine, "-v", lang if lang in ("es", "en") else "es", "-w", str(out_path), "-f", src],
                              capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        out_path.unlink(missing_ok=True)
        raise ValueError("El motor de voz tardó demasiado; prueba con un texto más corto.") from exc
    finally:
        Path(src).unlink(missing_ok=True)
    if proc.returncode != 0 or not out_path.is_file() or out_path.stat().st_size == 0:
        out_path.unlink(missing_ok=True)
        raise ValueError("El motor de voz no pudo generar el audio: " + proc.stderr.decode("utf-8", "replace")[:200])
    return {"engine": Path(engine).name, "bytes": out_path.stat().st_size, "narrated_chars": len(text), "format": "wav", "language": lang}
