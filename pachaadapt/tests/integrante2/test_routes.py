"""Capa HTTP del integrante 2. Con FastAPI instalado se prueba de extremo a extremo; sin él, se verifica la estructura por AST."""
import ast
import unittest

from tests._bootstrap import ROOT
from tests.integrante2._helpers import IsolatedEnvMixin, TEXT, make_text_pdf

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = None

API = ROOT / "backend" / "app" / "api" / "v1"


class RouteStructureTests(unittest.TestCase):
    """No necesita FastAPI: detecta errores de orden de rutas y registro."""

    def _routes(self, name):
        out = []
        for node in ast.walk(ast.parse((API / name).read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef):
                for d in node.decorator_list:
                    if isinstance(d, ast.Call) and getattr(d.func, "attr", "") in {"get", "post"}:
                        out.append((d.func.attr.upper(), d.args[0].value))
        return out

    def test_static_routes_precede_dynamic_ones(self):
        paths = [p for _, p in self._routes("materials.py")]
        self.assertLess(paths.index("/capabilities"), paths.index("/{material_id}"))

    def test_expected_routes_exist(self):
        mats, adap = self._routes("materials.py"), self._routes("adaptations_persisted.py")
        for r in [("GET", ""), ("GET", "/capabilities"), ("GET", "/{material_id}/original"), ("GET", "/{material_id}/text"),
                  ("POST", "/{material_id}/extract"), ("POST", "/{material_id}/adapt")]:
            self.assertIn(r, mats)
        self.assertEqual(len(adap), 6)

    def test_main_registers_integrante2(self):
        main = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn("register_integrante2(app)", main)


@unittest.skipIf(TestClient is None, "FastAPI no está instalado en este equipo")
class RouteIntegrationTests(IsolatedEnvMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        from app.main import app
        # Con el contexto, corre el lifespan de main.py (ahí se conecta el procesador documental).
        self._client = TestClient(app)
        self.c = self._client.__enter__()
        self.addCleanup(self._client.__exit__, None, None, None)
        self.a, self.b = {"X-Dev-Teacher-Id": "teacher-a"}, {"X-Dev-Teacher-Id": "teacher-b"}

    def test_full_flow_and_isolation(self):
        up = self.c.post("/api/v1/materials", headers=self.a, files={"file": ("l.pdf", make_text_pdf([TEXT[:100], TEXT[100:200]]), "application/pdf")})
        self.assertEqual(up.status_code, 201, up.text)
        mid = up.json()["id"]
        self.assertEqual(self.c.post(f"/api/v1/materials/{mid}/extract", headers=self.a).status_code, 200)
        self.assertEqual(self.c.get(f"/api/v1/materials/{mid}/text", headers=self.a).status_code, 200)
        ad = self.c.post(f"/api/v1/materials/{mid}/adapt", headers=self.a, json={"adaptation": "summary"})
        self.assertEqual(ad.status_code, 200, ad.text)
        aid = ad.json()["id"]
        self.assertEqual(len(self.c.get(f"/api/v1/materials/{mid}/adaptations", headers=self.a).json()), 1)
        self.assertEqual(self.c.post(f"/api/v1/materials/{mid}/adaptations/{aid}/review", headers=self.a, json={"approved": True}).json()["review_status"], "approved")
        self.assertEqual(self.c.get(f"/api/v1/materials/{mid}/original", headers=self.a).content[:4], b"%PDF")
        self.assertEqual(self.c.get(f"/api/v1/materials/{mid}/adaptations/{aid}/export?format=html", headers=self.a).status_code, 200)
        for url in (f"/api/v1/materials/{mid}", f"/api/v1/materials/{mid}/original", f"/api/v1/materials/{mid}/adaptations"):
            self.assertEqual(self.c.get(url, headers=self.b).status_code, 404, url)
        self.assertEqual(self.c.get("/api/v1/materials", headers=self.b).json(), [])

    def test_errors_map_to_http_codes(self):
        self.assertEqual(self.c.post("/api/v1/materials", headers=self.a, files={"file": ("x.pdf", b"nada", "application/pdf")}).status_code, 400)
        mid = self.c.post("/api/v1/materials", headers=self.a, files={"file": ("x.txt", TEXT.encode(), "text/plain")}).json()["id"]
        self.assertEqual(self.c.post(f"/api/v1/materials/{mid}/adapt", headers=self.a, json={"adaptation": "summary"}).status_code, 400)  # sin extraer
        self.assertEqual(self.c.post(f"/api/v1/materials/{mid}/adapt", headers=self.a, json={"adaptation": "braille"}).status_code, 422)
        self.c.post(f"/api/v1/materials/{mid}/extract", headers=self.a)
        self.assertEqual(self.c.post(f"/api/v1/materials/{mid}/adapt", headers=self.a, json={"adaptation": "translation"}).status_code, 501)
        self.assertFalse(self.c.get("/api/v1/materials/capabilities", headers=self.a).json()["features"]["translation"]["available"])

    def test_documents_import_is_no_longer_503(self):
        mid = self.c.post("/api/v1/materials", headers=self.a, files={"file": ("x.txt", TEXT.encode(), "text/plain")}).json()["id"]
        self.c.post(f"/api/v1/materials/{mid}/extract", headers=self.a)
        r = self.c.post("/api/v1/documents/import", headers=self.a, json={"material_id": mid})
        self.assertNotEqual(r.status_code, 503, r.text)


if __name__ == "__main__":
    unittest.main()
