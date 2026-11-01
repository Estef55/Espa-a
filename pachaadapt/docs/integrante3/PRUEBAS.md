# Pruebas

Entorno de desarrollo: Python 3.12.3, **sin red**; FastAPI, Pydantic y pytest no estaban disponibles. Se usa `unittest`.

## Ejecución (desde la raíz del proyecto)
```
python -m unittest discover -s tests -t . -p "test_*.py" -v
```
Resultado real: **46 pruebas, 0 fallos** (3 ejecuciones seguidas). En el primer intento hubo 2 fallos, ambos en las pruebas (una llamada sin adaptar a la nueva estructura y un error de mi doble de Pydantic); se corrigieron las pruebas, no el código del producto.

## Cobertura
| Área | Qué se prueba |
|---|---|
| `tests/ai/test_assistant.py` | solicitud válida; pregunta vacía/larga (sin llamar al proveedor); sin proveedor (no guarda nada); *timeout*, HTTP 500, JSON inválido, respuesta vacía, conexión rechazada; contexto documental autorizado y ajeno; conversación y aislamiento; preferencias aplicadas; truncado; la clave API no sale |
| `tests/ai/test_documents.py` | guardar + historial; restaurar sin perder historial; conflicto; 6 guardados simultáneos → 1 éxito y 5 conflictos; acceso ajeno → 404; persistencia tras «reinicio»; validaciones; original inmutable y archivado; puerto del procesador |
| `tests/ai/test_preferences.py` | defaults; actualización parcial; rechazo de inválidos; aislamiento; persistencia; prompt y parámetros |
| `tests/ai/test_reports.py` | cálculos con cifras conocidas; sin fuente; sin datos / insuficientes; registros inválidos; control de acceso; criterios; recomendaciones enlazadas y coherentes; IA separada y sin identificadores |
| `tests/backend/test_structure.py` | identidad; migración en `database/migrations/` idempotente y solo tablas `i3_*`; `ai/` nunca importa `backend/`; sin claves |
| `tests/backend/test_routes_wiring.py` | el `main.py` real mantiene `/health` y expone las 4 rutas nuevas; los 4 routers importan; rutas esperadas sin duplicados ni pisar `/health`; funciones de ruta con flujos completos y códigos 404/409/422/503 |

Datos de prueba: sintéticos, dentro de los tests. El «servidor de IA» es un `HTTPServer` local solo de pruebas.

## NO ejecutado
- **FastAPI real**: las rutas se probaron llamando a sus funciones con un doble (`tests/backend/_stubs.py`, solo si FastAPI no está instalado). No se verificó validación de cuerpos, códigos HTTP reales ni OpenAPI.
- `/health` y `/docs`; compilación del frontend (`npm run build`); proveedor de IA real; datos reales; rendimiento.
