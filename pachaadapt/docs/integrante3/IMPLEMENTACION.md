# Implementación del Integrante 3 (v2: dentro de la estructura original)

## Estado real por funcionalidad
| Funcionalidad | Estado | Qué falta |
|---|---|---|
| **A. Asistente de IA** (`ai/assistant/chat_service.py`, `ai/model_gateway.py`) | Implementado y probado contra un servidor HTTP local de prueba. Sin proveedor → 503 controlado, sin simulación | Probar con un proveedor real; interfaz |
| **B. Documentos y versiones** (`document_builder.py`, `revision_manager.py`) | Implementado y probado: persistencia, historial, restauración, conflictos, permisos, archivado | Conexión con el procesador del integrante 2 (puerto listo); interfaz |
| **C. Preferencias** (`preference_manager.py`) | Implementado y probado | Que el integrante 2 acepte los parámetros propuestos; interfaz |
| **D. Análisis e informes** (`ai/learning_analysis/*`, `report_service.py`) | Implementado y probado con datos **sintéticos de prueba**; sin fuente real → 503 | Una fuente real de resultados; exportar a PDF/Word (hoy JSON y Markdown) |
| **E. Integración** | Asistente ← preferencias y documentos; informes ← puerto de datos; routers montados en `main.py` | Frontend; verificar con FastAPI real |

## Arquitectura (dependencia en un solo sentido: backend → ai)
```
backend/app/api/v1/{preferences,documents,ai_chat,reports}.py   (FastAPI; delgado)
        │  usa _deps.py (identidad + errores) y services/container.py
        ▼
backend/app/services/report_service.py ─┐
ai/assistant/*   ai/learning_analysis/*  ├─► ai/storage.py (SQLite provisional, tablas i3_*)
ai/model_gateway.py                      │   ai/errors.py   ai/settings.py
```
`ai/` nunca importa `backend/` (hay una prueba que lo comprueba). El backend se ejecuta desde `backend/` y `app/core/paths.py` añade la raíz del repo a `sys.path` para poder importar `ai`.

Decisiones provisionales y reemplazables: **SQLite** propio (no impone motor; cambiar implica reescribir `ai/storage.py` y la migración); **identidad** enchufable, con sustituto de desarrollo apagado por defecto (**no apto para producción**); **proveedor de IA** compatible con `/chat/completions`.

## Garantías
- *Documentos:* v1 = original (también en `original_content`, nunca actualizado); `expected_version` obligatorio (409 si otro cambió el documento); restaurar crea versión nueva; sin borrado físico (solo archivar); SQL parametrizado; transacciones `BEGIN IMMEDIATE`; documento ajeno → 404.
- *Asistente:* el documento se pasa como datos delimitados; la respuesta marca `generated_by_model: true` y el contexto usado (documento, versión, truncado); historial acotado; pregunta ≤ 4 000 caracteres; la clave API solo vive en el servidor; si el proveedor falla no se guarda nada.
- *Informes:* solo agregados; mínimos de 5 registros y 3 estudiantes; temas con < 3 registros no se interpretan; registros inválidos excluidos y contados; observaciones etiquetadas `medido`/`calculado`; cada recomendación enlaza sus observaciones; la interpretación por IA es opcional, separada y solo recibe agregados; criterios y fecha quedan guardados.

## Preferencias admitidas (todas se usan)
| Clave | Valores |
|---|---|
| `education_level` | `inicial`, `primaria`, `secundaria`, o `null` (por defecto: no especificado) |
| `complexity` | `basico`, `intermedio` (def.), `avanzado` |
| `length` | `corta`, `media` (def.), `larga` |
| `tone` | `formal`, `cercano`, `neutro` (def.) |
| `format` | `texto` (def.), `esquema`, `lista` |
| `language` | `es` (def.), `qu` — la calidad del quechua generado por un modelo **no está verificada** |

## Contratos de API (requieren identidad de docente)
| Método y ruta | Cuerpo | Respuesta / errores |
|---|---|---|
| `GET /api/v1/preferences` | — | `{preferences, is_default, updated_at, allowed_values}` |
| `PUT /api/v1/preferences` | subconjunto de las claves | ídem; 422 si hay claves/valores inválidos |
| `GET /api/v1/preferences/adaptation-params` | — | `{proposed_params}` (propuesta para el integrante 2) |
| `POST /api/v1/documents` | `{title, content, source_material_id?}` | 201 documento v1 |
| `POST /api/v1/documents/import` | `{material_id}` | 201; **503** si el procesador no está conectado |
| `GET /api/v1/documents` (`?include_archived=true`) | — | lista |
| `GET /api/v1/documents/{id}` | — | documento con `content`; 404 |
| `PUT /api/v1/documents/{id}` | `{content, expected_version, reason?}` | documento nuevo; **409** `{current_version}`; 422 |
| `GET /api/v1/documents/{id}/versions` · `/versions/{n}` | — | historial / versión |
| `POST /api/v1/documents/{id}/restore` | `{version, expected_version, reason?}` | documento (versión nueva); 409/404 |
| `POST /api/v1/documents/{id}/archive` | — | documento archivado |
| `GET /api/v1/ai-chat/status` | — | `{ai_provider_configured, document_processor_connected, learning_data_source_connected}` |
| `POST /api/v1/ai-chat` | `{question, conversation_id?, document_id?}` | `{conversation_id, answer, generated_by_model, provider, model, document_context, preferences_applied, notice}`; 422 / 404 / **503** sin proveedor / 504 timeout / 502 error o respuesta vacía |
| `GET /api/v1/ai-chat/conversations/{id}` | — | mensajes; 404 |
| `POST /api/v1/reports` | `pass_threshold_pct, topic, group, date_from, date_to, include_ai_interpretation` (todos opcionales) | 201; `status: "ok"` o `"insufficient_data"` (+`missing`); **503** sin fuente de datos |
| `GET /api/v1/reports` · `/{id}` · `/{id}/markdown` | — | lista / informe / Markdown |

Errores: `{"detail": {"code", "message", ...}}`. Sin autenticación configurada: 503 `auth_not_configured`.

## Persistencia
`database/migrations/001_integrante3.sql` (incremental, solo `CREATE ... IF NOT EXISTS`, tablas `i3_*`). Se aplica sola al primer uso, sobre **su propio archivo** (`PACHAADAPT_I3_DB`, por defecto `storage/integrante3.sqlite3`). `database/schema.sql` no se tocó.

## Limitaciones conocidas
- **Rutas HTTP no probadas con FastAPI real** (no disponible al desarrollar): se probaron las funciones de ruta con un doble de FastAPI. Falta verificar validación de cuerpos y códigos HTTP reales.
- Sin frontend del integrante 3. Sin proveedor de IA real ni datos reales.
- Informes solo en JSON y Markdown.
- Sin endpoint para listar o borrar conversaciones.
- El umbral por defecto (55 %) es un criterio ajustable, no una norma validada.
