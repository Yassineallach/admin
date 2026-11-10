"""Pinterest pins (1000 x 1500) for every listing + PINS.md with a title, description and board idea for each.

Usage: python pins.py      -> listings/pins/*.png and listings/pins/PINS.md
Every screenshot is a real render of the product (taken from each listing's screens/ folder).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from listing_kit import DARK, GREY, LAV, NAVY, ORANGE, TEAL, WHITE, card, font, framed, pill, text

ROOT = Path(__file__).resolve().parent.parent / "listings"
OUT = ROOT / "pins"
PW, PH = 1000, 1500
M = "05_Minis/"
# (file, product folder, screen, crop bottom, kicker, title, 3 points, pin title, description)
PINS = [
    ("project_manager", "01_Ultimate_Project_Manager", "AllinOne_Dashboard", 0.6, "EXCEL & GOOGLE SHEETS", "Project Management\nTemplate",
     ["Dashboard, Gantt & Kanban", "Tasks, calendars & budgets", "Updates automatically"],
     "Project Management Template for Excel & Google Sheets",
     "Run every project from one spreadsheet: auto-updating dashboard, Gantt chart, Kanban board, task tracker and calendars. 15 connected tabs, no macros. #projectmanagement #exceltemplate #googlesheets #ganttchart #smallbusiness"),
    ("weekly_planner", "03_Weekly_Planner_Pro", "week_top", 1.0, "EXCEL & GOOGLE SHEETS", "Weekly Planner\nSpreadsheet",
     ["Plan 6 weeks at a time", "Tasks, schedule & habits", "Monthly calendar fills itself"],
     "Weekly Planner Spreadsheet with Habit Tracker",
     "Plan your week, track habits, water and exercise, and see your month at a glance. Six reusable weekly planners for Excel and Google Sheets. #weeklyplanner #habittracker #googlesheets #productivity #digitalplanner"),
    ("budget_spreadsheet", "04_Ultimate_Budget_Spreadsheet", "dashboard", 0.62, "EXCEL & GOOGLE SHEETS", "Budget\nSpreadsheet",
     ["12 monthly budgets + dashboard", "Bills post themselves", "Debt, savings & net worth"],
     "Budget Spreadsheet for Excel & Google Sheets — 28 tabs",
     "A complete budget system: monthly budgets, bill calendar, debt snowball plan, sinking funds, net worth and more. Log once, everything updates. #budgetspreadsheet #budgeting #debtfree #googlesheets #personalfinance"),
    ("budget_debt", "04_Ultimate_Budget_Spreadsheet", "debt", 1.0, "DEBT SNOWBALL OR AVALANCHE", "Become Debt-Free\nFaster",
     ["Debt-free date for every debt", "Month-by-month payoff plan", "Part of a 28-tab budget"],
     "Debt Snowball Plan inside the Ultimate Budget Spreadsheet",
     "See your debt-free date and a month-by-month snowball or avalanche plan, built into a full budget spreadsheet for Excel and Google Sheets. #debtsnowball #debtfreejourney #budgeting #moneytips"),
    ("digital_planner", "02_Ultimate_OneNote_Planner", "index", 1.0, "HYPERLINKED PDF", "2027 Digital\nPlanner",
     ["Dated 2027 + undated edition", "111 work templates", "GoodNotes, Notability & more"],
     "2027 Digital Planner — Hyperlinked PDF with 111 Templates",
     "Yearly goals, 12 months, 53 weekly trackers, 111 professional templates and 8 note layouts, all linked from one index. Includes an undated edition. #digitalplanner #goodnotesplanner #2027planner #ipadplanner #notability"),
    ("bundle", "06_Ultimate_Productivity_Bundle", None, 1.0, "3-IN-1 BUNDLE", "Productivity\nSpreadsheet Bundle",
     ["Project Manager · 15 tabs", "Weekly Planner Pro · 8 tabs", "Budget Spreadsheet · 28 tabs"],
     "Productivity Spreadsheet Bundle — Projects, Planner & Budget",
     "Three complete Excel and Google Sheets templates at one bundle price: project manager, weekly planner and budget spreadsheet. #spreadsheettemplates #productivity #budgeting #projectmanagement #googlesheets"),
    ("debt_payoff", M + "Debt_Payoff_Calculator", "main", 1.0, "SNOWBALL OR AVALANCHE", "Debt Payoff\nCalculator",
     ["Your debt-free date", "Month-by-month plan", "Interest saved"],
     "Debt Payoff Calculator Spreadsheet (Snowball & Avalanche)",
     "List your debts, pick snowball or avalanche and see your debt-free date. Excel and Google Sheets. #debtpayoff #debtsnowball #debtfree #budgeting"),
    ("sinking_funds", M + "Sinking_Funds_Tracker", "main", 1.0, "SAVINGS GOALS", "Sinking Funds\nTracker",
     ["15 savings goals", "Progress & months to go", "Deposit & withdrawal log"],
     "Sinking Funds Tracker Spreadsheet",
     "Save for every goal with progress bars, months to go and an on-track check. Excel and Google Sheets. #sinkingfunds #savingsgoals #budgeting #savingmoney"),
    ("net_worth", M + "Net_Worth_Tracker", "main", 0.8, "KNOW YOUR NUMBER", "Net Worth\nTracker",
     ["Assets & liabilities", "24-month history", "Charts by type"],
     "Net Worth Tracker Spreadsheet",
     "Track what you own and what you owe, and watch your net worth grow month by month. Excel and Google Sheets. #networth #personalfinance #wealthbuilding"),
    ("no_spend", M + "No_Spend_Challenge_Tracker", "main", 0.75, "SAVE MORE", "No-Spend\nChallenge Tracker",
     ["Up to 60 days", "Streaks & success rate", "Money saved"],
     "No-Spend Challenge Tracker Spreadsheet",
     "Take a no-spend challenge and see your streaks and savings add up. Excel and Google Sheets. #nospendchallenge #savingschallenge #frugalliving #savingmoney"),
    ("investment", M + "Investment_Growth_Calculator", "main", 1.0, "COMPOUND GROWTH", "Investment Growth\nCalculator",
     ["Future value & growth", "3 return scenarios", "Inflation-adjusted"],
     "Investment Growth Calculator Spreadsheet",
     "See how regular investing could grow, with three return scenarios side by side. Hypothetical projections for planning. Excel and Google Sheets. #investing #compoundinterest #financialplanning"),
    ("habit_tracker", M + "Habit_Tracker", "main", 1.0, "12 MONTHS", "Habit Tracker\nSpreadsheet",
     ["Tick ✓ each day", "Success rates & goals", "Year overview"],
     "Habit Tracker Spreadsheet — 12 Months + Year Overview",
     "Track up to 12 habits every day and see your success rate by month and year. Excel and Google Sheets. #habittracker #goalsetting #productivity #newyeargoals"),
]


def bg():
    img = Image.new("RGB", (PW, PH), WHITE)
    d = ImageDraw.Draw(img)
    for y in range(PH):
        t = y / PH
        d.line([(0, y), (PW, y)], fill=tuple(int(a * (1 - t) + b * t) for a, b in zip((225, 243, 240), (255, 255, 255))))
    layer = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse((-250, -250, 450, 450), fill=(31, 169, 156, 40))
    ld.ellipse((650, 1100, 1250, 1700), fill=(155, 123, 224, 34))
    layer = layer.filter(ImageFilter.GaussianBlur(50))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def shot(prod, name, bottom, right=1.0):
    im = Image.open(ROOT / prod / "screens" / f"{name}.png").convert("RGB")
    w, h = im.size
    return im.crop((0, 0, int(w * right), int(h * bottom)))


RIGHT = {"debt": 0.6, "main@Debt_Payoff_Calculator": 0.6, "main@Sinking_Funds_Tracker": 0.62}     # very wide tabs: show the left part
POINTS_Y = PH - 110 - 40 - 3 * 96            # the three points always sit just above the footer


def make(spec):
    fname, prod, screen, bottom, kicker, title, points, *_ = spec
    img = bg()
    d = ImageDraw.Draw(img)
    text(img, (PW // 2, 70), kicker, 30, "SemiBold", TEAL, anchor="ma")
    f = font(84, "ExtraBold")
    d.multiline_text((PW // 2, 125), title, font=f, fill=NAVY, anchor="ma", align="center", spacing=4)
    top = d.multiline_textbbox((PW // 2, 125), title, font=f, anchor="ma", align="center", spacing=4)[3] + 45
    room = POINTS_Y - 45 - top                 # space for the screenshot between title and points
    if screen:
        right = RIGHT.get(screen, RIGHT.get(f"{screen}@{prod.split('/')[-1]}", 1.0))
        sh = shot(prod, screen, bottom, right)
        scale = min((PW - 136) / sh.width, (room - 16) / sh.height)
        w, h = int(sh.width * scale) + 16, int(sh.height * scale) + 16
        img, _ = framed(img, sh, (PW - w) // 2, top + (room - h) // 2, w, h, radius=20, border=8)
    else:                                      # bundle: three overlapping screenshots
        y0 = top + (room - 700) // 2
        img, _ = framed(img, shot("03_Weekly_Planner_Pro", "week_top", 0.7), 470, y0, 480, 380, radius=18, border=6)
        img, _ = framed(img, shot("01_Ultimate_Project_Manager", "AllinOne_Dashboard", 0.55), 50, y0 + 110, 620, 380, radius=18, border=6)
        img, _ = framed(img, shot("04_Ultimate_Budget_Spreadsheet", "dashboard", 0.6), 330, y0 + 330, 620, 380, radius=18, border=6)
    y = POINTS_Y
    for p in points:
        img = card(img, (110, y, PW - 110, y + 78), radius=39, shade=False, fill=WHITE)
        text(img, (160, y + 39), "✓", 36, "Bold", TEAL, anchor="lm")
        text(img, (215, y + 39), p, 34, "SemiBold", DARK, anchor="lm")
        y += 96
    d = ImageDraw.Draw(img)
    d.rectangle((0, PH - 110, PW, PH), fill=NAVY)
    text(img, (PW // 2, PH - 55), "Instant download on Etsy  ›", 36, "SemiBold", WHITE, anchor="mm")
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"pin_{fname}.png", "PNG", optimize=True)


def main():
    lines = ["# Pinterest pins", "",
             "One pin per listing, 1000 × 1500 px. For each pin: upload the image, paste the title and description, and set the "
             "link to that product's Etsy listing URL.", "",
             "Suggested boards: *Budget Spreadsheets & Money Trackers*, *Planner & Productivity Templates*, "
             "*Excel & Google Sheets Templates*. Pin one or two a day instead of all at once, and re-pin the best performers to a second board.", ""]
    for spec in PINS:
        make(spec)
        fname, prod, *_rest, ptitle, pdesc = spec
        assert len(ptitle) <= 100 and len(pdesc) <= 500, (fname, len(ptitle), len(pdesc))
        lines += [f"## pin_{fname}.png", "", f"- **Links to:** the Etsy listing for `{prod.split('/')[-1]}`", f"- **Title:** {ptitle}",
                  f"- **Description:** {pdesc}", ""]
        print("wrote", f"pin_{fname}.png")
    (OUT / "PINS.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
