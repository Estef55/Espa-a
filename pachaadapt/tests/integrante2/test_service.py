"""Pruebas del servicio de materiales (integrante 2): carga, extracción, estados, adaptaciones y vínculos. No requieren FastAPI."""
import json
import os
import stat
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from tests._bootstrap import ROOT
from tests.integrante2._helpers import DEMO_DIR, IsolatedEnvMixin, TEXT, make_encrypted_pdf, make_scanned_pdf, make_text_pdf


class UploadTests(IsolatedEnvMixin, unittest.TestCase):
    def test_original_is_kept_intact_and_hashed(self):
        data = make_text_pdf(["Hola mundo de prueba."])
        meta = self.ms.save_material("a b.pdf", data, "teacher-a", "application/pdf")
        path, _, ctype = self.ms.original_file(meta["id"], "teacher-a")
        import hashlib
        self.assertEqual(path.read_bytes(), data)
        self.assertEqual((meta["status"], meta["sha256"], ctype), ("uploaded", hashlib.sha256(data).hexdigest(), "application/pdf"))

    def test_invalid_uploads_are_rejected_without_leaving_files(self):
        for name, content, msg in [("a.txt", b"", "vacío"), ("a.docx", b"x", "Formato no admitido"),
                                   ("a.pdf", b"no soy pdf", "PDF válido"), ("a.txt", b"abc\x00\x01def", "binarios")]:
            with self.assertRaisesRegex(ValueError, msg):
                self.ms.save_material(name, content, "teacher-a")
        with mock.patch.object(self.ms, "MAX_UPLOAD_BYTES", 10), self.assertRaisesRegex(ValueError, "límite"):
            self.ms.save_material("a.txt", b"x" * 11, "teacher-a")
        self.assertEqual(self.ms.list_materials("teacher-a"), [])
        self.assertEqual(list(self.storage.glob("*")) if self.storage.exists() else [], [])

    def test_list_and_isolation_between_teachers(self):
        a, b = self.upload_txt(TEXT), self.upload_txt(TEXT, owner="teacher-b")
        self.assertEqual([m["id"] for m in self.ms.list_materials("teacher-a")], [a["id"]])
        for fn in (self.ms.describe_material, self.ms.original_file, self.ms.get_organized_text, self.ms.list_adaptations):
            with self.assertRaises(FileNotFoundError):
                fn(b["id"], "teacher-a")
        with self.assertRaises(ValueError):
            self.ms.describe_material("../../etc/passwd", "teacher-a")


class ExtractionTests(IsolatedEnvMixin, unittest.TestCase):
    def test_txt_and_digital_pdf_extraction_and_state(self):
        t = self.upload_txt(TEXT)
        r = self.ms.extract_material_text(t["id"], owner_id="teacher-a")
        self.assertEqual((r["status"], r["method"]), ("extracted", "txt"))
        pdf = self.ms.save_material("p.pdf", make_text_pdf(["La fotosintesis produce oxigeno.", "Las plantas usan luz."]), "teacher-a")
        r = self.ms.extract_material_text(pdf["id"], owner_id="teacher-a")
        self.assertIn("fotosintesis", r["text"])
        self.assertEqual((r["status"], r["method"], r["page_count"]), ("extracted", "pdf_text", 1))
        d = self.ms.describe_material(pdf["id"], "teacher-a")
        self.assertEqual((d["status"], d["attempts"], d["page_count"]), ("extracted", 1, 1))

    def test_corrupt_pdf_records_failure_and_retry_counts_attempts(self):
        m = self.ms.save_material("roto.pdf", b"%PDF-1.4\nesto no es un pdf real", "teacher-a")
        for expected in (1, 2):
            with self.assertRaises(ValueError):
                self.ms.extract_material_text(m["id"], owner_id="teacher-a")
            d = self.ms.describe_material(m["id"], "teacher-a")
            self.assertEqual((d["status"], d["error"]["code"], d["attempts"]), ("failed", "invalid_document", expected))
        with self.assertRaises(ValueError):
            self.ms.adapt_material(m["id"], "summary", owner_id="teacher-a")

    def test_encrypted_pdf_is_reported(self):
        m = self.ms.save_material("c.pdf", make_encrypted_pdf(), "teacher-a")
        with self.assertRaisesRegex(ValueError, "contraseña"):
            self.ms.extract_material_text(m["id"], owner_id="teacher-a")
        self.assertEqual(self.ms.describe_material(m["id"], "teacher-a")["error"]["code"], "invalid_document")

    def test_missing_original_is_recorded(self):
        m = self.upload_txt(TEXT)
        for f in self.storage.glob("*"):
            f.unlink()
        with self.assertRaises(FileNotFoundError):
            self.ms.extract_material_text(m["id"], owner_id="teacher-a")
        self.assertEqual(self.ms.describe_material(m["id"], "teacher-a")["error"]["code"], "original_missing")

    def test_scanned_pdf_without_text_is_identified_not_faked(self):
        data = make_scanned_pdf()
        if data is None:
            self.skipTest("Pillow no está instalado")
        m = self.ms.save_material("scan.pdf", data, "teacher-a")
        r = self.ms.extract_material_text(m["id"], owner_id="teacher-a")
        self.assertEqual((r["status"], r["text"]), ("no_text", ""))
        self.assertTrue(any("OCR" in w for w in r["warnings"]))
        with self.assertRaisesRegex(ValueError, "No hay texto"):
            self.ms.adapt_material(m["id"], "summary", owner_id="teacher-a")

    def test_ocr_unavailable_is_a_clear_error(self):
        data = make_scanned_pdf()
        if data is None:
            self.skipTest("Pillow no está instalado")
        m = self.ms.save_material("scan.pdf", data, "teacher-a")
        with mock.patch.dict(os.environ, {"PACHAADAPT_OCR_LANGS": "idioma_inexistente"}), \
                mock.patch("ai.document_processing.ocr_processor.ocr_status", return_value={"available": False, "languages": "x", "reason": "falta Tesseract"}), \
                self.assertRaisesRegex(RuntimeError, "OCR no disponible"):
            self.ms.extract_material_text(m["id"], use_ocr=True, owner_id="teacher-a")
        self.assertEqual(self.ms.describe_material(m["id"], "teacher-a")["error"]["code"], "engine_unavailable")

    def test_ocr_reads_a_scanned_pdf_when_tesseract_is_installed(self):
        from ai.document_processing.ocr_processor import ocr_status
        data = make_scanned_pdf()
        with mock.patch.dict(os.environ, {"PACHAADAPT_OCR_LANGS": "eng"}):
            if data is None or not ocr_status()["available"]:
                self.skipTest("OCR (Tesseract+Poppler+Pillow) no está disponible en este equipo")
            m = self.ms.save_material("scan.pdf", data, "teacher-a")
            r = self.ms.extract_material_text(m["id"], use_ocr=True, owner_id="teacher-a")
        self.assertEqual((r["status"], r["method"], r["ocr_used"]), ("extracted", "ocr", True))
        self.assertIn("photosynthesis", r["text"].lower())

    def test_organized_text_requires_extraction_first(self):
        with self.assertRaisesRegex(ValueError, "Aún no se extrajo"):
            self.ms.get_organized_text(self.upload_txt(TEXT)["id"], "teacher-a")


class AdaptationTests(IsolatedEnvMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.m = self.upload_txt("Fotosíntesis\n\n" + TEXT + "\n\nBeneficios\n- Produce oxígeno\n- Da alimento")
        self.ms.extract_material_text(self.m["id"], owner_id="teacher-a")

    def test_every_local_adaptation_is_persisted_and_linked_to_its_original(self):
        for kind in ("summary", "easy_read", "quiz", "outline"):
            a = self.ms.adapt_material(self.m["id"], kind, owner_id="teacher-a")
            self.assertTrue(a["persisted"] and a["review_required"])
            self.assertEqual((a["material_id"], a["adaptation"], a["review_status"]), (self.m["id"], kind, "pending"))
            self.assertEqual(self.ms.get_adaptation(self.m["id"], a["id"], "teacher-a")["text"], a["text"])
        self.assertEqual(sorted(x["adaptation"] for x in self.ms.list_adaptations(self.m["id"], "teacher-a")),
                         ["easy_read", "outline", "quiz", "summary"])
        self.assertEqual(self.ms.describe_material(self.m["id"], "teacher-a")["adaptation_count"], 4)
        self.assertTrue(self.ms.original_file(self.m["id"], "teacher-a")[0].is_file())

    def test_adaptations_only_use_text_from_the_document(self):
        words = set(TEXT.lower().replace(".", "").split()) | {"fotosíntesis", "beneficios", "produce", "oxígeno", "da", "alimento"}
        for kind in ("summary", "easy_read"):
            text = self.ms.adapt_material(self.m["id"], kind, owner_id="teacher-a")["text"]
            for w in text.lower().replace(".", "").replace("\n", " ").split():
                if w != "-":
                    self.assertIn(w, words, f"{kind} contiene «{w}», que no está en el documento")

    def test_quiz_is_partial_when_text_is_short_and_empty_is_not_persisted(self):
        a = self.ms.adapt_material(self.m["id"], "quiz", options={"count": 20}, owner_id="teacher-a")
        self.assertEqual(a["status"], "partial")
        self.assertTrue(any("pregunta" in w for w in a["warnings"]))
        short = self.upload_txt("Hola.", name="corto.txt")
        r = self.ms.adapt_material(short["id"], "quiz", owner_id="teacher-a")
        self.assertEqual((r["status"], r["persisted"], r["id"]), ("empty", False, None))
        self.assertEqual(self.ms.list_adaptations(short["id"], "teacher-a"), [])

    def test_edited_text_is_recorded_as_such(self):
        a = self.ms.adapt_material(self.m["id"], "summary", text="Texto corregido por el docente con varias palabras útiles aquí.", owner_id="teacher-a")
        self.assertEqual(a["source_origin"], "edited")

    def test_page_markers_never_leak_into_adaptations(self):
        pdf = self.ms.save_material("p.pdf", make_text_pdf([TEXT[:90], TEXT[90:180]]), "teacher-a")
        self.ms.extract_material_text(pdf["id"], owner_id="teacher-a")
        for kind in ("summary", "easy_read", "quiz", "outline"):
            self.assertNotIn("[Página", self.ms.adapt_material(pdf["id"], kind, owner_id="teacher-a")["text"])

    def test_unavailable_or_unknown_adaptations_report_clearly(self):
        with self.assertRaisesRegex(RuntimeError, "traducción no está disponible"):
            self.ms.adapt_material(self.m["id"], "translation", owner_id="teacher-a")
        with self.assertRaisesRegex(ValueError, "no reconocida"):
            self.ms.adapt_material(self.m["id"], "braille", owner_id="teacher-a")
        with self.assertRaisesRegex(ValueError, "TXT"):
            self.ms.adapt_material(self.m["id"], "image_notes", owner_id="teacher-a")
        self.assertEqual(self.ms.list_adaptations(self.m["id"], "teacher-a"), [])

    def test_audio_unavailable_without_engine(self):
        with mock.patch("ai.adaptations.local_audio.detect_engine", return_value=None), self.assertRaisesRegex(RuntimeError, "motor de voz"):
            self.ms.adapt_material(self.m["id"], "audio", owner_id="teacher-a")
        self.assertEqual(self.ms.list_adaptations(self.m["id"], "teacher-a"), [])

    def test_audio_with_a_local_engine_stores_and_serves_the_file(self):
        # Motor de voz FALSO (script que escribe un WAV mínimo): prueba la integración, no la calidad de voz real.
        engine = Path(self.tmp.name) / "espeak-ng"
        engine.write_text('#!/bin/sh\nwhile [ $# -gt 0 ]; do [ "$1" = "-w" ] && out="$2"; shift; done\nprintf "RIFF....WAVEfmt " > "$out"\n')
        engine.chmod(engine.stat().st_mode | stat.S_IEXEC)
        with mock.patch("ai.adaptations.local_audio.detect_engine", return_value=str(engine)):
            a = self.ms.adapt_material(self.m["id"], "audio", owner_id="teacher-a")
        self.assertEqual((a["adaptation"], a["persisted"]), ("audio", True))
        self.assertTrue(self.ms.adaptation_audio_file(self.m["id"], a["id"], "teacher-a").is_file())
        with self.assertRaises(FileNotFoundError):
            self.ms.adaptation_audio_file(self.m["id"], a["id"], "teacher-b")
        with self.assertRaisesRegex(ValueError, "no es un audio"):
            self.ms.adaptation_audio_file(self.m["id"], self.ms.adapt_material(self.m["id"], "summary", owner_id="teacher-a")["id"], "teacher-a")

    def test_review_is_explicit_and_reversible(self):
        a = self.ms.adapt_material(self.m["id"], "summary", owner_id="teacher-a")
        r = self.ms.review_adaptation(self.m["id"], a["id"], True, "teacher-a")
        self.assertEqual((r["review_status"], r["review_required"]), ("approved", False))
        self.assertTrue(r["reviewed_at"])
        self.assertEqual(self.ms.review_adaptation(self.m["id"], a["id"], False, "teacher-a")["review_status"], "pending")
        with self.assertRaises(FileNotFoundError):
            self.ms.review_adaptation(self.m["id"], a["id"], True, "teacher-b")

    def test_export_is_escaped_labelled_and_owner_only(self):
        evil = self.upload_txt("<script>alert(1)</script> es una frase de prueba con suficientes palabras.", name="x.txt")
        a = self.ms.adapt_material(evil["id"], "easy_read", owner_id="teacher-a")
        data, ctype, filename = self.ms.export_adaptation(evil["id"], a["id"], "html", "teacher-a")
        body = data.decode()
        self.assertNotIn("<script>", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertIn('lang="es"', body)
        self.assertIn("Aún no fue revisado", body)
        self.assertTrue(filename.endswith(".html") and ctype.startswith("text/html"))
        self.ms.review_adaptation(evil["id"], a["id"], True, "teacher-a")
        self.assertIn("Revisado por el docente", self.ms.export_adaptation(evil["id"], a["id"], "html", "teacher-a")[0].decode())
        s = self.ms.adapt_material(self.m["id"], "summary", owner_id="teacher-a")
        self.assertIn("SIN REVISAR", self.ms.export_adaptation(self.m["id"], s["id"], "txt", "teacher-a")[0].decode())
        with self.assertRaisesRegex(ValueError, "braille"):
            self.ms.export_adaptation(evil["id"], a["id"], "braille", "teacher-a")
        with self.assertRaises(FileNotFoundError):
            self.ms.export_adaptation(evil["id"], a["id"], "html", "teacher-b")


class LinkTests(IsolatedEnvMixin, unittest.TestCase):
    def test_link_to_assignment_and_document_keeps_original_adaptation_activity_chain(self):
        from app.db import init_db, transaction
        from app.services.container import Container
        from ai.settings import load_settings
        init_db()
        m = self.upload_txt(TEXT)
        a = self.ms.adapt_material(m["id"], "quiz", owner_id="teacher-a")
        with transaction() as con:
            con.execute("INSERT INTO assignments(id,title,instructions,created_by,status) VALUES('as1','Act','x','teacher-a','draft')")
            con.execute("INSERT INTO assignments(id,title,instructions,created_by,status) VALUES('as2','Ajena','x','teacher-b','draft')")
        c = Container(load_settings())
        doc = c.documents.create("teacher-a", "Doc", "contenido", m["id"])
        other = c.documents.create("teacher-b", "Doc", "contenido")
        self.ms.link_adaptation(m["id"], a["id"], "assignment", "as1", "teacher-a")
        self.ms.link_adaptation(m["id"], a["id"], "document", doc["id"], "teacher-a")
        r = self.ms.link_adaptation(m["id"], a["id"], "document", doc["id"], "teacher-a")  # idempotente
        self.assertEqual(sorted((l["target_type"], l["target_id"]) for l in r["links"]), [("assignment", "as1"), ("document", doc["id"])])
        for t, i in (("assignment", "as2"), ("document", other["id"]), ("assignment", "no-existe")):
            with self.assertRaises(FileNotFoundError):
                self.ms.link_adaptation(m["id"], a["id"], t, i, "teacher-a")
        with self.assertRaisesRegex(ValueError, "target_type"):
            self.ms.link_adaptation(m["id"], a["id"], "otro", "x", "teacher-a")


class ProcessorPortTests(IsolatedEnvMixin, unittest.TestCase):
    def test_i3_import_uses_the_best_adaptation_and_respects_ownership(self):
        from app.services.container import Container
        from app.services.material_processor import MaterialProcessor
        from ai.errors import NotFound, ValidationError
        from ai.settings import load_settings
        c = Container(load_settings(), processor=MaterialProcessor())
        m = self.upload_txt(TEXT)
        with self.assertRaises(ValidationError):
            c.documents.import_from_processor("teacher-a", m["id"])
        self.ms.extract_material_text(m["id"], owner_id="teacher-a")
        d = c.documents.import_from_processor("teacher-a", m["id"])
        self.assertTrue(d["title"].startswith("Texto extraído") and d["source_material_id"] == m["id"])
        self.ms.adapt_material(m["id"], "summary", owner_id="teacher-a")
        self.assertTrue(c.documents.import_from_processor("teacher-a", m["id"])["title"].startswith("Resumen"))
        easy = self.ms.adapt_material(m["id"], "easy_read", owner_id="teacher-a")
        doc = c.documents.import_from_processor("teacher-a", m["id"])
        self.assertTrue(doc["title"].startswith("Lectura fácil") and doc["content"] == easy["text"])
        with self.assertRaises(NotFound):
            c.documents.import_from_processor("teacher-b", m["id"])
        with self.assertRaises(NotFound):
            c.documents.import_from_processor("teacher-a", "0" * 32)


class DemoAndPersistenceTests(IsolatedEnvMixin, unittest.TestCase):
    def test_three_demo_materials_are_processed_flagged_and_idempotent(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import import_materials
        files = [DEMO_DIR / n for n in import_materials.DEMO_FILES]
        self.assertEqual([f.stem for f in files], ["DEMO_fotosintesis", "DEMO_ciclo_del_agua", "DEMO_sistema_digestivo"])
        self.assertTrue(all(r["created"] for r in [import_materials.import_file(f, "demo-teacher", True) for f in files]))
        mats = self.ms.list_materials("demo-teacher")
        self.assertEqual(len(mats), 3)
        self.assertTrue(all(m["is_demo"] and m["filename"].startswith("DEMO_") and m["status"] == "extracted" for m in mats))
        for m in mats:
            kinds = {a["adaptation"] for a in self.ms.list_adaptations(m["id"], "demo-teacher")}
            self.assertTrue({"summary", "easy_read", "outline", "quiz"} <= kinds, m["filename"])
        photo = next(m for m in mats if "fotosintesis" in m["filename"])
        notes = next(a for a in self.ms.list_adaptations(photo["id"], "demo-teacher") if a["adaptation"] == "image_notes")
        self.assertIn("Figura 1", notes["text"])
        water = next(m for m in mats if "agua" in m["filename"])
        easy = next(a for a in self.ms.list_adaptations(water["id"], "demo-teacher") if a["adaptation"] == "easy_read")
        self.assertIn("Evaporación — El calor del sol convierte el agua en vapor.", easy["text"])  # la tabla no se pierde
        second = [import_materials.import_file(f, "demo-teacher", True) for f in files]
        self.assertFalse(any(r["created"] or r["adaptations"] for r in second))
        self.assertEqual(len(self.ms.list_materials("demo-teacher")), 3)

    def test_data_survives_a_server_restart(self):
        m = self.upload_txt(TEXT)
        self.ms.extract_material_text(m["id"], owner_id="teacher-a")
        a = self.ms.adapt_material(m["id"], "outline", owner_id="teacher-a")
        self.ms.review_adaptation(m["id"], a["id"], True, "teacher-a")
        code = ("import json,sys;sys.path[:0]=[sys.argv[1],sys.argv[1]+'/backend'];from pathlib import Path;"
                "from app.services import material_service as ms;ms.STORAGE_DIR=Path(sys.argv[2]);"
                "mid,aid=sys.argv[3],sys.argv[4];"
                "print(json.dumps({'m':ms.describe_material(mid,'teacher-a'),'a':ms.get_adaptation(mid,aid,'teacher-a'),"
                "'orig':ms.original_file(mid,'teacher-a')[0].is_file()}))")
        out = subprocess.run([sys.executable, "-c", code, str(ROOT), str(self.storage), m["id"], a["id"]], capture_output=True, text=True,
                             env={**os.environ, "PACHAADAPT_DB_PATH": self.db_path})
        self.assertEqual(out.returncode, 0, out.stderr)
        data = json.loads(out.stdout)
        self.assertEqual((data["m"]["status"], data["m"]["adaptation_count"], data["a"]["review_status"], data["orig"]), ("extracted", 1, "approved", True))
        self.assertEqual(data["a"]["text"], a["text"])

    def test_capabilities_are_honest(self):
        c = self.ms.capabilities()
        f = c["features"]
        self.assertFalse(f["translation"]["available"] or f["braille"]["available"])
        self.assertTrue(all(f[k]["available"] for k in ("summary", "easy_read", "quiz", "outline")))
        self.assertTrue(all(f[k]["needs_internet"] is False for k in ("text_extraction", "ocr", "summary", "audio")))
        with mock.patch("ai.adaptations.local_audio.detect_engine", return_value=None):
            self.assertFalse(self.ms.capabilities()["features"]["audio"]["available"])
        self.assertEqual(c["formats"], [".pdf", ".txt"])


if __name__ == "__main__":
    unittest.main()
