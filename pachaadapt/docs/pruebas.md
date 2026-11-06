# Guía de pruebas de aceptación

## Pruebas automatizadas del backend
En PowerShell:
```powershell
cd backend
pytest -q
```

## Pruebas del frontend
```powershell
cd frontend
npm test
```
Usa el ejecutor nativo de Node (`node --test`, versión 22.6 o superior) y no añade dependencias. Comprueban que cada servicio llama al endpoint, método y cuerpo que expone el backend, la normalización de errores (permisos, conflictos, 503, red), los permisos por perfil, la navegación, el CSV, la resolución de conflictos y el índice local de materiales.

Además, `tests/frontend/test_frontend_contract.py` (se ejecuta con el resto de `unittest`) verifica leyendo el código que todo endpoint que llama el frontend existe en los routers del backend.

## Prueba funcional en navegador
1. Inicia el backend y el frontend.
2. Selecciona el perfil Docente y crea una actividad.
3. Cambia a Estudiante y envía una respuesta.
4. Cambia a Docente y confirma que la entrega aparece.
5. Marca la entrega como revisada.
6. Con el perfil Docente abre «Archivos y adaptación», sube un TXT, extrae el texto, genera una adaptación y guárdala como documento; edítala en «Documentos editables» y restaura una versión anterior.
7. Comprueba que el Asistente y los Informes explican qué falta configurar si el servidor no tiene proveedor de IA o fuente de resultados.
8. Sin conexión (DevTools > Network > Offline), envía una respuesta como estudiante y comprueba en «Conexión y sincronización» que queda pendiente y se envía al volver la red.

## Prueba de operación offline (PWA)
Para probar el Service Worker, usa compilación de producción:
```powershell
cd frontend
npm run build
npm run preview
```
Abre la URL local que Vite indique, carga la página al menos una vez y luego activa el modo Offline desde DevTools > Network. La caché de actividades y las respuestas pendientes usan IndexedDB. Al volver a Online, la cola reintenta la sincronización.

## Prueba de respaldo
Desde la raíz:
```powershell
python scripts/backup.py
```
Comprueba que se creó un archivo en `backups`. Para probar restauración, detén el backend y ejecuta:
```powershell
python scripts/restore.py backups\NOMBRE_DE_LA_COPIA.sqlite3
```
La base anterior se guarda con extensión `.before-restore`.

## Integrante 2 (materiales y adaptaciones guardadas)
`python -m unittest discover -s tests/integrante2 -t .` (38 pruebas; 3 de ellas, las HTTP de extremo a extremo, requieren FastAPI y se omiten sin él) y `cd frontend && npm test` (incluye `tests/materials.test.ts`).
