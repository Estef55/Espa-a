# PACHAADAPT by YACHAY

Versión integrada con interfaz React/PWA, carga y adaptación de materiales, gestión de actividades, entregas y sincronización offline. El inicio de sesión real aún no forma parte del prototipo; el selector de perfiles de la interfaz es solo demostrativo.

## Inicio rápido en Windows (PowerShell)

Desde la raíz de `pachaadapt`:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

El comando de política solo afecta esa ventana de PowerShell. Abre **dos terminales** desde la raíz:

**Terminal 1 — API:**
```powershell
.\.venv\Scripts\python.exe .\scripts\start_server.py
```

**Terminal 2 — interfaz:**
```powershell
cd frontend
npm run dev
```

Abre `http://127.0.0.1:5173`. API y estado: `http://127.0.0.1:8000/docs` y `http://127.0.0.1:8000/health`.

`setup.ps1` crea el entorno virtual, instala los requisitos backend y las dependencias npm. Si ya se instalaron, no hace falta repetir la preparación.

### Instalación manual

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
cd frontend
npm install
```

Luego, en la raíz, inicia el backend como arriba. Para ejecutarlo manualmente en modo local, activa el entorno y define antes:

```powershell
$env:PACHAADAPT_I3_DEV_AUTH = "1"
python -m uvicorn --app-dir backend app.main:app --reload
```

## Qué incluye

- Materiales del integrante 2: carga y conservación de PDF/TXT, extracción, OCR opcional y adaptaciones locales.
- Catálogo de recursos, asignaciones, entregas y revisión docente del integrante 4.
- PWA con IndexedDB, caché de recursos same-origin, cola offline, reintentos y manejo de conflictos.
- Módulos de preferencias, documentos, chat e informes del integrante 3.
- Panel inicial con aulas autorizadas de solo lectura y revisión docente con calificaciones explícitas/validadas.
- Copias de seguridad y restauración de SQLite.

El catálogo de recursos (URLs) usa `/api/v1/material-library`; la carga de archivos PDF/TXT permanece en `/api/v1/materials`, de modo que ambas interfaces no colisionen. El usuario de demostración se selecciona en el frontend; esos encabezados no son autenticación de producción.

## Interfaz

La interfaz (`frontend/`) da acceso visual a las funciones implementadas: actividades, entregas, catálogo, carga y adaptación de PDF/TXT, documentos con versiones, asistente, preferencias, informes y sincronización offline. Los informes consultan resultados revisados y validados en la base compartida; si no existen datos suficientes no se inventan estadísticas. Para habilitar el Asistente de IA en desarrollo, copia `.env.example` a `.env`, añade la API key en backend y reinicia; ver `CONFIGURACION_SERVICIOS_IA.md`. Las aulas y membresías tienen endpoints backend; el inicio muestra solo las aulas autorizadas y no ofrece administración de matrículas. Detalle: `docs/frontend_interfaz.md`; integración I3/I4: `INFORME_INTEGRACION_I3_I4.md`; cambios I1: `INFORME_INTEGRANTE1_FRONTEND.md`.

## Persistencia y migraciones

Los módulos comparten una base SQLite provisional. Por defecto se conserva la ruta `storage/integrante3.sqlite3` para no separar los datos de las versiones integradas anteriores. La variable común recomendada es `PACHAADAPT_DB_PATH`; también se aceptan `PACHAADAPT_DB` y `PACHAADAPT_I3_DB` por compatibilidad.

Las migraciones previas están en `database/migrations/`; las del integrante 4, en `database/migrations/integrante4/`. Se aplican al iniciar. Los originales PDF/TXT quedan en `storage/materials/`; metadatos extraídos y relaciones de los otros módulos se guardan en la base compartida.

Se incluyen esquemas/migraciones PostgreSQL como referencia, pero el backend operativo configurado aquí usa SQLite. No se debe tratar PostgreSQL como activado o probado.

Para crear una actividad demostrativa:

```powershell
.\.venv\Scripts\python.exe .\database\seed_data.py
```

## Pruebas

Desde la raíz:

```powershell
python -m unittest discover -s tests -t . -v
python -m pytest -q backend/tests
```

Pruebas del frontend (Node 22.6+):

```powershell
cd frontend
npm test
```

Compilación del frontend:

```powershell
cd frontend
npm run build
```

## Seguridad y límites

`PACHAADAPT_I3_DEV_AUTH=1` habilita cabeceras de demostración (`X-User-Id`, `X-Role` o `X-Dev-Teacher-Id`). El script `start_server.py` lo activa solo para el arranque local de desarrollo. No expongas esa API a Internet con autenticación de cabecera; antes de producción hace falta integrar autenticación y autorización reales. El OCR requiere instalar Tesseract/Poppler y dependencias opcionales.

