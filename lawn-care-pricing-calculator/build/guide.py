"""Quick-start guide PDF for the Lawn Care Pricing Calculator (Brass Ledger style, US Letter).

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
import lawn_config as CFG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "lawn-care-pricing-calculator" / "BrassLedger_Lawn_Care_Quick_Start_Guide.pdf"
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
    return f"${x:,.2f}"


def build():
    s = settings()
    m = quote(SAMPLE, s)
    eq = CFG.EQUIPMENT[0]
    mower_year = eq[1] / eq[2] + eq[3]
    logo_path = Path(tempfile.mkdtemp()) / "logo.png"
    logo_rgba(1400).save(logo_path)
    from PIL import Image as PI
    lim = PI.open(logo_path)
    story = []
    # ------------------------------------------------------------ cover
    lw = 70 * mm
    story += [Spacer(1, 14 * mm), Image(str(logo_path), width=lw, height=lw * lim.height / lim.width, hAlign="LEFT"), Spacer(1, 16 * mm),
              P(spaced("Quick-start guide"), "kicker"),
              Paragraph("Lawn Care Pricing Calculator", ParagraphStyle("t", fontName="Head", fontSize=32, leading=36, textColor=c(GREEN))),
              Spacer(1, 6), Rule(110, 34), Spacer(1, 12),
              Paragraph("Price every lawn for profit in two minutes.", ParagraphStyle("st", fontName="Body", fontSize=14, leading=19, textColor=c(INK))),
              Spacer(1, 4), P("For lawn mowing and yard care businesses. Excel and Google Sheets.", "small"),
              Spacer(1, 9 * mm), shot("quote_top", crop=(0, 0, 1, 0.62)), Spacer(1, 7 * mm),
              P("Prices are estimates based on the numbers you enter. Adjust to your local market. Not financial, legal or tax advice.", "small"),
              PageBreak()]
    # ------------------------------------------------------------ included + opening
    story += section("1 · What's included", "What's in your download")
    story += [table([["File", "Use it for"],
                     ["BrassLedger_Lawn_Care_Pricing_Calculator.xlsx", "Your own business. Example costs are filled in for you to replace."],
                     ["BrassLedger_Lawn_Care_Pricing_Calculator_SAMPLE.xlsx", "A fictional business with quotes, 15 route clients and a season of figures."],
                     ["BrassLedger_Lawn_Care_Quick_Start_Guide.pdf", "This guide."]], [0.52, 0.48]),
              Spacer(1, 8),
              table([["Tab", "What it does"],
                     ["START HERE", "Three-step quick start, colour key, measuring tips, disclaimer."],
                     ["SETTINGS", "Your details, pay, equipment, overhead, fuel, mower speeds, multipliers and add-on prices."],
                     ["QUICK QUOTE", "The calculator: lawn in, price per visit, monthly and season prices out."],
                     ["CUSTOMER QUOTE", "A one-page quote with your business name, ready to print or save as PDF."],
                     ["QUOTE LOG", "Every quote you send, its answer, and your win rate."],
                     ["ROUTE PLANNER", "Recurring clients by weekday and revenue per hour for each day."],
                     ["SEASON TRACKER", "Month-by-month revenue against your goal."],
                     ["DASHBOARD", "Break-even rate, average price, win rate, best day and three charts."]], [0.28, 0.72], bold_first=True),
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
    # ------------------------------------------------------------ costs
    story += section("2 · Setting up", "Your costs, once")
    story += [P("Open <b>SETTINGS</b> and replace the example values with your own: business details (they appear on the "
                "customer quote), your target pay, working hours per year, equipment, overhead and fuel. Every other tab "
                "reads from here."),
              P("How a $12,000 mower becomes a cost per hour", "h2"),
              table([["Step", "Example", "Result"],
                     ["Purchase price ÷ expected life", f"{money(eq[1])} ÷ {eq[2]} years", money(eq[1] / eq[2]) + " a year"],
                     ["+ yearly maintenance", f"blades, oil, belts, tyres: {money(eq[3])}", money(mower_year) + " a year"],
                     ["÷ working hours per year", f"{money(mower_year)} ÷ {s['hours']:,} hours", money(mower_year / s["hours"]) + " per hour"]],
                    [0.36, 0.40, 0.24]),
              Spacer(1, 6),
              P(f"Do the same for every machine and the trailer, and the whole equipment list costs "
                f"<b>{money(s['equip_year'])} a year</b>, or <b>{money(s['equip_hr'])} per working hour</b>. Overhead (insurance, "
                f"licences, phone, marketing, accounting) adds {money(s['over_year'])} a year, <b>{money(s['over_hr'])} per hour</b>. "
                f"With your own pay of {money(s['owner_pay'])}, your <b>break-even hourly rate is {money(s['breakeven_hr'])}</b>: "
                f"charge less than that for your time and you are paying yourself less than you planned."),
              shot("settings2", crop=(0, 0, 1, 1), max_h=270), Spacer(1, 6),
              callout("<b>Working hours per year</b> spreads equipment and overhead over the hours you actually work, "
                      "driving included. A 30-week season at 40 hours is 1,200. If you work fewer hours, every hour has to "
                      "carry more cost, and your prices go up."),
              PageBreak()]
    # ------------------------------------------------------------ measuring + speeds
    story += section("3 · Measuring", "Measuring a lawn and timing yourself")
    story += [bullets(["<b>Google Maps on a computer:</b> right-click a corner of the lawn, choose <b>Measure distance</b>, "
                       "click around the edge back to the start. The area shows in square feet.",
                       "<b>Google Earth (web):</b> the ruler tool has a <b>Polygon</b> option that traces an area. Many "
                       "counties' free GIS parcel maps have a measuring tool too.",
                       "Measure only the grass: leave out the house, driveway, patio and beds. Measure front and back "
                       "separately and add them up. If you only know acres, type acres instead: 1 acre = 43,560 sq ft."]),
              P("Mowing speed, multipliers and detail work", "h2"),
              P("Mowing time is the lawn area divided by your mower's speed in square feet per hour (SETTINGS). The "
                "example speeds come from the usual rule, <b>mph × deck width in inches ÷ 99 = acres per hour</b>, "
                "reduced to about 50-60 % for turns, overlap and small yards. Time a few of your own lawns and adjust."),
              table([["Multiplier", "Example values", "When to use it"],
                     ["Obstacles", "Low 1.00 · Medium 1.15 · High 1.30", "Trees, beds, play sets. Also adds to trimming time."],
                     ["Slope", "Flat 1.00 · Moderate 1.15 · Steep 1.35", "Slower passes on hills."],
                     ["Grass condition", "Normal 1.00 · Overgrown 1.50", "First cut of the year or neglected lawns."],
                     ["Bag clippings", "1.20 plus disposal", "Emptying bags and dump fees."]], [0.22, 0.38, 0.40], bold_first=True),
              Spacer(1, 6),
              P("Trimming, edging and blowing use <b>minutes per 1,000 sq ft of lawn, with a minimum per visit</b>. Example: "
                "trimming at 1.5 minutes per 1,000 sq ft on a 9,500 sq ft lawn is 14.25 minutes; on a 3,000 sq ft lawn "
                "it would be 4.5, so the 8-minute minimum applies. One clear rule that scales with the lawn and never "
                "underprices a small yard."),
              callout("<b>Crew size</b> divides the time on site, with a small efficiency loss (10 % per extra person by "
                      "default). Your helper's wage plus payroll costs is added to the labour cost."),
              PageBreak()]
    # ------------------------------------------------------------ first quote
    story += section("4 · Quoting", "Quoting your first job")
    story += [P(f"The sample file quotes <b>{CFG.QUOTE['client']}</b>: {CFG.QUOTE['sqft']:,} sq ft, 52\" zero-turn, medium "
                f"obstacles, flat, trimming, edging and blowing, {CFG.QUOTE['drive']} minutes' drive, {CFG.QUOTE['miles']} miles, weekly."),
              table([["Line", "How it's worked out", "Amount"],
                     ["Time on site", f"mowing {m['mow']:.1f} min + detail work {m['detail']:.1f} min", f"{m['onsite']:.1f} min"],
                     ["Labour", f"{m['onsite']:.1f} min at your pay of {money(s['owner_pay'])} an hour", money(m["c_lab"])],
                     ["Equipment + overhead", f"{m['job_hours']:.2f} job hours (on site + driving) × {money(s['equip_hr'] + s['over_hr'])}",
                      money(m["c_eq"] + m["c_ov"])],
                     ["Mower fuel", f"{m['mow']:.1f} min × 1.2 gal/h × {money(s['fuel_price'])}", money(m["c_fuel"])],
                     ["Travel", f"{CFG.QUOTE['drive']} min of your time + {CFG.QUOTE['miles']} miles × {money(s['vehicle_mile'])}", money(m["c_trav"])],
                     ["<b>Cost per visit</b>", "", f"<b>{money(m['cost'])}</b>"],
                     ["Price", f"{money(m['cost'])} ÷ (1 − {s['margin']:.0%} margin) = {money(m['cost'] / (1 - s['margin']))}, rounded up to the next $5",
                      f"<b>{money(m['price'])}</b>"],
                     ["Profit", f"{money(m['profit'])} a visit, {money(m['profit_hr'])} per job hour", ""]],
                    [0.24, 0.58, 0.18]),
              Spacer(1, 6),
              P(f"Monthly: {money(m['price'])} × 52 ÷ 12 = <b>{money(m['monthly'])}</b>. Season contract: {s['season_weeks']} visits "
                f"= <b>{money(m['season'])}</b>, or {money(m['prepaid'])} paid in advance. The add-ons (spring cleanup, aeration "
                f"at {money(12)} per 1,000 sq ft, 3 cubic yards of mulch) total <b>{money(m['addons'])}</b>, billed once."),
              P("Warnings", "h2"),
              bullets(["<b>Red, below break-even:</b> your own price (if you typed one) is under the cost of the visit.",
                       f"<b>Red, low profit:</b> profit per job hour is under your target ({money(s['target_profit_hr'])} by default).",
                       "<b>Going rate:</b> type what you think others charge and the quote shows how far above or below it you are. "
                       "Don't drop below your cost to match it."]),
              PageBreak()]
    # ------------------------------------------------------------ customer quote + log
    story += section("5 · Sending", "The customer quote")
    story += [P("<b>CUSTOMER QUOTE</b> fills itself from QUICK QUOTE and your SETTINGS: your business name and contact "
                "details, the client, the service, frequency, price per visit, monthly and season prices, add-ons, your "
                "terms and a signature line. It carries no Brass Ledger branding."),
              shot("customer", width=CW * 0.56), Spacer(1, 6),
              bullets(["<b>Print or PDF:</b> File › Print, or choose Save as PDF / Microsoft Print to PDF. It fits one letter page.",
                       "<b>Your logo:</b> Insert › Picture and place it over the dashed box. If Excel blocks it, Review › "
                       "Unprotect Sheet (there is no password).",
                       "<b>Valid until</b> = quote date + the days you set on SETTINGS (30 by default)."]),
              PageBreak()]
    story += section("6 · Learning", "Using the quote log to adjust prices")
    story += [P("At the bottom of QUICK QUOTE is a green row with the quote's date, client, address, size, frequency and "
                "prices. Copy it, click the first empty Date cell on <b>QUOTE LOG</b>, and paste values only "
                "(Excel: Ctrl+Alt+V then V; Google Sheets: Ctrl+Shift+V). Set the status when the client answers."),
              shot("log", crop=(0, 0, 1, 0.75)), Spacer(1, 6),
              bullets(["<b>Win rate</b> = accepted ÷ (accepted + declined + no reply). Quotes still marked Sent don't count yet.",
                       "<b>Price per 1,000 sq ft, accepted vs declined:</b> if the quotes people decline are much higher per "
                       "1,000 sq ft than the ones they accept, look at those jobs first: steep lots and long drives cost more for a reason.",
                       "Winning nearly every quote can mean you are cheaper than you need to be. Many owners are comfortable "
                       "winning about half."]),
              P("Planning routes", "h2"),
              P("On <b>ROUTE PLANNER</b>, list each recurring client with its weekday, price, minutes on site and drive minutes "
                "from the stop before. The summary shows each day's revenue per hour and warns when driving takes more than "
                "25 % of the day. Bi-weekly clients count half, so the numbers are an average week."),
              shot("route_summary", crop=(0, 0, 1, 0.8), max_h=170),
              PageBreak()]
    # ------------------------------------------------------------ season, dashboard, FAQ
    story += section("7 · The season", "Season tracker and dashboard")
    story += [P("Each month, type your active clients, mowing revenue and add-on revenue on <b>SEASON TRACKER</b>. Goals "
                "fill in from SETTINGS for the months of your season; type over any of them. The <b>DASHBOARD</b> shows "
                "your break-even rate, average price per visit, win rate, active clients, revenue year to date and your "
                "best day per hour, with charts of revenue against goal, quotes by status and revenue per hour by weekday."),
              shot("dash_top", crop=(0, 0, 1, 1), max_h=300),
              PageBreak()]
    story += section("8 · Questions", "FAQ")
    faq = [("My price looks higher than competitors'.",
            "Check the cost lines first: is your working-hours figure realistic, and are speeds right for your mower? If "
            "they are, the gap is usually a competitor who isn't counting equipment wear, insurance or driving. Win on "
            "reliability and route density rather than price, raise prices gradually for existing clients, and use the "
            "going-rate check to see the difference in plain numbers."),
           ("How do I price leaves and cleanups?",
            "As add-ons. Flat prices work for routine spring and fall cleanups; per hour suits leaf removal and heavy jobs "
            "you can't see in advance. Estimate the hours, multiply by your hourly rate at target margin (SETTINGS) and set "
            "the price list to match. Change any unit (flat, per hour, per 1,000 sq ft, per cubic yard, per bag) on SETTINGS."),
           ("Can I offer fertilising and weed control?",
            "Many US states require a pesticide applicator licence for applying fertiliser with weed control or other "
            "products. Check your state's rules first."),
           ("Two people on site: is the price halved?",
            "No. The time on site is shared, but you pay a helper's wage plus payroll costs, and two people are a little "
            "slower than twice as fast (the efficiency loss on SETTINGS)."),
           ("What does the minimum job charge do?", "No visit is priced below it, however small the lawn. Driving and setup "
            "time make tiny lawns cost more than their size suggests."),
           ("Can I use it on my phone?", "It opens in the Excel and Google Sheets apps, but quoting is easiest on a computer."),
           ("Does it work outside the US?", "Yes: change the currency symbol on SETTINGS and set fuel in your own units "
            "consistently. Rates and prices are US examples.")]
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
            cv.drawCentredString(PW / 2, 10.5 * mm, "Lawn Care Pricing Calculator · Quick-start guide")
            cv.drawRightString(PW - SIDE, 10.5 * mm, f"Page {doc.page}")
            cv.setStrokeColor(c(BORDER))
            cv.line(SIDE, 16 * mm, PW - SIDE, 16 * mm)
        cv.restoreState()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER, leftMargin=SIDE, rightMargin=SIDE, topMargin=16 * mm, bottomMargin=21 * mm,
                            title="Lawn Care Pricing Calculator — Quick-start guide", author="Brass Ledger")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
