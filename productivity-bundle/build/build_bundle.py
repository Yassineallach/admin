"""Bundle listing: Ultimate Productivity Bundle = Project Manager + Weekly Planner Pro + Budget Spreadsheet.

Builds listings/06_Ultimate_Productivity_Bundle/: etsy_upload/ (one ZIP + START_HERE.pdf), 7 images, LISTING.md.
Run after the three products and their listing screenshots exist.
Usage: python build_bundle.py
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
import md_to_pdf  # noqa: E402
import brand_listing as BL  # noqa: E402
from brand_listings_content import BUNDLE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "listings" / "06_Ultimate_Productivity_Bundle"
IMAGES, UP = OUT / "images", OUT / "etsy_upload"
# (dist folder, name, list price, launch price)
PRODUCTS = [("01_Ultimate_Project_Manager", "Ultimate Project Manager", 14.99, 8.99),
            ("03_Weekly_Planner_Pro", "Weekly Planner Pro", 8.99, 4.99),
            ("04_Ultimate_Budget_Spreadsheet", "Ultimate Budget Spreadsheet", 19.99, 9.99)]
LIST_PRICE, LAUNCH_PRICE = 29.99, 16.99


def images():
    sep_list = sum(p[2] for p in PRODUCTS)
    BL.make(BUNDLE)
    return sep_list, round(100 * (1 - LIST_PRICE / sep_list))


def package():
    if UP.exists():
        shutil.rmtree(UP)
    UP.mkdir(parents=True)
    z = UP / "Ultimate_Productivity_Bundle.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for prod, nm, _lp, _l in PRODUCTS:
            dist = ROOT / "dist" / prod
            for f in sorted(dist.rglob("*")):
                if f.is_file() and f.suffix in (".xlsx", ".pdf"):
                    zf.write(f, Path("Ultimate_Productivity_Bundle") / prod[3:] / f.relative_to(dist))
    md = UP / "START_HERE.md"
    md.write_text("""# Start Here — Ultimate Productivity Bundle

Thank you for your purchase from Brass Ledger. Your download has this guide and **Ultimate_Productivity_Bundle.zip**. Unzip it first (double-click on Mac; right-click › Extract All on Windows). Inside are three folders, one per template.

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

- White cells with a border are for your input; shaded cells are formulas, so don't type over them.
- DEMO files are fixed to a sample date so they always look current. Clear *Today's date override* on the Setup tab to use the real date.
- Each template works on its own: start with whichever you need first.

## Need help?

Send me a message on Etsy and I will help you get set up.
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
    launch_sum = sum(p[3] for p in PRODUCTS)
    (OUT / "LISTING.md").write_text(f"""# Etsy listing — Ultimate Productivity Bundle

Three templates in one listing: Ultimate Project Manager, Weekly Planner Pro and Ultimate Budget Spreadsheet. Publish this after the three single listings are live.

{BL.photos_table(BUNDLE)}
Add more photos from the single listings if you like (Etsy allows up to 20).

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
- Keep the bundle cheaper than the sum of whatever the three singles cost at that moment. The images show no prices, so you can change prices without rebuilding them.
- Etsy fees at ${LAUNCH_PRICE:.2f} ≈ ${0.065 * LAUNCH_PRICE + 0.03 * LAUNCH_PRICE + 0.25 + 0.20:.2f} per sale (US rates).

## Description

```
Run your projects, your week and your money from three workbooks, at one price. Each one updates itself as you type and works in Microsoft Excel and Google Sheets. No macros, no add-ons, no formulas to write. They work in any year.

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
• Questions? Send me a message and I will help.
```

> **AI disclosure (check Etsy's current policy).** Parts of these products and the listing images were made with AI assistance. If Etsy still asks for it, add *"Designed by me with the help of AI tools."* to the description.

## Files to upload

Upload everything in `etsy_upload/`: `Ultimate_Productivity_Bundle.zip` and `START_HERE.pdf`.

## Seller checklist

- [ ] Publish the three single listings first, then this one.
- [ ] Upload the 7 images in order and add the alt text.
- [ ] Paste the title, tags, description and materials. Set the price below the sum of the singles.
- [ ] Upload the two files from `etsy_upload/`.
- [ ] Mention the bundle in each single listing's description ("Save with the 3-in-1 bundle in my shop").
""", encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    package()
    sep, pct = images()
    listing(sep, pct)
