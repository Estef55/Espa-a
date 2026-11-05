"""Servicio y router de adaptaciones del integrante 2 (con el doble de FastAPI si no está instalado)."""
import os
import tempfile
import unittest
from pathlib import Path

from tests.backend import _stubs
_stubs.install()

from tests import _bootstrap  # noqa: E402,F401
from app.services import material_service, adaptation_service as svc  # noqa: E402
from app.api.v1 import adaptations as api  # noqa: E402
from app.core import identity  # noqa: E402
from fastapi import HTTPException  # noqa: E402

TEXT = (b"La fotosintesis es un proceso de las plantas. Las plantas usan luz solar para producir alimento. "
        b"El agua participa en la fotosintesis. Las plantas necesitan dioxido de carbono del aire.")


class AdaptationServiceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        os.environ["PACHAADAPT_I3_DB"] = str(Path(tmp.name) / "db.sqlite3")
        self.addCleanup(os.environ.pop, "PACHAADAPT_I3_DB", None)
        old = material_service.STORAGE_DIR
        material_service.STORAGE_DIR = Path(tmp.name) / "m"
        self.addCleanup(setattr, material_service, "STORAGE_DIR", old)
        self.mid = material_service.save_material("l.txt", TEXT, "t1", "text/plain")["id"]
        self.addCleanup(svc.set_translation_provider, None)

    def test_adaptations_work_and_are_owner_scoped(self):
        self.assertTrue(svc.visual(self.mid, "t1", "concept_map")["review_required"])
        self.assertIn("braille", svc.accessible(self.mid, "t1", "bundle")["result"])
        self.assertTrue(svc.audio_script(self.mid, "t1")["result"]["chunks"])
        with self.assertRaises(FileNotFoundError):
            svc.visual(self.mid, "t2")
        with self.assertRaises(ValueError):
            svc.accessible(self.mid, "t1", "pdf")

    def test_translation_501_until_provider(self):
        with self.assertRaises(RuntimeError):
            svc.translate(self.mid, "t1", "qu")
        svc.set_translation_provider(lambda t, s, d: "xx", requires_connection=True)
        r = svc.translate(self.mid, "t1", "qu")
        self.assertTrue(r["requires_internet"] and r["result"]["human_review_required"])

    def test_capabilities_separate_offline_and_server(self):
        res = {r["id"]: r for r in svc.capabilities()["resources"]}
        self.assertTrue(res["cached_materials"]["works_offline_on_device"])
        self.assertTrue(res["saved_adaptations"]["works_offline_on_device"])
        for k in ("summary_easy_quiz", "translation", "audio", "image_description"):
            self.assertTrue(res[k]["requires_server"])
        self.assertFalse(res["translation"]["available"])
        self.assertFalse(res["image_description"]["available"])

    def test_router_error_mapping_and_routes(self):
        identity.set_identity_resolver(lambda h: identity.Principal("t1"))
        self.addCleanup(identity.set_identity_resolver, None)
        p = identity.Principal("t1")
        with self.assertRaises(HTTPException) as cm:
            api.translate(self.mid, api.TranslateRequest(target="qu"), p)
        self.assertEqual(cm.exception.status_code, 501)
        with self.assertRaises(HTTPException) as cm:
            api.visual("0" * 32, api.VisualRequest(), p)
        self.assertEqual(cm.exception.status_code, 404)
        with self.assertRaises(HTTPException) as cm:
            api.accessible(self.mid, api.AccessibleRequest(format="zip"), p)
        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn("resources", api.capabilities(p))
        self.assertEqual(api.subtitles(api.SubtitlesRequest(content="1\n00:00:01,000 --> 00:00:02,000\nHola\n"), p)["text"], "Hola")
        paths = {(m, r.path) for r in api.router.routes for m in r.methods}
        self.assertIn(("POST", "/adaptations/materials/{material_id}/audio"), paths)


if __name__ == "__main__":
    unittest.main()
