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
from reportlab.platypus import Flowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand as BR  # noqa: E402

GREEN, BRASS, PAPER, INK, INK2, BORDER, BRASS_DARK = BR.GREEN, BR.BRASS, BR.PAPER, BR.INK, BR.INK2, BR.BORDER, BR.BRASS_DARK
pdfmetrics.registerFont(TTFont("Body", str(BR.INTER[400])))
pdfmetrics.registerFont(TTFont("Body-Bold", str(BR.INTER[700])))
pdfmetrics.registerFont(TTFont("Body-Semi", str(BR.INTER[600])))
pdfmetrics.registerFont(TTFont("Head", str(BR.FRAUNCES)))
pdfmetrics.registerFont(TTFont("Sym", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body", boldItalic="Body-Bold")
_CMAP = set(pdfmetrics.getFont("Body").face.charToGlyph)      # characters Inter (latin) can draw


def c(h):
    return colors.HexColor("#" + h)


ST = {
    "kicker": ParagraphStyle("kicker", fontName="Body-Bold", fontSize=7.5, leading=10, textColor=c(BRASS)),
    "h1": ParagraphStyle("h1", fontName="Head", fontSize=24, leading=28, textColor=c(PAPER)),
    "h2": ParagraphStyle("h2", fontName="Head", fontSize=15, leading=19, textColor=c(GREEN), spaceBefore=12, spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="Body-Bold", fontSize=8, leading=11, textColor=c(BRASS_DARK), spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="Body", fontSize=9.5, leading=13.8, textColor=c(INK), alignment=TA_LEFT, spaceAfter=4),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.3, leading=10.8, textColor=c(INK)),
    "cellh": ParagraphStyle("cellh", fontName="Body-Bold", fontSize=8.3, leading=10.8, textColor=c(PAPER)),
}


def spaced(t):
    """Uppercase kicker with letter-spacing of about 0.28em (a non-breaking space between letters, three between words)."""
    return "\u00a0\u00a0\u00a0".join("\u00a0".join(w) for w in t.upper().split())


def inline(t: str) -> str:
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", t)
    t = re.sub(r"`(.+?)`", rf'<font color="#{BRASS_DARK}">\1</font>', t)
    # anything Inter can't draw (symbols such as ✓ ⌂ ▲) falls back to the symbol font
    return "".join(ch if (ord(ch) in _CMAP or ch in "<>/=\"#&; ") else f'<font name="Sym">{ch}</font>' for ch in t)


def table(rows):
    data = [[Paragraph(inline(x), ST["cellh" if i == 0 else "cell"]) for x in r] for i, r in enumerate(rows)]
    n = len(rows[0])
    avail = A4[0] - 36 * mm
    lens = [max(len(r[j]) for r in rows) for j in range(n)]
    tot = sum(min(x, 60) + 6 for x in lens)
    widths = [avail * (min(x, 60) + 6) / tot for x in lens]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), c(GREEN)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c("F3EFE7")]),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, c(BORDER)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


class DoubleRule(Flowable):
    """Short brass double rule (the brand's mark under headlines)."""

    def __init__(self, width=60, em=14, color=BRASS):
        super().__init__()
        self.w, self.em, self.color = width, em, color
        self.height = em * 0.147 + 2

    def wrap(self, aw, ah):
        return self.w, self.height

    def draw(self):
        cv, em = self.canv, self.em
        cv.setFillColor(c(self.color))
        cv.rect(0, self.height - 0.075 * em, self.w, 0.075 * em, stroke=0, fill=1)
        cv.rect(0, self.height - 0.147 * em, self.w, 0.022 * em, stroke=0, fill=1)


def render(md_path: Path, pdf_path: Path, footer: str = "Brass Ledger"):
    lines = md_path.read_text(encoding="utf-8").splitlines()
    story, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("# "):
            title = ln[2:]
            kick = "Guide"
            for sep in (" — ", " - "):
                if sep in title:
                    a_, b_ = title.split(sep, 1)
                    kick, title = (a_, b_) if len(a_) < len(b_) else (b_, a_)
                    break
            t = Table([[Paragraph(spaced(kick), ST["kicker"])], [Paragraph(inline(title), ST["h1"])], [DoubleRule(90, 24)]],
                      colWidths=[A4[0] - 36 * mm])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c(GREEN)), ("LEFTPADDING", (0, 0), (-1, -1), 16),
                                   ("TOPPADDING", (0, 0), (-1, 0), 16), ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
                                   ("TOPPADDING", (0, 1), (-1, 1), 0), ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                                   ("TOPPADDING", (0, 2), (-1, 2), 2), ("BOTTOMPADDING", (0, 2), (-1, 2), 16)]))
            story += [t, Spacer(1, 12)]
        elif ln.startswith("## "):
            story.append(Paragraph(inline(ln[3:]), ST["h2"]))
        elif ln.startswith("### "):
            story.append(Paragraph(spaced(ln[4:]), ST["h3"]))
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
                                      bulletFontName="Body-Bold", bulletFontSize=8, bulletColor=c(BRASS_DARK), leftIndent=12))
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
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("LINEBEFORE", (0, 0), (0, -1), 3, c(BRASS)),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            story += [t, Spacer(1, 6)]
            continue
        elif ln.strip():
            story.append(Paragraph(inline(ln), ST["p"]))
        i += 1

    def on_page(cv, doc):
        cv.saveState()
        cv.setFillColor(c(PAPER))
        cv.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        # logo bottom-left: wordmark with its brass double rule
        x, y, em = 18 * mm, 10.5 * mm, 11
        cv.setFillColor(c(GREEN))
        cv.setFont("Head", em)
        cv.drawString(x, y, BR.NAME)
        w = pdfmetrics.stringWidth(BR.NAME, "Head", em)
        cv.setFillColor(c(BRASS))
        cv.rect(x, y - 0.24 * em, w, 0.075 * em, stroke=0, fill=1)
        cv.rect(x, y - 0.24 * em - 0.072 * em, w, 0.022 * em, stroke=0, fill=1)
        cv.setFillColor(c(INK2))
        cv.setFont("Body", 7.5)
        if footer and footer != BR.NAME:
            cv.drawCentredString(A4[0] / 2, 10 * mm, footer.replace("Ultimate Productivity Bundle", BR.NAME))
        cv.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        cv.setStrokeColor(c(BORDER))
        cv.line(18 * mm, 15.5 * mm, A4[0] - 18 * mm, 15.5 * mm)
        cv.restoreState()

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=20 * mm, title=md_path.stem.replace("_", " "))
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        p = Path(a)
        render(p, p.with_suffix(".pdf"))
        print("wrote", p.with_suffix(".pdf"))
