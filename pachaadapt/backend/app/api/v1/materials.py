"""API de carga y extracción de materiales."""
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from app.services import material_service as service

router = APIRouter(prefix="/materials", tags=["materials"])

class ExtractionRequest(BaseModel):
    ocr: bool = False

class AdaptationRequest(BaseModel):
    adaptation: str = Field(..., pattern="^(summary|easy_read|quiz)$")
    text: str | None = None
    options: dict = Field(default_factory=dict)

@router.post("", status_code=201)
async def upload_material(file: UploadFile = File(...)):
    try:
        content = await file.read(service.MAX_UPLOAD_BYTES + 1)
        result = service.save_material(file.filename or "material.pdf", content, file.content_type or "application/octet-stream")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()

@router.get("/{material_id}")
def material_details(material_id: str):
    try:
        meta = service.get_material(material_id)
        return {k: v for k, v in meta.items() if k not in ("original_path", "text")}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.post("/{material_id}/extract")
def extract_material(material_id: str, request: ExtractionRequest = ExtractionRequest()):
    try:
        return service.extract_material_text(material_id, use_ocr=request.ocr)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

@router.post("/{material_id}/adapt")
def adapt_material(material_id: str, request: AdaptationRequest):
    try:
        return service.adapt_material(material_id, request.adaptation, request.text, request.options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
