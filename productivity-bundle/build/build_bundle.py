"""Bundle listing: Ultimate Productivity Bundle = Project Manager + Weekly Planner Pro + Budget Spreadsheet.

Builds listings/06_Ultimate_Productivity_Bundle/: etsy_upload/ (one ZIP + START_HERE.pdf), 6 images, LISTING.md.
Run after the three products and their listing screenshots exist.
Usage: python build_bundle.py
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import icons  # noqa: E402
import md_to_pdf  # noqa: E402
from listing_kit import (CORAL, DARK, GREY, LAV, MINT, NAVY, ORANGE, TEAL, W, WHITE, canvas, card, footer, framed,  # noqa: E402
                         heading, icon_bullet, laptop, pill, text)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "listings" / "06_Ultimate_Productivity_Bundle"
IMAGES, UP = OUT / "images", OUT / "etsy_upload"
FOOT = "Instant download  ·  3 templates  ·  Excel + Google Sheets  ·  No macros"
BLUE = (47, 111, 170)
PRODUCTS = [
    ("01_Ultimate_Project_Manager", "Ultimate Project Manager", "15 tabs", "AllinOne_Dashboard", NAVY, 14.99, 8.99,
     ["Auto-updating dashboard", "Gantt chart & Kanban board", "Monthly & weekly calendars", "Budget, revenue & margin"]),
    ("03_Weekly_Planner_Pro", "Weekly Planner Pro", "8 tabs", "week_top", BLUE, 8.99, 4.99,
     ["6 reusable weekly planners", "Tasks, schedule & priorities", "Habit, water & exercise trackers", "Auto-filling monthly calendar"]),
    ("04_Ultimate_Budget_Spreadsheet", "Ultimate Budget Spreadsheet", "28 tabs", "dashboard", TEAL, 19.99, 9.99,
     ["12 monthly budgets + dashboard", "Recurring bills post themselves", "Debt snowball & avalanche plan", "Sinking funds, net worth & more"]),
]
LIST_PRICE, LAUNCH_PRICE = 29.99, 16.99


def shot(prod, name, top=0.0, bottom=1.0):
    im = Image.open(ROOT / "listings" / prod / "screens" / f"{name}.png").convert("RGB")
    w, h = im.size
    return im.crop((0, int(h * top), w, int(h * bottom)))


def save(img, name):
    IMAGES.mkdir(parents=True, exist_ok=True)
    img.save(IMAGES / name, "PNG", optimize=True)
    print("wrote", name)


def images():
    sep_list = sum(p[5] for p in PRODUCTS)
    save_pct = round(100 * (1 - LIST_PRICE / sep_list))
    # 1 hero
    img = canvas()
    text(img, (150, 150), "3-IN-1 BUNDLE", 60, "SemiBold", TEAL)
    text(img, (150, 230), "Ultimate\nProductivity\nBundle", 112, "ExtraBold", NAVY, spacing=0)
    text(img, (150, 640), "Excel & Google Sheets templates", 46, "Medium", DARK)
    y = 750
    for _p, nm, tabs, *_ in PRODUCTS:
        img = card(img, (150, y, 900, y + 92), radius=46, shade=False, fill=WHITE)
        text(img, (200, y + 46), "✓", 42, "Bold", TEAL, anchor="lm")
        text(img, (260, y + 46), f"{nm}  ·  {tabs}", 34, "SemiBold", DARK, anchor="lm")
        y += 118
    x_ = pill(img, (150, y + 30), "51 TABS", 40, NAVY)
    pill(img, (x_ + 26, y + 30), f"SAVE {save_pct}%", 40, ORANGE)
    img, _ = framed(img, shot(PRODUCTS[1][0], PRODUCTS[1][3], 0, 0.75), 1560, 300, 760, 640)
    img, _ = framed(img, shot(PRODUCTS[0][0], PRODUCTS[0][3], 0, 0.55), 1000, 560, 1000, 640)
    img, _ = framed(img, shot(PRODUCTS[2][0], PRODUCTS[2][3], 0, 0.6), 1340, 1020, 980, 640)
    footer(img, FOOT)
    save(img, "01_hero.png")
    # 2 what's included
    img = canvas()
    heading(img, "Three complete templates", "Run your projects, your week and your money")
    x = 130
    for prod, nm, tabs, scr, color, lp, _l, feats in PRODUCTS:
        img = card(img, (x, 360, x + 690, 1300), radius=36)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((x, 360, x + 690, 460), 36, fill=color)
        d.rectangle((x, 420, x + 690, 460), fill=color)
        text(img, (x + 345, 410), nm, 36, "Bold", WHITE, anchor="mm")
        img, b = framed(img, shot(prod, scr, 0, 0.5), x + 30, 490, 630, 330)
        pill(img, (x + 40, 850), tabs.upper(), 30, MINT, NAVY)
        yy = 940
        for f_ in feats:
            text(img, (x + 40, yy), "✓", 34, "Bold", TEAL)
            text(img, (x + 95, yy), f_, 31, "Medium", DARK, max_w=560)
            yy += 80
        x += 725
    img = card(img, (130, 1370, W - 130, 1640), radius=40)
    text(img, (190, 1415), "YOU RECEIVE", 30, "Bold", TEAL)
    x = 190
    for f_ in ("12 spreadsheet files", "Excel + Google Sheets editions", "DEMO + BLANK versions", "3 PDF user guides"):
        x = pill(img, (x, 1480), f_, 32, MINT, NAVY) + 26
    footer(img, FOOT)
    save(img, "02_whats_included.png")
    # 3-5 one per product
    subs = ["Projects, tasks, Gantt, Kanban and calendars — all connected",
            "Plan six weeks at a time and track your habits",
            "Budgets, bills, debt payoff and savings in one place"]
    icons_ = [("bar_chart", "table", "gantt", "calendar"), ("week", "clipboard", "repeat", "calendar"), ("money", "repeat", "card", "piggy")]
    for i, (prod, nm, tabs, scr, color, _lp, _l, feats) in enumerate(PRODUCTS):
        img = canvas()
        heading(img, nm, subs[i])
        img, _ = framed(img, shot(prod, scr), 110, 360, 1450, 1330)
        y = 400
        for icon, f_ in zip(icons_[i], feats):
            y = icon_bullet(img, (1640, y), icons.ICONS[icon](c="FFFFFF", size=96), f_, "", w=680, circle=color, title_size=38, body_size=10) + 40
        pill(img, (1640, y + 20), tabs.upper(), 36, NAVY)
        footer(img, FOOT)
        save(img, f"0{3 + i}_{prod[3:].lower()}.png")
    # 6 value
    img = canvas()
    heading(img, "Better together", f"Save {save_pct}% compared with buying each template separately")
    img = card(img, (130, 380, W - 130, 1080), radius=40)
    y = 450
    for _p, nm, tabs, _s, _c, lp, _l, _f in PRODUCTS:
        text(img, (220, y), nm, 44, "SemiBold", DARK)
        text(img, (1300, y + 4), tabs, 36, "Medium", GREY)
        text(img, (W - 220, y), f"${lp:.2f}", 44, "SemiBold", GREY, anchor="ra")
        y += 110
    ImageDraw.Draw(img).line((220, y + 10, W - 220, y + 10), fill=(200, 215, 212), width=4)
    text(img, (220, y + 50), "Bought separately", 40, "Medium", GREY)
    text(img, (W - 220, y + 50), f"${sep_list:.2f}", 40, "Medium", GREY, anchor="ra")
    text(img, (220, y + 140), "Bundle price", 56, "ExtraBold", NAVY)
    text(img, (W - 220, y + 130), f"${LIST_PRICE:.2f}", 72, "ExtraBold", TEAL, anchor="ra")
    img = card(img, (130, 1150, W - 130, 1620), radius=40)
    text(img, (190, 1200), "WORKS WITH", 32, "Bold", TEAL)
    yy = 1270
    for t_, b_ in (("Microsoft Excel (Windows & Mac) and Excel for the web", "Clickable icon sidebar"),
                   ("Google Sheets", "Dedicated editions with the same formulas and charts"),
                   ("Not for Apple Numbers", "Not supported")):
        mark, colr = ("✗", CORAL) if t_.startswith("Not") else ("✓", TEAL)
        text(img, (200, yy), mark, 44, "Bold", colr)
        text(img, (270, yy), t_, 36, "SemiBold", DARK)
        text(img, (1400, yy + 4), b_, 30, "Regular", GREY, max_w=800)
        yy += 110
    footer(img, FOOT)
    save(img, "06_better_together.png")
    return sep_list, save_pct


def package():
    if UP.exists():
        shutil.rmtree(UP)
    UP.mkdir(parents=True)
    z = UP / "Ultimate_Productivity_Bundle.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for prod, nm, *_ in PRODUCTS:
            dist = ROOT / "dist" / prod
            for f in sorted(dist.rglob("*")):
                if f.is_file() and f.suffix in (".xlsx", ".pdf"):
                    zf.write(f, Path("Ultimate_Productivity_Bundle") / prod[3:] / f.relative_to(dist))
    md = UP / "START_HERE.md"
    md.write_text("""# Start Here — Ultimate Productivity Bundle

Thank you for your purchase! Your download has this guide and **Ultimate_Productivity_Bundle.zip**. Unzip it first (double-click on Mac; right-click › Extract All on Windows). Inside are three folders, one per template.

## What's inside

| Folder | Template | Start on this tab |
|---|---|---|
| Ultimate_Project_Manager | Projects, tasks, Gantt chart, Kanban board, calendars (15 tabs) | Setup |
| Weekly_Planner_Pro | Six weekly planners, trackers and a monthly calendar (8 tabs) | Setup |
| Ultimate_Budget_Spreadsheet | Budgets, bills, debt payoff, savings and net worth (28 tabs) | Easy Setup |

Each folder has an **Excel** folder, a **Google_Sheets** folder and a **Guides** folder with a PDF user guide.

## Which file do I open?

| You use | Open this file |
|---|---|
| Microsoft Excel (Windows or Mac) | Excel / …_Excel_DEMO.xlsx to explore, …_Excel_BLANK.xlsx for real work |
| Excel for the web | Upload the Excel file to OneDrive and open it there |
| Google Sheets | Google_Sheets / …_GoogleSheets_DEMO.xlsx or …_BLANK.xlsx (see below) |

## Excel

Double-click the file. If you see *Protected View*, click **Enable Editing**. The files have no macros.

## Google Sheets

1. Go to drive.google.com › **New › File upload** and choose a file from a Google_Sheets folder.
2. Right-click it › **Open with › Google Sheets**.
3. **File › Save as Google Sheets.** Work in that copy.

## Tips

- Light-mint cells are for your input; grey cells are formulas, so don't type over them.
- DEMO files are fixed to a sample date so they always look current. Clear *Today's date override* on the Setup tab to use the real date.
- Each template works on its own: start with whichever you need first.

## Need help?

Send me a message on Etsy. I'm happy to help you get set up.
""", encoding="utf-8")
    md_to_pdf.render(md, UP / "START_HERE.pdf", footer="Ultimate Productivity Bundle · Start Here")
    md.unlink()
    for f in sorted(UP.iterdir()):
        mb = f.stat().st_size / 1e6
        print(f"{f.name}: {mb:.2f} MB", "(OVER Etsy's 20 MB limit!)" if mb > 20 else "")


def listing(sep_list, save_pct):
    title = "Productivity Bundle Excel Google Sheets, Project Management Template, Budget Spreadsheet, Weekly Planner, Habit Tracker, Gantt Chart"
    tags = ("productivity bundle, spreadsheet bundle, budget spreadsheet, project management, weekly planner, google sheets bundle, "
            "excel templates, habit tracker, gantt chart, debt snowball, small business, template bundle, planner bundle")
    tl = [t.strip() for t in tags.split(",")]
    assert len(title) <= 140 and len(tl) == 13 and all(len(t) <= 20 for t in tl), (len(title), [t for t in tl if len(t) > 20])
    launch_sum = sum(p[6] for p in PRODUCTS)
    (OUT / "LISTING.md").write_text(f"""# Etsy listing — Ultimate Productivity Bundle

Three templates in one listing: Ultimate Project Manager, Weekly Planner Pro and Ultimate Budget Spreadsheet. Publish this after the three single listings are live.

## Photos (upload in this order)

| # | File | Alt text |
|---|---|---|
| 1 | 01_hero.png | Productivity bundle of three spreadsheet templates: project manager, weekly planner and budget |
| 2 | 02_whats_included.png | The three templates with their main features and the files included |
| 3 | 03_ultimate_project_manager.png | Project manager dashboard with KPIs, charts and an icon sidebar |
| 4 | 04_weekly_planner_pro.png | Weekly planner with week overview, progress tiles and day cards |
| 5 | 05_ultimate_budget_spreadsheet.png | Budget dashboard with income, expenses, savings and charts |
| 6 | 06_better_together.png | Bundle price compared with buying the three templates separately |

Add more photos from the single listings if you like (Etsy allows up to 20). Video: reuse one of the single listings' videos.

## Title ({len(title)} / 140 characters)

```
{title}
```

## Listing details

| Field | Value |
|---|---|
| Who made it | I did |
| What is it | A finished product |
| When was it made | 2020 – 2026 |
| Type | Digital files |
| Category (suggested) | Paper & Party Supplies › Paper › Calendars & Planners (pick the closest current option) |
| Instant download | Yes |

## Tags (13 / 13)

```
{tags}
```

## Materials

```
Microsoft Excel, Google Sheets, digital download, spreadsheet template
```

## Price

- **List ${LIST_PRICE:.2f}**: {save_pct}% less than the three list prices added up (${sep_list:.2f}).
- **Launch at about ${LAUNCH_PRICE:.2f}** while the single listings are at their launch prices (${launch_sum:.2f} together), so the bundle is always the better deal.
- Keep the bundle cheaper than the sum of whatever the three singles cost at that moment. Image 6 shows the list prices: rebuild it with `python3 build/build_bundle.py` if you change them.
- Etsy fees at ${LAUNCH_PRICE:.2f} ≈ ${0.065 * LAUNCH_PRICE + 0.03 * LAUNCH_PRICE + 0.25 + 0.20:.2f} per sale (US rates).

## Description

```
Three complete templates to run your projects, your week and your money — at one bundle price. Each one updates itself as you type and works in Microsoft Excel and Google Sheets. No macros, no add-ons, no formulas to write. Tested formulas that work any year.

━━━━━━━━━━━━━━━━━━━━
1. ULTIMATE PROJECT MANAGER — 15 TABS
━━━━━━━━━━━━━━━━━━━━
✔ All-in-one dashboard with KPIs, 6 charts and smart lists
✔ Project overview, project detail view and project budget
✔ 500-row task database, recurring tasks, task schedule and task filter
✔ Gantt chart, Kanban board, monthly and weekly calendars
✔ Decision matrix with Eisenhower view

━━━━━━━━━━━━━━━━━━━━
2. WEEKLY PLANNER PRO — 8 TABS
━━━━━━━━━━━━━━━━━━━━
✔ Six reusable weekly planners: goal, top 3 priorities, live progress tiles
✔ 7 day cards with priorities, 10-task checklist, time schedule, appointments and notes
✔ Habit, water, exercise and productivity trackers with charts
✔ Weekly reflection and a monthly calendar that fills itself

━━━━━━━━━━━━━━━━━━━━
3. ULTIMATE BUDGET SPREADSHEET — 28 TABS
━━━━━━━━━━━━━━━━━━━━
✔ All-in-one dashboard: 8 KPIs and 6 charts, full year or any month
✔ 12 monthly budgets, annual totals, automated calendar and paycheck planner
✔ Recurring transactions that post themselves, payments with due dates, 1,000-row log
✔ Debt snowball / avalanche plan, sinking funds, 50/30/20, net worth, investment forecast, no-spend challenge

━━━━━━━━━━━━━━━━━━━━
WHAT YOU RECEIVE
━━━━━━━━━━━━━━━━━━━━
• 12 spreadsheet files: each template as Excel and Google Sheets editions, DEMO (sample data) and BLANK
• 3 PDF user guides + a Start Here guide

━━━━━━━━━━━━━━━━━━━━
COMPATIBILITY
━━━━━━━━━━━━━━━━━━━━
✔ Microsoft Excel desktop (Windows & Mac) and Excel for the web
✔ Google Sheets (free Google account)
✘ Not for Apple Numbers

━━━━━━━━━━━━━━━━━━━━
PLEASE NOTE
━━━━━━━━━━━━━━━━━━━━
• This is a DIGITAL product. Nothing will be shipped.
• The budget template is a planning tool, not financial advice.
• For personal or internal business use. Please don't resell or share the files.
• Questions? Send me a message — I'm happy to help.
```

> **AI disclosure (check Etsy's current policy).** Parts of these products and the listing images were made with AI assistance. If Etsy still asks for it, add *"Designed by me with the help of AI tools."* to the description.

## Files to upload

Upload everything in `etsy_upload/`: `Ultimate_Productivity_Bundle.zip` and `START_HERE.pdf`.

## Seller checklist

- [ ] Publish the three single listings first, then this one.
- [ ] Upload the 6 images in order and add the alt text.
- [ ] Paste the title, tags, description and materials. Set the price below the sum of the singles.
- [ ] Upload the two files from `etsy_upload/`.
- [ ] Mention the bundle in each single listing's description ("Save with the 3-in-1 bundle in my shop").
""", encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    package()
    sep, pct = images()
    listing(sep, pct)
