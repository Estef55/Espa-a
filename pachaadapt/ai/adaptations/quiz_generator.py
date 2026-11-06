"""Generación heurística de preguntas de comprensión, sin afirmar respuestas inventadas.

Las preguntas se reparten a lo largo del texto (no solo al inicio) y citan el fragmento literal;
no tienen clave de respuesta y requieren revisión docente.
"""
import re

PAGE_MARK = re.compile(r"^\s*\[Página \d+\]\s*$", re.M)


def generate_quiz(text: str, count: int = 5) -> list[dict]:
    if not text or not text.strip():
        return []
    count = max(1, min(int(count), 20))
    text = PAGE_MARK.sub("", text)
    sentences, seen = [], set()
    for s in re.split(r"(?<=[.!?])\s+|\n+", text):
        s = re.sub(r"\s+", " ", s).strip()
        if len(s.split()) >= 5 and s.endswith((".", "!", "?")) and s.lower() not in seen:
            seen.add(s.lower())
            sentences.append(s)
    if len(sentences) > count:  # reparte la selección a lo largo del documento
        step = len(sentences) / count
        sentences = [sentences[int(i * step)] for i in range(count)]
    questions = []
    for i, sentence in enumerate(sentences[:count], 1):
        words = sentence.split()
        topic = " ".join(words[:min(5, len(words))]).strip(" ,;:")
        questions.append({
            "id": i,
            "type": "open",
            "question": f"Explica con tus palabras la idea principal de este fragmento: «{sentence}»",
            "reference_fragment": sentence,
            "topic_hint": topic,
            "answer_key": None,
            "teacher_review_required": True
        })
    return questions
