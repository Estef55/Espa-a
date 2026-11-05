import unittest
from tests._bootstrap import TempContainerMixin
from ai.assistant import preference_manager as P
from ai.errors import ValidationError
from app.services.container import Container


class PreferencesTests(TempContainerMixin, unittest.TestCase):
    def test_defaults_when_nothing_saved(self):
        r = self.c.preferences.get("t1")
        self.assertTrue(r["is_default"])
        self.assertEqual(r["preferences"], P.DEFAULTS)

    def test_valid_partial_update_and_merge(self):
        self.c.preferences.update("t1", {"tone": "cercano"})
        r = self.c.preferences.update("t1", {"length": "corta", "education_level": "primaria"})
        self.assertFalse(r["is_default"])
        self.assertEqual(r["preferences"]["tone"], "cercano")
        self.assertEqual(r["preferences"]["length"], "corta")
        self.assertEqual(r["preferences"]["complexity"], "intermedio")  # sigue por defecto

    def test_invalid_values_rejected(self):
        for bad in ({"tone": "agresivo"}, {"nope": "x"}, {}, {"tone": 3}, {"complexity": None}, "x"):
            with self.assertRaises(ValidationError, msg=str(bad)):
                self.c.preferences.update("t1", bad)
        self.assertTrue(self.c.preferences.get("t1")["is_default"])  # nada se guardó

    def test_isolation_between_teachers(self):
        self.c.preferences.update("t1", {"tone": "formal"})
        self.assertEqual(self.c.preferences.get("t2")["preferences"]["tone"], "neutro")

    def test_persistence_after_restart(self):
        self.c.preferences.update("t1", {"language": "qu"})
        c2 = Container(self.settings)  # "reinicio": nueva instancia, mismo archivo
        self.assertEqual(c2.preferences.get("t1")["preferences"]["language"], "qu")

    def test_clear_removes_saved_preferences_and_restores_defaults(self):
        self.c.preferences.update("t1", {"tone": "formal", "language": "qu"})
        cleared = self.c.preferences.clear("t1")
        self.assertTrue(cleared["is_default"])
        self.assertEqual(cleared["preferences"], P.DEFAULTS)
        with self.c.db.read() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM i3_teacher_preferences WHERE teacher_id='t1'").fetchone()[0], 0)
        self.assertEqual(self.c.preferences.get("t2")["preferences"], P.DEFAULTS)

    def test_prompt_and_adaptation_params(self):
        prefs = self.c.preferences.update("t1", {"education_level": "secundaria"})["preferences"]
        self.assertIn("nivel educativo: secundaria", P.prompt_fragment(prefs))
        self.assertEqual(P.adaptation_params(prefs)["education_level"], "secundaria")
        self.assertNotIn("education_level", P.adaptation_params(P.DEFAULTS))


if __name__ == "__main__":
    unittest.main()
