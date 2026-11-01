"""Elaboración de informes académicos.

- Valida los criterios, ensambla el informe a partir de los módulos de análisis y
  lo exporta a Markdown. Cada afirmación está etiquetada: ``medido``, ``calculado`` o
  ``generado por IA`` (interpretación opcional, siempre separada de los datos).
- Con datos insuficientes devuelve ``insufficient_data`` y explica qué falta.
- Guarda criterios y fecha en el informe para poder reproducirlo.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from ai.errors import ProviderError, ProviderNotConfigured, ValidationError
from ai.learning_analysis import difficulty_detector, lesson_suggestions, result_analyzer as ra
from ai.storage import now_iso

DEFAULT_PASS_PCT = 55.0  # umbral por defecto; es un CRITERIO configurable, no una norma

INTERPRETATION_SYSTEM = (
    "Eres un asistente pedagógico. Recibes SOLO métricas agregadas de un grupo. Redacta una interpretación "
    "breve (máx. 150 palabras) y prudente. No inventes datos ni cifras que no estén en las métricas, no "
    "diagnostiques a estudiantes ni atribuyas condiciones personales, y menciona las limitaciones.")


def validate_criteria(criteria) -> dict:
    criteria = {} if criteria is None else criteria
    if not isinstance(criteria, dict):
        raise ValidationError("criteria debe ser un objeto.")
    allowed = {"pass_threshold_pct", "topic", "group", "date_from", "date_to", "include_ai_interpretation"}
    unknown = set(criteria) - allowed
    if unknown:
        raise ValidationError(f"Criterios desconocidos: {sorted(unknown)}", allowed_keys=sorted(allowed))
    out = {"pass_threshold_pct": DEFAULT_PASS_PCT, "topic": None, "group": None,
           "date_from": None, "date_to": None, "include_ai_interpretation": False}
    out.update(criteria)
    t = out["pass_threshold_pct"]
    if isinstance(t, bool) or not isinstance(t, (int, float)) or not 0 < t <= 100:
        raise ValidationError("pass_threshold_pct debe ser un número en (0, 100].")
    for k in ("topic", "group"):
        if out[k] is not None and (not isinstance(out[k], str) or not 0 < len(out[k]) <= 120):
            raise ValidationError(f"{k} inválido.")
    for k in ("date_from", "date_to"):
        if out[k] is not None and ra.parse_dt(out[k]) is None:
            raise ValidationError(f"{k} debe ser una fecha ISO 8601.")
    if not isinstance(out["include_ai_interpretation"], bool):
        raise ValidationError("include_ai_interpretation debe ser booleano.")
    return out


def interpret(provider, metrics: dict, observations: list[dict]) -> dict:
    """Interpretación opcional por IA. Recibe SOLO agregados (nunca identificadores de estudiantes)."""
    if provider is None:
        return {"status": "unavailable", "reason": "ai_provider_not_configured"}
    payload = json.dumps({"metrics": metrics, "observations": observations}, ensure_ascii=False)
    try:
        res = provider.generate([{"role": "system", "content": INTERPRETATION_SYSTEM},
                                 {"role": "user", "content": payload}], 400)
    except ProviderNotConfigured:
        return {"status": "unavailable", "reason": "ai_provider_not_configured"}
    except ProviderError as e:
        return {"status": "error", "reason": e.code}
    return {"status": "ok", "generated_by_ai": True, "provider": res.provider, "model": res.model, "text": res.text}


def build_report(criteria: dict, records_received: int, records_invalid: int,
                 valid: list, source_name: str, provider=None) -> dict:
    report = {"id": uuid.uuid4().hex, "created_at": now_iso(), "criteria": criteria,
              "data_summary": {"source": source_name, "records_received": records_received,
                               "records_used": len(valid), "records_invalid": records_invalid},
              "legend": {"medido": "valor observado en los datos", "calculado": "cálculo sobre los datos",
                         "generado por IA": "interpretación de un modelo; no es un dato"},
              "limitations": ["Solo se analizan agregados; no se evalúa a estudiantes individuales.",
                              "El umbral es un criterio configurable, no una norma oficial."]}
    students = len({r.student_ref for r in valid})
    missing = []
    if len(valid) < ra.MIN_RECORDS:
        missing.append(f"Se necesitan al menos {ra.MIN_RECORDS} registros válidos; hay {len(valid)}.")
    if students < ra.MIN_STUDENTS:
        missing.append(f"Se necesitan al menos {ra.MIN_STUDENTS} estudiantes distintos; hay {students}.")
    if missing:
        report.update(status="insufficient_data", missing=missing, metrics=None, observations=[],
                      recommendations=[], ai_interpretation=None)
        return report
    threshold = criteria["pass_threshold_pct"]
    metrics = ra.compute(valid, threshold)
    observations = difficulty_detector.detect(metrics, threshold)
    report.update(status="ok", metrics=metrics, observations=observations,
                  recommendations=lesson_suggestions.suggest(observations),
                  ai_interpretation=interpret(provider, metrics, observations)
                  if criteria["include_ai_interpretation"] else None)
    return report


def render_markdown(report: dict) -> str:
    L = ["# Informe de resultados de aprendizaje", "",
         f"- Generado: {report['created_at']}", f"- Estado: {report['status']}",
         f"- Criterios: `{json.dumps(report['criteria'], ensure_ascii=False)}`",
         f"- Registros usados: {report['data_summary']['records_used']} de "
         f"{report['data_summary']['records_received']}", ""]
    if report["status"] != "ok":
        L += ["## Datos insuficientes", *[f"- {m}" for m in report["missing"]]]
        return "\n".join(L) + "\n"
    m = report["metrics"]
    L += ["## Valores medidos", *[f"- {k}: {v}" for k, v in m["measured"].items()], "",
          "## Valores calculados", *[f"- {k}: {v}" for k, v in m["calculated"].items() if k != "trend"], "",
          "## Observaciones", *[f"- **{o['id']}** ({o['kind']}): {o['text']}" for o in report["observations"]], "",
          "## Recomendaciones (basadas en las observaciones indicadas)",
          *[f"- **{r['id']}** [{', '.join(r['based_on'])}]: {r['text']}" for r in report["recommendations"]], ""]
    ai = report.get("ai_interpretation")
    if ai:
        L += ["## Interpretación generada por IA (no es un dato)",
              ai.get("text") if ai["status"] == "ok" else f"No disponible: {ai['reason']}", ""]
    L += ["## Limitaciones", *[f"- {x}" for x in report["limitations"]]]
    return "\n".join(L) + "\n"
