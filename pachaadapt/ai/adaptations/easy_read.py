"""Transformación conservadora a lectura fácil; requiere revisión docente."""
import re

def simplify_text(text: str, max_words: int = 22) -> str:
    if not text or not text.strip():
        return ""
    # Divide por frases y, si son largas, por conectores/puntuación suave.
    parts = re.split(r"(?<=[.!?;:])\\s+|\\n+", text.strip())
    output = []
    for part in parts:
        part = re.sub(r"\\s+", " ", part).strip()
        if not part:
            continue
        words = part.split()
        while len(words) > max_words:
            cut = max_words
            for j in range(max_words, max(5, max_words // 2), -1):
                if words[j-1].endswith((",", " y", " pero")):
                    cut = j
                    break
            output.append(" ".join(words[:cut]).strip() + ".")
            words = words[cut:]
        if words:
            output.append(" ".join(words))
    return "\\n".join(output)
