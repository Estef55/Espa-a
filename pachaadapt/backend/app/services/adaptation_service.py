"""Adaptaciones accesibles del integrante 2 (organizadores, Braille, HTML accesible, audio, traducción,
imágenes y subtítulos) y matriz de disponibilidad offline/online de cada recurso.

Reutiliza ``material_service`` (no lo modifica). Nada se simula: lo que depende de un motor o servicio
ausente responde con ``RuntimeError`` (la API lo traduce a 501).
"""
from __future__ import annotations

import base64
import binascii
import importlib.util
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from app.services import material_service as ms
from ai.adaptations import accessibility, visual_organizer
from ai.adaptations.audio_generator import audio_status, build_narration_script, synthesize_audio
from ai.adaptations.translator import translate_text, translation_status
from ai.document_processing import image_describer, media_transcriber
from ai.language_support.language_registry import REGISTRY

_translation = {"provider": None, "requires_connection": True}
_vision = {"provider": None, "requires_connection": True}


def set_translation_provider(provider: Optional[Callable], requires_connection: bool = True) -> None:
    """Punto de enchufe: función ``(texto, origen, destino) -> texto``."""
    _translation.update(provider=provider, requires_connection=requires_connection)


def set_vision_provider(provider: Optional[Callable], requires_connection: bool = True) -> None:
    """Punto de enchufe: función ``(bytes, idioma) -> texto``."""
    _vision.update(provider=provider, requires_connection=requires_connection)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def material_text(material_id: str, owner_id: str, ocr: bool = False) -> str:
    meta = ms.get_material(material_id, owner_id)
    text = meta.get("extracted_text")
    if text is None:
        text = ms.extract_material_text(material_id, use_ocr=ocr, owner_id=owner_id)["text"]
    if not text or not text.strip():
        raise ValueError("No hay texto para adaptar. Verifique el PDF o active OCR para documentos escaneados.")
    if len(text) > 500_000:
        raise ValueError("El texto supera el límite de procesamiento (500 000 caracteres).")
    return text


def _wrap(material_id: str, kind: str, result: Any, **extra) -> dict:
    return {"material_id": material_id, "adaptation": kind, "result": result, "review_required": True,
            "generated_at": _now(), **extra}


def visual(material_id: str, owner_id: str, kind: str = "outline", options: Optional[dict] = None) -> dict:
    o = options or {}
    text = material_text(material_id, owner_id)
    if kind == "outline":
        res = visual_organizer.build_outline(text, int(o.get("max_topics", 5)), int(o.get("max_points", 3)))
    elif kind == "concept_map":
        res = visual_organizer.build_concept_map(text, int(o.get("max_topics", 5)), int(o.get("max_points", 3)))
    else:
        raise ValueError("Tipo visual no reconocido. Opciones: outline, concept_map.")
    return _wrap(material_id, f"visual_{kind}", res, requires_server=True, requires_internet=False)


def accessible(material_id: str, owner_id: str, fmt: str = "bundle", language: str = "es") -> dict:
    text = material_text(material_id, owner_id)
    title = Path(ms.get_material(material_id, owner_id)["filename"]).stem
    builders = {"plain": lambda: accessibility.plain_text(text),
                "html": lambda: accessibility.to_accessible_html(text, title, language),
                "braille": lambda: accessibility.to_braille(text),
                "bundle": lambda: accessibility.accessible_bundle(text, title, language)}
    if fmt not in builders:
        raise ValueError("Formato no reconocido. Opciones: plain, html, braille, bundle.")
    return _wrap(material_id, f"accessible_{fmt}", builders[fmt](), requires_server=True, requires_internet=False)


def audio_script(material_id: str, owner_id: str, language: str = "es", max_chars: int = 400) -> dict:
    text = material_text(material_id, owner_id)
    return _wrap(material_id, "audio_script", build_narration_script(text, max_chars, language),
                 requires_server=True, requires_internet=False)


def audio(material_id: str, owner_id: str, language: str = "es") -> dict:
    """Síntesis local; devuelve el WAV en base64. RuntimeError (501) si no hay motor de voz."""
    text = material_text(material_id, owner_id)
    with tempfile.TemporaryDirectory() as tmp:
        info = synthesize_audio(text, Path(tmp) / "narracion.wav", language)
        data = Path(info["path"]).read_bytes()
    info.pop("path", None)
    return _wrap(material_id, "audio", {**info, "audio_base64": base64.b64encode(data).decode("ascii"),
                                       "mime_type": "audio/wav"}, requires_server=True, requires_internet=False)


def translate(material_id: str, owner_id: str, target: str, source: str = "es") -> dict:
    text = material_text(material_id, owner_id)
    res = translate_text(text, source, target, _translation["provider"],
                         requires_connection=_translation["requires_connection"])
    return _wrap(material_id, "translation", res, requires_server=True,
                 requires_internet=_translation["requires_connection"])


def _decode_b64(data: str) -> bytes:
    try:
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise ValueError("La imagen no es base64 válido.") from exc


def inspect_image(image_base64: str) -> dict:
    return image_describer.inspect_image(_decode_b64(image_base64))


def describe_image(image_base64: str, language: str = "es") -> dict:
    return image_describer.describe_image(_decode_b64(image_base64), language, _vision["provider"],
                                          requires_connection=_vision["requires_connection"])


def subtitles(content: str) -> dict:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Pegue el contenido de un archivo .srt o .vtt.")
    return media_transcriber.subtitles_to_text(content)


def _ocr_available() -> bool:
    return (importlib.util.find_spec("pytesseract") is not None and importlib.util.find_spec("pdf2image") is not None
            and shutil.which("tesseract") is not None and shutil.which("pdftoppm") is not None)


def capabilities() -> dict:
    """Qué recurso funciona sin conexión al servidor, cuál necesita servidor y cuál Internet."""
    aud, trans = audio_status(), media_transcriber.transcription_status()
    tr, vi = translation_status(_translation["provider"], _translation["requires_connection"]), {
        "available": _vision["provider"] is not None, "requires_connection": _vision["requires_connection"]}
    def item(id_, label, available, server, internet, note=""):
        return {"id": id_, "label": label, "available": bool(available), "requires_server": server,
                "requires_internet": internet, "works_offline_on_device": not server, "note": note}
    resources = [
        item("cached_materials", "Materiales ya descargados en el dispositivo", True, False, False,
             "Solo los que se descargaron antes con conexión al servidor."),
        item("saved_adaptations", "Adaptaciones guardadas en el dispositivo", True, False, False),
        item("activity_drafts", "Borradores de actividades en curso", True, False, False,
             "Se conservan localmente hasta que el servidor confirme la entrega."),
        item("upload_extract", "Subir y extraer texto (PDF/TXT)", True, True, False, "Requiere llegar al servidor de la escuela."),
        item("ocr", "OCR de PDF escaneados", _ocr_available(), True, False, "Requiere Tesseract y Poppler en el servidor."),
        item("summary_easy_quiz", "Resumen, lectura fácil y preguntas", True, True, False, "Métodos heurísticos locales."),
        item("visual", "Esquemas y mapas conceptuales", True, True, False, "Borrador heurístico."),
        item("accessible", "HTML accesible y Braille", True, True, False),
        item("audio_script", "Guion de narración", True, True, False),
        item("audio", "Audio sintetizado", aud["synthesis_available"], True, False, aud["reason"] or ""),
        item("subtitles", "Texto desde subtítulos SRT/VTT", True, True, False),
        item("media_transcription", "Transcripción de audio/video", trans["audio_transcription_available"], True, False, trans["reason"] or ""),
        item("translation", "Traducción automática", tr["available"], True, tr["requires_connection"], tr["reason"] or ""),
        item("image_description", "Descripción automática de imágenes", vi["available"], True, vi["requires_connection"],
             "" if vi["available"] else "No hay modelo de visión configurado."),
    ]
    return {"resources": resources, "languages": REGISTRY.describe(), "generated_at": _now()}
