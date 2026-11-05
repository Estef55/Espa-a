"""Texto de apoyo para contenido audiovisual.

- Subtítulos existentes (.srt / .vtt): se convierten en texto, localmente y sin Internet.
- Transcripción de audio/video: solo con el motor opcional ``faster-whisper`` y un modelo ya descargado.
  Sin él se lanza ``TranscriptionUnavailable``; no se simulan transcripciones.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Union

MAX_SUBTITLE_BYTES = 5 * 1024 * 1024
_TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
_ARROW = re.compile(r"^\s*(\S+)\s+-->\s+(\S+)")


class TranscriptionUnavailable(RuntimeError):
    """No hay motor de transcripción instalado."""


def _seconds(token: str) -> float:
    m = _TIME.fullmatch(token.strip())
    if not m:
        raise ValueError(f"Marca de tiempo inválida: {token!r}.")
    h, mi, s, ms = int(m.group(1) or 0), int(m.group(2)), int(m.group(3)), m.group(4).ljust(3, "0")
    return h * 3600 + mi * 60 + s + int(ms) / 1000


def parse_subtitles(content: Union[str, bytes]) -> list[dict]:
    """Interpreta SRT o WebVTT y devuelve ``[{start, end, text}]``."""
    if isinstance(content, bytes):
        if len(content) > MAX_SUBTITLE_BYTES:
            raise ValueError("El archivo de subtítulos supera 5 MB.")
        content = content.decode("utf-8-sig", errors="replace")
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cues, i = [], 0
    while i < len(lines):
        m = _ARROW.match(lines[i])
        if not m:
            i += 1
            continue
        start, end = _seconds(m.group(1)), _seconds(m.group(2))
        i += 1
        text_lines = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(re.sub(r"<[^>]+>", "", lines[i]).strip())
            i += 1
        text = " ".join(t for t in text_lines if t)
        if text:
            cues.append({"start": start, "end": end, "text": text})
    if not cues:
        raise ValueError("No se encontraron subtítulos válidos (formatos SRT o VTT).")
    return cues


def subtitles_to_text(content: Union[str, bytes]) -> dict:
    cues = parse_subtitles(content)
    text = "\n".join(c["text"] for c in cues)
    return {"text": text, "cues": len(cues), "duration_seconds": max(c["end"] for c in cues),
            "source": "subtitles", "requires_connection": False, "review_required": True}


def transcription_status() -> dict:
    try:
        import faster_whisper  # noqa: F401
        available = True
    except Exception:
        available = False
    return {"subtitles_supported": True, "audio_transcription_available": available, "requires_connection": False,
            "reason": None if available else "Transcribir audio/video requiere instalar 'faster-whisper' y un modelo local; "
                                            "sí se pueden convertir subtítulos SRT/VTT existentes."}


def transcribe_media(path: Union[str, Path], language: str = "es", model_size: str = "small") -> dict:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError("No se encontró el archivo de audio o video.")
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionUnavailable(transcription_status()["reason"]) from exc
    try:
        model = WhisperModel(model_size, local_files_only=True)
        segments, _info = model.transcribe(str(p), language=language or None)
        parts = [s.text.strip() for s in segments if s.text.strip()]
    except Exception as exc:
        raise TranscriptionUnavailable(f"No se pudo transcribir (¿modelo local no descargado?): {exc}") from exc
    return {"text": "\n".join(parts), "source": "speech_recognition", "language": language,
            "requires_connection": False, "review_required": True}
