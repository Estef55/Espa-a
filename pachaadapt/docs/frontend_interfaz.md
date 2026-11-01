# Interfaz web de PACHAADAPT

Frontend en React 19 + TypeScript + Vite (`frontend/`), sin dependencias nuevas. Navegación por hash (`#/ruta`), diseño adaptable (menú lateral en escritorio, desplegable en móvil) y los mismos modos de conexión/desconexión que ya existían (IndexedDB, cola offline, reintentos, conflictos).

## Pantallas y servicios que usan

| Pantalla (`#/ruta`) | Perfil | Servicios del backend |
|---|---|---|
| Inicio (`inicio`) | todos | `/assignments`, `/submissions`, `/material-library`, `/ai-chat/status` (docente) |
| Actividades (`actividades`) | estudiante: ver y responder · docente/admin: crear, editar, buscar, filtrar | `GET/POST /assignments`, `PUT /assignments/{id}?expected_version=`, `POST /submissions` |
| Entregas (`entregas`) | estudiante: «Mis entregas» · docente/admin: revisar, devolver, exportar CSV | `GET /submissions`, `PATCH /submissions/{id}/review` |
| Catálogo (`catalogo`) | todos ven · docente/admin registran | `GET/POST /material-library` |
| Archivos y adaptación (`materiales`) | docente | `POST /materials`, `GET /materials/{id}`, `POST …/extract`, `POST …/adapt` |
| Documentos editables (`documentos`) | docente | `/documents` (crear, listar, guardar con `expected_version`, versiones, restaurar, archivar, importar) |
| Asistente de IA (`asistente`) | docente | `/ai-chat/status`, `POST /ai-chat`, `GET /ai-chat/conversations/{id}` |
| Preferencias (`preferencias`) | docente | `GET/PUT /preferences`, `GET /preferences/adaptation-params` |
| Informes (`informes`) | docente | `/reports` (generar, listar, ver, Markdown) |
| Conexión y sincronización (`sincronizacion`) | todos | `POST /synchronization/push` (cola), `GET /synchronization/status`, `GET /synchronization/pull` |
| Estado de funciones (`estado`) | todos | `GET /health`, `/ai-chat/status` |
| Perfil de demostración (`perfil`) | todos | cabeceras `X-User-Id` / `X-Role` |

## Perfil: identidad de demostración

No hay autenticación real. El perfil se envía en las cabeceras `X-User-Id` y `X-Role`, y el backend solo las acepta con `PACHAADAPT_I3_DEV_AUTH=1` (lo activa `scripts/start_server.py`). La interfaz lo indica en la barra superior («Demostración · Docente») y en la pantalla Perfil. El administrador de demostración usa el usuario `demo-teacher`, como en la versión anterior.

## Permisos (según el código del backend)

- Solo **docente**: archivos y adaptación, documentos, asistente, preferencias e informes. El rol *Administrador* recibe 403 en esas rutas.
- **Docente y administrador**: crear/editar actividades (el docente solo las que creó), revisar entregas, registrar materiales en el catálogo.
- **Estudiante**: enviar respuestas.

La interfaz explica «Permisos insuficientes» antes de llamar, y el servidor vuelve a exigirlo.

## Funciones que dependen de la configuración del servidor

El backend no conecta por sí solo estas integraciones (`configure_integrations()` no se invoca en `main.py`), por eso la interfaz las desactiva y lo explica, según `GET /ai-chat/status`:

- **Asistente de IA**: requiere `PACHAADAPT_AI_PROVIDER=openai_compatible`, `PACHAADAPT_AI_BASE_URL` y `PACHAADAPT_AI_MODEL` (y `PACHAADAPT_AI_API_KEY` si el servicio la pide). Sin ellos no se genera ninguna respuesta.
- **Importar documento desde el procesador**: `POST /documents/import` responde 503 hasta que se conecte un procesador documental.
- **Generar informes**: requiere una fuente de resultados de aprendizaje; los informes ya generados se pueden consultar.
- **OCR**: requiere Tesseract y Poppler y `pytesseract`/`pdf2image` en el servidor; sin ellos el backend responde 501.

## Limitaciones conocidas del contrato

- No hay endpoint para **listar** los materiales subidos ni para **descargar** el original. La pantalla «Archivos y adaptación» recuerda en el navegador (por perfil) los identificadores subidos o consultados, y cada ficha se pide al servidor. El servidor conserva el original; la interfaz muestra su SHA-256 y lo compara con el del archivo local al subirlo.
- No hay exportación de entregas en el servidor: el CSV se genera en el navegador con las entregas visibles (con protección contra fórmulas de hoja de cálculo).
- Las entregas solo tienen los estados *entregada*, *revisada* y *devuelta*; no hay notas ni comentarios.
- Sin implementar en el proyecto (no tienen pantalla): autenticación real, usuarios, aulas e instituciones, traducción, audio, esquemas visuales, salidas accesibles, descripción de imágenes y transcripción.
- Los parámetros de `GET /preferences/adaptation-params` son una propuesta del servidor y todavía no se aplican automáticamente a las adaptaciones.

## Cambios en la capa offline (justificados)

- Cada respuesta pendiente guarda ahora el perfil que la creó (campo opcional `actor`, compatible con operaciones anteriores). Antes, al cambiar de perfil con respuestas pendientes, la cola las enviaba con el perfil nuevo, el servidor respondía 403 y **se descartaban sin aviso**.
- Un rechazo del servidor («actividad no disponible») ahora se avisa en vez de borrarse en silencio.
- Las copias locales de actividades y materiales se separan por usuario, y un error 4xx (permisos, validación) ya no se disfraza con datos antiguos.
- Al abrir la aplicación y al cambiar a un estudiante se intenta sincronizar solo la cola de ese perfil.

## Pruebas

Ver `docs/pruebas.md`. Resumen:

```powershell
cd frontend
npm test            # pruebas unitarias de servicios y lógica (Node 22.6+; sin dependencias nuevas)
npm run build       # tsc -b && vite build
cd ..
python -m unittest discover -s tests -t . -v
python -m pytest -q backend/tests
```
