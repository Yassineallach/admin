"""Pinterest pins (1000 x 1500) for every listing + PINS.md with a title, description and board idea for each.

Usage: python pins.py      -> listings/pins/*.png and listings/pins/PINS.md
Every screenshot is a real render of the product (taken from each listing's screens/ folder).
"""
from pathlib import Path

from PIL import Image, ImageDraw

import brand as BR
import brand_listing as BL

ROOT = Path(__file__).resolve().parent.parent / "listings"
OUT = ROOT / "pins"
PW, PH = 1000, 1500
M = "05_Minis/"
# (file, product folder, screen, crop bottom, kicker, title, 3 points, pin title, description)
PINS = [
    ("project_manager", "01_Ultimate_Project_Manager", "AllinOne_Dashboard", 0.6, "PROJECT MANAGER · EXCEL AND GOOGLE SHEETS", "See every project, task and deadline in one place.",
     ["Dashboard, Gantt chart and Kanban board", "Tasks, calendars and budgets", "Updates automatically"],
     "Project Management Template for Excel & Google Sheets",
     "Run every project from one spreadsheet: auto-updating dashboard, Gantt chart, Kanban board, task tracker and calendars. 15 connected tabs, no macros. #projectmanagement #exceltemplate #googlesheets #ganttchart #smallbusiness"),
    ("weekly_planner", "03_Weekly_Planner_Pro", "week_top", 1.0, "WEEKLY PLANNER · EXCEL AND GOOGLE SHEETS", "Plan the week and see what got done.",
     ["Plan 6 weeks at a time", "Tasks, schedule and habits", "Monthly calendar fills itself"],
     "Weekly Planner Spreadsheet with Habit Tracker",
     "Plan your week, track habits, water and exercise, and see your month at a glance. Six reusable weekly planners for Excel and Google Sheets. #weeklyplanner #habittracker #googlesheets #productivity #digitalplanner"),
    ("budget_spreadsheet", "04_Ultimate_Budget_Spreadsheet", "dashboard", 0.62, "BUDGET SPREADSHEET · EXCEL AND GOOGLE SHEETS", "Know where your money went, and what is left.",
     ["12 monthly budgets and a dashboard", "Bills post themselves", "Debt, savings and net worth"],
     "Budget Spreadsheet for Excel & Google Sheets — 28 tabs",
     "monthly budgets, bill calendar, debt snowball plan, sinking funds, net worth and more. Log once, everything updates. #budgetspreadsheet #budgeting #debtfree #googlesheets #personalfinance"),
    ("budget_debt", "04_Ultimate_Budget_Spreadsheet", "debt", 1.0, "BUDGET SPREADSHEET · DEBT PLAN", "Know the date you will be debt-free.",
     ["Debt-free date for every debt", "Month-by-month payoff plan", "Part of a 28-tab budget"],
     "Debt Snowball Plan inside the Ultimate Budget Spreadsheet",
     "See your debt-free date and a month-by-month snowball or avalanche plan, built into a full budget spreadsheet for Excel and Google Sheets. #debtsnowball #debtfreejourney #budgeting #moneytips"),
    ("digital_planner", "02_Ultimate_OneNote_Planner", "index", 1.0, "DIGITAL PLANNER · HYPERLINKED PDF", "Your year, your weeks and your work notes in one file.",
     ["Dated 2027 and undated editions", "111 work templates", "GoodNotes, Notability and other PDF apps"],
     "2027 Digital Planner — Hyperlinked PDF with 111 Templates",
     "Yearly goals, 12 months, 53 weekly trackers, 111 work templates and 8 note layouts, all linked from one index. Includes an undated edition. #digitalplanner #goodnotesplanner #2027planner #ipadplanner #notability"),
    ("bundle", "06_Ultimate_Productivity_Bundle", None, 1.0, "THREE TEMPLATES · EXCEL AND GOOGLE SHEETS", "Run your projects, your week and your money.",
     ["Project Manager · 15 tabs", "Weekly Planner Pro · 8 tabs", "Budget Spreadsheet · 28 tabs"],
     "Productivity Spreadsheet Bundle — Projects, Planner & Budget",
     "Three complete Excel and Google Sheets templates at one bundle price: project manager, weekly planner and budget spreadsheet. #spreadsheettemplates #productivity #budgeting #projectmanagement #googlesheets"),
    ("debt_payoff", M + "Debt_Payoff_Calculator", "main", 1.0, "DEBT PAYOFF CALCULATOR", "Know the date you will be debt-free.",
     ["Your debt-free date", "Month-by-month plan", "Interest saved"],
     "Debt Payoff Calculator Spreadsheet (Snowball & Avalanche)",
     "List your debts, pick snowball or avalanche and see your debt-free date. Excel and Google Sheets. #debtpayoff #debtsnowball #debtfree #budgeting"),
    ("sinking_funds", M + "Sinking_Funds_Tracker", "main", 1.0, "SINKING FUNDS TRACKER", "Save for each goal and see if you are on track.",
     ["15 savings goals", "Progress and months to go", "Deposit and withdrawal log"],
     "Sinking Funds Tracker Spreadsheet",
     "Save for every goal with progress bars, months to go and an on-track check. Excel and Google Sheets. #sinkingfunds #savingsgoals #budgeting #savingmoney"),
    ("net_worth", M + "Net_Worth_Tracker", "main", 0.8, "NET WORTH TRACKER", "See what you own, what you owe and the difference.",
     ["Assets and liabilities", "24-month history", "Charts by type"],
     "Net Worth Tracker Spreadsheet",
     "Track what you own and what you owe, and watch your net worth grow month by month. Excel and Google Sheets. #networth #personalfinance #wealthbuilding"),
    ("no_spend", M + "No_Spend_Challenge_Tracker", "main", 0.75, "NO-SPEND CHALLENGE TRACKER", "Count your no-spend days and what they saved.",
     ["Up to 60 days", "Streaks and success rate", "Money saved"],
     "No-Spend Challenge Tracker Spreadsheet",
     "Take a no-spend challenge and see your streaks and savings add up. Excel and Google Sheets. #nospendchallenge #savingschallenge #frugalliving #savingmoney"),
    ("investment", M + "Investment_Growth_Calculator", "main", 1.0, "INVESTMENT GROWTH CALCULATOR", "See what regular investing could be worth.",
     ["Future value and growth", "3 return scenarios", "Inflation-adjusted"],
     "Investment Growth Calculator Spreadsheet",
     "See how regular investing could grow, with three return scenarios side by side. Hypothetical projections for planning. Excel and Google Sheets. #investing #compoundinterest #financialplanning"),
    ("habit_tracker", M + "Habit_Tracker", "main", 1.0, "HABIT TRACKER · 12 MONTHS", "See which habits you keep, month by month.",
     ["Tick each day", "Success rates and goals", "Year overview"],
     "Habit Tracker Spreadsheet — 12 Months + Year Overview",
     "Track up to 12 habits every day and see your success rate by month and year. Excel and Google Sheets. #habittracker #goalsetting #productivity #newyeargoals"),
]


def shot(prod, name, bottom, right=1.0):
    im = Image.open(ROOT / prod / "screens" / f"{name}.png").convert("RGB")
    w, h = im.size
    return im.crop((0, 0, int(w * right), int(h * bottom)))


RIGHT = {"debt": 0.6, "main@Debt_Payoff_Calculator": 0.6, "main@Sinking_Funds_Tracker": 0.62}     # very wide tabs: show the left part
MX = 70


def make(spec):
    """Brass Ledger pin: paper background, brass kicker, green Fraunces headline, double rule, real screenshot, logo."""
    fname, prod, screen, bottom, kicker, title, points, *_ = spec
    img = Image.new("RGB", (PW, PH), BL.PAPER)
    d = ImageDraw.Draw(img)
    top = BL.head(img, kicker, title.replace("\n", " "), x=MX, y=80, max_w=PW - 2 * MX, size=92, ksize=21) + 50
    py = PH - 150 - len(points) * 64 - 30
    if screen:
        right = RIGHT.get(screen, RIGHT.get(f"{screen}@{prod.split('/')[-1]}", 1.0))
        BL.frame(img, shot(prod, screen, bottom, right), (MX, top, PW - MX, py - 50), "t")
    else:                                      # bundle: three overlapping screenshots
        BL.frame(img, shot("01_Ultimate_Project_Manager", "AllinOne_Dashboard", 0.5), (MX, top, 640, top + 420), "tl")
        BL.frame(img, shot("03_Weekly_Planner_Pro", "week_top", 0.8), (400, top + 200, PW - MX, top + 600), "tr")
        BL.frame(img, shot("04_Ultimate_Budget_Spreadsheet", "dashboard", 0.45), (MX + 60, top + 400, 700, py - 50), "tl")
    BL.checks(img, points, MX, py, PW - 2 * MX, size=36, gap=18, color=BL.GREEN)
    BR.wordmark(img, (MX, PH - 120), 52)
    d.text((PW - MX, PH - 78), "Instant download on Etsy", font=BL.F(26, 500), fill=BL.INK2, anchor="rm")
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
