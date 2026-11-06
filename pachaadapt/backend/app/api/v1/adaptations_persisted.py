"""Adaptaciones persistidas de un material: consulta, revisión docente, vínculos, exportación y audio.

La generación sigue en ``POST /materials/{id}/adapt`` (materials.py). Solo docentes, y solo sobre
materiales propios (otro docente recibe 404).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from app.api.v1._deps import principal
from app.core.identity import Principal
from app.services import material_service as service

router = APIRouter(prefix="/api/v1/materials", tags=["adaptations"])


class ReviewRequest(BaseModel):
    approved: bool = True


class LinkRequest(BaseModel):
    target_type: str = Field(..., pattern="^(document|assignment)$")
    target_id: str = Field(..., min_length=1, max_length=128)


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.get("/{material_id}/adaptations")
def list_adaptations(material_id: str, kind: str | None = Query(default=None), user: Principal = Depends(principal)):
    return _call(service.list_adaptations, material_id, user.user_id, kind)


@router.get("/{material_id}/adaptations/{adaptation_id}")
def get_adaptation(material_id: str, adaptation_id: str, user: Principal = Depends(principal)):
    return _call(service.get_adaptation, material_id, adaptation_id, user.user_id)


@router.post("/{material_id}/adaptations/{adaptation_id}/review")
def review_adaptation(material_id: str, adaptation_id: str, body: ReviewRequest, user: Principal = Depends(principal)):
    return _call(service.review_adaptation, material_id, adaptation_id, body.approved, user.user_id)


@router.post("/{material_id}/adaptations/{adaptation_id}/links", status_code=201)
def link_adaptation(material_id: str, adaptation_id: str, body: LinkRequest, user: Principal = Depends(principal)):
    return _call(service.link_adaptation, material_id, adaptation_id, body.target_type, body.target_id, user.user_id)


@router.get("/{material_id}/adaptations/{adaptation_id}/export")
def export_adaptation(material_id: str, adaptation_id: str, format: str = Query(default="html"), user: Principal = Depends(principal)):
    data, media_type, filename = _call(service.export_adaptation, material_id, adaptation_id, format, user.user_id)
    return Response(content=data, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{material_id}/adaptations/{adaptation_id}/audio")
def adaptation_audio(material_id: str, adaptation_id: str, user: Principal = Depends(principal)):
    path = _call(service.adaptation_audio_file, material_id, adaptation_id, user.user_id)
    return FileResponse(path, media_type="audio/wav", filename=path.name)
