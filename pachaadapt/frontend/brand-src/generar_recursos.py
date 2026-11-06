#!/usr/bin/env python3
"""Genera los recursos gráficos de PACHAADAPT en frontend/public/brand/.

Uso (desde frontend/):  python brand-src/generar_recursos.py
Requiere: fonttools, Pillow y Playwright+Chromium (solo para los PNG).
Las fuentes se convierten a trazados: los SVG no dependen de ninguna fuente instalada.
Poppins se usa solo como forma de letra (licencia SIL OFL); no se distribuye el archivo de fuente.
"""
import os, sys, io
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

OUT = Path(__file__).resolve().parent.parent / "public" / "brand"
FONT_DIR = os.environ.get("PACHA_FONT_DIR", "/usr/share/fonts/truetype/google-fonts")

# ---- Tokens de marca (los mismos de styles.css; los «derivados» son tintas para ilustración)
LAKED, LAKE, QUI, GOLD, OCH, TERRA = "#143f56", "#1d5470", "#2e6b4f", "#e0a030", "#94600e", "#a5402c"
CREAM, PAPER, INK, LINE, MUTED = "#f7f3ec", "#fffdfa", "#2b2622", "#e2dacb", "#5f574c"
LAKEL, TERRAL = "#5b9ab5", "#d98b5f"          # derivados: azul lago claro, terracota claro
BLUEBG, GREENLINE, REDBG = "#e6eef2", "#a8cdb5", "#fbebe5"
ONDARK_MUTED = "#c9dbe4"

def w(name, text):
    p = OUT / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8"); return p

# ---- Texto a trazados --------------------------------------------------------
_fonts = {}
def font(name):
    if name not in _fonts:
        f = TTFont(f"{FONT_DIR}/{name}.ttf"); _fonts[name] = (f, f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm)
    return _fonts[name]
def text_path(txt, fname, size, x, y, fill, tracking=0.0):
    f, gs, cmap, upm = font(fname); s = size / upm; cx = 0.0; d = []
    for ch in txt:
        g = cmap[ord(ch)]; pen = SVGPathPen(gs, ntos=lambda v: str(round(v))); gs[g].draw(pen)
        d.append(f'<path transform="translate({cx:.1f} 0)" d="{pen.getCommands()}"/>')
        cx += f["hmtx"][g][0] + tracking * upm
    width = (cx - tracking * upm) * s
    return f'<g fill="{fill}" transform="translate({x:.2f} {y:.2f}) scale({s:.5f} -{s:.5f})">{"".join(d)}</g>', width

# ---- La marca: «Andén y sol» -------------------------------------------------
# Dos laderas de andenes (terrazas andinas, la adaptación de la tierra al cultivo) forman un
# valle abierto como un libro; sobre él sale el sol del conocimiento. Seis columnas de colores
# distintos = diversidad: familia fría a la izquierda, cálida a la derecha.
PITCH, CW, CR, BASE = 9.7, 8.7, 2, 54
X0 = 3.4
TOPS = [14, 26, 38, 38, 26, 14]
FILLS = [LAKED, QUI, LAKEL, TERRAL, TERRA, OCH]
def mark_inner(mono=None, sun_fill=GOLD):
    out = []; ops = [1, .7, .45, .45, .7, 1]
    for i, (t, c) in enumerate(zip(TOPS, FILLS)):
        x = round(X0 + i * PITCH, 2); fill = c if mono is None else mono
        op = "" if mono is None else f' fill-opacity="{ops[i]}"'
        bl = 4 if i == 0 else 0.6; br = 4 if i == 5 else 0.6
        out.append(f'<path fill="{fill}"{op} d="M{x} {BASE-bl}V{t+CR}a{CR} {CR} 0 0 1 {CR} -{CR}h{round(CW-2*CR,2)}a{CR} {CR} 0 0 1 {CR} {CR}V{BASE-br}a{br} {br} 0 0 1 -{br} {br}h-{round(CW-bl-br,2)}a{bl} {bl} 0 0 1 -{bl} -{bl}z"/>')
    out.append(f'<circle cx="32" cy="24" r="8.5" fill="{sun_fill if mono is None else mono}"/>')
    return "".join(out)
def mark_svg(extra="", mono=None):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="PACHAADAPT"{extra}><title>PACHAADAPT</title>{mark_inner(mono)}</svg>\n'
def badge_inner(size=64, bg=CREAM, rx=14, pad_scale=0.86):
    s = size / 64 * pad_scale; tx = size / 2 - 32 * s; ty = size / 2 - 33 * s
    return f'<rect width="{size}" height="{size}" rx="{rx}" fill="{bg}"/><g transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})">{mark_inner()}</g>'

# ---- Logotipos ---------------------------------------------------------------
def wordmark(x, y, size, dark=False, tracking=0.02):
    a, wa = text_path("PACHA", "Poppins-Bold", size, x, y, "#ffffff" if dark else LAKED, tracking)
    b, wb = text_path("ADAPT", "Poppins-Bold", size, x + wa + size * tracking, y, GOLD if dark else TERRA, tracking)
    return a + b, wa + wb + size * tracking
def logo_horizontal(dark=False):
    wm, ww = wordmark(78, 44.5, 34, dark); W = round(78 + ww + 2)
    mark = f'<g>{badge_inner(64)}</g>' if dark else f'<g>{mark_inner()}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 64" role="img" aria-label="PACHAADAPT"><title>PACHAADAPT</title>{mark}{wm}</svg>\n'
def logo_stacked(dark=False):
    size = 40; wm, ww = wordmark(0, 0, size, dark); W = round(ww + 8)
    wm, ww = wordmark((W - ww) / 2, 150, size, dark)
    by, wby = text_path("by YACHAY", "Poppins-Medium", 14, 0, 0, ONDARK_MUTED if dark else MUTED, 0.06)
    by, wby = text_path("by YACHAY", "Poppins-Medium", 14, (W - wby) / 2, 176, ONDARK_MUTED if dark else MUTED, 0.06)
    s = 1.6; mk = f'<g transform="translate({W/2-32*s:.2f} 0) scale({s})">{mark_inner() if not dark else badge_inner(64)}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 184" role="img" aria-label="PACHAADAPT by YACHAY"><title>PACHAADAPT by YACHAY</title>{mk}{wm}{by}</svg>\n'

# ---- Iconos (24×24, trazo 1,75, esquinas redondeadas, color = currentColor) ---
DOC = '<path d="M14 3.5H7.5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V8z"/><path d="M14 3.5V8h4.5"/>'
ICONS = {
 "home": '<path d="M3.5 11 12 4l8.5 7"/><path d="M6 9.5V20h12V9.5"/><path d="M10 20v-5.5h4V20"/>',
 "actividades": '<rect x="5" y="4.5" width="14" height="16.5" rx="2.5"/><path d="M9 4.5V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v.5"/><path d="m8.8 13 2.2 2.2 4.2-4.4"/>',
 "entregas": '<path d="M3.5 13.5 6 5.5h12l2.5 8"/><path d="M3.5 13.5V19a1 1 0 0 0 1 1h15a1 1 0 0 0 1-1v-5.5h-5.5a3 3 0 0 1-6 0z"/>',
 "catalogo": '<rect x="3.5" y="4" width="4.5" height="16" rx="1"/><rect x="9.5" y="4" width="4.5" height="16" rx="1"/><path d="m16 5.6 3.8-1.1 3.6 14.3-3.8 1z"/>',
 "materiales": DOC + '<path d="M12 17v-5.5"/><path d="m9.7 13.6 2.3-2.4 2.3 2.4"/>',
 "documentos": DOC + '<path d="M9 12.5h6M9 15.5h6M9 9.5h2"/>',
 "asistente": '<path d="M4.5 6.5A2.5 2.5 0 0 1 7 4h10a2.5 2.5 0 0 1 2.5 2.5v7A2.5 2.5 0 0 1 17 16h-6l-4.5 4v-4H7a2.5 2.5 0 0 1-2.5-2.5z"/><path d="M12 7.2v4.6M9.7 9.5h4.6"/>',
 "preferencias": '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
 "informes": '<rect x="4.5" y="10" width="3.5" height="10" rx="1"/><rect x="10.25" y="4" width="3.5" height="16" rx="1"/><rect x="16" y="13" width="3.5" height="7" rx="1"/>',
 "sincronizacion": '<path d="M19.5 9a7.5 7.5 0 0 0-13.3-2.2L4.5 8.5"/><path d="M4.5 4v4.5H9"/><path d="M4.5 15a7.5 7.5 0 0 0 13.3 2.2l1.7-1.7"/><path d="M19.5 20v-4.5H15"/>',
 "estado": '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>',
 "perfil": '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/>',
 "wifi": '<path d="M3.5 9.5a12 12 0 0 1 17 0M6.5 12.8a8 8 0 0 1 11 0M9.3 16a4 4 0 0 1 5.4 0"/><circle cx="12" cy="19" r="1" fill="currentColor"/>',
 "wifi-off": '<path d="M3.5 9.5a12 12 0 0 1 4-2.6M20.5 9.5a12 12 0 0 0-6-3.3M6.5 12.8a8 8 0 0 1 2.7-1.7M17.5 12.8a8 8 0 0 0-1.5-1.3M9.3 16a4 4 0 0 1 5.4 0"/><circle cx="12" cy="19" r="1" fill="currentColor"/><path d="m4 4 16 16"/>',
 "check-circle": '<circle cx="12" cy="12" r="8.5"/><path d="m8.3 12.3 2.6 2.6 4.8-5"/>',
 "alerta": '<path d="M12 4 21 19.5H3z"/><path d="M12 10v4.2"/><circle cx="12" cy="16.9" r=".6" fill="currentColor"/>',
 "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5"/><circle cx="12" cy="8" r=".7" fill="currentColor"/>',
 "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
 "cerrar": '<path d="m6 6 12 12M18 6 6 18"/>',
 "descargar": '<path d="M12 4v11"/><path d="m7.5 10.8 4.5 4.5 4.5-4.5"/><path d="M5 19.5h14"/>',
 "libro-abierto": '<path d="M12 6.5C10 5 7.5 4.5 4 4.5v14c3.5 0 6 .5 8 2 2-1.5 4.5-2 8-2v-14c-3.5 0-6 .5-8 2z"/><path d="M12 6.5v14"/>',
 "docente": '<rect x="3.5" y="4" width="17" height="11" rx="1.5"/><path d="M8.5 20l3.5-5 3.5 5"/><path d="M8 8.5h8M8 11.5h5"/>',
 "estudiante": '<path d="m12 5 9.5 4.5L12 14 2.5 9.5z"/><path d="M6.5 11.7V16c1.5 1.5 3.3 2.3 5.5 2.3s4-.8 5.5-2.3v-4.3"/><path d="M21.5 9.5V15"/>',
 "idioma": '<path d="M3.5 6h10M8.5 4v2M5 6c.8 3.5 3.2 6 6 7M11.5 6C11 9.5 8 12.5 4.5 14"/><path d="m12.5 20 4-9 4 9M13.8 17h5.4"/>',
 "audio": '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
 "lectura-facil": '<circle cx="5.5" cy="7" r="1.5"/><circle cx="5.5" cy="12" r="1.5"/><circle cx="5.5" cy="17" r="1.5"/><path d="M10 7h10M10 12h10M10 17h7"/>',
 "ver": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
 "candado": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>',
 "guardado-local": '<rect x="7" y="3.5" width="10" height="17" rx="2"/><path d="m10.2 12.2 1.4 1.4 2.4-2.6"/><path d="M11 17.5h2"/>',
 "resumen": '<path d="M5 6.5h14M5 11.5h14M5 16.5h8"/><path d="m15.5 17.5 1.7 1.7 3.3-3.5"/>',
 "ayuda": '<circle cx="12" cy="12" r="8.5"/><path d="M9.7 9.5a2.4 2.4 0 0 1 4.7.6c0 1.6-2.4 2-2.4 3.4"/><circle cx="12" cy="16.8" r=".7" fill="currentColor"/>',
}
def sprite():
    sy = "".join(f'<symbol id="i-{k}" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{v}</g></symbol>\n' for k, v in ICONS.items())
    return f'<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n{sy}</svg>\n'

# ---- Ilustraciones -----------------------------------------------------------
def stairs(side, W, H, y0, n, sw, sh, fill, x0=0):
    pts = [(0, H)]; x = 0; y = y0
    for _ in range(n):
        pts += [(x, y), (x + sw, y)]; x += sw; y += sh
    pts.append((x, H))
    if side == "R": pts = [(W - px, py) for px, py in pts]
    return f'<polygon fill="{fill}" stroke="{CREAM}" stroke-width="2" stroke-linejoin="round" points="{" ".join(f"{a:g},{b:g}" for a,b in pts)}"/>'
def spark(cx, cy, r, fill=GOLD):
    k = r * .28
    return f'<path fill="{fill}" d="M{cx} {cy-r}Q{cx+k} {cy-k} {cx+r} {cy}Q{cx+k} {cy+k} {cx} {cy+r}Q{cx-k} {cy+k} {cx-r} {cy}Q{cx-k} {cy-k} {cx} {cy-r}z"/>'
def svg(vb, body, label, desc=""):
    W, H = vb
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{label}"><title>{label}</title>{body}</svg>\n'
def ground(W=240, H=160):
    return (stairs("L", W, H, 96, 4, 28, 12, LAKEL) + stairs("R", W, H, 96, 4, 28, 12, TERRAL) +
            stairs("L", W, H, 124, 3, 26, 9, LAKED) + stairs("R", W, H, 124, 3, 26, 9, TERRA) +
            f'<rect y="{H-14}" width="{W}" height="14" fill="{QUI}" opacity=".0"/>')
def hero():
    W, H = 960, 320
    b = f'<circle cx="480" cy="120" r="86" fill="none" stroke="{GOLD}" stroke-width="3" opacity=".2"/><circle cx="480" cy="120" r="64" fill="none" stroke="{GOLD}" stroke-width="3" opacity=".4"/><circle cx="480" cy="120" r="44" fill="{GOLD}"/>'
    for side, cols in (("L", (LAKEL, QUI, LAKED)), ("R", (TERRAL, TERRA, OCH))):
        b += stairs(side, W, H, 112, 6, 70, 18, cols[0]) + stairs(side, W, H, 166, 5, 66, 18, cols[1]) + stairs(side, W, H, 222, 4, 60, 14, cols[2])
    b += f'<g stroke="{LAKED}" stroke-width="3" stroke-linejoin="round"><path fill="{PAPER}" d="M480 262C450 248 414 247 388 256V308C414 299 450 300 480 314Z"/><path fill="{PAPER}" d="M480 262C510 248 546 247 572 256V308C546 299 510 300 480 314Z"/></g>'
    b += f'<g fill="none" stroke="{LINE}" stroke-width="3" stroke-linecap="round"><path d="M406 272c20-6 44-5 60 3M406 284c20-6 44-5 60 3M406 296c20-6 44-5 60 3M554 272c-20-6-44-5-60 3M554 284c-20-6-44-5-60 3"/></g>'
    b += spark(430, 208, 12) + spark(540, 196, 9, QUI) + spark(596, 226, 7, TERRA) + f'<circle cx="372" cy="226" r="5" fill="{LAKE}"/><circle cx="318" cy="76" r="5" fill="{GOLD}"/><circle cx="650" cy="72" r="5" fill="{LAKEL}"/>'
    return svg((W, H), b, "Paisaje de andenes con el sol saliendo sobre un libro abierto")
def empty_actividades():
    b = ground() + f'<rect x="84" y="26" width="72" height="92" rx="9" fill="{PAPER}" stroke="{LAKED}" stroke-width="3"/><rect x="104" y="19" width="32" height="14" rx="6" fill="{GOLD}" stroke="{LAKED}" stroke-width="3"/>'
    for i, y in enumerate((52, 74, 96)):
        b += f'<circle cx="99" cy="{y}" r="6" fill="{QUI if i<2 else "none"}" stroke="{QUI}" stroke-width="2.5"/>' + (f'<path d="m96 {y} 2.4 2.4 4-4.4" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>' if i<2 else "") + f'<path d="M112 {y}h30" stroke="{LINE}" stroke-width="4" stroke-linecap="round"/>'
    b += f'<g transform="rotate(35 176 92)"><rect x="170" y="52" width="12" height="52" rx="2" fill="{TERRA}"/><path d="M170 104h12l-6 14z" fill="{GOLD}"/></g>'
    return svg((240, 160), b, "Lista de actividades con tareas marcadas y un lápiz")
def empty_materiales():
    b = ground() + f'<rect x="62" y="96" width="116" height="22" rx="4" fill="{LAKED}"/><rect x="72" y="72" width="100" height="22" rx="4" fill="{QUI}"/><rect x="58" y="48" width="108" height="22" rx="4" fill="{TERRA}"/>'
    b += f'<g stroke="{PAPER}" stroke-width="3" stroke-linecap="round" opacity=".85"><path d="M72 107h22M84 83h20M70 59h24"/></g><path d="m172 26-5 12 12-2z" fill="{GOLD}" opacity="0"/>' + spark(184, 44, 12) + spark(46, 64, 7, QUI)
    return svg((240, 160), b, "Pila de materiales de estudio")
def empty_asistente():
    b = ground() + f'<path fill="{LAKED}" d="M52 32a10 10 0 0 1 10-10h76a10 10 0 0 1 10 10v36a10 10 0 0 1-10 10H92l-20 16V78h-10a10 10 0 0 1-10-10z"/><path d="M68 40h60M68 54h40" stroke="{CREAM}" stroke-width="4" stroke-linecap="round"/>'
    b += f'<path fill="{PAPER}" stroke="{LAKED}" stroke-width="3" d="M96 76a10 10 0 0 1 10-10h76a10 10 0 0 1 10 10v26a10 10 0 0 1-10 10h-6v14l-18-14h-52a10 10 0 0 1-10-10z" transform="translate(-6 -6)"/>' + spark(170, 40, 13) + f'<path d="M96 80h56M96 92h36" stroke="{LINE}" stroke-width="4" stroke-linecap="round" transform="translate(0 0)"/>'
    return svg((240, 160), b, "Conversación con una burbuja de asistente y un destello")
def offline():
    b = ground() + f'<g fill="none" stroke="{LAKED}" stroke-width="6" stroke-linecap="round"><path d="M66 62a74 74 0 0 1 108 0"/><path d="M85 82a46 46 0 0 1 70 0"/><path d="M104 100a18 18 0 0 1 32 0"/></g><circle cx="120" cy="114" r="6" fill="{LAKED}"/><path d="M62 28 178 120" stroke="{CREAM}" stroke-width="14" stroke-linecap="round"/><path d="M62 28 178 120" stroke="{TERRA}" stroke-width="6" stroke-linecap="round"/>' + spark(196, 38, 8, QUI) + f'<circle cx="46" cy="52" r="5" fill="{GOLD}"/>'
    return svg((240, 160), b, "Señal de red interrumpida sobre los andenes")
def adaptacion():
    W, H = 480, 220
    b = f'<rect x="24" y="52" width="112" height="116" rx="12" fill="{PAPER}" stroke="{LAKED}" stroke-width="3"/><path d="M42 82h76M42 100h76M42 118h50M42 136h64" stroke="{LINE}" stroke-width="5" stroke-linecap="round"/><rect x="42" y="68" width="40" height="8" rx="4" fill="{GOLD}"/>'
    t, _ = text_path("Un material", "Poppins-Medium", 13, 36, 192, LAKED); b += t
    chips = [(230, 22, QUI, "audio", "Audio"), (230, 64, LAKE, "lectura-facil", "Lectura fácil"), (230, 106, TERRA, "idioma", "Otro idioma"), (230, 148, OCH, "resumen", "Resumen")]
    for i, (x, y, c, ic, lab) in enumerate(chips):
        b += f'<path d="M138 110C180 110 190 {y+20} {x} {y+20}" fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round" stroke-dasharray="1 7"/>'
        b += f'<rect x="{x}" y="{y}" width="226" height="40" rx="20" fill="{c}"/><circle cx="{x+20}" cy="{y+20}" r="13" fill="{PAPER}"/>'
        t, _ = text_path(lab, "Poppins-Medium", 15, x + 44, y + 25.5, "#ffffff"); b += t
        g = ICONS[ic]
        b += f'<g transform="translate({x+12} {y+12}) scale(.67)" fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">{g}</g>'
    return svg((W, H), b, "Un mismo material se adapta a audio, lectura fácil, otro idioma y resumen")

# ---- PNG (PWA) ---------------------------------------------------------------
def icon_svg(size, kind):
    if kind == "any":      # baldosa redondeada, esquinas transparentes
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">{badge_inner(size, CREAM, size*0.22, 0.86)}</svg>'
    s = size / 64 * (0.78 if kind == "maskable" else 0.84)   # maskable: marca dentro del círculo seguro (80 %)
    tx = size / 2 - 32 * s; ty = size / 2 - 33 * s
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}"><rect width="{size}" height="{size}" fill="{CREAM}"/><g transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})">{mark_inner()}</g></svg>'
def rasterize():
    from playwright.sync_api import sync_playwright
    from PIL import Image
    jobs = [("icon-192.png", 192, "any"), ("icon-512.png", 512, "any"), ("icon-maskable-512.png", 512, "maskable"), ("apple-touch-icon.png", 180, "maskable"), ("favicon-32.png", 32, "any"), ("favicon-48.png", 48, "any"), ("favicon-16.png", 16, "any")]
    with sync_playwright() as p:
        br = p.chromium.launch()
        for name, size, kind in jobs:
            pg = br.new_page(viewport={"width": size, "height": size})
            pg.set_content(f'<html><body style="margin:0;background:transparent">{icon_svg(size, kind)}</body></html>')
            pg.screenshot(path=str(OUT / name), omit_background=True, clip={"x": 0, "y": 0, "width": size, "height": size}); pg.close()
        br.close()
    for name, *_ in jobs:                       # aligerar: paleta de 64 colores conservando transparencia
        im = Image.open(OUT / name).convert("RGBA")
        q = im.quantize(colors=64, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        q.save(OUT / name, optimize=True)
    ims = [Image.open(OUT / f"favicon-{n}.png").convert("RGBA") for n in (16, 32, 48)]
    ims[2].save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)], append_images=ims[:2])
    for n in (16, 48): (OUT / f"favicon-{n}.png").unlink()

def main():
    w("pachaadapt-marca.svg", mark_svg())
    w("pachaadapt-marca-mono.svg", mark_svg(mono=LAKED))
    w("pachaadapt-insignia.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="PACHAADAPT"><title>PACHAADAPT</title>{badge_inner(64)}</svg>\n')
    w("favicon.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect x=".5" y=".5" width="63" height="63" rx="14" fill="{CREAM}" stroke="{LINE}"/><g transform="translate(2.56 1.64) scale(.92)">{mark_inner()}</g></svg>\n')
    w("logo-horizontal.svg", logo_horizontal(False)); w("logo-horizontal-oscuro.svg", logo_horizontal(True))
    w("logo-vertical.svg", logo_stacked(False)); w("logo-vertical-oscuro.svg", logo_stacked(True))
    w("iconos.svg", sprite())
    for n, f in (("ilustracion-aprendizaje.svg", hero), ("vacio-actividades.svg", empty_actividades), ("vacio-materiales.svg", empty_materiales),
                 ("vacio-asistente.svg", empty_asistente), ("sin-conexion.svg", offline), ("adaptacion-diversidad.svg", adaptacion)):
        w(f"ilustraciones/{n}", f())
    rasterize()
    # hoja de iconos de la PWA se referencia desde manifest.json (ver docs/identidad_grafica.md)
if __name__ == "__main__": main()
