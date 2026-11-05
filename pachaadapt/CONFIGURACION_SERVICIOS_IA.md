# Configuración del servicio de IA

## Compatibilidad

PACHAADAPT usa la pasarela `openai_compatible`, que envía `POST <PACHAADAPT_AI_BASE_URL>/chat/completions` con el formato `messages`/`model`/`max_tokens`. Puede apuntar a un servicio remoto compatible o a un servidor local compatible. Cambiar entre `openai`, `groq`, `ollama` u `openai_compatible` solo selecciona la etiqueta/proveedor conocido; todos requieren una URL base compatible con OpenAI explícita y el ID de modelo que ese endpoint acepta. El proceso backend debe reiniciarse para leer nuevas variables. Estos alias no convierten APIs propietarias incompatibles en compatibles: verifique que el proveedor exponga `POST /chat/completions` y acepte `messages`, `model` y `max_tokens`.

## Variables de entorno

Configure en el proceso del **backend**, antes de iniciarlo:

| Variable | Requerida | Uso |
|---|---|---|
| `PACHAADAPT_AI_PROVIDER` | Sí | `openai_compatible`, `openai`, `groq` u `ollama`. Los cuatro seleccionan la misma API compatible; no son SDKs propietarios. |
| `PACHAADAPT_AI_BASE_URL` | Sí | Base URL de la API compatible (por ejemplo, `https://api.example/v1`); el servidor añade `/chat/completions`. Use la URL oficial/servida por su proveedor. |
| `PACHAADAPT_AI_MODEL` | Sí | Identificador exacto del modelo disponible en el endpoint. |
| `PACHAADAPT_AI_API_KEY` | Según proveedor | Credencial leída solo por backend; puede omitirse para endpoint local sin autenticación. |
| `PACHAADAPT_AI_TIMEOUT` | No | Tiempo máximo en segundos; valor predeterminado 30, limitado de 1 a 300. |
| `PACHAADAPT_AI_MAX_TOKENS` | No | Límite de salida; predeterminado 800, limitado de 16 a 4000. |

La base de datos conserva su configuración actual (`PACHAADAPT_DB_PATH`); estas variables no sustituyen ni cambian SQLite.

## Configuración local con `.env`

1. En la raíz del proyecto, copia el ejemplo: `Copy-Item .env.example .env`.
2. Edita `.env` y reemplaza `PACHAADAPT_AI_API_KEY=` con la clave creada en el panel oficial del proveedor. No envíes ni publiques la clave.
3. Conserva el endpoint base y el ID de modelo que el proveedor muestra como disponibles; los modelos pueden cambiar según la cuenta.
4. Reinicia el backend para que lea la configuración. `ai.settings` carga `.env` en el proceso del servidor solo cuando una variable equivalente no está ya definida en el entorno. No se evalúan comandos ni se imprimen valores.

El `.gitignore` excluye `.env` y permite incluir solamente `.env.example`. La clave no se envía al frontend ni se devuelve en respuestas. Para Groq, crea la API key en [console.groq.com/keys](https://console.groq.com/keys); la URL compatible documentada es `https://api.groq.com/openai/v1`. Usa el ID de modelo que aparezca habilitado en tu cuenta (el ejemplo inicial usa `llama-3.3-70b-versatile`; comprueba que siga disponible).

`openai_compatible` usa la misma pasarela genérica. Para cambiar de Groq a OpenAI o Ollama, ajusta `PACHAADAPT_AI_PROVIDER`, `PACHAADAPT_AI_BASE_URL`, `PACHAADAPT_AI_MODEL` y la clave según el proveedor. El proyecto no requiere cambiar su código para alternar esos endpoints.

## Inicio

Desde la raíz del proyecto, para desarrollo local:

```powershell
.\.venv\Scripts\python.exe .\scripts\start_server.py
```

También puede iniciar Uvicorn desde la raíz después de instalar requisitos y activar el entorno:

```powershell
$env:PACHAADAPT_I3_DEV_AUTH = "1"  # solo desarrollo local; no es autenticación real
python -m uvicorn --app-dir backend app.main:app --reload
```

El script de desarrollo activa identidad por cabeceras si no hay otro valor configurado. No exponga este modo a Internet: el mecanismo de cabeceras no autentica realmente a la persona.

## Comprobar disponibilidad

1. Consulte `GET http://127.0.0.1:8000/api/v1/ai-chat/status` con la identidad de desarrollo habilitada. `ai_provider_configured: true` confirma que hay configuración sintáctica de proveedor, pero **no** prueba que el endpoint, el modelo o la credencial sean válidos.
2. Envíe una consulta de prueba desde la pantalla Asistente o a `POST /api/v1/ai-chat` con `{"question":"Responde brevemente: conexión de prueba"}` y cabeceras de identidad válidas en desarrollo. Una respuesta generada por modelo acredita que el proveedor contestó a esa solicitud. La aplicación no emite respuestas simuladas.
3. Si falla, revise URL base, nombre de modelo, credencial en el entorno del proceso, firewall y logs del proveedor. PACHAADAPT convierte timeout, fallo HTTP, red y formato inesperado en errores controlados; no devuelve la credencial.

No se incorporó un endpoint de “ping” que invoque al proveedor automáticamente, por lo que la consulta status no genera consumo del servicio.

## Si no se configura

- El chat y la interpretación opcional de informes no están disponibles; el chat informa con error controlado `503` y no fabrica respuestas.
- Las funciones de documentos, historial, preferencias y procesamiento local de TXT no dependen del proveedor.
- La carga/extracción PDF/TXT del integrante 2 utiliza el servicio documental existente y no implica que el modelo IA esté conectado.
- Los informes permanecen disponibles solo cuando exista una fuente de resultados real y autorizada; configurar IA no crea esa fuente ni permite producir calificaciones.

La configuración de proveedor no resuelve la autenticación institucional pendiente ni convierte el prototipo en un servicio listo para producción.