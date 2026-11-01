# Auditoría inicial — Integrante 3 (PACHAADAPT by YACHAY)

Fecha: 29-oct-2026. Fase 0: **solo lectura**; no se modificó ningún archivo existente.
Origen: `pachaadapt.zip` (extraído en una copia de trabajo; el zip original no se tocó).

## 1. Resumen ejecutivo

El repositorio entregado es **una plantilla de esqueletos**, no una aplicación con módulos de los integrantes 1 y 2:

- 66 de los ~87 archivos de código/docs son un comentario `# TODO` de una línea.
- No hay rutas de API, modelos, esquema de base de datos, autenticación, carga de documentos, procesamiento de documentos, adaptaciones, proveedor de IA ni fuente de resultados de aprendizaje.
- El README lo confirma: «Los módulos contienen únicamente esqueletos y tareas pendientes; no representan una aplicación completa».

Consecuencia: gran parte de las dependencias que el prompt da por existentes (documentos procesados, autenticación, resultados de estudiantes, contratos del integrante 2) **no existen todavía** en este zip.

## 2. Inventario comprobado

### Existe y tiene contenido real
| Archivo | Contenido real |
|---|---|
| `backend/app/main.py` | App FastAPI con un único endpoint `GET /health`. No incluye routers. |
| `backend/requirements.txt` | `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `python-multipart` (sin versiones fijadas). |
| `frontend/index.html` (12,5 KB) | **Prototipo en JavaScript puro** con CSS inline y datos simulados (roles Docente/Estudiante/Administrador, Inicio, Biblioteca, Grupos, Aulas, Áreas, Temas, Instituciones, Usuarios, Niveles, Grados, login, selector Español/Quechua). Parece el trabajo de diseño del integrante 1. |
| `frontend/src/styles.css` (11 KB) | Hoja de estilos (clases `.topbar`, `.sidebar`, `.panel`, `.material-card`, modo `.dark`, etc.). **No es importada** por `App.tsx` ni `main.tsx`. |
| `frontend/src/App.tsx` | Placeholder de 3 líneas («Plantilla inicial del proyecto»). |
| `frontend/src/main.tsx`, `vite.config.ts`, `tsconfig.json`, `package.json` | Configuración mínima de React + Vite + TS (`strict: true`). Dependencias con versión `latest`. |
| `frontend/src/i18n/es.json`, `qu.json` | Solo `appName` y `language`. |
| `frontend/public/manifest.json`, `offline.html` | Manifiesto PWA mínimo (sin iconos) y página offline. |
| `README.md` | Descripción de la estructura. |

### Solo esqueleto (`# TODO`)
- Todo `backend/app/api/v1/*` (adaptations, ai_chat, assignments, auth, classrooms, documents, institutions, materials, preferences, reports, submissions, synchronization, users).
- Todo `backend/app/core/*` (config, logging, security) y `backend/app/services/*`.
- Todo `ai/*`, incluidos `model_gateway.py` y `ai/assistant/{chat_service,document_builder,preference_manager,revision_manager}.py` y `ai/learning_analysis/*` (estos nombres coinciden con las funciones del integrante 3 y están vacíos).
- `database/schema.sql`, `database/seed_data.py`, `scripts/*`, `docker-compose.yml` (`services: {}`), `frontend/src/services/*`, `frontend/src/offline/*`, `docs/*` (excepto este directorio).

### Mencionado pero inexistente
- Carpetas `storage/` y `tests/` (citadas en el README): **no existen**.
- Archivos `__init__.py`: no hay ninguno (los paquetes funcionan como *namespace packages*).
- Repositorio Git: **no hay `.git`**; no se puede distinguir quién cambió qué.

## 3. Hallazgos por área requerida

1. **Persistencia:** motor no definido. `schema.sql` vacío; sin ORM; sin `pydantic-settings` usado todavía. No se puede afirmar SQLite/MariaDB.
2. **Autenticación/autorización:** inexistente (`security.py` y `auth.py` son TODO). No hay usuario actual, roles ni permisos.
3. **Documentos/procesamiento (integrante 2):** inexistente (`documents.py`, `materials.py`, `pdf_extractor.py`, `adaptations/*` son TODO). No hay contrato que consumir.
4. **IA:** `model_gateway.py` es TODO; no hay proveedor, clave ni variable de entorno definida.
5. **Resultados de aprendizaje:** no existe fuente (`submissions.py`, `grading_service.py`, `result_analyzer.py` son TODO). El esquema no define estudiantes, entregas ni calificaciones.
6. **Informes:** `report_service.py` y `reports.py` son TODO; no hay módulo reutilizable.
7. **Sincronización offline:** solo archivos TODO.
8. **Frontend:** el contenido real vive en `index.html` (JS puro). Vite sirve ese `index.html`, que **no carga** `src/main.tsx` (no hay `<script type="module">` ni `#root`), así que `npm run dev` muestra el prototipo y no `App.tsx`. No existe ninguna pantalla de asistente, versiones, preferencias o informes.
9. **Pruebas:** no hay ninguna.

## 4. Elementos que no deberían estar en una entrega
- `backend/.venv/` (venv de **Windows**, ~miles de archivos) y `frontend/node_modules/` (binarios **win32**): no sirven en Linux/macOS ni deben versionarse.
- `backend/app/__pycache__/main.cpython-312.pyc`.
- Sugerencia: `.gitignore` (no se crea aquí: es archivo compartido).

Versiones observadas en el venv: FastAPI 0.162.0, Starlette 1.10.0, Pydantic 2.14.2, Uvicorn 0.54.0, pydantic-settings 2.16.2 (Python 3.12).

## 5. Limitaciones del entorno de auditoría
- Sin acceso a red: no se pudo instalar FastAPI/pytest/httpx ni dependencias npm.
- El venv y `node_modules` del zip son de Windows y no se pueden ejecutar aquí.
- Por tanto, **en este entorno no se puede ejecutar el backend FastAPI ni compilar el frontend**; solo se puede ejecutar Python estándar (`unittest`, `sqlite3`). Estas pruebas deben hacerse en la máquina del usuario.
