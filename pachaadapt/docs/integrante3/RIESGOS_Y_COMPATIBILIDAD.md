> **Actualización (entrega final):** las decisiones D1–D5 no se esperaron; se resolvieron con soluciones provisionales y aisladas (SQLite propio con tablas `i3_*`, identidad enchufable apagada por defecto, proveedor de IA por variables de entorno, puertos para el integrante 2 y para los resultados). D5 (destino del frontend) sigue abierta. Ver `IMPLEMENTACION.md` e `INTEGRACION_PENDIENTE.md`.

# Riesgos, compatibilidad y decisiones pendientes

## Contradicciones entre el prompt y el repositorio real
(Prevalece la protección del proyecto existente.)

1. El prompt asume trabajo existente de los integrantes 1 y 2; en este zip **no hay código de backend ni de IA** de ellos. Solo el prototipo visual (`index.html`, `styles.css`).
2. El prompt asume autenticación, documentos procesados y resultados de aprendizaje; **ninguno existe**.
3. El prompt pide no asumir el motor de BD; el esquema está vacío.
4. El prompt asume que `npm run dev` ejecuta la app React; en realidad Vite sirve `index.html` (JS puro) y `App.tsx` no se carga.
5. No hay Git: no se puede atribuir autoría ni hacer diffs fiables.

## Riesgos
| Riesgo | Impacto | Mitigación |
|---|---|---|
| El zip no es la versión actual del repo del equipo | Duplicar o chocar con trabajo ya hecho | **Confirmar versión antes de implementar (D1)** |
| Identidad sin autenticación real | Endpoints sin protección | Dependencia enchufable; sustituto de desarrollo apagado por defecto; documentado como no apto para producción |
| Motor de BD indefinido | Migración posterior | SQL portable en archivo propio; almacén aislado; sin tocar `schema.sql` |
| Contrato de documentos del integrante 2 inexistente | Acoplamiento incorrecto | Referencia opcional por `material_id`; sin reprocesar archivos |
| Proveedor de IA no elegido | Sin respuestas reales | Configuración por entorno; 503 controlado; sin simulación |
| Sin datos de resultados | Informes vacíos | Respuesta explícita de «datos insuficientes»; sin datos inventados |
| Entorno sin red | No se pueden ejecutar FastAPI ni `tsc` aquí | Núcleo probado con stdlib; rutas y compilación se verifican en la máquina del usuario; se documenta |
| `.venv`/`node_modules` Windows y `.pyc` en el zip | Entrega pesada y no portable | Excluidos de la copia de seguridad; recomendar `.gitignore` |

## Medidas de protección aplicadas hasta ahora
- Cero modificaciones a archivos existentes.
- Copia de seguridad del árbol (sin `.venv`, `node_modules`, `__pycache__`) en una ubicación independiente.
- Solo se añadieron los tres documentos de `docs/integrante3/`.

## Decisiones que necesito del equipo (D1–D5)
- **D1.** ¿Este zip es la versión más reciente, o los integrantes 1 y 2 ya tienen código (auth, documentos, BD) que debo ver?
- **D2.** Motor de BD: ¿SQLite provisional aislado para mi módulo, o ya hay uno decidido?
- **D3.** Autenticación: ¿quién la implementa y con qué contrato (JWT, sesión, cabecera)? Mientras tanto, ¿acepto el sustituto de desarrollo?
- **D4.** Proveedor de IA: ¿local (Ollama u otro) o remoto (¿cuál?)
- **D5.** Frontend: ¿el destino real es React (`App.tsx`) o el prototipo `index.html`? ¿Autorizas el cambio mínimo de montaje?
