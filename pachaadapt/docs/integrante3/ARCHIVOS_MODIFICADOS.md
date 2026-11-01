# Archivos que incorpora la entrega

La entrega **rellena los archivos vacíos del esqueleto** (los que solo contenían una línea `# TODO`) y añade archivos nuevos. Se verificó que cada archivo reemplazado contenía únicamente comentarios `# TODO` / `-- TODO`.

## A. Archivos del esqueleto que se reemplazan (eran solo `# TODO`)
| Archivo | Ahora contiene |
|---|---|
| `ai/assistant/chat_service.py` | `ChatService`: asistente de IA para docentes |
| `ai/assistant/preference_manager.py` | `PreferenceManager`: preferencias del docente |
| `ai/assistant/document_builder.py` | `DocumentBuilder`: documentos editables, archivado, importación del procesador (puerto) |
| `ai/assistant/revision_manager.py` | `RevisionManager`: historial de versiones, restauración, control de conflictos |
| `ai/model_gateway.py` | Pasarela de modelos: proveedor configurable (`OpenAICompatibleProvider` / `NotConfiguredProvider`) |
| `ai/learning_analysis/result_analyzer.py` | Validación de registros y métricas agregadas |
| `ai/learning_analysis/difficulty_detector.py` | Detección de dificultades por tema (observaciones con evidencia) |
| `ai/learning_analysis/lesson_suggestions.py` | Sugerencias vinculadas a las observaciones |
| `ai/learning_analysis/academic_report.py` | Ensamblado del informe y exportación a Markdown |
| `backend/app/services/report_service.py` | Generación y persistencia de informes sobre el puerto de datos |
| `backend/app/api/v1/ai_chat.py` | Rutas `/api/v1/ai-chat` |
| `backend/app/api/v1/documents.py` | Rutas `/api/v1/documents` |
| `backend/app/api/v1/preferences.py` | Rutas `/api/v1/preferences` |
| `backend/app/api/v1/reports.py` | Rutas `/api/v1/reports` |

Si un compañero ya rellenó alguno de estos archivos en su copia, **no extraiga encima sin comparar**: ver `LEEME_INTEGRACION.md`.

## B. Archivos nuevos (no existían)
- `ai/errors.py`, `ai/settings.py`, `ai/storage.py`: errores de dominio, configuración por variables de entorno y persistencia SQLite provisional.
- `backend/app/core/paths.py`: permite que el backend importe el paquete `ai/` (está en la raíz del repo).
- `backend/app/core/identity.py`: contrato de identidad del docente (punto de enchufe para la autenticación real).
- `backend/app/services/container.py`: ensamblado de servicios y `configure_integrations(...)`.
- `backend/app/api/v1/_deps.py`, `backend/app/api/v1/register.py`: utilidades de rutas y función `register_integrante3(app)`.
- `database/migrations/001_integrante3.sql` y `001_integrante3.down.sql` (reversión manual y destructiva; nunca se ejecuta sola).
- `tests/` (`__init__.py`, `_bootstrap.py`, `ai/`, `backend/`): 46 pruebas.
- `docs/integrante3/`: esta documentación y `backups/main.py.original`.
- `LEEME_INTEGRACION.md` (raíz).

## C. Archivo compartido modificado (único)
`backend/app/main.py`: **+2 líneas** (import y `register_integrante3(app)`); el resto del archivo es idéntico. Original respaldado en `docs/integrante3/backups/main.py.original`.

## D. Archivos compartidos NO modificados
`backend/requirements.txt`, `backend/app/core/{config,security,logging}.py`, `database/schema.sql`, `frontend/**`, `README.md`, `docker-compose.yml`: **idénticos al original**. Las rutas se montan con las 2 líneas de `main.py` indicadas arriba.
