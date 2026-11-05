# Entrega del Integrante 2 — Documentos y adaptación (continuación)

## Archivos creados (antes contenían solo `# TODO`)
- `ai/document_processing/image_describer.py`, `media_transcriber.py`
- `ai/adaptations/visual_organizer.py`, `accessibility.py`, `audio_generator.py`, `translator.py`
- `ai/language_support/language_registry.py`, `cultural_validation.py` (+ `__init__.py`)
- `backend/app/api/v1/adaptations.py` (antes TODO) y `backend/app/services/adaptation_service.py` (nuevo)
- Frontend (nuevos): `src/services/adaptations.service.ts`, `src/offline/adaptation-store.ts`, `src/lib/resources.ts`, `tests/adaptations.test.ts`
- Pruebas: `tests/test_integrante2_accessibility.py`, `tests/backend/test_adaptations_service.py`

## Único archivo compartido modificado
`backend/app/main.py`: +2 líneas (import e `include_router` de `adaptations_router`, marcadas `# integrante 2`). Sin ellas el frontend llamaría rutas inexistentes (lo verifica `test_frontend_contract`).

## API nueva (`/api/v1/adaptations`, solo docente, mismo mecanismo de identidad que `/materials`)
| Ruta | Función |
|---|---|
| `GET /capabilities` | Matriz de recursos: ¿funciona offline en el dispositivo, necesita servidor, necesita Internet, está disponible? |
| `POST /materials/{id}/visual` | `outline` o `concept_map` (Mermaid) |
| `POST /materials/{id}/accessible` | `plain`, `html`, `braille` (grado 1) o `bundle` |
| `POST /materials/{id}/audio-script` | Guion/SSML de narración |
| `POST /materials/{id}/audio` | Audio WAV (base64) — **501** si no hay motor de voz local |
| `POST /materials/{id}/translate` | **501** mientras no se configure proveedor (`adaptation_service.set_translation_provider`) |
| `POST /images/inspect`, `/images/describe` | Metadatos reales; descripción **501** sin modelo de visión (`set_vision_provider`) |
| `POST /subtitles` | SRT/VTT → texto |

## Offline (indicaciones del Integrante 2)
1. Materiales descargados: los sigue cacheando `offline/cache-manager.ts` (Integrante 4); no se tocó.
2. Adaptaciones guardadas: `offline/adaptation-store.ts` (IndexedDB propia `pachaadapt-adaptations`, por usuario).
3. Contenido de actividad: borradores locales (`saveDraft/getDraft`); se borran solo con `clearDraft` tras confirmación del servidor. **No son entregas** ni sustituyen la cola de sincronización.
4. Qué requiere conexión: `GET /adaptations/capabilities` y `lib/resources.ts` (`splitByConnection`).
5. Coordinación con Integrante 4: almacén independiente, sin cambiar `local-db.ts`.

## Lo que NO se promete
- Traducción, descripción de imágenes y transcripción de audio no tienen modelo local incluido: responden 501 hasta configurarlos.
- Audio requiere `espeak-ng`/`espeak` o `pyttsx3` en el servidor; voces en quechua no verificadas.
- Resumen, lectura fácil, preguntas, esquemas y Braille son heurísticos: toda salida lleva `review_required`. El Braille debe revisarlo un transcriptor.
- Quechua: variedad sin definir (`variety_confirmed=false`); la validación cultural es registro de decisión humana, no automática.

## Integración pendiente
- Pantallas: `Materiales.tsx` (Integrante 1) aún no usa los nuevos servicios/almacén; no se modificó para no pisar su trabajo.
- `documents/import` (Integrante 3) sigue 503 hasta llamar `configure_integrations(processor=...)`; este ZIP no lo conecta.
- Validación de rutas con FastAPI real: no había FastAPI en el entorno de desarrollo (ver pruebas).

## Pruebas ejecutadas
`python -m unittest discover -s tests -t . -p "test_*.py"` → 76 pruebas; 74 OK y 2 errores previos y ajenos (`test_material_api`, `test_main_keeps_health_and_exposes_new_routes`) porque FastAPI no está instalado en este entorno. `npm test` (frontend) → 31/31. `npm run build` **no se pudo ejecutar** (sin `node_modules` ni red); sí se verificó con `tsc` que mis 3 archivos TypeScript no tienen errores.
