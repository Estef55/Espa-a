# Verificación de requisitos — Integrante 4

## Resultado de verificación de esta entrega

La implementación cubre los flujos centrales solicitados en la guía. La persistencia ejecutable y probada de esta entrega es SQLite; los esquemas y migraciones PostgreSQL 15+ están versionados, pero no hay un adaptador PostgreSQL conectado a la API. Por ello no se debe presentar PostgreSQL como motor probado en ejecución.

| Requisito de la guía | Evidencia en el proyecto | Estado |
|---|---|---|
| Base de datos inicial y migraciones versionadas | `database/schema.sql`, migraciones SQLite 001–003 y PostgreSQL 001–003 | Implementado; SQLite probado, PostgreSQL preparado a nivel SQL |
| Asignaciones, entregas y registro de respuestas | API `/api/v1/assignments` y `/api/v1/submissions` | Implementado y probado |
| API para validar, guardar y consultar resultados | FastAPI, validación Pydantic y `/docs` | Implementado y probado |
| PWA y almacenamiento local de materiales/respuestas | Manifest, Service Worker, IndexedDB y caché de recursos same-origin | Implementado; prueba manual de navegador requerida |
| Cola, reintentos, confirmaciones y deduplicación | UUID idempotente, ACK, reintentos exponenciales con jitter, límite de lote | Implementado; reintento en navegador requiere prueba manual |
| Conflictos entre dispositivo y servidor | `base_version`, `server_version`, resolución en interfaz | Implementado y probado en API |
| Estado de sincronización | Estado online/offline, pendientes, sincronizando y última confirmación | Implementado en interfaz |
| Registros, copias y recuperación | Log JSON consola/archivo con rotación, `audit_log`, backup y restore con integridad | Implementado y probado |
| Permisos, integridad y red local | Roles, aislamiento por propietario, claves foráneas, Vite proxy y pruebas API | Implementado y probado en API; prueba entre dispositivos requiere red física |

## Pruebas automatizadas

Desde `backend/` ejecutar `pytest -q`. La suite de esta entrega contiene 12 pruebas automatizadas: asignaciones, permisos, entregas, versionado, auditoría, sincronización idempotente, pull/status, límites de lote, backup y restauración. En el entorno de preparación se obtuvo `12 passed`.

## Validación manual pendiente en el equipo de demostración

1. Ejecutar `npm install` y `npm run build` en `frontend/` con conexión disponible. La compilación del frontend no pudo verificarse en el entorno de preparación porque el registro npm agotó el tiempo de conexión; el comando debe ejecutarse en el equipo de entrega.
2. Abrir la aplicación con `npm run dev` y comprobar creación de actividad y entrega.
3. En DevTools, activar Offline, guardar una respuesta, confirmar que aumenta el contador pendiente y volver a Online.
4. En modo producción (`npm run build` y `npm run preview`), comprobar el Service Worker y la página offline.
5. Para una prueba real de red local, abrir Vite desde otro equipo usando la IP LAN del equipo servidor. El Service Worker requiere localhost o HTTPS en los navegadores modernos.

## Alcance y seguridad

La autenticación actual por cabeceras `X-User-Id` y `X-Role` es deliberadamente de demostración para laboratorio/red local. No publicar la API directamente en Internet. Antes de un despliegue institucional deben incorporarse autenticación real, sesiones/tokens, HTTPS y validación de pertenencia a aulas.

PostgreSQL está preparado mediante DDL y migraciones numeradas; el backend operativo de esta entrega usa SQLite. La activación de PostgreSQL como motor requiere desarrollar y probar un adaptador de persistencia específico.
