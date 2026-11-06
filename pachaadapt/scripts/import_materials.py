"""Importa materiales a PACHAADAPT y genera sus adaptaciones locales (integrante 2).

Sin argumentos importa los TRES MATERIALES DE DEMOSTRACIÓN (fotosíntesis, ciclo del agua y sistema
digestivo) de ``database/demo_materials/``. Quedan marcados como demostración (``is_demo``) y no
sustituyen materiales reales. Es idempotente: no duplica un material ya importado (mismo SHA-256 y
dueño) y solo genera las adaptaciones que falten.

    python scripts/import_materials.py                          # demostración, dueño demo-teacher
    python scripts/import_materials.py --owner profe1           # demostración con otro dueño
    python scripts/import_materials.py --dir ruta --authorized  # PDF/TXT reales, SOLO con autorización

No usa servicios en línea. El audio no se genera aquí (hazlo desde la interfaz si el servidor tiene motor de voz).
"""
from __future__ import annotations

import argparse
import hashlib
import mimetypes
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

DEMO_DIR = ROOT / "database" / "demo_materials"
DEMO_FILES = ("DEMO_fotosintesis.pdf", "DEMO_ciclo_del_agua.pdf", "DEMO_sistema_digestivo.txt")
KINDS = ("summary", "easy_read", "outline", "quiz")


def import_file(path: Path, owner: str, demo: bool) -> dict:
    from app.services import material_service as ms
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    existing = next((m for m in ms.list_materials(owner) if m["sha256"] == digest), None)
    created = existing is None
    if created:
        material_id = ms.save_material(path.name, content, owner, mimetypes.guess_type(path.name)[0] or "application/octet-stream", is_demo=demo)["id"]
    else:
        material_id = existing["id"]
    summary = {"file": path.name, "material_id": material_id, "created": created, "adaptations": [], "skipped": []}
    try:
        if created or existing["status"] != "extracted":
            if ms.extract_material_text(material_id, owner_id=owner)["status"] != "extracted":
                summary["skipped"].append("sin texto extraíble (usa OCR desde la interfaz si el PDF es escaneado)")
                return summary
        have = {a["adaptation"] for a in ms.list_adaptations(material_id, owner)}
        for kind in list(KINDS) + (["image_notes"] if path.suffix.lower() == ".pdf" else []):
            if kind in have:
                continue
            try:
                result = ms.adapt_material(material_id, kind, owner_id=owner)
                (summary["adaptations"] if result["persisted"] else summary["skipped"]).append(kind if result["persisted"] else f"{kind} (vacía)")
            except (ValueError, RuntimeError) as exc:
                summary["skipped"].append(f"{kind}: {exc}")
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        summary["skipped"].append(f"error: {exc}")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--owner", default="demo-teacher", help="identificador del docente dueño (por defecto demo-teacher)")
    parser.add_argument("--dir", type=Path, help="carpeta con PDF/TXT reales a importar")
    parser.add_argument("--authorized", action="store_true", help="confirma que tienes autorización para usar esos materiales")
    args = parser.parse_args(argv)
    from app.db import init_db
    init_db()
    if args.dir:
        if not args.authorized:
            print("Para importar materiales reales confirma con --authorized que tienes autorización para usarlos.", file=sys.stderr)
            return 2
        files, demo = sorted(p for p in args.dir.iterdir() if p.suffix.lower() in (".pdf", ".txt")), False
    else:
        files, demo = [DEMO_DIR / n for n in DEMO_FILES], True
    if not files:
        print("No se encontraron archivos PDF o TXT.", file=sys.stderr)
        return 1
    for f in files:
        r = import_file(f, args.owner, demo)
        print(f"{'NUEVO    ' if r['created'] else 'YA EXISTE'} {r['file']} → {r['material_id']}  adaptaciones: {', '.join(r['adaptations']) or '—'}"
              + (f"  | no generadas: {'; '.join(r['skipped'])}" if r["skipped"] else ""))
    print("Materiales de demostración: no son contenido curricular oficial." if demo else "Importación terminada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
