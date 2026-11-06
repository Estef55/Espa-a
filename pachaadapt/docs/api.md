# Contratos de API — PACHAADAPT

Base local: `http://127.0.0.1:8000/api/v1`. JSON UTF-8. Errores FastAPI usan
`{"detail": ...}`. La identidad de cabecera es exclusivamente demostrativa:
`X-User-Id` y `X-Role` (`teacher`, `student`, `admin`) solo funcionan cuando
`PACHAADAPT_I3_DEV_AUTH=1`; sin autenticación/resolvedor configurado la API
protegida responde 503/401 según el módulo. No es autenticación de producción.

## Aulas
- `POST /classrooms` (teacher/admin): `{"name":"..."}` -> 201 con `id`, `teacher_id`, `is_demo`.
- `GET /classrooms`: docente ve solo sus aulas; estudiante solo las aulas donde está inscrito; admin todas.
- `POST /classrooms/{id}/members` (teacher/admin): `{"user_id":"...","role":"student"}` -> 201. El usuario estudiante debe existir y estar activo; no se crean cuentas a partir de una cabecera. No se mezclan miembros reales y demo. El docente solo gestiona su aula.

## Actividades
- `POST /assignments` (teacher/admin): `title`, `instructions?`, `classroom_id?`, `material_id?`, `due_at?`, `status?` (`draft|published|closed`). -> 201.
- `GET /assignments[?classroom_id=...]`: estudiante ve publicadas de aulas donde está inscrito (y actividades heredadas sin aula); docente solo las propias; admin todas.
- `GET /assignments/{id}`: permisos equivalentes.
- `PUT /assignments/{id}?expected_version=N`: actualiza y aumenta `version`; versión obsoleta -> 409.

## Entregas y revisión
- `POST /submissions` (student): `assignment_id`, `answer` (1–50000 caracteres), `client_updated_at?`. Una entrega por estudiante/actividad; una nueva respuesta actualiza el registro y `server_version`.
- `GET /submissions[?assignment_id=...]`: estudiante solo sus entregas; docente solo entregas de actividades propias; admin global.
- `PATCH /submissions/{id}/review?status=reviewed|returned&score=N&max_score=M&validation_status=pending|validated|rejected` (teacher/admin). Puntuación y máximo deben enviarse juntos, con `0 <= score <= max_score` y máximo positivo. Para `validated` se exige `status=reviewed` y puntuación explícita. Valor por defecto `validation_status=pending`; revisar no equivale a validar. Un resultado ya validado queda bloqueado frente a modificaciones posteriores (409).

## Sincronización offline
- `POST /synchronization/push`: array de hasta 100 operaciones `{operation_id: UUID, entity_type:"submission", entity_id: assignment_id, payload:{assignment_id, answer, base_version, client_updated_at?}}`.
- Respuesta: `{results:[{operation_id,status:"acknowledged|conflict|rejected",...}],received,acknowledged,conflicts,rejected}`. Repetir UUID + contenido devuelve resultado original; UUID de otro actor o con otro contenido -> 409. Operaciones inválidas -> 422; lotes >100 -> 413.
- `GET /synchronization/pull?since=ISO/SQLite timestamp`: asignaciones/entregas visibles al actor.
- `GET /synchronization/status`: estado del servidor y conteo técnico de operaciones recibidas.

## Informes
- `POST /reports`: criterios opcionales `topic`, `group`, `date_from`, `date_to`, `pass_threshold_pct`, `include_ai_interpretation`. Solo incluye entregas `reviewed`, `validation_status=validated`, con `score`, `max_score` y `reviewed_at` válidos, dentro de aulas del docente autenticado y del mismo ámbito demo/real. Los informes no mezclan datos ficticios y reales.
- `GET /reports`, `GET /reports/{id}`, `GET /reports/{id}/markdown`: solo informes del docente propietario.
- Sin fuente de datos disponible: 503. Datos insuficientes: informe `insufficient_data`, no se inventan resultados.

## Materiales
- `POST/GET /materials` y `/materials/{id}`: archivos PDF/TXT del integrante 2; propiedad por usuario.
- `/material-library`: catálogo de recursos URL del integrante 4; estudiantes ven solo publicados, docentes solo propios.

Los endpoints de materiales, documentos, preferencias y chat del integrante 3 mantienen sus contratos existentes. Consultar `/docs` para el OpenAPI efectivo.

## Materiales y adaptaciones guardadas (Integrante 2)
Solo docente; cada docente ve únicamente lo suyo (otro docente → 404).

| Método y ruta | Descripción |
|---|---|
| `GET /api/v1/materials` | Lista con estado de procesamiento |
| `GET /api/v1/materials/capabilities` | Qué ofrece realmente el servidor (OCR, audio, adaptaciones) |
| `GET /api/v1/materials/{id}/original` | Archivo original sin modificar |
| `GET /api/v1/materials/{id}/text` | Texto organizado en bloques |
| `POST /api/v1/materials/{id}/extract` / `/adapt` | Extraer / generar y **guardar** una adaptación |
| `GET /api/v1/materials/{id}/adaptations[/{aid}]` | Adaptaciones guardadas |
| `POST …/adaptations/{aid}/review` | `{approved}` revisión docente |
| `POST …/adaptations/{aid}/links` | `{target_type: document\|assignment, target_id}` |
| `GET …/adaptations/{aid}/export?format=html\|txt` | Descarga etiquetada |
| `GET …/adaptations/{aid}/audio` | WAV (solo si hay motor de voz) |

Las rutas sin estado de `/api/v1/adaptations/...` (organizadores, Braille, audio con guion, traducción con proveedor, imágenes, subtítulos) siguen funcionando igual; las de arriba son adicionales y no las reemplazan.
