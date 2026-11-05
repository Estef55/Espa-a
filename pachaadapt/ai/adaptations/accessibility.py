"""Salidas accesibles: HTML semántico, texto plano para lector de pantalla y Braille Unicode.

Todo se genera localmente (funciona sin Internet). El Braille es una transcripción
literaria de grado 1 (sin contracciones) para español: es un punto de partida que debe
revisar una persona con formación en Braille antes de embosar o entregar.
"""
from __future__ import annotations

import html
import re
import textwrap

_LETTERS = dict(zip("abcdefghijklmnopqrstuvwxyz",
                    "⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵"))
_SPANISH = {"ñ": "⠻", "á": "⠷", "é": "⠮", "í": "⠌", "ó": "⠬", "ú": "⠾", "ü": "⠳"}
_DIGITS = dict(zip("1234567890", "⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚"))
_PUNCT = {".": "⠲", ",": "⠂", ";": "⠆", ":": "⠒", "?": "⠢", "¿": "⠢", "!": "⠖", "¡": "⠖",
          "-": "⠤", "«": "⠦", "»": "⠴", '"': "⠦", "'": "⠄"}
_CAPITAL, _NUMBER = "⠠", "⠼"
MAX_CHARS = 200_000


def plain_text(text: str) -> str:
    """Texto limpio para lector de pantalla: sin marcas internas de página ni espacios repetidos."""
    if not text or not text.strip():
        raise ValueError("No hay texto para adaptar.")
    cleaned = re.sub(r"\[Página (\d+)\]", r"Página \1.", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def to_accessible_html(text: str, title: str = "Material adaptado", language: str = "es") -> str:
    """Documento HTML5 semántico: idioma declarado, encabezado, párrafos y alto contraste."""
    body = plain_text(text)
    if len(body) > MAX_CHARS:
        raise ValueError("El texto supera el límite para generar HTML accesible.")
    lang = re.sub(r"[^A-Za-z-]", "", language or "es")[:12] or "es"
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    items = "\n".join(f"    <p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)
    safe_title = html.escape(title.strip() or "Material adaptado")
    return (f'<!doctype html>\n<html lang="{lang}">\n<head>\n  <meta charset="utf-8">\n'
            f'  <meta name="viewport" content="width=device-width, initial-scale=1">\n  <title>{safe_title}</title>\n'
            "  <style>body{font-family:system-ui,sans-serif;font-size:1.2rem;line-height:1.7;max-width:46rem;margin:auto;"
            "padding:1rem;color:#111;background:#fff}h1{font-size:1.6rem}p{margin:0 0 1em}</style>\n</head>\n<body>\n"
            f"  <main>\n    <h1>{safe_title}</h1>\n{items}\n  </main>\n</body>\n</html>\n")


def to_braille(text: str, line_width: int = 32) -> dict:
    """Transcripción Braille Unicode (grado 1, español). Informa los caracteres sin equivalente."""
    source = plain_text(text)
    if len(source) > MAX_CHARS:
        raise ValueError("El texto supera el límite para transcribir a Braille.")
    line_width = max(10, min(int(line_width), 80))
    unmapped: set[str] = set()
    out: list[str] = []
    in_number = False
    for ch in source:
        low = ch.lower()
        if ch.isdigit() and ch in _DIGITS:
            if not in_number:
                out.append(_NUMBER)
                in_number = True
            out.append(_DIGITS[ch])
            continue
        if in_number and low in "abcdefghij":   # una letra a-j tras un número necesita separación
            out.append("⠐")
        in_number = False
        if low in _LETTERS or low in _SPANISH:
            if ch != low:
                out.append(_CAPITAL)
            out.append(_LETTERS.get(low) or _SPANISH[low])
        elif ch in _PUNCT:
            out.append(_PUNCT[ch])
        elif ch in " \t":
            out.append(" ")
        elif ch == "\n":
            out.append("\n")
        else:
            unmapped.add(ch)
    lines: list[str] = []
    for raw in "".join(out).split("\n"):
        lines.extend(textwrap.wrap(raw, width=line_width, break_long_words=False) or [""])
    return {"braille": "\n".join(lines).strip("\n"), "grade": 1, "language": "es", "line_width": line_width,
            "unmapped_characters": sorted(unmapped), "review_required": True,
            "note": "Transcripción literaria de grado 1 generada automáticamente; requiere revisión por una persona "
                    "con formación en Braille antes de embosar."}


def accessible_bundle(text: str, title: str = "Material adaptado", language: str = "es") -> dict:
    return {"plain_text": plain_text(text), "html": to_accessible_html(text, title, language),
            "braille": to_braille(text), "review_required": True}
