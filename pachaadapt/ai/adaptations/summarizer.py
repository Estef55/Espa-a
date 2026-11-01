"""Resumen extractivo local, determinista y sin servicios externos."""
import re
from collections import Counter

def summarize_text(text: str, max_sentences: int = 5) -> str:
    if not text or not text.strip():
        return ""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 20]
    if len(sentences) <= max_sentences:
        return " ".join(sentences or [text.strip()])
    words = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
    stop = set("para como donde desde hasta entre sobre este esta estos estas una uno unos unas los las del al por con sin que se su sus y o de la el en es son fue".split())
    freq = Counter(w for w in words if len(w) > 3 and w not in stop)
    scored = []
    for i, sentence in enumerate(sentences):
        tokens = [w for w in re.findall(r"\w+", sentence.lower(), flags=re.UNICODE) if w in freq]
        score = sum(freq[w] for w in tokens) / max(len(tokens), 1)
        scored.append((score, i, sentence))
    chosen = sorted(sorted(scored, reverse=True)[:max(1, max_sentences)], key=lambda x: x[1])
    return " ".join(item[2] for item in chosen)
