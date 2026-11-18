"""Quick-start guide PDF for the Home Daycare Tax Workbook (Brass Ledger style, US Letter).

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
from test_workbook import model, sample_inputs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "home-daycare-tax-workbook" / "BrassLedger_Home_Daycare_Quick_Start_Guide.pdf"
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


def pct(x):
    return f"{x * 100:.2f}%"


def diagram(m):
    """Plain picture of time × space: a floor plan bar and a day bar, then the formula."""
    W, H = CW, 250
    d = Drawing(W, H)
    G, Bc, Pp, Gy = c(GREEN), c(BRASS), c(PAPER), c("C9C3B8")
    # space bar
    y0 = 180
    d.add(String(0, y0 + 46, "SPACE  ·  your home's square feet", fontName="Body-Bold", fontSize=8, fillColor=c(INK2)))
    total = m["home"]
    ex, rg = m["excl"], m["reg"]
    x = 0
    for val, col, lab in ((ex, G, "Exclusive"), (rg, Bc, "Regular: child care + family"), (total - ex - rg, Gy, "Not used")):
        w = W * val / total
        d.add(Rect(x, y0, w, 34, fillColor=col, strokeColor=Pp, strokeWidth=1.5))
        if w > 70:
            d.add(String(x + 6, y0 + 20, lab, fontName="Body-Bold", fontSize=7.5, fillColor=Pp if col != Gy else c(INK)))
            d.add(String(x + 6, y0 + 8, f"{val:,.0f} sq ft · {val / total * 100:.1f}%", fontName="Body", fontSize=7.5,
                         fillColor=Pp if col != Gy else c(INK)))
        x += w
    # time bar
    y1 = 100
    d.add(String(0, y1 + 46, "TIME  ·  hours in the year the home was used for the business", fontName="Body-Bold", fontSize=8, fillColor=c(INK2)))
    tw = W * m["time"]
    d.add(Rect(0, y1, W, 34, fillColor=c(CALC), strokeColor=c(BORDER), strokeWidth=0.8))
    d.add(Rect(0, y1, tw, 34, fillColor=Bc, strokeColor=None))
    d.add(String(6, y1 + 20, "Business hours", fontName="Body-Bold", fontSize=7.5, fillColor=Pp))
    d.add(String(6, y1 + 8, f"{m['bizhours']:,.0f} of {m['avail']:,.0f} hours · {pct(m['time'])}", fontName="Body", fontSize=7.5, fillColor=Pp))
    d.add(String(tw + 6, y1 + 14, "Family time, nights, weekends off", fontName="Body", fontSize=7.5, fillColor=c(INK2)))
    # formula
    y2 = 20
    d.add(Rect(0, y2, W, 58, fillColor=G, strokeColor=None))
    d.add(String(12, y2 + 38, "TIME-SPACE PERCENTAGE", fontName="Body-Bold", fontSize=7.5, fillColor=Bc))
    d.add(String(12, y2 + 16, f"Exclusive {pct(m['excl_pct'])}   +   Regular {pct(m['reg_pct'])} × Time {pct(m['time'])}   =   {pct(m['ts'])}",
                 fontName="Body-Bold", fontSize=11.5, fillColor=Pp))
    return d


def build():
    m = model(sample_inputs())
    logo_path = Path(tempfile.mkdtemp()) / "logo.png"
    logo_rgba(1400).save(logo_path)
    from PIL import Image as PI
    lim = PI.open(logo_path)
    story = []
    # ------------------------------------------------------------ cover
    lw = 70 * mm
    story += [Spacer(1, 14 * mm), Image(str(logo_path), width=lw, height=lw * lim.height / lim.width, hAlign="LEFT"), Spacer(1, 18 * mm),
              P(spaced("Quick-start guide"), "kicker"),
              Paragraph("Home Daycare Tax Workbook", ParagraphStyle("t", fontName="Head", fontSize=34, leading=38, textColor=c(GREEN))),
              Spacer(1, 6), Rule(110, 34), Spacer(1, 12),
              Paragraph("Your time-space percentage, calculated and documented.", ParagraphStyle("st", fontName="Body", fontSize=14, leading=19, textColor=c(INK))),
              Spacer(1, 4), P("For family child care providers in the United States. Excel and Google Sheets.", "small"),
              Spacer(1, 10 * mm), shot("summary1", crop=(0, 0, 1, 0.5)), Spacer(1, 8 * mm),
              P("For record keeping and estimates only. Not tax or legal advice.", "small"), PageBreak()]
    # ------------------------------------------------------------ included + opening
    story += section("1 · What's included", "What's in your download")
    story += [table([["File", "Use it for"],
                     ["BrassLedger_Home_Daycare_Tax_Workbook.xlsx", "Your own records. Start here."],
                     ["BrassLedger_Home_Daycare_Tax_Workbook_SAMPLE.xlsx", "A fictional provider's full 2026 year, so you can see every tab working."],
                     ["BrassLedger_Home_Daycare_Quick_Start_Guide.pdf", "This guide."]], [0.5, 0.5]),
              Spacer(1, 8),
              table([["Tab", "What it does"],
                     ["START HERE", "Quick start, colour key, what to give your preparer, disclaimer."],
                     ["SETTINGS", "Tax year, business dates, rates (simplified method, mileage, meals) and your usual hours."],
                     ["ROOMS", "Each room's square feet and use type. Works out your space shares."],
                     ["HOURS LOG", "One row per day for the whole tax year, prefilled from your usual hours."],
                     ["EXPENSES", "One row per receipt, 500 rows. Applies 100%, time %, time-space % or 0%."],
                     ["MEALS", "Optional food log for the standard meal and snack rates."],
                     ["MILEAGE", "Optional business mileage log."],
                     ["SUMMARY", "The step-by-step percentage and every total, ready to print."],
                     ["TIME-SPACE STATEMENT", "One printable page showing the calculation."],
                     ["FOR YOUR TAX PREPARER", "Home purchase details, improvements, carryovers, income and a checklist."]], [0.3, 0.7], bold_first=True),
              Spacer(1, 8), P("Opening the file", "h2"),
              P("<b>Excel (Windows or Mac, 2016 or later):</b> double-click the .xlsx. If Excel shows <i>Protected View</i>, click "
                "<b>Enable Editing</b>. There are no macros."),
              P("<b>Google Sheets, quickest:</b> open this link while signed in to Google and choose <b>File › Make a copy</b>:"),
              callout("<b>Google Sheets copy link:</b>  [GOOGLE SHEETS COPY LINK]"),
              Spacer(1, 6),
              P("<b>Google Sheets, from the file:</b> drive.google.com › <b>New › File upload</b>, pick the .xlsx, right-click it › "
                "<b>Open with › Google Sheets</b>, then <b>File › Save as Google Sheets</b>. Check <b>File › Settings › Locale</b> is "
                "United States."),
              P("In Google Sheets the formulas, dropdowns and colours all work. Sheet protection does not carry over, so take care not "
                "to type over the shaded cells.", "small"),
              PageBreak()]
    # ------------------------------------------------------------ time-space in plain English
    story += section("2 · The idea", "The time-space percentage, in plain English")
    story += [P("Your home is part business, part family home. The IRS lets you deduct the business part of your home costs. "
                "For a home daycare, that part depends on two things:"),
              bullets(["<b>Space:</b> how much of the home is used for child care. A room used <b>only</b> for child care is "
                       "<b>exclusive</b>. A room the children use every business day that your family also uses is <b>regular</b>. "
                       "Bedrooms and other areas the children don't use don't count.",
                       "<b>Time:</b> how many hours in the year the home was used for the business, out of all the hours in the "
                       "year (8,760; 8,784 in a leap year; fewer if you started or stopped during the year)."]),
              P("Shared rooms only count for the time they are used for the business. Exclusive rooms count in full, so they are "
                "not multiplied by time. The sample provider below has a 320 sq ft playroom used only for child care:"),
              diagram(m), Spacer(1, 6),
              callout(f"<b>The exclusive-use rule.</b> If some space is exclusive and some is regular, the IRS asks you to figure the "
                      f"two parts separately, add them, and attach the calculation (Form 8829 instructions, \"Special Computation for "
                      f"Certain Daycare Facilities\"). The TIME-SPACE STATEMENT tab is that page. With no exclusive space it is "
                      f"simply space % × time %: for example 1,000 of 2,000 sq ft at 23% time = 11.5%."),
              Spacer(1, 6),
              P(f"Sample: {m['bizhours']:,.2f} business hours ÷ {m['avail']:,} hours = {pct(m['time'])} time. Exclusive 320 ÷ 2,000 = "
                f"{pct(m['excl_pct'])}; regular 1,110 ÷ 2,000 = {pct(m['reg_pct'])}, × {pct(m['time'])} = {pct(m['reg_time'])}. "
                f"Time-space percentage: {pct(m['ts'])}.", "small"),
              PageBreak()]
    # ------------------------------------------------------------ settings + rooms
    story += section("3 · Set up", "Settings and rooms")
    story += [P("<b>SETTINGS.</b> Enter your business name and tax year. Leave the start and stop dates empty unless you opened "
                "or closed during the year: then total hours are 24 × the days you were in business, as the Form 8829 "
                "instructions require. Enter your usual opening hours for each weekday; they prefill the hours log."),
              P("<b>Rates.</b> Every rate has a <i>Last checked</i> cell. Rates change, so check each one for your tax year: the "
                "simplified method rate and maximum, the standard mileage rate (2026 changed on July 1: 72.5¢, then 76¢), and the "
                "standard meal and snack rates for your state."),
              P("<b>ROOMS.</b> Measure the whole home and enter the total. Then list every room and area, including hallways, "
                "bathrooms and rooms not used for child care, with its square feet and use type. If the rooms don't add up to the "
                "total, a red message tells you."),
              shot("rooms", crop=(0, 0, 1, 0.82), max_h=290), Spacer(1, 6),
              table([["Use type", "Means", "Examples"],
                     ["Exclusive child care", "Used only for the daycare. No family use, even in the evening.", "A playroom or converted garage that is only for the daycare"],
                     ["Regular child care + family", "Available for child care throughout each business day and used regularly, also used by your family.", "Living room, kitchen, nap room, bathroom, hallway, laundry room"],
                     ["Not used for child care", "Children don't use it, or only occasionally.", "Your bedroom, a home office, a storage room"]],
                    [0.24, 0.4, 0.36], bold_first=True),
              PageBreak()]
    # ------------------------------------------------------------ hours
    story += section("4 · Hours", "Logging hours")
    story += [P("Every day of the tax year is already on the HOURS LOG, prefilled in grey from your usual hours. Once a week:"),
              bullets(["Change the days that were different: late pickups, early closes, extra hours.",
                       "Mark days you were closed with <b>Y</b> in <i>Closed?</i>.",
                       "Mark every other day <b>Yes</b> in <i>Confirmed?</i>. A day counts once it is confirmed, edited or closed."], True),
              shot("hours_left", crop=(0, 0, 1, 0.62)), Spacer(1, 6),
              P("What counts as business hours", "h2"),
              table([["Counts", "Doesn't count"],
                     ["Hours children are in your care", "Shopping trips and errands (time away from home)"],
                     ["Setting up before children arrive", "Family time in the same rooms"],
                     ["Cleaning up after they leave", "Days you were closed"],
                     ["Meal preparation for the children", "Hours you didn't use the home for the business"],
                     ["Paperwork, records, planning at home", ""],
                     ["Parent meetings and interviews at home", ""]], [0.5, 0.5]),
              Spacer(1, 6),
              callout("Pub. 587 compares \"the total time used for business\" with the total time available. It does not list "
                      "these activities, but counting preparation, cleaning and paperwork in the home is common practice among "
                      "providers and preparers. Keep notes of what you did, and confirm with your preparer."),
              PageBreak()]
    # ------------------------------------------------------------ expenses
    story += section("5 · Expenses", "Entering expenses")
    story += [P("Add one row per receipt: date, vendor, description, amount, <b>expense type</b> and <b>category</b>. The type "
                "decides the deductible share; the category decides whether it goes on Schedule C or Form 8829."),
              table([["Expense type", "Share", "Examples"],
                     ["Direct (business only)", "100%", "Toys, craft supplies, cots, license fee, liability insurance, training"],
                     ["Direct home: exclusive area", "100%", "Painting or repairs only in the exclusive playroom"],
                     ["Direct home: shared area", "× time %", "A repair only in the nap room your family also uses (Pub. 587)"],
                     ["Indirect home", "× time-space %", "Mortgage interest, real estate taxes, home insurance, rent, utilities, general repairs, HOA fees"],
                     ["Shared household", "× time-space %", "Cleaning products, paper goods, a washing machine used for both"],
                     ["Personal", "0%", "Family groceries, gifts: recorded but never counted"]], [0.28, 0.16, 0.56], bold_first=True),
              Spacer(1, 6),
              shot("expenses", crop=(0, 0.05, 1, 0.62)), Spacer(1, 6),
              bullets(["The <b>Check</b> column flags anything to fix, such as a receipt from another year or a home cost entered "
                       "with a business type.",
                       "Home costs dated before you started or after you stopped are not counted (Form 8829 instructions).",
                       "Large items such as furniture or appliances may need to be depreciated: your preparer decides.",
                       "A basic local telephone line for the home is not deductible (Pub. 587)."]),
              PageBreak()]
    # ------------------------------------------------------------ meals + mileage
    story += section("6 · Optional", "Meals and mileage")
    story += [P("Food for the children in your care is deductible. You can use either your actual food receipts or the "
                "standard meal and snack rates for eligible children, for the whole year: never both. Choose the method on SETTINGS."),
              P("Standard meal and snack rates", "h2"),
              bullets(["List each child once on the MEALS tab. Children who live in your home, including your own, and children you "
                       "care for as a personal favour are not eligible (Pub. 587).",
                       "Log one row per child per day: breakfast, lunch and dinner (1 each) and up to 3 snacks.",
                       "Rates change each year. Check the current standard meal and snack rates for your state before using. The "
                       "2026 defaults are the contiguous-state rates.",
                       "Food program (CACFP) reimbursements are subtracted from the food deduction; any excess is income (Pub. 587)."]),
              Spacer(1, 4),
              shot("meals", crop=(0, 0.05, 1, 0.5)), Spacer(1, 6),
              P("Mileage", "h2"),
              P("Log business trips: grocery runs for the daycare, training, field trips. The SETTINGS tab holds the standard mileage "
                "rate and an optional change date; for 2026 the IRS rate was 72.5¢ until June 30 and 76¢ from July 1. If you use the "
                "standard mileage rate, don't also enter gas, repairs or insurance for the car."),
              PageBreak()]
    # ------------------------------------------------------------ summary + preparer
    story += section("7 · Results", "The summary and your tax preparer")
    story += [P("The <b>SUMMARY</b> shows the time-space percentage step by step, then Schedule C expenses by category, home "
                "expenses for Form 8829 (direct and indirect columns), food, mileage, and a simplified method estimate next to the "
                "regular method total. The <b>TIME-SPACE STATEMENT</b> is a one-page printout of the calculation."),
              shot("statement", crop=(0, 0, 1, 0.82), max_h=330), Spacer(1, 6),
              P("Give your preparer", "h2"),
              bullets(["The printed SUMMARY and TIME-SPACE STATEMENT, and this file.",
                       "The FOR YOUR TAX PREPARER tab: purchase date and price, land value, improvements, last year's carryovers.",
                       "Form 1098, property tax bills, insurance declarations, utility bills and receipts.",
                       "Food program statements and records of parent payments."]),
              callout("Home depreciation is not calculated in this workbook. Your preparer figures it from the details on the FOR "
                      "YOUR TAX PREPARER tab. The simplified method estimate is an estimate only: your tax preparer will choose the "
                      "right method."),
              PageBreak()]
    # ------------------------------------------------------------ FAQ
    story += section("8 · Questions", "FAQ")
    faq = [("Do I have to log every day?", "Yes: one row per day is already there. Most weeks you only confirm the days that matched "
            "your usual hours and fix the ones that didn't."),
           ("Why doesn't a day count yet?", "Prefilled days count once you confirm, edit or close them, so the log only reflects days "
            "you have checked. The SUMMARY also shows a projection for the unchecked days."),
           ("Can I use it on my phone?", "It opens in the Excel and Google Sheets apps, but it is best on a computer."),
           ("I started my daycare in March.", "Enter the start date on SETTINGS. Total hours become 24 × the days you were in business, "
            "days before that show \"Not in business\", and home costs before that date are not counted."),
           ("I have no exclusive-use room.", "Mark rooms as regular use. The percentage is space × time; no statement is required."),
           ("Should I use the simplified method?", "The SUMMARY shows an estimate next to the regular method total. Your tax preparer "
            "will choose the right method, taking depreciation and income limits into account."),
           ("Does it work for another year?", "Change the tax year on SETTINGS; the dates and total hours update. Start a fresh copy "
            "of the blank file for each year so last year's records stay as they were."),
           ("Is this the IRS form?", "No. It organises your records and shows the calculation. Your preparer completes Schedule C and "
            "Form 8829.")]
    for q_, a_ in faq:
        story.append(KeepTogether([P(f"<b>{q_}</b>"), P(a_), Spacer(1, 1)]))
    story += [Spacer(1, 6), P("IRS sources to check", "h2"),
              bullets(["Publication 587, Business Use of Your Home (daycare facility, simplified method, standard meal and snack rates)",
                       "Form 8829 and its instructions (lines 1 to 7, and the Special Computation for Certain Daycare Facilities)",
                       "Schedule C (Form 1040) and its instructions",
                       "IRS standard mileage rates page (IRS.gov)"]),
              Spacer(1, 6),
              callout("<b>Disclaimer.</b> For record keeping and estimates only. Not tax or legal advice. Tax rules and rates change; "
                      "confirm with IRS Publication 587, the Form 8829 instructions, or a tax professional. For US providers. "
                      "No specific tax saving is promised.")]

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
            cv.drawCentredString(PW / 2, 10.5 * mm, "Home Daycare Tax Workbook · Quick-start guide")
            cv.drawRightString(PW - SIDE, 10.5 * mm, f"Page {doc.page}")
            cv.setStrokeColor(c(BORDER))
            cv.line(SIDE, 16 * mm, PW - SIDE, 16 * mm)
        cv.restoreState()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER, leftMargin=SIDE, rightMargin=SIDE, topMargin=16 * mm, bottomMargin=21 * mm,
                            title="Home Daycare Tax Workbook — Quick-start guide", author="Brass Ledger")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
