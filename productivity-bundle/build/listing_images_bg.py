"""Etsy listing images for PRODUCT 4 — Ultimate Budget Spreadsheet (10 images, 2400x1800).

Screenshots are real renders of the DEMO workbook: the builder runs with one print area per tab (fitted to one
page), LibreOffice recalculates and prints it, and each page is identified by its title text.

Usage: python listing_images_bg.py [--reshoot]
Output: listings/04_Ultimate_Budget_Spreadsheet/images/01_hero.png ... 10_*.png
"""
from __future__ import annotations

import argparse
import glob
import io
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_budget as B  # noqa: E402
import icons  # noqa: E402
from common import solidify_databars  # noqa: E402
from listing_kit import (CORAL, DARK, GREY, LAV, MINT, NAVY, ORANGE, TEAL, W, WHITE, canvas, card,  # noqa: E402
                         footer, framed, heading, icon_bullet, laptop, pill, text)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "listings" / "04_Ultimate_Budget_Spreadsheet"
SCREENS, SHEETS_SCREENS, IMAGES = OUT / "screens", OUT / "screens_sheets", OUT / "images"
FOOT = "Instant download  ·  Excel + Google Sheets  ·  No macros"
RED, BLUE = (207, 58, 67), (47, 111, 170)

# (screen name, sheet, print area, title the page starts with)
SHOTS = [("dashboard", B.S_DASH, "A1:M63", "ALL-IN-ONE DASHBOARD"), ("month", "October", "A1:M57", "OCTOBER"),
         ("annual", B.S_AT, "A1:V41", "ANNUAL TOTALS"), ("calendar", B.S_CAL, "A1:K39", "AUTOMATED CALENDAR"),
         ("debt", B.S_DC, "A1:X24", "DEBT CALCULATOR"), ("funds", B.S_SF, "A1:N34", "SINKING FUNDS"),
         ("rule", B.S_503, "A1:K36", "50/30/20 DASHBOARD"), ("networth", B.S_NW, "A1:M43", "NET WORTH"),
         ("invest", B.S_IF, "A1:N41", "INVESTMENT FORECAST"), ("nospend", B.S_NS, "A1:R40", "NO-SPENDING CHALLENGE"),
         ("transactions", B.S_TR, "A1:K40", "VARIABLE TRANSACTIONS"), ("recurring", B.S_RT, "A1:M30", "RECURRING TRANSACTIONS"),
         ("setup", B.S_SET, "A1:K36", "EASY SETUP"), ("paycheck", B.S_PC, "A1:K30", "PAYCHECK DASHBOARD"),
         ("distribution", B.S_ED, "A1:N40", "EXPENSE DISTRIBUTION"), ("accounts", B.S_BA, "A1:J20", "BANK ACCOUNTS")]


def crop_tail(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    last = h - 1
    while last > 0 and all(min(px[x, last]) > 245 for x in range(int(w * 0.08), w, 7)):
        last -= 1
    im.crop((0, 0, w, min(h, last + 12))).save(path)


def shoot(edition, folder, only=None):
    folder.mkdir(parents=True, exist_ok=True)
    b = B.Builder(edition, True)
    wb = b.build()
    wanted = {s[1]: s for s in SHOTS if not only or s[0] in only}
    for n in B.ORDER:
        ws = b.ws[n]
        if n in wanted:
            ws.print_area = wanted[n][2]
            ws.page_setup.fitToHeight = 1
            ws.page_setup.fitToWidth = 1
        else:
            ws.print_area = "ZZ900:ZZ900"
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "s.xlsx"
    wb.save(p)
    solidify_databars(p)
    for name, lay in getattr(b, "side_layers", {}).items():
        lay.inject(p, name)
    rc = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
    subprocess.run([sys.executable, rc, str(p), "900"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(p)], capture_output=True)
    pdf = tmp / "s.pdf"
    n_pages = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    found = {}
    for i in range(1, n_pages + 1):
        t = " ".join(subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True, text=True).stdout.split())
        for name, _s, _a, mark in wanted.values():
            if name not in found and mark in t[:400]:
                found[name] = i
    missing = [s[0] for s in wanted.values() if s[0] not in found]
    if missing:
        raise SystemExit(f"pages not found for {missing}")
    for name, i in found.items():
        stem = tmp / name
        subprocess.run(["pdftoppm", "-f", str(i), "-l", str(i), "-r", "220", "-png", "-singlefile", str(pdf), str(stem)], capture_output=True)
        subprocess.run(["convert", f"{stem}.png", "-trim", "+repage", str(folder / f"{name}.png")])
        crop_tail(folder / f"{name}.png")
    shutil.rmtree(tmp, ignore_errors=True)


def shot(name, top=0.0, bottom=1.0, left=0.0, right=1.0, folder=None):
    im = Image.open((folder or SCREENS) / f"{name}.png").convert("RGB")
    w, h = im.size
    return im.crop((int(w * left), int(h * top), int(w * right), int(h * bottom)))


def ic(name, color="FFFFFF"):
    return icons.ICONS[name](c=color, size=96)


def save(img, name):
    IMAGES.mkdir(parents=True, exist_ok=True)
    img.save(IMAGES / name, "PNG", optimize=True)
    print("wrote", name)


def bullets(img, items, x=1640, y=400, w=680, circle=TEAL, gap=46, ts=40, bs=29):
    for icon, t_, b_ in items:
        y = icon_bullet(img, (x, y), ic(icon), t_, b_, w=w, circle=circle, title_size=ts, body_size=bs) + gap
    return y


def hero():
    img = canvas()
    text(img, (150, 170), "ULTIMATE", 64, "SemiBold", TEAL)
    text(img, (150, 250), "Budget\nSpreadsheet", 112, "ExtraBold", NAVY, spacing=0)
    text(img, (150, 590), "Excel & Google Sheets template", 50, "Medium", DARK)
    y = 710
    for t_ in ("Auto-updating dashboard & charts", "12 monthly budgets + annual totals", "Debt snowball & avalanche plan",
               "Sinking funds, net worth & more"):
        img = card(img, (150, y, 900, y + 92), radius=46, shade=False, fill=WHITE)
        text(img, (200, y + 46), "✓", 42, "Bold", TEAL, anchor="lm")
        text(img, (260, y + 46), t_, 38, "SemiBold", DARK, anchor="lm")
        y += 118
    pill(img, (150, 1230), "28 TABS", 40, NAVY)
    pill(img, (400, 1230), "NO MACROS", 40, TEAL)
    pill(img, (150, 1340), "DEMO + BLANK VERSIONS", 40, ORANGE)
    img, _ = laptop(img, shot("dashboard", 0, 0.6), 1640, 330, 1300)
    footer(img, FOOT)
    save(img, "01_hero.png")


def included():
    img = canvas()
    heading(img, "28 tabs in 4 sections", "Everything you need to run your money — all connected")
    secs = [("TRANSACTIONS", (20, 149, 139), ["Easy Setup", "Bank Accounts", "Recurring Transactions", "Payments",
                                              "Variable Transactions"]),
            ("DASHBOARDS", (11, 79, 76), ["All-in-One Dashboard", "Annual Totals", "Automated Calendar", "Paycheck Dashboard"]),
            ("MONTHLY INSIGHTS", BLUE, ["January … December", "12 monthly budgets", "Income · fixed · variable", "Savings · debt payments",
                                        "Transactions this month"]),
            ("BUILD YOUR WEALTH", LAV, ["50/30/20 Dashboard", "Expense Distribution", "Sinking Funds", "Debt Calculator", "Net Worth",
                                        "Investment Forecast", "No-Spending Challenge"])]
    x = 130
    for title, color, items in secs:
        img = card(img, (x, 360, x + 500, 1290), radius=36)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((x, 360, x + 500, 450), 36, fill=color)
        d.rectangle((x, 410, x + 500, 450), fill=color)
        text(img, (x + 250, 405), title, 34, "Bold", WHITE, anchor="mm")
        y = 490
        for it in items:
            text(img, (x + 40, y), "•", 34, "Bold", color)
            text(img, (x + 75, y), it, 32, "Medium", DARK, max_w=400)
            y += 100 if len(it) > 22 else 78
        x += 545
    img = card(img, (130, 1360, W - 130, 1640), radius=40)
    text(img, (190, 1405), "YOU RECEIVE", 30, "Bold", TEAL)
    x = 190
    for f_ in ("Excel – DEMO", "Excel – BLANK", "Google Sheets – DEMO", "Google Sheets – BLANK", "PDF user guide"):
        x = pill(img, (x, 1470), f_, 32, MINT, NAVY) + 26
    footer(img, FOOT)
    save(img, "02_whats_included.png")


def dashboard():
    img = canvas()
    heading(img, "See your whole financial picture", "8 KPIs and 6 live charts — pick the full year or any month")
    img, _ = framed(img, shot("dashboard"), 110, 360, 1450, 1330)
    bullets(img, [("bar_chart", "8 KPI cards", "Income, expenses, net cash flow, savings, savings rate, budget, remaining, debt"),
                  ("pie", "6 charts", "Income vs expenses, distribution, cash flow, savings, budget vs actual, categories"),
                  ("calendar", "Period selector", "Full year or any single month"),
                  ("receipt", "Upcoming bills & balances", "Overdue payments flagged in red")], gap=40)
    footer(img, FOOT)
    save(img, "03_dashboard.png")


def months():
    img = canvas()
    heading(img, "12 monthly budgets that fill themselves", "Budget vs actual for every category — start in any month")
    img, _ = framed(img, shot("month"), 110, 360, 1450, 1330)
    bullets(img, [("money", "Income, fixed & variable", "Budget, actual and remaining per category"),
                  ("piggy", "Savings & debt payments", "Planned vs actual, automatically"),
                  ("bar_chart", "Monthly summary", "Net cash flow, savings rate and a spending chart"),
                  ("table", "Transactions this month", "Pulled in from your log"),
                  ("calendar", "Any start month", "Budget years can begin in any month")], gap=36)
    footer(img, FOOT)
    save(img, "04_monthly_budgets.png")


def automation():
    img = canvas()
    heading(img, "Log once — everything updates", "Recurring items post themselves; categories decide income vs expense")
    img, _ = framed(img, shot("recurring", 0, 0.75), 110, 360, 1300, 700)
    img, _ = framed(img, shot("transactions", 0, 0.75), 900, 980, 1390, 680)
    bullets(img, [("repeat", "Recurring transactions", "Weekly to annual; each occurrence counts automatically"),
                  ("receipt", "Payments", "One-off bills with due dates and status")], x=1480, y=420, w=820, gap=40)
    bullets(img, [("table", "1,000-row log", "Dropdowns for category, account and method"),
                  ("bank", "Account transfers", "Move money between accounts without double counting")], x=150, y=1120, w=700, gap=40)
    footer(img, FOOT)
    save(img, "05_automation.png")


def calendar_pay():
    img = canvas()
    heading(img, "Know what's coming", "Automated calendar and a paycheck planner")
    img, _ = framed(img, shot("calendar"), 110, 350, 1400, 1150)
    img, _ = framed(img, shot("paycheck", 0, 0.62), 1180, 860, 1110, 780)
    bullets(img, [("calendar", "Automated calendar", "Income ↑, bills ↓, savings and payment deadlines by day"),
                  ("wallet", "Paycheck dashboard", "Net pay, bills before the next paycheck, what's left")],
            x=1560, y=380, w=760, gap=36, ts=38, bs=28)
    footer(img, FOOT)
    save(img, "06_calendar_paycheck.png")


def debt():
    img = canvas()
    heading(img, "Become debt-free faster", "Snowball or avalanche — with a month-by-month payoff plan")
    img, _ = framed(img, shot("debt"), 110, 360, W - 220, 900)
    items = [("card", "All your debts", "Balance, APR, minimum and extra payment"),
             ("scale", "Snowball or avalanche", "Switch methods and compare"),
             ("calendar", "Debt-free date", "For each debt and overall"),
             ("money", "Interest saved", "vs paying each debt separately")]
    x = 130
    for icon, t_, b_ in items:
        icon_bullet(img, (x, 1340), ic(icon), t_, b_, w=520, circle=RED, title_size=36, body_size=27)
        x += 545
    footer(img, FOOT)
    save(img, "07_debt_calculator.png")


def savings():
    img = canvas()
    heading(img, "Save with a plan", "Sinking funds for every goal and the 50/30/20 rule")
    img, _ = framed(img, shot("funds", 0, 0.62), 110, 360, 1250, 760)
    img, _ = framed(img, shot("rule", 0, 0.95), 1260, 760, 1030, 900)
    bullets(img, [("piggy", "Sinking funds", "Target, progress, months to go and on-track status")], x=1430, y=420, w=860)
    bullets(img, [("pie", "50/30/20 dashboard", "Needs, wants and savings vs the rule — any month or the year")],
            x=150, y=1220, w=1000)
    footer(img, FOOT)
    save(img, "08_savings.png")


def wealth():
    img = canvas()
    heading(img, "Build your wealth", "Net worth, investment forecast and a no-spend challenge")
    img, b1 = framed(img, shot("networth"), 110, 420, 1120, 1180)
    img, b2 = framed(img, shot("invest", 0, 0.75), 1280, 420, 1010, 560)
    img, b3 = framed(img, shot("nospend", 0, 0.62), 1280, b2[3] + 80, 1010, 560)
    pill(img, (b1[0] + 10, 345), "Net worth", 32, (11, 79, 76))
    pill(img, (b2[0] + 10, 345), "Investment forecast", 32, LAV)
    pill(img, (b3[0] + 10, b2[3] + 8), "No-spend challenge", 32, TEAL)
    img2 = img
    text(img2, (W // 2, 1640), "Projections are hypothetical — clearly labelled in the file", 30, "Medium", GREY, anchor="ma")
    footer(img2, FOOT)
    save(img2, "09_wealth.png")


def editions():
    img = canvas()
    heading(img, "Excel & Google Sheets editions", "Both included — pick the app you already use")
    img, _ = framed(img, shot("dashboard", 0, 0.5), 110, 330, 1480, 1000)
    img, _ = framed(img, shot("dashboard", 0, 0.5, folder=SHEETS_SCREENS), 1000, 800, 1290, 860)
    pill(img, (1640, 380), "Excel edition", 38, NAVY)
    text(img, (1640, 470), "Clickable icon sidebar,\nprotected formulas", 34, "Medium", GREY, spacing=8)
    pill(img, (140, 1230), "Google Sheets edition", 38, TEAL)
    text(img, (140, 1320), "Same formulas, charts\nand dashboards", 34, "Medium", GREY, spacing=8)
    footer(img, FOOT)
    save(img, "10_excel_and_sheets.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reshoot", action="store_true")
    a = ap.parse_args()
    if a.reshoot or not (SCREENS / "dashboard.png").exists():
        shoot("excel", SCREENS)
    if a.reshoot or not (SHEETS_SCREENS / "dashboard.png").exists():
        shoot("gsheets", SHEETS_SCREENS, only={"dashboard"})
    for f in (hero, included, dashboard, months, automation, calendar_pay, debt, savings, wealth, editions):
        f()


if __name__ == "__main__":
    main()
