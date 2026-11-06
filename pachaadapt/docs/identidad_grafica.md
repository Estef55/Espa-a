# Identidad gráfica de PACHAADAPT

Recursos en `frontend/public/brand/` (se sirven como `/brand/…`, mismo origen). Sin fuentes ni imágenes remotas, sin scripts, sin librerías nuevas. **Total ≈ 64 KB** (SVG ≈ 50 KB, PNG ≈ 10 KB). Vista previa: abrir `docs/identidad_grafica/vista_previa.html` en el navegador.

## Concepto: «Andén y sol»

*Pacha* (tierra, mundo, tiempo) + *adapt*. Los **andenes** son terrazas con las que las comunidades andinas adaptaron la montaña al cultivo: adaptación en forma de escalera. Dos laderas escalonadas forman un valle abierto como un **libro**; sobre él sale el **sol** del conocimiento.

| Idea | Cómo se expresa |
|---|---|
| Educación / aprendizaje | Libro abierto (valle) y sol que sale; escalones ascendentes |
| Adaptación | Terrazas: el terreno se adapta a quien lo usa; la ilustración «un material → varios formatos» |
| Diversidad | Seis columnas de colores distintos bajo un mismo sol: familia fría (lago, quinua, lago claro) y cálida (terracota claro, terracota, ocre) |
| Calidez y tecnología | Papel crema, tintas cálidas, geometría simple y redondeada, tipografía geométrica |

No usa la chakana ni motivos textiles concretos (símbolos con significado propio que no conviene reducir a decoración), ni personas ni fotografías de banco de imágenes.

## Paleta y tipografía

Colores = tokens de `styles.css` (`--lake-d #143f56`, `--quinoa #2e6b4f`, `--red #a5402c`, `--ochre #94600e`, `--gold #e0a030`, `--bg #f7f3ec`). Dos tintas derivadas solo para ilustración: azul lago claro `#5b9ab5` y terracota claro `#d98b5f` (decorativas; nunca para texto). Logotipo: «PACHA» en `--lake-d` y «ADAPT» en `--red` (sobre oscuro: blanco y `--gold`). Las letras están **convertidas a trazados** (forma Poppins Bold/Medium, licencia SIL OFL): no hay dependencia de fuentes y la tipografía de la interfaz sigue siendo la del sistema.

## Inventario

| Archivo | Uso | Fondo |
|---|---|---|
| `pachaadapt-marca.svg` | Marca a color sola (menú lateral, avisos, vacíos) | claro |
| `pachaadapt-marca-mono.svg` | Una tinta (`--lake-d`), impresión, sellos | claro |
| `pachaadapt-insignia.svg` | **Cabecera**: baldosa crema con la marca (sustituye al cuadro «P») | oscuro (`--lake-d`) |
| `logo-horizontal.svg` / `-oscuro.svg` | Marca + nombre. Menú lateral/ficha / sobre `--lake-d` | claro / oscuro |
| `logo-vertical.svg` / `-oscuro.svg` | Marca + nombre + «by YACHAY». **Pantalla de acceso / portada** | claro / oscuro |
| `iconos.svg` | Sprite de 30 iconos de interfaz (`#i-<nombre>`) | hereda `currentColor` |
| `favicon.svg`, `favicon-32.png`, `favicon.ico` (16/32/48) | Pestaña del navegador | — |
| `icon-192.png`, `icon-512.png` | PWA (`purpose: any`, baldosa redondeada) | — |
| `icon-maskable-512.png` | PWA (`maskable`, marca dentro del 80 % central) | — |
| `apple-touch-icon.png` | iOS (180×180, sin transparencia) | — |
| `ilustraciones/ilustracion-aprendizaje.svg` | Portada / acceso / bienvenida (960×320) | claro |
| `ilustraciones/adaptacion-diversidad.svg` | Explica que un material se adapta a audio, lectura fácil, otro idioma y resumen (corresponde a módulos reales de `ai/adaptations`) | claro |
| `ilustraciones/vacio-actividades.svg`, `vacio-materiales.svg`, `vacio-asistente.svg` | Estados vacíos (240×160) | claro |
| `ilustraciones/sin-conexion.svg` | Aviso/pantalla sin conexión (240×160) | claro |

Iconos: `home, actividades, entregas, catalogo, materiales, documentos, asistente, preferencias, informes, sincronizacion, estado, perfil` (una por ruta), más `wifi, wifi-off, check-circle, alerta, info, menu, cerrar, descargar, libro-abierto, docente, estudiante, idioma, audio, lectura-facil, resumen, ver, candado, guardado-local, ayuda`. Rejilla 24 px, trazo 1,75, extremos redondeados.

## Cómo usarlos (para las fases 05–13; **no aplicado aún**)

```html
<!-- Cabecera (Fase 05): sustituye <span class="brand-mark">P</span>; el texto «PACHAADAPT» ya acompaña, por eso alt="" -->
<img src="/brand/pachaadapt-insignia.svg" width="38" height="38" alt="" />

<!-- Icono de menú (Fase 06): decorativo, hereda el color del texto -->
<svg width="20" height="20" aria-hidden="true" focusable="false"><use href="/brand/iconos.svg#i-home"/></svg>

<!-- Ilustración con significado: alt descriptivo. Decorativa: alt="" -->
<img src="/brand/ilustraciones/vacio-actividades.svg" width="240" height="160" alt="" />
```

Mapa ruta → icono sugerido: inicio `home`, actividades `actividades`, entregas `entregas`, catálogo `catalogo`, materiales `materiales`, documentos `documentos`, asistente `asistente`, preferencias `preferencias`, informes `informes`, sincronización `sincronizacion`, estado `estado`, perfil `perfil`. Etiqueta «solo docente»: `candado` o `docente`. Conexión: `wifi` / `wifi-off`.

Reglas: zona libre alrededor de la marca ≥ ½ de su ancho; no recolorear columnas ni deformar; tamaño mínimo de la marca 20 px (por debajo, usar `favicon.svg`); sobre fondos oscuros usar siempre `insignia` o las versiones `-oscuro`; los iconos nunca llevan solo color como información (acompañar con texto). No hay pantalla de inicio de sesión (el perfil de demostración está en `#/perfil`): la versión «acceso» queda definida para esa portada o para una futura autenticación real.

## Funcionamiento sin conexión

El service worker (intocable) guarda en caché en ejecución toda respuesta GET del mismo origen, así que lo que la app use de `/brand/` queda disponible sin red **tras la primera carga con conexión**. No está en la lista de precarga (`SHELL`): si se quiere garantizar el primer arranque sin red con la identidad completa, habrá que autorizar añadir `/brand/iconos.svg` y `/brand/pachaadapt-insignia.svg` a `SHELL` y subir la versión de caché (Fase 14). El icono instalado de la PWA lo guarda el sistema operativo al instalar.

## Regenerar

Desde `frontend/`: `python brand-src/generar_recursos.py` (requiere `fonttools`, `Pillow`, `playwright` con Chromium y la carpeta de fuentes Poppins en `PACHA_FONT_DIR`). El script contiene todas las formas y colores; editar allí y regenerar, no retocar los SVG a mano.
