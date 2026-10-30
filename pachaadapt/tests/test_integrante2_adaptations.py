import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai.adaptations.summarizer import summarize_text
from ai.adaptations.easy_read import simplify_text
from ai.adaptations.quiz_generator import generate_quiz

class AdaptationTests(unittest.TestCase):
    def test_empty_inputs(self):
        self.assertEqual(summarize_text(""), "")
        self.assertEqual(simplify_text(""), "")
        self.assertEqual(generate_quiz(""), [])

    def test_summary_returns_text(self):
        text = ("La fotosíntesis es un proceso importante para las plantas. "
                "Las plantas utilizan la luz solar para producir alimento. "
                "El agua y el dióxido de carbono participan en este proceso.")
        self.assertTrue(summarize_text(text, 2))

    def test_easy_read_splits_long_sentences(self):
        text = " ".join(["palabra"] * 50)
        self.assertGreater(simplify_text(text, 10).count("\\n"), 0)

    def test_quiz_marks_teacher_review(self):
        quiz = generate_quiz("La fotosíntesis permite que las plantas produzcan su propio alimento.")
        self.assertTrue(quiz)
        self.assertTrue(quiz[0]["teacher_review_required"])
        self.assertIsNone(quiz[0]["answer_key"])

if __name__ == "__main__":
    unittest.main()
