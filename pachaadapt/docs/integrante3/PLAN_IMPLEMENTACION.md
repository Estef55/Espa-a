> **Actualización (entrega final, v2):** el plan original proponía una carpeta aislada `backend/app/integrante3/`; **se descartó** y el código se colocó dentro de los archivos vacíos del esqueleto que corresponden a cada función (ver `ARCHIVOS_MODIFICADOS.md`). Se ejecutó sin tocar archivos compartidos. T1–T7 y T10 están implementadas; T8 (montar los routers en `main.py`) y T9 (frontend) quedan **pendientes** y se describen en `INTEGRACION_PENDIENTE.md`. Estado real: `IMPLEMENTACION.md`.

# Plan de implementación — Integrante 3

Estado: **propuesta pendiente de confirmación** (ver `RIESGOS_Y_COMPATIBILIDAD.md`, decisiones D1–D5).

## 1. Principios
- Solo archivos **nuevos** en `backend/app/integrante3/`, `docs/integrante3/` y `tests/integrante3/`.
- Núcleo en Python estándar, independiente de FastAPI, para poder probarlo sin dependencias.
- Capa HTTP (router FastAPI) delgada sobre el núcleo.
- Ningún archivo compartido se modifica sin copia previa y autorización.

## 2. Tareas
| # | Tarea | Depende de | Estado de dependencia |
|---|---|---|---|
| T1 | Capa de identidad: dependencia `get_current_teacher` enchufable | Auth compartida | **No existe**; se usaría un sustituto de desarrollo (cabecera) claramente marcado, desactivado por defecto |
| T2 | Persistencia aislada del integrante 3 (SQL portable, migración incremental, consultas parametrizadas) | Decisión de motor | **No definido** |
| T3 | Preferencias del docente (valores válidos, defaults, aislamiento por docente) | T1, T2 | Posible |
| T4 | Documentos editables + versiones (versión incremental, autor, motivo, restauración sin borrar historial, control optimista `expected_version`, original inmutable) | T1, T2, contrato de documentos del integrante 2 | Parcial: el documento adaptado aún no existe; se propone que el integrante 3 guarde **texto editable propio** con referencia opcional a un `material_id` externo |
| T5 | Asistente docente: pasarela de IA por variables de entorno, error controlado 503 si no hay proveedor, sin simulación, contexto de documento autorizado, límites de tamaño/tiempo | T1, T3, T4 | Posible; **proveedor externo por decidir** |
| T6 | Análisis e informes: métricas calculadas solo desde datos reales; si no hay datos → respuesta «datos insuficientes» | Fuente de resultados | **No existe**; se implementaría el cálculo sobre un *puerto* (interfaz) que reciba datos, sin inventarlos |
| T7 | Pruebas `unittest` (núcleo) + pruebas de rutas con `TestClient` | T2–T6 | Las de rutas requieren instalar dependencias |
| T8 | Integración mínima: 1 línea `include_router` en `main.py` | Autorización | **Archivo compartido** |
| T9 | Frontend: servicio TS + panel propio | Autorización | **Bloqueado** por la ambigüedad `index.html` vs `App.tsx` |
| T10 | Documentación final | — | — |

## 3. Archivos que se crearían (nuevos)
`backend/app/integrante3/{__init__,config,identity,db,preferences,documents,assistant,reports,router}.py`,
`backend/app/integrante3/migrations/001_integrante3.sql`,
`tests/integrante3/test_*.py`, `docs/integrante3/*.md`.

## 4. Archivos compartidos potencialmente afectados (NO tocados)
| Archivo | Cambio mínimo | Necesario para |
|---|---|---|
| `backend/app/main.py` | +2 líneas (`import` y `app.include_router(...)`) | exponer las rutas |
| `backend/requirements.txt` | +`httpx` (proveedor de IA) y `pytest` (pruebas) | T5/T7; evitable usando `urllib` y `unittest` |
| `frontend/src/services/ai.service.ts`, `reports.service.ts` | rellenar TODO | cliente HTTP |
| `frontend/index.html` o `App.tsx` | punto de montaje de pantallas | UI |
| `database/schema.sql` | solo si se decide unificar el esquema | T2 |
