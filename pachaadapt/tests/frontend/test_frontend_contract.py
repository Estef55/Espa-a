"""Contrato frontend ↔ backend: cada endpoint que llama el frontend debe existir en los routers.

Solo lee código fuente (no necesita FastAPI). Evita que la interfaz llame rutas inexistentes
y avisa si un router del backend deja de exponer algo que la interfaz usa.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "backend" / "app" / "api" / "v1"
FRONT = ROOT / "frontend" / "src"
MAIN = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")


def backend_routes() -> set[tuple[str, str]]:
    routes = set()
    for path in API.glob("*.py"):
        src = path.read_text(encoding="utf-8")
        prefix = re.search(r'APIRouter\(prefix="([^"]*)"', src)
        if not prefix:
            continue
        base = prefix.group(1)
        if not base.startswith("/api/v1"):
            if f"{path.stem}_router" not in MAIN:
                continue  # router no incluido en la aplicación
            base = "/api/v1" + base
        for method, route in re.findall(r'@router\.(get|post|put|patch|delete)\(\s*"([^"]*)"', src):
            routes.add((method.upper(), re.sub(r"\{[^}]+\}", "{}", base + route)))
    routes.add(("GET", "/health"))
    return routes


def frontend_calls() -> set[tuple[str, str]]:
    calls = set()
    for path in list((FRONT / "services").glob("*.ts")) + list((FRONT / "offline").glob("*.ts")):
        src = path.read_text(encoding="utf-8")
        consts = dict(re.findall(r'const (\w+)\s*=\s*"(/[^"]*)"', src))
        for raw in re.findall(r'[`"\'](/(?:api/v1|health)[^`"\']*|\$\{(?:API|base)\}[^`"\']*)[`"\']', src):
            text = raw
            for name, value in consts.items():
                text = text.replace("${" + name + "}", value)
            text = text.replace("${API}", "")
            text = re.sub(r"\$\{[^}]*\}", "{}", text.split("?")[0])
            text = re.sub(r"/+$", "", text)
            if text.startswith("/api/v1") or text == "/health":
                calls.add(text)
    return {("*", c) for c in calls}


class FrontendContractTests(unittest.TestCase):
    def test_every_frontend_endpoint_exists_in_backend(self):
        paths = {p for _, p in backend_routes()}
        missing = sorted(p for _, p in frontend_calls() if p not in paths)
        self.assertEqual(missing, [], f"El frontend llama endpoints que el backend no expone: {missing}")

    def test_frontend_covers_the_known_backend_areas(self):
        used = {p for _, p in frontend_calls()}
        for expected in ("/api/v1/assignments", "/api/v1/submissions", "/api/v1/material-library",
                         "/api/v1/materials", "/api/v1/materials/{}/extract", "/api/v1/materials/{}/adapt",
                         "/api/v1/documents", "/api/v1/documents/{}/restore", "/api/v1/preferences",
                         "/api/v1/ai-chat", "/api/v1/ai-chat/status", "/api/v1/reports",
                         "/api/v1/synchronization/push", "/api/v1/synchronization/pull", "/api/v1/synchronization/status"):
            self.assertIn(expected, used, f"La interfaz no usa {expected}")

    def test_methods_used_for_writes_are_declared(self):
        declared = backend_routes()
        for method, path in (("PUT", "/api/v1/assignments/{}"), ("PATCH", "/api/v1/submissions/{}/review"),
                             ("POST", "/api/v1/documents/import"), ("PUT", "/api/v1/documents/{}"),
                             ("PUT", "/api/v1/preferences"), ("POST", "/api/v1/ai-chat")):
            self.assertIn((method, path), declared)

    def test_frontend_has_no_secrets(self):
        pattern = re.compile(r"(api[_-]?key|secret|password|bearer\s+[A-Za-z0-9]{12,})\s*[:=]\s*[\"'][^\"']{6,}", re.I)
        for path in FRONT.rglob("*"):
            if path.suffix in {".ts", ".tsx", ".json", ".css"}:
                self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")), f"Posible credencial en {path}")


if __name__ == "__main__":
    unittest.main()
