import unittest
from tests._bootstrap import TempContainerMixin
from ai.learning_analysis import academic_report as AR
from ai.learning_analysis import result_analyzer as RA
from ai.errors import DataSourceNotConfigured, NotFound, ProviderNotConfigured, ValidationError
from ai.model_gateway import ProviderResult
from ai.learning_analysis.result_analyzer import LearningRecord as L


class FakeSource:
    """Doble de prueba con datos SINTÉTICOS (no son estudiantes reales)."""
    def __init__(self, records):
        self.records, self.calls = records, []

    def fetch_records(self, teacher_id, filters):
        self.calls.append((teacher_id, filters))
        return self.records if teacher_id == "t1" else []


def synthetic():
    # Fracciones: 20,40,60 de 100 -> media 40 ; Lectura: 80,90,100 -> media 90
    rows = []
    for i, (t, s, d) in enumerate([("Fracciones", 20, "2026-03-01"), ("Fracciones", 40, "2026-03-02"),
                                   ("Fracciones", 60, "2026-03-03"), ("Lectura", 80, "2026-03-04"),
                                   ("Lectura", 90, "2026-03-05"), ("Lectura", 100, "2026-03-06")]):
        rows.append(L(f"s{i % 3}", t, s, 100, d))
    return rows


class ComputeTests(unittest.TestCase):
    def test_known_numbers(self):
        m = RA.compute(synthetic(), 55)
        self.assertEqual(m["measured"]["records"], 6)
        self.assertEqual(m["measured"]["distinct_students"], 3)
        self.assertEqual(m["measured"]["records_below_threshold"], 2)   # solo 20 y 40 < 55
        self.assertEqual(m["calculated"]["mean_pct"], 65.0)
        self.assertEqual(m["calculated"]["median_pct"], 70.0)
        topics = {t["topic"]: t for t in m["topics"]}
        self.assertEqual(topics["Fracciones"]["mean_pct"], 40.0)
        self.assertEqual(topics["Lectura"]["mean_pct"], 90.0)
        self.assertEqual(m["calculated"]["trend"]["direction"], "mejora")  # (20,40,60)=40 vs (80,90,100)=90


class ReportServiceTests(TempContainerMixin, unittest.TestCase):
    def test_not_configured_source(self):
        with self.assertRaises(DataSourceNotConfigured):
            self.c.reports.generate("t1")

    def test_report_consistent_with_metrics(self):
        self.c.configure(data_source=FakeSource(synthetic()))
        rep = self.c.reports.generate("t1", {"pass_threshold_pct": 55})
        self.assertEqual(rep["status"], "ok")
        self.assertEqual(rep["metrics"]["calculated"]["mean_pct"], 65.0)
        ids = {o["id"] for o in rep["observations"]}
        self.assertTrue(rep["recommendations"])
        for r in rep["recommendations"]:                      # toda recomendación remite a observaciones reales
            self.assertTrue(r["based_on"] and set(r["based_on"]) <= ids)
        texts = " ".join(r["text"] for r in rep["recommendations"])
        self.assertIn("Fracciones", texts)                    # el tema débil se recomienda...
        self.assertNotIn("Lectura", texts)                    # ...el fuerte no
        self.assertEqual(rep["criteria"]["pass_threshold_pct"], 55)
        self.assertIn("created_at", rep)
        self.assertEqual(self.c.reports.get("t1", rep["id"])["id"], rep["id"])
        self.assertIn("Fracciones", AR.render_markdown(rep))

    def test_no_data_and_insufficient_data(self):
        self.c.configure(data_source=FakeSource([]))
        rep = self.c.reports.generate("t1")
        self.assertEqual(rep["status"], "insufficient_data")
        self.assertIsNone(rep["metrics"])
        self.assertTrue(rep["missing"])
        self.c.reports.set_data_source(FakeSource(synthetic()[:2]))
        rep2 = self.c.reports.generate("t1")
        self.assertEqual(rep2["status"], "insufficient_data")
        self.assertEqual(rep2["recommendations"], [])

    def test_invalid_records_are_excluded_and_counted(self):
        bad = [L("s9", "X", 150, 100, "2026-03-01"), L("s9", "X", 5, 0, "2026-03-01"),
               L("s9", "X", 5, 10, "no-es-fecha"), L("", "X", 5, 10, "2026-03-01")]
        self.c.configure(data_source=FakeSource(synthetic() + bad))
        rep = self.c.reports.generate("t1")
        self.assertEqual(rep["data_summary"]["records_invalid"], 4)
        self.assertEqual(rep["data_summary"]["records_used"], 6)

    def test_access_control_and_isolation(self):
        src = FakeSource(synthetic())
        self.c.configure(data_source=src)
        rep = self.c.reports.generate("t1")
        self.assertEqual(self.c.reports.generate("t2")["status"], "insufficient_data")  # la fuente filtra por docente
        self.assertEqual(src.calls[-1][0], "t2")
        with self.assertRaises(NotFound):
            self.c.reports.get("t2", rep["id"])
        self.assertEqual(self.c.reports.list("t2")[0]["status"], "insufficient_data")

    def test_criteria_validation(self):
        self.c.configure(data_source=FakeSource(synthetic()))
        for bad in ({"pass_threshold_pct": 0}, {"pass_threshold_pct": "55"}, {"x": 1}, {"date_from": "ayer"},
                    {"include_ai_interpretation": "si"}, "no"):
            with self.assertRaises(ValidationError):
                self.c.reports.generate("t1", bad)

    def test_ai_interpretation_is_separate_and_optional(self):
        self.c.configure(data_source=FakeSource(synthetic()))
        rep = self.c.reports.generate("t1", {"include_ai_interpretation": True})
        self.assertEqual(rep["ai_interpretation"], {"status": "unavailable", "reason": "ai_provider_not_configured"})

        seen = {}

        class P:
            configured = True
            def generate(self, messages, max_tokens):
                seen["payload"] = messages[1]["content"]
                return ProviderResult("Interpretación de prueba", "m", "p")

        self.c.configure(provider=P())
        rep = self.c.reports.generate("t1", {"include_ai_interpretation": True})
        self.assertTrue(rep["ai_interpretation"]["generated_by_ai"])
        self.assertNotIn("s0", seen["payload"])               # identificadores de estudiantes no salen al modelo
        self.assertIn("Interpretación generada por IA", AR.render_markdown(rep))


if __name__ == "__main__":
    unittest.main()
