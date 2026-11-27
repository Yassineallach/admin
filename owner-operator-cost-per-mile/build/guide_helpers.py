"""Quick-start guide PDF for the Owner-Operator Cost Per Mile & Load Profit Calculator (Brass Ledger style, US Letter).

Screenshots come from shoot.py (real renders of the SAMPLE workbook). The worked example uses the test model on the sample
data, so every number in the guide matches the workbook.
Usage: python guide.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (Flowable, Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

sys.path.insert(0, "/home/user/admin/productivity-bundle/build")
import brand as BR  # noqa: E402
import md_to_pdf  # noqa: E402,F401  (registers the Body / Head fonts)

from brandimg import logo_rgba  # noqa: E402
from test_workbook import load_model, settings_model  # noqa: E402
import truck_config as CFG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "owner-operator-cost-per-mile" / CFG.GUIDE_NAME
PW, PH = LETTER
SIDE = 20 * mm
CW = PW - 2 * SIDE
GREEN, BRASS, PAPER, INK, INK2, BORDER = BR.GREEN, BR.BRASS, BR.PAPER, BR.INK, BR.INK2, BR.BORDER
BRASS_TINT, CALC, POS_TINT = "F6EBD3", "F1ECE2", "E4EFE8"


def c(h):
    return colors.HexColor("#" + h)


S = {
    "kicker": ParagraphStyle("k", fontName="Body-Bold", fontSize=8, leading=11, textColor=c(BRASS), spaceAfter=2),
    "h1": ParagraphStyle("h1", fontName="Head", fontSize=23, leading=27, textColor=c(GREEN), spaceAfter=4),
    "h2": ParagraphStyle("h2", fontName="Head", fontSize=13.5, leading=17, textColor=c(GREEN), spaceBefore=9, spaceAfter=4),
    "p": ParagraphStyle("p", fontName="Body", fontSize=10, leading=14.3, textColor=c(INK), alignment=TA_LEFT, spaceAfter=5),
    "small": ParagraphStyle("s", fontName="Body", fontSize=8.5, leading=12, textColor=c(INK2), spaceAfter=4),
    "cell": ParagraphStyle("c", fontName="Body", fontSize=8.8, leading=11.8, textColor=c(INK)),
    "cellb": ParagraphStyle("cb", fontName="Body-Bold", fontSize=8.8, leading=11.8, textColor=c(INK)),
    "cellh": ParagraphStyle("ch", fontName="Body-Bold", fontSize=8.8, leading=11.8, textColor=c(PAPER)),
    "callout": ParagraphStyle("co", fontName="Body", fontSize=9.8, leading=14, textColor=c(INK)),
}


def spaced(t):
    return "   ".join(" ".join(w) for w in t.upper().split())


class Rule(Flowable):
    def __init__(self, width=70, em=24):
        super().__init__()
        self.w, self.em = width, em

    def wrap(self, aw, ah):
        return self.w, self.em * 0.2

    def draw(self):
        cv, e = self.canv, self.em
        cv.setFillColor(c(BRASS))
        cv.rect(0, e * 0.12, self.w, e * 0.075, stroke=0, fill=1)
        cv.rect(0, e * 0.12 - 0.072 * e, self.w, e * 0.022, stroke=0, fill=1)


def P(t, st="p"):
    return Paragraph(t, S[st])


def section(kicker, title):
    return [P(spaced(kicker), "kicker"), P(title, "h1"), Rule(), Spacer(1, 10)]


def bullets(items, numbered=False):
    return ListFlowable([ListItem(P(t), leftIndent=14) for t in items], bulletType="1" if numbered else "bullet",
                        start="1" if numbered else None, bulletFontName="Body-Bold", bulletFontSize=9, bulletColor=c(BRASS), leftIndent=14)


def table(rows, widths, head=True, bold_first=False):
    data = []
    for i, r in enumerate(rows):
        st = "cellh" if head and i == 0 else "cell"
        data.append([Paragraph(str(x), S["cellb" if (bold_first and j == 0 and st == "cell") else st]) for j, x in enumerate(r)])
    t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1 if head else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.5, c(BORDER)), ("BACKGROUND", (0, 0), (-1, -1), colors.white),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 5)]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), c(GREEN)))
    t.setStyle(TableStyle(style))
    return t


def callout(text, tint=BRASS_TINT):
    t = Table([[Paragraph(text, S["callout"])]], colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c(tint)), ("LINEBEFORE", (0, 0), (0, -1), 3, c(BRASS)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def shot(name, width=CW, crop=None, max_h=None):
    from PIL import Image as PI
    p = SCREENS / f"{name}.png"
    im = PI.open(p)
    if crop:
        w, h = im.size
        im = im.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
        p = Path(tempfile.mkdtemp()) / f"{name}.png"
        im.save(p)
    w, h = im.size
    if max_h and width * h / w > max_h:
        width = max_h * w / h
    img = Image(str(p), width=width, height=width * h / w)
    t = Table([[img]], colWidths=[width + 8])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, c(BORDER)), ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t



