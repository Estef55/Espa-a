import sqlite3
import threading
import unittest
from tests._bootstrap import TempContainerMixin
from app.services.container import Container
from ai.errors import Conflict, IntegrationNotConfigured, NotFound, ValidationError
from ai.assistant.document_builder import AdaptedDocument


class DocumentTests(TempContainerMixin, unittest.TestCase):
    def new_doc(self, owner="t1", content="original"):
        return self.c.documents.create(owner, "Guía", content)

    def test_create_save_history(self):
        d = self.new_doc()
        self.assertEqual(d["current_version"], 1)
        d2 = self.c.revisions.save("t1", d["id"], "editado", 1, "mejora de redacción")
        self.assertEqual((d2["current_version"], d2["content"]), (2, "editado"))
        vs = self.c.revisions.versions("t1", d["id"])
        self.assertEqual([v["version"] for v in vs], [2, 1])
        self.assertEqual(vs[0]["reason"], "mejora de redacción")
        self.assertEqual(vs[0]["author_id"], "t1")
        self.assertEqual(self.c.revisions.get_version("t1", d["id"], 1)["content"], "original")

    def test_restore_keeps_history(self):
        d = self.new_doc()
        self.c.revisions.save("t1", d["id"], "v2", 1)
        self.c.revisions.save("t1", d["id"], "v3", 2)
        r = self.c.revisions.restore("t1", d["id"], 1, 3)
        self.assertEqual((r["current_version"], r["content"]), (4, "original"))
        vs = self.c.revisions.versions("t1", d["id"])
        self.assertEqual(len(vs), 4)                      # nada se perdió
        self.assertEqual(vs[0]["restored_from"], 1)
        self.assertEqual(self.c.revisions.get_version("t1", d["id"], 3)["content"], "v3")

    def test_stale_expected_version_conflicts(self):
        d = self.new_doc()
        self.c.revisions.save("t1", d["id"], "A", 1)
        with self.assertRaises(Conflict) as cm:
            self.c.revisions.save("t1", d["id"], "B", 1)
        self.assertEqual(cm.exception.extra["current_version"], 2)
        self.assertEqual(self.c.documents.get("t1", d["id"])["content"], "A")

    def test_concurrent_saves_only_one_wins(self):
        d = self.new_doc()
        results, barrier = [], threading.Barrier(6)

        def worker(i):
            barrier.wait()
            try:
                self.c.revisions.save("t1", d["id"], f"edit {i}", 1)
                results.append("ok")
            except Conflict:
                results.append("conflict")

        ts = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(sorted(results), ["conflict"] * 5 + ["ok"])
        self.assertEqual(self.c.documents.get("t1", d["id"])["current_version"], 2)

    def test_unauthorized_access_is_not_found(self):
        d = self.new_doc("t1")
        ops = [lambda: self.c.documents.get("t2", d["id"]),
               lambda: self.c.revisions.save("t2", d["id"], "x", 1),
               lambda: self.c.revisions.versions("t2", d["id"]),
               lambda: self.c.revisions.get_version("t2", d["id"], 1),
               lambda: self.c.revisions.restore("t2", d["id"], 1, 1),
               lambda: self.c.documents.archive("t2", d["id"])]
        for op in ops:
            with self.assertRaises(NotFound):
                op()
        self.assertEqual(self.c.documents.list("t2"), [])
        self.assertEqual(self.c.documents.get("t1", d["id"])["current_version"], 1)

    def test_persistence_after_restart(self):
        d = self.new_doc()
        self.c.revisions.save("t1", d["id"], "persistido", 1, "r")
        c2 = Container(self.settings)
        self.assertEqual(c2.documents.get("t1", d["id"])["content"], "persistido")
        self.assertEqual(len(c2.revisions.versions("t1", d["id"])), 2)

    def test_validation(self):
        d = self.new_doc()
        for kwargs in ({"content": "  ", "expected_version": 1}, {"content": "x", "expected_version": 0},
                       {"content": "x", "expected_version": True}, {"content": "x" * 500_001, "expected_version": 1},
                       {"content": "original", "expected_version": 1}):   # sin cambios
            with self.assertRaises(ValidationError):
                self.c.revisions.save("t1", d["id"], **kwargs)
        with self.assertRaises(ValidationError):
            self.c.documents.create("t1", "", "x")

    def test_original_immutable_and_no_physical_delete(self):
        d = self.new_doc(content="texto original")
        self.c.revisions.save("t1", d["id"], "otro", 1)
        self.c.documents.archive("t1", d["id"])
        with self.assertRaises(ValidationError):
            self.c.revisions.save("t1", d["id"], "más", 2)       # archivado: solo lectura
        raw = sqlite3.connect(self.settings.db_path)
        self.assertEqual(raw.execute("SELECT original_content FROM i3_documents").fetchone()[0], "texto original")
        raw.close()
        self.assertEqual(self.c.documents.list("t1"), [])
        self.assertEqual(len(self.c.documents.list("t1", include_archived=True)), 1)

    def test_processor_port(self):
        with self.assertRaises(IntegrationNotConfigured):
            self.c.documents.import_from_processor("t1", "m1")
        calls = []

        class FakeProcessor:  # doble de prueba del puerto del integrante 2
            def get_adapted_text(self, material_id, owner_id):
                calls.append((material_id, owner_id))
                return AdaptedDocument(material_id, "Fracciones adaptadas", "texto adaptado")

        self.c.configure(processor=FakeProcessor())
        d = self.c.documents.import_from_processor("t1", "m1")
        self.assertEqual((d["source_material_id"], d["content"]), ("m1", "texto adaptado"))
        self.assertEqual(calls, [("m1", "t1")])


if __name__ == "__main__":
    unittest.main()
