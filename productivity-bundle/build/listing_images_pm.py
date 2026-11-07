"""Etsy listing images for PRODUCT 1 — Ultimate Project Manager (10 images, 2400x1800).

Usage: python listing_images_pm.py   (renders screenshots first if missing)
Output: listings/01_Ultimate_Project_Manager/images/01_hero.png ... 10_*.png
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import icons  # noqa: E402
import render_screens  # noqa: E402
from listing_kit import (CORAL, DARK, GREY, H, LAV, MINT, NAVY, ORANGE, TEAL, TEAL2, W, WHITE, canvas, card,  # noqa: E402
                         footer, framed, heading, icon_bullet, laptop, pill, text)

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "01_Ultimate_Project_Manager"
OUT = ROOT / "listings" / "01_Ultimate_Project_Manager"
SCREENS, SHEETS_SCREENS, IMAGES = OUT / "screens", OUT / "screens_sheets", OUT / "images"


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


# ------------------------------------------------------------------ 1 hero
def hero():
    img = canvas()
    text(img, (150, 170), "ULTIMATE", 64, "SemiBold", TEAL)
    text(img, (150, 250), "Project\nManager", 150, "ExtraBold", NAVY, spacing=0)
    text(img, (150, 600), "Excel & Google Sheets template", 50, "Medium", DARK)
    y = 720
    for t_ in ("Auto-updating dashboard", "Gantt chart & Kanban board", "Monthly & weekly calendars", "Budget, revenue & margin"):
        img = card(img, (150, y, 840, y + 92), radius=46, shade=False, fill=WHITE)
        text(img, (200, y + 46), "✓", 42, "Bold", TEAL, anchor="lm")
        text(img, (260, y + 46), t_, 38, "SemiBold", DARK, anchor="lm")
        y += 118
    pill(img, (150, 1240), "15 TABS", 40, NAVY)
    pill(img, (420, 1240), "NO MACROS", 40, TEAL)
    pill(img, (150, 1350), "DEMO + BLANK VERSIONS", 40, (235, 140, 60))
    img, _ = laptop(img, shot("AllinOne_Dashboard", 0, 0.55), 1640, 330, 1300)
    footer(img)
    save(img, "01_hero.png")


# ------------------------------------------------------------------ 2 what's included
def included():
    img = canvas()
    heading(img, "What's included", "15 connected tabs + 4 files, ready in minutes")
    groups = [
        ("SET UP", TEAL, [("gear", "Setup", "workspace, lists, currency")]),
        ("DASHBOARDS", NAVY, [("bar_chart", "All-in-One Dashboard", "KPIs, 6 charts, 6 lists"),
                              ("calendar", "Monthly Calendar", "tasks, deadlines, recurring"),
                              ("week", "Weekly Calendar", "time blocks & workload")]),
        ("PROJECTS", (47, 111, 170), [("table", "Project Overview", "portfolio, health, margin"),
                                       ("people", "Project Manager", "one-project detail view"),
                                       ("money", "Project Budget", "planned vs actual")]),
        ("TASKS", (31, 169, 156), [("clipboard", "Variable Tasks", "500-row task database"),
                                   ("repeat", "Recurring Tasks", "daily to custom repeats"),
                                   ("clock", "Task Schedule", "time blocks"),
                                   ("filter", "Task Filter", "10 filters + search")]),
        ("EXTRAS", LAV, [("scale", "Decision Matrix", "weighted scoring + Eisenhower"),
                         ("kanban", "Kanban Board", "cards move by status"),
                         ("gantt", "Gantt Chart", "daily / weekly timeline"),
                         ("question", "Instructions", "step-by-step help")]),
    ]
    cols = [(130, [0, 1]), (900, [2, 3]), (1670, [4])]
    for x, idxs in cols:
        y = 380
        for gi in idxs:
            name, color, items = groups[gi]
            pill(img, (x, y), name, 30, color)
            y += 90
            for icon, title, body in items:
                y = icon_bullet(img, (x, y), ic(icon), title, body, w=640, circle=color, title_size=36, body_size=28) + 30
            y += 30
    # files strip
    img = card(img, (130, 1430, W - 130, 1640), radius=40)
    files = ["Excel – DEMO", "Excel – BLANK", "Google Sheets – DEMO", "Google Sheets – BLANK", "PDF user guide"]
    x = 190
    text(img, (190, 1470), "YOU RECEIVE", 30, "Bold", TEAL)
    for f_ in files:
        x = pill(img, (x, 1530), f_, 32, MINT, NAVY) + 26
    footer(img)
    save(img, "02_whats_included.png")


# ------------------------------------------------------------------ 3 dashboard
def dashboard():
    img = canvas()
    heading(img, "Your command center", "Everything updates automatically from your task list")
    img, box = framed(img, shot("AllinOne_Dashboard", 0, 0.62), 110, 360, 1450, 1330)
    x = 1640
    y = 400
    for icon, t_, b_ in (("stack", "4 KPI tiles", "Projects, task completion, remaining budget and the period you pick"),
                         ("calendar", "Period picker", "Choose a year and month range — tiles and charts follow"),
                         ("bar_chart", "6 live charts", "Tasks by month, project status, progress, budget, priority, team"),
                         ("clipboard", "6 smart lists", "Due today (incl. recurring), upcoming, overdue, recent, deadlines"),
                         ("table", "Performance table", "Progress bars, spend, margin and health per project")):
        y = icon_bullet(img, (x, y), ic(icon), t_, b_, w=680, title_size=40, body_size=29) + 46
    footer(img)
    save(img, "03_dashboard.png")


# ------------------------------------------------------------------ 4 calendars
def calendars():
    img = canvas()
    heading(img, "Monthly & weekly calendars", "Deadlines, recurring tasks and time blocks — filled in for you")
    img, _ = framed(img, shot("Monthly_Calendar", 0.0, 1.0, 0, 0.78), 110, 340, 1560, 1290)
    img, _ = framed(img, shot("Weekly_Calendar", 0.0, 0.62), 1180, 640, 1110, 1000)
    pill(img, (1720, 380), "Pick any week or month", 34, TEAL)
    pill(img, (1720, 470), "↻ Recurring shown", 34, LAV)
    footer(img)
    save(img, "04_calendars.png")


# ------------------------------------------------------------------ 5 kanban + gantt
def kanban_gantt():
    img = canvas()
    heading(img, "Kanban board & Gantt chart", "Change a status or a date once — both views redraw themselves")
    img, _ = framed(img, shot("Kanban_Board", 0, 0.55), 110, 340, 1560, 900)
    img, _ = framed(img, shot("Gantt_Chart", 0, 0.40, 0, 0.72), 900, 860, 1390, 800)
    pill(img, (1720, 380), "5 status columns", 34, NAVY)
    pill(img, (1720, 470), "Priority flags ‼ ▲", 34, TEAL)
    pill(img, (140, 1300), "Daily / weekly timeline", 34, NAVY)
    pill(img, (140, 1390), "Milestones & today line", 34, TEAL)
    footer(img)
    save(img, "05_kanban_gantt.png")


# ------------------------------------------------------------------ 6 projects & budget
def projects():
    img = canvas()
    heading(img, "Every project in one place", "Detail view, portfolio health, budget, revenue and margin")
    img, _ = framed(img, shot("Project_Manager", 0, 0.62, 0, 0.62), 110, 340, 1100, 1300)
    img, _ = framed(img, shot("Project_Overview", 0, 0.30, 0, 0.62), 1000, 360, 1290, 640)
    img, _ = framed(img, shot("Project_Budget", 0, 0.40, 0, 1.0), 1000, 1000, 1290, 640)
    footer(img)
    save(img, "06_projects_budget.png")


# ------------------------------------------------------------------ 7 tasks
def tasks():
    img = canvas()
    heading(img, "Tasks that run themselves", "One-time, recurring and scheduled work — with filters and search")
    img, _ = framed(img, shot("Variable_Tasks", 0, 0.45, 0, 0.62), 110, 360, 1380, 720)
    img, _ = framed(img, shot("Recurring_Tasks", 0, 0.32, 0, 0.7), 110, 1110, 1380, 520)
    x, y = 1580, 400
    for icon, t_, b_ in (("clipboard", "500-row task database", "Priority, status, hours, progress, notes"),
                         ("repeat", "Recurring tasks", "Daily, weekly, biweekly, monthly, quarterly, annual or every N days"),
                         ("calendar", "Completion dates", "Track when work was really finished"),
                         ("filter", "Task Filter", "Combine 10 filters plus keyword search"),
                         ("clock", "Time blocks", "Schedule tasks by the hour")):
        y = icon_bullet(img, (x, y), ic(icon), t_, b_, w=700, title_size=38, body_size=28) + 40
    footer(img)
    save(img, "07_tasks.png")


# ------------------------------------------------------------------ 8 decisions
def decisions():
    img = canvas()
    heading(img, "Decide faster", "Weighted decision matrix + Eisenhower priority matrix")
    dm = shot("Decision_Matrix")
    w, h = dm.size
    img, _ = framed(img, dm.crop((0, 0, w, int(h * 0.56))), 110, 330, 1560, 900)
    img, _ = framed(img, dm.crop((0, int(h * 0.56), int(w * 0.62), h)), 1060, 860, 1230, 800)
    text(img, (1720, 380), "Weighted scores pick\nthe best option", 40, "Bold", NAVY, spacing=8)
    y = 1180
    for t_, color in (("Do first", CORAL), ("Schedule", (47, 111, 170)), ("Delegate", ORANGE), ("Eliminate", GREY)):
        pill(img, (140, y), t_, 38, color)
        y += 100
    text(img, (140, 1110), "Eisenhower quadrants", 40, "Bold", NAVY)
    footer(img)
    save(img, "08_decisions.png")


# ------------------------------------------------------------------ 9 how it works
def how_it_works():
    img = canvas()
    heading(img, "Ready in 3 steps", "No formulas to write — just fill in the light-mint cells")
    steps = [("gear", "1. Set up", "Add your name, team, currency and categories on the Setup tab."),
             ("clipboard", "2. Add projects & tasks", "Type them in — dropdowns keep everything consistent."),
             ("bar_chart", "3. Watch it update", "Dashboard, calendars, Kanban and Gantt fill in by themselves.")]
    x = 130
    for icon, t_, b_ in steps:
        img = card(img, (x, 380, x + 680, 900), radius=40)
        from listing_kit import icon_bullet as _ib  # noqa
        import io
        from PIL import ImageDraw
        d = ImageDraw.Draw(img)
        d.ellipse((x + 50, 430, x + 190, 570), fill=TEAL)
        icim = Image.open(io.BytesIO(ic(icon))).convert("RGBA").resize((80, 80), Image.LANCZOS)
        img.paste(icim, (x + 80, 460), icim)
        text(img, (x + 50, 620), t_, 46, "Bold", NAVY)
        text(img, (x + 50, 700), b_, 32, "Regular", GREY, max_w=580)
        x += 735
    img = card(img, (130, 980, W - 130, 1620), radius=40)
    text(img, (190, 1030), "WORKS WITH", 32, "Bold", TEAL)
    rows = [("Microsoft Excel (desktop, Windows & Mac)", "Recommended — full design: rounded cards, icon sidebar, live dashboard"),
            ("Excel for the web", "Opens the same Excel file"),
            ("Google Sheets", "Dedicated edition — same formulas, charts and layout with a flat design"),
            ("Not for Apple Numbers", "Not supported — Numbers can't run the dashboard features")]
    y = 1100
    for t_, b_ in rows:
        mark, color = ("✗", CORAL) if t_.startswith("Not") else ("✓", TEAL)
        text(img, (200, y), mark, 44, "Bold", color)
        text(img, (270, y), t_, 38, "SemiBold", DARK)
        text(img, (1150, y + 4), b_, 32, "Regular", GREY, max_w=1050)
        y += 120
    footer(img)
    save(img, "09_how_it_works.png")


# ------------------------------------------------------------------ 10 excel + google sheets
def editions():
    img = canvas()
    heading(img, "Excel & Google Sheets editions", "Both included — pick the app you already use")
    img, _ = framed(img, shot("AllinOne_Dashboard", 0, 0.5), 110, 330, 1480, 1000)
    img, _ = framed(img, shot("AllinOne_Dashboard", 0, 0.5, folder=SHEETS_SCREENS), 1000, 800, 1290, 860)
    pill(img, (1640, 380), "Excel edition", 38, NAVY)
    text(img, (1640, 470), "Rounded cards, icon\nsidebar, live tiles", 34, "Medium", GREY, spacing=8)
    pill(img, (140, 1230), "Google Sheets edition", 38, TEAL)
    text(img, (140, 1320), "Same formulas, charts\nand layout — flat design", 34, "Medium", GREY, spacing=8)
    footer(img)
    save(img, "10_excel_and_sheets.png")


def main():
    if not (SCREENS / "AllinOne_Dashboard.png").exists():
        render_screens.render(DIST / "Excel" / "Ultimate_Project_Manager_Excel_DEMO.xlsx", SCREENS, 220)
    if not (SHEETS_SCREENS / "AllinOne_Dashboard.png").exists():
        render_screens.render(DIST / "Google_Sheets" / "Ultimate_Project_Manager_GoogleSheets_DEMO.xlsx", SHEETS_SCREENS, 220,
                              markers={"All-in-One Dashboard": "Budget vs actual by project"})
    for f in (hero, included, dashboard, calendars, kanban_gantt, projects, tasks, decisions, how_it_works, editions):
        f()


if __name__ == "__main__":
    main()
