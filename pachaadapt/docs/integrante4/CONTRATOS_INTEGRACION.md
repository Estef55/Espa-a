# Contratos de integración — PACHAADAPT

## Principios comunes
- SQLite sigue siendo la persistencia operativa. La migración `004_learning_results_and_demo.sql` es aditiva.
- UUID para entidades/operaciones; timestamps ISO 8601 o timestamp SQLite en `since`.
- No renombrar rutas ni campos existentes sin coordinación. Los campos nuevos son opcionales para clientes anteriores.
- Errores: códigos HTTP estándar y objeto `detail`; `409` para conflicto de versión/idempotencia, `422` para payload inválido, `403` para rol/propiedad.

## I1 — interfaz y API
- Prefijo `/api/v1`; contratos completos en `docs/api.md` y OpenAPI `/docs`.
- Identidad demo: `X-User-Id` + `X-Role`; habilitar localmente con `PACHAADAPT_I3_DEV_AUTH=1`. No usar fuera de local.
- Actividades incluyen `id`, `classroom_id`, `material_id`, `status`, `version`, `created_by`.
- Entregas incluyen `id`, `assignment_id`, `student_id`, `answer`, `status`, `server_version`, `score`, `max_score`, `validation_status`, `reviewed_at`.
- La UI debe tratar `acknowledged` como confirmación de recepción; `conflict` necesita decisión humana; `rejected` se conserva localmente y no es resultado.

## I2 — materiales y adaptaciones
- La carga PDF/TXT sigue en `/api/v1/materials`; sus metadatos tienen `id`, `owner_id`, `filename`, `sha256`, `extracted_text`, `extracted_at`.
- El catálogo de recursos externos está separado en `/api/v1/material-library`.
- Actividades pueden referenciar `material_id` del catálogo. El vínculo es opcional y no copia binarios ni texto extraído.
- Las adaptaciones requieren revisión; `review_required=true` no significa contenido validado/publicado automáticamente.

## I3 — informes y preferencias
- La fuente oficial implementada es `SQLiteLearningDataSource.fetch_records(teacher_id, filters)`.
- Solo consulta entregas revisadas + validadas, puntuación no nula y rango válido, con fecha de revisión, aula y docente propietario. Los identificadores estudiantiles se convierten en referencias opacas.
- Campos de agregación: grupo/aula, tema/material o actividad, score, max_score, fecha de revisión y referencia opaca. No se exportan nombres ni respuestas.
- Entrega pendiente, rechazada, sin puntuación o sin fecha de revisión queda fuera del informe.
- Los informes se persisten en `i3_reports` y se aíslan por `teacher_id`. Preferencias y documentos siguen en tablas `i3_*`; sus contratos previos no cambian.

## I4 — sincronización y datos demo
- IndexedDB conserva cola offline; el servidor mantiene `sync_operations` para idempotencia, `audit_log` para trazabilidad y `server_version` para conflictos.
- Un mismo UUID y payload da la misma respuesta. UUID con payload diferente o perteneciente a otro actor da 409.
- La sincronización no sobrescribe entregas revisadas/devueltas ni resultados validados; las actualizaciones de entregas pendientes limpian cualquier puntuación/validación anterior. Conflictos/rechazos se retienen para resolución.
- Seed: `python database/seed_data.py`; reinicio exclusivo demo: `python database/seed_data.py --reset`; reiniciar y cargar: `python database/seed_data.py --reset --seed`.
- Los registros demo tienen `is_demo=1`; los datos reales conservan `is_demo=0`. Nunca cargar datos personales reales en seed. La semilla aborta si encuentra una colisión entre sus identificadores reservados y una cuenta real.
