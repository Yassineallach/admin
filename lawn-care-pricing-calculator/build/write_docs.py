"""Write etsy-listing.md and test-report.md for the Lawn Care Pricing Calculator (numbers from test_results.json)."""
import json
from pathlib import Path

import lawn_config as CFG

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "lawn-care-pricing-calculator"
RES = json.loads((ROOT / "dist" / "test_results.json").read_text())

TITLE = ("Lawn Care Pricing Calculator Spreadsheet, Lawn Mowing Business Quote Template, Bid Estimator & Route Planner, "
         "Excel & Google Sheets")
TAGS = ["lawn care pricing", "lawn care business", "mowing business", "lawn care quote", "landscaping bid",
        "lawn mowing quote", "bid estimator", "route planner", "landscaping quote", "yard care pricing",
        "lawn care template", "google sheets tool", "small business excel"]
assert len(TITLE) <= 140, len(TITLE)
assert len(TAGS) == 13 and len(set(TAGS)) == 13 and all(len(t) <= 20 for t in TAGS)

q = RES["sample_quote"]
cph = RES["cost_per_hour"]


def money(x):
    return f"${x:,.2f}"


LISTING = f"""# Etsy listing: Lawn Care Pricing Calculator

## Title ({len(TITLE)} of 140 characters)
{TITLE}

## Tags (13, each 20 characters or fewer)
{chr(10).join(f"{i + 1}. {t} ({len(t)})" for i, t in enumerate(TAGS))}

## Photos (in this order)
| # | File | Shows |
|---|------|-------|
| 1 | 01_hero.png | Promise, three benefits, QUICK QUOTE on a laptop, Excel + Google Sheets badge |
| 2 | 02_whats_included.png | The eight tabs and the files in the download |
| 3 | 03_quick_quote.png | QUICK QUOTE result with callouts on price per visit and profit per job hour |
| 4 | 04_customer_quote.png | The printable customer quote with the user's own business name |
| 5 | 05_routes_dashboard.png | Route planner by weekday and the dashboard charts |
| 6 | 06_compatibility.png | Excel and Google Sheets, best on a computer, digital download |
| 7 | 07_what_you_receive.png | Files list, instant download, no physical item |

## Description

Price every lawn for profit in two minutes.

Most new lawn care businesses guess their prices or copy a competitor. This spreadsheet adds up what each visit really costs you (your time, equipment wear, fuel, insurance, driving between jobs) and prices the job so you keep a profit on top of your own pay. Built only for lawn care, in the trade's own terms: deck size, trimming and edging, bi-weekly visits, season contracts, cleanups and route density. Not a generic quote template.

━━━━━━━━━━━━━━━━━━━━
WHO IT'S FOR
━━━━━━━━━━━━━━━━━━━━
Lawn mowing and yard care businesses in their first seasons, usually solo or with one helper, working from a truck and trailer. No spreadsheet skills needed: you fill in white cells and pick from dropdowns.

━━━━━━━━━━━━━━━━━━━━
WHAT IT DOES
━━━━━━━━━━━━━━━━━━━━
✔ Works out your cost per working hour from your equipment (price, life, maintenance), overhead and target pay, and shows your break-even hourly rate
✔ Times each lawn from its size and your mower's speed (21" push to 61" zero-turn), with multipliers for obstacles, slope, overgrown grass and bagging
✔ Adds trimming, edging and blowing time, crew size, drive time and miles
✔ Prices the visit at your target margin, rounded up to the nearest $5 (or your choice), never below your minimum charge
✔ Shows cost per visit, price per visit, profit per visit, profit per job hour and price per 1,000 sq ft
✔ Red warnings when a price is below break-even or under your profit target, and a check against the local going rate
✔ Monthly price (weekly = 52 ÷ 12 visits) and season contract price, with an optional prepay discount
✔ Add-on price list: leaf removal, spring and fall cleanups, aeration, overseeding, fertilising, mulching, hedge trimming, weed pulling, gutter cleaning
✔ A one-page customer quote with YOUR business name, contact details, terms and a signature line
✔ Quote log with win rate and price per 1,000 sq ft for accepted vs declined quotes, so you can see if you're priced too high or too low
✔ Route planner by weekday: revenue per hour and a warning when driving eats the day
✔ Season tracker and dashboard: revenue against your monthly goal, best day, active clients

━━━━━━━━━━━━━━━━━━━━
WHAT'S INCLUDED
━━━━━━━━━━━━━━━━━━━━
• Blank workbook (.xlsx) with 8 tabs: Start Here, Settings, Quick Quote, Customer Quote, Quote Log, Route Planner, Season Tracker, Dashboard. Example costs are filled in for you to replace.
• Sample workbook (.xlsx): a fictional lawn business with quotes, 15 route clients and a full season of figures
• Quick-start guide (PDF, 9 pages): setting up your costs, measuring a lawn, a worked quote, sending the customer quote, using the quote log, planning routes, FAQ

━━━━━━━━━━━━━━━━━━━━
HOW DELIVERY WORKS
━━━━━━━━━━━━━━━━━━━━
1. Buy, then download the files from Etsy › You › Purchases and reviews. Nothing is shipped.
2. Open the .xlsx in Excel, or use the Google Sheets copy link in the guide (File › Make a copy).
3. Fill in Settings once, then quote your first lawn.

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
It tells you what YOU need to charge to cover your costs and pay yourself, then compares that with the going rate you enter. Local prices vary a lot; the example values are typical US figures to replace with your own.

My price comes out higher than competitors'. Is it wrong?
Check your working hours and mower speeds first. Often the competitor isn't counting equipment wear, insurance or drive time. The guide covers what to do.

How do I price leaves and cleanups?
As add-ons: flat, per hour, per 1,000 sq ft, per cubic yard or per bag. You set the prices.

Can I put my logo on the quote?
Yes, there's a space for it. The quote carries your business name only.

Do fertilising and weed control need a licence?
In many US states, yes: a pesticide applicator licence. Check your state's rules.

Can I get a refund?
Because this is a digital download, refunds aren't offered, but message me if anything doesn't work and I'll help.

━━━━━━━━━━━━━━━━━━━━
PLEASE NOTE
━━━━━━━━━━━━━━━━━━━━
Prices are estimates based on your inputs. Adjust to your local market. Not financial, legal or tax advice. No specific earnings are promised.

Designed by Brass Ledger with help from AI tools; every formula was built and tested by the seller.

## Price
**Suggested: $17.00** (your range $15–19).
- It replaces a quote template, a pricing worksheet, a route sheet and a season log, and the cost-per-hour and customer quote are the parts buyers usually can't build themselves.
- Lawn care is a business purchase: one underpriced lawn costs more over a season than the file.
- $17 leaves room for a 15–20 % launch or sale discount while staying above $13.
- Consider $19 once the listing has reviews.

## Etsy attributes
- Category: **Paper & Party Supplies › Paper › Stationery › Design & Templates › Templates** (the path Etsy suggests for spreadsheet templates; pick the closest "Templates" option it offers)
- Type: Digital download
- File types: XLSX, PDF
- Who made it: I did · What is it: A finished product · When was it made: 2020–2026
- Designed by seller: Yes
- Renewal: automatic
"""

REPORT = f"""# Test report: Lawn Care Pricing Calculator

Result: **{RES['passed']} checks passed, {RES['failed']} failed.**
Formulas: blank file {RES['BrassLedger_Lawn_Care_Pricing_Calculator.xlsx']:,}, sample file {RES['BrassLedger_Lawn_Care_Pricing_Calculator_SAMPLE.xlsx']:,}.

## 1. What was checked
1. **Both files recalculated in LibreOffice headless:** 0 formula errors (#REF!, #VALUE!, #DIV/0!, #NAME?, #N/A), and no error value in any cell.
2. **Independent Python model** (`test_workbook.py`, no formulas) recomputes cost per hour from the sample Settings and the full quote,
   then compares every line with the recalculated workbook:
   mowing minutes, detail minutes, crew time, job hours, labour, equipment, overhead, fuel, travel, disposal, cost, calculated price,
   rounding, minimum charge, price used, profit, profit per job hour, price per 1,000 sq ft, monthly, season, prepaid, each add-on line,
   the warning, the values-ready "Save this quote" row and the customer quote.
3. **Four lawns:**

| Lawn | Area | Cost per visit | Price per visit | Profit per job hour | Monthly | Season | Add-ons |
|---|---|---|---|---|---|---|---|
""" + "\n".join(
    f"| {name} | {RES[key]['area']:,.0f} sq ft | {money(RES[key]['cost'])} | {money(RES[key]['price'])} | {money(RES[key]['profit_hr'])} | "
    f"{money(RES[key]['monthly'])} | {money(RES[key]['season'])} | {money(RES[key]['addons'])} |"
    for name, key in (("Sample quote (9,500 sq ft, 52\" zero-turn, medium obstacles, weekly)", "sample_quote"),
                      ("Small push-mower lawn, weekly", "Small push-mower lawn (3,000 sq ft)"),
                      ("Medium zero-turn lawn, high obstacles, moderate slope, crew of 2, bi-weekly", "Medium zero-turn lawn, high obstacles, crew 2"),
                      ("Large lawn entered as 0.9 acres, overgrown, bagging, crew of 2, six add-ons", "Large lawn in acres, overgrown, bagging, add-ons"))) + f"""

   The small lawn calculates to $35 and is lifted to the $40 minimum job charge. The large lawn was entered in acres
   (0.9 acres = 39,204 sq ft) and uses add-on quantities typed (hours, cubic yards, a 20 x 1,000 sq ft override) and automatic
   (flat = 1; per 1,000 sq ft = lawn area ÷ 1,000).
4. **Edge cases:** lawn area blank (price, profit, monthly, season blank; tiles show "–"; message asks for the area; customer
   quote empty), margin 0 %, crew of 2, own price below cost (red BELOW BREAK-EVEN), rounding increment 0 (rounds to cents),
   one-time job (no monthly or season price), monthly visits (7 visits in a 30-week season).
5. **Settings change ripple:** fuel $5.00, margin 30 %, 52" mower speed 50,000 sq ft/h, owner pay $28. The sample price moved
   from {money(RES['settings_change']['before'])} to {money(RES['settings_change']['after'])}; every line matched the model; the customer quote, the
   QUICK QUOTE tile and the dashboard break-even tile all updated.
6. **Cost per hour (sample Settings):** equipment {money(cph['equip_year'])} a year = {money(cph['equip_hr'])}/h; overhead {money(cph['over_year'])} a year
   = {money(cph['over_hr'])}/h; break-even (with $25 pay) {money(cph['breakeven_hr'])}/h; at 25 % margin {money(cph['target_hr'])}/h.
   The guide's example: $12,000 mower ÷ 6 years + $600 maintenance = $2,600 a year ÷ 1,200 hours = $2.17/h.
7. **Quote log, route planner, season tracker, dashboard** against the model: win rate, average price, price per 1,000 sq ft
   accepted vs declined, each weekday's stops, revenue, hours, revenue per hour, driving share and warning, each month's total and
   % of goal, revenue year to date, all six dashboard tiles, 3 dashboard charts.
8. **Blank file:** 300 log rows, 100 route rows, 12 season rows and the weekday summary are blank (no zeros, no errors); the quote
   shows no price until an area is entered; tiles show "–"; the customer quote shows "Your business name".
9. **Printing:** the customer quote prints on exactly one letter page (portrait, fit to page), shows the user's business name and
   price, and contains no "Brass Ledger" text anywhere. Every other tab printed with no "###" (column too narrow).
10. **Structure and layout:** no macros, no Excel Tables, no external links, no LAMBDA/LET/XLOOKUP/FILTER/TEXT()/INDIRECT/OFFSET;
    every tab protected without a password; header rows frozen; dropdowns on every list field; layout lint (clipped text and
    chart geometry): 0 problems in both files.

## 2. How the price is worked out
- Area used = lawn sq ft, or acres × 43,560 if only acres are entered.
- Mowing minutes = area ÷ mower speed × 60 × obstacles × slope × condition (× bagging multiplier if bagging).
- Trimming, edging, blowing: **minutes per 1,000 sq ft of lawn, with a minimum per visit** (chosen because it scales with the lawn
  and never underprices a small yard), × the obstacles multiplier.
- Time on site = total work × (1 + efficiency loss × (crew − 1)) ÷ crew.
- Labour = time on site × (owner pay + helpers × helper wage × (1 + payroll %)). Equipment and overhead per hour × job hours
  (on site + driving). Fuel = mowing hours × gallons per hour × fuel price. Travel = drive time × crew labour rate + miles × vehicle
  cost per mile (fuel ÷ mpg + wear). Disposal when bagging.
- Price = cost ÷ (1 − margin), rounded up to the increment, never below the minimum charge. Optional own price overrides it.
- Monthly = price × visits per month (weekly 52 ÷ 12, bi-weekly 26 ÷ 12, monthly 1). Season = price × visits in the season
  (weekly = weeks, bi-weekly = weeks ÷ 2 rounded up, monthly = weeks × 12 ÷ 52 rounded). Prepaid = season × (1 − discount).
- Route planner days are an average week: bi-weekly clients count 0.5, monthly 12 ÷ 52.
- Win rate = accepted ÷ (accepted + declined + no reply); quotes still "Sent" are not counted yet.

## 3. Default values and where they come from
All defaults are labelled on SETTINGS as **example values, adjust to your area and equipment**.

| Setting | Default | Source / reasoning |
|---|---|---|
| Mowing speeds | 21" push 13,000; 36" walk-behind 30,000; 48" stand-on 42,000; 52" ZTR 57,000; 61" ZTR 70,000 sq ft/h | Effective field capacity: acres/hour = mph × width (in) ÷ 99 at 100 % (ASABE formula; Exmark uses ÷ 124 at 80 %). Residential speeds (2.5–6 mph) and 50–60 % efficiency for turns, overlap and small lawns. [Exmark productivity](https://www.exmark.com/exmark-advantage/news-and-resources/blog/zero-turn-vs-lawn-tractor-productivity-comparison-of-4-5000-mowers), [Iowa State PM1976](https://store.extension.iastate.edu/Product/pm1976-pdf) |
| Mower fuel use | 0.15 / 0.6 / 1.0 / 1.2 / 1.5 gal/h | Gas commercial mowers 1–2 gal/h; Grasshopper cites 1.8 gal/h gas for a large ZTR; an owner reports ~0.9 gal/h on a 52" 22 hp; a 25 hp spec sheet lists 1.1–1.9. [Grasshopper](https://blog.grasshoppermower.com/quickcuts/your-next-mower-should-be-a-diesel-zero-turn-mower), [West Equip spec](https://west-equip.com/products/new/915e_tc) |
| Fuel price | $4.00/gal | EIA US regular average $4.096 (week of 27 July 2026). [EIA Gasoline and Diesel Fuel Update](https://www.eia.gov/petroleum/gasdiesel/) |
| Truck mpg (towing), wear per mile | 14 mpg, $0.30 | Seller estimate; fuel + wear = 58.6¢/mile, below the IRS 2026 standard mileage rate of 72.5¢ (which also covers insurance and depreciation) |
| Equipment list | 52" ZTR $12,000/6 yr/$600; push mower $500; trimmer $380; edger $350; blower $550; 6x12 trailer $2,800; tools $400 | Seller estimates of typical US retail for commercial-grade gear |
| Overhead | $4,710 a year (liability insurance $1,200, licence $150, phone $600, software $360, marketing $600, accounting $500, vehicle insurance share $1,000, other $300) | Seller estimates for a solo operator |
| Working hours | 1,200 a year | 30-week season × 40 hours |
| Owner pay / helper wage / payroll | $25 / $17 / 12 % | Helper wage near the BLS median for landscaping and groundskeeping workers (about $18/h); payroll covers employer FICA (7.65 %), unemployment taxes and workers' comp: confirm with an accountant |
| Margin, profit target, minimum, rounding | 25 %, $10 per job hour, $40, $5 | Common starting points; the margin is profit after paying yourself |
| Season, prepay, crew loss, driving warning | 30 weeks, 5 %, 10 % per extra person, 25 % of the day | Seller estimates |
| Multipliers | Obstacles 1.00/1.15/1.30; slope 1.00/1.15/1.35; overgrown 1.50; bagging 1.20 + $5 disposal | Seller estimates; time your own jobs and adjust |
| Detail work | Trimming 1.5 min/1,000 sq ft (min 8); edging 1.0 (min 5); blowing 0.75 (min 4) | Seller estimates (a 10,000 sq ft lawn ≈ 30 min of detail work) |
| Aeration | $12 per 1,000 sq ft | HomeGuide $7–25 per 1,000 sq ft; a pro quoted ~$10/1,000. [HomeGuide](https://www.homeguide.com/costs/lawn-aeration-cost), [Lawn & Landscape](https://www.lawnandlandscape.com/article/pulling-the-plugs--benefits-of-aeration) |
| Spring / fall cleanup | $200 / $250 flat | HomeGuide: spring $125–300, fall $150–400. [HomeGuide yard cleanup](https://homeguide.com/costs/yard-cleanup-cost) |
| Mulching | $70 per cubic yard | HomeGuide $35–70 per cubic yard delivered and installed (other guides quote much higher) |
| Gutter cleaning | $160 flat | National cost guides cluster around $120–230, ~$160 average (single storey) |
| Leaf removal $60/h, hedge trimming $55/h, weed pulling $45/h, overseeding $15 and fertilising $6 per 1,000 sq ft | | Seller estimates within commonly advertised ranges; **verify locally**. Fertilising and weed control may need a pesticide applicator licence (noted on SETTINGS and in the guide). |

## 4. Google Sheets: what can differ, and how it's handled
| Feature | In Google Sheets | Handling |
|---|---|---|
| Icon sidebar (drawn shapes) | Dropped on import | A dark column of short text links sits underneath, so navigation still works |
| Sheet protection | Not carried over | Shaded cells are clearly marked; guide says not to type over them |
| Data bars | Not supported; dropped | They are decoration only; the % values remain |
| Paste values | Ctrl+Shift+V | Shown on QUICK QUOTE and in the guide next to the Excel shortcut |
| Printing the customer quote | Print settings are not imported | Guide: File › Print, Scale "Fit to page" |
| Formulas | SUMIFS, COUNTIFS, AVERAGEIFS, INDEX/MATCH, IFERROR, ROUNDUP, FIXED all supported | No TEXT() date codes (locale-proof), no dynamic arrays, no structured references |
| Charts | Imported; colours may shift slightly | Data tables beside each chart carry the same numbers |
| Logo on the customer quote | Insert › Image › Image over cells | Guide explains both apps |

## 5. Choices made (no questions were needed)
- Money in the working tabs uses plain #,##0.00 with the currency symbol from SETTINGS in headings, tiles and the customer quote,
  so a non-US buyer can change it in one place.
- Equipment and overhead are charged on job hours including driving, so the working-hours figure (on site + driving) and the
  per-hour rates match.
- A "Target profit per job hour" setting drives the low-profit warning; an optional "your own price" input makes the
  below-break-even warning meaningful.
- Route planner totals are an average week (bi-weekly counts half) so revenue per hour is honest for mixed frequencies.
- Customer quote uses Arial and grey lines only, no brand colours or names, and it has no navigation sidebar.
- Logo: the supplied Brass Ledger logo PNG is used in the guide and images.

## 6. Reusing the engine (next product: pressure washing bids)
`engine.py` builds every tab from a config module. `lawn_config.py` holds everything lawn-specific. For pressure washing,
copy it to `pressure_config.py` and change: METHODS → surface types with sq ft per hour (driveway, siding, deck, roof) and
chemical/fuel use; MULTIPLIERS → dirt level, height/storeys, access; DETAIL_TASKS → setup, pre-treat, rinse; EXTRA → e.g.
sealing with its time multiplier and material cost; ADDONS, EQUIPMENT, OVERHEAD, sample data and wording. Then
`engine.main(pressure_config, out_dir)`. The tests' model mirrors the engine and can be pointed at the new config.
"""

(OUT / "etsy-listing.md").write_text(LISTING)
(OUT / "test-report.md").write_text(REPORT)
print("wrote etsy-listing.md and test-report.md")
