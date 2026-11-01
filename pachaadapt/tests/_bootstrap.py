"""Hace importables ``ai`` (raíz del repo) y ``app`` (carpeta backend/) sin tocar la configuración del proyecto."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from ai.settings import Settings  # noqa: E402
from app.services.container import Container  # noqa: E402


def make_settings(tmpdir: str, **over) -> Settings:
    base = dict(db_path=str(Path(tmpdir) / "i3.sqlite3"), ai_provider="", ai_base_url="", ai_model="")
    base.update(over)
    return Settings(**base)


class TempContainerMixin:
    """Cada prueba usa una base SQLite temporal propia (datos 100 % sintéticos de prueba)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.settings = make_settings(self._tmp.name)
        self.c = Container(self.settings)
