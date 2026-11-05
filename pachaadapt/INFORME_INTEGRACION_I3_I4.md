# Informe de integración selectiva — PACHAADAPT I3 + I4

## Base y criterio de integración

La base es `pachaadapt_integrante3_fase2_actualizado.zip`; el archivo de I4 se trató como fuente selectiva, nunca como reemplazo. Antes de modificar se conservó `pachaadapt_integrante3_fase2_actualizado_pre_i4.zip`. Se revisaron las rutas y los hashes de ambos árboles. Los módulos de IA y configuración de proveedores del I3 se conservaron; no se reemplazaron por la versión diferente incluida en el ZIP de I4.

## Matriz de integración

| Componente | Proyecto base I3 | ZIP I4 | Acción aplicada |
|---|---|---|---|
| Backend / actividades | Rutas existentes, con operaciones y contratos de sincronización incompletos | Validación de roles, propiedad, versión optimista y aislamiento | Se integraron selectivamente las rutas de aulas, actividades y sincronización; se reforzó persistencia y acceso a entregas. |
| Base de datos | SQLite compartida y migraciones 001–003 | Migración aditiva para aulas, calificaciones validadas y ámbito demo/real | Se incorporó migración 004; registros previos reciben valores seguros por defecto (no demo, sin puntuación validada). |
| Sincronización offline | Cola IndexedDB, reintentos y UI existentes | UUID idempotente, ACK/conflicto/rechazo, límites y protección de entregas revisadas | Se integró servicio y endpoints I4 conservando el frontend/cola del proyecto base. |
| Informes pedagógicos | Servicio I3 con puerto `LearningDataSource`, pero sin implementación conectada | Fuente SQLite de resultados autorizados y validados | Se conectó al arranque. Solo entran calificaciones revisadas, validadas, puntuadas y dentro del ámbito del docente. Se añadió soporte seguro para actividades sin aula. |
| Documentos y materiales | Documentos editables/historial I3 y procesador de materiales existente | Contratos y biblioteca de materiales | Se preservaron los servicios del proyecto base; no se duplicó procesamiento documental. |
| IA | Asistente y proveedor configurable (OpenAI compatible, OpenAI, Groq, Ollama) | Copia de `ai/model_gateway.py` distinta | Se conservó intacto el archivo de I3 y sus variables/configuración. |
| Interfaz | Pantallas existentes para actividades, entregas, catálogo, sincronización e informes | Principalmente cambios backend/documentación | Se conservó el frontend; no se afirmó una nueva pantalla de administración de aulas. |

## Archivos incorporados

- `backend/app/api/v1/classrooms.py`
- `backend/app/services/learning_data_source.py`
- `database/migrations/integrante4/004_learning_results_and_demo.sql`
- `docs/integrante4/CONTRATOS_INTEGRACION.md`
- `docs/MEJORAS_SEGUNDA_REVISION.md`

## Archivos existentes modificados

- `backend/app/api/v1/assignments.py`
- `backend/app/api/v1/submissions.py`
- `backend/app/api/v1/synchronization.py`
- `backend/app/main.py` (registro aditivo de aulas y fuente de resultados; conserva routers I3/I2 y middleware)
- `backend/app/services/sync_service.py`
- `backend/tests/test_workflows.py`
- `database/seed_data.py`
- `docs/api.md`
- `docs/integrante4/CONTRATOS_INTEGRACION.md`
- `docs/MEJORAS_SEGUNDA_REVISION.md`
- `README.md`
- `tests/ai/test_material_integration.py`
- `tests/backend/test_routes_wiring.py`

## Elementos preservados

Se conservaron sin reemplazo los módulos funcionales I3 de `ai/`, las rutas y servicios de documentos, preferencias, chat e informes, las migraciones 001–003, el middleware y los routers ya registrados, además del frontend, sus servicios API, caché offline y cola IndexedDB. `CONFIGURACION_SERVICIOS_IA.md` y las variables existentes no se reemplazaron con las copias recibidas.

## Conflictos y resolución

- `main.py` era compartido: se añadió el router de aulas y se conectó `SQLiteLearningDataSource` manteniendo el procesador documental, healthcheck, adaptaciones y routers existentes.
- `ai/model_gateway.py` y la documentación IA diferían: se mantuvo la versión actual de I3, que soporta aliases del proveedor flexible.
- Una prueba I3 anterior esperaba que los informes siguieran sin fuente incluso al arrancar el servidor. Se actualizó esa expectativa porque la fuente SQLite ya es parte de la integración pedida.
- La fuente I4 original omitía resultados de actividades sin aula por usar un `JOIN` obligatorio. Se reprodujo con una prueba fallida; se ajustó a `LEFT JOIN` y se limita ese caso al docente propietario. La prueba confirma también que otro docente no obtiene los resultados.
- En la primera suite se observó una prueba de identidad dependiente del estado global de autenticación demo; se incorporó la expectativa I4 que apaga explícitamente dicho modo durante esa verificación.

## Cambios y datos

La migración 004 añade `classrooms`, `classroom_members`, ámbitos `is_demo`, referencias materiales y columnas de puntuación/validación/revisión. No borra datos ni cambia SQLite. Las migraciones se aplican al mismo archivo compartido al iniciar backend. La carga demo usa IDs deterministas y aborta ante colisión con cuentas reales; `--reset` elimina únicamente filas marcadas demo.

## Funcionalidades integradas y probadas

- Creación/listado de aulas y matrícula con roles, propiedad, existencia/estado del estudiante y separación demo/real.
- Creación/edición de actividades con versión optimista y controles de acceso.
- Envío, consulta y revisión de entregas; puntuación validada explícita y protección frente a sobrescritura.
- Push idempotente con UUID, detección de contenido distinto, conflictos y atomicidad de lotes; pull/status y límite de lote.
- Informes desde datos SQLite confirmados y autorizados, incluyendo resultados de actividades con y sin aula.
- Carga demo idempotente, rechazo de colisiones y reset sin borrar filas reales.
- Arranque y coexistencia de rutas de informes, IA, documentos, preferencias, materiales, actividades, entregas, aulas y sincronización.
- Regresión I3 de documentos/materiales, IA, informes y preferencias.

## Pruebas ejecutadas

- `python -m pytest -q ./backend/tests ./tests`: **105 passed**, con una advertencia de deprecación en AnyIO/pytest.
- `python -m unittest discover -s tests -t . -q`: **85 passed**.
- Pruebas backend focalizadas para resultados con y sin aula: **2 passed**.
- `npm test` desde `frontend/`: **33 passed**.
- `npm run build` desde `frontend/`: compilación correcta, 67 módulos transformados.
- `python -m compileall -q ai backend scripts database tests`: correcto.
- La suite cubre contratos y flujos API con SQLite temporal, seed idempotente y aislamiento demo/real. No equivale a una prueba física multi-dispositivo ni a una revisión de seguridad de autenticación de producción.

## Pendientes y límites conocidos

- El proyecto no incorpora autenticación de producción: identidad por cabeceras es solo desarrollo/demo según configuración. No usarla como control de acceso de producción.
- No se añadió una pantalla específica para administrar aulas/membresías; sus endpoints backend existen. Las pantallas frontend existentes de actividades, entregas y sincronización se conservaron.
- Pruebas offline entre navegadores/dispositivos y reconexión en una red real requieren validación manual.
- No se ejecutó todavía en este punto la prueba de frontend/build sobre el árbol integrado; el resultado se anotará solo después de correr los comandos.
