"""Narración y audio.

Dos niveles, para no prometer más de lo que existe:
1. ``build_narration_script``: guion de lectura (fragmentos, pausas, SSML). Siempre disponible y local.
2. ``synthesize_audio``: genera un archivo de audio SOLO si hay un motor de voz local instalado
   (``espeak-ng``/``espeak`` o ``pyttsx3``). Sin motor lanza ``AudioEngineUnavailable``; no se simulan audios.
La calidad y la disponibilidad de voces en quechua dependen del motor instalado y deben verificarse.
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

MAX_SYNTH_CHARS = 50_000
_ENGINES = ("espeak-ng", "espeak")


class AudioEngineUnavailable(RuntimeError):
    """No hay un motor de síntesis de voz local instalado."""


def _clean(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("No hay texto para narrar.")
    cleaned = re.sub(r"\[Página (\d+)\]", r"Página \1.", text)
    return re.sub(r"[ \t]+", " ", cleaned).strip()


def build_narration_script(text: str, max_chars: int = 400, language: str = "es") -> dict:
    cleaned = _clean(text)
    max_chars = max(80, min(int(max_chars), 2000))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", cleaned) if s.strip()]
    chunks, current = [], ""
    for sentence in sentences:
        while len(sentence) > max_chars:                       # frase muy larga: se corta en un espacio
            cut = sentence.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    lang = re.sub(r"[^A-Za-z-]", "", language or "es") or "es"
    ssml = (f'<speak version="1.1" xml:lang="{lang}">' +
            "".join(f'<p>{html.escape(c)}</p><break time="600ms"/>' for c in chunks) + "</speak>")
    words = len(cleaned.split())
    return {"language": lang, "chunks": chunks, "ssml": ssml, "words": words,
            "estimated_minutes": round(words / 140, 1), "review_required": True}


def available_engine() -> Optional[str]:
    for name in _ENGINES:
        if shutil.which(name):
            return name
    try:
        import pyttsx3  # noqa: F401
        return "pyttsx3"
    except Exception:
        return None


def audio_status() -> dict:
    engine = available_engine()
    return {"script_available": True, "synthesis_available": engine is not None, "engine": engine,
            "requires_connection": False,
            "reason": None if engine else "No hay motor de voz local (espeak-ng o pyttsx3); solo se genera el guion de lectura."}


def synthesize_audio(text: str, out_path, language: str = "es", timeout: int = 120) -> dict:
    cleaned = _clean(text)
    if len(cleaned) > MAX_SYNTH_CHARS:
        raise ValueError(f"El texto supera el límite de síntesis ({MAX_SYNTH_CHARS} caracteres).")
    engine = available_engine()
    if engine is None:
        raise AudioEngineUnavailable("No hay motor de voz local instalado (espeak-ng, espeak o pyttsx3). "
                                     "No se genera audio simulado.")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lang = re.sub(r"[^A-Za-z-]", "", language or "es") or "es"
    if engine in _ENGINES:
        cmd = [engine, "-v", lang, "-w", str(out), "--", cleaned]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise AudioEngineUnavailable("La síntesis de voz excedió el tiempo permitido.") from exc
        if proc.returncode != 0 or not out.is_file():
            raise AudioEngineUnavailable("El motor de voz no pudo generar el audio (¿idioma sin voz instalada?).")
    else:
        import pyttsx3
        try:
            tts = pyttsx3.init()
            tts.save_to_file(cleaned, str(out))
            tts.runAndWait()
        except Exception as exc:
            raise AudioEngineUnavailable(f"El motor de voz falló: {exc}") from exc
        if not out.is_file():
            raise AudioEngineUnavailable("El motor de voz no generó el archivo.")
    return {"path": str(out), "engine": engine, "language": lang, "bytes": out.stat().st_size,
            "format": "wav", "review_required": True}
