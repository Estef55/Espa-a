$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Instala Python 3.11+ y vuelve a ejecutar." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Instala Node.js LTS y vuelve a ejecutar." }
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Push-Location frontend
npm install
Pop-Location
Write-Host "Dependencias instaladas. Usa scripts/start_server.py o los comandos del README." -ForegroundColor Green
