# PACHAADAPT — Entrega parcial del integrante 2

## Alcance de esta entrega
Se implementa la primera mitad prioritaria del módulo de documentos y adaptación:
- Carga de PDF y TXT, con validación básica y conservación del original.
- Metadatos, identificador aleatorio y huella SHA-256.
- Extracción de texto de PDF digitales y TXT.
- OCR opcional para PDF escaneados (requiere dependencias Python y programas del sistema).
- Adaptaciones locales iniciales: resumen extractivo, lectura fácil conservadora y preguntas abiertas.
- API FastAPI para cargar, consultar, extraer y adaptar materiales.

## API
La API se monta bajo `/api/v1`:
- `POST /materials` — multipart/form-data, campo `file`.
- `GET /materials/{material_id}` — metadatos.
- `POST /materials/{material_id}/extract` — JSON opcional `{"ocr": true}`.
- `POST /materials/{material_id}/adapt` — JSON `{"adaptation":"summary"}`, `{"adaptation":"easy_read"}` o `{"adaptation":"quiz","options":{"count":5}}`.

Las adaptaciones se marcan para revisión docente; no deben publicarse directamente sin validación. La API requiere una identidad docente configurada y oculta materiales de otros usuarios (en desarrollo local puede usarse `PACHAADAPT_I3_DEV_AUTH=1` junto con la cabecera `X-Dev-Teacher-Id`).
Los originales se guardan por defecto en `storage/materials/`, configurable con `PACHAADAPT_STORAGE_DIR`; metadatos y texto extraído se registran en la base SQLite compartida mediante la migración `002_integrante2_materiales.sql`. El límite por defecto es 25 MiB (`PACHAADAPT_MAX_UPLOAD_BYTES`).

## Instalación y ejecución
Desde `pachaadapt/`:
```bash
python -m pip install -r backend/requirements.txt
uvicorn --app-dir backend app.main:app --reload
```
Si se ejecuta desde la carpeta `backend/`:
```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```
Para OCR escaneado se necesita instalar además `pytesseract` y `pdf2image`, junto con Tesseract OCR (idioma `spa`) y Poppler en el sistema operativo.

## Limitaciones conocidas
- El resumen y la lectura fácil son heurísticos, no modelos generativos; verificar fidelidad y adecuación.
- El OCR no se activa automáticamente por defecto para evitar dependencias externas y latencias inesperadas.
- El generador crea preguntas abiertas basadas en fragmentos, sin claves de respuesta automáticas.
- Esta entrega no implementa todavía audio, descripción de imágenes, transcripción audiovisual, mapas visuales, traducción ni compatibilidad Braille avanzada.
