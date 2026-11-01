#!/usr/bin/env sh
# Prepara el entorno de desarrollo en Linux/macOS.
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
command -v python3 >/dev/null 2>&1 || { echo "Instala Python 3.11+" >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Instala Node.js LTS" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "Instala npm junto con Node.js" >&2; exit 1; }
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt
(cd frontend && npm install)
echo "Entorno preparado. Ejecuta: .venv/bin/python scripts/start_server.py"
