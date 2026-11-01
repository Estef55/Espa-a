"""Cableado de los routers: importan, registran las rutas esperadas y sus funciones de ruta
llaman bien a los servicios y traducen los errores. Se ejecutan las funciones directamente
(con el doble de tests/backend/_stubs.py si FastAPI no está instalado)."""
import tempfile
import unittest
from types import SimpleNamespace

from tests.backend import _stubs
STUBBED = _stubs.install()

from tests._bootstrap import make_settings  # noqa: E402
from ai.model_gateway import ProviderResult  # noqa: E402
from ai.learning_analysis.result_analyzer import LearningRecord as L  # noqa: E402
from app.api.v1 import _deps, ai_chat, documents, preferences, reports  # noqa: E402
from app.api.v1.register import register_integrante3  # noqa: E402
from app.core import identity  # noqa: E402
from app.services import container as container_mod  # noqa: E402
from fastapi import HTTPException  # noqa: E402

P1 = identity.Principal("t1")


class FakeSource:
    def fetch_records(self, teacher_id, filters):
        rows = [("Fracciones", 20), ("Fracciones", 40), ("Fracciones", 60),
                ("Lectura", 80), ("Lectura", 90), ("Lectura", 100)]
        return [L(f"s{i % 3}", t, s, 100, f"2026-03-0{i + 1}") for i, (t, s) in enumerate(rows)]


class RouteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        container_mod._container = container_mod.Container(make_settings(self._tmp.name))
        self.addCleanup(container_mod.reset_container)
        self.addCleanup(identity.set_identity_resolver, None)

    def code(self, fn, *a, **kw):
        with self.assertRaises(HTTPException) as cm:
            fn(*a, **kw)
        return cm.exception.status_code, cm.exception.detail["code"]

    def test_register_exposes_expected_routes_without_duplicates(self):
        app = SimpleNamespace(routes=[], include_router=lambda r: app.routes.extend(r.routes))
        register_integrante3(app)
        got = [(m, r.path) for r in app.routes for m in r.methods]
        self.assertEqual(len(got), len(set(got)), "rutas duplicadas")
        for expected in [("GET", "/api/v1/preferences"), ("PUT", "/api/v1/preferences"),
                         ("POST", "/api/v1/documents"), ("POST", "/api/v1/documents/import"),
                         ("PUT", "/api/v1/documents/{document_id}"),
                         ("GET", "/api/v1/documents/{document_id}/versions"),
                         ("POST", "/api/v1/documents/{document_id}/restore"),
                         ("POST", "/api/v1/ai-chat"), ("GET", "/api/v1/ai-chat/status"),
                         ("POST", "/api/v1/reports"), ("GET", "/api/v1/reports/{report_id}/markdown")]:
            self.assertIn(expected, got)
        self.assertTrue(all(p.startswith("/api/v1/") for _, p in got))
        self.assertNotIn("/health", [p for _, p in got])      # no se pisan rutas existentes

    def test_main_keeps_health_and_exposes_new_routes(self):
        from app.main import app  # importa el main real del proyecto
        paths = set(app.openapi()["paths"])                 # FastAPI actualiza routers incluidos de forma diferida
        self.assertIn("/health", paths)                       # la ruta original sigue
        for expected in ("/api/v1/preferences", "/api/v1/documents", "/api/v1/ai-chat", "/api/v1/reports"):
            self.assertIn(expected, paths)

    def test_principal_dependency(self):
        req = SimpleNamespace(headers={"x-user": "t7"})
        self.assertEqual(self.code(_deps.principal, req), (503, "auth_not_configured"))
        identity.set_identity_resolver(lambda h: identity.Principal(h["x-user"]))
        self.assertEqual(_deps.principal(req).user_id, "t7")

    def test_preferences_routes(self):
        self.assertTrue(preferences.get_preferences(P1)["is_default"])
        r = preferences.put_preferences(preferences.PreferencesIn(tone="formal"), P1)
        self.assertEqual(r["preferences"]["tone"], "formal")
        self.assertEqual(self.code(preferences.put_preferences, preferences.PreferencesIn(tone="loco"), P1),
                         (422, "validation_error"))
        self.assertEqual(preferences.adaptation_params(P1)["proposed_params"]["tone"], "formal")

    def test_documents_routes_full_flow(self):
        d = documents.create_document(documents.DocumentCreate(title="Guía", content="uno"), P1)
        did = d["id"]
        d2 = documents.save_document(did, documents.DocumentSave(content="dos", expected_version=1, reason="r"), P1)
        self.assertEqual(d2["current_version"], 2)
        self.assertEqual(self.code(documents.save_document, did,
                                   documents.DocumentSave(content="tres", expected_version=1), P1),
                         (409, "version_conflict"))
        self.assertEqual(len(documents.list_versions(did, P1)), 2)
        self.assertEqual(documents.get_version(did, 1, P1)["content"], "uno")
        d3 = documents.restore_document(did, documents.DocumentRestore(version=1, expected_version=2), P1)
        self.assertEqual((d3["current_version"], d3["content"]), (3, "uno"))
        self.assertEqual(documents.get_document(did, P1)["content"], "uno")
        self.assertEqual(self.code(documents.get_document, did, identity.Principal("t2")), (404, "not_found"))
        self.assertEqual(self.code(documents.import_document, documents.DocumentImport(material_id="m1"), P1),
                         (503, "integration_not_configured"))
        self.assertEqual(documents.archive_document(did, P1)["archived"], True)
        self.assertEqual(documents.list_documents(False, P1), [])

    def test_chat_routes(self):
        self.assertFalse(ai_chat.status(P1)["ai_provider_configured"])
        self.assertEqual(self.code(ai_chat.chat, ai_chat.ChatIn(question="hola"), P1),
                         (503, "ai_provider_not_configured"))
        self.assertEqual(self.code(ai_chat.chat, ai_chat.ChatIn(question=" "), P1), (422, "validation_error"))

        class Prov:
            configured = True
            def generate(self, messages, max_tokens):
                return ProviderResult("ok-test", "m", "p")
        container_mod.get_container().configure(provider=Prov())
        r = ai_chat.chat(ai_chat.ChatIn(question="hola"), P1)
        self.assertEqual(r["answer"], "ok-test")
        self.assertEqual(len(ai_chat.get_conversation(r["conversation_id"], P1)["messages"]), 2)
        self.assertEqual(self.code(ai_chat.get_conversation, r["conversation_id"], identity.Principal("t2")),
                         (404, "not_found"))

    def test_report_routes(self):
        self.assertEqual(self.code(reports.create_report, reports.ReportIn(), P1), (503, "data_source_not_configured"))
        container_mod.get_container().configure(data_source=FakeSource())
        rep = reports.create_report(reports.ReportIn(pass_threshold_pct=55), P1)
        self.assertEqual(rep["status"], "ok")
        self.assertEqual(reports.get_report(rep["id"], P1)["id"], rep["id"])
        self.assertEqual(len(reports.list_reports(P1)), 1)
        self.assertIn("Informe de resultados", reports.report_markdown(rep["id"], P1))
        self.assertEqual(self.code(reports.get_report, rep["id"], identity.Principal("t2")), (404, "not_found"))
        self.assertEqual(self.code(reports.create_report, reports.ReportIn(pass_threshold_pct=0), P1),
                         (422, "validation_error"))


if __name__ == "__main__":
    unittest.main()
