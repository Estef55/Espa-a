# Implementación del Integrante 3 (v2: dentro de la estructura original)

## Estado real por funcionalidad
| Funcionalidad | Estado | Qué falta |
|---|---|---|
| **A. Asistente de IA** (`ai/assistant/chat_service.py`, `ai/model_gateway.py`, interfaz) | Implementado; proveedor intercambiable por configuración, historial propietario, preferencias y documento propio como contexto; sin proveedor → 503 controlado | Probar con un proveedor remoto real; credencial/endpoint no disponibles en esta entrega |
| **B. Documentos y versiones** (`document_builder.py`, `revision_manager.py`, interfaz) | Persistencia, historial, restauración, conflictos y permisos probados; borrador local IndexedDB y conflicto explícito; integración material→documento conectada | El guardado de borradores no se sincroniza automáticamente; confirmar en línea |
| **C. Preferencias** (`preference_manager.py`, interfaz) | Consulta, actualización, aislamiento y eliminación/restauración a defaults implementados | Integrar identidad institucional real |
| **D. Análisis e informes** (`ai/learning_analysis/*`, `report_service.py`, interfaz) | Cálculo y validación probados con fixtures; sin fuente real → 503; no se presentan fixtures como resultados reales | Conectar fuente autorizada con calificaciones revisadas; solo JSON y Markdown |
| **E. Integración** | Asistente ← preferencias/documentos; documentos ← materiales del integrante 2; rutas verificadas con FastAPI real y SQLite temporal | Proveedor remoto, origen de calificaciones y autenticación institucional pendientes |

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
`database/migrations/001_integrante3.sql` (incremental, solo `CREATE ... IF NOT EXISTS`, tablas `i3_*`). La migración de integrante 3 usa la ruta SQLite configurada con `PACHAADAPT_DB_PATH` (compatibilidad: `PACHAADAPT_DB`, `PACHAADAPT_I3_DB`); el backend comparte esa base con los módulos integrados. Si no se define, el valor predeterminado es `storage/integrante3.sqlite3`. `database/schema.sql` es documento de referencia, no se sustituyó.

## Limitaciones conocidas
- Prueba HTTP con `TestClient`, SQLite temporal y almacenamiento temporal ejecutada: health, estado, ausencia de proveedor/fuente, propiedad, actualización y conflicto de versiones; flujo material TXT → documento y rechazo por propiedad también comprobados.
- Hay interfaz React funcional de integrante 3 (`Asistente`, `Documentos`, `Preferencias`, `Informes`); no se hizo una prueba visual de navegador ni con varios dispositivos.
- No hay proveedor de IA real ni fuente real de calificaciones en esta entrega.
- Informes solo en JSON y Markdown; no se ofrece PDF/Word.
- Sin endpoint para listar o borrar conversaciones.
- El umbral por defecto (55 %) es un criterio ajustable, no una norma validada.
