# Guía de ejecución

## 1. Pruebas (sin instalar nada), desde la raíz
```
python -m unittest discover -s tests -t . -p "test_*.py" -v
```
(En Linux/macOS use `python3`.) Esperado: `Ran 46 tests … OK`. Si FastAPI está instalado, las pruebas de rutas lo usan en lugar del doble.

## 2. Probar las rutas HTTP reales (pendiente, en su máquina)
1. `backend/app/main.py` ya incluye las 2 líneas de registro (respaldo del original en `docs/integrante3/backups/main.py.original`).
2. PowerShell:
   ```
   $env:PACHAADAPT_I3_DEV_AUTH = "1"      # SOLO desarrollo
   cd backend
   uvicorn app.main:app --reload
   ```
3. Abrir `http://127.0.0.1:8000/docs` (etiquetas `preferences`, `documents`, `ai-chat`, `reports`) y comprobar que `/health` sigue respondiendo.
4. Ejemplo:
   ```
   curl -H "X-Dev-Teacher-Id: docente1" http://127.0.0.1:8000/api/v1/preferences
   curl -X POST -H "X-Dev-Teacher-Id: docente1" -H "Content-Type: application/json" \
        -d '{"title":"Guía","content":"Texto"}' http://127.0.0.1:8000/api/v1/documents
   ```

## 3. Configurar el asistente de IA (variables de entorno del servidor)
| Variable | Descripción |
|---|---|
| `PACHAADAPT_AI_PROVIDER` | `openai_compatible` |
| `PACHAADAPT_AI_BASE_URL` | p. ej. `http://localhost:11434/v1` (Ollama) o la URL de su proveedor |
| `PACHAADAPT_AI_MODEL` | nombre del modelo |
| `PACHAADAPT_AI_API_KEY` | opcional para servicios locales |
| `PACHAADAPT_AI_TIMEOUT` / `PACHAADAPT_AI_MAX_TOKENS` | def. 30 s (1–300) / 800 |
| `PACHAADAPT_I3_DB` | archivo SQLite del módulo (def. `storage/integrante3.sqlite3`) |
| `PACHAADAPT_I3_DEV_AUTH` | `1` = identidad de desarrollo por cabecera (**no producción**) |

Sin configuración, `POST /api/v1/ai-chat` devuelve 503 `ai_provider_not_configured`.
