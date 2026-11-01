"""Ensamblado de los servicios del integrante 3 y punto único de conexión con otros integrantes."""
from __future__ import annotations

import threading
from typing import Optional

from app.core import paths  # noqa: F401  (habilita "import ai")
from ai.assistant.chat_service import ChatService
from ai.assistant.document_builder import DocumentBuilder
from ai.assistant.preference_manager import PreferenceManager
from ai.assistant.revision_manager import RevisionManager
from ai.model_gateway import build_provider
from ai.settings import Settings, load_settings
from ai.storage import Database
from app.services.report_service import ReportService


class Container:
    def __init__(self, settings: Optional[Settings] = None, provider=None, processor=None, data_source=None):
        self.settings = settings or load_settings()
        self.db = Database(self.settings.db_path)
        self.provider = provider or build_provider(self.settings)
        self.preferences = PreferenceManager(self.db)
        self.documents = DocumentBuilder(self.db, processor)
        self.revisions = RevisionManager(self.db)
        self.assistant = ChatService(self.db, self.provider, self.preferences, self.documents,
                                     max_tokens=self.settings.ai_max_tokens)
        self.reports = ReportService(self.db, data_source, self.provider)

    def configure(self, processor=None, data_source=None, provider=None) -> None:
        if processor is not None:
            self.documents.set_processor(processor)
        if data_source is not None:
            self.reports.set_data_source(data_source)
        if provider is not None:
            self.provider = provider
            self.assistant.set_provider(provider)
            self.reports.set_provider(provider)


_container: Optional[Container] = None
_lock = threading.Lock()


def get_container() -> Container:
    global _container
    with _lock:
        if _container is None:
            _container = Container()
        return _container


def reset_container() -> None:
    global _container
    with _lock:
        _container = None


def configure_integrations(processor=None, data_source=None, provider=None) -> None:
    """Llamar desde el arranque del backend cuando existan el procesador documental (integrante 2),
    la fuente de resultados de aprendizaje o un proveedor de IA alternativo."""
    get_container().configure(processor=processor, data_source=data_source, provider=provider)
