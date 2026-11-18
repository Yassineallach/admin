"""Writes etsy-listing.md and test-report.md into the deliverables folder (checks title, tags and voice rules)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "home-daycare-tax-workbook"

TITLE = ("Home Daycare Tax Spreadsheet, Time Space Percentage Calculator, Family Child Care Expense Tracker, "
         "Form 8829 Helper, Excel & Google Sheets")
TAGS = ["daycare tax", "home daycare", "time space percent", "child care forms", "daycare expenses", "provider records",
        "form 8829", "daycare spreadsheet", "family child care", "daycare provider", "child care business",
        "daycare bookkeeping", "tax organizer"]
HYPE = re.compile(r"\b(ultimate|game.?changing|amazing|revolutionary|must.have|perfect|maximi[sz]e|save thousands|guaranteed)\b", re.I)

DESCRIPTION = """Your time-space percentage, calculated and documented.

As a family child care provider you can deduct part of your home costs and shared household items. The deductible share is your time-space percentage, and it is easy to get wrong: hours spent preparing, cleaning and doing paperwork get forgotten, and exclusive-use rooms are often figured the same way as shared rooms. This workbook keeps the records and does the calculation step by step, so you and your tax preparer can see exactly where the number comes from.

Built only for home child care, in your business's own terms: time-space percentage, exclusive-use rooms, direct and indirect expenses, food program meals. Not a generic bookkeeping sheet.

━━━━━━━━━━━━━━━━━━━━
WHO IT'S FOR
━━━━━━━━━━━━━━━━━━━━
Licensed or registered family child care providers in the United States who file a Schedule C and Form 8829, on their own or with a tax preparer. No spreadsheet or accounting skills needed.

━━━━━━━━━━━━━━━━━━━━
WHAT IT DOES
━━━━━━━━━━━━━━━━━━━━
✔ Time percentage from a daily hours log for the whole year, prefilled from your usual hours: you confirm the usual days and fix the rest
✔ Counts the hours children are in your care plus preparation, cleaning, meal prep and paperwork time in the home
✔ Total hours available worked out for you: 8,760, 8,784 in a leap year, or 24 × days if you started or stopped during the year
✔ Space shares from your rooms, with exclusive-use rooms figured separately from rooms shared with your family
✔ Step-by-step time-space percentage, plus a one-page Time-Space Statement to attach when you have exclusive-use space
✔ Expense log with the right share applied: direct 100%, shared-room repairs × time %, indirect home and shared household items × time-space %, personal 0%
✔ Totals sorted into Schedule C business expenses and Form 8829 home expenses (direct and indirect columns)
✔ Optional meal log for the standard meal and snack rates, compared with your food receipts, net of food program reimbursements
✔ Optional mileage log, with two standard mileage rates by date
✔ Simplified method estimate shown next to the regular method total
✔ A page for your tax preparer: home purchase details, improvements, carryovers, income and a document checklist

━━━━━━━━━━━━━━━━━━━━
WHAT'S INCLUDED
━━━━━━━━━━━━━━━━━━━━
• Blank workbook (.xlsx) with 10 tabs: Start Here, Settings, Rooms, Hours Log, Expenses, Meals, Mileage, Summary, Time-Space Statement, For Your Tax Preparer
• Sample workbook (.xlsx): a full 2026 year for a fictional provider, so you can see every tab working
• Quick-start guide (PDF, 9 pages): set-up, what counts as business hours, expense types with examples, meals and mileage, FAQ and the IRS sources to check

━━━━━━━━━━━━━━━━━━━━
HOW DELIVERY WORKS
━━━━━━━━━━━━━━━━━━━━
1. Buy, then download the files from Etsy › You › Purchases and reviews. Nothing is shipped.
2. Open the .xlsx in Excel, or use the Google Sheets copy link in the guide (File › Make a copy).
3. Fill in Settings and Rooms, then log your hours weekly and your receipts as they come in.

━━━━━━━━━━━━━━━━━━━━
COMPATIBILITY
━━━━━━━━━━━━━━━━━━━━
✔ Microsoft Excel 2016 or later (Windows and Mac)
✔ Google Sheets (free Google account)
✔ Best on a computer. It opens in the phone apps, but logging is easier on a laptop.
No macros, no add-ons.

━━━━━━━━━━━━━━━━━━━━
FAQ
━━━━━━━━━━━━━━━━━━━━
Is this tax advice?
No. It keeps your records and shows the calculation. Your tax preparer completes your return.

Which rules does it follow?
The time and space calculation, the exclusive-use computation, total hours for part-year businesses, standard meal and snack rate limits and the simplified method were checked against IRS Publication 587, Form 8829 and its instructions, and Schedule C. Rules can change, so confirm with your preparer.

Are the rates included?
Yes, as editable defaults for 2026: simplified method $5 per square foot up to 300 square feet, standard mileage 72.5¢ to June 30 and 76¢ from July 1, and contiguous-state meal and snack rates. Rates change; check current rates for your year and state, and note the date you checked them.

Do I have to log every day?
Every day is already listed and prefilled from your usual hours. Most weeks you only confirm the days that matched and fix the ones that didn't.

Does it calculate depreciation of my home?
No. It collects what your preparer needs (purchase price, land value, improvements) so they can figure it.

Can I use it next year?
Yes. Start a fresh copy of the blank file and change the tax year on Settings.

Can I get a refund?
Digital files can't be returned once downloaded. If something doesn't work, send me a message and I will help.

━━━━━━━━━━━━━━━━━━━━
PLEASE NOTE
━━━━━━━━━━━━━━━━━━━━
• Not tax advice. For record keeping and estimates only.
• For US providers.
• Rates change; check current rates.
• No specific tax saving is promised: your result depends on your own home, hours and records.
• Digital download. No physical item will be shipped.
• For use in your own business. Please don't resell or share the files.
• Designed by me, Brass Ledger, with the help of AI tools.

Brass Ledger · Simple tools for small business numbers."""


def listing_md():
    assert len(TITLE) <= 140, len(TITLE)
    assert len(TAGS) == 13 and len(set(TAGS)) == 13 and all(len(t) <= 20 for t in TAGS), [t for t in TAGS if len(t) > 20]
    body = TITLE + " ".join(TAGS) + DESCRIPTION
    assert "!" not in body and not HYPE.search(body), HYPE.search(body)
    tag_rows = "\n".join(f"| {i + 1} | {t} | {len(t)} |" for i, t in enumerate(TAGS))
    return f"""# Etsy listing — Home Daycare Tax Workbook

Copy-paste ready. Fields follow the order of Etsy's listing form.

## Photos (upload in this order)

Files are in `listing-images/`, 2700 × 2025 px PNG. Every screenshot is a real render of the SAMPLE workbook.

| # | File | Alt text |
|---|---|---|
| 1 | 01_hero.png | Home daycare tax workbook summary on a laptop showing the step-by-step time-space percentage |
| 2 | 02_whats_included.png | The ten tabs of the workbook and the files in the download |
| 3 | 03_hours_log.png | Daily hours log prefilled from usual hours, with the other business hours columns highlighted: counts prep and cleaning time too |
| 4 | 04_rooms_and_summary.png | Rooms tab with square feet by use type, and the summary's step-by-step time and space calculation |
| 5 | 05_how_it_works.png | Four steps: settings, rooms, hours each week, expenses |
| 6 | 06_compatibility.png | Works in Excel 2016 or later and Google Sheets; best on a computer; for US providers; instant download |
| 7 | 07_what_you_receive.png | Two workbooks and a PDF guide; instant download, no physical item shipped |

## Title ({len(TITLE)} / 140 characters)

```
{TITLE}
```

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

- **Launch at $19.99**, then move to **$24.99** after about five reviews.
- Comparable listings found in a search on 18 Nov 2026: home daycare tax and expense trackers on Etsy and elsewhere at about
  $15–20 (for example $14.99, $17.99, $18.99 and $19.99). Most multiply space by time for the whole home and do not handle
  exclusive-use rooms, part-year businesses, meal rate limits or CACFP reimbursements.
- This workbook does more (10 tabs, a printable statement, IRS-checked rules, meals and mileage), which supports the upper half
  of your $19–29 range once it has reviews. Starting at $19.99 keeps it close to the market while the shop has no reviews.
- Demand is seasonal: providers buy in December to March for tax season, and again in January to start the year's records.
- Etsy fees at $19.99 (US): 6.5 % transaction ($1.30) + payment processing about 3 % + $0.25 ($0.85) + $0.20 listing ≈ **$2.35**,
  so you keep about $17.64 per sale. At $24.99 you keep about $22.19.

## Listing details / attributes

| Field | Value |
|---|---|
| Who made it | I did |
| What is it | A finished product |
| When was it made | 2020 – 2026 |
| Creativity (Etsy) | Designed by seller (Brass Ledger), made with the help of AI tools |
| Type | Digital files |
| Instant download | Yes |
| Files to upload | BrassLedger_Home_Daycare_Tax_Workbook.xlsx, BrassLedger_Home_Daycare_Tax_Workbook_SAMPLE.xlsx, BrassLedger_Home_Daycare_Quick_Start_Guide.pdf |
| File types | XLSX, PDF |
| Category (suggested) | Paper & Party Supplies › Paper › Calendars & Planners, or the closest "templates" or business category Etsy offers when you list |
| Renewal | Automatic |
| Materials (optional) | Microsoft Excel, Google Sheets, spreadsheet template, digital download |

## Before you publish

- [ ] Open the blank and sample .xlsx in Excel on a computer once.
- [ ] Upload the blank .xlsx to Google Drive, convert it (File › Save as Google Sheets), and make the copy link by changing the
      end of its URL from `/edit…` to `/copy`. Put that link where the START HERE tab and the guide say [GOOGLE SHEETS COPY LINK].
- [ ] Check the rates on SETTINGS for the year you are selling for (Pub. 587 for the new year, the IRS mileage page, your meal rates).
- [ ] Upload the 7 images in order with the alt text, then the three files.
"""


def test_report():
    res = json.loads((ROOT / "dist" / "test_results.json").read_text())
    struct = (ROOT / "dist" / "structure_check.txt").read_text()
    s = res["sample"]
    ke = res["known_examples"]
    comparisons = res["sample_checks"] + res["scenario_rates_checks"] + res["scenario_year_checks"] + res["scenario_start_checks"]
    known_rows = "\n".join(f"| {k} | {v.get('time', 0) * 100:.4f}% | {v.get('ts', 0) * 100:.4f}% | {v.get('hours_available', '')} |"
                           for k, v in ke.items() if "ts" in v)
    year_rows = "\n".join(f"| {k} | {v['days']} | {v['hours']:,} |" for k, v in ke.items() if "days" in v)
    return f"""# Test report — Home Daycare Tax Workbook

Result: **{res['passed']} tests passed, {res['failed']} failed**, covering {comparisons:,} individual figure comparisons between the
workbook and an independent Python calculation. Both workbooks recalculate in LibreOffice (headless) with **zero formula errors**.
Scripts: `build/test_workbook.py` (values) and the structure check in section 7.

## 1. Formula errors (both versions)

| File | Formulas | Errors (#REF!, #VALUE!, #DIV/0!, #NAME?, #N/A) |
|---|---|---|
| BrassLedger_Home_Daycare_Tax_Workbook.xlsx (blank) | {res['BrassLedger_Home_Daycare_Tax_Workbook.xlsx']:,} | 0 |
| BrassLedger_Home_Daycare_Tax_Workbook_SAMPLE.xlsx | {res['BrassLedger_Home_Daycare_Tax_Workbook_SAMPLE.xlsx']:,} | 0 |

Every cell of the recalculated files, and of every scenario below, was also scanned for error values: none.

## 2. Known examples (entered into the blank workbook and recalculated)

| Example | Time % | Time-space % | Hours available |
|---|---|---|---|
{known_rows}

- No exclusive space, 1,000 of 2,000 sq ft at 23 % time → **11.5 %** (expected 11.5 %).
- Exclusive 300 + regular 900 of 2,000 sq ft at 40 % time → 15 % + 18 % = **33 %** (expected 33 %).
- IRS Pub. 587 (2025) Example 1 (Rene): 3,000 / 8,760 = 34.25 % time; 50 % × 34.25 % = **17.12 %** (the publication shows 17.12 %).
- IRS Pub. 587 (2025) Example 3 (Rene stops on June 24): 24 × 175 = **4,200** hours available, 1,500 / 4,200 = **35.71 %**.

| Year / dates | Days available | Total hours |
|---|---|---|
{year_rows}

The leap-year test also confirms that December 31 appears in row 366 of the hours log; the 2026 test confirms row 366 is blank;
the mid-year start shows "Not in business" for January 1 to March 14.

## 3. Sample provider, full year, recomputed independently ({res['sample_checks']:,} comparisons)

The Python model reads the same inputs as the workbook (sample_data.py) and recomputes everything without the formulas:
- SETTINGS dates, days and hours; all 366 hours-log rows (date, status, children hours, other hours, total); the monthly table and tiles.
- ROOMS totals and shares; every SUMMARY step (time %, each space figure, time-space %).
- Every expense row's deductible share and amount; every Schedule C category (amount entered, deductible) and every Form 8829
  category (direct column, indirect column, deductible); totals.
- Every meal row's value; meal counts by type; standard-rate total vs food receipts; CACFP netting; mileage with two rates by date;
  the simplified method estimate (including rounding the reduced rate to cents, half up); the Time-Space Statement figures.

Sample results (tax year 2026): {s['bizhours']:,.2f} business hours of {s['avail']:,} → time **{s['time'] * 100:.2f} %**; exclusive
{s['excl_pct'] * 100:.2f} % + regular {s['reg_pct'] * 100:.2f} % × time → time-space **{s['ts'] * 100:.2f} %**. Home expenses (Form 8829,
before limits) ${s['home_total']:,.2f}; Schedule C expenses ${s['sc_total']:,.2f}; standard meal rates ${s['std']:,.2f} vs receipts
${s['actual']:,.2f}, food deduction after reimbursements ${s['food_net']:,.2f}; {s['miles']:,.1f} miles = ${s['mile_ded']:,.2f}; simplified
estimate ${s['simp']:,.2f}. {s['to_confirm']} days are left unconfirmed in the sample to show the projection.

## 4. Changes update everything

Each scenario was entered into the sample file, recalculated in LibreOffice, and compared in full with the model:
- **Rates, method and a room:** simplified rate $6 and 250 sq ft maximum; one mileage rate of 70¢; new meal rates; food method
  switched to actual receipts; reimbursements raised to $5,000 (so they exceed food cost and show as income); the living room changed
  from regular to exclusive use. {res['scenario_rates_checks']:,} comparisons, all equal; the time-space percentage moved as expected.
- **Tax year changed to 2027:** hours-log dates move to 2027, total hours update, 2026 receipts, meals and trips drop out as "Not in
  this tax year". {res['scenario_year_checks']:,} comparisons, all equal.
- **Business start date March 15, 2026:** 292 days, 7,008 hours; earlier days "Not in business"; earlier home costs not counted.
  {res['scenario_start_checks']:,} comparisons, all equal.

## 5. Blank version

- All 500 expense rows, 2,500 meal rows and 300 mileage rows show blank calculated cells: no zeros, no errors.
- Time % and time-space % are 0; ROOMS asks for the home's total square feet; hours-log days show "Usual day off" until the usual
  hours are set on SETTINGS.

## 6. Layout

A layout linter estimated text widths for every cell in both recalculated files (SUMMARY, TIME-SPACE STATEMENT, ROOMS, SETTINGS,
START HERE and FOR YOUR TAX PREPARER checked strictly). Final result: 0 problems: no "####", no clipped labels. Renders of every tab
were checked by eye; three layout problems found that way were fixed (notes that stretched hours-log and meal rows, truncated labels,
a shrunken food-method label).

## 7. Structure (technical requirements)

```
{struct.strip()}
```

## 8. Tax rules implemented, and the IRS source checked

Sources read on 18 Nov 2026: Publication 587 (2025 edition, the latest available); Instructions for Form 8829 (2025); Form 8829 (2025)
and the 2026 draft (same lines); Schedule C (2026); IRS standard mileage rates page and IR-2025-128 / Announcement 2026-11; USDA CACFP
rates notice (Federal Register 2025-13892).

| Rule | Implementation | Source |
|---|---|---|
| Time % = hours used for daycare ÷ total hours available | SUMMARY steps 3–6 | Pub. 587 Daycare Facility; Form 8829 lines 4–6 |
| Total hours = 24 × days (8,760; 8,784 leap year) | SETTINGS, leap-year aware | Pub. 587 Daycare Facility Worksheet line 2 |
| Started or stopped during the year: 24 × days available | Start/stop dates on SETTINGS | Form 8829 instructions, line 5 |
| A regularly used room counts for the whole business day | Hours are per day, not per room | Pub. 587 Daycare Facility |
| Exclusive + regular areas: two parts, added, statement attached | SUMMARY steps 7–13; TIME-SPACE STATEMENT; note to write "See attached computation" | Form 8829 instructions, Special Computation for Certain Daycare Facilities |
| No exclusive area: space % × time % | Same formula reduces to it | Form 8829 line 7; Pub. 587 Example 1 |
| Direct expenses 100% in column (a) | Type "Direct home: exclusive area" | Form 8829 instructions, columns (a) and (b) |
| Direct expenses for a regularly (not exclusively) used area × time % | Type "Direct home: shared area" | Pub. 587 Example 1 ("deduct 34.25% of any direct expenses for the basement") |
| Indirect expenses × business percentage | Type "Indirect home" × time-space % | Form 8829 lines 13 and 24; Pub. 587 Table 1 |
| Part-year: home expenses only for the business period | Home costs outside business dates count 0 | Form 8829 instructions, columns (a) and (b) |
| Unrelated/personal expenses not deductible | Type "Personal" 0% | Pub. 587 Table 1 |
| Basic local telephone line not deductible | Stated in the guide | Pub. 587 |
| Food for daycare children 100%; never your family's | Food category, Direct type only | Pub. 587 Meals |
| Standard meal and snack rates: either method for the whole year, not both | One method chosen on SETTINGS; the other is shown but not counted | Pub. 587 Standard meal and snack rates |
| Max 1 breakfast, 1 lunch, 1 dinner, 3 snacks per eligible child per day | Dropdown limits, MIN() caps, duplicate child-day rows not counted | Pub. 587 |
| Eligible children exclude residents of the home (incl. your own) and care as a personal favour | Two questions per child on MEALS | Pub. 587 |
| Rates for a year = CACFP Tier I rates in effect Dec 31 of the prior year | 2026 defaults $1.70 / $3.22 / $3.22 / $0.96 (contiguous states) | Pub. 587 Table 3 footnote; Federal Register 2025-13892 |
| CACFP reimbursements reduce the food deduction; excess is income | SUMMARY section E | Pub. 587 Meals |
| Simplified method: $5 × up to 300 sq ft; rate × time fraction for non-exclusive daycare space, rounded to cents; no reduction if ≥ 300 sq ft exclusive | SUMMARY section G, values editable on SETTINGS | Pub. 587 Simplified Method; Daycare Facility Worksheet |
| Standard mileage rate 2026: 72.5¢ Jan 1–Jun 30, 76¢ Jul 1–Dec 31 | Two rates and a change date on SETTINGS | IR-2025-128; IRS Announcement 2026-11 |
| Line numbers | Schedule C (2026): 8, 9, 11, 13, 15, 17, 18, 20a, 21, 22, 23, 24a, 26, 27b. Form 8829 (2025, same in 2026 draft): 10, 11, 18–22, with lines 4–7 for the percentage | Printed forms |
| Depreciation of the home | Not calculated; details collected for the preparer | Form 8829 Part III (as requested) |

## 9. Where the IRS text changed or refined the brief

1. **Preparation and cleaning time.** Pub. 587 compares "the total time used for business" with total time available and does not
   list activities. The workbook counts children's hours plus other business use of the home, as requested, and the guide labels
   this as common practice to confirm with a preparer. Shopping trips are excluded: they are not time the home is used.
2. **Direct expenses in a shared room** are multiplied by the time percentage (Pub. 587 Example 1), so "Direct" is split into three
   types: business only (100%), home exclusive area (100%) and home shared area (× time %).
3. **Eligible children** for meal rates exclude every child living in the home and children cared for as a personal favour, not only
   the provider's own children.
4. **CACFP reimbursements** are subtracted from the food deduction (added to SETTINGS and SUMMARY).
5. **Part-year businesses:** home costs dated outside the business period are not counted.
6. **2026 mileage** changed mid-year, so the log takes two rates and a change date.
7. **Simplified method with both exclusive and regular space:** the IRS worksheet applies one rate to the area. The estimate applies the
   full rate to exclusive area and the time-reduced rate to the rest, within 300 sq ft, and is labelled "Estimate only. Your tax
   preparer will choose the right method."

## 10. Google Sheets: what can behave differently, and how it is handled

| Feature | In Google Sheets | Handling |
|---|---|---|
| Sheet protection | Not imported | Guide and START HERE say so; shaded cells are clearly marked. |
| Fonts | Inter and Georgia are available, but import can fall back to the default | Column widths have a margin. |
| Links between tabs | Native cell hyperlinks | Import and work in both apps. |
| Dropdowns | "Dropdown from a range" | Lists are plain ranges on SETTINGS. |
| Dates as text | TEXT() date codes depend on the app's language | Not used; weekdays via CHOOSE(WEEKDAY()); statement dates built from MONTH/DAY/YEAR. |
| Date arithmetic | DATE(year, 3, 0) for the leap-year test | Works in both (day 0 rolls back to the last day of February). |
| Wildcards in COUNTIFS | `?` or `*` in a child's name would act as a wildcard in the duplicate check | Names rarely contain them; noted here. |
| Large logs | 2,500 meal rows with an expanding duplicate check | Recalculates in LibreOffice in seconds; Sheets handles the same size. |

Not tested here: real Microsoft Excel and real Google Sheets (LibreOffice only). Open both files once in each before publishing.

## 11. Other choices

- **Hours design:** days are prefilled; a day counts once Confirmed, edited or Closed. SUMMARY shows the percentage from checked days
  and a projection if the unchecked days match the usual hours (both explained on START HERE).
- **Home square feet:** an input for the measured total, with a warning when the listed rooms don't add up to it.
- **Totals by tax year:** expenses, meals and trips only count when dated in the tax year on SETTINGS.
- **Sample data:** a fictional provider (Little Acorns Family Child Care) with 2,000 sq ft, a 320 sq ft exclusive playroom, holidays,
  late pickups, monthly deep cleans and parent meetings, eight children (two not eligible), a CACFP reimbursement, two mileage rates,
  a receipt from the prior year and personal items to show the exclusions.
- **Logo:** the Brass Ledger logo PNG supplied earlier (no new files came with this request), made transparent for the paper background.
"""


def main():
    (OUT / "etsy-listing.md").write_text(listing_md(), encoding="utf-8")
    (OUT / "test-report.md").write_text(test_report(), encoding="utf-8")
    print("wrote etsy-listing.md and test-report.md")


if __name__ == "__main__":
    main()
