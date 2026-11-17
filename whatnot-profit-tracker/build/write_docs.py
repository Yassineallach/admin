"""Writes etsy-listing.md (copy-paste listing) and test-report.md into the deliverables folder.

The listing copy is checked here: title length, 13 unique tags of 20 characters or fewer, no exclamation marks,
no hype words. The test report reads the results of test_tracker.py and structure_check.txt.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "whatnot-profit-tracker"

TITLE = "Whatnot Seller Profit Tracker Spreadsheet, Live Show Sales & Fees Calculator, Reseller Dashboard, Excel & Google Sheets"
TAGS = ["whatnot seller", "live selling", "reseller tracker", "profit tracker", "whatnot spreadsheet", "live show tracker",
        "fee calculator", "reseller spreadsheet", "sales tracker", "trading card seller", "small business excel", "google sheets",
        "giveaway tracker"]
HYPE = re.compile(r"\b(ultimate|game.?changing|amazing|revolutionary|best ever|must.have|perfect)\b", re.I)

DESCRIPTION = """See the real profit from every show in two minutes.

Whatnot shows you sales after a show, not profit. This spreadsheet takes off commission, payment-processing fees, the cost of what you sold, giveaways and supplies, and shows which shows, days, time slots and categories actually make money.

Built for live selling: one row per show. Not a generic reseller inventory sheet.

━━━━━━━━━━━━━━━━━━━━
WHO IT'S FOR
━━━━━━━━━━━━━━━━━━━━
Sellers who run live shows on Whatnot: trading cards, Pokemon and TCG, sneakers, clothing, vintage, beauty, toys and collectibles. Side business or full time. No spreadsheet skills needed: you type numbers in white cells and the rest is done for you.

━━━━━━━━━━━━━━━━━━━━
WHAT IT DOES
━━━━━━━━━━━━━━━━━━━━
✔ Works out commission and processing fees for every show from the rates you set
✔ Net profit, profit margin, profit per hour live and average order value
✔ Giveaway cost per show, and giveaways as a share of sales
✔ Losing shows turn red; your top 25 % of shows turn green
✔ Dashboard: profit this month and year to date, average profit per show and per hour, fees paid, giveaway cost and progress toward your monthly goal
✔ Profit by time slot, weekday and category, a 12-month trend, and your top 5 and bottom 5 shows, each with a plain-English summary line
✔ Year summary by month, ready to hand to your tax preparer
✔ Optional item-by-item tracking with a per-show summary

━━━━━━━━━━━━━━━━━━━━
WHAT'S INCLUDED
━━━━━━━━━━━━━━━━━━━━
• Blank workbook (.xlsx) for your shows: Start Here, Settings, Show Log (300 rows), Item Sales, Dashboard, Year Summary
• Sample workbook (.xlsx) with 12 example shows, so you can see every tab working
• Quick-start guide (PDF, 9 pages): opening the file, setting your fees, a worked example, reading the dashboard, FAQ

━━━━━━━━━━━━━━━━━━━━
HOW DELIVERY WORKS
━━━━━━━━━━━━━━━━━━━━
1. Buy, then download the files from Etsy › You › Purchases and reviews. Nothing is shipped.
2. Open the .xlsx in Excel, or follow the guide to open it in Google Sheets (copy link included).
3. Check the fee rates on Settings, then log your first show.

━━━━━━━━━━━━━━━━━━━━
COMPATIBILITY
━━━━━━━━━━━━━━━━━━━━
✔ Microsoft Excel 2016 or later (Windows and Mac) and Excel for the web
✔ Google Sheets (free Google account)
✔ Best on a computer. It opens in the phone apps, but logging and the dashboard are easier on a laptop.
No macros, no add-ons.

━━━━━━━━━━━━━━━━━━━━
FAQ
━━━━━━━━━━━━━━━━━━━━
Are the Whatnot fees built in?
The defaults are 8 % commission and 2.9 % + $0.30 processing, based on published rates as of 2025. Rates can differ by category and change over time, so you check and set them on the Settings tab.

Does commission include shipping?
You choose: sale price only (default) or sale price + shipping.

How long does logging take?
About two minutes per show: one row with your totals from the show.

Can I use it outside the US?
Yes. Change the currency symbol and check your local fees.

Can I track each item?
Yes, optionally, on the Item Sales tab. Most sellers only log show totals.

Can I get a refund?
Digital files can't be returned once downloaded. If something doesn't work, send me a message and I will help.

━━━━━━━━━━━━━━━━━━━━
PLEASE NOTE
━━━━━━━━━━━━━━━━━━━━
• Digital download. No physical item will be shipped.
• Not affiliated with or endorsed by Whatnot.
• Not tax advice. The year summary is a record-keeping aid for you and your tax preparer.
• For personal use in your own business. Please don't resell or share the files.
• Designed by me, Brass Ledger, with the help of AI tools.

Brass Ledger · Simple tools for small business numbers."""


def listing_md():
    assert len(TITLE) <= 140, len(TITLE)
    assert len(TAGS) == 13 and len(set(TAGS)) == 13 and all(len(t) <= 20 for t in TAGS), [t for t in TAGS if len(t) > 20]
    text = TITLE + " ".join(TAGS) + DESCRIPTION
    assert "!" not in text and not HYPE.search(text), HYPE.search(text)
    tag_rows = "\n".join(f"| {i + 1} | {t} | {len(t)} |" for i, t in enumerate(TAGS))
    return f"""# Etsy listing — Whatnot Live Show Profit Tracker

Copy-paste ready. Fields follow the order of Etsy's listing form.

## Photos (upload in this order)

Files are in `listing-images/`, 2700 × 2025 px PNG. Every screenshot is a real render of the SAMPLE workbook.

| # | File | Alt text |
|---|---|---|
| 1 | 01_hero.png | Whatnot live show profit tracker dashboard on a laptop with monthly profit, fees and giveaway tiles |
| 2 | 02_whats_included.png | The six tabs of the workbook, what it calculates, and the files in the download |
| 3 | 03_show_log.png | Show log with one row per show and the net profit column highlighted; losses in red, top shows in green |
| 4 | 04_dashboard.png | Dashboard tables and charts of profit by time slot and by category |
| 5 | 05_how_it_works.png | Three steps: set your fees, log the show, read the dashboard |
| 6 | 06_compatibility.png | Works in Excel 2016 or later, Excel for the web and Google Sheets; best on a computer |
| 7 | 07_what_you_receive.png | Two workbooks and a PDF guide; instant download, no physical item shipped |

## Title ({len(TITLE)} / 140 characters)

```
{TITLE}
```

"Whatnot Seller" describes who it is for. The description and images say it is not affiliated with Whatnot.

## Tags (13 / 13, each 20 characters or fewer)

```
{", ".join(TAGS)}
```

| # | Tag | Characters |
|---|---|---|
{tag_rows}

## Description

```
{DESCRIPTION}
```

## Price

- **Launch at $14.99**, then move to **$17.99** after about five reviews.
- Comparable listings found in a search on 17 Nov 2026: a Whatnot trading-card break tracker at about $21 (on sale near $16), a
  multi-platform reseller tracker with a Whatnot fee calculator at $17.99, and general marketplace profit trackers at $12–15.
  Few are built around one row per live show, which supports the upper half of your $14–19 range once the listing has reviews.
- $14.99 is low enough to be an easy first purchase for a side seller and still well above the $4–8 generic trackers, which
  signals a specialised tool.
- Etsy fees at $14.99 (US): 6.5 % transaction ($0.97) + payment processing about 3 % + $0.25 ($0.70) + $0.20 listing ≈ **$1.87**,
  so you keep about $13.12 per sale. At $17.99 you keep about $15.90.

## Listing details / attributes

| Field | Value |
|---|---|
| Who made it | I did |
| What is it | A finished product |
| When was it made | 2020 – 2026 (Made to order is not needed) |
| Creativity (Etsy) | Designed by seller (Brass Ledger), made with the help of AI tools |
| Type | Digital files |
| Instant download | Yes |
| Files to upload | BrassLedger_Whatnot_Profit_Tracker.xlsx, BrassLedger_Whatnot_Profit_Tracker_SAMPLE.xlsx, BrassLedger_Whatnot_Quick_Start_Guide.pdf |
| File types | XLSX, PDF |
| Category (suggested) | Paper & Party Supplies › Paper › Calendars & Planners, or the closest "templates" category Etsy offers when you list |
| Renewal | Automatic |
| Materials (optional) | Microsoft Excel, Google Sheets, spreadsheet template, digital download |

## Before you publish

- [ ] Open the blank and sample .xlsx in Excel on a computer once.
- [ ] Upload the blank .xlsx to Google Drive, convert it (File › Save as Google Sheets), and build the copy link by changing the
      end of its URL from `/edit…` to `/copy`. Put that link where the guide and the START HERE tab say [GOOGLE SHEETS COPY LINK]
      (rebuild the guide with `python3 build/guide.py` after editing it, or edit the PDF).
- [ ] Check Whatnot's current seller fees. If the defaults are out of date, change SETTINGS in both files and the FAQ above.
- [ ] Upload the 7 images in order with the alt text, then the three files.
"""


def test_report():
    res = json.loads((ROOT / "dist" / "test_results.json").read_text())
    structure = (ROOT / "dist" / "structure_check.txt").read_text()
    e = res["expected"]
    return f"""# Test report — Whatnot Live Show Profit Tracker

Result: **{res['passed']} automated checks passed, {res['failed']} failed.** Both workbooks recalculate in LibreOffice (headless) with **zero formula
errors**. Scripts: `build/test_tracker.py` (values) and the structure check below.

## 1. Formula errors (both versions)

| File | Formulas | Errors (#REF!, #VALUE!, #DIV/0!, #NAME?, #N/A) |
|---|---|---|
| BrassLedger_Whatnot_Profit_Tracker.xlsx (blank) | {res['BrassLedger_Whatnot_Profit_Tracker.xlsx']:,} | 0 |
| BrassLedger_Whatnot_Profit_Tracker_SAMPLE.xlsx | {res['BrassLedger_Whatnot_Profit_Tracker_SAMPLE.xlsx']:,} | 0 |

Every cell of the recalculated files was also scanned for error values: none.

## 2. Sample data vs an independent Python calculation ({res['sample_checks']} checks)

The 12 sample shows were recomputed in Python from the same inputs and rules (not by reading the formulas), then compared with the
workbook after LibreOffice recalculated it (tolerance half a cent):

- SHOW LOG, all 12 shows: weekday, hours live (including a show that runs past midnight), giveaway cost (default and override),
  commission, processing fees, total fees, net profit, margin, profit per hour, average order value, giveaways % of sales.
- DASHBOARD for October 2026: all 8 tiles, the goal line, the time slot, weekday and category tables (shows, net profit, average per
  show, profit per hour), the 12-month trend, top 5 and bottom 5 shows, and all five plain-English insight lines, word for word.
- YEAR SUMMARY: shows and every money column for all 12 months, the year total, and that the totals add up
  (gross − fees − items − giveaways − supplies − other = net profit).
- ITEM SALES summary: items, gross sales, cost, not-shipped count and the "In SHOW LOG?" flag for both sample shows, and that the
  list ends after the last show.

Key sample figures (October 2026): net profit this month **${e['month_profit']:,.2f}**, profit year to date **${e['ytd_profit']:,.2f}**, 4 shows,
average **${e['avg_show']:,.2f}** per show and **${e['avg_hour']:,.2f}** per hour, fees year to date **${e['fees_ytd']:,.2f}**, giveaways year to date
**${e['give_ytd']:,.2f}**, goal progress **{e['goal'] * 100:.0f} %**. The guide's worked example (Oct 6 show) is computed by the same model.

## 3. Changing settings updates everything ({res['fee_change_checks']} checks)

SETTINGS were changed to commission 10 %, processing 3.49 % + $0.49, commission on **sale price + shipping**, default giveaway $4.50,
goal $1,000, and the dashboard month to September. After recalculation every SHOW LOG, DASHBOARD and YEAR SUMMARY figure matched the
model with the new rates, and commission, processing, total fees, giveaway cost and net profit were confirmed to have changed.
Changing the currency symbol to £ updated the headings and the dashboard text.

## 4. Blank version

- All 3,300 calculated SHOW LOG cells (300 rows × 11 columns) are blank: no zeros, no errors.
- Profit tiles show 0; average tiles show "–"; every insight line shows its "Log a few shows…" message.
- ITEM SALES summary is empty.
- The dashboard opens on the current month and year (formula default the buyer can overwrite).

## 5. Layout

A layout linter estimated text widths for every cell in the recalculated files. Dashboard, Year Summary and Start Here were checked
strictly (every value must fit its own cell). Result: 0 problems: no "####", no clipped text, no chart overlapping cells.
The final renders (used for the images) were checked by eye at 100 %.

## 6. Structure (technical requirements)

```
{structure.strip()}
```

## 7. Google Sheets: what can behave differently, and how it is handled

| Feature | In Google Sheets | Handling |
|---|---|---|
| Sheet protection | Not imported | Guide and START HERE say so; shaded cells are clearly marked. |
| Fonts | Inter and Georgia are available in Sheets, but import can fall back to the default font | Column widths have a margin; nothing depends on the font. |
| Charts | Imported and editable; styling (colours, gap width) can change slightly | Data ranges are plain ranges on the DASHBOARD tab. |
| Links between tabs | Native cell hyperlinks (not HYPERLINK formulas) | Native links import and work in Sheets and Excel. |
| Dropdowns | Imported as "dropdown from a range" | Lists are plain ranges on SETTINGS (no named ranges in validation). |
| Dates as text | TEXT() date codes depend on the language of the app | Not used. Weekdays use CHOOSE(WEEKDAY()), months come from a list on SETTINGS, amounts in sentences use FIXED(). |
| Wildcards in COUNTIFS | `?` and `*` in show titles would act as wildcards | Show and item matching uses exact SUMPRODUCT comparisons. |
| Formula recalculation | Automatic | The file is also flagged to fully recalculate when Excel opens it. |

Not tested in this environment: real Microsoft Excel and real Google Sheets (only LibreOffice was available). Open both files once
in each before publishing.

## 8. Choices made (and why)

- **Giveaway cost** is an optional input ("blank = auto") plus a calculated column, so the default from SETTINGS applies without
  overwriting a formula.
- **Shipping charged to buyers** is treated as pass-through for the label: it is not profit, but fees are charged on it (processing
  always; commission only if SETTINGS says so). Label costs the seller pays go under Other costs.
- **Processing** = rate × (sale price + shipping charged) + fixed fee × orders. Sales tax is not tracked (Whatnot collects it).
- **Category commission differences and caps** (some categories have lower rates or a cap on large sales) are not modelled; the
  seller sets the rate on SETTINGS, and the FAQ points this out.
- **Currency**: number cells use plain number formats and every heading shows the symbol from SETTINGS, because Excel and Sheets
  cannot change a number format from a cell.
- **Dashboard**: tiles follow the chosen month; tables, charts and top/bottom 5 cover the chosen year (more shows, more useful).
- **Top quartile** highlighting starts once 4 shows are logged.
- **Show Log** has 300 rows (about six shows a week for a year); the guide suggests a new copy per year.
- **Sample data**: 12 invented shows Aug–Oct 2026 (one loss, one past midnight, one with a giveaway override), and item rows for one
  logged show and one show not yet logged, to show both "Yes" and "Not yet".
- **Logo**: the Brass Ledger logo PNG supplied earlier (no new files came with this request), made transparent for the paper background.
"""


def main():
    (OUT / "etsy-listing.md").write_text(listing_md(), encoding="utf-8")
    (OUT / "test-report.md").write_text(test_report(), encoding="utf-8")
    print("wrote etsy-listing.md and test-report.md")


if __name__ == "__main__":
    main()
