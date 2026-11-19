"""Write etsy-listing.md and test-report.md for the Pressure Washing Bid Calculator (numbers from test_results.json)."""
import json
from pathlib import Path

import pw_config as CFG

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "pressure-washing-bid-calculator"
RES = json.loads((ROOT / "dist" / "test_results.json").read_text())

TITLE = ("Pressure Washing Business Pricing Calculator, Soft Wash Bid Estimator & Quote Template, Power Washing "
         "Spreadsheet, Excel & Google Sheets")
TAGS = ["pressure washing", "power washing", "soft wash business", "pressure wash quote", "cleaning bid",
        "bid estimator", "power wash pricing", "exterior cleaning", "house wash pricing", "quote template",
        "small business excel", "google sheets tool", "job estimate sheet"]
BUNDLE_TITLE = ("Lawn Care & Pressure Washing Pricing Calculator Bundle, Quote Templates, Bid Estimator, Route Planner, "
                "Excel & Google Sheets")
for t in (TITLE, BUNDLE_TITLE):
    assert len(t) <= 140, (len(t), t)
assert len(TAGS) == 13 and len(set(TAGS)) == 13 and all(len(t) <= 20 for t in TAGS), [t for t in TAGS if len(t) > 20]


def money(x):
    return f"-${-x:,.2f}" if x < 0 else f"${x:,.2f}"


q = RES["sample_quote"]
cph = RES["cost_per_hour"]

LISTING = f"""# Etsy listing: Pressure Washing Bid Calculator

## Title ({len(TITLE)} of 140 characters)
{TITLE}

## Tags (13, each 20 characters or fewer)
{chr(10).join(f"{i + 1}. {t} ({len(t)})" for i, t in enumerate(TAGS))}

## Photos (in this order)
| # | File | Shows |
|---|------|-------|
| 1 | 01_hero.png | Promise, three benefits, QUICK QUOTE on a laptop, Excel + Google Sheets badge |
| 2 | 02_whats_included.png | The eight tabs and the files in the download |
| 3 | 03_quick_quote.png | QUICK QUOTE with callouts on the service lines and profit per job hour |
| 4 | 04_customer_quote.png | The printable customer quote with the user's own business name |
| 5 | 05_plans_job_log.png | Maintenance plans due next and the job log's estimate-vs-actual notes |
| 6 | 06_compatibility.png | Excel and Google Sheets, best on a computer, digital download |
| 7 | 07_what_you_receive.png | Files list, instant download, no physical item |

## Description

Quote any pressure washing job in two minutes, without underpricing.

Exterior cleaning is priced by surface and size, with extras for stains, heavy growth, second storeys and poor access. Miss one of them, or underestimate chemicals, setup and driving, and the job pays far less than it should. This spreadsheet adds up what each job really costs you and prices every service so you keep a profit on top of your own pay. Built only for exterior cleaning, in the trade's own terms: flatwork, surface cleaner, soft wash, house wash by storey, roof wash, pavers, gutter brightening, sealing. Not a generic quote template.

━━━━━━━━━━━━━━━━━━━━
WHO IT'S FOR
━━━━━━━━━━━━━━━━━━━━
Pressure washing and soft washing businesses in their first seasons, usually solo or with one helper, working from a truck or trailer setup. No spreadsheet skills needed: you fill in white cells and pick from dropdowns.

━━━━━━━━━━━━━━━━━━━━
WHAT IT DOES
━━━━━━━━━━━━━━━━━━━━
✔ Works out your cost per working hour from your equipment (price, life, maintenance), overhead and target pay, and shows your break-even hourly rate
✔ 20 services ready to edit: driveways, walkways, patios, pool decks, garage floors, pavers (clean, re-sand, seal), house wash, roof soft wash, decks, fences, gutter brightening, commercial flatwork, dumpster pads, drive-thru lanes, window rinse and more
✔ Each service has its own production rate (units per hour) and chemical or material cost per 1,000 units
✔ Up to 10 services per quote, each with condition (light, normal, heavy), height and access (storeys, roof pitch, ladder, lift) and stain treatment (oil, rust, gum, organic)
✔ Adds setup and breakdown time, crew size, drive time, water hauling and a travel surcharge beyond the miles you include
✔ Prices each line at your target margin, rounded up, with a bundle discount for 2 or more services, and never below your minimum job charge
✔ Shows total time, the cost breakdown, profit, profit per job hour and price per sq ft of flatwork, with red warnings when a job is below break-even or under your profit target
✔ Compares each line with the local going rate you enter
✔ Prices a yearly or twice-yearly maintenance plan with a plan discount
✔ A one-page customer quote with YOUR business name, itemised services, the plan offer, terms and a signature line
✔ Quote log with win rate and flatwork price per sq ft for accepted vs declined quotes
✔ Job log comparing estimated and actual hours by service, with a plain-English note on which production rates to change
✔ Maintenance plan tracker: next due dates, plans due in the next 30 days, yearly plan revenue
✔ Dashboard: break-even rate, average job, win rate, revenue, profit per hour, plans due, three charts

━━━━━━━━━━━━━━━━━━━━
WHAT'S INCLUDED
━━━━━━━━━━━━━━━━━━━━
• Blank workbook (.xlsx) with 8 tabs: Start Here, Settings, Quick Quote, Customer Quote, Quote Log, Job Log, Maintenance Plans, Dashboard. Example costs and services are filled in for you to replace.
• Sample workbook (.xlsx): a fictional exterior cleaning business with 8 quotes, 10 completed jobs and 8 maintenance plans
• Quick-start guide (PDF, 8 pages): setting up your costs, measuring surfaces, a worked house wash + driveway + walkway quote, sending the customer quote, selling plans, tuning your rates, FAQ

━━━━━━━━━━━━━━━━━━━━
HOW DELIVERY WORKS
━━━━━━━━━━━━━━━━━━━━
1. Buy, then download the files from Etsy › You › Purchases and reviews. Nothing is shipped.
2. Open the .xlsx in Excel, or use the Google Sheets copy link in the guide (File › Make a copy).
3. Fill in Settings once, then quote your first job.

━━━━━━━━━━━━━━━━━━━━
COMPATIBILITY
━━━━━━━━━━━━━━━━━━━━
• Microsoft Excel 2016 or later (Windows and Mac), Excel for the web
• Google Sheets (free Google account)
• Best on a computer; it opens in the phone apps but quoting is easier on a laptop
• No macros, no add-ons

━━━━━━━━━━━━━━━━━━━━
FAQ
━━━━━━━━━━━━━━━━━━━━
Will it tell me what to charge in my area?
It tells you what YOU need to charge to cover your costs and pay yourself, then compares each line with the going rate you enter. Local prices vary a lot; the example values are typical US figures to replace with your own.

My price looks higher than competitors'. Is it wrong?
Check your working hours and production rates first. Often a competitor isn't counting chemicals, setup, insurance or driving. The guide covers what to do.

How do I price oil stains?
Pick Oil under Stain treatment and type the number of spots. Each spot adds the minutes and materials you set, and the price includes your margin.

Can I add my own services?
Yes: there are empty rows in the services table on Settings, and they appear in the dropdowns straight away.

Can I put my logo on the quote?
Yes, there's a space for it. The quote carries your business name only.

Can I get a refund?
Because this is a digital download, refunds aren't offered, but message me if anything doesn't work and I'll help.

━━━━━━━━━━━━━━━━━━━━
PLEASE NOTE
━━━━━━━━━━━━━━━━━━━━
Prices are estimates based on your inputs. Adjust to your local market. Not financial, legal or tax advice. No specific earnings are promised.

Reminders, not legal advice: many cities regulate wash-water runoff into storm drains; soft wash chemicals can harm plants and surfaces; washing painted surfaces on older homes may disturb lead-based paint; carry liability insurance, and check whether your area requires a business licence.

Designed by Brass Ledger with help from AI tools; every formula was built and tested by the seller.

## Price
**Suggested: $17.00** (your range $15–19), the same as the Lawn Care Pricing Calculator.
- Matching prices make the two read as siblings and keep the bundle maths simple.
- It replaces a quote template, a pricing worksheet, a job log and a plan tracker; the multi-service pricing, job log and customer quote are the parts buyers can't easily build themselves.
- One underpriced house wash costs more than the file. $17 leaves room for a 15–20 % launch discount while staying above $13.
- Consider $19 once the listing has reviews.

## Etsy attributes
- Category: **Paper & Party Supplies › Paper › Stationery › Design & Templates › Templates** (the path Etsy suggests for spreadsheet templates; pick the closest "Templates" option it offers)
- Type: Digital download
- File types: XLSX, PDF
- Who made it: I did · What is it: A finished product · When was it made: 2020–2026
- Designed by seller: Yes
- Renewal: automatic

---

## Future bundle listing: Lawn Care + Pressure Washing

**Title ({len(BUNDLE_TITLE)} of 140 characters):**
{BUNDLE_TITLE}

**Price: $27.00** (two products at $17 = $34; about 20 % off). Etsy shows the saving clearly at this level, and it stays
above either product alone so neither undercuts the other. Sale floor: $23.

**Description (opening):**

Price every lawn and every wash for profit: two sibling calculators for outdoor service businesses.

Many lawn care businesses add pressure washing in spring and fall, and many pressure washers mow in summer. This bundle gives you both Brass Ledger pricing calculators, built on the same engine: the same Settings layout, the same cost-per-hour logic, the same customer quote and quote log. Learn one and you know the other.

INCLUDED
• Lawn Care Pricing Calculator (blank + sample + quick-start guide): price per visit, monthly and season prices, add-ons, route planner, season tracker
• Pressure Washing Bid Calculator (blank + sample + quick-start guide): up to 10 services per job, condition, height and stain extras, maintenance plans, job log

Then reuse the "How delivery works", "Compatibility", "Please note" and AI-disclosure sections from the two listings.

**Bundle tags (suggestions):** lawn care pricing, pressure washing, lawn care business, power washing, mowing business, soft wash business, landscaping bid, cleaning bid, bid estimator, quote template, outdoor business, small business excel, google sheets tool
"""

REPORT = f"""# Test report: Pressure Washing Bid Calculator

Result: **{RES['passed']} checks passed, {RES['failed']} failed.**
Formulas: blank file {RES['BrassLedger_Pressure_Washing_Bid_Calculator.xlsx']:,}, sample file {RES['BrassLedger_Pressure_Washing_Bid_Calculator_SAMPLE.xlsx']:,}.

## 1. What was checked
1. **Both files recalculated in LibreOffice headless:** 0 formula errors (#REF!, #VALUE!, #DIV/0!, #NAME?, #N/A), no error value in any cell.
2. **Independent Python model** (`test_workbook.py`, no formulas) recomputes cost per hour and the full quote, then compares with the
   recalculated workbook: each line's minutes, chemicals, cost, price, price per unit and "vs going rate"; job totals (service time,
   setup and water hauling, crew time, job hours, labour, equipment, overhead, machine fuel, chemicals, travel, other costs, cost);
   subtotal, bundle discount, water hauling, travel surcharge, minimum top-up, total, profit, profit per hour, flatwork sq ft and price
   per sq ft, plan value, the warning, the "Save this quote" row, and the customer quote (each line, totals with no gaps, plan offer).
3. **Four jobs:**

| Job | Services | Cost | Subtotal | Bundle | Water + travel | Min. top-up | Total | Profit per job hour | Plan a year |
|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(
    f"| {name} | {RES[k]['n']} | {money(RES[k]['cost'])} | {money(RES[k]['subtotal'])} | {money(RES[k]['bundle'])} | "
    f"{money(RES[k]['water_fee'] + RES[k]['travel_fee'])} | {money(RES[k]['min_adj'])} | {money(RES[k]['total'])} | "
    f"{money(RES[k]['profit_hr'])} | {money(RES[k]['plan']) if RES[k]['plan'] != '' else '–'} |"
    for name, k in (("Sample: 2-storey house wash + heavy driveway with 3 oil spots + walkway + 2-storey gutters", "sample_quote"),
                    ("Driveway only, 400 sq ft (below the minimum charge)", "Driveway only, below the minimum"),
                    ("2-storey house wash + driveway + gutters, plan on house and driveway", "2-storey house wash + driveway + gutters, bundle and plan"),
                    ("Commercial flatwork 8,000 sq ft heavy + 12 oil spots, dumpster pad, crew of 2, no water, 24 miles",
                     "Commercial flatwork, heavy, oil stains, crew 2, no water, travel surcharge"))) + f"""

4. **Edge cases:** empty quote (all totals blank, tiles "–", message asks for a service, customer quote empty), a line with quantity 0
   (ignored), margin 0 %, no water on site (water hauling time and charge), rounding increment 0, and a service typed that is not in
   SETTINGS (line ignored, unit shows "not in SETTINGS").
5. **Settings change ripple:** driveway chemicals $3 → $12 per 1,000 sq ft, house wash rate 1,200 → 900 wall sq ft per hour, margin
   35 % → 40 %. The sample total moved from {money(RES['settings_change']['before'])} to {money(RES['settings_change']['after'])}; every line
   matched the model; the customer quote and the QUICK QUOTE tile updated; changing your pay updated the dashboard break-even.
6. **Job log:** each row's actual cost (hours × (crew labour + equipment + overhead per hour) + chemicals + extra costs), profit, profit
   per hour and time vs estimate; the by-service table and its notes. On the sample data:
""" + "\n".join(f"   - {k}: {v}" for k, v in RES["job_notes"].items()) + f"""
7. **Maintenance plans:** visits a year, annual value, next due date (EDATE from the last clean), status (overdue / due in N days /
   scheduled / paused), and the tiles (annual revenue, due in 30 days, overdue). These depend on today's date; the test computes the
   expected values for the day it runs.
8. **Quote log and dashboard:** win rate, average quote, flatwork price per sq ft for accepted vs declined quotes; all seven dashboard
   tiles, revenue by service type, 3 charts.
9. **Blank file:** 300 quote log rows, 300 job log rows, the by-service table, 150 plan rows and the 10 quote lines are blank (no zeros,
   no errors); tiles show "–"; the customer quote shows "Your business name".
10. **Printing:** the customer quote prints on exactly one letter page, shows the user's business name and total, and contains no
    "Brass Ledger" text. Every other tab printed with no "###".
11. **Structure and layout:** no macros, no Excel Tables, no external links, no LAMBDA/LET/XLOOKUP/FILTER/TEXT()/INDIRECT/OFFSET; every
    tab protected without a password; header rows frozen; dropdowns on every list field; layout lint (clipped text, chart geometry):
    0 problems in both files.

Cost per hour (sample Settings): equipment {money(cph['equip_year'])} a year = {money(cph['equip_hr'])}/h; overhead {money(cph['over_year'])} a year =
{money(cph['over_hr'])}/h; break-even with $35 pay {money(cph['breakeven_hr'])}/h; at 35 % margin {money(cph['target_hr'])}/h.

## 2. How the price is worked out
- Line minutes = quantity ÷ units per hour × 60 × condition time multiplier × height/access multiplier + stain qty × stain minutes.
- Line chemicals = quantity ÷ 1,000 × chemicals per 1,000 × condition chemical multiplier + stain qty × stain material cost.
- Job: on site = (service minutes + setup/breakdown + water hauling minutes if no water) × (1 + loss × (crew − 1)) ÷ crew.
  Job hours = (on site + driving) ÷ 60.
- Cost = labour (on site × crew labour rate) + equipment and overhead per job hour + pressure washer fuel (spray time × gallons per hour
  × fuel price) + chemicals + travel (driving time × crew rate + miles × vehicle cost per mile) + other job costs.
- Each line carries its own chemicals plus a share of the other costs in proportion to its minutes.
- Line price = line cost ÷ (1 − margin), rounded up to the increment. Subtotal − bundle discount (2+ services) + water hauling charge +
  travel surcharge (miles beyond the included miles × rate), topped up to the minimum job charge.
- Maintenance plan = Σ line price × visits a year (0, 1 or 2 per line) × (1 − plan discount).
- Job log actual cost = actual hours × (owner pay + helpers × wage × (1 + payroll) + equipment + overhead per hour) + actual chemicals +
  extra costs. Notes trigger when a service's actual hours are more than 15 % above or below the estimate; the suggested rate is
  current rate × estimated ÷ actual hours.

## 3. Default values and where they come from
All defaults are labelled on SETTINGS as **example values, adjust to your area and equipment**.

| Setting | Default | Source / reasoning |
|---|---|---|
| Flatwork production | Driveway 1,000 sq ft/h; walkway 700; patio 800; pool deck 700; garage 500 | Operators with a 4 GPM machine and 20" surface cleaner report about 1,500 sq ft/h on open concrete; older benchmarks 700–900 sq ft/h. Defaults sit between, allowing for edges and pre/post-treatment. [Pressure Washing Resource forum](https://pressurewashingresource.com/community/t/surface-cleaning/3358), [productivity estimates](https://pressurewashinginfo.blogspot.com/2010/11/pressure-wash-productivity-estimates.html) |
| House wash, roof | 1,200 wall / roof sq ft per hour | Seller estimate for soft washing (mix, apply, dwell, rinse); a 2,600 sq ft wall area takes about 2.5–3 h on 2 storeys. The job log adjusts it |
| Pavers, decks, sealing | Pavers clean 500/h, + re-sand 250/h, + seal 150/h; deck 300/h, + stain 100/h | Seller estimates; materials (joint sand ~$350, sealer ~$300, stain ~$300 per 1,000 sq ft) included in the chemicals column |
| Chemicals | $2–30 per 1,000 units (sodium hypochlorite mixes, surfactant, degreaser) | Seller estimates at typical US supply-house prices |
| Going rates | Driveway $0.20/sq ft, walkway $0.20, patio $0.30, house $0.12 per wall sq ft, roof $0.45, gutters $1.00/linear ft, pavers seal $1.90 … | National cost guides: driveways $0.20–0.55/sq ft, house washing $0.10–0.50/sq ft, roof soft wash $0.30–0.75/sq ft. [Fixr](https://www.fixr.com/costs/pressure-wash-driveway), [HomeAdvisor](https://www.homeadvisor.com/cost/painting/powerwash-exterior-surfaces), [Bob Vila](https://www.bobvila.com/articles/cost-to-pressure-wash-driveway) |
| Condition | Light 0.8 / Normal 1.0 / Heavy 1.4 time, 1.5 chemicals | Seller estimates |
| Height / access | 2 storeys 1.3, 3 storeys 1.6, ladder 1.2, steep pitch 1.4, lift 1.5, difficult access 1.25 | Seller estimates |
| Stains | Oil 10 min + $3 a spot; rust 0.5 min + $0.60 a sq ft; gum 1 min + $0.05 a spot; organic 0.1 min + $0.04 a sq ft | Seller estimates (rust remover ~$30/gal covers ~50 sq ft) |
| Equipment | 4 GPM 4000 PSI washer $2,200/5 yr; 20" surface cleaner $450; 12V soft wash system $1,200; hoses and reels $650; ladders $500; trailer $3,000; 525-gal tank $600; guns/tips/PPE $500 | Seller estimates of typical US retail |
| Overhead | $5,470 a year (liability insurance $1,500 …) | Seller estimates for a solo operator |
| Fuel | $4.00/gal; washer 0.8 gal/h; truck 15 mpg towing; wear $0.30/mile | EIA US regular ~$4.10 (July 2026); a 13–14 hp washer engine burns roughly 0.6–1 gal/h |
| Targets | 1,100 hours; pay $35; helper $18; payroll 12 %; margin 35 %; $10 profit per job hour target; minimum $150; round to $5; setup 30 min; bundle 10 %; plan 10 %; water hauling $50 + 20 min; 15 free miles then $1.50/mile | Common starting points for a solo operator; minimum job charges of $150–200 are widely used |

## 4. Google Sheets: what can differ, and how it's handled
| Feature | In Google Sheets | Handling |
|---|---|---|
| Icon sidebar (drawn shapes) | Dropped on import | Dark column of short text links underneath |
| Sheet protection | Not carried over | Shaded cells clearly marked; guide warns |
| Data bars | Dropped | Decoration only |
| EDATE, SUMIFS, COUNTIFS, AVERAGEIF, INDEX/MATCH, IFERROR, ROUNDUP, FIXED | Supported | No TEXT() date codes, no dynamic arrays |
| Conditional border on the customer quote total | Supported | If a version drops it, the total is still bold |
| Paste values | Ctrl+Shift+V | Shown on QUICK QUOTE and in the guide |
| Print settings | Not imported | Guide: File › Print, Scale "Fit to page" |
| Dates relative to today (plans due) | Same | Plans are recalculated on open |

## 5. Choices made (no questions were needed)
- **Reuse:** `pw_engine.py` subclasses `engine.py` from the Lawn Care product: same styling, title bars, tiles, sidebar, helpers,
  settings layout and wording, customer quote style, quote log and dashboard pattern, so the two read as siblings in a bundle.
- **Shared costs per line:** each line carries its own chemicals plus a time-based share of setup, travel, equipment, overhead and
  fuel, so a quick walkway isn't priced like a long house wash.
- **Rounding per line** (not on the total) keeps every customer-facing line a round number; the bundle discount is then exact.
- **Water hauling and travel surcharge** are customer charges on their own lines; the hauling time is also counted as cost.
- **Maintenance plan** = visits a year per line (0, 1 or 2), so "house wash each spring, driveway each fall" is two lines at 1 visit.
- **Going rate** is per unit in the services table (one place to maintain), compared per line on the quote.
- **Job log** uses the main service per job for the estimate-vs-actual table; notes need the difference to exceed 15 %, and the
  guide advises waiting for 3 jobs before changing a rate.
- **Sample settings** use $35 pay and a 35 % margin (pressure washing usually carries higher margins than mowing).
- Logo: the supplied Brass Ledger logo PNG is used in the guide and images.
"""

(OUT / "etsy-listing.md").write_text(LISTING)
(OUT / "test-report.md").write_text(REPORT)
print("wrote etsy-listing.md and test-report.md")
