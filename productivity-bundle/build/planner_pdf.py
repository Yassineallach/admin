"""PRODUCT 2 — hyperlinked PDF edition of the Ultimate Planner.

Landscape US Letter (11 x 8.5 in). Every page has a left navigation rail with clickable tabs (Index, Year, 12 months,
Weeks, 10 template categories, Notes); the current tab is highlighted. Index and contents pages link to every page;
every page links back to the index. Works for print, PDF annotation apps (GoodNotes, Notability, Xodo, Drawboard)
and as a OneNote printout.
"""
from __future__ import annotations

import calendar as cal
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import planner_content as PC  # noqa: E402

LIB = "/usr/share/fonts/truetype/liberation/"
pdfmetrics.registerFont(TTFont("Sans", LIB + "LiberationSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", LIB + "LiberationSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Sym", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans", boldItalic="Sans-Bold")

PW, PH = landscape(letter)
RAIL = 74
MX0, MX1, MY0, MY1 = RAIL + 26, PW - 26, 24, PH - 22
NAVY, TXT, SUB = colors.HexColor("#0B4F4C"), colors.HexColor("#1F3533"), colors.HexColor("#5F7472")
LINE, HEAD, LABEL, CANVAS = colors.HexColor("#D5E5E2"), colors.HexColor("#E2F2EF"), colors.HexColor("#E7EFEE"), colors.HexColor("#F6FAF9")
CW = MX1 - MX0

ST = {
    "title": ParagraphStyle("t", fontName="Sans-Bold", fontSize=19, leading=23, textColor=NAVY),
    "sub": ParagraphStyle("s", fontName="Sans", fontSize=9, leading=12, textColor=SUB),
    "h": ParagraphStyle("h", fontName="Sans-Bold", fontSize=10.5, leading=13, spaceBefore=7, spaceAfter=3),
    "cell": ParagraphStyle("c", fontName="Sans", fontSize=8, leading=10, textColor=TXT),
    "cellb": ParagraphStyle("cb", fontName="Sans-Bold", fontSize=8, leading=10, textColor=TXT),
    "note": ParagraphStyle("n", fontName="Sans", fontSize=8.5, leading=11, textColor=TXT),
    "link": ParagraphStyle("l", fontName="Sans", fontSize=9, leading=13, textColor=colors.HexColor("#14958B")),
}


def hexc(h):
    return colors.HexColor("#" + h)


MARKS: dict = {}   # page key -> page number (filled while building; used by the validator)


class Mark(Flowable):
    """Zero-size flowable: bookmarks the page (link target) and records the current tab for the rail."""
    def __init__(self, key, tab):
        super().__init__()
        self.key, self.tab = key, tab
        self.width = self.height = 0

    def draw(self):
        MARKS[self.key] = self.canv.getPageNumber()
        self.canv.bookmarkPage(self.key, fit="XYZ", left=0, top=PH)
        self.canv._planner_tab = self.tab


def P(text, style="cell"):
    return Paragraph(text, ST[style])


def grid(data, widths, header=True, row_h=None, extra=None, label_col=False):
    t = Table(data, colWidths=widths, rowHeights=row_h)
    cmds = [("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 0), (-1, -1), "Sans"), ("FONTSIZE", (0, 0), (-1, -1), 8), ("TEXTCOLOR", (0, 0), (-1, -1), TXT),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), HEAD), ("FONTNAME", (0, 0), (-1, 0), "Sans-Bold")]
    if label_col:
        cmds += [("BACKGROUND", (0, 0), (0, -1), LABEL), ("FONTNAME", (0, 0), (0, -1), "Sans-Bold")]
    t.setStyle(TableStyle(cmds + (extra or [])))
    return t


K = 1.0   # vertical compaction factor (auto-fit sets it per page)


def SP(h):
    return Spacer(1, h * K)


def block(b, width, color):
    kind = b[0]
    col = hexc(color)
    if kind == "h":
        st = ParagraphStyle("hx", parent=ST["h"], textColor=col)
        return [Paragraph(b[1], st)]
    if kind == "note":
        t = Table([[Paragraph(b[1], ST["note"])]], colWidths=[width])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF0E3")), ("BOX", (0, 0), (-1, -1), 0, colors.white),
                               ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
        return [t, SP(4)]
    if kind == "fields":
        labels, cols = b[1], b[2]
        lw = width / cols * 0.38
        aw = width / cols - lw
        data, ws = [], []
        for i in range(0, len(labels), cols):
            chunk = labels[i:i + cols] + [""] * (cols - len(labels[i:i + cols]))
            row = []
            for l in chunk:
                row += [P(l, "cellb"), ""]
            data.append(row)
        ws = [lw, aw] * cols
        extra = [("BACKGROUND", (c, 0), (c, -1), LABEL) for c in range(0, 2 * cols, 2)]
        return [grid(data, ws, header=False, row_h=17 * K, extra=extra), SP(4)]
    if kind == "check":
        items = b[1] if isinstance(b[1], list) else [""] * b[1]
        data = [[Paragraph('<font name="Sym" color="#14958B" size="10">☐</font>', ST["cell"]), P(t)] for t in items]
        t = Table(data, colWidths=[16, width - 16], rowHeights=15 * K)
        t.setStyle(TableStyle([("LINEBELOW", (1, 0), (1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        return [t, SP(4)]
    if kind == "table":
        headers, rows = b[1], b[2]
        n = len(headers)
        data = [[P(h, "cellb") for h in headers]]
        rr = rows if isinstance(rows, list) else [[""] * n for _ in range(rows)]
        data += [[P(v, "cellb" if j == 0 and v else "cell") for j, v in enumerate(r)] for r in rr]
        return [grid(data, [width / n] * n, row_h=[16 * K] + [16 * K] * len(rr)), SP(4)]
    if kind == "lines":
        t = Table([[""] for _ in range(b[1])], colWidths=[width], rowHeights=17 * K)
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE)]))
        return [t, SP(4)]
    if kind == "scale":
        label, n = b[1], b[2]
        lw = width * 0.4
        data = [[P(label, "cellb")] + [str(i) for i in range(1, n + 1)]]
        return [grid(data, [lw] + [(width - lw) / n] * n, header=False, row_h=17 * K,
                     extra=[("BACKGROUND", (0, 0), (0, 0), LABEL), ("ALIGN", (1, 0), (-1, -1), "CENTER"), ("TEXTCOLOR", (1, 0), (-1, -1), SUB)]),
                SP(4)]
    if kind == "habit":
        habits, days = b[1], b[2]
        names = habits if isinstance(habits, list) else [""] * habits
        hw = 120 if days <= 7 else 90
        dw = (width - hw) / days
        head = ["Habit"] + ([d[:3] for d in PC.DAYS] if days == 7 else [str(i) for i in range(1, days + 1)])
        box = '<font name="Sym" color="#9AAAA9" size="8">☐</font>'
        cst = ParagraphStyle("hc", parent=ST["cell"], alignment=TA_CENTER, fontSize=7 if days > 7 else 8)
        data = [[Paragraph(h, cst) if i else P(h, "cellb") for i, h in enumerate(head)]]
        data += [[P(nm)] + [Paragraph(box, cst) for _ in range(days)] for nm in names]
        return [grid(data, [hw] + [dw] * days, row_h=16 * K), SP(4)]
    if kind == "calendar":
        y, m = b[1], b[2]
        weeks = cal.Calendar(0).monthdatescalendar(y, m)
        rh = min(56, 300 / len(weeks)) * K
        data = [[d[:3] for d in PC.DAYS]]
        extra = [("BACKGROUND", (0, 0), (-1, 0), col), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Sans-Bold"),
                 ("ALIGN", (0, 0), (-1, 0), "CENTER"), ("VALIGN", (0, 1), (-1, -1), "TOP")]
        for wi, wk in enumerate(weeks):
            row = []
            for di, d in enumerate(wk):
                row.append(str(d.day))
                if d.month != m:
                    extra += [("BACKGROUND", (di, wi + 1), (di, wi + 1), CANVAS), ("TEXTCOLOR", (di, wi + 1), (di, wi + 1), colors.HexColor("#9AAAA9"))]
            data.append(row)
        extra.append(("FONTNAME", (0, 1), (-1, -1), "Sans-Bold"))
        return [grid(data, [width / 7] * 7, header=False, row_h=[16 * K] + [rh] * len(weeks), extra=extra), SP(6)]
    if kind == "yearcal":
        y = b[1]
        mw = width / 4 - 8
        cells = []
        for m in range(1, 13):
            d = [[PC.MONTHS[m - 1]] + [""] * 6, [x[:2] for x in PC.DAYS]]
            for wk in cal.Calendar(0).monthdayscalendar(y, m):
                d.append([str(x) if x else "" for x in wk])
            while len(d) < 8:
                d.append([""] * 7)
            t = Table(d, colWidths=[mw / 7] * 7, rowHeights=13 * K)
            t.setStyle(TableStyle([("SPAN", (0, 0), (-1, 0)), ("BACKGROUND", (0, 0), (-1, 0), col), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("FONTNAME", (0, 0), (-1, 0), "Sans-Bold"), ("FONTNAME", (0, 1), (-1, -1), "Sans"), ("FONTSIZE", (0, 0), (-1, -1), 7),
                                   ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TEXTCOLOR", (0, 1), (-1, 1), SUB), ("FONTNAME", (0, 1), (-1, 1), "Sans-Bold"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
            cells.append(t)
        rows = [cells[i:i + 4] for i in range(0, 12, 4)]
        t = Table(rows, colWidths=[width / 4] * 4)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        return [t]
    if kind == "cols":
        half = width / 2 - 8
        left = [f for x in b[1] for f in block(x, half, color)]
        right = [f for x in b[2] for f in block(x, half, color)]
        t = Table([[left, right]], colWidths=[width / 2, width / 2])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, -1), 8)]))
        return [t]
    raise ValueError(kind)


# ---------------------------------------------------------------- page decorations
def make_rail(tabs):
    """tabs: [(key, label, color, target_key)]"""
    def draw(canv, doc):
        cur = getattr(canv, "_planner_tab", None)
        canv.saveState()
        canv.setFillColor(NAVY)
        canv.rect(0, 0, RAIL, PH, stroke=0, fill=1)
        h = (PH - 20) / len(tabs)
        for i, (key, label, color, target) in enumerate(tabs):
            y = PH - 10 - (i + 1) * h
            if key == cur:
                canv.setFillColor(colors.white)
                canv.roundRect(6, y + 1.5, RAIL - 10, h - 3, 4, stroke=0, fill=1)
                canv.setFillColor(hexc(color))
                canv.rect(6, y + 1.5, 3, h - 3, stroke=0, fill=1)
                canv.setFillColor(NAVY)
                canv.setFont("Sans-Bold", 7.5)
            else:
                canv.setFillColor(hexc(color))
                canv.circle(13, y + h / 2, 2.4, stroke=0, fill=1)
                canv.setFillColor(colors.white)
                canv.setFont("Sans", 7.5)
            canv.drawString(20, y + h / 2 - 2.6, label)
            canv.linkRect("", target, (0, y, RAIL, y + h), relative=0, thickness=0)
        # index link top-right of the content card
        canv.setFillColor(colors.HexColor("#14958B"))
        canv.setFont("Sans", 8)
        canv.drawRightString(MX1, PH - 26, "⌂ Index")
        canv.linkRect("", "index", (MX1 - 40, PH - 30, MX1, PH - 18), relative=0, thickness=0)
        canv.setFillColor(SUB)
        canv.setFont("Sans", 7)
        canv.drawRightString(MX1, 16, f"{doc.page}")
        canv.restoreState()
    return draw


def background(canv, doc):
    """Drawn BEFORE the page content: light canvas + white content card."""
    canv.saveState()
    canv.setFillColor(CANVAS)
    canv.rect(RAIL, 0, PW - RAIL, PH, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.roundRect(RAIL + 12, 10, PW - RAIL - 22, PH - 20, 10, stroke=0, fill=1)
    canv.restoreState()


def header(sec_name, color, title, subtitle=""):
    lab = Table([[sec_name.upper()]], hAlign="LEFT")
    lab.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), hexc(color)), ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                             ("FONTNAME", (0, 0), (-1, -1), "Sans-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 7),
                             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 7),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    out = [lab, Spacer(1, 4), Paragraph(title, ST["title"])]
    if subtitle:
        out.append(Paragraph(subtitle, ST["sub"]))
    out.append(Spacer(1, 6))
    return out


AVAIL = MY1 - MY0 - 8 - 4
FIT_LOG: dict = {}


def fit_page(p, s):
    """Build the page; if it is taller than the frame, compact row heights/spacers until it fits (>= 70 %)."""
    global K
    flow = []
    for k in (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7):
        K = k
        flow = header(s.name, s.color, p.title, p.subtitle)
        for b in p.blocks:
            flow += block(b, CW, s.color)
        h = sum(f.wrap(CW, AVAIL)[1] + f.getSpaceBefore() + f.getSpaceAfter() for f in flow)
        if h <= AVAIL:
            break
    FIT_LOG[p.key] = (K, h)
    K = 1.0
    return flow


def a(key, text):
    return f'<a href="#{key}" color="#14958B">{text}</a>'


def build_pdf(out: Path, year=PC.YEAR):
    secs = PC.build(year)
    tabs = [("index", "Index", "A9D8D1", "index"), ("start", "Year", "6FCBBE", "year_goals")]
    for s in secs:
        if s.group == "Months":
            tabs.append((s.key, s.short, s.color, s.pages[0].key))
    tabs.append(("weekly", "Weeks", "2F6FAA", "contents_weekly"))
    for s in secs:
        if s.group == "Templates":
            tabs.append((s.key, s.short, s.color, f"contents_{s.key}"))
    tabs.append(("notes", "Notes", "9B7BE0", "contents_notes"))

    doc = BaseDocTemplate(str(out), pagesize=(PW, PH), leftMargin=MX0, rightMargin=PW - MX1, topMargin=PH - MY1, bottomMargin=MY0,
                          title=f"Ultimate Planner {year}", author="Ultimate Productivity Bundle")
    frame = Frame(MX0, MY0, CW, MY1 - MY0 - 8, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate("p", [frame], onPage=background, onPageEnd=make_rail(tabs))])
    story = []

    # cover + index
    story += [Mark("cover", "index"), Spacer(1, 120),
              Paragraph(f'<font size="14" color="#14958B">ULTIMATE</font>', ST["title"]), Spacer(1, 14),
              Paragraph(f'<font size="44">Planner {year}</font>', ParagraphStyle("big", parent=ST["title"], leading=50)), Spacer(1, 18),
              Paragraph("Yearly goals · 12 monthly calendars · 53 weekly trackers · 111 templates · 8 note layouts", ST["sub"]), Spacer(1, 30),
              Paragraph(a("index", "Open the General Index ›"), ParagraphStyle("go", parent=ST["link"], fontSize=13)),
              Spacer(1, 10), Paragraph("Tip: the tabs on the left are clickable on every page.", ST["sub"]), PageBreak()]
    story += [Mark("index", "index")] + header("General index", "0B4F4C", f"Ultimate Planner {year}",
                                              "Click any link to jump to that page. Every page has a ⌂ Index link (top right) and the tabs on the left.")
    rows = []
    months = [s for s in secs if s.group == "Months"]

    def r(label, html, color):
        lab = Paragraph(f'<font color="white"><b>{label}</b></font>', ST["cell"])
        return [lab, Paragraph(html, ST["link"])], color
    data = [r("Start", " · ".join(a(p.key, p.title) for p in secs[0].pages), "0B4F4C"),
            r("Monthly calendars", " · ".join(a(f"m{m}_cal", PC.MONTHS[m - 1][:3]) for m in range(1, 13)), "14958B"),
            r("Monthly goals", " · ".join(a(f"m{m}_goals", PC.MONTHS[m - 1][:3]) for m in range(1, 13)), "14958B"),
            r("Monthly reflections", " · ".join(a(f"m{m}_refl", PC.MONTHS[m - 1][:3]) for m in range(1, 13)), "14958B"),
            r("Weekly trackers", " ".join(a(f"w{w}", f"{w:02d}") for w in range(1, 54)), "2F6FAA")]
    for s in secs:
        if s.group == "Templates":
            data.append(r(f"{s.name} ({len(s.pages)})", a(f"contents_{s.key}", "Contents") + " · " + " · ".join(a(p.key, p.title) for p in s.pages[:3]) + " …", s.color))
    nt = next(s for s in secs if s.key == "notes")
    data.append(r("Notes", " · ".join(a(p.key, p.title) for p in nt.pages), nt.color))
    t = Table([d for d, _ in data], colWidths=[150, CW - 150])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
                          + [("BACKGROUND", (0, i), (0, i), hexc(c)) for i, (_, c) in enumerate(data)]))
    story += [t, PageBreak()]

    # sections
    for s in secs:
        tab = s.key if s.group in ("Months", "Templates", "Weekly", "Notes") else "start"
        if s.group in ("Templates", "Weekly", "Notes"):
            story += [Mark(f"contents_{s.key}", tab)] + header(s.name, s.color, f"{s.name} — contents", f"{len(s.pages)} pages. Click a title to open it.")
            items = [a(p.key, f"{i}. {p.title}") for i, p in enumerate(s.pages, 1)]
            ncol = 4 if len(items) > 30 else 3 if len(items) > 12 else 2
            per = -(-len(items) // ncol)
            colsd = [[Paragraph(x, ST["link"]) for x in items[c * per:(c + 1) * per]] for c in range(ncol)]
            t = Table([colsd], colWidths=[CW / ncol] * ncol)
            t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story += [t, PageBreak()]
        for p in s.pages:
            story += [Mark(p.key, tab)] + fit_page(p, s)
            story.append(PageBreak())
    doc.build(story)
    return doc


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "dist" / "02_Ultimate_OneNote_Planner" / "PDF_Planner"
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"Ultimate_Planner_{PC.YEAR}_Hyperlinked.pdf"
    build_pdf(f)
    print("wrote", f)
