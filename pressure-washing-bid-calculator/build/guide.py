"""Quick-start guide PDF for the Pressure Washing Bid Calculator (Brass Ledger style, US Letter).

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
from test_workbook import SAMPLE, quote, settings  # noqa: E402
import pw_config as CFG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "pressure-washing-bid-calculator" / "BrassLedger_Pressure_Washing_Quick_Start_Guide.pdf"
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



def money(x):
    return f"-${-x:,.2f}" if x < 0 else f"${x:,.2f}"


def build():
    s = settings()
    m = quote(SAMPLE, s)
    eq = CFG.EQUIPMENT[0]
    eq_year = eq[1] / eq[2] + eq[3]
    logo_path = Path(tempfile.mkdtemp()) / "logo.png"
    logo_rgba(1400).save(logo_path)
    from PIL import Image as PI
    lim = PI.open(logo_path)
    story = []
    lw = 70 * mm
    story += [Spacer(1, 14 * mm), Image(str(logo_path), width=lw, height=lw * lim.height / lim.width, hAlign="LEFT"), Spacer(1, 16 * mm),
              P(spaced("Quick-start guide"), "kicker"),
              Paragraph("Pressure Washing Bid Calculator", ParagraphStyle("t", fontName="Head", fontSize=30, leading=34, textColor=c(GREEN))),
              Spacer(1, 6), Rule(110, 34), Spacer(1, 12),
              Paragraph("Quote any pressure washing job in two minutes, without underpricing.",
                        ParagraphStyle("st", fontName="Body", fontSize=14, leading=19, textColor=c(INK))),
              Spacer(1, 4), P("For pressure washing and soft washing businesses. Excel and Google Sheets.", "small"),
              Spacer(1, 9 * mm), shot("quote_top", crop=(0, 0, 1, 1), max_h=300), Spacer(1, 6 * mm),
              P("Prices are estimates based on the numbers you enter. Adjust to your local market. Not financial, legal or tax advice.", "small"),
              PageBreak()]
    story += section("1 · What's included", "What's in your download")
    story += [table([["File", "Use it for"],
                     ["BrassLedger_Pressure_Washing_Bid_Calculator.xlsx", "Your own business. Example costs and services are filled in to replace."],
                     ["BrassLedger_Pressure_Washing_Bid_Calculator_SAMPLE.xlsx", "A fictional business with 8 quotes, 10 completed jobs and 8 plans."],
                     ["BrassLedger_Pressure_Washing_Quick_Start_Guide.pdf", "This guide."]], [0.55, 0.45]),
              Spacer(1, 8),
              table([["Tab", "What it does"],
                     ["START HERE", "Quick start, colour key, measuring tips, reminders, disclaimer."],
                     ["SETTINGS", "Your details, pay, equipment, overhead, fuel, services with production rates and chemical costs, multipliers."],
                     ["QUICK QUOTE", "Up to 10 services per job: time, cost, price per line, total, profit per hour, plan value."],
                     ["CUSTOMER QUOTE", "A one-page quote with your business name, ready to print or save as PDF."],
                     ["QUOTE LOG", "Every quote, its answer, win rate and flatwork price per sq ft."],
                     ["JOB LOG", "Estimated vs actual hours and profit, with notes on which production rates to change."],
                     ["MAINTENANCE PLANS", "Repeat clients, next due dates and yearly plan revenue."],
                     ["DASHBOARD", "Break-even rate, average job, win rate, revenue, plans due and three charts."]], [0.28, 0.72], bold_first=True),
              Spacer(1, 8), P("Opening in Excel", "h2"),
              P("Excel 2016 or later on Windows or Mac: double-click the .xlsx. If you see <i>Protected View</i>, click "
                "<b>Enable Editing</b>. There are no macros. Use the dark bar on the left of each tab to move around."),
              P("Opening in Google Sheets", "h2"),
              P("Quickest: open this link while signed in to Google and choose <b>File › Make a copy</b>:"),
              callout("<b>Google Sheets copy link:</b>  [GOOGLE SHEETS COPY LINK]"),
              Spacer(1, 5),
              P("Or upload the .xlsx to drive.google.com, right-click it, <b>Open with › Google Sheets</b>, then "
                "<b>File › Save as Google Sheets</b>. Formulas, dropdowns, colours and charts work. Sheet protection and "
                "the icon bar don't carry over (short text links appear instead), so take care not to type over shaded cells.", "small"),
              PageBreak()]
    story += section("2 · Setting up", "Your costs, once")
    story += [P("Open <b>SETTINGS</b> and replace the example values with your own: business details (they appear on the "
                "customer quote), your target pay, working hours per year, equipment, overhead, fuel, and the services table. "
                "Every other tab reads from here."),
              P("How your equipment becomes a cost per hour", "h2"),
              table([["Step", "Example", "Result"],
                     ["Purchase price ÷ expected life", f"{eq[0]}: {money(eq[1])} ÷ {eq[2]} years", money(eq[1] / eq[2]) + " a year"],
                     ["+ yearly maintenance", f"pump oil, seals, nozzles: {money(eq[3])}", money(eq_year) + " a year"],
                     ["÷ working hours per year", f"{money(eq_year)} ÷ {s['hours']:,} hours", money(eq_year / s["hours"]) + " per hour"]],
                    [0.36, 0.42, 0.22]),
              Spacer(1, 6),
              P(f"All the equipment together costs <b>{money(s['equip_year'])} a year</b> ({money(s['equip_hr'])} per working hour). "
                f"Overhead adds {money(s['over_year'])} a year ({money(s['over_hr'])} per hour). With your pay of {money(s['owner_pay'])}, "
                f"your <b>break-even hourly rate is {money(s['breakeven_hr'])}</b>."),
              P("The services table", "h2"),
              P("One row per service: its unit (sq ft, wall sq ft, roof sq ft, linear ft, per item), <b>units per hour</b> for one "
                "person on a normal job, <b>chemicals and materials per 1,000 units</b> (sealer, sand and stain included) and, "
                "optionally, the local going rate per unit. Add your own services in the empty rows."),
              shot("settings_svc", crop=(0, 0, 1, 1), max_h=215),
              Spacer(1, 4),
              table([["Multiplier", "Example values", "When to use it"],
                     ["Condition", "Light 0.8 · Normal 1.0 · Heavy 1.4 (chemicals 1.5)", "Heavy growth, grime or neglect."],
                     ["Height / access", "2 storeys 1.3 · 3 storeys 1.6 · steep pitch 1.4 · lift 1.5", "Storeys for houses, pitch for roofs."],
                     ["Stains", "Oil 10 min + $3 a spot · rust 0.5 min + $0.60 a sq ft", "Priced as time and materials, then margin."]],
                    [0.2, 0.46, 0.34], bold_first=True),
              PageBreak()]
    story += section("3 · Measuring", "Measuring surfaces")
    story += [bullets(["<b>Driveways, patios, roofs:</b> Google Maps on a computer (right-click › <b>Measure distance</b>, "
                       "click around the area back to the start) or Google Earth's polygon ruler gives square feet. Many "
                       "counties' free parcel maps have a measuring tool too.",
                       "<b>Roofs:</b> a map shows the flat footprint. A pitched roof has more surface: add about 10-20 % for a "
                       "moderate pitch and choose <b>Steep roof pitch</b> for steep ones.",
                       "<b>House walls:</b> perimeter × wall height (about 9-10 ft per storey), minus big garage doors. "
                       "Choose 2 or 3 storeys under Height / access.",
                       "<b>Fences:</b> length × height × sides (1 or 2). <b>Gutters:</b> the run in linear feet.",
                       "The <b>area helper</b> on QUICK QUOTE multiplies length × height × sides for you."]),
              Spacer(1, 6),
              callout("Check your first few jobs on site with a measuring wheel, and time them. The JOB LOG then tells you "
                      "which production rates to adjust."),
              PageBreak()]
    story += section("4 · Quoting", "Quoting your first job")
    rows = [["Service", "Quantity", "Minutes", "Chemicals", "Line price"]]
    for d in m["lines"]:
        if d["ok"]:
            rows.append([d["svc"], f"{d['qty']:,} {d['unit']}", f"{d['min']:.0f}", money(d["chem"]), money(d["price"])])
    story += [P(f"The sample file quotes <b>{CFG.QUOTE['client']}</b>: a 2-storey house wash, a heavily stained driveway "
                f"with 3 oil spots, the front walkway and the gutters, {CFG.QUOTE['drive']} minutes' drive."),
              table(rows, [0.36, 0.18, 0.14, 0.15, 0.17]), Spacer(1, 6),
              table([["How the price builds", ""],
                     ["Time on site", f"{m['work']:.0f} min of services + {m['extra']:.0f} min setup = {m['onsite']:.0f} min; "
                                      f"{m['job_hours']:.1f} job hours with driving"],
                     ["Cost of the job", f"labour {money(m['c_lab'])} + equipment and overhead {money(m['c_eq'] + m['c_ov'])} + fuel "
                                         f"{money(m['c_fuel'])} + chemicals {money(m['c_chem'])} + travel {money(m['c_trav'])} = <b>{money(m['cost'])}</b>"],
                     ["Line prices", f"each line's cost ÷ (1 − {s['margin']:.0%} margin), rounded up to the next $5: subtotal {money(m['subtotal'])}"],
                     ["Bundle discount", f"{s['bundle_disc']:.0%} off for 2 or more services: {money(m['bundle'])}"],
                     ["Total", f"<b>{money(m['total'])}</b>: profit {money(m['profit'])}, {money(m['profit_hr'])} per job hour"]],
                    [0.24, 0.76], bold_first=True),
              Spacer(1, 6),
              P("Job-wide costs (setup, travel, equipment, overhead) are spread over the lines by time, so a quick walkway "
                "carries less than a long house wash. Water hauling, the travel surcharge beyond the free miles, and a top-up "
                "to your minimum job charge are added as their own lines.", "small"),
              PageBreak()]
    story += section("5 · Sending", "The customer quote")
    story += [P("<b>CUSTOMER QUOTE</b> fills itself from QUICK QUOTE and SETTINGS: your business name and contact details, the "
                "client, each service with its details and price, the bundle discount, any water or travel charges, the total, "
                "the maintenance plan offer, your terms and a signature line. It carries no Brass Ledger branding."),
              shot("customer", width=CW * 0.52), Spacer(1, 6),
              bullets(["<b>Print or PDF:</b> File › Print, or Save as PDF. It fits one letter page.",
                       "<b>Your logo:</b> Insert › Picture over the dashed box (Review › Unprotect Sheet if Excel blocks it; no password)."]),
              PageBreak()]
    story += section("6 · Plans", "Selling maintenance plans")
    story += [P(f"On QUICK QUOTE, put <b>1</b> or <b>2</b> under <i>Plan visits a year</i> for each service the client could "
                f"have on a schedule: for example the house wash each spring and the driveway each fall. The quote shows the "
                f"plan's annual value at your plan discount ({s['plan_disc']:.0%}); the sample plan is worth <b>{money(m['plan'])} a year</b>, "
                f"and the customer quote offers it in one line."),
              P("When a client says yes, add them to <b>MAINTENANCE PLANS</b>: services, frequency, price per visit and the "
                "last clean date. The next due date fills in, plans due within 30 days turn brass, overdue ones red."),
              shot("plans", crop=(0, 0, 1, 1), max_h=200), Spacer(1, 6),
              P("Using the job log to tune your rates", "h2"),
              P("After each job, log the quoted price, the estimated hours (from the quote) and your actual hours, chemicals "
                "and extra costs on <b>JOB LOG</b>. The table on the right compares estimate and actual by service and tells "
                "you what to change: more than 15 % slower or faster suggests a new units-per-hour figure for SETTINGS."),
              shot("jobs_summary", crop=(0, 0, 1, 1), max_h=190),
              PageBreak()]
    story += section("7 · Reminders", "Compliance reminders (not legal advice)")
    story += [bullets(CFG.COMPLIANCE), Spacer(1, 8)]
    story += section("8 · Questions", "FAQ")
    faq = [("My price looks higher than competitors'.",
            "Check your working hours and production rates first, then the going-rate column on QUICK QUOTE. Many "
            "low-priced competitors aren't counting chemicals, setup time, insurance or driving. Win on reliability, "
            "plans and add-ons rather than dropping below your cost."),
           ("How do I price oil stains?",
            "Pick Oil under Stain treatment and type the number of spots. Each spot adds the minutes and materials set on "
            "SETTINGS (10 minutes and $3 by default), and the line price includes them with your margin. Tell the client "
            "old oil stains lighten but may not disappear."),
           ("Why is a small job priced at my minimum?", "Setup, driving and packing up cost the same on a tiny job. The "
            "minimum job charge makes sure small jobs are worth the trip."),
           ("Can I quote commercial work?", "Yes: set Property type to Commercial and use the commercial flatwork, dumpster "
            "pad and drive-thru lines, a crew size and the water hauling option."),
           ("Does it work outside the US?", "Yes: change the currency symbol on SETTINGS and keep your units consistent. "
            "Rates and prices are US examples.")]
    for qn, ans in faq:
        story += [P(f"<b>{qn}</b>"), P(ans), Spacer(1, 2)]
    story += [Spacer(1, 6), callout("<b>Disclaimer.</b> Prices are estimates based on the numbers you enter. Adjust to your "
                                    "local market. Not financial, legal or tax advice. No specific earnings are promised.")]

    def on_page(cv, doc):
        cv.saveState()
        cv.setFillColor(c(PAPER))
        cv.rect(0, 0, PW, PH, stroke=0, fill=1)
        if doc.page > 1:
            x, y, em = SIDE, 11 * mm, 11
            cv.setFillColor(c(GREEN))
            cv.setFont("Head", em)
            cv.drawString(x, y, BR.NAME)
            w = pdfmetrics.stringWidth(BR.NAME, "Head", em)
            cv.setFillColor(c(BRASS))
            cv.rect(x, y - 0.24 * em, w, 0.075 * em, stroke=0, fill=1)
            cv.rect(x, y - 0.24 * em - 0.072 * em, w, 0.022 * em, stroke=0, fill=1)
            cv.setFillColor(c(INK2))
            cv.setFont("Body", 7.5)
            cv.drawCentredString(PW / 2, 10.5 * mm, "Pressure Washing Bid Calculator · Quick-start guide")
            cv.drawRightString(PW - SIDE, 10.5 * mm, f"Page {doc.page}")
            cv.setStrokeColor(c(BORDER))
            cv.line(SIDE, 16 * mm, PW - SIDE, 16 * mm)
        cv.restoreState()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER, leftMargin=SIDE, rightMargin=SIDE, topMargin=16 * mm, bottomMargin=21 * mm,
                            title="Pressure Washing Bid Calculator — Quick-start guide", author="Brass Ledger")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
