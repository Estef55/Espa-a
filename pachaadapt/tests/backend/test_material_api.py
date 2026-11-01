import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from tests._bootstrap import ROOT  # noqa: F401 - configura las rutas de importación del backend
from app.services import material_service


class MaterialsApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._old = {key: os.environ.get(key) for key in ("PACHAADAPT_I3_DB", "PACHAADAPT_STORAGE_DIR", "PACHAADAPT_I3_DEV_AUTH")}
        self.addCleanup(self._restore_env)
        os.environ["PACHAADAPT_I3_DB"] = str(Path(self.tmp.name) / "shared.sqlite3")
        os.environ["PACHAADAPT_STORAGE_DIR"] = str(Path(self.tmp.name) / "materials")
        self._old_storage_dir = material_service.STORAGE_DIR
        material_service.STORAGE_DIR = Path(os.environ["PACHAADAPT_STORAGE_DIR"])
        self.addCleanup(setattr, material_service, "STORAGE_DIR", self._old_storage_dir)
        os.environ["PACHAADAPT_I3_DEV_AUTH"] = "1"
        from app.main import app
        self.client = TestClient(app)

    def _restore_env(self):
        for key, value in self._old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_upload_extract_adapt_and_owner_isolation(self):
        headers = {"X-Dev-Teacher-Id": "teacher-a"}
        uploaded = self.client.post("/api/v1/materials", headers=headers,
                                    files={"file": ("lesson.txt", b"La fotosintesis es importante para las plantas.", "text/plain")})
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        material_id = uploaded.json()["id"]
        extracted = self.client.post(f"/api/v1/materials/{material_id}/extract", headers=headers)
        self.assertEqual(extracted.status_code, 200, extracted.text)
        self.assertIn("fotosintesis", extracted.json()["text"])
        adapted = self.client.post(f"/api/v1/materials/{material_id}/adapt", headers=headers,
                                   json={"adaptation": "easy_read"})
        self.assertEqual(adapted.status_code, 200, adapted.text)
        self.assertTrue(adapted.json()["review_required"])
        other = self.client.get(f"/api/v1/materials/{material_id}", headers={"X-Dev-Teacher-Id": "teacher-b"})
        self.assertEqual(other.status_code, 404)
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_material_routes_require_configured_identity(self):
        os.environ.pop("PACHAADAPT_I3_DEV_AUTH", None)
        response = self.client.get("/api/v1/materials/00000000000000000000000000000000")
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
