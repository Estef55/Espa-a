"""Utilidades de las pruebas del integrante 2: entorno temporal y documentos de prueba SINTÉTICOS."""
import io
import os
import tempfile
from pathlib import Path
from unittest import mock

from tests._bootstrap import ROOT  # noqa: F401 - rutas de importación
from app.services import material_service

DEMO_DIR = ROOT / "database" / "demo_materials"


def make_text_pdf(lines: list[str]) -> bytes:
    """PDF mínimo válido con texto digital (solo ASCII; es un documento de prueba)."""
    esc = lambda s: s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = "BT /F1 12 Tf 72 740 Td 16 TL " + " ".join(f"({esc(l)}) Tj T*" for l in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(content)} >>\nstream\n{content}\nendstream", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offsets = b"%PDF-1.4\n", []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def make_scanned_pdf(text: str = "Photosynthesis feeds the plants"):
    """PDF que es solo una imagen (como un escaneo). None si no hay Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    im = Image.new("RGB", (1400, 260), "white")
    try:
        font = ImageFont.load_default(size=64)
    except TypeError:
        font = ImageFont.load_default()
    ImageDraw.Draw(im).text((30, 80), text, fill="black", font=font)
    buf = io.BytesIO()
    im.save(buf, "PDF")
    return buf.getvalue()


def make_encrypted_pdf() -> bytes:
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(make_text_pdf(["Documento protegido de prueba."]))).pages:
        writer.add_page(page)
    writer.encrypt("secreto")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class IsolatedEnvMixin:
    """Base SQLite y almacenamiento temporales propios de cada prueba."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = str(Path(self.tmp.name) / "shared.sqlite3")
        patcher = mock.patch.dict(os.environ, {"PACHAADAPT_DB_PATH": self.db_path, "PACHAADAPT_I3_DEV_AUTH": "1"}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in ("PACHAADAPT_DB", "PACHAADAPT_I3_DB"):
            os.environ.pop(key, None)
        self.storage = Path(self.tmp.name) / "materials"
        old = material_service.STORAGE_DIR
        material_service.STORAGE_DIR = self.storage
        self.addCleanup(setattr, material_service, "STORAGE_DIR", old)
        self.ms = material_service

    def upload_txt(self, text: str, owner="teacher-a", name="lesson.txt"):
        return self.ms.save_material(name, text.encode("utf-8"), owner, "text/plain")


TEXT = ("La fotosíntesis es el proceso por el cual las plantas fabrican su alimento. "
        "Las hojas captan la luz del sol con la clorofila. "
        "Las raíces absorben agua del suelo y las hojas toman dióxido de carbono del aire. "
        "Con esa energía la planta produce glucosa y libera oxígeno. "
        "El oxígeno que respiramos llega al aire gracias a este proceso. "
        "Muchos animales se alimentan de plantas y dependen de ellas.")
