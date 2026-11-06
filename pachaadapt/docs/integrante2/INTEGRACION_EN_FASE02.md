# Integración del Integrante 2 en `fase02_sistema_visual`

Qué se sumó, qué se dejó intacto a propósito y cómo se comprobó. Regla seguida: **nada de lo que ya funcionaba en fase02 se sobrescribe**; lo nuevo entra como archivos nuevos o como funciones añadidas.

## Qué se añadió
**Backend**
- `ai/adaptations/errors.py`, `ai/document_processing/text_organizer.py`, `backend/app/services/material_processor.py`, `backend/app/api/v1/register_integrante2.py`.
- `ai/adaptations/organized_outline.py` (esquema a partir del texto organizado) y `ai/adaptations/local_audio.py` (audio con espeak-ng): en la entrega original se llamaban `visual_organizer.py` y `audio_generator.py`, nombres que fase02 ya usa con otra API, por eso entran con otro nombre.
- `backend/app/api/v1/adaptations_persisted.py`: rutas `/api/v1/materials/{id}/adaptations…` (consulta, revisión docente, vínculos, exportación HTML/TXT, audio). El `adaptations.py` de fase02 (`/api/v1/adaptations/...`) no se toca.
- Migración `database/migrations/003_integrante2_adaptaciones{,.down}.sql` (solo `CREATE … IF NOT EXISTS`), materiales de demostración y `scripts/import_materials.py`.
- Funciones **añadidas** (las existentes no cambian) en `accessibility.py` (`render_html`, `render_text`), `image_describer.py` (`describe_pdf_images`), `language_registry.py` (`list_languages`) y `cultural_validation.py` (`review_notice`).
- Reemplazos por versiones compatibles hacia atrás: `pdf_extractor.py`, `ocr_processor.py` (añade `ocr_status`), `quiz_generator.py` (reparte las preguntas a lo largo del texto), `material_service.py` y `materials.py` (mismas funciones y rutas de antes, más listado, estado, original, texto organizado y adaptaciones guardadas).

**Frontend**
- `lib/{materials.types,materialsView,materialsOffline}.ts`, `offline/materials-cache.ts`, `components/MaterialDetail.tsx`, `hooks/useAnswerDraft.ts`, `services/http.ts` (+`requestBlob`), `services/materials.service.ts`, bloque de estilos añadido al final de `styles.css`, `tests/materials.test.ts`.
- `pages/Materiales.tsx` ahora muestra la lista del servidor con estado, texto organizado, adaptaciones guardadas (revisión, descargas, audio, vínculo a documento/actividad), «Guardar para usar sin conexión» y «Qué puede hacer este servidor». **Se conservan** las funciones de fase02: consulta por identificador, verificación de huella SHA-256, OCR opcional, corregir el texto extraído y adaptar el texto corregido, cantidad de oraciones/palabras/preguntas, copiar texto, guardar como documento editable y la copia local de cada adaptación (visible también sin conexión).
- `pages/Estado.tsx`: filas actualizadas (el listado y la descarga del original ya existen).

## Qué NO se aplicó, a propósito
- **`pages/Actividades.tsx` de la entrega original**: quitaba `isSubmissionLocked` (bloqueo de entregas revisadas/devueltas) y reemplazaba los borradores de fase02 (`adaptation-store`). Fase02 ya guarda borradores, así que se dejó como estaba. `hooks/useAnswerDraft.ts` se incluye pero **no está conectado**.
- **`MaterialProcessor` como procesador documental**: `main.py` sigue conectando `MaterialDocumentProcessor` (texto extraído sin transformar, con sus pruebas). Para que `/documents/import` prefiera la mejor adaptación guardada: `configure_integrations(processor=MaterialProcessor())`.
- `backend/app/main.py` conserva `classrooms`, `DELETE` en CORS y `configure_integrations`; solo se añadió `register_integrante2(app)`.
- `docs/api.md`, `docs/pruebas.md` y `docs/integrante_2_entrega_parcial.md`: solo se les añadieron secciones.

## Verificación (resultado real)
- Python: `python -m unittest discover -s tests -t .` → fase02 sola: 88 pruebas, 4 errores; integrado: **126 pruebas, los mismos 4 errores, 3 omitidas**. Los 4 errores son previos (`test_material_integration`, `test_material_api`, 2 de `test_routes_wiring`): FastAPI no está instalado en este entorno. Las 3 omitidas son las HTTP de extremo a extremo de `tests/integrante2/test_routes.py`.
- Se ajustaron 3 pruebas de la entrega original por el cambio de nombres/cableado: la de rutas (apunta a `adaptations_persisted.py` y abre el cliente con `lifespan`), la de migraciones de `test_structure.py` (ahora 3) y los `mock.patch` de audio.
- Frontend: `npm test` → 36 pruebas en fase02 sola; **48 con la integración, todas OK**. `tests/frontend/test_frontend_contract.py` OK.
- **No se ejecutaron** `npm run build` ni la interfaz en un navegador (sin red para instalar React/Vite). Se validó la sintaxis de los `.tsx` con esbuild y los tipos con `tsc` contra un stub de React: no aparecen identificadores ni importaciones inexistentes; los avisos restantes son del stub.
