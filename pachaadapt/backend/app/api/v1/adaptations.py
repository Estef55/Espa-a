"""API de adaptaciones accesibles (integrante 2). Prefijo efectivo: /api/v1/adaptations.

Solo usa APIRouter/Depends/HTTPException/BaseModel. Las imágenes viajan en base64 (JSON).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.v1._deps import principal
from app.core.identity import Principal
from app.services import adaptation_service as svc

router = APIRouter(prefix="/adaptations", tags=["adaptations"])


class VisualRequest(BaseModel):
    kind: str = "outline"          # outline | concept_map
    options: Optional[dict] = None


class AccessibleRequest(BaseModel):
    format: str = "bundle"         # plain | html | braille | bundle
    language: str = "es"


class AudioRequest(BaseModel):
    language: str = "es"
    max_chars: int = 400


class TranslateRequest(BaseModel):
    target: str
    source: str = "es"


class ImageRequest(BaseModel):
    image_base64: str
    language: str = "es"


class SubtitlesRequest(BaseModel):
    content: str


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:   # motor/servicio no disponible: se informa, no se simula
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.get("/capabilities")
def capabilities(user: Principal = Depends(principal)):
    return svc.capabilities()


@router.post("/materials/{material_id}/visual")
def visual(material_id: str, body: VisualRequest, user: Principal = Depends(principal)):
    return _call(svc.visual, material_id, user.user_id, body.kind, body.options)


@router.post("/materials/{material_id}/accessible")
def accessible(material_id: str, body: AccessibleRequest, user: Principal = Depends(principal)):
    return _call(svc.accessible, material_id, user.user_id, body.format, body.language)


@router.post("/materials/{material_id}/audio-script")
def audio_script(material_id: str, body: AudioRequest, user: Principal = Depends(principal)):
    return _call(svc.audio_script, material_id, user.user_id, body.language, body.max_chars)


@router.post("/materials/{material_id}/audio")
def audio(material_id: str, body: AudioRequest, user: Principal = Depends(principal)):
    return _call(svc.audio, material_id, user.user_id, body.language)


@router.post("/materials/{material_id}/translate")
def translate(material_id: str, body: TranslateRequest, user: Principal = Depends(principal)):
    return _call(svc.translate, material_id, user.user_id, body.target, body.source)


@router.post("/images/inspect")
def inspect_image(body: ImageRequest, user: Principal = Depends(principal)):
    return _call(svc.inspect_image, body.image_base64)


@router.post("/images/describe")
def describe_image(body: ImageRequest, user: Principal = Depends(principal)):
    return _call(svc.describe_image, body.image_base64, body.language)


@router.post("/subtitles")
def subtitles(body: SubtitlesRequest, user: Principal = Depends(principal)):
    return _call(svc.subtitles, body.content)
