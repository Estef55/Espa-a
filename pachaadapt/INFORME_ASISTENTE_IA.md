# PACHAADAPT — Asistente de IA

## Auditoría

La versión recibida ya incluía `ai/model_gateway.py`, el `ChatService`, `/api/v1/ai-chat`, persistencia de conversación por docente, contexto de documentos editables, preferencias, controles de privacidad, timeout y la página React conectada. También había pruebas de transporte HTTP local y aliases para `openai_compatible`, OpenAI, Groq y Ollama. La causa del mensaje de “pendiente” era la configuración ausente en el proceso del backend: no había API key configurada y el proyecto no cargaba un archivo `.env`.

## Cambios realizados

- Añadí un lector mínimo de `.env` en `ai/env_file.py`, sin dependencias extra, ejecución de shell ni salida de valores. Las variables ya definidas en el entorno del sistema tienen precedencia.
- `ai.settings.load_settings()` carga `.env` de la raíz del proyecto cuando usa el entorno del proceso.
- Añadí `.env.example` con Groq como primer endpoint compatible, sin credenciales reales; `.gitignore` permite ese ejemplo y sigue excluyendo `.env`.
- Mejoré los mensajes seguros de errores HTTP 400/401/403/404/429; se descarta el cuerpo upstream y no se devuelve la clave.
- Para los alias `groq` y `openai`, la configuración se considera incompleta si no hay API key. `openai_compatible` y `ollama` mantienen clave opcional porque pueden apuntar a endpoints locales o sin autenticación.
- Actualicé la interfaz para explicar la configuración local y proteger explícitamente la clave; actualicé las instrucciones en README y documentación del asistente.
- Añadí pruebas para la carga y precedencia de `.env`, configuración incompleta, errores de autenticación/modelo, y se conservaron las pruebas de conversación, privacidad, documentos y selección de proveedor.

## Pruebas ejecutadas

- `python -m pytest -q ./backend/tests ./tests`: **110 passed**, 8 subtests, una advertencia externa de deprecación AnyIO/pytest.
- `python -m unittest discover -s tests -t . -q`: **90 OK**.
- `python -m compileall -q ai backend scripts database tests`: correcto.
- `npm ci`: 69 paquetes instalados; auditoría reportó 0 vulnerabilidades.
- `npm test`: **36 passed**.
- `npm run build`: correcto, **70 módulos**.
- Prueba HTTP del backend local sin proveedor: `/api/v1/ai-chat/status` reportó `false`; `POST /api/v1/ai-chat` devolvió **503 `ai_provider_not_configured`** y no generó respuesta ficticia.
- Pruebas de proveedor con servidor HTTP local cubren respuesta, conversación con contexto, documento autorizado, aliases, timeout, conexión rechazada, 400/401/403/404/429 y protección de la clave. Son pruebas de contrato, no una llamada a un modelo hospedado.

## Pendiente para activar inferencia real

En este entorno no hay una API key de proveedor configurada. No se inventó ni se solicitó que se pegue una clave en el chat; por eso **no fue posible probar una consulta real al modelo ni afirmar que Groq/OpenAI haya respondido**. El gateway y la UI quedan preparados, pero la disponibilidad real depende de que el usuario configure un proveedor válido.

1. En la consola oficial de Groq, crea una API key: https://console.groq.com/keys
2. En la raíz, ejecuta `Copy-Item .env.example .env` y edita `.env` localmente. Pega la key solo en `PACHAADAPT_AI_API_KEY`; comprueba que el ID de modelo siga habilitado en tu cuenta.
3. Reinicia el backend y verifica `GET /api/v1/ai-chat/status` desde el perfil docente; luego envía una pregunta desde Asistente. Una respuesta de ese endpoint acredita la conexión real.
4. No compartas el `.env`, no lo incluyas en ZIP y no expongas el backend con autenticación demo.

Para cambiar de proveedor ajusta `PACHAADAPT_AI_PROVIDER`, `PACHAADAPT_AI_BASE_URL`, `PACHAADAPT_AI_MODEL` y la key en `.env`; `openai_compatible` usa el mismo transporte genérico. Véase `CONFIGURACION_SERVICIOS_IA.md`.

## Límites conservados

- Los informes agregados se consultan en su módulo existente, pero el chat todavía no incorpora automáticamente resultados pedagógicos agregados como contexto. No se añadieron datos ni estadísticas al chat.
- La identidad por perfiles sigue siendo demostrativa; falta autenticación de producción.
- La prueba final contra un proveedor externo queda pendiente hasta que haya una API key/modelo accesible.
