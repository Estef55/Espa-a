"""Esquemas, organizadores gráficos y mapas conceptuales a partir de texto.

Método heurístico, local y determinista (sin IA generativa): detecta términos
frecuentes, agrupa las oraciones que los mencionan y construye un esquema.
Es un BORRADOR para que el docente corrija; no interpreta relaciones semánticas.
"""
from __future__ import annotations

import re
from collections import Counter

_STOP = set("""para como donde desde hasta entre sobre este esta estos estas esto una uno unos unas los las del al por con sin que
se su sus de la el en es son fue ser han hay muy mas más pero también cuando porque cada todo todos otra otros otras
tiene tienen puede pueden además así aunque mientras según""".split())


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.split()) >= 4]


def _terms(text: str, limit: int) -> list[str]:
    words = re.findall(r"[^\W\d_]{4,}", text.lower(), flags=re.UNICODE)
    freq = Counter(w for w in words if w not in _STOP)
    return [w for w, n in freq.most_common(limit) if n >= 2] or [w for w, _ in freq.most_common(limit)]


def _mm(label: str) -> str:
    return re.sub(r"[\"\[\](){}<>]", " ", label).strip()[:60]


def build_outline(text: str, max_topics: int = 5, max_points: int = 3) -> dict:
    if not text or not text.strip():
        raise ValueError("No hay texto para organizar.")
    max_topics, max_points = max(1, min(int(max_topics), 10)), max(1, min(int(max_points), 6))
    sentences = _sentences(text)
    if not sentences:
        raise ValueError("El texto es demasiado breve para generar un esquema.")
    topics, used = [], set()
    for term in _terms(text, max_topics * 2):
        points = [s for i, s in enumerate(sentences) if i not in used and term in s.lower()][:max_points]
        if not points:
            continue
        used.update(i for i, s in enumerate(sentences) if s in points)
        topics.append({"topic": term, "points": points})
        if len(topics) == max_topics:
            break
    if not topics:  # texto sin términos repetidos: se conservan las primeras oraciones
        topics = [{"topic": "ideas principales", "points": sentences[:max_points * max_topics]}]
    title = _mm(sentences[0])[:60]
    markdown = [f"# {title}"] + [f"\n## {t['topic'].capitalize()}\n" + "\n".join(f"- {p}" for p in t["points"]) for t in topics]
    return {"title": title, "topics": topics, "markdown": "\n".join(markdown), "review_required": True,
            "method": "heuristic_keyword_grouping"}


def build_concept_map(text: str, max_topics: int = 5, max_points: int = 3) -> dict:
    outline = build_outline(text, max_topics, max_points)
    root = "root"
    nodes = [{"id": root, "label": _mm(outline["title"])}]
    edges, lines = [], ["graph TD", f'  {root}["{_mm(outline["title"])}"]']
    for i, topic in enumerate(outline["topics"], 1):
        tid = f"t{i}"
        nodes.append({"id": tid, "label": topic["topic"]})
        edges.append({"from": root, "to": tid, "label": "incluye"})
        lines += [f'  {tid}["{_mm(topic["topic"])}"]', f"  {root} --> {tid}"]
        for j, point in enumerate(topic["points"], 1):
            pid = f"{tid}p{j}"
            nodes.append({"id": pid, "label": _mm(point)})
            edges.append({"from": tid, "to": pid, "label": "detalle"})
            lines += [f'  {pid}["{_mm(point)}"]', f"  {tid} --> {pid}"]
    return {"nodes": nodes, "edges": edges, "mermaid": "\n".join(lines), "outline_markdown": outline["markdown"],
            "review_required": True, "method": outline["method"],
            "note": "Las relaciones son genéricas («incluye», «detalle»); el docente debe ajustarlas."}
