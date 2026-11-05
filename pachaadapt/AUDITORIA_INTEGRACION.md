# Auditoría de integración PACHAADAPT

**Alcance:** revisión de la carpeta extraída `Downloads/pachaadapt/pachaadapt`, sin desarrollar nuevas funciones del integrante 3. El ZIP original `pachaadapt(2).zip` no estaba presente; se recibió su carpeta descomprimida. Se creó una copia de seguridad antes de auditar.

## Estado inicial

El proyecto contiene frontend React/TypeScript/Vite, API FastAPI, persistencia SQLite y módulos de los integrantes 1, 2, 3 y 4. La API conecta rutas de materiales/adaptaciones, actividades/entregas/sincronización y preferencias/documentos/chat/informes. La interfaz ya tiene páginas para esas áreas. El frontend tiene IndexedDB para caché, recursos y operaciones pendientes; existe otro almacén IndexedDB para adaptaciones/borradores.

## Lo que ya funciona (verificado en código y pruebas)

- Reconexión automática observada por el frontend y envío de operaciones pendientes por `/api/v1/synchronization/push`; hay botón manual y contadores.
- UUID de operación, idempotencia por actor+hash de payload, verificación de `base_version`, respuesta de conflicto servidor/local y backoff ante fallos de red/servidor.
- Caché offline de listados de actividades/materiales, descarga de recursos same-origin a IndexedDB, cola de entregas, filtro por perfil.
- Procesamiento de PDF/TXT y adaptaciones disponibles en servidor; la interfaz restringe estas operaciones cuando no hay conexión y describe capacidades faltantes sin fingir disponibilidad offline.
- SQLite compartida configurada y migraciones al arranque; rutas para revisar permisos según identidad disponible.
- Documentos editables con versiones, restauración y control de versión; preferencias e informes/chat muestran dependencias externas no configuradas.
- La identidad actual es de demostración mediante cabeceras; no constituye autenticación de producción.

## Hallazgos y límites

1. **Persistencia local reparada en actividades/materiales.** `Actividades.tsx` guarda y recupera borradores por usuario/actividad y los limpia cuando la respuesta se entrega a la cola durable o recibe respuesta del servidor. `Materiales.tsx` ahora guarda/recupera adaptaciones por usuario/material/tipo en IndexedDB. El archivo original subido y el texto de extracción no se conservan offline: la pantalla lo explica.
2. **Disponibilidad de recursos del catálogo.** `cache-manager.ts` precarga recursos same-origin a `localDB.assets`; `Catalogo.tsx` sí consulta `getAsset` y abre la copia local. Enlaces externos no se cachean localmente.
3. **Rechazos definitivos preservados.** `sync-queue.ts` mantiene la respuesta en IndexedDB con estado de rechazo, la excluye de reintentos automáticos, la presenta en la pantalla de sincronización y permite reintento explícito con nuevo UUID. No se pierde silenciosamente.
4. **Alcance de sincronización acotado.** El push sincroniza entregas; el pull actualiza listados según permisos; no es un mecanismo universal para materiales/adaptaciones.
5. **Autorización parcialmente endurecida, producción aún bloqueada.** Se restringió el listado/detalle de actividades y el pull de entregas para docentes a las actividades propias. Se mantiene el riesgo: cabeceras de desarrollo son alterables, no hay matrícula/relación estudiante-aula, los estudiantes ven actividades publicadas sin comprobar pertenencia, y admin conserva alcance amplio. No usar datos reales ni exponer a Internet antes de integrar autenticación y membresías reales.
6. **Lote atómico.** `/synchronization/push` procesa el lote en una sola transacción SQLite; prueba de regresión comprueba rollback si una operación posterior es inválida.
7. **Revisión docente protegida.** Si una entrega ya fue `reviewed` o `returned`, una nueva operación de sync da conflicto con versión local/servidor y no sustituye silenciosamente la respuesta/revisión.
8. **Cobertura de campo pendiente.** Las suites no prueban un navegador real en desconexión/recarga/reconexión ni dispositivos concurrentes; las pruebas actuales comprueban unidad/API vía TestClient y contratos.
9. **Esquemas.** `database/schema.sql` es nota de referencia; SQLite se aplica desde migraciones en `database/migrations/integrante4/` y migraciones del módulo. Documentación heredada contiene una ruta de migración equivocada; PostgreSQL sigue siendo referencia no activada.

## Integrante 3 (auditoría preparatoria)

Existen pantallas, servicios y rutas para asistente, documentos, preferencias e informes, incluidos controles de acceso y persistencia/versionado. Las rutas están registradas en `main.py`. Persisten puertos pendientes: proveedor IA, procesador documental y fuente de resultados; las pantallas los presentan como no configurados. No se añadieron funciones nuevas del integrante 3.

## Archivos modificados

- `backend/app/api/v1/assignments.py`: docentes solo listan/consultan sus actividades.
- `backend/app/api/v1/synchronization.py`: pull para docentes limitado a actividades propias; push usa una transacción única por lote.
- `backend/app/services/sync_service.py`: conflicto explícito para proteger entregas revisadas/devueltas.
- `backend/tests/test_workflows.py`: regresiones para aislamiento, revisión preservada y atomicidad.
- `frontend/src/pages/Actividades.tsx`: persistencia/restauración de borradores por perfil y actividad.
- `frontend/src/pages/Materiales.tsx`: persistencia/restauración de adaptaciones en IndexedDB.
- `frontend/src/offline/local-db.ts`, `sync-queue.ts`, `frontend/src/context.tsx`, `frontend/src/pages/Sincronizacion.tsx`: estado persistente de rechazadas y reintento manual.
- `frontend/tests/sync-queue.test.ts`: prueba de rechazo retenido, no reintento automático y reintento explícito.
- Los cuatro informes de integración.

No se añadieron migraciones ni se alteraron credenciales. Las dependencias instaladas localmente generaron `frontend/node_modules` y `frontend/dist`; no incluirlos en ZIP.

## Preparación

Se corrigieron borradores/adaptaciones locales, rechazos descartados, acceso teacher cross-records, atomicidad de lote y sobrescritura de revisión. La base se puede usar como prototipo local y para iniciar la siguiente fase del integrante 3, pero no para datos reales/producción: faltan autenticación real y pertenencia estudiante-aula, además de validación de campo con varios dispositivos. No se inició la fase siguiente.