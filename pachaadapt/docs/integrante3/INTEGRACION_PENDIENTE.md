# Puntos de conexión pendientes

## 1. Routers montados en `backend/app/main.py` (HECHO en esta versión integrada)
Se añadieron solo 2 líneas (el original está respaldado en `docs/integrante3/backups/main.py.original`):
```python
from app.api.v1.register import register_integrante3   # tras el import de FastAPI
register_integrante3(app)                               # al final del archivo
```
`/health` no cambió. **Pendiente de verificar con FastAPI real**: si al arrancar `uvicorn` hubiera algún error de importación, basta quitar esas 2 líneas (o restaurar el respaldo) para volver al estado anterior.

## 2. Autenticación (quien implemente `core/security.py`)
```python
from app.core.identity import set_identity_resolver, Principal
set_identity_resolver(lambda headers: Principal(user_id=..., role="docente"))  # lanzar Unauthorized si no hay sesión
```
Hasta entonces: 503 `auth_not_configured`, o `PACHAADAPT_I3_DEV_AUTH=1` solo en desarrollo.

## 3. Procesador documental (integrante 2)
Implementar `DocumentProcessorPort.get_adapted_text(material_id, owner_id) -> AdaptedDocument(material_id, title, text)` (definido en `ai/assistant/document_builder.py`), verificando que `owner_id` puede ver el material, y registrar:
```python
from app.services.container import configure_integrations
configure_integrations(processor=MiProcesador())
```
Pendiente de acordar: devolver ediciones al procesador (hoy solo hay flujo de ida) y el mapeo de `/preferences/adaptation-params`.

## 4. Resultados de aprendizaje
Implementar `LearningDataSource.fetch_records(teacher_id, filters) -> [LearningRecord(student_ref, topic, score, max_score, recorded_at, group)]` (puerto en `backend/app/services/report_service.py`, tipo en `ai/learning_analysis/result_analyzer.py`), devolviendo **solo** lo que ese docente puede ver y con `student_ref` opaco; registrar con `configure_integrations(data_source=...)`. Falta definir en el esquema compartido de dónde salen entregas y calificaciones.

## 5. Proveedor de IA
Variables de entorno (ver `GUIA_EJECUCION.md`) o `configure_integrations(provider=...)`. `ai/model_gateway.py` quedó con el proveedor; si el integrante 2 necesita modelos, conviene reutilizarlo en lugar de duplicarlo.

## 6. Frontend (integrante 1, no tocado)
Decidir si el destino es React (`App.tsx`) o el prototipo `index.html` (hoy Vite sirve `index.html`, que no carga React). Rellenar `frontend/src/services/ai.service.ts` y `reports.service.ts`. Pantallas pendientes: chat, editor con versiones, preferencias, informes.

## 7. Base de datos compartida
Si el equipo adopta motor/ORM: migrar las tablas `i3_*` (SQL portable) o reescribir `ai/storage.py`. Añadir `storage/` a `.gitignore` (el archivo SQLite del módulo no debe versionarse).

## 8. Dependencias
Ninguna nueva: solo librería estándar más FastAPI/Pydantic ya presentes. `requirements.txt` sin cambios.
