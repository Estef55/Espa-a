"""Permite que el backend (que se ejecuta desde ``backend/``) importe el paquete ``ai/``,
que vive en la raíz del repositorio. Se añade la raíz al FINAL de sys.path (no altera
la resolución de otros paquetes) y es idempotente."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # backend/app/core/paths.py -> raíz del repo
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
