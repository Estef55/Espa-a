"""Pruebas de los módulos del integrante 2 que no dependen de FastAPI."""
import base64
import struct
import unittest

from tests import _bootstrap  # noqa: F401
from ai.adaptations import accessibility, audio_generator, translator, visual_organizer
from ai.document_processing import image_describer, media_transcriber
from ai.language_support import cultural_validation as cv
from ai.language_support.language_registry import LanguageRegistry, default_registry

TEXT = ("La fotosíntesis es un proceso de las plantas. Las plantas usan luz solar para producir alimento. "
        "El agua participa en la fotosíntesis. Las plantas necesitan dióxido de carbono del aire.")


def png(w=10, h=20):
    return b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + struct.pack(">II", w, h)


class AccessibilityTests(unittest.TestCase):
    def test_braille_basic(self):
        r = accessibility.to_braille("Hola, Ñandú 25.")
        self.assertTrue(r["braille"].startswith("⠠⠓⠕⠇⠁⠂"))
        self.assertIn("⠼⠃⠑", r["braille"])
        self.assertTrue(r["review_required"])

    def test_braille_reports_unmapped(self):
        self.assertIn("@", accessibility.to_braille("a@b")["unmapped_characters"])

    def test_html_escapes_and_declares_language(self):
        h = accessibility.to_accessible_html("<script>x</script> hola", "T<", "qu")
        self.assertIn('lang="qu"', h)
        self.assertNotIn("<script>", h)

    def test_empty_rejected(self):
        for fn in (accessibility.plain_text, accessibility.to_braille, visual_organizer.build_outline):
            with self.assertRaises(ValueError):
                fn("  ")


class VisualTests(unittest.TestCase):
    def test_outline_and_map(self):
        o = visual_organizer.build_outline(TEXT)
        self.assertTrue(o["topics"] and o["review_required"])
        m = visual_organizer.build_concept_map(TEXT)
        self.assertTrue(m["mermaid"].startswith("graph TD"))
        ids = {n["id"] for n in m["nodes"]}
        self.assertTrue(all(e["from"] in ids and e["to"] in ids for e in m["edges"]))


class AudioTests(unittest.TestCase):
    def test_script_chunks_long_sentence(self):
        s = audio_generator.build_narration_script("palabra " * 200, max_chars=100)
        self.assertTrue(all(len(c) <= 100 for c in s["chunks"]))
        self.assertIn("<speak", s["ssml"])

    def test_synthesis_is_honest_without_engine(self):
        if audio_generator.available_engine():
            self.skipTest("hay un motor de voz instalado")
        with self.assertRaises(audio_generator.AudioEngineUnavailable):
            audio_generator.synthesize_audio("hola", "/tmp/x.wav")
        self.assertFalse(audio_generator.audio_status()["synthesis_available"])


class TranslatorTests(unittest.TestCase):
    def test_no_provider_no_fake_translation(self):
        with self.assertRaises(translator.TranslationUnavailable):
            translator.translate_text("hola", "es", "qu")

    def test_with_provider_requires_review(self):
        r = translator.translate_text("hola", "es", "qu", provider=lambda t, s, d: "napaykullayki")
        self.assertTrue(r["human_review_required"] and r["community_validation_required"])
        self.assertEqual(r["validation"]["status"], "pending")

    def test_same_language_and_unknown_language(self):
        with self.assertRaises(ValueError):
            translator.translate_text("hola", "es", "es", provider=lambda *a: "x")
        with self.assertRaises(translator.TranslationUnavailable):
            translator.translate_text("hola", "es", "xx", provider=lambda *a: "x")


class ImageAndMediaTests(unittest.TestCase):
    def test_inspect_and_no_invented_description(self):
        self.assertEqual(image_describer.inspect_image(png())["width"], 10)
        with self.assertRaises(image_describer.ImageDescriptionUnavailable):
            image_describer.describe_image(png())
        with self.assertRaises(ValueError):
            image_describer.inspect_image(b"no es imagen")

    def test_subtitles_srt_and_vtt(self):
        srt = "1\n00:00:01,000 --> 00:00:02,500\nHola <i>mundo</i>\n\n2\n00:00:03,000 --> 00:00:04,000\nAdiós\n"
        r = media_transcriber.subtitles_to_text(srt)
        self.assertEqual(r["text"], "Hola mundo\nAdiós")
        vtt = "WEBVTT\n\n00:01.000 --> 00:02.000\nUno\n"
        self.assertEqual(media_transcriber.subtitles_to_text(vtt)["text"], "Uno")
        with self.assertRaises(ValueError):
            media_transcriber.subtitles_to_text("sin tiempos")

    def test_transcription_status_honest(self):
        self.assertTrue(media_transcriber.transcription_status()["subtitles_supported"])


class LanguageTests(unittest.TestCase):
    def test_registry_quechua_variety_unconfirmed(self):
        reg = default_registry()
        self.assertFalse(reg.get("qu").variety_confirmed)
        reg.confirm_variety("qu", "Quechua ejemplo")
        self.assertTrue(reg.get("qu").variety_confirmed)
        with self.assertRaises(KeyError):
            LanguageRegistry().get("es")

    def test_validation_flow(self):
        rec = cv.request_validation("texto", "qu")
        self.assertFalse(rec.usable_in_class)
        with self.assertRaises(ValueError):
            cv.review(rec, "texto", "", "teacher", cv.APPROVED)
        with self.assertRaises(ValueError):
            cv.review(rec, "texto cambiado", "t1", "teacher", cv.APPROVED)
        with self.assertRaises(ValueError):
            cv.review(rec, "texto", "t1", "teacher", cv.REJECTED)  # sin motivo
        cv.review(rec, "texto", "t1", "community_speaker", cv.APPROVED)
        self.assertTrue(rec.usable_in_class)


if __name__ == "__main__":
    unittest.main()
