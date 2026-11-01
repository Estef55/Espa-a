import os
import tempfile
import unittest
from pathlib import Path

from tests._bootstrap import ROOT, make_settings
from ai.settings import load_settings
from ai.storage import Database
from app.services import material_service


class MaterialPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["PACHAADAPT_I3_DB"] = str(Path(self.tmp.name) / "shared.sqlite3")
        os.environ["PACHAADAPT_STORAGE_DIR"] = str(Path(self.tmp.name) / "materials")
        self._old_storage_dir = material_service.STORAGE_DIR
        material_service.STORAGE_DIR = Path(os.environ["PACHAADAPT_STORAGE_DIR"])
        self.addCleanup(setattr, material_service, "STORAGE_DIR", self._old_storage_dir)
        self.addCleanup(os.environ.pop, "PACHAADAPT_I3_DB", None)
        self.addCleanup(os.environ.pop, "PACHAADAPT_STORAGE_DIR", None)

    def test_material_metadata_uses_shared_migration_database(self):
        saved = material_service.save_material("lesson.txt", b"Hola mundo", owner_id="teacher-a", content_type="text/plain")
        found = material_service.get_material(saved["id"], owner_id="teacher-a")
        self.assertEqual(found["sha256"], saved["sha256"])
        self.assertEqual(found["owner_id"], "teacher-a")
        self.assertTrue(Path(found["original_path"]).is_file())
        db = Database(load_settings().db_path)
        with db.read() as conn:
            row = conn.execute("SELECT owner_id, filename FROM i2_materials WHERE id=?", (saved["id"],)).fetchone()
        self.assertEqual((row["owner_id"], row["filename"]), ("teacher-a", "lesson.txt"))

    def test_material_is_not_visible_to_another_owner(self):
        saved = material_service.save_material("lesson.txt", b"Hola mundo", owner_id="teacher-a", content_type="text/plain")
        with self.assertRaises(FileNotFoundError):
            material_service.get_material(saved["id"], owner_id="teacher-b")


if __name__ == "__main__":
    unittest.main()
