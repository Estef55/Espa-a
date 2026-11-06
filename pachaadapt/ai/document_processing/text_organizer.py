"""Organiza el texto extraído en páginas, títulos, párrafos, listas y posibles tablas.

Reglas locales y deterministas: no inventa contenido, solo reordena y etiqueta lo que
ya está en el documento. Los títulos y las tablas se detectan por heurística, así que
el resultado siempre debe revisarse (se informa en ``warnings``).
"""
from __future__ import annotations

import re

PAGE_RE = re.compile(r"^\[Página (\d+)\]\s*$")
LIST_RE = re.compile(r"^\s*(?:[-•*·▪●]|\d{1,3}[.)])\s+\S")
BULLET_RE = re.compile(r"^\s*(?:[-•*·▪●]|\d{1,3}[.)])\s+")
TABLE_GAP_RE = re.compile(r"\S(?: {3,}|\t)\S")
NOTICE_RE = re.compile(r"^MATERIAL DE DEMOSTRACIÓN\b")  # aviso del material de demostración: no es contenido a adaptar
END_PUNCT = (".", "!", "?", ";", ",", ":", "…")


def _is_table_line(line: str) -> bool:
    return line.count("|") >= 2 or len(TABLE_GAP_RE.findall(line)) >= 1


def _heading_like(line: str, prev_ended: bool, next_line: str | None) -> bool:
    text = line.strip()
    words = text.split()
    if not text or len(text) > 70 or len(words) > 9 or LIST_RE.match(line) or _is_table_line(line):
        return False
    if text.endswith(END_PUNCT[:-2]) or text.endswith(","):
        return False
    if text.endswith(":") and len(words) <= 9:
        return True
    if next_line is None or not next_line.strip():
        return prev_ended and (text.isupper() or text[0].isupper() and len(words) <= 6)
    nxt = next_line.strip()
    starts_upper = nxt[0].isupper() or nxt[0].isdigit() or LIST_RE.match(next_line) is not None
    numbered = re.match(r"^\d{1,2}(?:\.\d{1,2})*[.)]?\s+\S", text) is not None
    return prev_ended and starts_upper and (text.isupper() or numbered or (text[0].isupper() and len(words) <= 6))


def flatten_table(text: str) -> str:
    """Una fila por línea, columnas unidas con « — » (no pierde ni inventa datos)."""
    rows = []
    for line in text.split("\n"):
        cells = [c.strip() for c in re.split(r" {3,}|\t|\|", line) if c.strip()]
        if cells:
            rows.append(" — ".join(cells))
    return "\n".join(rows)


def _body_text(b: dict) -> str:
    if b["type"] == "list":
        return "\n".join(BULLET_RE.sub("", l).rstrip(".;,") + "." for l in b["text"].split("\n"))
    return b["text"]


def split_pages(raw: str) -> list[tuple[int | None, str]]:
    """Separa el texto por los marcadores «[Página N]» que escribe el extractor."""
    pages: list[tuple[int | None, list[str]]] = []
    for line in (raw or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        m = PAGE_RE.match(line.strip())
        if m:
            pages.append((int(m.group(1)), []))
        else:
            if not pages:
                pages.append((None, []))
            pages[-1][1].append(line)
    return [(n, "\n".join(lines).strip("\n")) for n, lines in pages if "".join(lines).strip()]


def organize_text(raw: str) -> dict:
    blocks: list[dict] = []
    page_stats: list[dict] = []
    for page, body in split_pages(raw):
        lines = body.split("\n")
        buf: list[str] = []
        prev_ended = True

        def flush():
            nonlocal buf
            if buf:
                text = re.sub(r"\s+", " ", " ".join(s.strip() for s in buf)).strip()
                blocks.append({"type": "notice" if NOTICE_RE.match(text) else "paragraph", "text": text, "page": page})
                buf = []

        i = 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                flush(); prev_ended = True; i += 1; continue
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if _is_table_line(line):
                flush()
                rows = [line.rstrip()]
                while i + 1 < len(lines) and _is_table_line(lines[i + 1]):
                    i += 1; rows.append(lines[i].rstrip())
                if len(rows) >= 2:
                    blocks.append({"type": "table_like", "text": "\n".join(rows), "page": page})
                else:
                    buf.append(rows[0])
                prev_ended = True
            elif LIST_RE.match(line):
                flush()
                items = [line.strip()]
                while i + 1 < len(lines) and LIST_RE.match(lines[i + 1]):
                    i += 1; items.append(lines[i].strip())
                blocks.append({"type": "list", "text": "\n".join(items), "page": page})
                prev_ended = True
            elif _heading_like(line, prev_ended, nxt):
                flush()
                blocks.append({"type": "heading", "text": line.strip().rstrip(":").strip(), "page": page})
                prev_ended = True
            else:
                buf.append(line)
                prev_ended = line.rstrip().endswith((".", "!", "?", ":", "…"))
            i += 1
        flush()
        page_stats.append({"page": page, "characters": len(body)})
    shown = [b for b in blocks if b["type"] != "notice"]
    clean = "\n\n".join(b["text"] for b in shown)
    # Resumen y preguntas usan solo párrafos y listas; las tablas se aplanan para lectura fácil y esquema.
    body_only = "\n\n".join(_body_text(b) for b in blocks if b["type"] in ("paragraph", "list"))
    adapt_text = "\n\n".join(flatten_table(b["text"]) if b["type"] == "table_like" else b["text"] for b in shown)
    warnings: list[str] = []
    if any(b["type"] == "table_like" for b in blocks):
        warnings.append("Se detectaron posibles tablas: el texto extraído puede perder filas y columnas. Revisa esas partes contra el original.")
    if not any(b["type"] == "heading" for b in blocks) and shown:
        warnings.append("No se detectaron títulos; el orden del texto sigue el del documento.")
    return {
        "clean_text": clean, "body_text": body_only, "adapt_text": adapt_text, "blocks": blocks, "pages": page_stats,
        "stats": {"pages": len([p for p in page_stats if p["page"] is not None]) or (1 if blocks else 0),
                  "words": len(clean.split()), "characters": len(clean),
                  "headings": sum(b["type"] == "heading" for b in blocks),
                  "tables": sum(b["type"] == "table_like" for b in blocks)},
        "warnings": warnings, "method": "heuristic_layout_rules",
    }
