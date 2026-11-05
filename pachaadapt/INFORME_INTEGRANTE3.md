# Informe técnico — Integrante 3 PACHAADAPT

## Estado de entrega

Se completaron cambios de integración y persistencia offline del módulo 3, preservando las páginas y servicios existentes. Se verificaron las suites automatizadas y se hicieron pruebas HTTP de la aplicación FastAPI con una SQLite temporal. **No se declara finalización integral**: no hay proveedor externo de IA configurado ni una fuente de resultados académicos reales que permita generar informes con calificaciones. Estas limitaciones quedan activas y documentadas, sin sustituirlas por datos ficticios.

## Funcionalidades existentes

- Pasarela desacoplada `chat/completions` con clave solo en backend, timeout y errores de red/proveedor controlados; sin configuración devuelve error 503, sin respuesta inventada.
- Documentos editables con propietario, historial de versiones, restauración, archivado lógico y control optimista `expected_version`.
- Preferencias de docente persistidas y separadas por identidad.
- Servicio de análisis que valida registros, excluye los inválidos, calcula métricas agregadas y separa observaciones/recomendaciones de una interpretación IA opcional.
- Rutas API registradas junto a materiales, adaptaciones, actividades, entregas y sincronización offline ya existentes.

## Auditoría inicial realizada sobre el ZIP solicitado

Se verificó el ZIP de entrada, se conservó una copia intacta y se extrajo a una carpeta de trabajo separada. Antes de editar, pasaron 82 pruebas `unittest`, 14 pruebas backend, 33 pruebas frontend y el build de producción. La inspección confirmó que el código existente ya tenía persistencia de conversaciones/documentos/preferencias, propietario por docente, control de versión, contexto de documentos, y pasarela genérica compatible con OpenAI. Dos brechas corregibles dentro del Integrante 3: el selector solo aceptaba `openai_compatible` (no las etiquetas explícitas `openai`, `groq`, `ollama`) y un HTTP 429 aparecía como fallo genérico sin explicar límite/cuota. La conexión de informes reales no puede resolverse con el esquema actual: las entregas contienen respuesta textual/estado, pero no resultado numérico revisado ni asociación autorizada de grupo/matrícula; no se infiere una nota a partir del texto.

## Cambios completados en esta continuación

- `ai/model_gateway.py`: `PACHAADAPT_AI_PROVIDER` ahora acepta `openai`, `groq`, `ollama` y `openai_compatible` usando un mismo adaptador OpenAI-compatible, endpoint explícito y modelo explícito. El identificador configurado se devuelve como etiqueta del proveedor. No se inventan URLs predeterminadas ni se afirma compatibilidad con APIs propietarias que no expongan `/chat/completions`.
- Errores HTTP 429 se presentan como límite/cuota con instrucción de reintentar más tarde; los cuerpos de respuesta HTTP de error se cierran sin leerlos. Así se evitan fugas de recursos y no se registra ni refleja contenido remoto/credenciales.
- `tests/ai/test_assistant.py`: cobertura con un servidor HTTP de prueba local para selección de los cuatro aliases, error 429 seguro/accionable y cierre del cuerpo HTTP de error.
- `CONFIGURACION_SERVICIOS_IA.md`: variables, proveedores compatibles, uso de URL/modelo explícitos y reinicio del backend documentados.

## Funcionalidades completadas en la fase anterior

- **Integración integrante 2 → documentos/asistente:** se añadió `MaterialDocumentProcessor` al arranque FastAPI. Reutiliza el servicio y almacenamiento de materiales existente, extrae texto mediante el procesador existente cuando corresponda, conserva la propiedad del material y no activa OCR de forma implícita. La importación crea un documento editable con el texto extraído; el asistente puede consultar ese documento sujeto a la propiedad.
- **Documentos offline:** la interfaz conserva borradores en IndexedDB por usuario/documento y versión base. Se muestran como locales y pendientes, no como sincronizados. Al volver a tener conexión el docente debe guardarlos explícitamente en el servidor. Los conflictos de versión presentan las versiones disponibles y requieren decisión; la cola de entregas de los integrantes 1/4 no se utiliza ni se modifica.
- **Asistente → documentos:** una propuesta generada puede revisarse y editarse; solo la acción explícita del docente la guarda como documento.
- **Preferencias:** se añadió eliminación de preferencias personalizadas, que restaura los valores por defecto sin registrar esos defaults como cambios hechos por el docente.
- **Informes:** se inspeccionaron las fuentes existentes; se normalizaron a UTC las comparaciones de fechas y el filtro final inclusivo de una fecha ISO diaria. Se conserva la desactivación cuando no hay fuente real; no se interpreta el texto de una entrega como calificación ni se inventan resultados. La estructura vigente de integrante 4 contiene respuestas y estados (`submitted`, `reviewed`, `returned`), pero no una calificación numérica, rúbrica confirmada, tema/resultado de aprendizaje ni una relación matrícula-aula suficiente para autorizar agregados pedagógicos.
- **Compatibilidad web:** se habilitó el método `DELETE` en CORS para que el borrado de preferencias funcione también desde el frontend entre orígenes permitidos. Se añadió una prueba de preflight: primero falló con `400 Disallowed CORS method` y, tras el ajuste, pasó con `200`.

## Integración con integrante 4 y preservación

No se alteraron las rutas ni la cola de sincronización, los UUID, la idempotencia, los reintentos, los conflictos ni la protección de entregas revisadas. Los informes no cuentan registros pendientes del dispositivo como resultados confirmados. Las suites previas de sincronización, recursos y entregas permanecen aprobadas. La inspección de `submissions` confirma que, para conectar informes, primero hace falta incorporar un esquema de calificación revisada y una relación verificable docente/grupo/estudiantes; no se simuló esa dependencia.

## Archivos modificados o añadidos

- `ai/model_gateway.py`, `tests/ai/test_assistant.py` — aliases `openai`/`groq`/`ollama` sobre el protocolo común, etiqueta de proveedor, manejo explícito HTTP 429, cierre de cuerpos HTTP de error y regresiones automatizadas.
- `CONFIGURACION_SERVICIOS_IA.md` — proveedores, variables de entorno, endpoint/modelo explícitos y límite de compatibilidad documentados.
- `backend/app/services/material_integration.py` — adaptador hacia materiales existentes.
- `backend/app/main.py` — registro aditivo del adaptador en el lifespan, conservando routers existentes.
- `backend/app/services/report_service.py`, `tests/ai/test_reports.py` — normalización UTC y fecha final inclusiva con prueba de regresión.
- `backend/app/main.py`, `tests/backend/test_routes_wiring.py` — CORS habilita `DELETE` y prueba HTTP real del preflight de preferencias.
- `tests/ai/test_material_integration.py` — extracción e aislamiento por propietario.
- `ai/assistant/preference_manager.py`, `backend/app/api/v1/preferences.py` — limpieza de preferencias.
- `frontend/src/services/preferences.service.ts`, `frontend/src/pages/Preferencias.tsx` — acción UI para volver a defaults.
- `frontend/src/services/ai.service.ts`, `frontend/src/pages/Asistente.tsx` — guardado explícito de propuesta como documento revisado.
- `frontend/src/offline/adaptation-store.ts`, `frontend/src/pages/Documentos.tsx` — borrador local, snapshot, recuperación y manejo de conflictos.
- `frontend/tests/adaptations.test.ts`, `frontend/tests/services.test.ts` — pruebas de aislamiento/persistencia de borradores y servicios.
- `tests/ai/test_preferences.py`, `tests/backend/test_routes_wiring.py` — cobertura de preferencias y preflight CORS.
- `PENDIENTES_INTEGRANTE3.md`, `docs/integrante3/IMPLEMENTACION.md` — estado actualizado de dependencias, integraciones y limitaciones.
- `INFORME_INTEGRANTE3.md`, `RESULTADOS_PRUEBAS_INTEGRANTE3.md`, `CONFIGURACION_SERVICIOS_IA.md` — documentación de esta entrega.

No se modificó la arquitectura de almacenamiento ni se cambió SQLite. El backup original está conservado aparte del ZIP fuente.

## Dependencias externas y limitaciones

1. **Proveedor IA:** no hay proveedor externo ni credencial configurada en este entorno. Las pruebas de proveedor ejercitan un servidor HTTP local de prueba; no demuestran conectividad/validez de una cuenta real.
2. **Informes:** siguen sin estar disponibles en el runtime (503 controlado) hasta conectar una fuente de resultados confirmados, autorizados y calificados. Los tests de análisis usan registros controlados como fixtures, no representan resultados escolares reales.
3. **Identidad:** las cabeceras de demostración y el selector de perfil no son autenticación. Hace falta integrar un proveedor de identidad institucional antes de producción.
4. **Offline de documentos:** se conserva el borrador en IndexedDB y se compara la versión base, pero no existe sincronización de documentos con la cola del servidor. El docente debe confirmar el guardado en línea. La prueba automatizada de almacenamiento usa la interfaz KV de las pruebas; no reemplaza una prueba de navegador/dispositivo real.
5. **Prueba integral:** las pruebas y el smoke test HTTP no equivalen a prueba de campo, despliegue, multi-dispositivo, proveedor externo o revisión pedagógica docente.

## Veredicto

Los cambios son aptos para revisión y para avanzar a pruebas integrales controladas de los flujos disponibles; no se debe etiquetar el prototipo como listo para producción ni afirmar que el informe pedagógico usa calificaciones reales hasta resolver las dependencias anteriores.