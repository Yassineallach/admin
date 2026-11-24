"""Pinterest pins for every Brass Ledger listing: three pin types per product, keyword copy and a posting schedule.

Pinterest is a search engine with pictures. A pin gets clicked when the searcher can tell, at feed size (about 236 px
wide), that it answers what they typed. So each product gets three different pins (Pinterest favours fresh pins over
repins of one image) that target three kinds of search:

  P  product    "budget spreadsheet"          the product name as a big keyword headline + a large real screenshot
  Q  question   "how much to charge for ..."  the searcher's question as the headline + the answer from the sample file
  L  inside     "debt tracker template"       what the file contains: three real screens with numbered captions

Every screenshot is a real render of the sample file. Result chips quote a figure visible in the screenshot and are
labelled as sample figures.

Output: listings/pins/<key>_<type>.png (1000 x 1500), listings/pins/PINS.md (title, description, alt text, board,
link for every pin) and listings/pins/pins_schedule.csv (Pinterest bulk-upload columns, two pins a day).

Usage: python pins.py [key ...]      (default: every product)
"""
from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import brand as BR
from brand_listing import BRASS, GREEN, INK, INK2, PAPER, WHITE, F, FH, wrap
from hero_thumb import BRASS_TINT, D, FAMILY, L, MINI, card, shadow, text_w, tracked

ROOT = Path(__file__).resolve().parent.parent / "listings"
OUT = ROOT / "pins"
PW, PH = 1000, 1500
MX = 56
XS = "Excel + Google Sheets"

BG, PM, WP, PL, BU = ("04_Ultimate_Budget_Spreadsheet", "01_Ultimate_Project_Manager", "03_Weekly_Planner_Pro",
                      "02_Ultimate_OneNote_Planner", "06_Ultimate_Productivity_Bundle")


def W_(path, left=0.0, top=0.0, width=1.0):
    """A window on a screenshot: left/top/width as fractions; the height follows the box it is drawn into."""
    return (path, left, top, width)


# Each product: family, Etsy listing, keyword name, benefit line, the three pins and their copy.
#   p     window for the product pin
#   q     (question, window, chip or None)
#   l     three (window, caption)
#   kw    search phrases, most important first (titles and descriptions are built from these)
#   board Pinterest board
PRODUCTS = {
    "budget": dict(
        fam="finance", listing=BG, name="Budget Spreadsheet", line="Know where your money went, and what is left.",
        p=W_(L(BG, "dashboard"), 0.0, 0.035, 0.62),
        q=("Where does your money actually go each month?", W_(L(BG, "dashboard"), 0.04, 0.16, 0.56),
           ("SAMPLE NET CASH FLOW", "$9,613 left")),
        l=[(W_(L(BG, "dashboard"), 0.03, 0.16, 1.0), "A dashboard for the whole year"),
           (W_(L(BG, "calendar"), 0.0, 0.08, 0.75), "Bills on a calendar that fills itself"),
           (W_(L(BG, "rule"), 0.0, 0.5, 1.0), "50/30/20 split, worked out for you")],
        kw=["budget spreadsheet", "monthly budget template", "Google Sheets budget", "Excel budget template", "bill tracker"],
        board="Budget Spreadsheets & Money Templates"),
    "debt": dict(
        fam="finance", listing=MINI + "Debt_Payoff_Calculator", name="Debt Payoff Calculator", line="Know the date you will be debt-free.",
        p=W_(L(MINI + "Debt_Payoff_Calculator", "main"), 0.0, 0.0, 0.55),
        q=("When will I actually be debt-free?", W_(L(MINI + "Debt_Payoff_Calculator", "main"), 0.73, 0.28, 0.27),
           ("DEBT-FREE DATE (SAMPLE)", "Apr 2030")),
        l=[(W_(L(MINI + "Debt_Payoff_Calculator", "main"), 0.0, 0.0, 0.6), "List every debt once"),
           (W_(L(MINI + "Debt_Payoff_Calculator", "schedule"), 0.0, 0.0, 0.55), "A month-by-month payoff plan"),
           (W_(L(MINI + "Debt_Payoff_Calculator", "main"), 0.0, 0.8, 1.0), "Debt-free date and interest saved")],
        kw=["debt payoff calculator", "debt snowball spreadsheet", "debt avalanche", "debt tracker", "debt free plan"],
        board="Debt Payoff & Saving Money"),
    "funds": dict(
        fam="finance", listing=MINI + "Sinking_Funds_Tracker", name="Sinking Funds Tracker", line="Save for each goal and see if you are on track.",
        p=W_(L(MINI + "Sinking_Funds_Tracker", "main"), 0.0, 0.0, 0.55),
        q=("How much should you save each month for each goal?", W_(L(MINI + "Sinking_Funds_Tracker", "main"), 0.03, 0.06, 0.58),
           ("OVERALL PROGRESS (SAMPLE)", "69% saved")),
        l=[(W_(L(MINI + "Sinking_Funds_Tracker", "main"), 0.03, 0.06, 0.6), "Up to 15 savings goals"),
           (W_(L(MINI + "Sinking_Funds_Tracker", "main"), 0.0, 0.6, 0.6), "Progress bars and months to go"),
           (W_(L(MINI + "Sinking_Funds_Tracker", "log"), 0.0, 0.1, 0.7), "A log for deposits and withdrawals")],
        kw=["sinking funds tracker", "savings goal tracker", "sinking funds spreadsheet", "savings tracker", "budget categories"],
        board="Debt Payoff & Saving Money"),
    "networth": dict(
        fam="finance", listing=MINI + "Net_Worth_Tracker", name="Net Worth Tracker", line="See what you own, what you owe and the difference.",
        p=W_(L(MINI + "Net_Worth_Tracker", "history"), 0.0, 0.0, 1.0),
        q=("Is your net worth actually going up?", W_(L(MINI + "Net_Worth_Tracker", "history"), 0.5, 0.06, 0.5), None),
        l=[(W_(L(MINI + "Net_Worth_Tracker", "main"), 0.0, 0.0, 0.7), "Assets and debts on one page"),
           (W_(L(MINI + "Net_Worth_Tracker", "history"), 0.0, 0.06, 0.55), "24 months of history"),
           (W_(L(MINI + "Net_Worth_Tracker", "history"), 0.5, 0.3, 0.5), "A chart of the trend")],
        kw=["net worth tracker", "net worth spreadsheet", "personal finance spreadsheet", "wealth tracker", "financial goals"],
        board="Budget Spreadsheets & Money Templates"),
    "nospend": dict(
        fam="finance", listing=MINI + "No_Spend_Challenge_Tracker", name="No-Spend Challenge", line="Count your no-spend days and what they saved.",
        p=W_(L(MINI + "No_Spend_Challenge_Tracker", "main"), 0.0, 0.0, 0.62),
        q=("How much could a no-spend month save you?", W_(L(MINI + "No_Spend_Challenge_Tracker", "main"), 0.0, 0.25, 0.62), None),
        l=[(W_(L(MINI + "No_Spend_Challenge_Tracker", "main"), 0.0, 0.0, 0.7), "Pick a start date and a length"),
           (W_(L(MINI + "No_Spend_Challenge_Tracker", "main"), 0.0, 0.25, 0.62), "Mark each day, keep your streak"),
           (W_(L(MINI + "No_Spend_Challenge_Tracker", "main"), 0.45, 0.45, 0.55), "See the money it saved")],
        kw=["no spend challenge", "no spend tracker", "savings challenge", "frugal living", "money saving challenge"],
        board="Debt Payoff & Saving Money"),
    "invest": dict(
        fam="finance", listing=MINI + "Investment_Growth_Calculator", name="Investment Calculator", line="See what regular investing could be worth.",
        p=W_(L(MINI + "Investment_Growth_Calculator", "main"), 0.0, 0.0, 0.62),
        q=("What could $250 a month grow to in 20 years?", W_(L(MINI + "Investment_Growth_Calculator", "compare"), 0.0, 0.0, 0.6),
           ("AT 6% A YEAR (HYPOTHETICAL)", "$132,061")),
        l=[(W_(L(MINI + "Investment_Growth_Calculator", "main"), 0.0, 0.0, 0.62), "Your amount, contribution and years"),
           (W_(L(MINI + "Investment_Growth_Calculator", "main"), 0.0, 0.72, 0.6), "Growth year by year"),
           (W_(L(MINI + "Investment_Growth_Calculator", "compare"), 0.0, 0.0, 0.6), "Three return scenarios side by side")],
        kw=["investment calculator", "compound interest calculator", "investment growth spreadsheet", "retirement savings", "investing for beginners"],
        board="Budget Spreadsheets & Money Templates"),
    "habits": dict(
        fam="finance", listing=MINI + "Habit_Tracker", name="Habit Tracker", line="See which habits you keep, month by month.",
        p=W_(L(MINI + "Habit_Tracker", "main"), 0.0, 0.0, 0.55),
        q=("Which habits do you actually keep?", W_(L(MINI + "Habit_Tracker", "year"), 0.0, 0.0, 0.6),
           ("SAMPLE YEAR", "64% overall")),
        l=[(W_(L(MINI + "Habit_Tracker", "main"), 0.0, 0.0, 0.55), "Tick each day, up to 12 habits"),
           (W_(L(MINI + "Habit_Tracker", "main"), 0.0, 0.6, 0.7), "Monthly success chart"),
           (W_(L(MINI + "Habit_Tracker", "year"), 0.0, 0.0, 0.6), "The whole year on one page")],
        kw=["habit tracker", "habit tracker spreadsheet", "digital habit tracker", "Google Sheets habit tracker", "2027 goals"],
        board="Planner & Productivity Templates"),
    "pm": dict(
        fam="planning", listing=PM, name="Project Manager", line="Every project, task and deadline in one place.",
        p=W_(L(PM, "AllinOne_Dashboard"), 0.0, 0.0, 0.6),
        q=("How do you keep track of every project at once?", W_(L(PM, "AllinOne_Dashboard"), 0.0, 0.0, 0.62), None),
        l=[(W_(L(PM, "AllinOne_Dashboard"), 0.0, 0.0, 1.0), "A dashboard that updates itself"),
           (W_(L(PM, "Gantt_Chart"), 0.0, 0.0, 0.6), "A Gantt chart for every project"),
           (W_(L(PM, "Kanban_Board"), 0.0, 0.0, 0.7), "A Kanban board for the week")],
        kw=["project management template", "project tracker spreadsheet", "Gantt chart template", "Kanban board", "small business planner"],
        board="Planner & Productivity Templates"),
    "wp": dict(
        fam="planning", listing=WP, name="Weekly Planner", line="Plan the week and see what got done.",
        p=W_(L(WP, "week_top"), 0.0, 0.0, 0.6),
        q=("What did you actually get done this week?", W_(L(WP, "trackers"), 0.0, 0.5, 0.6), None),
        l=[(W_(L(WP, "week_top"), 0.0, 0.0, 0.7), "Plan the week in one view"),
           (W_(L(WP, "trackers"), 0.0, 0.0, 0.6), "Habits, water and exercise"),
           (W_(L(WP, "calendar"), 0.0, 0.0, 0.7), "A monthly calendar that fills itself")],
        kw=["weekly planner spreadsheet", "digital weekly planner", "weekly planner template", "to do list template", "productivity planner"],
        board="Planner & Productivity Templates"),
    "planner": dict(
        fam="planning", listing=PL, name="OneNote Digital Planner", line="Your year, your weeks and your work notes in one place.",
        p=W_(L(PL, "index"), 0.0, 0.0, 1.0),
        q=("Looking for a 2027 planner for OneNote?", W_(L(PL, "index"), 0.0, 0.0, 1.0), None),
        l=[(W_(L(PL, "index"), 0.0, 0.0, 1.0), "One index links every page"),
           (W_(L(PL, "m1_cal"), 0.0, 0.0, 1.0), "12 months and 53 weeks"),
           (W_(L(PL, "meeting_1"), 0.0, 0.0, 1.0), "111 work templates")],
        kw=["OneNote planner", "2027 digital planner", "digital planner", "hyperlinked PDF planner", "work planner"],
        board="Planner & Productivity Templates"),
    "bundle": dict(
        fam="planning", listing=BU, name="Productivity Bundle", line="Your projects, your week and your money: three templates.",
        p=None,
        q=("Need one system for your projects, your week and your money?", None, None),
        l=[(W_(L(PM, "AllinOne_Dashboard"), 0.0, 0.0, 1.0), "Project Manager, 15 tabs"),
           (W_(L(WP, "week_top"), 0.0, 0.0, 0.7), "Weekly Planner Pro, 8 tabs"),
           (W_(L(BG, "dashboard"), 0.03, 0.16, 1.0), "Budget Spreadsheet, 28 tabs")],
        kw=["spreadsheet bundle", "productivity templates", "Google Sheets templates", "Excel templates", "planner bundle"],
        board="Planner & Productivity Templates"),
    "whatnot": dict(
        fam="business", listing="whatnot-profit-tracker", name="Whatnot Profit Tracker", line="See the real profit from every live show.",
        p=W_(D("whatnot-profit-tracker", "dash_hero"), 0.0, 0.0, 0.6),
        q=("Are your Whatnot shows actually making money?", W_(D("whatnot-profit-tracker", "dash_hero"), 0.0, 0.0, 0.6),
           ("SAMPLE PROFIT PER LIVE HOUR", "$139.94")),
        l=[(W_(D("whatnot-profit-tracker", "log_profit"), 0.0, 0.0, 0.6), "One row per show"),
           (W_(D("whatnot-profit-tracker", "dash_trend"), 0.0, 0.0, 1.0), "Profit month by month"),
           (W_(D("whatnot-profit-tracker", "dash_slot"), 0.0, 0.0, 1.0), "Your most profitable time slot")],
        kw=["Whatnot seller", "Whatnot profit tracker", "reseller spreadsheet", "live selling", "reseller profit tracker"],
        board="Small Business Pricing & Profit Templates"),
    "daycare": dict(
        fam="business", listing="home-daycare-tax-workbook", name="Home Daycare Tax Workbook", line="Your time-space percentage, calculated and documented.",
        p=W_(D("home-daycare-tax-workbook", "dash_top"), 0.0, 0.0, 0.62),
        q=("What is your daycare time-space percentage?", W_(D("home-daycare-tax-workbook", "dash_hero"), 0.0, 0.0, 0.5),
           ("SAMPLE TIME-SPACE PERCENTAGE", "35.48%")),
        l=[(W_(D("home-daycare-tax-workbook", "hours"), 0.0, 0.0, 0.5), "Log hours, including prep and cleaning"),
           (W_(D("home-daycare-tax-workbook", "dash_space"), 0.0, 0.0, 1.0), "Space use worked out from your rooms"),
           (W_(D("home-daycare-tax-workbook", "dash_ded"), 0.0, 0.0, 1.0), "Every deduction in one summary")],
        kw=["home daycare taxes", "family child care tax", "time space percentage", "daycare business", "daycare expense tracker"],
        board="Small Business Pricing & Profit Templates"),
    "lawn": dict(
        fam="business", listing="lawn-care-pricing-calculator", name="Lawn Care Pricing Calculator", line="Price every lawn for profit in two minutes.",
        p=W_(D("lawn-care-pricing-calculator", "quote_top"), 0.0, 0.0, 0.62),
        q=("How much should you charge to mow a lawn?", W_(D("lawn-care-pricing-calculator", "dash_hero"), 0.0, 0.0, 0.5),
           ("SAMPLE BREAK-EVEN RATE", "$32.14 / hour")),
        l=[(W_(D("lawn-care-pricing-calculator", "quote_top"), 0.0, 0.0, 0.62), "Quote a lawn in two minutes"),
           (W_(D("lawn-care-pricing-calculator", "route_summary"), 0.0, 0.0, 1.0), "Revenue per hour, by weekday"),
           (W_(D("lawn-care-pricing-calculator", "dash_months"), 0.0, 0.0, 1.0), "Season revenue against goal")],
        kw=["lawn care pricing", "lawn mowing prices", "lawn care business", "how much to charge for lawn care", "landscaping business"],
        board="Small Business Pricing & Profit Templates"),
    "pressure": dict(
        fam="business", listing="pressure-washing-bid-calculator", name="Pressure Washing Bid Calculator", line="Quote any job in two minutes, without underpricing.",
        p=W_(D("pressure-washing-bid-calculator", "quote_top"), 0.0, 0.0, 0.6),
        q=("How much should you charge for pressure washing?", W_(D("pressure-washing-bid-calculator", "quote_lines"), 0.0, 0.0, 0.5),
           ("SAMPLE 4-SERVICE JOB", "$531 quote")),
        l=[(W_(D("pressure-washing-bid-calculator", "quote_lines"), 0.0, 0.0, 0.55), "Price each surface on one quote"),
           (W_(D("pressure-washing-bid-calculator", "quote_cost"), 0.0, 0.0, 0.6), "Chemicals, setup and drive time counted"),
           (W_(D("pressure-washing-bid-calculator", "jobs_summary"), 0.0, 0.0, 1.0), "Estimate against actual, by service")],
        kw=["pressure washing pricing", "pressure washing business", "power washing prices", "pressure washing estimate", "soft wash pricing"],
        board="Small Business Pricing & Profit Templates"),
    "cake": dict(
        fam="business", listing="cake-pricing-calculator", name="Cake Pricing Calculator", line="Know what every cake really costs.",
        p=W_(D("cake-pricing-calculator", "cake1_price"), 0.0, 0.0, 0.6),
        q=("How much should you charge for a cake?", W_(D("cake-pricing-calculator", "cake1_price"), 0.0, 0.0, 0.6),
           ("SAMPLE WEDDING CAKE", "$11.35 / serving")),
        l=[(W_(D("cake-pricing-calculator", "recipe_block"), 0.0, 0.0, 0.6), "Cost every recipe once"),
           (W_(D("cake-pricing-calculator", "cake1_top"), 0.0, 0.0, 0.62), "Build the cake tier by tier"),
           (W_(D("cake-pricing-calculator", "orders_up"), 0.0, 0.0, 1.0), "Orders and deposits in one list")],
        kw=["cake pricing", "how to price cakes", "home bakery business", "cake pricing calculator", "cake business"],
        board="Small Business Pricing & Profit Templates"),
}

# Pin colours per family: product pin (top, panel), question pin (background, text, accent)
PFAM = {
    "finance": dict(q_bg=GREEN, q_text=PAPER, q_line=BR.rgb("D6E0DC"), q_logo_green=True),
    "planning": dict(q_bg=PAPER, q_text=GREEN, q_line=INK2, q_logo_green=False),
    "business": dict(q_bg=BRASS, q_text=GREEN, q_line=GREEN, q_logo_green=False),
}


def fmt_of(p):
    return "OneNote + PDF" if p["listing"] == PL else XS


# ---------------------------------------------------------------------------------------------- drawing helpers
def window(spec, aspect):
    """Crop a window from a screenshot at the given width/height aspect, keeping it inside the image."""
    path, left, top, width = spec
    im = Image.open(path).convert("RGB")
    w, h = im.size
    cw = int(w * width)
    ch = int(cw / aspect)
    if ch > h:                                  # too tall for the image: keep the full height, narrow the width
        ch, cw = h, int(h * aspect)
    x0 = min(int(w * left), w - cw)
    y0 = max(0, min(int(h * top), h - ch))
    return im.crop((x0, y0, x0 + cw, y0 + ch))


def shot_card(img, spec, box):
    """A window that fills the box exactly, on a white card."""
    x0, y0, x1, y1 = box
    pad = 14
    sh = window(spec, (x1 - x0 - 2 * pad) / (y1 - y0 - 2 * pad))
    return card(img, sh, x0, y0, x1 - x0, y1 - y0)


def headline(d, text, top, color, max_w, size, max_lines, min_size=60):
    """Fraunces headline, centred, as large as fits in max_lines. Returns y below it."""
    while True:
        f = FH(size)
        lines = wrap(d, text, f, max_w)
        if (len(lines) <= max_lines and all(text_w(d, ln, f) <= max_w for ln in lines)) or size <= min_size:
            break
        size -= 4
    y = top
    for ln in lines:
        tracked(d, (PW / 2 - text_w(d, ln, f) / 2, y), ln, f, color)
        y += size * 1.12
    return y + size * 0.2


def chip(img, x1, y0, lab, fig, fill=GREEN):
    d = ImageDraw.Draw(img)
    fl, ff = F(24, 700), F(58, 800)
    w = max(d.textlength(fig, font=ff), d.textlength(lab, font=fl) + 0.2 * 24 * len(lab)) + 76
    box = (x1 - w, y0, x1, y0 + 160)
    shadow(img, box, 22, 110, 20, 12)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, 22, fill=fill)
    BR.spaced(d, (box[0] + 38, box[1] + 36), lab, fl, BRASS, 0.2)
    d.text((box[0] + 38, box[1] + 118), fig, font=ff, fill=PAPER, anchor="ls")
    return box


def footer(img, on_green, fg, sub_col):
    d = ImageDraw.Draw(img)
    BR.wordmark(img, (MX, PH - 96), 44, on_green=on_green)
    d.text((PW - MX, PH - 70), "Instant download on Etsy", font=F(26, 600), fill=sub_col, anchor="rm")


def pill_row(d, y, items, fills):
    bs, gap = 28, 18
    f = F(bs, 700)
    widths = [d.textlength(b, font=f) + 1.6 * bs for b in items]
    x = PW / 2 - (sum(widths) + gap * (len(items) - 1)) / 2
    for b, (fill, col), wd in zip(items, fills, widths):
        d.rounded_rectangle((x, y, x + wd, y + 2 * bs), bs, fill=fill)
        d.text((x + wd / 2, y + bs), b, font=f, fill=col, anchor="mm")
        x += wd + gap
    return y + 2 * bs


def fan(img, top, bottom):
    """Bundle: the three products' screens, overlapping."""
    hgt = bottom - top
    cw = 600
    card(img, window(W_(L(WP, "week_top"), 0, 0, 0.7), 1.25), MX, top, cw, int(hgt * 0.62))
    card(img, window(W_(L(BG, "dashboard"), 0.0, 0.035, 0.62), 1.25), PW - MX - cw, top, cw, int(hgt * 0.62))
    mw = min(700, int(hgt * 0.62 * 1.3) + 28)
    return card(img, window(W_(L(PM, "AllinOne_Dashboard"), 0, 0, 0.6), 1.3), PW // 2 - mw // 2, top + int(hgt * 0.36), mw, int(hgt * 0.64))


# ---------------------------------------------------------------------------------------------- the three pin types
def pin_product(key, p):
    fam = FAMILY[p["fam"]]
    img = Image.new("RGB", (PW, PH), fam["top"])
    d = ImageDraw.Draw(img)
    BR.spaced(d, (PW / 2, 78), (fmt_of(p) + (" template" if fmt_of(p) == XS else " planner")).upper(), F(24, 700), BRASS, 0.22, anchor="m")
    y = headline(d, p["name"], 118, fam["title"], PW - 2 * MX, 118, 2)
    BR.double_rule(d, PW / 2 - 110, y + 4, 220, 60)
    y += 52
    for ln in wrap(d, p["line"], F(36, 500), PW - 2 * MX - 40):
        d.text((PW / 2, y), ln, font=F(36, 500), fill=fam["line"], anchor="mt")
        y += 46
    top, bottom = int(y) + 34, PH - 190
    d.rectangle((0, top + 120, PW, PH), fill=fam["panel"])     # colour panel behind the lower part of the screenshot
    if p["p"] is None:
        box = fan(img, top, bottom)
    else:
        box = shot_card(img, p["p"], (MX, top, PW - MX, bottom))
    if p["q"][2] and key != "debt":
        chip(img, PW - MX + 10, box[3] - 120, *p["q"][2])
    footer(img, fam["logo_green"], None, PAPER if fam["panel"] == GREEN else GREEN)
    return img


def pin_question(key, p):
    pf = PFAM[p["fam"]]
    img = Image.new("RGB", (PW, PH), pf["q_bg"])
    d = ImageDraw.Draw(img)
    question, spec, ch = p["q"]
    y = headline(d, question, 96, pf["q_text"], PW - 2 * MX, 112, 4)
    BR.double_rule(d, PW / 2 - 110, y + 6, 220, 60)
    y += 70
    bottom = PH - 330
    if spec is None:
        box = fan(img, int(y) - 40, bottom - 40)
    else:
        box = shot_card(img, spec, (MX, int(y), PW - MX, bottom))
    if ch:
        chip(img, PW - MX + 10, box[3] - 110, *ch, fill=GREEN if p["fam"] != "finance" else BR.rgb("16302A"))
    # the answer: the product, named
    yy = PH - 268
    d.text((PW / 2, yy), "THE TEMPLATE", font=F(22, 700), fill=BRASS if p["fam"] != "business" else GREEN, anchor="mt")
    f = FH(64)
    while text_w(d, p["name"], f) > PW - 2 * MX and f.size > 40:
        f = FH(f.size - 2)
    tracked(d, (PW / 2 - text_w(d, p["name"], f) / 2, yy + 34), p["name"], f, pf["q_text"])
    footer(img, pf["q_logo_green"], None, pf["q_line"])
    return img


def pin_inside(key, p):
    img = Image.new("RGB", (PW, PH), PAPER)
    d = ImageDraw.Draw(img)
    f = FH(96)
    one_line = len(wrap(d, p["name"], f, PW - 2 * MX)) == 1
    band = 300 if one_line else 400
    d.rectangle((0, 0, PW, band), fill=GREEN)
    BR.spaced(d, (PW / 2, 62), "WHAT IS INSIDE", F(24, 700), BRASS, 0.25, anchor="m")
    headline(d, p["name"], 98, PAPER, PW - 2 * MX, 96, 2, min_size=56)
    pill_row(d, band - 28, [fmt_of(p), "Instant download"], [(BRASS, GREEN), (PAPER, GREEN)])
    y = band + 44
    step = (PH - 130 - y) / 3
    for i, (spec, cap) in enumerate(p["l"], 1):
        d.ellipse((MX, y, MX + 52, y + 52), fill=BRASS)
        d.text((MX + 26, y + 27), str(i), font=F(30, 800), fill=GREEN, anchor="mm")
        d.text((MX + 72, y + 27), cap, font=F(34, 700), fill=GREEN, anchor="lm")
        shot_card(img, spec, (MX, int(y + 66), PW - MX, int(y + step - 30)))
        y += step
    footer(img, False, None, INK2)
    return img


TYPES = {"product": pin_product, "question": pin_question, "inside": pin_inside}


# ---------------------------------------------------------------------------------------------- copy
def cap(s):
    return s[0].upper() + s[1:]


def copy(key, p, kind):
    """Pin title (<= 100), description (<= 500) and alt text. Keyword first, plain voice, no hashtags."""
    k = p["kw"]
    nm = p["name"]
    fmt = "Works in Excel and Google Sheets." if p["listing"] != PL else "OneNote notebook plus a hyperlinked PDF for GoodNotes, Notability and other PDF apps."
    if kind == "product":
        title = f"{cap(k[0])}: {p['line'].rstrip('.')}"
        desc = (f"{nm} template. {p['line']} {fmt} Includes a filled-in sample so you can see how it works before "
                f"you add your own numbers. Use it as a {k[1]} or a {k[2]}. Instant download from Brass Ledger on Etsy.")
        alt = f"{nm} template shown in a spreadsheet, with the text: {p['line']}"
    elif kind == "question":
        q = p["q"][0]
        title = f"{q} {cap(k[0])}"
        ans = {
            "budget": "Log income and spending once and the dashboard shows where it went, what is left and how much you saved.",
            "debt": "List your debts, choose snowball or avalanche, and the calculator gives your debt-free date and a monthly plan.",
            "funds": "Enter a target and a date for each goal and the tracker works out the monthly amount and whether you are on track.",
            "networth": "Record what you own and what you owe once a month and the tracker charts the change over 24 months.",
            "nospend": "Mark each day of your challenge and the tracker counts your streak and the money it kept in your account.",
            "invest": "Enter a starting amount, a monthly contribution and the years, and compare three return assumptions. Hypothetical projections for planning, not advice.",
            "habits": "Tick each habit every day and the tracker shows your success rate by habit, month and year.",
            "pm": "Projects, tasks, budgets and deadlines go in once; the dashboard, Gantt chart and Kanban board update themselves.",
            "wp": "Plan tasks, schedule and habits for the week, then see what got done and how the month looks.",
            "planner": "A 2027 and undated planner with an index that links every month, week and template.",
            "bundle": "Three complete templates at one price: a project manager, a weekly planner and a budget spreadsheet.",
            "whatnot": "Log each show once and the tracker takes off fees, item costs, giveaways and supplies to show real profit per show and per hour.",
            "daycare": "Log your hours and rooms and the workbook works out your time-space percentage and the share of each expense. For US providers; check with your tax preparer.",
            "lawn": "Enter your costs once and the calculator gives your break-even hourly rate and a price for every lawn, visit and season.",
            "pressure": "Enter each surface and its size and the calculator prices the job, counting chemicals, setup, drive time and your target margin.",
            "cake": "Cost your recipes once, build the cake tier by tier, and see the true cost, the price and the price per serving.",
        }[key]
        desc = f"{q} {ans} {fmt} A simple {k[0]} and {k[3]}. Instant download from Brass Ledger on Etsy."
        alt = f"The question '{q}' above a screenshot of the {nm} answering it with sample figures"
    else:
        caps = "; ".join(c for _, c in p["l"]).lower()
        title = f"What is inside the {nm} | {cap(k[2])}"
        desc = (f"What is inside the {nm}: {caps}. {fmt} Ready to use, with a sample file and a blank file. "
                f"A simple {k[2]} and {k[4]} template. Instant download from Brass Ledger on Etsy.")
        alt = f"Three screenshots of the {nm}: {caps}"
    assert len(title) <= 100 and len(desc) <= 500, (key, kind, len(title), len(desc))
    return title, desc, alt


# ---------------------------------------------------------------------------------------------- schedule
# New Year money and planning searches peak now through January; tax and lawn-season searches start in January and
# February, so those products go first in their own rounds but repeat in the follow-up notes.
ORDER = ["budget", "debt", "planner", "daycare", "habits", "nospend", "wp", "cake", "funds", "whatnot", "pm",
         "invest", "networth", "lawn", "pressure", "bundle"]


def main(keys):
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("pin_*.png"):           # the previous single-pin set
        old.unlink()
    made = {}
    for key in keys:
        p = PRODUCTS[key]
        for kind, fn in TYPES.items():
            path = OUT / f"{key}_{kind}.png"
            fn(key, p).save(path, "PNG", optimize=True)
            made[(key, kind)] = path
            print("wrote", path.name)
    if set(keys) != set(PRODUCTS):
        return
    start = dt.date.today() + dt.timedelta(days=1)
    rows, md = [], ["# Pinterest pins", "",
                    "Three pins per listing, 1000 x 1500 px: a **product** pin (the name as the headline), a **question** pin "
                    "(what buyers type into Pinterest search, answered by the sample file) and an **inside** pin (three real screens). "
                    "Three different images send three times the fresh-pin signal of one image pinned three times.", "",
                    "How to post: upload the image, paste the title, description and alt text, choose the board, and set the link "
                    "to that product's Etsy listing. `pins_schedule.csv` has the same copy in Pinterest's bulk-upload format "
                    "(add your Etsy links and the image URLs, or post by hand from it). Two pins a day keeps the account active "
                    "without flooding followers.", "",
                    "## Boards", "",
                    "Create these boards first and give each a one-line description that uses its name:", "",
                    *[f"- **{b}**" for b in dict.fromkeys(p["board"] for p in PRODUCTS.values())],
                    "- **Excel & Google Sheets Templates**: save every pin here as well, as a second board.", ""]
    n = 0
    for kind in TYPES:
        for key in ORDER:
            p = PRODUCTS[key]
            title, desc, alt = copy(key, p, kind)
            day = start + dt.timedelta(days=n // 2)
            n += 1
            rows.append({"Title": title, "Media URL": "", "Pinterest board": p["board"], "Thumbnail": "",
                         "Description": desc, "Link": f"ETSY LINK: {p['name']}", "Publish date": f"{day.isoformat()}T{'14:00:00' if n % 2 else '20:00:00'}",
                         "Keywords": ", ".join(p["kw"]), "Image file": made[(key, kind)].name, "Alt text": alt})
    md += ["## Pins, in posting order", ""]
    for r in rows:
        md += [f"### {r['Image file']} ({r['Publish date'][:10]})", "", f"- **Board:** {r['Pinterest board']}",
               f"- **Title:** {r['Title']}", f"- **Description:** {r['Description']}", f"- **Alt text:** {r['Alt text']}",
               f"- **Link:** the Etsy listing for {PRODUCTS[r['Image file'].rsplit('_', 1)[0]]['name']}", ""]
    (OUT / "PINS.md").write_text("\n".join(md), encoding="utf-8")
    with open(OUT / "pins_schedule.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("wrote PINS.md and pins_schedule.csv,", len(rows), "pins")


if __name__ == "__main__":
    BR.ensure_fonts()
    main(sys.argv[1:] or list(PRODUCTS))
