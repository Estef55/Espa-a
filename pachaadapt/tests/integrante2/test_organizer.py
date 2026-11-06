import unittest

from tests._bootstrap import ROOT  # noqa: F401
from ai.adaptations.quiz_generator import generate_quiz
from ai.adaptations.organized_outline import build_outline, outline_to_text
from ai.document_processing.text_organizer import flatten_table, organize_text


class OrganizerTests(unittest.TestCase):
    RAW = ("[Página 1]\nLA FOTOSÍNTESIS\nLas plantas producen su alimento usando la luz solar. Este proceso ocurre\nen los cloroplastos.\n\n"
           "Etapas\n- Fase luminosa\n- Fase oscura\n\nGas   Símbolo   Función\nO2   Oxígeno   Se libera\n\n[Página 2]\nResumen final\nTodo termina bien.")

    def test_blocks_pages_and_warnings(self):
        o = organize_text(self.RAW)
        self.assertEqual([b["type"] for b in o["blocks"]], ["heading", "paragraph", "heading", "list", "table_like", "heading", "paragraph"])
        self.assertIn("en los cloroplastos", o["blocks"][1]["text"])
        self.assertEqual((o["stats"]["pages"], o["stats"]["tables"]), (2, 1))
        self.assertTrue(any("tablas" in w for w in o["warnings"]))
        self.assertNotIn("[Página", o["clean_text"])

    def test_tables_are_flattened_without_losing_cells(self):
        self.assertEqual(flatten_table("Gas   Símbolo\nO2   Oxígeno"), "Gas — Símbolo\nO2 — Oxígeno")

    def test_empty_and_plain_text(self):
        self.assertEqual(organize_text("")["blocks"], [])
        o = organize_text("Una sola frase larga sin título que explica algo importante sobre el tema tratado aquí.")
        self.assertTrue(any("títulos" in w for w in o["warnings"]))

    def test_demo_notice_is_not_content(self):
        o = organize_text("[Página 1]\nMATERIAL DE DEMOSTRACIÓN — no es un material curricular oficial.\n\nTítulo\nUna frase normal del documento.")
        self.assertEqual(o["blocks"][0]["type"], "notice")
        self.assertNotIn("DEMOSTRACIÓN", o["adapt_text"])

    def test_outline_is_extractive(self):
        o = organize_text(self.RAW)
        out = build_outline(o)
        self.assertFalse(out["is_concept_map"])
        text = outline_to_text(out)
        self.assertIn("## Etapas", text)
        self.assertIn("Fase luminosa", text)

    def test_quiz_spreads_over_the_whole_text(self):
        text = " ".join(f"Esta es la oración número {n} del documento de prueba." for n in range(1, 21))
        frags = [q["reference_fragment"] for q in generate_quiz(text, 4)]
        self.assertEqual(len(frags), 4)
        self.assertTrue(int(frags[-1].split("número ")[1].split()[0]) > 10)


if __name__ == "__main__":
    unittest.main()
