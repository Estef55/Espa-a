"""Arranca el backend en modo de desarrollo local desde la raíz del proyecto."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
backend = ROOT / "backend"
env = os.environ.copy()
if not any(env.get(name) for name in ("PACHAADAPT_DB_PATH", "PACHAADAPT_DB", "PACHAADAPT_I3_DB")):
    # Conserva la ruta usada por las versiones integradas anteriores.
    env["PACHAADAPT_DB_PATH"] = str(ROOT / "storage" / "integrante3.sqlite3")
env.setdefault("PACHAADAPT_I3_DEV_AUTH", "1")
env.setdefault("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
os.chdir(backend)
raise SystemExit(subprocess.call([
    sys.executable, "-m", "uvicorn", "app.main:app", "--reload",
    "--host", env.get("PACHAADAPT_HOST", "127.0.0.1"), "--port", env.get("PACHAADAPT_PORT", "8000"),
], env=env))

