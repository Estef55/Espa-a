"""Generación de informes: obtiene resultados reales por el puerto ``LearningDataSource``,
aplica los filtros, delega el análisis en ``ai/learning_analysis`` y persiste el informe
(criterios y fecha incluidos).

Sin fuente de datos conectada -> 503 controlado. Este servicio no genera ni simula registros.
"""
from __future__ import annotations

import json
from datetime import timedelta, timezone
from typing import Optional, Protocol, Sequence

from app.core import paths  # noqa: F401  (habilita "import ai")
from ai.errors import DataSourceNotConfigured, NotFound
from ai.learning_analysis import academic_report as ar
from ai.learning_analysis import result_analyzer as ra
from ai.learning_analysis.result_analyzer import LearningRecord
from ai.storage import Database


class LearningDataSource(Protocol):
    def fetch_records(self, teacher_id: str, filters: dict) -> Sequence[LearningRecord]:
        """Devuelve SOLO resultados autorizados, confirmados y con calificación real; student_ref debe ser opaco."""


def _utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class ReportService:
    def __init__(self, db: Database, data_source: Optional[LearningDataSource] = None, provider=None):
        self.db, self.data_source, self.provider = db, data_source, provider

    def set_data_source(self, ds) -> None:
        self.data_source = ds

    def set_provider(self, provider) -> None:
        self.provider = provider

    def generate(self, teacher_id: str, criteria=None) -> dict:
        crit = ar.validate_criteria(criteria)
        if self.data_source is None:
            raise DataSourceNotConfigured("La fuente de resultados de aprendizaje no está conectada.",
                                          pending="LearningDataSource.fetch_records")
        filters = {k: crit[k] for k in ("topic", "group", "date_from", "date_to") if crit[k] is not None}
        received = list(self.data_source.fetch_records(teacher_id, filters))
        valid = [r for r in received if ra.is_valid(r)]
        invalid = len(received) - len(valid)
        if crit["topic"]:
            valid = [r for r in valid if r.topic.strip() == crit["topic"]]
        if crit["group"]:
            valid = [r for r in valid if r.group == crit["group"]]
        if crit["date_from"]:
            lo = _utc(ra.parse_dt(crit["date_from"]))
            valid = [r for r in valid if _utc(ra.parse_dt(r.recorded_at)) >= lo]
        if crit["date_to"]:
            end_value = crit["date_to"]
            hi = _utc(ra.parse_dt(end_value))
            if len(end_value) == 10:  # date-only filters include that whole calendar day
                hi += timedelta(days=1)
                valid = [r for r in valid if _utc(ra.parse_dt(r.recorded_at)) < hi]
            else:
                valid = [r for r in valid if _utc(ra.parse_dt(r.recorded_at)) <= hi]
        report = ar.build_report(crit, len(received), invalid, valid,
                                 type(self.data_source).__name__, self.provider)
        with self.db.transaction() as conn:
            conn.execute("INSERT INTO i3_reports(id, teacher_id, created_at, status, criteria_json, report_json) "
                         "VALUES (?,?,?,?,?,?)",
                         (report["id"], teacher_id, report["created_at"], report["status"],
                          json.dumps(crit, ensure_ascii=False), json.dumps(report, ensure_ascii=False)))
        return report

    def get(self, teacher_id: str, report_id: str) -> dict:
        with self.db.read() as conn:
            row = conn.execute("SELECT report_json FROM i3_reports WHERE id=? AND teacher_id=?",
                               (report_id, teacher_id)).fetchone()
        if row is None:
            raise NotFound("Informe no encontrado.")
        return json.loads(row["report_json"])

    def list(self, teacher_id: str) -> list[dict]:
        with self.db.read() as conn:
            rows = conn.execute("SELECT id, created_at, status, criteria_json FROM i3_reports "
                                "WHERE teacher_id=? ORDER BY created_at DESC", (teacher_id,)).fetchall()
        return [{"id": r["id"], "created_at": r["created_at"], "status": r["status"],
                 "criteria": json.loads(r["criteria_json"])} for r in rows]
