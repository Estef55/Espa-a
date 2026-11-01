"""Endpoints de informes de resultados de aprendizaje. Prefijo: /api/v1/reports."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict

from ai.learning_analysis.academic_report import render_markdown
from app.api.v1._deps import principal, run
from app.core.identity import Principal
from app.services.container import get_container

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pass_threshold_pct: Optional[float] = None
    topic: Optional[str] = None
    group: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    include_ai_interpretation: Optional[bool] = None


@router.post("", status_code=201)
def create_report(body: ReportIn, p: Principal = Depends(principal)):
    """Genera un informe (503 si no hay fuente de resultados; ``insufficient_data`` si faltan datos)."""
    return run(get_container().reports.generate, p.user_id, body.model_dump(exclude_none=True))


@router.get("")
def list_reports(p: Principal = Depends(principal)):
    return run(get_container().reports.list, p.user_id)


@router.get("/{report_id}")
def get_report(report_id: str, p: Principal = Depends(principal)):
    return run(get_container().reports.get, p.user_id, report_id)


@router.get("/{report_id}/markdown", response_class=PlainTextResponse)
def report_markdown(report_id: str, p: Principal = Depends(principal)):
    return render_markdown(run(get_container().reports.get, p.user_id, report_id))
