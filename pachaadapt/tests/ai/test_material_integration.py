import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests._bootstrap import ROOT, make_settings  # adds the backend/repo paths and temp Settings helper
from ai.errors import NotFound
from ai.model_gateway import ProviderResult
from app.services import material_service
from app.services.container import Container, get_container, reset_container
from app.main import app, lifespan
from app.services.material_integration import MaterialDocumentProcessor
from app.services.learning_data_source import SQLiteLearningDataSource


class MaterialDocumentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = str(Path(self.temp.name) / "shared.sqlite3")
        self.old_storage_dir = material_service.STORAGE_DIR
        material_service.STORAGE_DIR = Path(self.temp.name) / "materials"
        self.addCleanup(setattr, material_service, "STORAGE_DIR", self.old_storage_dir)

    def test_document_processor_extracts_real_owned_material_and_denies_other_owner(self):
        with patch.dict(os.environ, {"PACHAADAPT_DB_PATH": self.db_path}):
            material = material_service.save_material(
                "lesson.txt", b"Contenido educativo original.", "teacher-1", "text/plain")
            processor = MaterialDocumentProcessor()
            result = processor.get_adapted_text(material["id"], "teacher-1")
            self.assertEqual(result.material_id, material["id"])
            self.assertIn("Contenido educativo original.", result.text)
            with self.assertRaises(NotFound):
                processor.get_adapted_text(material["id"], "teacher-2")

            container=Container(make_settings(self.temp.name,db_path=self.db_path))
            class FakeProvider:
                configured=True
                def generate(self,messages,max_tokens):
                    self.messages=messages
                    return ProviderResult("Propuesta revisable","modelo-prueba","proveedor-prueba")
            provider=FakeProvider();container.configure(processor=processor,provider=provider)
            document=container.documents.import_from_processor("teacher-1",material["id"])
            self.assertEqual(document["source_material_id"],material["id"])
            self.assertEqual(document["content"],"Contenido educativo original.")
            reply=container.assistant.chat("teacher-1","Propón una actividad",document_id=document["id"])
            self.assertEqual(reply["answer"],"Propuesta revisable")
            self.assertIn("Contenido educativo original.",provider.messages[0]["content"])
            with self.assertRaises(NotFound):
                container.documents.import_from_processor("teacher-2",material["id"])

    def test_application_lifespan_connects_material_processor_and_report_source(self):
        reset_container()
        self.addCleanup(reset_container)
        with patch.dict(os.environ, {"PACHAADAPT_DB_PATH": self.db_path}):
            async def exercise():
                async with lifespan(app):
                    container = get_container()
                    self.assertIsInstance(container.documents.processor, MaterialDocumentProcessor)
                    self.assertIsInstance(container.reports.data_source, SQLiteLearningDataSource)
            asyncio.run(exercise())
