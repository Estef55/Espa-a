"""Esquema por reglas: títulos → ideas clave literales + términos frecuentes.

Es un ESQUEMA EXTRACTIVO (usa frases del propio documento), no un mapa conceptual ni
un diagrama generado: no establece relaciones entre conceptos ni inventa contenido.
"""
from __future__ import annotations

import re
from collections import Counter

STOP = set("para como donde desde hasta entre sobre este esta estos estas esto una uno unos unas los las del al por con sin que se su sus y o de la el en es son fue ser también cada muy más pero porque cuando mientras así sino ya lo le les".split())
_BULLET = re.compile(r"^\s*(?:[-•*·▪●]|\d{1,3}[.)])\s+")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip().split()) >= 4]


def _terms(text: str, limit: int = 8) -> list[str]:
    words = [w for w in re.findall(r"[^\W\d_]{5,}", text.lower()) if w not in STOP]
    return [w for w, n in Counter(words).most_common(limit * 2) if n >= 2][:limit]


def build_outline(organized: dict, points_per_section: int = 3) -> dict:
    from ai.document_processing.text_organizer import flatten_table
    blocks = [b for b in organized.get("blocks", []) if b["type"] != "notice"]
    all_text = organized.get("body_text") or " ".join(b["text"] for b in blocks if b["type"] != "table_like")
    freq = Counter(w for w in re.findall(r"\w+", all_text.lower()) if len(w) > 3 and w not in STOP)

    def score(sentence: str) -> float:
        toks = [w for w in re.findall(r"\w+", sentence.lower()) if w in freq]
        return sum(freq[w] for w in toks) / max(len(toks), 1)

    sections, warnings = [], []
    has_headings = any(b["type"] == "heading" for b in blocks)
    cur, para_count = None, 0
    for b in blocks:
        if b["type"] == "heading":
            cur = {"heading": b["text"], "page": b.get("page"), "text": [], "items": []}
            sections.append(cur); para_count = 0
            continue
        if cur is None or (not has_headings and para_count >= 3):
            cur = {"heading": None, "page": b.get("page"), "text": [], "items": []}
            sections.append(cur); para_count = 0
        if b["type"] == "table_like":
            cur["items"] += flatten_table(b["text"]).split("\n")[:12]
        elif b["type"] == "list":
            cur["items"] += [_BULLET.sub("", l).strip() for l in b["text"].split("\n")][:8]
        else:
            cur["text"].append(b["text"])
        para_count += 1
    out_sections = []
    for i, s in enumerate(sections, 1):
        sents = _sentences("\n".join(s["text"]))
        if len(sents) > points_per_section:
            top = sorted(sorted(enumerate(sents), key=lambda x: -score(x[1]))[:points_per_section])
            sents = [x[1] for x in top]
        sents = sents + s["items"]
        if not sents and not s["heading"]:
            continue
        out_sections.append({"heading": s["heading"] or f"Parte {i}", "page": s["page"], "points": sents})
    if not has_headings and out_sections:
        warnings.append("No se detectaron títulos en el documento; las secciones son grupos de párrafos consecutivos.")
    if any(not s["points"] for s in out_sections):
        warnings.append("Algunas secciones no tienen frases completas para resumir; solo se muestra su título.")
    title = next((b["text"] for b in blocks[:1] if b["type"] == "heading"), None)
    return {"title": title, "sections": out_sections, "key_terms": _terms(all_text), "method": "extractive_rules",
            "warnings": warnings, "is_concept_map": False}


def outline_to_text(outline: dict) -> str:
    lines = []
    first = outline["sections"][0]["heading"] if outline["sections"] else None
    if outline.get("title") and outline["title"] != first:
        lines += [f"# {outline['title']}", ""]
    for s in outline["sections"]:
        lines.append(f"## {s['heading']}" + (f" (página {s['page']})" if s.get("page") else ""))
        lines += [f"- {p}" for p in s["points"]]
        lines.append("")
    if outline.get("key_terms"):
        lines.append("Términos que se repiten: " + ", ".join(outline["key_terms"]))
    return "\n".join(lines).strip()
