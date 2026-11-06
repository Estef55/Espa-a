"""Genera los PDF de demostración (solo desarrollo; requiere reportlab y Pillow). Los PDF generados ya se incluyen."""
from pathlib import Path
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).parent
styles = getSampleStyleSheet()
AVISO = "MATERIAL DE DEMOSTRACIÓN — no es un material curricular oficial."


def diagram(path: Path):
    im = Image.new("RGB", (480, 260), "white")
    d = ImageDraw.Draw(im)
    d.ellipse((20, 20, 90, 90), fill=(250, 200, 40))
    for k in range(6):
        d.line((90 + k * 10, 60 + k * 14, 190, 120 + k * 8), fill=(250, 170, 20), width=3)
    d.rectangle((235, 150, 250, 250), fill=(110, 80, 40))
    d.ellipse((190, 70, 300, 170), fill=(60, 150, 70))
    d.line((340, 250, 400, 230), fill=(70, 70, 200), width=4)
    im.save(path)


def build(name, story):
    SimpleDocTemplate(str(HERE / name), pagesize=A4, title=name, author="PACHAADAPT (demostración)").build(story)


def p(text, style="BodyText"):
    return Paragraph(text, styles[style])


img = HERE / "_diagrama.png"
diagram(img)
build("DEMO_fotosintesis.pdf", [
    p(AVISO, "Italic"), p("La fotosíntesis", "Title"),
    p("La fotosíntesis es el proceso por el cual las plantas fabrican su propio alimento. Para hacerlo usan la luz del sol, el agua y el dióxido de carbono del aire."),
    p("Dónde ocurre", "Heading2"),
    p("La fotosíntesis ocurre principalmente en las hojas. Dentro de las células de las hojas hay cloroplastos, que contienen clorofila. La clorofila es el pigmento verde que captura la luz."),
    RLImage(str(img), width=300, height=162),
    p("Figura 1: La luz del sol, el agua y el dióxido de carbono llegan a la hoja; la planta produce glucosa y libera oxígeno."),
    p("Qué se necesita y qué se obtiene", "Heading2"),
    p("Las raíces absorben agua del suelo. Las hojas toman dióxido de carbono del aire por unos pequeños orificios llamados estomas. Con la energía de la luz, la planta produce glucosa y libera oxígeno."),
    p("Por qué es importante", "Heading2"),
    p("Gracias a la fotosíntesis las plantas obtienen alimento y el oxígeno que respiramos llega al aire. Muchos animales se alimentan de plantas, por eso la fotosíntesis sostiene a casi todos los seres vivos."),
])
rows = [["Etapa", "Qué ocurre"], ["Evaporación", "El calor del sol convierte el agua en vapor."],
        ["Condensación", "El vapor se enfría y forma nubes."], ["Precipitación", "El agua cae como lluvia, granizo o nieve."],
        ["Escorrentía", "El agua corre por el suelo hacia ríos y lagos."]]
t = Table(rows, colWidths=[110, 330])
t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)]))
build("DEMO_ciclo_del_agua.pdf", [
    p(AVISO, "Italic"), p("El ciclo del agua", "Title"),
    p("El agua de la Tierra se mueve continuamente entre los océanos, el aire y el suelo. Este recorrido se llama ciclo del agua y no se detiene nunca."),
    p("Etapas del ciclo", "Heading2"), t, Spacer(1, 12),
    p("El agua que cae en las montañas alimenta ríos y lagos, y parte se filtra y forma aguas subterráneas. Las plantas también devuelven agua al aire por sus hojas."),
    p("Por qué importa", "Heading2"),
    p("El ciclo del agua renueva el agua dulce que usamos para beber, cultivar y vivir. Cuidar el agua ayuda a que el ciclo continúe."),
])
img.unlink()
