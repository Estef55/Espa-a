# Resultados de pruebas de integración

## Estado inicial (antes de cambios funcionales)

| Comando | Resultado real |
|---|---|
| `python -m unittest discover -s tests -t . -v` | **77 pruebas OK**. Se observó `ResourceWarning` en una prueba de proveedor HTTP, sin fallo. |
| `python -m pytest -q backend/tests` | Inicialmente bloqueado: `pytest` no estaba instalado. Tras instalar `pytest 9.2.0` en el entorno activo: **12 passed**, 1 warning de compatibilidad del plugin AnyIO con pytest 9. |
| `npm test` | **31 pruebas OK** antes de añadir dependencias locales. |
| `npm run build` | Inicialmente bloqueado porque faltaba `frontend/node_modules/.bin/tsc`. Tras `npm ci`: build de TypeScript/Vite **OK**, 66 módulos transformados. |

## Verificación posterior a correcciones

- `python -m unittest discover -s tests -t . -v` — **77 OK**.
- `python -m pytest -q backend/tests` — **14 passed**, 1 warning del plugin AnyIO con pytest 9.
- Desde `frontend/`: `npm run build` — **OK**, TypeScript y Vite; 67 módulos transformados.
- Desde `frontend/`: `npm test` — **32 passed**, incluye prueba nueva de rechazo retenido/reintento manual.
- Tres regresiones backend se observaron en rojo antes de corregir: filtro docente de actividades/pull, preservación de revisión tras sync y rollback del lote. Las tres pasan ahora.

## Hallazgos críticos: estado tras correcciones

- Docente: `/api/v1/assignments` y `/pull` se limitan ahora a actividades propias; regresión de dos docentes verifica el aislamiento.
- Push: una transacción SQLite rodea el lote; si una operación inválida falla, se revierten las escrituras anteriores del mismo lote.
- Sync: reenvíos sobre entrega ya revisada/devuelta resultan en conflicto recuperable, sin revertir la revisión.
- Rechazos HTTP 4xx/estado `rejected`: quedan marcados localmente, excluidos de envío automático y se presentan con acción manual que usa UUID nuevo; prueba frontend verifica persistencia/no-retry/ACK.
- **Pendiente de seguridad:** identidad sigue basada en cabeceras configurables de demostración; estudiantes listan actividades publicadas sin verificación de matrícula porque no existe tabla/relación de pertenencia a aula. No usar con identidades/datos reales ni exponer a Internet.

Se inició temporalmente FastAPI con SQLite aislada bajo `AppData/Local/hermes/cache/scratch/pachaadapt-audit.sqlite3`, `PACHAADAPT_I3_DEV_AUTH=1` y se detuvo después. Resultado: `/health` respondió con `database: ok`, motor `sqlite`; OpenAPI confirmó `/api/v1/synchronization/push`, `/submissions`, `/materials`, `/adaptations/capabilities`, `/preferences`, `/documents`, `/ai-chat` y `/reports`; solicitud autenticada de demostración a `/api/v1/synchronization/status` respondió `server: online`, cero operaciones aceptadas. La DB temporal quedó fuera del proyecto.

No se ejecutó un navegador automatizado ni se simularon dos dispositivos reales para el ciclo completo de pérdida de red, recarga y reconexión. Las pruebas nuevas cubren en código el ciclo de borrador (almacén), rechazo/retry/ACK de cola y regresiones API, pero no equivalen a un ensayo de campo ni prueban IndexedDB con navegador real.

## Límites detectados en pruebas

- La suite frontend verifica el almacén de borradores/adaptaciones aislado y la cola de rechazo, pero no una recarga real de React/IndexedDB desde una página renderizada.
- Identidad de desarrollo con cabeceras sigue activa solo si se configura explícitamente; no se verificó autenticación real ni la matrícula de estudiantes en grupos.
- Proveedores IA, procesador documental, OCR opcional y fuente de informes requieren configuración/dependencias externas; no se validaron contra proveedores reales.
- PostgreSQL no se probó ni se habilitó; el backend usa SQLite.

Se probó el artefacto limpio `../pachaadapt_integrado_20261102.zip`: extracción en scratch, `python -m unittest discover -s tests -t . -q` (77 OK), `python -m pytest -q backend/tests` (14 passed, 1 warning), `npm ci` (70 paquetes, cero vulnerabilidades reportadas), `npm run build` (OK, 67 módulos) y `npm test` (32 OK). No se incluyeron bases locales, credenciales, dependencias instaladas ni output de build.
