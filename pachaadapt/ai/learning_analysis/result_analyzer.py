"""Análisis de resultados de estudiantes: validación de registros y métricas agregadas.

Funciones puras y deterministas. Los datos llegan de una fuente real (ver
``backend/app/services/report_service.py``); este módulo nunca genera ni completa datos.
Trabaja con AGREGADOS: no emite juicios sobre estudiantes individuales.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

MIN_RECORDS = 5          # registros válidos mínimos para analizar
MIN_STUDENTS = 3         # estudiantes distintos mínimos (privacidad y robustez)
MIN_PER_TOPIC = 3        # registros mínimos para reportar un tema
MIN_FOR_TREND = 6
TREND_STABLE_BAND = 5.0  # puntos porcentuales


@dataclass(frozen=True)
class LearningRecord:
    """Un resultado real de aprendizaje. ``student_ref`` es un identificador opaco
    (nunca nombre ni dato personal); solo sirve para contar estudiantes distintos."""
    student_ref: str
    topic: str
    score: float
    max_score: float
    recorded_at: str            # ISO 8601 (fecha o fecha-hora)
    group: Optional[str] = None


def parse_dt(value) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def is_valid(r: LearningRecord) -> bool:
    try:
        return (isinstance(r.student_ref, str) and r.student_ref != "" and isinstance(r.topic, str)
                and r.topic.strip() != "" and r.max_score > 0 and 0 <= r.score <= r.max_score
                and parse_dt(r.recorded_at) is not None)
    except (TypeError, AttributeError):
        return False


def pct(r: LearningRecord) -> float:
    return 100.0 * r.score / r.max_score


def compute(records: list[LearningRecord], threshold: float) -> dict:
    """Cálculo sobre registros ya validados (al menos uno)."""
    pcts = [pct(r) for r in records]
    below = sum(1 for p in pcts if p < threshold)
    dts = sorted(parse_dt(r.recorded_at) for r in records)
    by_topic: dict[str, list[float]] = {}
    for r in records:
        by_topic.setdefault(r.topic.strip(), []).append(pct(r))
    topics, thin = [], []
    for name, vals in sorted(by_topic.items()):
        if len(vals) < MIN_PER_TOPIC:
            thin.append({"topic": name, "records": len(vals)})
            continue
        topics.append({"topic": name, "records": len(vals), "mean_pct": round(statistics.fmean(vals), 1),
                       "share_below_threshold": round(sum(v < threshold for v in vals) / len(vals), 3)})
    trend = None
    if len(records) >= MIN_FOR_TREND and len(set(dts)) >= 2:
        ordered = [p for _, p in sorted(zip((parse_dt(r.recorded_at) for r in records), pcts), key=lambda x: x[0])]
        half = len(ordered) // 2
        first, second = statistics.fmean(ordered[:half]), statistics.fmean(ordered[half:])
        delta = round(second - first, 1)
        trend = {"first_half_mean_pct": round(first, 1), "second_half_mean_pct": round(second, 1),
                 "delta_pp": delta,
                 "direction": "estable" if abs(delta) < TREND_STABLE_BAND else ("mejora" if delta > 0 else "descenso")}
    return {
        "measured": {"records": len(records), "distinct_students": len({r.student_ref for r in records}),
                     "min_pct": round(min(pcts), 1), "max_pct": round(max(pcts), 1),
                     "records_below_threshold": below,
                     "date_range": [dts[0].date().isoformat(), dts[-1].date().isoformat()]},
        "calculated": {"mean_pct": round(statistics.fmean(pcts), 1), "median_pct": round(statistics.median(pcts), 1),
                       "share_below_threshold": round(below / len(pcts), 3), "trend": trend},
        "topics": topics, "topics_with_insufficient_data": thin,
    }
