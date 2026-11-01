"""Endpoints de preferencias docentes. Prefijo: /api/v1/preferences."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from ai.assistant import preference_manager as prefs_mod
from app.api.v1._deps import principal, run
from app.core.identity import Principal
from app.services.container import get_container

router = APIRouter(prefix="/api/v1/preferences", tags=["preferences"])


class PreferencesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    education_level: Optional[str] = None
    complexity: Optional[str] = None
    length: Optional[str] = None
    tone: Optional[str] = None
    format: Optional[str] = None
    language: Optional[str] = None


@router.get("")
def get_preferences(p: Principal = Depends(principal)):
    return run(get_container().preferences.get, p.user_id)


@router.put("")
def put_preferences(body: PreferencesIn, p: Principal = Depends(principal)):
    return run(get_container().preferences.update, p.user_id, body.model_dump(exclude_unset=True))


@router.get("/adaptation-params")
def adaptation_params(p: Principal = Depends(principal)):
    """Parámetros PROPUESTOS para una solicitud de adaptación (contrato pendiente con el integrante 2)."""
    prefs = run(get_container().preferences.get, p.user_id)["preferences"]
    return {"proposed_params": prefs_mod.adaptation_params(prefs)}
