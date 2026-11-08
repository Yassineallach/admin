"""Etsy listing images for PRODUCT 3 — Weekly Planner Pro (10 images, 2400x1800).

Screenshots are real renders of the DEMO workbooks: the builder runs with listing print areas (overview, one day
card, trackers, calendar, setup), LibreOffice recalculates and prints them, and each page becomes a PNG.

Usage: python listing_images_wp.py [--reshoot]
Output: listings/03_Weekly_Planner_Pro/images/01_hero.png ... 10_*.png
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
import build_weekly_planner as B  # noqa: E402
import icons  # noqa: E402
from common import solidify_databars  # noqa: E402
from listing_kit import (CORAL, DARK, GREY, LAV, MINT, NAVY, ORANGE, TEAL, W, WHITE, canvas, card,  # noqa: E402
                         footer, framed, heading, icon_bullet, laptop, pill, text)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "listings" / "03_Weekly_Planner_Pro"
SCREENS, SHEETS_SCREENS, IMAGES = OUT / "screens", OUT / "screens_sheets", OUT / "images"
FOOT = "Instant download  ·  Excel + Google Sheets  ·  No macros"
BLUE = (47, 111, 170)

# (screen name, sheet, print area)
SHOTS = [("setup", B.S_SETUP, "A1:L24"),
         ("week_top", "Week 2", f"A1:L{B.DAY_ROW[1] - 2}"),
         ("day_card", "Week 2", f"B{B.DAY_ROW[2]}:L{B.DAY_ROW[2] + 11}"),
         ("trackers", "Week 2", f"A{B.HT}:L{B.CH + B.CH_H}"),
         ("reflection", "Week 1", f"B{B.RF}:L{B.RF + 5}"),
         ("calendar", B.S_CAL, "A1:L38")]


def shoot(edition, folder):
    """Build the DEMO workbook with listing print areas, print it with LibreOffice and save one PNG per area."""
    folder.mkdir(parents=True, exist_ok=True)
    b = B.Builder(edition, True)
    wb = b.build()
    areas = {}
    for name, sheet, area in SHOTS:
        areas.setdefault(sheet, []).append(area)
    for n in B.ORDER:
        ws = b.ws[n]
        if n in areas:
            ws.print_area = areas[n]
            ws.page_setup.orientation = "portrait" if n in B.WEEKS else "landscape"
            ws.page_setup.fitToHeight = 0
        else:
            ws.print_area = "Z300:Z300"          # empty: LibreOffice prints no page for it
    wb.active = B.ORDER.index(B.S_SETUP)
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "s.xlsx"
    wb.save(p)
    solidify_databars(p)
    for name, lay in getattr(b, "side_layers", {}).items():
        if name in areas:
            lay.inject(p, name)
    rc = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
    subprocess.run([sys.executable, rc, str(p), "300"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(p)], capture_output=True)
    # identify every printed page by its text (page order is not reliable across LibreOffice versions)
    pdf = tmp / "s.pdf"
    n_pages = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    marks = {"setup": lambda t: t.startswith("WEEKLY PLANNER PRO"), "week_top": lambda t: t.startswith("WEEK 2"),
             "trackers": lambda t: "HABIT TRACKER" in t, "reflection": lambda t: "What went well" in t,
             "calendar": lambda t: t.startswith("MONTHLY CALENDAR"),
             "day_card": lambda t: "Task checklist" in t and "WEEK 2" not in t and "HABIT" not in t}
    found = {}
    for i in range(1, n_pages + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True, text=True).stdout
        t = " ".join(t.split()).replace("Setup Wk 1 Wk 2 Wk 3 Wk 4 Wk 5 Wk 6 Month ", "").lstrip("Setup ").strip()
        for name, f in marks.items():
            if name not in found and f(t):
                found[name] = i
    missing = [s_[0] for s_ in SHOTS if s_[0] not in found]
    if missing:
        raise SystemExit(f"pages not found for {missing}")
    for name, i in found.items():
        stem = tmp / name
        subprocess.run(["pdftoppm", "-f", str(i), "-l", str(i), "-r", "260", "-png", "-singlefile", str(pdf), str(stem)],
                       capture_output=True)
        subprocess.run(["convert", f"{stem}.png", "-trim", "+repage", str(folder / f"{name}.png")])
        crop_tail(folder / f"{name}.png")
    shutil.rmtree(tmp, ignore_errors=True)


def crop_tail(path):
    """Cut the empty page below the content (the sidebar shape runs past the print area)."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    x0 = int(w * 0.08)
    last = h - 1
    while last > 0 and all(min(px[x, last]) > 245 for x in range(x0, w, 7)):
        last -= 1
    im.crop((0, 0, w, min(h, last + 12))).save(path)


def shot(name, top=0.0, bottom=1.0, left=0.0, right=1.0, folder=None):
    im = Image.open((folder or SCREENS) / f"{name}.png").convert("RGB")
    w, h = im.size
    return im.crop((int(w * left), int(h * top), int(w * right), int(h * bottom)))


def ic(name, color="FFFFFF"):
    f = icons.ICONS[name] if isinstance(name, str) else name
    return f(c=color, size=96)


def save(img, name):
    IMAGES.mkdir(parents=True, exist_ok=True)
    img.save(IMAGES / name, "PNG", optimize=True)
    print("wrote", name)


def bullets(img, items, x=1640, y=400, w=680, circle=TEAL, gap=46):
    for icon, t_, b_ in items:
        y = icon_bullet(img, (x, y), ic(icon), t_, b_, w=w, circle=circle, title_size=40, body_size=29) + gap
    return y


# ------------------------------------------------------------------ 1 hero
def hero():
    img = canvas()
    text(img, (150, 170), "WEEKLY", 64, "SemiBold", TEAL)
    text(img, (150, 250), "Planner\nPro", 150, "ExtraBold", NAVY, spacing=0)
    text(img, (150, 600), "Excel & Google Sheets template", 50, "Medium", DARK)
    y = 720
    for t_ in ("6 reusable weekly planners", "Tasks, schedule & priorities", "Habit, water & exercise trackers",
               "Auto-filling monthly calendar"):
        img = card(img, (150, y, 860, y + 92), radius=46, shade=False, fill=WHITE)
        text(img, (200, y + 46), "✓", 42, "Bold", TEAL, anchor="lm")
        text(img, (260, y + 46), t_, 38, "SemiBold", DARK, anchor="lm")
        y += 118
    pill(img, (150, 1240), "8 TABS", 40, NAVY)
    pill(img, (390, 1240), "NO MACROS", 40, TEAL)
    pill(img, (150, 1350), "DEMO + BLANK VERSIONS", 40, ORANGE)
    img, _ = laptop(img, shot("week_top"), 1640, 330, 1300)
    footer(img, FOOT)
    save(img, "01_hero.png")


# ------------------------------------------------------------------ 2 what's included
def included():
    img = canvas()
    heading(img, "What's included", "8 connected tabs + 4 files, ready in minutes")
    tabs = [("gear", "Setup", "Your details, preferences, working hours, lists and a six-week overview", LAV),
            (icons.week_num(1), "Week 1 … Week 6", "Six identical weekly planners — each one reusable for any week", BLUE),
            ("calendar", "Monthly Calendar", "Dates, deadlines, tasks from your weeks, week goals and monthly priorities", NAVY)]
    y = 380
    for icon, t_, b_, col in tabs:
        img = card(img, (130, y, 1150, y + 250), radius=36)
        icon_bullet(img, (180, y + 60), ic(icon), t_, b_, w=920, circle=col, title_size=44, body_size=30)
        y += 290
    img = card(img, (1250, 380, W - 130, 1240), radius=36)
    text(img, (1310, 430), "EVERY WEEK TAB HAS", 30, "Bold", TEAL)
    feats = ["Week number, dates & main goal", "Top 3 priorities", "7 day cards: priorities, 10 tasks,",
             "   10-slot schedule, appointments, notes", "Live progress tiles", "Habit tracker (8 habits)",
             "Water & exercise trackers", "Productivity score + 2 charts", "Weekly reflection & rating"]
    yy = 500
    for f_ in feats:
        indent = f_.startswith("   ")
        if not indent:
            text(img, (1320, yy), "✓", 36, "Bold", TEAL)
        text(img, (1380, yy), f_.strip(), 34, "Medium", DARK)
        yy += 78
    img = card(img, (130, 1330, W - 130, 1640), radius=40)
    text(img, (190, 1380), "YOU RECEIVE", 30, "Bold", TEAL)
    x = 190
    for f_ in ("Excel – DEMO", "Excel – BLANK", "Google Sheets – DEMO", "Google Sheets – BLANK", "PDF user guide"):
        x = pill(img, (x, 1450), f_, 32, MINT, NAVY) + 26
    footer(img, FOOT)
    save(img, "02_whats_included.png")


# ------------------------------------------------------------------ 3 week overview
def week_overview():
    img = canvas()
    heading(img, "Your week at a glance", "Goal, priorities and live progress — all in one place")
    img, _ = framed(img, shot("week_top"), 110, 360, 1450, 1330)
    bullets(img, [("stack", "Week overview", "Week number, dates, your main goal and top 3 priorities"),
                  ("bar_chart", "8 live tiles", "Progress, tasks done, habits, water, exercise, productivity"),
                  ("calendar", "Jump links", "One click to any day, the trackers or your reflection"),
                  ("clock", "Today highlighted", "Today's card turns teal automatically")])
    footer(img, FOOT)
    save(img, "03_week_overview.png")


# ------------------------------------------------------------------ 4 day card
def day_card():
    img = canvas()
    heading(img, "Plan every day in detail", "Seven day cards per week, Monday to Sunday")
    img, box = framed(img, shot("day_card"), 110, 380, W - 220, 760)
    items = [("stack", "Top 3 priorities", "Tick them off with ✓"),
             ("clipboard", "10-task checklist", "Category, priority and status dropdowns; done tasks strike through"),
             ("clock", "Time schedule", "10 slots from your working hours"),
             ("people", "Appointments & notes", "Three appointments plus space for notes")]
    x = 130
    for icon, t_, b_ in items:
        icon_bullet(img, (x, box[3] + 70), ic(icon), t_, b_, w=520, title_size=36, body_size=27)
        x += 545
    footer(img, FOOT)
    save(img, "04_day_cards.png")


# ------------------------------------------------------------------ 5 trackers
def trackers():
    img = canvas()
    heading(img, "Build better habits", "Habit, water, exercise and productivity trackers in every week")
    img, _ = framed(img, shot("trackers"), 110, 360, 1450, 1330)
    bullets(img, [("repeat", "Habit tracker", "8 habits from Setup, ✓ or ✗ each day, weekly count"),
                  ("week", "Water intake", "Glasses per day; ✓ when you reach your daily goal"),
                  ("clock", "Exercise", "Type and minutes per day vs your weekly goal"),
                  ("bar_chart", "Productivity", "Score each day 1–10; two charts update by themselves")], circle=LAV)
    footer(img, FOOT)
    save(img, "05_trackers.png")


# ------------------------------------------------------------------ 6 monthly calendar
def calendar():
    img = canvas()
    heading(img, "A monthly calendar that fills itself", "Pick any month — dates, deadlines and your week tabs appear")
    img, _ = framed(img, shot("calendar"), 110, 360, 1500, 1330)
    bullets(img, [("calendar", "Month selector", "Choose a year and month from the dropdowns"),
                  ("stack", "★ Important dates", "Birthdays, holidays and events"),
                  ("clipboard", "Deadlines", "Late ones turn red automatically"),
                  ("bar_chart", "Your tasks", "Done / planned from all six week tabs"),
                  ("week", "Week goals & priorities", "Each week's goal and 3 monthly priorities")], x=1690, w=630, gap=34)
    footer(img, FOOT)
    save(img, "06_monthly_calendar.png")


# ------------------------------------------------------------------ 7 reflection
def reflection():
    img = canvas()
    heading(img, "Reflect and improve", "A weekly review with prompts and a 1–10 rating")
    img, box = framed(img, shot("reflection"), 110, 380, W - 220, 760)
    items = [("question", "Guided prompts", "What went well, what was hard, what you learned"),
             ("stack", "Next week's focus", "Carry lessons into the next week"),
             ("bar_chart", "Week rating", "1–10 rating shown as stars")]
    x = 130
    for icon, t_, b_ in items:
        icon_bullet(img, (x, box[3] + 80), ic(icon), t_, b_, w=700, circle=LAV, title_size=38, body_size=28)
        x += 730
    footer(img, FOOT)
    save(img, "07_reflection.png")


# ------------------------------------------------------------------ 8 setup
def setup():
    img = canvas()
    heading(img, "Set it up once", "Your preferences drive every week — and see all six weeks on one page")
    img, _ = framed(img, shot("setup"), 110, 360, 1450, 1330)
    bullets(img, [("gear", "Preferences", "Week starts Monday or Sunday, Week 1 date, goals"),
                  ("clock", "Working hours", "Start, end and slot length build the schedules"),
                  ("table", "Your lists", "Categories, priorities, statuses, habits, exercise"),
                  ("week", "Six-week overview", "Dates, goals and progress, one click to each week")])
    footer(img, FOOT)
    save(img, "08_setup.png")


# ------------------------------------------------------------------ 9 how it works
def how_it_works():
    img = canvas()
    heading(img, "Ready in 3 steps", "No formulas to write — just fill in the light-mint cells")
    steps = [("gear", "1. Set up", "Pick your week start, Week 1 date, working hours and habits."),
             ("clipboard", "2. Plan your week", "Write your goal, priorities, tasks and schedule."),
             ("bar_chart", "3. Track & review", "Tick tasks and habits — progress, charts and calendar update.")]
    x = 130
    for icon, t_, b_ in steps:
        img = card(img, (x, 380, x + 680, 900), radius=40)
        d = ImageDraw.Draw(img)
        d.ellipse((x + 50, 430, x + 190, 570), fill=TEAL)
        icim = Image.open(io.BytesIO(ic(icon))).convert("RGBA").resize((80, 80), Image.LANCZOS)
        img.paste(icim, (x + 80, 460), icim)
        text(img, (x + 50, 620), t_, 46, "Bold", NAVY)
        text(img, (x + 50, 700), b_, 32, "Regular", GREY, max_w=580)
        x += 735
    img = card(img, (130, 980, W - 130, 1620), radius=40)
    text(img, (190, 1030), "WORKS WITH", 32, "Bold", TEAL)
    rows = [("Microsoft Excel (desktop, Windows & Mac)", "Recommended — clickable icon sidebar"),
            ("Excel for the web", "Opens the same Excel file"),
            ("Google Sheets", "Dedicated edition — same formulas, trackers and calendar"),
            ("Not for Apple Numbers", "Not supported")]
    y = 1100
    for t_, b_ in rows:
        mark, color = ("✗", CORAL) if t_.startswith("Not") else ("✓", TEAL)
        text(img, (200, y), mark, 44, "Bold", color)
        text(img, (270, y), t_, 38, "SemiBold", DARK)
        text(img, (1150, y + 4), b_, 32, "Regular", GREY, max_w=1050)
        y += 120
    footer(img, FOOT)
    save(img, "09_how_it_works.png")


# ------------------------------------------------------------------ 10 editions
def editions():
    img = canvas()
    heading(img, "Excel & Google Sheets editions", "Both included — pick the app you already use")
    img, _ = framed(img, shot("week_top", 0, 0.62), 110, 330, 1480, 1000)
    img, _ = framed(img, shot("week_top", 0, 0.62, folder=SHEETS_SCREENS), 1000, 800, 1290, 860)
    pill(img, (1640, 380), "Excel edition", 38, NAVY)
    text(img, (1640, 470), "Clickable icon sidebar,\nprotected formulas", 34, "Medium", GREY, spacing=8)
    pill(img, (140, 1230), "Google Sheets edition", 38, TEAL)
    text(img, (140, 1320), "Same formulas, trackers\nand calendar", 34, "Medium", GREY, spacing=8)
    footer(img, FOOT)
    save(img, "10_excel_and_sheets.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reshoot", action="store_true")
    a = ap.parse_args()
    if a.reshoot or not (SCREENS / "week_top.png").exists():
        shoot("excel", SCREENS)
    if a.reshoot or not (SHEETS_SCREENS / "week_top.png").exists():
        shoot("gsheets", SHEETS_SCREENS)
    for f in (hero, included, week_overview, day_card, trackers, calendar, reflection, setup, how_it_works, editions):
        f()


if __name__ == "__main__":
    main()
