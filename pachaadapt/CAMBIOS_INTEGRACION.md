# Cambios de integración

## Resultado
Se aplicaron correcciones puntuales tras reproducir tres defectos de backend con pruebas fallidas antes de corregirlos: exposición de actividades/entregas entre docentes, sobrescritura de una revisión docente y escritura parcial de lotes sync. También se conectaron el borrador local de actividad y el almacén IndexedDB de adaptaciones; los rechazos definitivos ahora quedan preservados con reintento explícito. No se desarrollaron nuevas funciones del integrante 3 ni se rediseñó la interfaz.

## Archivos añadidos

- `AUDITORIA_INTEGRACION.md`: estado inicial, funcionalidades, defectos y límites.
- `CAMBIOS_INTEGRACION.md`: este registro.
- `RESULTADOS_PRUEBAS_INTEGRACION.md`: comandos y resultados efectivos.
- `PENDIENTES_INTEGRANTE3.md`: inventario preparatorio y dependencias.

## Archivos funcionales modificados

- `backend/app/api/v1/assignments.py`: consulta/listado docente acotado a actividades propias.
- `backend/app/api/v1/synchronization.py`: pull docente acotado y lote push atómico.
- `backend/app/services/sync_service.py`: conflicto ante reenvío de entregas revisadas/devueltas.
- `backend/tests/test_workflows.py`: 3 regresiones de aislamiento, conflicto de revisión y atomicidad.
- `frontend/src/pages/Actividades.tsx`: guarda/restaura y limpia borradores locales.
- `frontend/src/pages/Materiales.tsx`: persiste y recupera adaptaciones por actor/material/tipo.
- `frontend/src/offline/local-db.ts`, `sync-queue.ts`, `context.tsx`, `pages/Sincronizacion.tsx`: retención de rechazos no reintentables y reintento manual con UUID nuevo.
- `frontend/tests/sync-queue.test.ts`: rechazo persistente, no reintento automático, retry explícito y ACK final.

## Protección y dependencias locales
La copia de seguridad previa se conservó. Se generó `../pachaadapt_integrado_20261102.zip` con el código fuente y los cuatro informes; omite `storage/`, `.env`, `.venv`, `node_modules`, `dist`, bases locales, logs y cachés. ZIP verificado: 197 archivos, sin entradas prohibidas. Extracción limpia reproducida desde el ZIP: 77 pruebas unittest, 14 pytest backend, `npm ci`, build de producción y 32 pruebas frontend pasan. El ZIP ya se probó desde su extracción limpia.

## Compatibilidad

No se añadieron rutas ni migraciones; se conservan los contratos existentes. El pull y lectura de actividades ahora aplican alcance del docente, y la vista de sync usa el registro de rechazo para intervención explícita. `retryRejected` crea UUID nuevo porque el servidor almacena el resultado rechazado como idempotente por UUID. La autenticación y membresía de estudiantes siguen sin resolverse.