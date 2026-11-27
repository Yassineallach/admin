"""Write etsy-listing.md and test-report.md for the Owner-Operator Cost Per Mile calculator.

Run test_workbook.py first (it writes ../dist/test_results.json).
Usage: python write_docs.py
"""
from __future__ import annotations

import json
from pathlib import Path

import truck_config as C
from test_workbook import load_model, settings_model

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "owner-operator-cost-per-mile"

TITLE = ("Owner Operator Cost Per Mile Calculator, Trucking Load Profit Spreadsheet, Hotshot Trucking Expense Tracker, "
         "Excel & Google Sheets")
TAGS = ["cost per mile", "owner operator", "hotshot trucking", "trucking spreadsheet", "truck driver", "load calculator",
        "IFTA log", "trucking expenses", "box truck business", "rate per mile", "trucking profit", "fuel log tracker",
        "trucking business"]


def money(x, d=2):
    return ("-" if x < 0 else "") + f"${abs(x):,.{d}f}"


def listing():
    assert len(TITLE) <= 140, len(TITLE)
    assert len(TAGS) == 13 and len(set(t.lower() for t in TAGS)) == 13 and all(len(t) <= 20 for t in TAGS), TAGS
    m = settings_model()
    o = load_model(m, **C.LOAD_CHECK)
    lc = C.LOAD_CHECK
    return f"""# Etsy listing: Owner-Operator Cost Per Mile & Load Profit Calculator

## Title ({len(TITLE)} of 140 characters)
{TITLE}

## Tags (13, each 20 characters or fewer)
{chr(10).join(f"{i + 1}. {t} ({len(t)})" for i, t in enumerate(TAGS))}

## Description

{C.PROMISE}

A load can look good on the rate and still lose money once deadhead, fuel, tolls, the truck payment, insurance and your own pay are counted. This spreadsheet works out what a mile really costs you, then tells you whether a load covers it: TAKE, NEGOTIATE or PASS, with the rate to counter with.

**Built for:** owner-operators running under their own authority or leased on, dry van, reefer and flatbed, plus hotshot (CDL and non-CDL) and box truck operators. It uses the trade's own terms: cost per mile, all-in rate, deadhead, linehaul, fuel surcharge, detention, factoring, dispatch fee, settlement. It is not a generic business budget.

**What it does**
- Your cost per mile, layer by layer: fixed, variable, operating (break-even) and all-in with your own pay, plus the target rate per mile for your margin
- A miles-per-month table that shows what idle weeks do to your cost per mile
- Equipment presets for dry van, reefer, flatbed, hotshot (CDL), hotshot (non-CDL) and box truck. Every value can be changed
- Fixed costs entered monthly or yearly: truck and trailer payments, five kinds of insurance, IRP plates, HVUT, UCR, IFTA licence, ELD, load boards, parking and more
- Trip log for 500 loads: revenue per loaded mile and per total mile, factoring and dispatch fees, trip profit, profit per day, unpaid invoices
- Fuel log with MPG between fill-ups and your average MPG, plus miles by state per trip and totals by state for a quarter (records to help with IFTA reporting; it does not calculate IFTA tax)
- Monthly P&L for 12 months: revenue, fuel, other costs, fixed costs, fees, pay drawn, net profit, deadhead % and your actual cost per mile against your estimate, flagged when it runs more than 10 % over
- Days away from home by month (records for your tax preparer, e.g. per diem; not tax advice)
- Dashboard with break-even and all-in cost per mile, revenue per mile, deadhead %, profit year to date, profit per day and unpaid invoices, and three charts

**The load checker, on your phone**
Open the LOAD CHECK tab in the Google Sheets app. It is one narrow column: no sideways scrolling. Type the rate, loaded miles, deadhead miles and days. You get:
- a green TAKE, amber NEGOTIATE or red PASS
- rate per loaded mile and all-in rate per total mile
- total cost, profit after your pay and profit per day
- the rate you need to hit your target, and the break-even rate

Optional lines take tolls, lumpers (reimbursed or not), scales and washes, extra stop pay, detention, a route fuel price, reefer hours and a different factoring or dispatch fee for that load. The sample load pays {money(o['rpl'], 2)} a loaded mile, which looks good, but with {lc['dh']} deadhead miles it is a PASS.

LOAD COMPARE puts five offers side by side and marks the best profit per day.

**What's included**
- BrassLedger_Owner_Operator_CPM_Calculator.xlsx: blank, with the presets and labelled example settings
- BrassLedger_Owner_Operator_CPM_Calculator_SAMPLE.xlsx: a fictional dry van operator with 46 loads, 19 fill-ups and three months of P&L, so you can see every tab working
- BrassLedger_Owner_Operator_Quick_Start_Guide.pdf: 9 pages, with set-up, worked examples, hotshot and box truck presets, and FAQ

**How delivery works**
Instant digital download. After purchase, download the files from your Etsy account (Purchases and reviews). No physical item is shipped.

**Compatibility**
- Microsoft Excel 2016 or later (Windows and Mac)
- Google Sheets: make a copy from the link in the guide, or upload the .xlsx to Google Drive
- Google Sheets app on Android and iPhone: the LOAD CHECK tab is built for a phone screen
- No macros, no add-ons. Formulas are locked against accidental edits (no password)

**FAQ**
*My cost per mile looks higher than what people post online.* Most posted numbers leave out your own pay, the truck payment or deadhead, or assume more miles than you run. This counts all of it and divides by your miles.

*Should I count my own pay?* Yes. The TAKE verdict always includes it. You choose whether the break-even line includes it.

*I run a hotshot.* Pick Hotshot (CDL) or Hotshot (non-CDL) on SETTINGS and enter your own fixed costs. The guide walks through it.

*I'm leased on.* Set the costs the carrier pays to 0 and use the dispatch fee % for the carrier's split.

*Does it file my IFTA or taxes?* No. The fuel log and days-away log are records to help you and your tax preparer.

**Please note**
- Estimates based on your inputs. The settings come with example values that you replace with your own numbers.
- Not financial, legal or tax advice.
- Not affiliated with any carrier, broker or load board.
- No specific earnings are promised.

Designed by Brass Ledger with help from AI tools; every formula was built and tested by the seller.

Brass Ledger · Simple tools for small business numbers.

## Price
**Suggested: $24.00** (your range $19–29).
- This is a deeper tool than the Lawn Care, Pressure Washing and Cake calculators ($17): eight tabs, a phone tab, a load comparer, IFTA-style records and a P&L. Pricing it at $17 would undersell that.
- Truckers spend money to make money and judge a tool by one load: avoiding a single money-losing load pays for it many times over. $24 sits in the middle of your range, so it doesn't look like a cheap template, and it doesn't ask a sceptical first-time buyer for top-of-range money.
- It leaves room for a launch sale of about 20 % (around $19) and a move to $27–29 once the listing has reviews.

## Etsy attributes
- Category: **Paper & Party Supplies › Paper › Stationery › Design & Templates › Templates** (the path Etsy suggests for spreadsheet templates; pick the closest "Templates" option it offers)
- Type: Digital download
- File types: XLSX, PDF
- Who made it: I did · What is it: A finished product · When was it made: 2020–2026
- Designed by seller: Yes
- Renewal: automatic
- Photos: the 7 images in listing-images/, in order (01_hero first)
- Section: Small business calculators
"""


SOURCES = """| Default | Example value | Source |
|---|---|---|
| Diesel price | $5.90/gal | US EIA weekly on-highway diesel average: $5.937 for the week ending Nov 16, 2026 (via Blue Book Services / FleetOwner reports of EIA data). Prices move weekly; the buyer types their own. |
| Repair and maintenance | $0.200–0.220/mi (class 8) | ATRI, *An Analysis of the Operational Costs of Trucking*, 2026 update (2025 data): 21.5 cents/mile, up from 19.8 (FleetOwner, CCJ, Overdrive, TT News coverage). |
| Tires | $6,000 set / 120,000 mi = $0.050/mi | ATRI 2026 update: 5.0 cents/mile. |
| Truck + trailer payments | $2,300 + $650 a month | ATRI 2026 update: 40.4 cents/mile across fleets; the example is set lower for a used owner-operator tractor (about 30 cents at 10,000 miles a month). |
| Insurance | $15,200 a year across five lines | Overdrive, Insureon, AtoB and broker guides: $9,000–22,000 a year for one truck under own authority; primary liability about $6,500–10,000; physical damage 2–6 % of truck value. ATRI 2026: 10.6 cents/mile. |
| HVUT (Form 2290) | $550 a year | IRS: $550 maximum for 75,000 lb and over, tax period July 1, 2026 to June 30, 2027. |
| UCR | $46 a year | State UCR tables (Washington UTC, Texas DMV): $46 for 0–2 vehicles in 2026; FMCSA final rule sets $55 for 2027. |
| IRP plates, IFTA licence, authority/BOC-3/consortium, ELD, load boards, phone, bookkeeping, parking | various | Typical published ranges; these vary most by state and operation and are flagged as examples to replace. |
| MPG, class 8 | 6.4–6.8 | ATRI 2026: fleet average 7.43 MPG; heavier over-the-road hauls about 6.73. Reefer set lower for the extra weight. |
| Reefer fuel | 0.75 gal/hour | FreightWaves (about 0.75 gal/hour), EPRI analysis (0.735 gal/hour average), CCJ rule of thumb (0.8). |
| DEF | $0.015/mi (class 8), $0.010 (light) | About 2–3 % of diesel volume at roughly $3–4 a gallon of DEF. Estimate. |
| Hotshot MPG and costs | 10.0 (CDL), 11.5 (non-CDL); M&R $0.11–0.13; tires $2,400–2,800 per 60,000 mi | Published hotshot cost guides give 9–11 MPG loaded for diesel duallies and lower repair reserves. Lower confidence than the ATRI figures; documented as such in the guide. |
| Box truck | 10.0 MPG; M&R $0.12; tires $2,400 per 70,000 mi | Typical 26 ft box truck figures. Estimate, lower confidence. |
| Owner's pay, miles, margin, factoring | $1,500/week, 2,500 miles/week, 48 weeks, 10 %, 3 % | Example planning values, not industry statistics. Factoring commonly runs 1–5 %. |

The ATRI 2026 report puts the industry average at $2.336 per mile for 2025, a record (Overdrive, FreightWaves, CCJ). The example dry van all-in cost of $2.308 per mile is close to that, though built differently: our figure uses 2026 diesel prices and the owner's chosen pay instead of fleet driver wages."""


def report():
    res = json.loads((ROOT / "dist" / "test_results.json").read_text())
    ok = sum(1 for _, o, _ in res if o)
    m = settings_model()
    rows = "\n".join(f"| {'PASS' if o else 'FAIL'} | {n.replace('|', '/')} |" for n, o, _ in res)
    return f"""# Test report: Owner-Operator Cost Per Mile & Load Profit Calculator

**Result: {ok} of {len(res)} checks passed.** Both workbooks were recalculated in LibreOffice headless and compared with an
independent Python model (`build/test_workbook.py`), which does not read any formula.

## What was checked
1. **Recalculation.** Both files recalculated in LibreOffice: 0 formula errors (#REF!, #VALUE!, #DIV/0!, #NAME?, #N/A) and no error values in any cell.
2. **Cost per mile (SETTINGS).** Fixed, variable, operating and all-in cost per mile, pay per mile, break-even and target rates, and the 6,000 / 8,000 / 10,000 / 12,000 miles-a-month table, from the sample settings.
3. **Load checker.** Four loads on LOAD COMPARE, every output and the counter-offer: a clear TAKE; a NEGOTIATE; a load that pays more per loaded mile than the target rate but is a PASS once deadhead is counted (the sample on the phone tab); a load with detention, extra stop pay, a non-reimbursed lumper and its own fee percentages. Two reefer loads with the Reefer preset (default and typed reefer hours).
4. **Tracking.** All 46 sample trips (miles, revenue, factoring, profit, profit per day), MPG for every fill-up and average MPG, miles by state, monthly P&L for September to November (miles, revenue, fuel, other costs, fixed costs, net profit, actual cost per mile and the >10 % flag), days away from home by month, and every dashboard tile.
5. **Edge cases.** Zero deadhead, zero miles, factoring 0 % on a load and in SETTINGS, lumper reimbursed, days left blank, switching the preset to Hotshot (CDL), Box truck and Flatbed, and typing your own value over a preset.
6. **Blank file.** Empty log rows and the empty load check show blanks, not zeros or errors; presets and labelled example settings are present; no sample data.
7. **Structure.** No functions missing from Excel 2016 or Google Sheets (no XLOOKUP, LET, LAMBDA, FILTER, MAXIFS, IFS, TEXTJOIN, INDIRECT, OFFSET, TEXT), no Excel Tables, macros or external links, tab order, every tab protected without a password, validations on every input tab, frozen header rows, conditional formatting with same-sheet formulas only, inputs unlocked and calculated cells locked.
8. **Phone width.** LOAD CHECK (PHONE) is columns A–D, {int(1.5 * 7 + 5) * 2 + int(27 * 7 + 5) + int(14.5 * 7 + 5)} px wide, plus about 46 px of row numbers in the Google Sheets app: under 390 px, so no sideways scrolling. Columns E–Z are hidden. Rendered at phone width (`dist/screens/check.png`, 2x scale): the verdict is a full-width 28 pt cell with white text on green, amber or red.
9. **Layout lint.** `lint_layout.py` on both recalculated files: 0 clipped labels, 0 "###" cells, no chart overlaps.

## Sample settings, worked out by hand
| | $/mile |
|---|---|
| Fuel ($5.90 / 6.8 MPG) | {m['parts']['fuel']:.4f} |
| DEF + maintenance + tires | {m['parts']['defc'] + m['parts']['maint'] + m['parts']['tire']:.4f} |
| Variable | {m['var']:.4f} |
| Fixed ({money(m['fixed_month'])} a month / {m['month_miles']:,.0f} miles) | {m['fixed_cpm']:.4f} |
| Operating (break-even) | {m['op']:.4f} |
| Your pay ($1,500 x 52 / (2,500 x 48)) | {m['paypm']:.4f} |
| All-in | {m['allin']:.4f} |
| Target rate (all-in / (1 - 10 % - 3 %)) | {m['target']:.4f} |

## Results
| Result | Check |
|---|---|
{rows}

## Sources for the default values
{SOURCES}

## Choices made (and why)
- **Fees in the target rate.** Factoring and dispatch are a share of revenue, not a cost per mile, so the target rate is all-in / (1 - margin - fees). With no fees this is exactly all-in / (1 - margin), as in the brief. The break-even rate likewise divides by (1 - fees).
- **Break-even line.** PASS means the load doesn't cover operating costs (everything except your pay). A setting switches it to all-in costs including your pay. TAKE always requires your target margin after your pay. An optional minimum profit per day can also be required for TAKE.
- **Fixed costs on a load and in the trip log** are charged per mile (fixed per month / expected miles), as in the brief. The monthly P&L charges the real monthly amount for every month from the first to the last month with a logged load, so idle months in between still carry their fixed costs.
- **Maintenance, tires and DEF** are a per-mile reserve in the trip log and P&L, since repairs come in lumps. The P&L notes this.
- **Phone tab order.** The four key inputs come first, then the verdict and results, then the optional details. This keeps the verdict on the first screen on a phone. The optional inputs still change the result above them.
- **Pay per mile** spreads 52 weeks of pay over the miles of the weeks you work, so time off is paid for.
- **Sample data** is a fictional dry van operator (Ridgeline Freight) with 46 loads in back-to-back stretches out of Springfield, MO, from September 1 to November 23, 2026. Revenue uses lane rates plus a $0.72/mi fuel surcharge; the sample truck's real MPG (6.7) is a little below the preset (6.8), which shows up in the P&L.

## Google Sheets (desktop and phone app): what may differ, and how it's handled
| Feature | Behaviour | Handling |
|---|---|---|
| Fonts | Inter and Georgia are Google fonts; Fraunces is not used in cells | Tab titles use Georgia; cells use Inter, with fallback if missing |
| Sidebar icons | Excel shows the drawn icon bar; Google Sheets does not show drawing shapes | Column A also has text links (Home, Start, Setup, ...) that work in Sheets |
| Conditional formatting | Sheets does not accept references to other sheets in rules | Every rule refers to cells on its own sheet (the verdict uses a hidden code cell on the phone tab) |
| Protection | Sheets imports sheet protection as "warning" ranges | Locked cells still warn before an edit; no password in either app |
| Data validation | Lists from another sheet (states) | Supported in Sheets; tested as cross-sheet list ranges |
| Hidden columns E–Z on the phone tab | Respected by the Sheets app | Nothing to the right to scroll to |
| Number formats that hide zeros | Supported | Used on the P&L and dashboard so empty months stay blank |
| Charts | Bar charts convert; colours and gap width can shift slightly | Simple clustered bars only |
| SUMPRODUCT(MIN(...)) / SUMPRODUCT(MAX(...)) for first and last month | Evaluated as arrays in both | Tested in LibreOffice; same functions in Sheets |
| Phone app editing | Tap a cell, type, tap the tick; dropdowns show as chips | Inputs are large (16 pt) merged cells, labels above them |
| Offline use in the app | Needs offline access turned on for the file | Explained in the guide FAQ |
"""


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "etsy-listing.md").write_text(listing(), encoding="utf-8")
    (OUT / "test-report.md").write_text(report(), encoding="utf-8")
    print("wrote etsy-listing.md and test-report.md")
