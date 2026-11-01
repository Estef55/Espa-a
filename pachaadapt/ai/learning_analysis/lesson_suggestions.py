"""Sugerencias pedagógicas para próximas sesiones.

Reglas explícitas (sin IA). Cada recomendación enlaza (``based_on``) las observaciones
que la justifican, de modo que siempre se pueda ver en qué dato se apoya.
"""
from __future__ import annotations


def suggest(observations: list[dict]) -> list[dict]:
    recs: list[dict] = []

    def add(based_on, text):
        recs.append({"id": f"R{len(recs) + 1}", "origin": "regla", "based_on": based_on, "text": text})

    for o in observations:
        sig = o.get("signal")
        if sig == "low_overall":
            add([o["id"]], "El promedio general queda bajo el umbral: considere revisar el ritmo y los "
                           "apoyos de las próximas sesiones antes de avanzar a contenidos nuevos.")
        elif sig == "weak_topic":
            add([o["id"]], f"Considere reforzar el tema «{o['topic']}» con ejemplos adicionales y una "
                           "actividad de práctica; vuelva a medir después para comprobar el efecto.")
        elif sig == "decline":
            add([o["id"]], "Los resultados recientes son menores que los anteriores: considere revisar "
                           "qué cambió en las últimas sesiones o evaluaciones.")
    return recs
