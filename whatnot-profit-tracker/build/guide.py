"""Quick-start guide PDF for the Whatnot Live Show Profit Tracker (Brass Ledger style).

US Letter pages with side margins wide enough that the content also prints on A4 without clipping.
Screenshots come from shoot.py; the worked example is computed from the sample data with the test model.
Usage: python guide.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

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

from listing_images import logo_rgba  # noqa: E402
from sample_data import SHOWS  # noqa: E402
from test_tracker import model_show  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "whatnot-profit-tracker" / "BrassLedger_Whatnot_Quick_Start_Guide.pdf"
PW, PH = LETTER
SIDE = 22 * mm                                    # content 172 mm wide: fits A4 (210 mm) too
CW = PW - 2 * SIDE
GREEN, BRASS, PAPER, INK, INK2, BORDER = BR.GREEN, BR.BRASS, BR.PAPER, BR.INK, BR.INK2, BR.BORDER
CALC, BRASS_TINT = "F1ECE2", "F6EBD3"


def c(h):
    return colors.HexColor("#" + h)


S = {
    "kicker": ParagraphStyle("k", fontName="Body-Bold", fontSize=8, leading=11, textColor=c(BRASS), spaceAfter=2),
    "h1": ParagraphStyle("h1", fontName="Head", fontSize=24, leading=28, textColor=c(GREEN), spaceAfter=4),
    "h2": ParagraphStyle("h2", fontName="Head", fontSize=14, leading=18, textColor=c(GREEN), spaceBefore=10, spaceAfter=4),
    "p": ParagraphStyle("p", fontName="Body", fontSize=10, leading=14.5, textColor=c(INK), alignment=TA_LEFT, spaceAfter=5),
    "small": ParagraphStyle("s", fontName="Body", fontSize=8.5, leading=12, textColor=c(INK2), spaceAfter=4),
    "cell": ParagraphStyle("c", fontName="Body", fontSize=9, leading=12, textColor=c(INK)),
    "cellb": ParagraphStyle("cb", fontName="Body-Bold", fontSize=9, leading=12, textColor=c(INK)),
    "cellh": ParagraphStyle("ch", fontName="Body-Bold", fontSize=9, leading=12, textColor=c(PAPER)),
    "callout": ParagraphStyle("co", fontName="Body", fontSize=10, leading=14.5, textColor=c(INK)),
}


def spaced(t):
    return "   ".join(" ".join(w) for w in t.upper().split())


class Rule(Flowable):
    """Short brass double rule: thick, gap, thin."""

    def __init__(self, width=70, em=24):
        super().__init__()
        self.w, self.em = width, em

    def wrap(self, aw, ah):
        return self.w, self.em * 0.2

    def draw(self):
        cv = self.canv
        cv.setFillColor(c(BRASS))
        e = self.em
        cv.rect(0, e * 0.12, self.w, e * 0.075, stroke=0, fill=1)
        cv.rect(0, e * 0.12 - 0.05 * e - 0.022 * e, self.w, e * 0.022, stroke=0, fill=1)


def P(t, st="p"):
    return Paragraph(t, S[st])


def section(kicker, title):
    return [P(spaced(kicker), "kicker"), P(title, "h1"), Rule(), Spacer(1, 12)]


def bullets(items, numbered=False):
    return ListFlowable([ListItem(P(t), leftIndent=14) for t in items], bulletType="1" if numbered else "bullet",
                        start="1" if numbered else None, bulletFontName="Body-Bold", bulletFontSize=9,
                        bulletColor=c(BRASS), leftIndent=14)


def table(rows, widths, head=True, bold_first=False):
    data = []
    for i, r in enumerate(rows):
        st = "cellh" if head and i == 0 else "cell"
        data.append([Paragraph(str(x), S["cellb" if (bold_first and j == 0 and st == "cell") else st]) for j, x in enumerate(r)])
    t = Table(data, colWidths=[w * CW for w in widths], repeatRows=1 if head else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.5, c(BORDER)), ("BACKGROUND", (0, 0), (-1, -1), colors.white),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
             ("LEFTPADDING", (0, 0), (-1, -1), 6)]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), c(GREEN)))
    t.setStyle(TableStyle(style))
    return t


def callout(text, tint=BRASS_TINT):
    t = Table([[Paragraph(text, S["callout"])]], colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), c(tint)), ("LINEBEFORE", (0, 0), (0, -1), 3, c(BRASS)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


def shot(name, width=CW, crop=None):
    from PIL import Image as PI
    p = SCREENS / f"{name}.png"
    im = PI.open(p)
    if crop:
        w, h = im.size
        im = im.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
        p = Path(tempfile.mkdtemp()) / f"{name}.png"
        im.save(p)
    w, h = im.size
    img = Image(str(p), width=width, height=width * h / w)
    t = Table([[img]], colWidths=[width + 8])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, c(BORDER)), ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return t


def money(x):
    """Rounded half up, like Excel's display of the same value."""
    from decimal import ROUND_HALF_UP, Decimal
    d = Decimal(str(round(abs(x), 9))).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return ("-" if x < 0 else "") + f"${d:,.2f}"


def build():
    logo_path = Path(tempfile.mkdtemp()) / "logo.png"
    logo_rgba(1400).save(logo_path)
    story = []
    # ---------------------------------------------------------------- cover
    from PIL import Image as PI
    lw = 70 * mm
    lim = PI.open(logo_path)
    story += [Spacer(1, 18 * mm), Image(str(logo_path), width=lw, height=lw * lim.height / lim.width, hAlign="LEFT"), Spacer(1, 22 * mm),
              P(spaced("Quick-start guide"), "kicker"),
              Paragraph("Whatnot Live Show Profit Tracker", ParagraphStyle("t", fontName="Head", fontSize=34, leading=38, textColor=c(GREEN))),
              Spacer(1, 6), Rule(110, 34), Spacer(1, 14),
              Paragraph("See the real profit from every show in two minutes.", ParagraphStyle("st", fontName="Body", fontSize=14, leading=19, textColor=c(INK))),
              Spacer(1, 14 * mm), shot("dash_top"), Spacer(1, 10 * mm),
              P("For Microsoft Excel 2016 or later and Google Sheets. Not affiliated with or endorsed by Whatnot.", "small"),
              PageBreak()]
    # ---------------------------------------------------------------- what's included
    story += section("1 · What's included", "What's in your download")
    story += [table([["File", "Use it for"],
                     ["BrassLedger_Whatnot_Profit_Tracker.xlsx", "Your own shows. Start here."],
                     ["BrassLedger_Whatnot_Profit_Tracker_SAMPLE.xlsx", "12 example shows from Aug–Oct 2026 so you can see how every tab works."],
                     ["BrassLedger_Whatnot_Quick_Start_Guide.pdf", "This guide."]], [0.48, 0.52]),
              Spacer(1, 10), P("The workbook has six tabs:"),
              table([["Tab", "What it does"],
                     ["START HERE", "Quick start, colour key and the two ways to log."],
                     ["SETTINGS", "Fee rates, giveaway cost, monthly goal, and the lists behind the dropdowns. All assumptions live here."],
                     ["SHOW LOG", "One row per show, 300 rows ready. You type the white cells; the shaded columns work out fees and profit."],
                     ["ITEM SALES", "Optional. One row per item, with a summary that totals sales and cost for each show."],
                     ["DASHBOARD", "Pick a month: profit, fees, giveaways and goal progress, plus profit by time slot, weekday, category and month."],
                     ["YEAR SUMMARY", "Month-by-month totals and a year total."]], [0.22, 0.78], bold_first=True),
              Spacer(1, 6),
              P("<b>Getting around.</b> Every tab has an icon bar on the left: click an icon to jump to that tab (in Google "
                "Sheets the bar shows short text links instead). The link at the top right of each tab goes back to the dashboard."),
              Spacer(1, 4), P("Cell colours", "h2"),
              table([["Cell", "Meaning"], ["White with a border", "Type here, or pick from the dropdown."],
                     ["Shaded", "A formula. Locked so it can't be overwritten by accident."],
                     ["Green block, brass figure", "A headline result."],
                     ["Red profit", "The show lost money."], ["Green profit", "One of your top 25 % of shows."]], [0.3, 0.7], bold_first=True),
              PageBreak()]
    # ---------------------------------------------------------------- opening
    story += section("2 · Opening the file", "Open it in Excel or Google Sheets")
    story += [P("Microsoft Excel (Windows or Mac)", "h2"),
              bullets(["Download the files from your Etsy purchase page and unzip them if needed.",
                       "Double-click <b>BrassLedger_Whatnot_Profit_Tracker.xlsx</b>.",
                       "If Excel shows <i>Protected View</i>, click <b>Enable Editing</b>. The file has no macros.",
                       "Save a copy somewhere you'll find it, for example Documents › Whatnot."], True),
              P("Google Sheets", "h2"),
              P("<b>Option A, quickest:</b> open this link while signed in to Google, then choose <b>File › Make a copy</b>. "
                "The copy is yours and saves in your Google Drive."),
              callout("<b>Google Sheets copy link:</b>  [GOOGLE SHEETS COPY LINK]"),
              Spacer(1, 8),
              P("<b>Option B, from the file:</b>"),
              bullets(["Go to drive.google.com and choose <b>New › File upload</b>. Pick the .xlsx file.",
                       "Right-click the uploaded file and choose <b>Open with › Google Sheets</b>.",
                       "Choose <b>File › Save as Google Sheets</b>, and work in that copy.",
                       "Check <b>File › Settings › Locale</b> is your country so dates read correctly."], True),
              Spacer(1, 6),
              callout("In Google Sheets the formulas, dropdowns, colours and charts all work. Sheet protection does not carry over, "
                      "so take care not to type over the shaded cells. Charts may look slightly different."),
              PageBreak()]
    # ---------------------------------------------------------------- settings
    story += section("3 · Settings", "Set your fees once")
    story += [P("Open <b>SETTINGS</b>. Every rate the workbook uses is on this tab; nothing is hidden in the formulas."),
              shot("settings", crop=(0, 0, 1, 1)), Spacer(1, 8),
              table([["Setting", "Default", "What it does"],
                     ["Currency symbol", "$", "Shown in headings and dashboard text."],
                     ["Whatnot commission", "8%", "Charged on each sale."],
                     ["Payment processing", "2.9%", "Charged on the sale price plus any shipping you charged."],
                     ["Processing fixed fee", "$0.30", "Added once per order."],
                     ["Commission is charged on", "Sale price only", "Switch to <i>Sale price + shipping</i> if your commission includes shipping."],
                     ["Default giveaway cost", "$3.00", "Item cost plus any shipping you cover, per giveaway."],
                     ["Monthly profit goal", "$1,500", "Drives the goal tile on the dashboard."]], [0.3, 0.18, 0.52], bold_first=True),
              Spacer(1, 8),
              callout("<b>Defaults are based on published rates as of 2025.</b> Check Whatnot's current seller fees and update these "
                      "cells. Change a rate and every show, tile and total updates at once."),
              Spacer(1, 6),
              P("Shipping you charge buyers pays for the label, so it is not counted as profit. Enter it only so fees charged on it "
                "are included. If you pay for labels yourself, put that under <b>Other costs</b>.", "small"),
              PageBreak()]
    # ---------------------------------------------------------------- first show (worked example)
    s = next(x for x in SHOWS if x["date"].month == 10 and x["date"].day == 6)
    cfg = dict(comm=0.08, proc=0.029, fixed=0.30, on_ship=False, give=3.00)
    m = model_show(s, cfg)
    story += section("4 · Logging a show", "Log your first show")
    story += [P("After each show, fill one row on <b>SHOW LOG</b>. Here is <b>Tuesday Night Breaks</b> on October 6, 2026 "
                "from the sample file."),
              table([["You type", "Value"],
                     ["Date, title, category, time slot, format", "Oct 6, 2026 · Tuesday Night Breaks · Sports Cards · Evening · Auction"],
                     ["Start and end time", "7:00 PM to 9:30 PM"],
                     ["Gross sales · orders", f"{money(s['gross'])} · {s['orders']} orders"],
                     ["Shipping charged (optional)", money(s["ship"])],
                     ["Cost of items sold", money(s["cogs"])],
                     ["Giveaways", f"{s['gives']} (cost left blank, so {s['gives']} × $3.00 from SETTINGS)"],
                     ["Supplies · other costs", f"{money(s['supplies'])} · {money(s['other'])}"]], [0.42, 0.58], bold_first=True),
              Spacer(1, 10), P("What the workbook works out", "h2"),
              table([["Calculation", "How", "Result"],
                     ["Hours live", "End time − start time", f"{m['hours']:.1f}"],
                     ["Commission", f"8% × {money(s['gross'])}", money(m["comm"])],
                     ["Processing fees", f"2.9% × ({money(s['gross'])} + {money(s['ship'])}) + $0.30 × {s['orders']}", money(m["proc"])],
                     ["Total fees", "Commission + processing", money(m["fees"])],
                     ["Giveaway cost", f"{s['gives']} × $3.00", money(m["gcost"])],
                     ["<b>Net profit</b>", "Gross sales − fees − items − giveaways − supplies − other", f"<b>{money(m['profit'])}</b>"],
                     ["Profit margin", "Net profit ÷ gross sales", f"{m['margin'] * 100:.1f}%"],
                     ["Profit per hour", "Net profit ÷ hours live", money(m["perhour"])]], [0.24, 0.56, 0.2], bold_first=True),
              P("Results are rounded to the cent. A show that ends after midnight is handled: 10:30 PM to 12:30 AM counts as 2 hours.", "small"),
              PageBreak(),
              P("The same show in the sample file: the NET PROFIT column is the brass one. Red marks a loss; green marks your top 25 % of shows."),
              shot("log_profit"), Spacer(1, 10),
              P("Logging tips", "h2"),
              bullets(["Log the show the same day, while the numbers are in front of you.",
                       "Gross sales is the total of your sold prices, before fees. Take it from your Whatnot show summary.",
                       "Cost of items sold is what you paid for the items that sold in this show.",
                       "Leave a cell empty rather than typing 0 if you don't know it yet. Every formula handles empty cells.",
                       "Peak viewers and notes are optional, but help you spot why a show did well."]),
              PageBreak()]
    # ---------------------------------------------------------------- dashboard
    story += section("5 · The dashboard", "Read the dashboard")
    story += [P("Pick a <b>month</b> from the dropdown and type the <b>year</b>. The tiles show that month; the tables and "
                "charts show the whole year."),
              shot("dash_top", crop=(0, 0, 1, 0.56)), Spacer(1, 8),
              table([["Tile", "Meaning"],
                     ["Net profit this month", "Profit from every show in the chosen month."],
                     ["Profit year to date", "January to the chosen month."],
                     ["Average profit per show / per hour", "How much a typical show, and a typical hour live, earns."],
                     ["Fees paid · giveaway cost year to date", "What Whatnot fees and giveaways have cost you this year."],
                     ["Monthly goal progress", "Profit this month as a share of your goal on SETTINGS."]], [0.42, 0.58], bold_first=True),
              Spacer(1, 8),
              P("Below the tiles, <b>where this month's sales went</b> splits gross sales into Whatnot fees, item costs, giveaways, "
                "supplies and the net profit you kept, with a doughnut chart."),
              P("Further down: profit by <b>time slot</b>, <b>weekday</b> and <b>category</b>, a 12-month <b>trend</b>, and your "
                "<b>top 5 and bottom 5</b> shows. Each table ends with a plain-English line such as <i>\"Your most profitable time "
                "slot is Evening.\"</i>"),
              shot("dash_cat"),
              PageBreak()]
    # ---------------------------------------------------------------- modes
    story += section("6 · Quick or detailed", "Two ways to log")
    story += [P("<b>Quick mode.</b> Type each show's totals straight into SHOW LOG. Most sellers only ever need this."),
              P("<b>Detailed mode.</b> On <b>ITEM SALES</b>, add one row per item: show date, show title, item, category, what it cost "
                "you, what it sold for, the buyer and whether it has shipped. The summary on the right adds up each show."),
              shot("items"), Spacer(1, 8),
              bullets(["Type the show date and title exactly as on SHOW LOG.",
                       "Copy <b>Gross sales</b> and <b>Cost of items</b> from the summary into that show's row on SHOW LOG.",
                       "<b>In SHOW LOG?</b> says <i>Not yet</i> until the show has a row there.",
                       "SHOW LOG never reads ITEM SALES, so leaving ITEM SALES empty causes no errors."]),
              Spacer(1, 6), P("Year summary", "h2"),
              P("<b>YEAR SUMMARY</b> lists gross sales, fees, cost of items, giveaways, supplies, other costs and net profit for each "
                "month, with a year total. It follows the dashboard year until you type a different year. It is useful for your tax "
                "preparer; it is not tax advice."),
              PageBreak()]
    # ---------------------------------------------------------------- FAQ
    story += section("7 · Questions", "FAQ")
    faq = [("My fees look different from Whatnot's.", "Check the rates on SETTINGS against your current Whatnot seller fees, and whether "
            "your commission includes shipping. Fee rules can differ by category and change over time; the workbook uses whatever "
            "you set. Payouts can also include adjustments, refunds or promotions the workbook doesn't know about: add those under Other costs."),
           ("Can I use it on my phone?", "The file opens in the Excel and Google Sheets phone apps, but it is best on a computer. "
            "The show log is wide and the dashboard has charts."),
           ("Where do I put shipping?", "Shipping charged to buyers goes in its own column so fees on it are counted. It is not profit, "
            "because it pays for the label. Label costs you pay yourself go under Other costs."),
           ("A giveaway cost more than usual.", "Type that show's total giveaway cost in <i>Giveaway cost (blank = auto)</i>. "
            "Leave it blank to use the number of giveaways × the default from SETTINGS."),
           ("Can I rename categories?", "Yes, on SETTINGS. Keep each name unique. Rows already logged keep the old name."),
           ("What if I do more than 300 shows?", "300 rows is about six shows a week for a year. Start a fresh copy of the blank file for each year."),
           ("Why can't I type in a shaded cell?", "Shaded cells hold formulas and the tabs are protected against accidental edits. "
            "To change the layout, use Review › Unprotect Sheet in Excel. There is no password."),
           ("How do I clear the sample data?", "Use the blank file for your own shows. The sample file is for exploring."),
           ("Does it work outside the US?", "Yes. Change the currency symbol on SETTINGS and check your local Whatnot fees.")]
    for q_, a_ in faq:
        story.append(KeepTogether([P(f"<b>{q_}</b>"), P(a_), Spacer(1, 2)]))
    story += [Spacer(1, 10), P("Need help?", "h2"), P("Send me a message on Etsy and I will help you get set up."),
              Spacer(1, 10),
              callout("<b>Disclaimer.</b> Not affiliated with or endorsed by Whatnot. Whatnot is a trademark of its owner. Fee rates change; "
                      "check your current rates in Settings. This workbook is a record-keeping tool, not tax, legal or financial advice.")]

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
            cv.drawCentredString(PW / 2, 10.5 * mm, "Whatnot Live Show Profit Tracker · Quick-start guide")
            cv.drawRightString(PW - SIDE, 10.5 * mm, f"Page {doc.page}")
            cv.setStrokeColor(c(BORDER))
            cv.line(SIDE, 16 * mm, PW - SIDE, 16 * mm)
        cv.restoreState()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER, leftMargin=SIDE, rightMargin=SIDE, topMargin=18 * mm, bottomMargin=22 * mm,
                            title="Whatnot Live Show Profit Tracker — Quick-start guide", author="Brass Ledger")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
