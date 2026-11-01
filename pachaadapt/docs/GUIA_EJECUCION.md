# Guía de ejecución local

Para la instalación actualizada de backend y frontend, usa el `README.md` de la raíz. Esta guía resume los comandos.

## Windows / PowerShell

Desde la raíz del proyecto:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

En una terminal:

```powershell
.\.venv\Scripts\python.exe .\scripts\start_server.py
```

En otra terminal:

```powershell
cd frontend
npm run dev
```

Abre `http://127.0.0.1:5173`. FastAPI y su documentación quedan en `http://127.0.0.1:8000` y `/docs`; estado en `/health`.

`start_server.py` activa el modo de identidad de demostración únicamente para desarrollo local. No uses esas cabeceras como autenticación de producción. El backend aplica las migraciones SQLite automáticamente y comparte el archivo de base de datos entre los módulos. `PACHAADAPT_DB_PATH` es la variable recomendada para cambiarlo; también se aceptan `PACHAADAPT_DB` y `PACHAADAPT_I3_DB` por compatibilidad.

Para las pruebas Python:

```powershell
python -m unittest discover -s tests -t . -v
python -m pytest -q backend/tests
```

Para compilar el frontend: `cd frontend; npm run build`. El OCR es opcional y requiere pytesseract, pdf2image, Tesseract (idioma `spa`) y Poppler.

