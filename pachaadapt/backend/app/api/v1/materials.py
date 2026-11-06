"""API autenticada de carga, extracción y adaptación de materiales."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.v1._deps import principal
from app.core.identity import Principal
from ai.adaptations.errors import ProcessingError
from app.services import material_service as service

router = APIRouter(prefix="/materials", tags=["materials"])


class ExtractionRequest(BaseModel):
    ocr: bool = False


class AdaptationRequest(BaseModel):
    adaptation: str = Field(..., pattern="^(summary|easy_read|quiz|outline|image_notes|audio|translation)$")
    text: str | None = None
    options: dict = Field(default_factory=dict)


@router.post("", status_code=201)
async def upload_material(file: UploadFile = File(...), user: Principal = Depends(principal)):
    try:
        content = await file.read(service.MAX_UPLOAD_BYTES + 1)
        return service.save_material(file.filename or "material.pdf", content, owner_id=user.user_id,
                                     content_type=file.content_type or "application/octet-stream")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()


@router.get("")
def list_materials(user: Principal = Depends(principal)):
    """Materiales del docente (más recientes primero), con estado de procesamiento."""
    return service.list_materials(user.user_id)


@router.get("/capabilities")
def capabilities(user: Principal = Depends(principal)):
    """Qué puede hacer realmente este servidor (OCR, audio, traducción…) y qué no."""
    return service.capabilities()


@router.get("/{material_id}")
def material_details(material_id: str, user: Principal = Depends(principal)):
    try:
        return service.describe_material(material_id, owner_id=user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{material_id}/original")
def download_original(material_id: str, user: Principal = Depends(principal)):
    """Descarga el archivo original tal como se subió (nunca se modifica)."""
    try:
        path, filename, content_type = service.original_file(material_id, user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path, media_type=content_type, filename=filename)


@router.get("/{material_id}/text")
def organized_text(material_id: str, user: Principal = Depends(principal)):
    """Texto extraído y organizado (páginas, títulos, párrafos, listas, posibles tablas)."""
    try:
        return service.get_organized_text(material_id, user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{material_id}/extract")
def extract_material(material_id: str, request: ExtractionRequest = ExtractionRequest(),
                     user: Principal = Depends(principal)):
    try:
        return service.extract_material_text(material_id, use_ocr=request.ocr, owner_id=user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProcessingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


@router.post("/{material_id}/adapt")
def adapt_material(material_id: str, request: AdaptationRequest,
                   user: Principal = Depends(principal)):
    try:
        return service.adapt_material(material_id, request.adaptation, request.text,
                                      request.options, owner_id=user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProcessingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
