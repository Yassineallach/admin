"""Quick-start guide PDF for the Owner-Operator Cost Per Mile & Load Profit Calculator (letter size).

Screenshots come from shoot.py (real renders of the SAMPLE workbook). Every number in the worked examples comes from
the test model (test_workbook.py), which the tests check against the workbook.
Usage: python guide.py
"""
from __future__ import annotations

from guide_helpers import (BRASS, BRASS_TINT, BR, CW, Drawing, GREEN, INK, INK2, Image, KeepTogether, LETTER, OUT, P,
                           PAPER, PH, PW, PageBreak, Paragraph, ParagraphStyle, POS_TINT, Rect, Rule, SIDE, SimpleDocTemplate,
                           Spacer, String, bullets, c, callout, logo_rgba, mm, pdfmetrics, section, shot, spaced, table, tempfile,
                           Path, CFG, load_model, settings_model)

NEG, POS, AMBER = "B3261E", "2E7D4F", "C77A1A"


def money(x, d=2):
    return ("-" if x < 0 else "") + f"${abs(x):,.{d}f}"


def cpm(x):
    return f"${x:.3f}"


def deadhead_diagram(o, rate, loaded, dh):
    """Two bars: loaded and deadhead miles, with the rate per loaded mile against the rate per total mile."""
    w, h = CW, 150
    d = Drawing(w, h)
    x0, bw = 10, w - 20
    scale = bw / (loaded + dh)
    lw = loaded * scale
    d.add(Rect(x0, 82, lw, 26, fillColor=c(GREEN), strokeColor=None))
    d.add(Rect(x0 + lw, 82, dh * scale, 26, fillColor=c(BRASS), strokeColor=None))
    d.add(String(x0 + 8, 91, f"Loaded: {loaded:,} miles (paid)", fontName="Body-Bold", fontSize=9.5, fillColor=c(PAPER)))
    d.add(String(x0 + lw + 8, 91, f"Deadhead: {dh:,} miles (unpaid)", fontName="Body-Bold", fontSize=9.5, fillColor=c(GREEN)))
    d.add(String(x0, 122, f"The load pays {money(rate, 0)}. Your truck drives {loaded + dh:,} miles to earn it.",
                 fontName="Body-Bold", fontSize=10.5, fillColor=c(INK)))
    d.add(String(x0, 56, f"Per loaded mile: {money(rate, 0)} / {loaded:,} = {cpm(o['rpl'])}   (what the load board shows)",
                 fontName="Body", fontSize=9.5, fillColor=c(INK)))
    d.add(String(x0, 38, f"Per total mile: {money(rate, 0)} / {loaded + dh:,} = {cpm(o['rpt'])}   (what your truck actually earns)",
                 fontName="Body-Bold", fontSize=9.5, fillColor=c(NEG)))
    d.add(String(x0, 16, f"Your all-in cost on this load: {cpm(o['cpm'])} a mile. The truck runs every deadhead mile at full cost.",
                 fontName="Body", fontSize=9.5, fillColor=c(INK2)))
    return d


def build():
    m = settings_model()
    lc = CFG.LOAD_CHECK
    o = load_model(m, **lc)
    D = CFG.SET
    logo_path = Path(tempfile.mkdtemp()) / "logo.png"
    logo_rgba(1400).save(logo_path)
    from PIL import Image as PI
    lim = PI.open(logo_path)
    story = []
    lw = 70 * mm
    story += [Spacer(1, 12 * mm), Image(str(logo_path), width=lw, height=lw * lim.height / lim.width, hAlign="LEFT"),
              Spacer(1, 14 * mm), P(spaced("Quick-start guide"), "kicker"),
              Paragraph("Owner-Operator Cost Per Mile &amp; Load Profit Calculator",
                        ParagraphStyle("t", fontName="Head", fontSize=29, leading=34, textColor=c(GREEN))),
              Spacer(1, 6), Rule(110, 34), Spacer(1, 12),
              Paragraph(CFG.PROMISE, ParagraphStyle("st", fontName="Body", fontSize=14, leading=19, textColor=c(INK))),
              Spacer(1, 4),
              P("For owner-operators and hotshot drivers: dry van, reefer, flatbed, hotshot and box truck. "
                "Excel, Google Sheets and the Google Sheets phone app.", "small"),
              Spacer(1, 8 * mm), shot("settings_top", max_h=300), Spacer(1, 5 * mm),
              P(CFG.DISCLAIMER, "small"), PageBreak()]

    # 1 included
    story += section("1 · What's included", "What's in your download")
    story += [table([["File", "Use it for"],
                     [f"{CFG.OUT_NAME}.xlsx", "Your own numbers. Presets and labelled example settings are filled in; logs are empty."],
                     [f"{CFG.OUT_NAME}_SAMPLE.xlsx", "A fictional dry van owner-operator with 46 loads, 19 fill-ups and three months of P&amp;L."],
                     [CFG.GUIDE_NAME, "This guide."]], [0.52, 0.48]),
              Spacer(1, 8),
              table([["Tab", "What it does"],
                     ["START HERE", "Three-step quick start, phone instructions, colour key."],
                     ["SETTINGS", "Equipment preset, fuel, fixed costs, your pay and miles, margin, fees, verdict words. Your cost per mile at the top."],
                     ["LOAD CHECK (PHONE)", "One narrow column for the Google Sheets app: TAKE, NEGOTIATE or PASS, profit per day, counter-offer."],
                     ["LOAD COMPARE", "Up to five offers side by side; the best profit per day is marked."],
                     ["TRIP LOG", "500 rows: one per load, with revenue per mile, fees, trip profit and profit per day."],
                     ["FUEL LOG", "Fill-ups with MPG, miles by state per trip and totals by state: records to help with IFTA reporting."],
                     ["MONTHLY P&amp;L", "Twelve months of revenue, costs, net profit, deadhead and actual cost per mile; days away from home."],
                     ["DASHBOARD", "Break-even and all-in cost per mile, revenue per mile, deadhead, profit, unpaid invoices, 3 charts."]],
                    [0.27, 0.73], bold_first=True),
              Spacer(1, 10)]
    story += section("2 · Opening the file", "Excel, Google Sheets and your phone")
    story += [P("<b>Excel (Windows or Mac, 2016 or newer).</b> Open the blank file and save a copy under your own name. "
                "Type only in the white cells; shaded cells are formulas and are locked (no password, so you can unprotect a "
                "tab under Review if you want to change something)."),
              P("<b>Google Sheets.</b> Open this link and choose <b>File &gt; Make a copy</b>: <b>[GOOGLE SHEETS COPY LINK]</b>. "
                "Or upload the .xlsx to Google Drive, open it, and choose <b>File &gt; Save as Google Sheets</b>."),
              P("<b>On your phone.</b> Install the Google Sheets app (Android or iPhone) and sign in with the same Google account. "
                "Your copy shows up in the app. Open it and tap the <b>LOAD CHECK (PHONE)</b> tab at the bottom of the screen. "
                "Star the file so it stays at the top of the list."),
              callout("Set up SETTINGS on a laptop or tablet once. After that, the phone tab is all you need at the truck stop."),
              PageBreak()]

    # 3 CPM + deadhead
    story += section("3 · The idea", "What cost per mile is, and why deadhead matters")
    story += [P("Your <b>cost per mile</b> is everything it costs to run the truck for a month, divided by the miles you run. "
                "It has three layers:"),
              bullets([f"<b>Variable costs</b> rise with every mile: fuel, DEF, maintenance and tires. Example: {cpm(m['var'])} a mile.",
                       f"<b>Fixed costs</b> don't stop when the truck sits: truck and trailer payments, insurance, plates, permits, "
                       f"ELD, load boards. Example: {money(m['fixed_month'])} a month, {cpm(m['fixed_cpm'])} a mile at "
                       f"{m['month_miles']:,.0f} miles a month.",
                       f"<b>Your pay.</b> Example: {money(D['weekly_pay'], 0)} a week is {cpm(m['paypm'])} a mile."]),
              P(f"Variable + fixed = <b>operating cost, {cpm(m['op'])} a mile</b>: the break-even line before you pay yourself. "
                f"Add your pay and you get the <b>all-in cost, {cpm(m['allin'])} a mile</b>. Add your target margin and fees and "
                f"you get the <b>target rate, {cpm(m['target'])} a mile</b>."),
              Spacer(1, 4), P("Deadhead", "h2"),
              P("Load boards quote the rate per <i>loaded</i> mile. Your truck burns fuel and wears tires on every mile, loaded or "
                "not. Here is the sample load from the phone tab:"),
              deadhead_diagram(o, lc["rate"], lc["loaded"], lc["dh"]),
              callout(f"{cpm(o['rpl'])} a loaded mile looks better than the {cpm(m['target'])} target. Counted over all "
                      f"{o['tot']:,} miles it pays {cpm(o['rpt'])}, which is below the break-even line. That's why the verdict is PASS."),
              Spacer(1, 4), P("Why idle weeks hurt", "h2"),
              table([["Miles a month", "Fixed $/mile", "All-in $/mile", "Target rate $/mile"]] +
                    [[f"{mi:,}", cpm(fx), cpm(al), cpm(tg)] for mi, (fx, al, tg) in zip(D["sens"], m["sens"])],
                    [0.25, 0.25, 0.25, 0.25]),
              P("Same truck, same costs. Fewer miles means each mile carries more of the payment and insurance.", "small"),
              PageBreak()]

    # 4 settings
    story += section("4 · Set up once", "Setting up your costs")
    story += [bullets([
        "<b>Equipment type.</b> Pick dry van, reefer, flatbed, hotshot (CDL or non-CDL) or box truck. The preset fills MPG, "
        "maintenance, tires, DEF and reefer fuel. Type your own value in <i>Your value</i> to override any of them.",
        "<b>Diesel $/gal.</b> What you usually pay. The load check can use a different price per route.",
        "<b>Fixed costs.</b> Type each amount and choose <i>Month</i> or <i>Year</i>; yearly items are divided by 12. Two spare rows "
        "are at the bottom for anything else.",
        "<b>Your pay and miles.</b> The take-home pay you want each week, the miles you run in a normal week (loaded + deadhead) "
        "and the weeks you work a year.",
        "<b>Targets.</b> Profit margin, factoring and dispatch fees, the three verdict words, and whether the break-even line "
        "includes your pay."], numbered=True),
              P("Worked example: the example values (dry van, own authority)", "h2"),
              table([["Line", "Example", "Per mile"],
                     ["Diesel / MPG", f"{money(D['fuel_price'])} / {m['mpg']}", cpm(m["parts"]["fuel"])],
                     ["Maintenance and repair reserve", "preset", cpm(m["parts"]["maint"])],
                     ["Tires", "$6,000 set / 120,000 miles", cpm(m["parts"]["tire"])],
                     ["DEF", "preset", cpm(m["parts"]["defc"])],
                     ["<b>Variable cost</b>", "", f"<b>{cpm(m['var'])}</b>"],
                     ["Fixed costs", f"{money(m['fixed_month'])} a month / {m['month_miles']:,.0f} miles", cpm(m["fixed_cpm"])],
                     ["<b>Operating cost (break-even)</b>", "", f"<b>{cpm(m['op'])}</b>"],
                     ["Your pay", f"{money(D['weekly_pay'], 0)} x 52 / ({D['weekly_miles']:,} x {D['weeks_year']})", cpm(m["paypm"])],
                     ["<b>All-in cost</b>", "", f"<b>{cpm(m['allin'])}</b>"],
                     ["Target rate", f"all-in / (1 - {D['margin']:.0%} margin - {D['factoring']:.0%} factoring)", f"<b>{cpm(m['target'])}</b>"]],
                    [0.42, 0.38, 0.2]),
              Spacer(1, 6),
              callout("These are example values, not your costs. Replace every white cell with your own numbers: your truck "
                      "note, your insurance bill, your fuel receipts."),
              PageBreak()]

    # 5 phone
    story += section("5 · On the road", "Checking a load on your phone")
    left = [P("Type four numbers:"),
            bullets(["Total rate offered", "Loaded miles", "Deadhead miles to pickup", "Days the load will take"], numbered=True),
            P("The verdict appears straight away:"),
            bullets(["<font color='#2E7D4F'><b>TAKE</b></font>: meets your target margin.",
                     "<font color='#C77A1A'><b>NEGOTIATE</b></font>: covers break-even, not your target. Counter with the "
                     "<i>Rate needed for your target</i>.",
                     "<font color='#B3261E'><b>PASS</b></font>: below break-even. Hauling it costs you money."]),
            P("Below the verdict: rate per loaded mile, all-in rate per total mile, profit after your pay, profit per day, the "
              "counter-offer and the break-even rate. <i>More details</i> takes tolls, lumpers, detention, extra stop pay, a "
              "route fuel price, reefer hours and a different factoring or dispatch fee for this load."),
            P("Worked example", "h2"),
            P(f"{money(lc['rate'], 0)} for {lc['loaded']} loaded miles, {lc['dh']} deadhead, {lc['days']} days."),
            table([["Output", "Value"], ["Rate per loaded mile", cpm(o["rpl"])], ["All-in rate per total mile", cpm(o["rpt"])],
                   ["Total cost of the load", money(o["allin"])], ["Profit after your pay", money(o["profit"])],
                   ["Profit per day", money(o["ppd"])], ["Rate needed for your target", money(o["counter"], 0)],
                   ["Break-even rate", money(o["be_rate"], 0)], ["Verdict", f"<b>{o['verdict']}</b>"]], [0.4, 0.21])]
    from reportlab.platypus import Table, TableStyle
    t = Table([[left, shot("check_top", width=58 * mm)]], colWidths=[CW - 64 * mm, 64 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [t, Spacer(1, 6),
              callout(f"To make this load work you would need about {money(o['counter'], 0)}, or a pickup much closer than "
                      f"{lc['dh']} miles. Counter, or let it go."),
              PageBreak()]

    # 6 compare + 7 logs
    story += section("6 · Choosing", "Comparing loads")
    story += [P("LOAD COMPARE puts up to five offers side by side with the same costs. Use it when you have a few options for "
                "the same day. The best <b>profit per day</b> is marked: it is the fairest way to compare a short load with a long one."),
              shot("compare_out", max_h=170), Spacer(1, 6)]
    story += section("7 · Records", "Logging trips and fuel")
    story += [bullets(["<b>TRIP LOG</b>: one row per load. Dates, broker, origin, destination, loaded and deadhead miles, "
                       "linehaul, fuel surcharge, detention, other revenue, fuel, tolls, other costs, factored (Y/N), paid (Y/N), "
                       "payment date. Fees, revenue per mile, trip profit and profit per day calculate. Unpaid loads turn red.",
                       "<b>FUEL LOG</b>: date, city, state, gallons, price, odometer, DEF. MPG between fill-ups and your average "
                       "MPG calculate. Fill up to full each time for an accurate MPG.",
                       "<b>Miles by state per trip</b> (on FUEL LOG) and the totals by state for a quarter are records to help "
                       "with IFTA reporting. The workbook does not calculate IFTA tax."]),
              shot("trips_left", max_h=150), PageBreak()]

    # 8 P&L
    story += section("8 · Every month", "Reading the monthly P&amp;L")
    story += [P("MONTHLY P&amp;L adds up the trip log by month: revenue, fuel, other variable costs (tolls, other trip costs and "
                "the per-mile reserve for maintenance, tires and DEF), fixed costs, fees, profit before your pay, the pay you "
                "drew, and net profit."),
              P("<b>Actual cost per mile</b> is fuel + other variable + fixed costs, divided by the miles you ran. It is compared "
                "with the operating cost per mile on SETTINGS. When the month runs more than 10 % above your estimate, the Check "
                "column turns red: usually fewer miles than planned, higher fuel, or a repair."),
              shot("pnl", max_h=170), Spacer(1, 6),
              P("In the sample, November has fewer miles (the month isn't over), so the fixed costs are spread thinner and the "
                "actual cost per mile is flagged 14 % above the estimate.", "small"),
              P("<b>Days away from home</b> (bottom of the P&amp;L): one row per stretch on the road. The days are split by month. "
                "Records for your tax preparer, e.g. per diem; not tax advice."),
              shot("dash_top", max_h=200), PageBreak()]

    # 9 presets
    story += section("9 · Other equipment", "Hotshot and box truck presets")
    story += [table([["Preset", "MPG", "Maint. $/mi", "Tire set", "Tire life", "DEF $/mi", "Reefer gal/h"]] +
                    [[p[0], f"{p[1]:.1f}", f"${p[2]:.3f}", money(p[3], 0), f"{p[4]:,}", f"${p[5]:.3f}", f"{p[6]:.2f}"] for p in CFG.PRESETS],
                    [0.22, 0.09, 0.13, 0.13, 0.15, 0.12, 0.16], bold_first=True),
              Spacer(1, 8),
              P("<b>Switching to hotshot</b>", "h2"),
              bullets(["On SETTINGS, set <b>Equipment type</b> to <i>Hotshot (CDL)</i> or <i>Hotshot (non-CDL)</i>. MPG, "
                       "maintenance, tires and DEF change straight away.",
                       "Change the fixed costs to match: a pickup payment instead of a tractor, a gooseneck trailer payment, "
                       "hotshot insurance. Under 75,000 lb the heavy vehicle use tax is lower or not due; check yours.",
                       "Set your weekly miles and pay. Hotshot loads are smaller, so the miles per week often differ.",
                       "If your truck gets better or worse mileage than the preset, type it in <i>Your value</i>."], numbered=True),
              P("Box truck works the same way: pick <i>Box truck</i>, then replace the fixed costs with your own.")]
    hm = settings_model("Hotshot (CDL)")
    story += [callout(f"With the hotshot preset and the same example fixed costs, variable cost drops to {cpm(hm['var'])} a mile "
                      f"and all-in to {cpm(hm['allin'])}. Your real fixed costs will be different again: enter them."),
              PageBreak()]

    # 10 FAQ + sources
    story += section("10 · Questions", "FAQ")
    faq = [("My cost per mile looks higher than what people post online.",
            "Most online numbers leave out your own pay, the truck payment, or the deadhead miles, or they divide by a month "
            "with more miles than you run. Diesel prices also move a lot. This workbook counts all of it and divides by your "
            "miles. Use your own numbers, not someone else's."),
           ("Should I count my own pay?",
            "Yes. If you don't, a load can look profitable while you work for nothing. The break-even line can be set to "
            "operating costs (the truck covers itself) or all-in (the truck and you). The TAKE verdict always includes your pay."),
           ("I'm leased on to a carrier.",
            "Set the trailer and the insurance you don't pay to 0, add the carrier's deductions to fixed costs, and use the "
            "dispatch fee % for the carrier's percentage if you are paid on a split."),
           ("Does it file my IFTA?", "No. FUEL LOG keeps records to help with IFTA reporting: gallons and miles by state. "
            "Your IFTA return uses your base state's rates and rules."),
           ("Do I need internet on the road?", "The Google Sheets app works offline if you turn on offline access for the file "
            "in the app. Changes sync when you are back online.")]
    for qn, ans in faq:
        story += [P(f"<b>{qn}</b>"), P(ans), Spacer(1, 1)]
    story += [P("Where the example numbers come from", "h2"),
              P("ATRI, <i>An Analysis of the Operational Costs of Trucking</i> (2026 update, 2025 data: $2.336 a mile average; "
                "repair and maintenance 21.5 cents, tires 5 cents, insurance 10.6 cents, truck and trailer payments 40.4 cents). "
                "US EIA weekly on-highway diesel price ($5.937, week ending Nov 16, 2026). Overdrive, FreightWaves and insurance "
                "broker surveys for owner-operator insurance ($9,000 to $22,000 a year with own authority). FMCSA (UCR $46 for 2026) "
                "and IRS Form 2290 ($550). FreightWaves and EPRI for reefer fuel use (about 0.75 gallons an hour). Hotshot and box "
                "truck figures are typical published ranges and are less certain: check them against your own records.", "small"),
              Spacer(1, 4),
              callout(f"<b>Disclaimer.</b> {CFG.DISCLAIMER} No specific earnings are promised.")]

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
            cv.drawCentredString(PW / 2, 10.5 * mm, "Owner-Operator Cost Per Mile · Quick-start guide")
            cv.drawRightString(PW - SIDE, 10.5 * mm, f"Page {doc.page}")
        cv.restoreState()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=LETTER, leftMargin=SIDE, rightMargin=SIDE, topMargin=16 * mm, bottomMargin=21 * mm,
                            title="Owner-Operator Cost Per Mile & Load Profit Calculator: Quick-start guide", author="Brass Ledger")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
