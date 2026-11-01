# Funcionamiento offline

## Datos locales
- `cache-manager.ts` conserva el último listado de actividades recibido.
- `local-db.ts` guarda caché y cola de entregas en IndexedDB.
- `service-worker.js` almacena la estructura de la PWA y presenta `offline.html` cuando no hay red.

## Flujo de entrega
1. El estudiante escribe su respuesta.
2. Si hay conexión, se envía al endpoint de entregas.
3. Si no hay conexión o falla la solicitud, se guarda una operación con UUID, versión base y fecha local.
4. Al volver la conexión se envía la operación a `/api/v1/synchronization/push`.
5. El servidor valida la actividad, rol y versión; registra el resultado idempotente y devuelve confirmación.
6. Si hay diferencia de versión, el servidor devuelve el estado del servidor y el contenido local. El usuario decide qué versión conservar.

## Reintentos y duplicados
- Se conserva la operación pendiente ante errores de red.
- Se aplica backoff exponencial limitado para no saturar redes lentas.
- Reutilizar el mismo UUID y contenido produce la misma respuesta del servidor.
- Reutilizar un UUID con contenido distinto devuelve conflicto HTTP 409.

## Prueba de campo
Usar dos dispositivos conectados a la misma red local. Publicar una actividad, abrirla en ambos, desconectar uno de los dispositivos, enviar una respuesta en ambos y volver a conectar el dispositivo offline. Verificar el contador de pendientes, la confirmación del servidor y la pantalla de resolución de conflictos.
