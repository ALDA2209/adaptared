"""Exporta la hoja de solución de una comunidad a PDF (español o inglés).

Usa reportlab con las fuentes estándar de PDF, así que no necesita archivos de fuentes
ni programas del sistema. El contenido lo arma app/solution.py con los datos de la comunidad.
"""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import i18n, solution

INK = colors.HexColor("#13262B")
MUTED = colors.HexColor("#4A5F63")
TEAL = colors.HexColor("#17606B")
LINE = colors.HexColor("#C9D6D6")
SOFT = colors.HexColor("#EEF3F1")
LEVEL_BG = {
    "bajo": colors.HexColor("#2E7D4F"),
    "moderado": colors.HexColor("#E0A526"),
    "alto": colors.HexColor("#D9731F"),
    "critico": colors.HexColor("#B3261E"),
}
LEVEL_FG = {"bajo": colors.white, "moderado": INK, "alto": colors.white, "critico": colors.white}

TEXT = {
    "es": {
        "title": "Hoja de solución",
        "tagline": "AdaptaRed · Qué hacer, quién y para cuándo",
        "issued": "Emitido el",
        "demo": "Demostración: las cifras de clima, población y riesgo son simuladas. No las use para tomar decisiones reales.",
        "msg": "Mensaje listo para enviar por radio y WhatsApp",
        "a_check": "", "a_action": "Qué hacer", "a_who": "Quién", "a_when": "Fecha límite",
        "tick": "Marque la casilla cuando la acción esté hecha.",
        "coord": "Coordina: {contact}.",
        "none": "No hay acciones urgentes esta semana: el riesgo es bajo en las tres amenazas. Mantener la vigilancia y revisar el pronóstico cada día.",
        "footer": "AdaptaRed · Datos de demostración",
        "page": "Página",
        "loc": "Distrito de {district}, provincia de {province}",
        "facts": "{pop} personas en {hh} hogares · {elev} m s. n. m. · Cultivos: {crops}",
    },
    "en": {
        "title": "Solution sheet",
        "tagline": "AdaptaRed · What to do, who, and by when",
        "issued": "Issued on",
        "demo": "Demo: the climate, population and risk figures are simulated. Do not use them for real decisions.",
        "msg": "Ready-to-send message for radio and WhatsApp",
        "a_check": "", "a_action": "What to do", "a_who": "Who", "a_when": "Deadline",
        "tick": "Tick the box when the action is done.",
        "coord": "Coordinated by: {contact}.",
        "none": "There are no urgent actions this week: risk is low for all three hazards. Keep watching and check the forecast every day.",
        "footer": "AdaptaRed · Demo data",
        "page": "Page",
        "loc": "{district} district, {province} province",
        "facts": "{pop} people in {hh} households · {elev} m above sea level · Crops: {crops}",
    },
}


class _Box(Flowable):
    """Casilla vacía para marcar cuando la acción esté hecha."""

    def __init__(self, size: float = 4.2 * mm):
        super().__init__()
        self.size = size

    def wrap(self, aw, ah):
        return self.size, self.size

    def draw(self):
        self.canv.setStrokeColor(INK)
        self.canv.setLineWidth(0.9)
        self.canv.rect(0, 0, self.size, self.size, stroke=1, fill=0)


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=10, leading=14, textColor=INK, alignment=TA_LEFT)
    return {
        "base": base,
        "small": ParagraphStyle("small", parent=base, fontSize=8.5, leading=11, textColor=MUTED),
        "tag": ParagraphStyle("tag", parent=base, fontSize=9, leading=12, textColor=TEAL, fontName="Helvetica-Bold"),
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=23, leading=27),
        "h2": ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=14, leading=18, spaceBefore=12, spaceAfter=2),
        "cell": ParagraphStyle("cell", parent=base, fontSize=9.5, leading=12.5),
        "cellb": ParagraphStyle("cellb", parent=base, fontSize=9.5, leading=12.5, fontName="Helvetica-Bold"),
        "head": ParagraphStyle("head", parent=base, fontSize=8.5, leading=11, textColor=MUTED, fontName="Helvetica-Bold"),
        "demo": ParagraphStyle("demo", parent=base, fontSize=8.5, leading=11, textColor=colors.HexColor("#7A5600")),
        "msg": ParagraphStyle("msg", parent=base, fontSize=10, leading=14),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)), style)


def _chip(level: str, label: str, st: dict) -> Table:
    fg = LEVEL_FG[level].hexval().replace("0x", "#")
    chip = Table([[Paragraph(f'<font color="{fg}"><b>{escape(label)}</b></font>', st["cell"])]], hAlign="LEFT")
    chip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LEVEL_BG[level]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return chip


def _stamp(lang: str, today) -> str:
    return f"{today.day} {i18n.MONTHS[lang][today.month - 1]} {today.year}"


def build_solution_pdf(c: dict, hazards: list[dict], plans: list[dict], obs: list[dict], lang: str = "es") -> bytes:
    """Genera la hoja de solución de una comunidad y la devuelve como bytes."""
    lang = lang if lang in TEXT else "es"
    t = TEXT[lang]
    st = _styles()
    levels = i18n.LEVEL_LABELS[lang]
    width = A4[0] - 36 * mm  # márgenes de 18 mm
    sol = solution.build_solution(c, hazards, plans, obs, lang)

    buf = BytesIO()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, f"{t['footer']}  ·  {c['name']}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"{t['page']} {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
        title=f"{t['title']} - {c['name']}", author="AdaptaRed",
    )
    out: list = []

    crops = i18n.crops_en(c.get("main_crops") or "") if lang == "en" else (c.get("main_crops") or "")
    out.append(_p(t["tagline"], st["tag"]))
    out.append(Spacer(1, 3))
    out.append(_p(f"{t['title']}: {c['name']}", st["h1"]))
    out.append(Spacer(1, 3))
    out.append(_p(t["loc"].format(district=c["district"], province=c["province"]), st["base"]))
    out.append(_p(t["facts"].format(pop=f"{c['population']:,}", hh=f"{c['households']:,}", elev=f"{c['elevation']:,}", crops=crops or "-"), st["small"]))
    out.append(_p(f"{t['issued']} {_stamp(lang, sol['today'])}", st["small"]))
    out.append(Spacer(1, 6))

    demo = Table([[_p(t["demo"], st["demo"])]], colWidths=[width])
    demo.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBF0CC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    out.append(demo)

    if not sol["blocks"]:
        out.append(Spacer(1, 10))
        out.append(_p(t["none"], st["base"]))

    for b in sol["blocks"]:
        head = Table([[_p(b["name"], st["h2"]), _chip(b["level"], levels[b["level"]], st)]], colWidths=[width - 34 * mm, 34 * mm])
        head.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ]))
        msg = Table([[_p(b["message"], st["msg"])]], colWidths=[width])
        msg.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
            ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        out.append(KeepTogether([
            head,
            _p(b["why"], st["small"]),
            Spacer(1, 6),
            _p(t["msg"], st["head"]),
            Spacer(1, 2),
            msg,
            Spacer(1, 6),
        ]))

        rows = [[_p(t["a_check"], st["head"]), _p(t["a_action"], st["head"]), _p(t["a_who"], st["head"]), _p(t["a_when"], st["head"])]]
        for a in b["actions"]:
            rows.append([_Box(), _p(a["text"], st["cell"]), _p(a["who"], st["cell"]), _p(a["when"], st["cellb"])])
        grid = Table(rows, colWidths=[9 * mm, width - 9 * mm - 38 * mm - 30 * mm, 38 * mm, 30 * mm], repeatRows=1)
        grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
            ("BACKGROUND", (0, 0), (-1, 0), SOFT),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 1), (0, -1), 7),
        ]))
        out.append(grid)

    if sol["blocks"]:
        out.append(Spacer(1, 8))
        out.append(_p(t["tick"] + "  " + t["coord"].format(contact=sol["contact"]), st["small"]))

    doc.build(out, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
