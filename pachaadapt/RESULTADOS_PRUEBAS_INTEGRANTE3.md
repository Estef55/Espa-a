# Resultados de pruebas — Integrante 3 PACHAADAPT

## Referencia inicial antes de esta continuación

Al extraer `pachaadapt_integrante3_fase2.zip` en un directorio limpio y antes de modificarlo, se ejecutaron las suites requeridas: **82** pruebas `unittest`, **14** pruebas backend, **33** pruebas frontend, además de `npm run build`; todas terminaron con código 0. Esta es la referencia para esta continuación.

## Matriz final de esta continuación

| Comando / verificación | Resultado observado |
|---|---|
| Desde la raíz: `python -m unittest discover -s tests -t . -v` | Exit 0; **85 tests**, `OK`. Incluye tests nuevos para aliases, error HTTP 429 y cierre del cuerpo de HTTPError. |
| Desde la raíz: `python -m pytest -q backend/tests` | Exit 0; **14 passed**, 1 warning de deprecación `anyio`/pytest. |
| Desde `frontend/`: `npm test` | Exit 0; **33 tests**, 33 pass, 0 fail, 0 skipped. |
| Desde `frontend/`: `npm run build` | Exit 0; `tsc -b` y Vite correctos; 67 módulos transformados. |
| Pruebas específicas en desarrollo | RED: prueba de aliases falló para los tres nombres nuevos porque `build_provider` respondía como no configurado. GREEN: tras cambio del adaptador, los cuatro aliases enviaron solicitud real al servidor HTTP local de prueba y recibieron respuesta con etiqueta correcta. RED: HTTP 429 daba mensaje genérico `HTTP 429`; GREEN: ahora se informa límite/cuota e intento posterior, sin exponer la clave. |
| ZIP actualizado `pachaadapt_integrante3_fase2_actualizado.zip`, extracción limpia | Validación estructural OK (200 archivos; sin `.env`, DB local, cachés, `node_modules` ni build incluido). Desde extracción: unittest **85 OK**, backend **14 passed** (1 warning anyio), frontend **33 passed**, `npm ci` 69 paquetes/0 vulnerabilidades y build Vite correcto (67 módulos). Se comprobó hash/byte diff: los demás archivos del ZIP fuente permanecen idénticos. |

Los servidores simulados existen únicamente dentro de pruebas automatizadas; no representan una cuenta ni servicio externo real. No se colocaron credenciales reales.

## Auditoría inicial de esta continuación

Se revisaron la pasarela, carga de ajustes, servicio conversacional, rutas de informes, servicio de entregas, controles de identidad, documentos y pruebas. La limitación de informes se confirmó: el backend de I4 almacena la respuesta textual y estados, pero no existe calificación numérica/rúbrica validada ni una relación autorizada de grupo/matrícula para análisis pedagógico. No se inventó puntuación ni se conectó un agregador sin ese contrato.

## Incidencias encontradas y corregidas

1. El selector de proveedor solo activaba `openai_compatible`, aunque el protocolo permitía usar endpoints compatibles. Se añadieron los identificadores `openai`, `groq` y `ollama` como aliases del mismo adaptador; requieren URL base y modelo explícitos. La etiqueta retornada identifica el valor configurado.
2. Las respuestas HTTP 429 se comunicaban solo como fallo genérico. Ahora se aclara límite/cuota y se indica reintentar más tarde. El mensaje no incluye body remoto ni credenciales.

## Pendientes que requieren integración externa/otro integrante

- No se probó endpoint o credencial remota real. Debe verificarse con el servicio elegido; los aliases no hacen compatibles APIs que no expongan `/chat/completions`.
- Informes con resultados escolares reales siguen bloqueados por falta de calificación revisada y relación autorizada de aula/matrícula. El endpoint continúa respondiendo 503 si no hay `LearningDataSource` configurada.
- Identidad institucional real, pruebas visuales de navegador y pruebas de desconexión/reconexión/multi-dispositivo quedan pendientes.
- No existe cola de sincronización de documentos; borradores offline se conservan localmente y requieren confirmación explícita al guardar en línea.

## Evidencia de preservación

La carpeta de trabajo procede de una extracción limpia del ZIP de entrega previo. Se mantuvo intacto el ZIP fuente y se creó copia de seguridad antes de los cambios. Los módulos de sincronización y entregas de I1/I4 no fueron modificados en esta continuación. El ZIP actualizado se validará contra el inventario original y se ejecutará desde una extracción nueva antes de entregarlo.