> **Nota de integración (fase 02).** Este informe describe la entrega original del Integrante 2. Al integrarla en `pachaadapt_fase02_sistema_visual` no se sobrescribió ningún módulo que ya existiera: los archivos con el mismo nombre pero API distinta se incorporaron con otro nombre (`ai/adaptations/organized_outline.py` = «visual_organizer» de este informe, `ai/adaptations/local_audio.py` = «audio_generator», `backend/app/api/v1/adaptations_persisted.py` = «adaptations»). Las cifras de pruebas de la sección 6 son las de la entrega original; las del proyecto integrado están en `docs/integrante2/INTEGRACION_EN_FASE02.md`.

# Informe del Integrante 2 — procesamiento de documentos y adaptaciones

> Todo lo descrito funciona con **reglas locales** (sin IA, sin Internet). No se promete ninguna función de IA, traducción o audio sin Internet que no exista como modelo/servicio local.

## 1. Diagnóstico inicial
- Existían: carga de PDF/TXT (`/materials`), extracción con OCR opcional, y tres adaptaciones (resumen, lectura fácil, preguntas) **sin persistencia**: se devolvían y se perdían. No había listado, descarga del original, estado de procesamiento ni relación adaptación↔original.
- `POST /documents/import` (Integrante 3) respondía 503 porque nadie conectaba el procesador documental.
- Los módulos `visual_organizer`, `audio_generator`, `accessibility`, `translator`, `quiz_generator`, `language_registry`, `cultural_validation` eran solo `# TODO`.
- El frontend recordaba materiales solo en `localStorage`, sin lista del servidor y sin consulta sin conexión.

## 2. Archivos nuevos o modificados
**Nuevos** — Backend: `ai/adaptations/{errors,visual_organizer,audio_generator,accessibility,translator,quiz_generator}.py`, `ai/document_processing/{text_organizer,image_describer}.py`, `ai/language_support/{language_registry,cultural_validation}.py`, `backend/app/api/v1/{adaptations,register_integrante2}.py`, `backend/app/services/material_processor.py`, `database/migrations/003_integrante2_adaptaciones{,.down}.sql`, `database/demo_materials/*`, `scripts/import_materials.py`. Frontend: `lib/{materials.types,materialsView,materialsOffline}.ts`, `offline/materials-cache.ts`, `hooks/useAnswerDraft.ts`, `components/MaterialDetail.tsx`. Pruebas: `tests/integrante2/*`, `frontend/tests/materials.test.ts`.
**Modificados (cambios acotados)** — `ai/document_processing/{pdf_extractor,ocr_processor}.py` (funciones añadidas, las originales intactas), `backend/app/services/material_service.py` (compatible hacia atrás), `backend/app/api/v1/materials.py`, `backend/app/main.py` (+2 líneas), `tests/backend/test_structure.py` (3 migraciones), `frontend/src/{pages/Materiales,pages/Actividades,pages/Estado}.tsx`, `services/{materials.service,http}.ts` (solo se añadió `requestBlob`), `lib/{types,quiz}.ts`, `styles.css` (añadidos), y documentación.

## 3. Adaptaciones que funcionan realmente
| Adaptación | Qué hace de verdad | Límite |
|---|---|---|
| Texto organizado | Páginas, títulos, párrafos, listas, tablas aplanadas (`celda — celda`) | Las tablas se detectan por heurística |
| Resumen | Elige las oraciones más importantes **del propio texto** | No redacta nada nuevo |
| Lectura fácil | Divide oraciones largas, quita paréntesis | No simplifica vocabulario |
| Esquema | Lista jerárquica de títulos y puntos | No es mapa conceptual |
| Preguntas | Preguntas abiertas a partir de fragmentos | Sin clave de respuestas (la define el docente) |
| Notas de imágenes | Pies de figura + texto dentro de la imagen con OCR | No describe lo que muestra la imagen |
| Audio | Solo si el servidor tiene `espeak-ng` | Si no, se informa “no disponible” y no se crea nada |

Todas se guardan en `i2_adaptations`, enlazadas a su original (`material_id`), con estado `complete/partial`, advertencias, hash del texto fuente, origen (extraído/editado) y `review_status` (pendiente/aprobada). Una adaptación vacía **no se guarda**. Se pueden vincular a un documento (I3) o a una actividad (I4).

## 4. Formatos soportados
Entrada: **PDF** (con texto digital; escaneados solo con OCR instalado) y **TXT**. PDF con contraseña o corrupto → error claro. Salida: HTML accesible (`lang="es"`, escapado, con aviso de revisión), TXT y WAV (si hay motor de voz). **No** hay DOCX, imágenes sueltas, braille, traducción, quechua ni transcripción de audio/video.

## 5. Limitaciones
- OCR: el servidor probado solo tiene idioma `eng`; en español requiere `tesseract-ocr-spa`.
- Audio: requiere espeak-ng; la calidad de voz no se pudo evaluar aquí (la prueba usa un motor simulado).
- Las adaptaciones **se generan siempre con conexión al servidor**; sin conexión se consultan solo las guardadas con «Guardar para usar sin conexión» (datos, adaptaciones y original) y los materiales del catálogo ya descargados.
- Identidad de demostración (cabeceras); los materiales son del docente que los subió.
- Todo debe ser revisado por el docente antes de usarse con estudiantes.

## 6. Pruebas realizadas (resultado real)
- Backend: `python -m unittest discover -s tests -t .` → **95 pruebas, 3 omitidas, 2 errores**. Los 2 errores (`test_material_api`, `test_routes_wiring`) existían antes de mis cambios: FastAPI no está instalado en el entorno de pruebas. Las pruebas del integrante 2 (38, de ellas 3 omitidas por FastAPI) pasan (carga, extracción, PDF/TXT, escaneado, cifrado, corrupto, original ausente, adaptaciones, persistencia entre procesos —reinicio—, aislamiento entre docentes, relaciones original↔adaptación↔documento/actividad, importación de I3, importación de demos idempotente).
- Las **pruebas HTTP de extremo a extremo** (`tests/integrante2/test_routes.py`) quedaron escritas pero **se omiten** sin FastAPI: no se ejecutaron. Pásalas en tu equipo.
- Frontend: `npm test` → 38 pruebas OK (14 nuevas de este integrante). Contrato frontend↔backend: OK.
- No se pudo ejecutar `npm run build` (React/Vite no instalados, sin red). `tsc` solo mostró los errores por falta de tipos de React, también presentes en archivos no modificados. **Las pantallas nuevas no se vieron en un navegador.**

## 7. Contrato de integración
- **I1 (interfaz)**: estado de cada material en `GET /materials` y `/materials/{id}`: `status` (`uploaded|extracted|no_text|failed`), `error{code,message}`, `warnings`, `attempts`, `is_demo`, `adaptation_count`. Capacidades reales en `GET /materials/capabilities`.
- **I3 (asistente/documentos)**: `MaterialProcessor.get_adapted_text` (puerto `DocumentProcessorPort`) devuelve lectura fácil → resumen → esquema → texto extraído. Se conecta en `register_integrante2(app)`.
- **I4 (datos)**: migración `003` (`i2_material_state`, `i2_adaptations`, `i2_adaptation_links`); originales en `STORAGE_DIR`; IDs de 32 hex; vínculos a `assignments`/`documents`; errores: 400 validación, 404 inexistente/ajeno, 501 no disponible, 500 fallo de procesamiento.
- Endpoints nuevos: `GET /materials`, `/materials/capabilities`, `/{id}/original`, `/{id}/text`, `/{id}/adaptations[/{aid}[/review|links|export|audio]]`. Los existentes `POST /materials`, `/extract`, `/adapt` y `GET /{id}` se conservan (respuestas ampliadas, no cambiadas).

## 8. Instrucciones de ejecución
1. Copia el contenido del ZIP sobre `pachaadapt/` (no borra nada).
2. `python scripts/start_server.py` (aplica la migración 003 al iniciar; si usas otro arranque, `Database.migrate()` la aplica).
3. Datos de demostración: `python scripts/import_materials.py --owner demo-teacher` (idempotente). Son tres materiales **marcados «MATERIAL DE DEMOSTRACIÓN»**: Fotosíntesis, Ciclo del agua, Sistema digestivo.
4. Frontend: `cd frontend && npm install && npm run dev`; entra como Docente → *Archivos y adaptación*.
5. Pruebas: `python -m unittest discover -s tests -t .` y `cd frontend && npm test`.
