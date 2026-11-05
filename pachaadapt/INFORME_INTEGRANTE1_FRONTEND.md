# Integrante 1 — Diagnóstico e implementación frontend

## Base de trabajo y auditoría inicial

Base oficial: `pachaadapt_integrante3_fase2_integrado_i4.zip` (205 entradas, ZIP válido). Se extrajo en un árbol de trabajo separado; no se reemplazó la base ni se modificó el ZIP original. Antes de cambios, la regresión fue: pytest **105 passed** (una advertencia externa de AnyIO/pytest), unittest **85 OK**, frontend **33 passed** y build Vite correcto con **67 módulos**.

La revisión de `App.tsx`, `context.tsx`, páginas, servicios, `offline/`, estilos y documentación encontró que ya existían navegación por hash, permisos por perfil de demostración, indicadores de conexión, PWA/IndexedDB, cola de sincronización y pantallas React adaptables. Actividades, catálogo, materiales, documentos, IA, preferencias e informes estaban conectados a servicios reales. Se preservaron esos flujos y la paleta/estilos ya existentes.

Dos huecos concretos impedían completar la demostración educativa: (1) el backend I4 aceptaba calificación y validación, pero la página de entregas solo enviaba `status`, por lo que la docente no podía generar resultados válidos para informes; (2) existía `GET /classrooms`, pero el panel inicial no mostraba las aulas del perfil. También la pantalla permitía editar y reenviar entregas ya revisadas/devueltas aunque el backend las bloquea.

## Cambios implementados

- **Revisión docente:** se agregaron campos de puntuación y máximo; validación local de rango/formato; opción de guardar una revisión pendiente y de validar explícitamente una calificación. La validación pide confirmación, indica que el resultado alimentará informes y respeta el bloqueo irreversible del backend.
- **Estudiante:** se muestran calificaciones solo cuando están validadas. Si una entrega revisada/devuelta está bloqueada por el contrato de servidor, se explica y se desactivan los campos y el reenvío, en vez de provocar un error 409 evitable.
- **Aulas en inicio:** se consulta el endpoint autorizado `/api/v1/classrooms` con la identidad activa y se muestran estados de carga, error, vacío y listado. Es una vista solo lectura; no crea usuarios ni inscribe estudiantes.
- **Servicios y tipos:** se añadió un cliente de revisión alineado con FastAPI y campos de puntuación/validación en el tipo `Submission`; el cliente de aulas usa exclusivamente el endpoint existente.
- **Documentación:** se corrigieron descripciones antiguas de conexiones de informes/materiales y se documentó el alcance real, incluyendo la ausencia de gestión de aulas y reapertura de entregas.

## Archivos modificados

- `README.md`
- `docs/frontend_interfaz.md`
- `frontend/src/lib/types.ts`
- `frontend/src/pages/Actividades.tsx`
- `frontend/src/pages/Entregas.tsx`
- `frontend/src/pages/Inicio.tsx`
- `frontend/src/services/assignments.service.ts`
- `frontend/tests/lib.test.ts`
- `frontend/tests/services.test.ts`

## Archivos nuevos

- `frontend/src/lib/submissions.ts`
- `frontend/src/services/classrooms.service.ts`
- `frontend/src/services/review.service.ts`
- `INFORME_INTEGRANTE1_FRONTEND.md`

## Conservación e integración

No se alteraron rutas FastAPI, contratos de persistencia, reglas de sincronización, `sync-queue.ts`, `local-db.ts`, Service Worker, identidad demo ni módulos I3 de IA/documentos/preferencias/informes. Las calificaciones usan los parámetros que I4 ya expone (`score`, `max_score`, `validation_status`); solo las validadas aparecen como resultados reportables. El panel de aulas solo usa el GET existente.

## Pruebas

- Base previa: `pytest` **105 passed**, `unittest` **85 OK**, `npm test` **33 passed**, build **67 módulos**.
- Integrado: `python -m pytest -q ./backend/tests ./tests` → **105 passed**, con una advertencia externa de deprecación AnyIO/pytest.
- `python -m unittest discover -s tests -t . -q` → **85 OK**.
- `npm test` → **36 passed** (incluye pruebas nuevas para contrato de calificación, consulta de aulas y bloqueo de reenvío según estado).
- `npm run build` → correcto, **70 módulos transformados**.
- `python -m compileall -q ai backend scripts database tests` → correcto.
- Las mismas pruebas se repitieron sobre una extracción limpia del ZIP final: **105 pytest**, **85 unittest**, **36 pruebas frontend** y build Vite correcto (70 módulos). `npm ci` instaló 69 paquetes; auditoría reportó 0 vulnerabilidades.
- La prueba automatizada de revisión verifica el PATCH con nota y `validation_status=validated`; la vista de aula usa el GET existente. No se alteró el contrato/backend.
- Smoke test en navegador local con datos demo aislados: se verificó el aula desde perfiles estudiante y docente; desde Entregas se validó 8/10 y una lectura posterior al endpoint confirmó `status=reviewed`, `validation_status=validated`, `score=8`, `max_score=10`.
- El diagnóstico y cambios corresponden al frontend y a contratos ya existentes; la comprobación de interfaz no equivale a pruebas de conectividad entre dispositivos ni de seguridad de autenticación de producción.

## Limitaciones pendientes

- No existe UI para crear aulas, matricular estudiantes ni gestionar usuarios. El dashboard muestra solamente asociaciones ya persistidas y autorizadas.
- El backend no tiene endpoint para reabrir una entrega revisada/devuelta; por eso no se simula la posibilidad de reenvío.
- No existe autenticación de producción; el perfil sigue siendo demostrativo, tal como indica la interfaz.
- Las pruebas de red offline real, cambio de conectividad y sincronización física entre dispositivos requieren validación manual; las pruebas automatizadas de cola y contratos no sustituyen esa prueba de campo.
