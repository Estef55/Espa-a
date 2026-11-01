"""Detección de dificultades POR TEMA a partir de las métricas agregadas.

Produce observaciones con su evidencia. Cada observación se etiqueta ``medido`` o
``calculado`` y puede llevar una ``signal`` (low_overall, weak_topic, decline) que usa
``lesson_suggestions`` para proponer acciones. No se diagnostica a estudiantes.
"""
from __future__ import annotations


def detect(metrics: dict, threshold: float) -> list[dict]:
    obs: list[dict] = []

    def add(kind, text, evidence, signal=None, topic=None):
        obs.append({"id": f"O{len(obs) + 1}", "kind": kind, "text": text, "evidence": evidence,
                    "signal": signal, "topic": topic})

    calc = metrics["calculated"]
    mean = calc["mean_pct"]
    add("calculado", f"El promedio general es {mean} % (umbral del criterio: {threshold:g} %).",
        {"mean_pct": mean, "threshold_pct": threshold}, "low_overall" if mean < threshold else None)
    for t in metrics["topics"]:
        weak = t["mean_pct"] < threshold or t["share_below_threshold"] >= 0.5
        add("calculado",
            f"Tema «{t['topic']}»: promedio {t['mean_pct']} % en {t['records']} registros; "
            f"{round(t['share_below_threshold'] * 100)} % bajo el umbral.",
            t, "weak_topic" if weak else None, t["topic"])
    tr = calc["trend"]
    if tr:
        add("calculado", f"Tendencia por fecha: {tr['direction']} ({tr['delta_pp']:+g} puntos entre la "
                         "primera y la segunda mitad de los registros).", tr,
            "decline" if tr["direction"] == "descenso" else None)
    thin = metrics["topics_with_insufficient_data"]
    if thin:
        add("medido", "Hay temas con muy pocos registros para analizarlos: "
            + ", ".join(f"«{x['topic']}» ({x['records']})" for x in thin) + ".", thin)
    if not any(o["signal"] for o in obs):
        add("calculado", "No se detectaron temas ni tendencias por debajo de los criterios; "
                         "esto no descarta dificultades individuales.", {})
    return obs
