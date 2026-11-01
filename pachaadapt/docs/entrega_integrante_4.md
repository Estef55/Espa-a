# Entrega técnica — Integrante 4

## Objetivo
Mantener integridad de asignaciones, entregas y datos en red local, soportando trabajo sin conexión y recuperación posterior.

## Matriz de requisitos

| Requisito | Implementación verificable |
|---|---|
| Base de datos inicial y migraciones versionadas | `database/schema.sql`, `database/migrations/001_initial_sqlite.sql`, `002_audit_and_sync_indexes.sql`; DDL PostgreSQL versionado en `database/migrations/postgresql/`. |
| Asignación de actividades, recepción de entregas y respuestas | API `/api/v1/assignments` y `/api/v1/submissions`; roles y validación Pydantic. |
| API para validar, guardar y consultar resultados | FastAPI; endpoints documentados en `/docs`; consulta y revisión de entregas. |
| PWA y almacenamiento local de materiales/respuestas pendientes | `frontend/public/manifest.json`, `service-worker.js`, `frontend/src/offline/local-db.ts` e `IndexedDB`. |
| Cola, reintentos, confirmaciones y deduplicación | `sync-queue.ts`, UUID por operación, hash idempotente en servidor y reintentos exponenciales. |
| Conflictos dispositivo/servidor | `base_version` y `server_version`; la interfaz permite conservar servidor o reenviar la respuesta local sobre la versión vigente. |
| Estado de sincronización para docente/estudiante | Indicador online/offline, operaciones pendientes, sincronización manual y avisos de conflicto en `App.tsx`. |
| Registros, copias y recuperación | Logger JSON, tabla `audit_log`, `scripts/backup.py` y `scripts/restore.py`. |
| Permisos, integridad y red local | Pruebas automatizadas para roles, aislamiento de entregas, control de versión, integridad e idempotencia; CORS limitado a orígenes locales configurados. |

## Arquitectura y operación

- Backend: Python + FastAPI.
- Persistencia operativa incluida: SQLite con WAL y claves foráneas.
- Esquema PostgreSQL 15+ y migraciones SQL entregados para migración/despliegue separado.
- Frontend: React + TypeScript + Vite.
- Offline: IndexedDB, Service Worker y cola local de operaciones.

## Cómo probar
1. Iniciar backend y frontend según `README.md`.
2. Entrar como docente y publicar una actividad.
3. Cambiar a estudiante y guardar una respuesta.
4. Consultar la entrega desde el perfil docente.
5. Desconectar la red desde el navegador, guardar una respuesta y verificar que aumente el contador pendiente.
6. Recuperar la conexión o pulsar “Sincronizar ahora”.
7. Para comprobar conflicto, editar la misma entrega desde dos sesiones/dispositivos y sincronizar la copia desactualizada.

## Alcance y limitaciones declaradas
La API operativa de esta entrega usa SQLite. El esquema PostgreSQL está versionado, pero no se incluye un adaptador de conexión PostgreSQL en tiempo de ejecución. Los perfiles y cabeceras son de demostración para red local; requieren autenticación real antes de un despliegue institucional o público.
