"""Quick-start guide PDF for the Cake Pricing Calculator (Brass Ledger style, US Letter).

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
from test_workbook import batch, cake, ingredients, recipes, settings  # noqa: E402
import cake_config as CFG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "cake-pricing-calculator" / "BrassLedger_Cake_Pricing_Quick_Start_Guide.pdf"
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
    ing = ingredients()
    rec = recipes(ing)
    w = cake(CFG.CAKES[0], rec, s)
    b = cake(CFG.CAKES[1], rec, s)
    cup = batch(CFG.BATCHES[0], rec, s)
    d = CFG.CAKES[0]
    logo_path = Path(tempfile.mkdtemp()) / "logo.png"
    logo_rgba(1400).save(logo_path)
    from PIL import Image as PI
    lim = PI.open(logo_path)
    story = []
    lw = 70 * mm
    story += [Spacer(1, 14 * mm), Image(str(logo_path), width=lw, height=lw * lim.height / lim.width, hAlign="LEFT"), Spacer(1, 16 * mm),
              P(spaced("Quick-start guide"), "kicker"),
              Paragraph("Cake Pricing Calculator", ParagraphStyle("t", fontName="Head", fontSize=32, leading=36, textColor=c(GREEN))),
              Spacer(1, 6), Rule(110, 34), Spacer(1, 12),
              Paragraph("Know what every cake really costs, and what to charge for it.",
                        ParagraphStyle("st", fontName="Body", fontSize=14, leading=19, textColor=c(INK))),
              Spacer(1, 4), P("For home bakers and small cake businesses. Excel and Google Sheets, US and metric units.", "small"),
              Spacer(1, 9 * mm), shot("cake1_top", crop=(0, 0, 1, 1), max_h=290), Spacer(1, 6 * mm),
              P("Prices are estimates based on the numbers you enter. Not financial, legal or tax advice.", "small"),
              PageBreak()]
    # 1 included + opening
    story += section("1 · What's included", "What's in your download")
    story += [table([["File", "Use it for"],
                     ["BrassLedger_Cake_Pricing_Calculator.xlsx", "Your bakery. 48 ingredient names with grams per cup, the pan table and defaults are filled in."],
                     ["BrassLedger_Cake_Pricing_Calculator_SAMPLE.xlsx", "A fictional bakery with prices, 9 recipes, two cakes, two batches and 15 orders."],
                     ["BrassLedger_Cake_Pricing_Quick_Start_Guide.pdf", "This guide."]], [0.5, 0.5]),
              Spacer(1, 8),
              table([["Tab", "What it does"],
                     ["START HERE", "Four-step quick start, colour key, reminders."],
                     ["SETTINGS", "Bakery details, hourly rate, margin, minimum per serving, deposit, overhead, delivery, supplies, decorations, units, pans."],
                     ["INGREDIENTS", "What you pay for each ingredient; cost per gram, ml and item."],
                     ["RECIPES", "Up to 40 recipes, each costed line by line, with cost per cup, gram or item."],
                     ["CAKE BUILDER", "Up to three cakes of up to 5 tiers: quantities, servings, cost, price, deposit."],
                     ["BATCH PRICING", "Cupcakes, cookies, cake pops: price per item, half dozen and dozen."],
                     ["CUSTOMER QUOTE", "A one-page quote with your bakery name, for letter or A4."],
                     ["ORDER TRACKER", "Orders, deposits, balances and what's coming up."],
                     ["DASHBOARD", "This month, the year, deposits and orders due this week."]], [0.26, 0.74], bold_first=True),
              Spacer(1, 8), P("Opening in Excel", "h2"),
              P("Excel 2016 or later on Windows or Mac: double-click the .xlsx. If you see <i>Protected View</i>, click "
                "<b>Enable Editing</b>. There are no macros. Use the dark bar on the left of each tab to move around."),
              P("Opening in Google Sheets", "h2"),
              P("Quickest: open this link while signed in to Google and choose <b>File › Make a copy</b>:"),
              callout("<b>Google Sheets copy link:</b>  [GOOGLE SHEETS COPY LINK]"),
              Spacer(1, 5),
              P("Or upload the .xlsx to drive.google.com, right-click it, <b>Open with › Google Sheets</b>, then <b>File › Save as "
                "Google Sheets</b>. Formulas, dropdowns and charts work; sheet protection and the icon bar don't carry over "
                "(short text links appear instead).", "small"),
              PageBreak()]
    # 2 rate and margin
    ing_only = w["ing"] + w["dec"] + w["sup"]
    story += section("2 · Your rate", "Your hourly rate, margin and minimum")
    story += [P("Open <b>SETTINGS</b> and set your bakery details, then three numbers that decide every price:"),
              bullets([f"<b>Hourly rate</b> ({money(s['rate'])} in the sample): what your time is worth. Every hour on the "
                       "cake, from the consultation to delivery, is charged at this rate.",
                       f"<b>Target margin</b> ({s['margin']:.0%}): profit on top of paying yourself, for slow months, new tools "
                       "and growth.",
                       f"<b>Minimum price per serving</b> ({money(s['min_serving'])}): the builder warns when a cake falls below it."]),
              P("Why pricing by ingredients loses money", "h2"),
              P(f"The sample wedding cake uses {money(w['ing'])} of batter, filling, frosting and fondant. Add the sugar "
                f"flowers, gold leaf, boards, drum, dowels and box and it is still only {money(ing_only)}. A common rule "
                f"of thumb, three times ingredients, would charge about {money(3 * ing_only)}. But the cake takes "
                f"<b>{w['hours']:.1f} hours</b>: at {money(s['rate'])} an hour that is {money(w['lab'])} of your time, before "
                f"overhead and delivery. Its real cost is <b>{money(w['cost'])}</b>, and the price that covers it with your "
                f"margin is <b>{money(w['price'])}</b>."),
              callout(f"Priced on ingredients alone, this cake would have paid you about "
                      f"{money(max(0, (3 * ing_only - (w['cost'] - w['lab'])) / w['hours']))} an hour."),
              Spacer(1, 6),
              P("Also on SETTINGS", "h2"),
              bullets(["<b>Overhead:</b> yearly costs (electricity and gas, equipment wear, licence, insurance, marketing) spread "
                       "per hour of work or per order.",
                       "<b>Delivery:</b> a rate per mile and a set-up fee for stacking on site.",
                       "<b>Supplies and decoration extras:</b> your cost for each board, box, dowel, sugar flower or topper.",
                       "<b>Units and pans:</b> US or metric display, and the pan table with batter, frosting, fondant and servings."]),
              PageBreak()]
    # 3 ingredients
    story += section("3 · Ingredients", "Adding ingredients")
    story += [P("On <b>INGREDIENTS</b>, type what you pay and the package size and unit. The cost per gram, ml and item "
                "follows. 48 common ingredients are already listed with their <b>grams per cup</b>, so a recipe can say "
                "\"2 cups flour\" even though you buy flour by the pound."),
              shot("ingredients", crop=(0, 0, 1, 0.62), max_h=260), Spacer(1, 6),
              table([["Example", "How it converts", "Cost"],
                     ["2 cups all-purpose flour", "2 × 120 g = 240 g of a $4.50, 5 lb bag (2,268 g)", money(2 * 120 * 4.5 / (5 * 453.592))],
                     ["1 tbsp butter", "1/16 cup × 227 g = 14.2 g of a $5, 1 lb block", money(14.7868 / 236.588 * 227 * 5 / 453.592)],
                     ["100 g of egg", "100 g ÷ 50 g per egg = 2 of a $4.20 dozen", money(100 / 50 * 4.2 / 12)],
                     ["1 metric cup heavy cream", "250 ml of a $5.50 pint (473 ml)", money(250 * 5.5 / 473.176)]], [0.3, 0.52, 0.18]),
              Spacer(1, 6),
              callout("If an ingredient has no grams per cup (sprinkles, food colouring, store-bought fondant) and a recipe "
                      "uses it in cups or spoons, the recipe shows a red message instead of a wrong number. Add the grams per "
                      "cup, or use the recipe in the unit you bought it in."),
              PageBreak()]
    # 4 recipe
    v = rec["Vanilla sponge"]
    story += section("4 · Recipes", "Building a recipe")
    story += [P("<b>RECIPES</b> has an index at the top and 40 blocks below. In a block, type the recipe's name and type, what "
                "one batch makes (its yield), then pick ingredients from the list with a quantity and unit."),
              shot("recipe_block", crop=(0, 0, 1, 1), max_h=270), Spacer(1, 6),
              bullets([f"The sample vanilla sponge costs <b>{money(v['total'])}</b> and makes 6 cups of batter: "
                       f"<b>{money(v['per_yield'])} per cup</b>.",
                       "<b>Yield matters.</b> Batters, fillings and frostings used on cakes need a volume yield (cups or ml); "
                       "fondant needs a weight (g, kg, oz); cupcake and cookie recipes can yield a number of items (24 each).",
                       "Use the <b>Go to</b> links in the index to jump to a block. A red check means a line needs a price or a conversion."]),
              PageBreak()]
    # 5 tiered cake
    rows = [["Tier", "Batter", "Filling", "Frosting", "Fondant", "Ingredients", "Servings"]]
    for k, (t, td) in enumerate(zip(w["tiers"], d["tiers"])):
        rows.append([f"{td[1]} {td[0].lower()}", f"{t['v'] / 236.588:.1f} cups", f"{t['w'] / 236.588:.2f} cups",
                     f"{t['x'] / 236.588:.2f} cups", f"{t['y'] / 28.3495:.0f} oz", money(t["cost"]), str(t["serv"])])
    story += section("5 · Tiered cakes", "Pricing a tiered cake")
    story += [P(f"The sample wedding cake for {d['customer']}: three round tiers (10\", 8\", 6\"), two 2-inch layers each, "
                "vanilla and chocolate sponge, raspberry filling and ganache, buttercream under fondant, detailed sugar "
                "flowers, delivered and set up 18 miles away."),
              table(rows, [0.16, 0.13, 0.13, 0.14, 0.12, 0.17, 0.15]), Spacer(1, 6),
              table([["Cost", ""],
                     ["Ingredients", money(w["ing"])], ["Decoration extras (8 sugar flowers, 2 gold leaf)", money(w["dec"])],
                     ["Supplies (drum, boards, dowels, box, ribbon)", money(w["sup"])],
                     [f"Labour: {w['hours']:.1f} hours (decorating × 2 for detailed) × {money(s['rate'])}", money(w["lab"])],
                     ["Overhead (per hour)", money(w["oh"])], ["Delivery (18 miles + set-up fee)", money(w["deliv"])],
                     ["<b>Total cost</b>", f"<b>{money(w['cost'])}</b>"]], [0.78, 0.22]),
              Spacer(1, 6),
              P(f"Price = {money(w['cost'])} ÷ (1 − {s['margin']:.0%}) = {money(w['cost'] / (1 - s['margin']))}, rounded up to the "
                f"next $5: <b>{money(w['price'])}</b>. That is <b>{money(w['per_serving'])} per serving</b> for {w['servings']} "
                f"wedding servings and <b>{money(w['hourly'])} an hour</b> for your time. Deposit {money(w['deposit'])}, balance "
                f"{money(w['balance'])}."),
              P("Amounts come from the pan table on SETTINGS: batter and filling per 2-inch layer, frosting and fondant to cover a "
                "4-inch tier. A tier with 3 layers uses 1.5 times the frosting and fondant and gives 1.5 times the servings.", "small"),
              PageBreak()]
    # 6 batches
    story += section("6 · Batches", "Pricing cupcakes by the dozen")
    story += [P("<b>BATCH PRICING</b> prices up to four products side by side. Pick the recipe and number of batches, the "
                "frosting and how much goes on each item, the decoration level, packaging per dozen and your hours."),
              shot("batch", crop=(0, 0, 0.82, 1), max_h=330), Spacer(1, 6),
              P(f"The sample: {cup['items']:.0f} vanilla cupcakes (2 batches) with 2.5 tbsp of buttercream each cost "
                f"{money(cup['cost'])}, or {money(cup['cost_item'])} each including {cup['hrs']:.1f} hours of your time. Priced "
                f"at <b>{money(cup['p_item'])} each, {money(cup['p_half'])} a half dozen and {money(cup['p_dozen'])} a dozen</b>."),
              PageBreak()]
    # 7 quote
    story += section("7 · Sending", "The customer quote")
    story += [P("<b>CUSTOMER QUOTE</b> shows the cake you choose (1, 2 or 3) with your bakery name and details, each tier, the "
                "design notes, extras, pickup or delivery, allergen notes, the total, deposit and balance, and your terms. It "
                "carries no Brass Ledger branding and fits one page on letter or A4."),
              shot("customer", width=CW * 0.52), Spacer(1, 6),
              bullets(["<b>Print or PDF:</b> File › Print, or Save as PDF.", "<b>Your logo:</b> Insert › Picture over the dashed box "
                       "(Review › Unprotect Sheet if Excel blocks it; no password)."]),
              PageBreak()]
    # 8 orders
    story += section("8 · Orders", "Taking deposits and tracking orders")
    story += [P("Add each enquiry to <b>ORDER TRACKER</b>: customer, event date, type, price, deposit paid and status (Enquiry, "
                "Quoted, Booked, Baking, Completed, Cancelled). The balance due fills in. Orders within 7 days turn brass; a "
                "balance still owed after the event turns red."),
              shot("orders", crop=(0, 0, 1, 1), max_h=210), Spacer(1, 6),
              P("Coming up, by date", "h2"),
              P("The list on the right sorts open orders by event date, so the next cake is always at the top. The DASHBOARD "
                "adds this month's orders and revenue, deposits not yet paid and orders due this week."),
              shot("orders_up", crop=(0, 0, 1, 1), max_h=180),
              PageBreak()]
    # 9 explaining + legal
    story += section("9 · Talking price", "Explaining your price to customers")
    story += [P(f"Customers compare a custom cake with a supermarket cake. Price per serving makes the comparison fair: the "
                f"sample birthday cake is {money(b['price'])} for {b['servings']} party servings, <b>{money(b['per_serving'])} a "
                f"slice</b>, made to order, decorated to their theme and delivered on the day."),
              bullets(["Quote the price per serving alongside the total; the quote does this for you.",
                       "If a customer pushes back, change the cake rather than your rate: fewer tiers, a simpler design, "
                       "buttercream instead of fondant, or cupcakes for part of the servings.",
                       "Keep your minimum per serving on SETTINGS. The builder turns red when a cake falls below it."]),
              Spacer(1, 6)]
    story += section("10 · Reminders", "Legal reminders (not advice)")
    story += [bullets(CFG.COMPLIANCE + ["Keep records of your ingredients and suppliers; some places require them for labels."]),
              PageBreak()]
    story += section("11 · Questions", "FAQ")
    faq = [("My price is higher than the supermarket.", "It should be. A supermarket cake is mass-produced; yours is designed, "
            "baked and decorated to order, with your hours in it. Show the price per serving, and offer a smaller or simpler "
            "cake if the budget is fixed, rather than cutting your rate."),
           ("How do I add a new pan size?", "On SETTINGS, scroll to the pan table and use an empty row: shape, size (as you "
            "want it in the dropdown, e.g. 7\"), batter per 2-inch layer, filling per layer, frosting and fondant to cover a "
            "4-inch tier, party and wedding servings. Add the size to the Sizes list under Dropdown lists. It appears in "
            "the builder straight away."),
           ("I use grams, not cups.", "Set the unit system to Metric on SETTINGS. Costs don't change; the builder shows "
            "batter and frosting in ml and fondant in g. Recipes can mix any units."),
           ("Australian cups are 250 ml.", "Use the unit \"metric cup\" (250 ml). \"cup\" is the US cup (236.6 ml)."),
           ("Can I price a cake I've already promised?", "Type it in, then put the agreed price in \"Your own price\": the "
            "builder shows the profit and hourly earnings at that price, and warns if it is too low.")]
    for qn, ans in faq:
        story += [P(f"<b>{qn}</b>"), P(ans), Spacer(1, 2)]
    story += [Spacer(1, 6), callout("<b>Disclaimer.</b> Prices are estimates based on the numbers you enter. Not financial, "
                                    "legal or tax advice. No specific earnings are promised.")]

    def on_page(cv, doc):
        cv.saveState()
        cv.setFillColor(c(PAPER))
        cv.rect(0, 0, PW, PH, stroke=0, fill=1)
        if doc.page > 1:
            x, y, em = SIDE, 11 * mm, 11
            cv.setFillColor(c(GREEN))
            cv.setFont("Head", em)
            cv.drawString(x, y, BR.NAME)
            wd = pdfmetrics.stringWidth(BR.NAME, "Head", em)
            cv.setFillColor(c(BRASS))
            cv.rect(x, y - 0.24 * em, wd, 0.075 * em, stroke=0, fill=1)
            cv.rect(x, y - 0.24 * em - 0.072 * em, wd, 0.022 * em, stroke=0, fill=1)
            cv.setFillColor(c(INK2))
            cv.setFont("Body", 7.5)
            cv.drawCentredString(PW / 2, 10.5 * mm, "Cake Pricing Calculator · Quick-start guide")
            cv.drawRightString(PW - SIDE, 10.5 * mm, f"Page {doc.page}")
            cv.setStrokeColor(c(BORDER))
            cv.line(SIDE, 16 * mm, PW - SIDE, 16 * mm)
        cv.restoreState()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER, leftMargin=SIDE, rightMargin=SIDE, topMargin=16 * mm, bottomMargin=21 * mm,
                            title="Cake Pricing Calculator — Quick-start guide", author="Brass Ledger")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
