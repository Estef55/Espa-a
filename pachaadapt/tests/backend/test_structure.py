import os
import sqlite3
import unittest
from pathlib import Path

from tests._bootstrap import ROOT, TempContainerMixin
from ai.errors import AuthNotConfigured, Forbidden, Unauthorized
from ai.storage import Database, MIGRATIONS_DIR
from app.core import identity


class IdentityTests(unittest.TestCase):
    def tearDown(self):
        identity.set_identity_resolver(None)
        os.environ.pop("PACHAADAPT_I3_DEV_AUTH", None)

    def test_no_auth_configured_is_controlled(self):
        os.environ.pop("PACHAADAPT_I3_DEV_AUTH", None)
        with self.assertRaises(AuthNotConfigured):
            identity.resolve_principal({"X-Dev-Teacher-Id": "t1"})   # sin DEV_AUTH la cabecera se ignora

    def test_dev_auth_only_when_enabled(self):
        os.environ["PACHAADAPT_I3_DEV_AUTH"] = "1"
        self.assertEqual(identity.resolve_principal({"X-Dev-Teacher-Id": "t1"}).user_id, "t1")
        for bad in ({}, {"X-Dev-Teacher-Id": "../etc"}):
            with self.assertRaises(Unauthorized):
                identity.resolve_principal(bad)

    def test_pluggable_resolver_and_role(self):
        identity.set_identity_resolver(lambda h: identity.Principal("u9", "estudiante"))
        with self.assertRaises(Forbidden):
            identity.require_teacher(identity.resolve_principal({}))


class StructureTests(TempContainerMixin, unittest.TestCase):
    def test_migration_lives_in_database_dir_and_is_idempotent(self):
        self.assertEqual(MIGRATIONS_DIR, ROOT / "database" / "migrations")
        self.assertTrue((MIGRATIONS_DIR / "001_integrante3.sql").is_file())
        db = Database(self.settings.db_path)
        self.assertEqual(db.migrate(), ["001_integrante3", "002_integrante2_materiales", "003_integrante2_adaptaciones"])
        self.assertEqual(db.migrate(), [])
        conn = sqlite3.connect(self.settings.db_path)
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        self.assertTrue(all(n.startswith(("i2_", "i3_", "sqlite_")) for n in names), names)

    def test_ai_package_never_imports_backend(self):
        """Dependencia en un solo sentido: backend -> ai (nunca ai -> backend)."""
        for f in (ROOT / "ai").rglob("*.py"):
            text = f.read_text(encoding="utf-8")
            self.assertNotIn("from app", text, f.name)
            self.assertNotIn("import app", text, f.name)

    def test_no_secrets(self):
        import re
        for f in list((ROOT / "ai").rglob("*.py")) + list((ROOT / "backend/app").rglob("*.py")):
            self.assertIsNone(re.search(r"sk-[A-Za-z0-9]{20,}", f.read_text(encoding="utf-8")), f.name)


if __name__ == "__main__":
    unittest.main()
