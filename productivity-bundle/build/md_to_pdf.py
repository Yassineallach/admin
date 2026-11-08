"""Render the bundle's Markdown guides to branded PDFs (headings, paragraphs, bullets, numbered lists, tables)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import BG, BLUE, BORDER, DARK, LIGHT_GRAY, MIDNIGHT, NAVY, SECONDARY  # noqa: E402

FONT_DIR = Path("/usr/share/fonts/truetype/liberation")
pdfmetrics.registerFont(TTFont("Body", str(FONT_DIR / "LiberationSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("Body-Bold", str(FONT_DIR / "LiberationSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("Body-Oblique", str(FONT_DIR / "LiberationSans-Italic.ttf")))
pdfmetrics.registerFont(TTFont("Sym", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Oblique", boldItalic="Body-Bold")


def c(h):
    return colors.HexColor("#" + h)


ST = {
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=20, leading=25, textColor=colors.white),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=13, leading=17, textColor=c(NAVY), spaceBefore=10, spaceAfter=4),
    "h3": ParagraphStyle("h3", fontName="Body-Bold", fontSize=11, leading=14, textColor=c(MIDNIGHT), spaceBefore=6, spaceAfter=2),
    "p": ParagraphStyle("p", fontName="Body", fontSize=9.5, leading=13.5, textColor=c(DARK), alignment=TA_LEFT, spaceAfter=4),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.3, leading=10.5, textColor=c(DARK)),
    "cellh": ParagraphStyle("cellh", fontName="Body-Bold", fontSize=8.3, leading=10.5, textColor=colors.white),
}


def inline(t: str) -> str:
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"([◆▲‼⋮⌂✓▼])", r'<font name="Sym">\1</font>', t)
    t = re.sub(r"`(.+?)`", rf'<font color="#{BLUE}">\1</font>', t)
    return t


def table(rows):
    data = [[Paragraph(inline(x), ST["cellh" if i == 0 else "cell"]) for x in r] for i, r in enumerate(rows)]
    n = len(rows[0])
    avail = A4[0] - 36 * mm
    lens = [max(len(r[j]) for r in rows) for j in range(n)]
    tot = sum(min(x, 60) + 6 for x in lens)
    widths = [avail * (min(x, 60) + 6) / tot for x in lens]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c(NAVY)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c(BG)]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, c(BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def render(md_path: Path, pdf_path: Path, footer: str = "Ultimate Productivity Bundle"):
    lines = md_path.read_text(encoding="utf-8").splitlines()
    story, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("# "):
            t = Table([[Paragraph(inline(ln[2:]), ST["h1"])]], colWidths=[A4[0] - 36 * mm])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c(NAVY)), ("TOPPADDING", (0, 0), (-1, -1), 10),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 10), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
            story += [t, Spacer(1, 8)]
        elif ln.startswith("## "):
            story.append(Paragraph(inline(ln[3:]), ST["h2"]))
        elif ln.startswith("### "):
            story.append(Paragraph(inline(ln[4:]), ST["h3"]))
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", x) for x in cells):
                    rows.append(cells)
                i += 1
            story += [table(rows), Spacer(1, 6)]
            continue
        elif re.match(r"^(\s*)([-*]|\d+\.) ", ln):
            items, numbered = [], bool(re.match(r"^\s*\d+\.", ln))
            while i < len(lines) and re.match(r"^(\s*)([-*]|\d+\.) ", lines[i]):
                txt = re.sub(r"^(\s*)([-*]|\d+\.) ", "", lines[i])
                indent = len(lines[i]) - len(lines[i].lstrip())
                items.append(ListItem(Paragraph(inline(txt), ST["p"]), leftIndent=12 + indent * 4))
                i += 1
            story.append(ListFlowable(items, bulletType="1" if numbered else "bullet", start="1" if numbered else None,
                                      bulletFontName="Body", bulletFontSize=8, bulletColor=c(BLUE), leftIndent=12))
            continue
        elif ln.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(lines[i].lstrip(">").strip())
                i += 1
            paras, cur = [], []
            for q in quote + [""]:
                if q:
                    cur.append(q)
                elif cur:
                    paras.append(" ".join(cur))
                    cur = []
            t = Table([[Paragraph(inline(q), ST["p"])] for q in paras], colWidths=[A4[0] - 36 * mm])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c(BG)), ("LINEBEFORE", (0, 0), (0, -1), 3, c(BLUE)),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            story += [t, Spacer(1, 6)]
            continue
        elif ln.strip():
            story.append(Paragraph(inline(ln), ST["p"]))
        i += 1

    def on_page(cv, doc):
        cv.saveState()
        cv.setFillColor(c(SECONDARY))
        cv.setFont("Body", 7.5)
        cv.drawString(18 * mm, 10 * mm, footer)
        cv.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        cv.setStrokeColor(c(LIGHT_GRAY))
        cv.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
        cv.restoreState()

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title=md_path.stem.replace("_", " "))
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        p = Path(a)
        render(p, p.with_suffix(".pdf"))
        print("wrote", p.with_suffix(".pdf"))
