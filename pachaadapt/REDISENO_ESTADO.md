# PACHAADAPT — Rediseño visual: estado y auditoría

**Fase 03/14 — Identidad gráfica y recursos visuales: ✅ COMPLETADA (2026-11-05)** (build pendiente de verificar en máquina del equipo). Detalle en «Registro Fase 03» al final; la Fase 02 está en «Registro Fase 02». La auditoría de la Fase 01 sigue vigente debajo.

## Estado de las fases

| Fase | Estado |
|---|---|
| 01 Auditoría y preparación | ✅ Completada |
| **02 Sistema visual base** | ✅ **Completada** (`npm run build` no ejecutable en este entorno: sin red) |
| **03 Identidad gráfica y recursos visuales** | ✅ **Completada** (solo recursos y metadatos PWA; nada de `src/` modificado) |
| 04–14 | ⏳ Sin iniciar |

Línea base verificada antes de cualquier cambio:
- `npm test` (frontend, 5 archivos): **36 de 36 pruebas OK**.
- `tests/frontend/test_frontend_contract.py` (contrato frontend↔backend): **4 de 4 OK** (ejecutar con `python -m unittest discover -s tests/frontend -t .`).
- No hay `node_modules` en el ZIP y el entorno no tiene red, por lo que `tsc -b && vite build` **no se pudo ejecutar** en esta fase. Debe hacerse en la máquina del equipo (`npm ci && npm run build`) antes y después de cada fase.

---

## 1. Estructura del proyecto

```
/
├─ backend/app/        FastAPI: api/v1 (15 routers), services, core, db.py   ← NO TOCAR
├─ ai/                 Proveedor de IA (model_gateway), asistente, adaptaciones, informes ← NO TOCAR
├─ database/           schema*.sql, migraciones SQLite/PostgreSQL, seed       ← NO TOCAR
├─ scripts/            setup, start_server, backup, restore, import_materials
├─ tests/              pruebas Python (ai, backend, frontend contract)
├─ docs/               manuales y arquitectura
├─ frontend/           React 19 + TypeScript + Vite (PWA), sin librerías de UI
│  ├─ index.html       theme-color #205b79, título «PACHAADAPT by YACHAY»
│  ├─ public/          manifest.json, service-worker.js, offline.html
│  ├─ tests/           5 archivos de prueba (node --test)
│  └─ src/
│     ├─ main.tsx · App.tsx · context.tsx · styles.css (48 líneas, todo el CSS)
│     ├─ components/ui.tsx        (único archivo de componentes compartidos)
│     ├─ pages/                   12 pantallas
│     ├─ hooks/                   useAsync, usePendingOps
│     ├─ lib/                     router, permissions, format, types, conflicts, csv, quiz, …
│     ├─ services/                12 servicios API (http.ts + uno por módulo)
│     ├─ offline/                 IndexedDB, cola de sincronización, caché, service-worker
│     └─ i18n/                    es.json, qu.json (4–5 líneas; **no se importan en ningún sitio**)
└─ *.md                README, informes de integración, configuración de IA
```

Datos útiles: ~2 260 líneas en `frontend/src`; el estilo es **compacto en una sola línea por regla**, sin Tailwind, sin CSS Modules, sin librería de componentes ni iconos. El único CSS es `styles.css`, importado desde `App.tsx`. No hay estilos en línea (`style={{…}}`) en ninguna página.

## 2. App.tsx, styles.css y ui.tsx (hallazgos)

**App.tsx (64 líneas).** `AppProvider` → `Shell`. El `Shell` contiene: enlace «Saltar al contenido», `header.topbar` (botón Menú, marca, chip de conexión, chip «Demostración · Rol»), `nav.sidebar` agrupado por `ROUTES[].group`, `main#contenido` con avisos globales (backend caído, sin conexión, conflictos) y la página activa, y `footer.foot`. La página se reinicia con `key={route:role:user:epoch}`. El título de `document.title` y el foco al `h1` forman parte de la accesibilidad actual.

**styles.css (48 líneas).** Paleta en variables `:root` (`--lake`, `--lake-d`, `--quinoa`, `--ochre`, `--red`, `--green-bg`, `--blue-bg`, `--ochre-bg`, `--red-bg`, `--ink`, `--muted`, `--bg`, `--surface`, `--line`, `--radius:8px`). Tipografía del sistema (Segoe UI/system-ui). Breakpoints: 900 px y 760 px. Respeta `prefers-reduced-motion`. Foco visible ámbar de 3 px.

**ui.tsx (49 líneas).** Exporta: `PageHeader`, `Panel`, `Notice`, `Loading`, `EmptyState`, `StatusPill`, `Field`, `ErrorNotice`, `Gate`, `OfflineNotice`, `CachedNotice`, `NotConnected`.

## 3. Pantallas existentes (12)

Rutas por hash `#/id`, definidas en `lib/router.ts` (`ROUTES`) y renderizadas en el mapa `PAGES` de `App.tsx`. Si el hash no existe, cae a `inicio`.

| # | Ruta | Archivo (líneas) | Grupo de menú | Quién la usa | Notas |
|---|---|---|---|---|---|
| 1 | `inicio` | `Inicio.tsx` (60) | General | Estudiante, docente, admin | Tarjetas de resumen (`.stats`), accesos por rol, estado de integraciones, aulas. |
| 2 | `actividades` | `Actividades.tsx` (113) | Trabajo en aula | Estudiante (responde) · Docente/admin (crea/edita) | Borradores locales y cola offline. |
| 3 | `entregas` | `Entregas.tsx` (99) | Trabajo en aula | Estudiante («Mis entregas») · Docente/admin («Entregas recibidas», revisa, exporta CSV) | Etiqueta cambia según rol. |
| 4 | `catalogo` | `Catalogo.tsx` (79) | Materiales | Todos leen · Docente/admin escriben | Caché local en IndexedDB. |
| 5 | `materiales` | `Materiales.tsx` (144) | Materiales | **Solo docente** (`Gate materials.upload`) | Subir PDF/TXT, extraer, adaptar. |
| 6 | `documentos` | `Documentos.tsx` (207) | Asistente docente | **Solo docente** (`Gate documents`) | Editor con versiones; borradores offline. La más grande. |
| 7 | `asistente` | `Asistente.tsx` (91) | Asistente docente | **Solo docente** (`Gate chat`) | Chat con IA; layout `.split.chat`. |
| 8 | `preferencias` | `Preferencias.tsx` (73) | Asistente docente | **Solo docente** (`Gate preferences`) | Preferencias del asistente. |
| 9 | `informes` | `Informes.tsx` (81) | Asistente docente | **Solo docente** (`Gate reports`) | Informes con Markdown descargable. |
| 10 | `sincronizacion` | `Sincronizacion.tsx` (81) | Sistema | Todos; foco real en **estudiante** (cola/conflictos) | Reintentar, resolver conflictos, estado servidor. |
| 11 | `estado` | `Estado.tsx` (37) | Sistema | Todos; detalle de IA solo docente | Tabla de funciones. |
| 12 | `perfil` | `Perfil.tsx` (38) | Sistema | Todos | Cambia el perfil de demostración (estudiante/docente/admin) y usuario. |

### Docente vs. estudiante

- **Comunes (7):** Inicio, Actividades, Entregas, Catálogo, Conexión y sincronización, Estado y Perfil. Actividades, Entregas y Catálogo cambian de contenido según el rol; en Sincronización la cola de envío solo existe para el estudiante.
- **Solo docente (5):** Archivos y adaptación, Documentos editables, Asistente de IA, Preferencias, Informes. En el menú siguen visibles para el estudiante con la etiqueta «Docente», y al entrar muestran el aviso «Permisos insuficientes» (`Gate`).
- **Rol admin:** existe en `lib/permissions.ts` (actividades, revisión, catálogo) pero no tiene pantallas propias.
- **Solo estudiante, lógica funcional:** el envío automático de cola en `context.tsx` y la cola de respuestas (`Actividades`, `Entregas`, `Sincronizacion`).

## 4. Rutas y navegación

- Navegación por hash sin dependencias (`parseHash`, `hrefFor`, `routeLabel` en `lib/router.ts`). Funciona con la PWA sin red.
- Menú lateral con 5 grupos: General, Trabajo en aula, Materiales, Asistente docente, Sistema.
- En móvil (≤760 px) el menú pasa a panel desplegable (`.sidebar.open`), se cierra con `hashchange` y con Esc.
- Los enlaces internos dentro de páginas usan `href="#/…"` directos (Asistente, Entregas, Actividades, Materiales, Inicio, `Gate`).
- `RouteDef` tiene `only` (rol) y `needsConnection`, pero **solo `only` se usa** (para la etiqueta «Docente»); `needsConnection` no se usa en la interfaz.

## 5. Componentes compartidos

**En `components/ui.tsx`:** `PageHeader` (enfoca el h1), `Panel`, `Notice` (error/success/info/warn, `role` alert/status), `Loading`, `EmptyState`, `StatusPill`, `Field`, `ErrorNotice` (traduce `ApiError.kind`), `Gate` (usa `can()` y `useApp`), `OfflineNotice`, `CachedNotice`, `NotConnected`.

**Compartidos fuera de `ui.tsx`:** `Shell` dentro de `App.tsx` (cabecera, menú, avisos globales, pie), `context.tsx` (`AppProvider/useApp`), hooks `useAsync` y `usePendingOps`.

**Patrones repetidos que NO son componentes** (solo clases CSS copiadas en cada página, candidatos a extraer en fases posteriores): tarjeta de estadística (`.stat`), listas de selección (`.pick`), pares clave-valor (`.kv/.kv-row`, 12 usos), tabla de datos (`table.data`), burbujas de chat (`.msg`), tarjeta de elemento (`.card`), barra de herramientas/filtros (`.toolbar`), botones (`.btn*`, 57 usos).

**Clases más usadas:** `.hint` (27), `.btn-primary` (21), `.btn-quiet` (19), `.btn` (17), `.row` (14), `.kv-row` (13), `.grid-2` (12), `.form` (9), `.meta` (8).

## 6. Uso de servicios API por página

(Todas las llamadas HTTP salen de `services/http.ts › request`; las páginas **nunca** llaman a `fetch` directamente.)

| Página | Servicios / módulos que utiliza |
|---|---|
| Inicio | `assignments.service` (fetchAssignments, fetchMaterials, getSubmissions), `classrooms.service`, `auth.service` (ROLE_LABEL), contexto (`ai`) |
| Actividades | `assignments.service` (fetch/create/update/createSubmission/getSubmissions), `offline/adaptation-store` (borradores), `usePendingOps` |
| Entregas | `assignments.service` (fetchAssignments, getSubmissions, reviewSubmission), `lib/csv`, `usePendingOps` |
| Catálogo | `assignments.service` (fetchMaterials, createMaterial), `offline/local-db` (`localDB`) |
| Materiales | `materials.service` (upload, extract, adapt, get), `documents.service.createDocument`, `lib/uploadIndex` (localStorage), `lib/hash`, `offline/adaptation-store` |
| Documentos | `documents.service` (list/get/create/save/import/versions/restore/archive), `offline/adaptation-store` (borradores, listas y snapshots) |
| Asistente | `ai.service` (sendChat, getConversation, saveAssistantProposal), `documents.service.listDocuments`, `localStorage` (`pacha-chat:<usuario>`) |
| Preferencias | `preferences.service` |
| Informes | `reports.service`, `lib/csv.downloadText` |
| Sincronización | `offline/sync-queue` (retryRejected, synchronize, queueSubmission), `offline/local-db`, `assignments.service`, `sync.service` (status, pull), `lib/conflicts` |
| Estado | `auth.service.getHealth`, contexto (`ai`) |
| Perfil | `auth.service` (perfiles demo), `sync.service.getServerSyncStatus`, `lib/permissions` |

Servicios: `adaptations`, `ai`, `assignments`, `auth`, `classrooms`, `documents`, `http`, `materials`, `preferences`, `reports`, `review`, `sync`. Existe `adaptations.service.ts` que ninguna página importa directamente.

## 7. Groq, Ollama, IndexedDB y sincronización

**Groq / Ollama — solo existen en el backend, el frontend no los menciona.**
- `ai/model_gateway.py`: `OpenAICompatibleProvider`; alias `openai`, `groq`, `ollama` comparten el contrato `/chat/completions`; `key_required` para `openai` y `groq`; `NotConfiguredProvider` nunca inventa respuestas.
- `.env.example`: `PACHAADAPT_AI_PROVIDER=groq`, `BASE_URL=https://api.groq.com/openai/v1`, modelo `llama-3.3-70b-versatile`, `API_KEY` vacía (solo en `.env`, nunca en el frontend).
- `ai/settings.py`, `ai/env_file.py`, `CONFIGURACION_SERVICIOS_IA.md`.
- Lo único visible en la interfaz: `AiStatus` (`ai_provider_configured`, etc.) vía `GET /api/v1/ai-chat/status` → contexto `ai` → `Inicio` («Estado de integraciones»), `Estado`, `Asistente` (aviso `NotConnected`, y `reply.provider · reply.model` como metadato de cada respuesta).
- **Implicación de diseño:** el rediseño puede cambiar *cómo se muestra* ese estado, pero nunca debe leer, mostrar ni solicitar la clave.

**IndexedDB (dos bases independientes):**
- `pachaadapt-offline` v2 (`offline/local-db.ts`): `PendingOperation` (cola), caché de actividades y materiales (`offline/cache-manager.ts`).
- `pachaadapt-adaptations` v1 (`offline/adaptation-store.ts`): adaptaciones, borradores de respuestas, borradores/listas/snapshots de documentos (con `MemoryKV` de reserva).
- Además: `localStorage` para perfil (`auth.service`), `pacha-last-sync`, `pacha-chat:<usuario>`, índice de subidas (`lib/uploadIndex`).

**Sincronización:**
- `offline/sync-queue.ts` (`queueSubmission`, `synchronize`, `retryRejected`, `belongsToCurrentActor`), `offline/sync-status.ts` (`watchSyncStatus`), `services/sync.service.ts`, `lib/conflicts.ts`.
- Eventos globales de `window`: `online/offline`, `pacha-sync-change`, `pacha-sync-conflict`, `pacha-sync-rejected`.
- `context.tsx` los consume y dispara `synchronize()` al abrir como estudiante, al cambiar de perfil y al volver el backend (`checkBackend` cada 15 s).
- Service worker: `public/service-worker.js` (caché de shell `pachaadapt-shell-v2`, omite `/api/`) y `offline.html`. Registro en `main.tsx` solo en producción.
- Backend de sync (`/api/v1/synchronization/{push,pull,status}`) está cubierto por el test de contrato.

## 8. Funciones críticas que NO deben modificarse

Durante todo el rediseño solo se permite cambiar **presentación** (JSX de estructura/clases, CSS, textos visuales). Intocables:

1. **Backend, base de datos y `ai/`** completos (incluido `model_gateway.py`, `.env.example`, esquemas y migraciones).
2. **`src/services/*`** (rutas, métodos, cabeceras, tiempos, manejo de `ApiError`). El test de contrato lee estos archivos con expresiones regulares: no renombrar ni reformatear las cadenas `"/api/v1/…"`.
3. **`src/offline/*`** (`sync-queue`, `local-db`, `cache-manager`, `adaptation-store`, `sync-status`, `service-worker`) y `public/service-worker.js`.
4. **`src/lib/permissions.ts`, `lib/conflicts.ts`, `lib/types.ts`, `lib/csv.ts`, `lib/hash.ts`, `lib/uploadIndex.ts`, `lib/submissions.ts`** y la lógica de `format.ts` (`dateLabel`, `isSafeResourceUrl`).
5. **`src/context.tsx`**: eventos de sincronización, identidad (`setActor` antes del primer render), `checkBackend`, `epoch`.
6. **`src/lib/router.ts`**: ids de ruta, `parseHash`, `hrefFor`, `only` (solo se puede añadir metadatos visuales, p. ej. iconos, en una fase explícita).
7. **`Gate`, `can()` y la reinicialización por `key` en `App.tsx`** (evitan que datos de un perfil se muestren en otro).
8. **Accesibilidad funcional ya existente:** foco al `h1` en `PageHeader`, enlace «Saltar al contenido», `role="alert|status"` en `Notice`, `aria-current`, `aria-expanded`, tablas con `caption`/`scope`, `aria-live` del chat, `:focus-visible`, `prefers-reduced-motion`.
9. **Cabeceras de demostración y avisos de honestidad:** «Demostración · Rol», el pie sobre autenticación real/HTTPS, y los avisos «generado por IA», «puede contener errores», «revisión humana obligatoria».
10. **`frontend/tests/*`** y **`tests/frontend/test_frontend_contract.py`**: deben seguir pasando tras cada fase (incluido `test_frontend_has_no_secrets`: no escribir en CSS/TSX nada que parezca `api_key: "…"`).
11. **Textos que la lógica compara:** p. ej. `message.startsWith("Guard…")` en `Materiales.tsx`: si se reformulan mensajes, revisar antes la condición.

## 9. Problemas visuales detectados

**Sistema**
- Todo el CSS está compactado en reglas de una línea: ilegible, difícil de revisar y propenso a conflictos al rediseñar.
- No hay tokens de espaciado, tipografía (escala), sombras ni elevación; los radios y colores están en parte fijos: `#9aa9af`, `#eef3f5`, `#edf1f2`, `#f0f4f5`, `#ffffff1f`, `#e0a030` y similares aparecen repetidos sin variable.
- Tipografía 100 % del sistema (Segoe UI), sin personalidad de marca; jerarquía débil (h1 1.6 rem, h2 1.1 rem, h3 1 rem).
- Sin modo oscuro ni `color-scheme`; `theme-color` del HTML (`#205b79`) no coincide con `--lake` (`#1d4e6b`) ni con la barra superior (`--lake-d`).
- No hay iconografía ni imagen de marca: la marca es un cuadro con la letra «P».
- Cadena i18n (`es.json`, `qu.json`) sin uso: no hay selector de idioma ni textos externalizados.

**Estructura y navegación**
- Barra superior pesada (azul oscuro + borde ocre de 4 px) con dos chips que compiten por la atención.
- Menú lateral solo de texto, sin iconos ni jerarquía visual; el estudiante ve 5 opciones de docente con una etiqueta «Docente» que llevan a un aviso de bloqueo. Esto es ruido para el estudiante y debe resolverse en una fase de navegación (visual, sin tocar permisos).
- En móvil el menú es un panel completo con `inset:62px 0 0 0` y la altura de la barra superior es variable (envuelve en 2 filas), por lo que el panel puede quedar desalineado.
- No hay indicación de migas, ni acciones fijas, ni navegación inferior para móvil/estudiante.
- Pie de página con aviso largo, sin jerarquía.

**Páginas y componentes**
- Las pantallas son casi todas «panel blanco + borde fino» apiladas: monotonía, poca jerarquía entre contenido primario y secundario.
- `Inicio`: cuatro `.stat` idénticas sin color ni icono; sin diferencia visual entre estudiante y docente; no hay mensaje de bienvenida con contexto de aprendizaje.
- `Actividades` / `Entregas` / `Catálogo`: tarjetas de lista con borde izquierdo verde uniforme; estados solo con `pill` de bajo contraste.
- `Documentos` (207 líneas) y `Materiales` (144): formularios largos y listas de selección (`.pick`) en columnas desiguales; el editor de texto no tiene área de trabajo propia.
- `Asistente`: el chat es un cuadro de altura fija (340 px), burbujas básicas, sin avatares ni estado de «escribiendo» claro; el panel de contexto queda estrecho.
- `Sincronizacion` y `Estado`: tablas y listas técnicas sin jerarquía; para un estudiante el estado de conexión debería ser comprensible de un vistazo.
- `Perfil`: formulario de demostración sin identidad visual de rol.
- Avisos (`Notice`) muy parecidos entre sí; el `pill` de «borrador» y «devuelta» comparten color (`ochre`).
- Botones: `btn-quiet` y `btn` casi indistinguibles; no hay variante destructiva/peligro ni tamaños.
- Formularios: `input` con borde gris `#9aa9af` y sin estados hover/disabled definidos; `.field-label` sin indicador de obligatorio.
- Accesibilidad: `.chip` blanco sobre fondo translúcido y `.chip.demo` ocre sobre crema tienen contraste justo; `.hint` `#55666d` sobre fondo `#f4f6f6` roza el mínimo AA en tamaños pequeños (.78–.85 rem).
- Los objetivos táctiles de `.nav-link` (40 px) y `.btn` (42 px) son inferiores a 44 px en escritorio; en móvil suben a 46 px.

## 10. Estilos reutilizables y estilos que necesitan renovación

**Reutilizar (conservar tal cual o con ajuste de valores):**
- Los **nombres de variables** de color (`--lake`, `--quinoa`, `--ochre`, etc.) y su carácter andino sobrio: se pueden redefinir sus valores sin cambiar las páginas.
- Utilidades de layout: `.row`, `.stack`, `.grid-2`, `.split`, `.toolbar`, `.form`, `.field`, `.table-wrap`, `.sr-only`, `.skip-link`, `.prewrap`, `.mono`, `.clip`.
- Accesibilidad: `:focus-visible`, `prefers-reduced-motion`, `.sr-only`, `.skip-link`.
- Lógica responsive de `.shell` (grid con áreas `top/nav/main/foot`) y breakpoints 900/760.
- La API de los componentes de `ui.tsx` (props) para que las 12 páginas no se rompan.
- Clases de estado `pill.*` y `notice.*` como contrato semántico (se pueden restilizar).

**Renovar:**
- `.topbar`, `.brand`, `.chip`, `.menu-btn` → nueva cabecera y marca.
- `.sidebar`, `.nav-*` → navegación con iconos, jerarquía y versión móvil (barra inferior o cajón).
- `.panel`, `.card`, `.stat`, `.stats`, `.pick`, `.msg`, `.chat-log` → superficies, elevación y variantes.
- `.btn*` → sistema de botones (primario/secundario/fantasma/peligro, tamaños, iconos).
- `input/select/textarea`, `.field*`, `.check` → sistema de formularios.
- `table.data`, `.kv*`, `.linklist`, `.statuslist` → tablas y listas.
- `.empty`, `.loading`, `.spinner`, `.notice` → estados vacíos, carga (esqueletos) y avisos.
- Tipografía y escala, espaciado y sombras: **crear tokens**.
- `h1/h2/h3` globales y `.page-head`.

## 11. Archivos que se modificarán en cada fase

Propuesta de plan de 14 fases (la Fase 01 es esta auditoría). Solo se permite modificar los archivos listados; todo lo no listado es intocable.

| Fase | Objetivo | Archivos permitidos |
|---|---|---|
| 01 | Auditoría (hecha) | `REDISENO_ESTADO.md` |
| 02 | Tokens y sistema base (colores, tipografía, espaciado, sombras, radios, reset legible) | `frontend/src/styles.css`, `frontend/index.html` (solo `theme-color`/fuentes), `REDISENO_ESTADO.md` |
| 03 | Botones, formularios y campos | `styles.css`, `components/ui.tsx` (solo marcado/clases de `Field`) |
| 04 | Componentes de estado: avisos, pills, vacíos, carga, errores | `styles.css`, `components/ui.tsx` |
| 05 | Estructura de la aplicación: cabecera, marca, pie | `App.tsx` (solo marcado y clases), `styles.css` |
| 06 | Navegación: menú lateral/móvil, grupos, etiqueta «Docente» | `App.tsx`, `styles.css`, `lib/router.ts` (solo metadatos visuales, p. ej. iconos, si se aprueba) |
| 07 | Inicio (estudiante/docente) | `pages/Inicio.tsx`, `styles.css` |
| 08 | Actividades y Entregas | `pages/Actividades.tsx`, `pages/Entregas.tsx`, `styles.css` |
| 09 | Catálogo y Materiales | `pages/Catalogo.tsx`, `pages/Materiales.tsx`, `styles.css` |
| 10 | Documentos editables | `pages/Documentos.tsx`, `styles.css` |
| 11 | Asistente de IA y Preferencias | `pages/Asistente.tsx`, `pages/Preferencias.tsx`, `styles.css` |
| 12 | Informes | `pages/Informes.tsx`, `styles.css` |
| 13 | Sincronización, Estado y Perfil | `pages/Sincronizacion.tsx`, `pages/Estado.tsx`, `pages/Perfil.tsx`, `styles.css` |
| 14 | Revisión final: contraste, responsive, accesibilidad, PWA (`manifest.json`, `offline.html`), documentación | `styles.css`, `public/manifest.json`, `public/offline.html`, `docs/frontend_interfaz.md`, `REDISENO_ESTADO.md` |

Al terminar **cada** fase: ejecutar `npm run build`, `npm test`, `python -m unittest discover -s tests/frontend -t .`, revisar en 360 px, 768 px y 1280 px, y actualizar la tabla de estado de este documento.

## 12. Riesgos para el rediseño

- **Sin build verificable aquí:** hasta ejecutar `npm ci && npm run build` en local no hay garantía de tipos. Pedir al equipo la salida del build en la línea base.
- **Un solo `styles.css`:** todas las fases lo editan; conviene conservar los nombres de clase existentes y añadir nuevas, retirando las antiguas solo en la fase 14.
- **Páginas con `.startsWith`/textos acoplados** a mensajes (ver §8.11).
- **Modo sin conexión:** cualquier fuente web externa (Google Fonts, CDN, iconos remotos) **rompe la promesa offline**; usar fuentes del sistema o incluirlas localmente en `public/` y añadirlas al `SHELL` del service worker (cambio que requeriría autorización explícita, porque el service worker es intocable).
- **Compatibilidad PWA:** si cambia `theme-color`, mantener `manifest.json` coherente.
- **Pruebas de contrato** leen el código fuente de servicios y buscan «credenciales» en `.css/.ts/.tsx/.json`.


---

## Registro Fase 02 — Sistema visual base

**Archivos modificados (solo los autorizados):** `frontend/src/styles.css`, `frontend/index.html` (únicamente `theme-color`), `REDISENO_ESTADO.md`. No se creó `REDISENO_CONTINUIDAD.md` porque la fase no quedó incompleta.

**Cambios realizados**
- `styles.css` reescrito de 48 líneas compactas a un archivo legible de ~1 150 líneas, con una regla por bloque y 15 secciones numeradas (tokens, base, accesibilidad, estructura, cabecera, navegación, contenido, superficies, utilidades, formularios, botones, avisos/pills, datos, responsive, movimiento reducido). **Se conservó el orden de la cascada y las 88 clases originales** (verificado por script: ninguna falta, ninguna nueva).
- **Tokens en `:root`:** color (neutros cálidos, marca, familias de estado fondo/borde/tinta, señales de conexión, sobre-oscuro, enlace y foco), tipografía (3 pilas + escala `--text-xs … --text-3xl`, pesos, interlineado), espaciado (`--space-1 … --space-12`), radios (`--radius-xs/sm/md/lg/pill`; `--radius` se mantiene como alias), sombras (`--shadow-xs … lg`, tinte cálido) y estructura (`--sidebar-w`, `--content-max`, z-index).
- **Paleta:** papel crema (`--bg #f7f3ec`, `--surface #fffdfa`), tinta cálida, azul lago `#1d5470` / `#143f56`, verde quinua, ocre, dorado y terracota. Se mantuvieron los **nombres** de variables anteriores (`--lake`, `--quinoa`, `--ochre`, `--red`, `--ink`, `--muted`, `--bg`, `--surface`, `--line`, `--*-bg`, `--radius`) con valores nuevos.
- **Tipografía:** sin recursos externos. Títulos h1/h2 con pila serif humanista del sistema (Iowan Old Style → Palatino → Georgia); texto y h3 con la pila sans original. h1 fluido de 24 a 30 px; h2 20 px; h3 18 px; `.lead` 18 px; `.hint/.meta` 14 px.
- **Global:** fondo y `color-scheme: light`, `::selection`, enlaces con subrayado siempre visible (el hover de color solo afecta a `a:not([class])` para no pisar `.btn`, `.brand`, `.nav-link`), superficies `.panel/.card/.stat` con borde cálido y `--shadow-xs`.
- Todos los colores literales fuera de `:root` se reemplazaron por tokens (verificado: 0 hex fuera de `:root`; 0 variables usadas sin definir).
- **Accesibilidad conservada y reforzada:** `:focus-visible`, `.sr-only`, `.skip-link`, `prefers-reduced-motion`, breakpoints 900/760 intactos. El anillo de foco pasó de `#e0a030` (≈2:1 sobre fondo claro) a `#b8780f` (≥3:1 sobre `--bg`, `--surface`, `--blue-bg` y `--lake-d`). El borde de controles `--line-strong` alcanza 3.7:1 sobre blanco.
- `index.html`: `theme-color` `#205b79` → `#143f56`, igual que la barra superior (`--lake-d`). Título y `<head>` sin más cambios; no se añadieron fuentes (no hacen falta).

**Contraste medido (WCAG, calculado con script)**: tinta/fondo 13.5:1; texto secundario/fondo 6.4:1; blanco/`--lake` 8.2:1; blanco/`--lake-d` 11.2:1; tintas de estado sobre su fondo 7.3–9.5:1; ocre sobre ocre-bg 4.75:1.

**Lo que NO se tocó (por alcance):** forma de botones, formularios, navegación, avisos y páginas (secciones marcadas «pendiente de rediseño» en el CSS). Sus tamaños de fuente y paddings siguen literales; los tokens de color/radio/foco ya los alimentan.

**Tokens reservados para fases siguientes (definidos, aún sin uso):** `--gold`, `--radius-lg`, `--shadow-sm/md/lg`, `--space-12`, `--text-xs`, `--text-3xl`, `--weight-medium`.

**Pruebas ejecutadas (resultados reales)**
- `npm test`: **36 de 36 OK**.
- `python -m unittest discover -s tests/frontend -t ..`: **4 de 4 OK**.
- `npm run build`: **NO se pudo ejecutar.** `npm ci` falla con `ENOTFOUND registry.npmjs.org` (sin red); los errores de `tsc` que aparecieron fueron por un `node_modules` incompleto, no por el cambio. Se eliminaron `node_modules` y `tsconfig.tsbuildinfo` generados por el intento. Los cambios son solo CSS y una meta, sin impacto en tipos, pero **debe ejecutarse `npm ci && npm run build` en la máquina del equipo**.
- Verificación visual extra: render en Chromium (Playwright) de un HTML estático con el marcado real de las clases (cabecera, menú, panel, tarjetas, pills, avisos, tabla, campo, vacío) a 1280 px y 360 px: sin desborde horizontal (scrollWidth = ancho de ventana). **No** se probó la app React real.

**Observaciones para las siguientes fases**
- `public/manifest.json` sigue con `theme_color #205b79` y `background_color #f4f7f5`; no estaba autorizado en esta fase. Alinear con `#143f56` y `#f7f3ec` en la Fase 14 (o antes si se autoriza).
- `.chip.demo` y `.pill.*` ahora usan tintas de estado con buen contraste; la Fase 04 puede refinar su forma.
- Los objetivos táctiles (`.nav-link` 40 px, `.btn` 42 px en escritorio) siguen por debajo de 44 px: pendiente en Fases 03 y 06.


---

## Registro Fase 03 — Identidad gráfica y recursos visuales

**Fecha:** 2026-11-05. **Partida:** ZIP `pachaadapt_fase02_integrante2_integrado`.

**Nota de numeración.** El plan de la sección 11 (Fase 01) asignaba la Fase 03 a «Botones, formularios y campos». La instrucción recibida define la Fase 03 como identidad gráfica, y así se ejecutó. **Botones/formularios, avisos y estados, estructura (cabecera/pie), navegación, páginas y revisión final siguen pendientes**; el equipo debe decidir si renumera 04–14 o intercala las tareas de la tabla 11 (la integración de marca e iconos en cabecera y menú encaja en las fases «Estructura» y «Navegación» de esa tabla).

**Objetivo:** dotar a PACHAADAPT de identidad propia (hasta ahora, un cuadro con la letra «P») sin alterar funcionamiento.

**Cambios realizados**
- **Marca «Andén y sol»**: dos laderas de andenes (terrazas andinas = adaptación) forman un valle como un libro abierto con el sol saliendo; seis columnas de colores = diversidad. Evita estereotipos (sin chakana, sin personas ni fotos de banco de imágenes). Concepto y reglas de uso en `docs/identidad_grafica.md`.
- **Versiones**: marca a color, monocroma, insignia para cabecera oscura, logotipos horizontal y vertical (claro/oscuro; el vertical incluye «by YACHAY») para menú lateral y pantalla de acceso/portada, favicon, iconos PWA (192, 512, maskable 512), apple-touch-icon.
- **Iconos**: sprite `iconos.svg` con 30 iconos propios (uno por cada una de las 12 rutas + conexión, avisos, adaptación, roles, permisos, etc.), coherentes con la marca, `currentColor`.
- **Ilustraciones** (6): portada de aprendizaje, «un material → audio / lectura fácil / otro idioma / resumen» (adaptación y diversidad), 3 estados vacíos (actividades, materiales, asistente) y sin conexión.
- **Ligereza**: todo SVG/PNG propio, sin fuentes ni imágenes remotas ni scripts (verificado por script); texto del logotipo convertido a trazados; PNG cuantizados. **Total 64 166 bytes** (mayor archivo: 15 KB).
- **Metadatos PWA** (únicos archivos existentes tocados, no son páginas ni componentes): `frontend/index.html` (enlaces a favicon y apple-touch-icon) y `frontend/public/manifest.json` (lista `icons`; además `theme_color` → `#143f56` y `background_color` → `#f7f3ec`, pendiente anotado en Fase 02, necesario para que el icono y la pantalla de arranque coincidan con la paleta). Reversible quitando esos campos.
- Script reproducible `frontend/brand-src/generar_recursos.py` (fuera de `public/`, no se publica) y hoja de revisión `docs/identidad_grafica/vista_previa.html`.

**Archivos creados:** `frontend/public/brand/**` (21 archivos), `frontend/brand-src/generar_recursos.py`, `docs/identidad_grafica.md`, `docs/identidad_grafica/vista_previa.html`.
**Archivos modificados:** `frontend/index.html`, `frontend/public/manifest.json`, `REDISENO_ESTADO.md`. Comparado con el ZIP de partida (`diff -rq`): no hay ninguna otra diferencia; **`frontend/src/**`, backend, `ai/`, base de datos, migraciones, service worker y `styles.css` sin cambios.**

**Funcionalidades conservadas:** todas (no se tocó código funcional, servicios, permisos, contratos API, sincronización ni offline). Las pantallas siguen mostrando la marca antigua («P») hasta que se integren los recursos.

**Pruebas ejecutadas (resultados reales)**
- `npm test`: **48 de 48 OK** (6 archivos). *Nota:* la Fase 02 registró 36 pruebas en 5 archivos; el ZIP actual incluye `adaptations.test.ts` y el total es 48. No se investigó la diferencia de conteo más allá de eso.
- `python -m unittest discover -s tests/frontend -t .`: **4 de 4 OK**.
- Script de validación: 100 % de SVG bien formados; sin `http(s)://` externos, `<script>`, `<image>` ni `font-family`; iconos del manifiesto existen; tamaños PNG correctos (192, 512, 512, 180, 32).
- Revisión visual en Chromium (Playwright) de todos los recursos (hoja de vista previa) y prueba de `<use href="/brand/iconos.svg#i-…">` servida por HTTP: los 30 iconos se pintan. Se detectaron y corrigieron antes de entregar: líneas negras en las páginas del libro, iconos descentrados en las fichas y primer boceto de marca que parecía un gráfico de barras (se rehízo con columnas contiguas y sol mayor).
- `npm run build`: **NO ejecutado** (sin `node_modules` ni red, igual que en Fase 02). No se tocó TypeScript. Debe ejecutarse `npm ci && npm run build` en la máquina del equipo.
- **No probado:** instalación real de la PWA en un móvil (aspecto del icono maskable en los distintos lanzadores) ni la app React en navegador.

**Problemas encontrados / límites**
- No existe pantalla de inicio de sesión (perfiles de demostración en `#/perfil`): la versión «acceso» se dejó definida, no aplicada.
- Los recursos de `/brand/` no están en la precarga del service worker (`SHELL`, intocable): se guardan en caché en ejecución tras la primera carga con red. Para garantizar el primer arranque sin red con la identidad completa se necesita autorización para ampliar `SHELL` y subir `CACHE` (propuesto para Fase 14).
- Las ilustraciones y el logotipo son propuestas de diseño del asistente: conviene validarlas con el equipo/YACHAY. «by YACHAY» se tomó del título actual de la aplicación.
- La forma de letra del logotipo es Poppins (OFL); si el equipo prefiere otra, basta cambiar el archivo en el script y regenerar.

**Pendientes para las siguientes fases**
1. Integrar `pachaadapt-insignia.svg` en la cabecera y sustituir `.brand-mark` (Fase «Estructura»).
2. Añadir iconos al menú lateral/móvil con el mapa de `docs/identidad_grafica.md` y, si se aprueba, metadatos de icono en `lib/router.ts` (Fase «Navegación»).
3. Usar las ilustraciones en `EmptyState`, `Inicio`, Sin conexión y la portada de acceso (fases de estados y de páginas); decidir si `offline.html` adopta la marca (Fase 14).
4. Pendientes ya existentes: botones/formularios, avisos y estados, objetivos táctiles de 44 px, páginas 07–13, revisión final y `npm ci && npm run build` local.

**Instrucción para continuar:** «Continúa con la siguiente fase del rediseño (estructura de la aplicación: cabecera, marca y pie) partiendo de `pachaadapt_fase03_*.zip`, leyendo `REDISENO_ESTADO.md` y `docs/identidad_grafica.md`.»
