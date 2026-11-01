"""Generación heurística de preguntas de comprensión, sin afirmar respuestas inventadas."""
import re

def generate_quiz(text: str, count: int = 5) -> list[dict]:
    if not text or not text.strip():
        return []
    count = max(1, min(int(count), 20))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 5]
    questions = []
    for i, sentence in enumerate(sentences[:count], 1):
        # Pregunta abierta basada en el contenido literal para evitar distractores falsos.
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
