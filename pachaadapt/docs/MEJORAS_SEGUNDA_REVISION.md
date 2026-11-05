# Segunda revisión técnica — Integrante 4

## Correcciones aplicadas

1. La fuente `SQLiteLearningDataSource` se mantiene conectada durante el ciclo de vida de FastAPI y filtra por docente, aula y ámbito `is_demo` en las tres entidades (aula, actividad y entrega).
2. La carga de demostración conserva los identificadores usados por el frontend (`demo-teacher`, `demo-student`) y ahora aborta si alguno ya pertenece a una cuenta real. No actualiza ni reclasifica usuarios reales.
3. La creación de aulas hereda el ámbito demo/real del docente cuando existe en SQLite.
4. La matrícula exige que el estudiante exista y esté activo; no crea cuentas a partir de un ID recibido en una petición. También impide mezclar estudiantes demo con aulas reales y viceversa.
5. Las actividades y entregas heredan el ámbito demo/real. Se bloquea la mezcla de materiales, aulas y actividades de distintos ámbitos.
6. Las actualizaciones de entregas pendientes limpian puntuaciones y validaciones anteriores antes de aceptar una nueva respuesta.
7. La revisión no permite modificar un resultado que ya quedó validado.
8. La sincronización offline aplica la misma protección de resultados validados y conserva el ACK/conflicto/rechazo idempotente.
9. Se corrigieron dos pruebas de integración que esperaban el comportamiento previo: conexión de la fuente de informes y autenticación demo explícitamente desactivada en la prueba de identidad.

## Verificación reproducible

- Backend + integración: `python -m pytest -q ./backend/tests ./tests` → **105 passed**, 1 warning externo de deprecación AnyIO/pytest.
- Regresión estándar: `python -m unittest discover -s tests -t . -q` → **85 OK**.
- Frontend: `npm test` desde `frontend/` → **33 passed**.
- Compilación frontend: `npm run build` → correcta, 67 módulos transformados.
- Sintaxis Python: `python -m compileall -q ai backend scripts database tests` → correcta.
- Seed: carga repetida, rechazo de colisión real y reinicio `--reset` comprobados en SQLite temporal.
- Se extrajo el ZIP final en una carpeta limpia y se repitieron las pruebas Python, frontend y build; los resultados coinciden.

## Límites que se mantienen

- No existe autenticación de producción; las cabeceras son solo para desarrollo local.
- SQLite continúa siendo el motor operativo. PostgreSQL sigue siendo DDL de referencia.
- La prueba PWA offline entre dispositivos físicos requiere validación manual en navegador y red local.
