"""Write etsy-listing.md and test-report.md for the Cake Pricing Calculator (numbers from test_results.json)."""
import json
from pathlib import Path

import cake_config as CFG

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "cake-pricing-calculator"
RES = json.loads((ROOT / "dist" / "test_results.json").read_text())

TITLE = ("Cake Pricing Calculator Spreadsheet, Home Bakery Recipe Cost Calculator, Tiered Cake Servings & Price, "
         "Order Tracker, Excel & Google Sheets")
TAGS = ["cake pricing", "bakery pricing", "cake business", "recipe cost", "home bakery", "cupcake pricing",
        "cake price sheet", "baking business", "cottage bakery", "cake order tracker", "cake servings chart",
        "bakery spreadsheet", "cake quote template"]
assert len(TITLE) <= 140, len(TITLE)
assert len(TAGS) == 13 and len(set(TAGS)) == 13 and all(len(t) <= 20 for t in TAGS), [t for t in TAGS if len(t) > 20]


def money(x):
    return f"${x:,.2f}"


w, b = RES["cakes"][0], RES["cakes"][1]
cup = RES["batches"][0]

LISTING = f"""# Etsy listing: Cake Pricing Calculator

## Title ({len(TITLE)} of 140 characters)
{TITLE}

## Tags (13, each 20 characters or fewer)
{chr(10).join(f"{i + 1}. {t} ({len(t)})" for i, t in enumerate(TAGS))}

## Photos (in this order)
| # | File | Shows |
|---|------|-------|
| 1 | 01_hero.png | Promise, three benefits, CAKE BUILDER on a laptop, Excel + Google Sheets badge |
| 2 | 02_whats_included.png | The nine tabs and the files in the download |
| 3 | 03_cake_builder.png | CAKE BUILDER price section with callouts on servings, price per serving and hourly earnings |
| 4 | 04_ingredients_recipes.png | INGREDIENTS with grams per cup and a costed recipe block |
| 5 | 05_quote_orders.png | The printable customer quote and the order tracker |
| 6 | 06_compatibility.png | Excel and Google Sheets, US and metric, best on a computer, digital download |
| 7 | 07_what_you_receive.png | Files list, instant download, no physical item |

## Description

Know what every cake really costs, and what to charge for it.

Pricing by ingredients alone leaves out your hours, boards and boxes, decorations, electricity and delivery, so cakes get underpriced and prices are hard to explain. This spreadsheet costs every ingredient, every recipe and every tier, adds your time at your own hourly rate, and gives you a price per serving you can stand behind.

━━━━━━━━━━━━━━━━━━━━
WHO IT'S FOR
━━━━━━━━━━━━━━━━━━━━
Home bakers and small cake businesses selling custom cakes, cupcakes and cookies for birthdays, weddings, baby showers and holidays. Works in US and metric units (US, UK, Canada, Australia). No spreadsheet skills needed: you fill in white cells and pick from dropdowns.

━━━━━━━━━━━━━━━━━━━━
WHAT IT DOES
━━━━━━━━━━━━━━━━━━━━
✔ Ingredient library: enter each ingredient once with what you pay; cost per gram, ml and item worked out for you
✔ Unit conversion: recipes can use cups, spoons, grams, ounces, ml or eggs; 48 common ingredients come with grams per cup
✔ Recipe library: 40 recipes (batters, fillings, frostings, ganache, fondant, cookie dough, royal icing) costed line by line, with cost per cup, gram or item
✔ Tiered cake builder: up to 5 tiers and 3 cakes; pan sizes 4"-16" round, square, sheet and heart with batter, filling, frosting, fondant and servings
✔ Party or wedding servings from a standard serving chart (editable)
✔ Decoration levels, extras (sugar flowers, toppers, drips, gold leaf), supplies (boards, drums, boxes, dowels), labour by task, overhead and delivery
✔ Suggested price at your margin, rounded up; price per serving checked against your minimum; your real hourly earnings; deposit and balance
✔ Red warnings when the price per serving or your hourly earnings fall too low
✔ Batch pricing for cupcakes, cookies, cake pops and brownies: per item, half dozen and dozen
✔ A one-page customer quote with YOUR bakery name, tiers, flavours, servings, deposit, allergen notes and terms (letter or A4)
✔ Order tracker: 300 orders with deposits, balances, statuses, orders due this week and an upcoming list by date
✔ Dashboard: orders and revenue this month and this year, average order, average price per serving, deposits not yet paid

━━━━━━━━━━━━━━━━━━━━
WHAT MAKES IT DIFFERENT
━━━━━━━━━━━━━━━━━━━━
• Ingredients are entered once and every recipe, cake and batch uses them
• The tier builder knows pan sizes, batter amounts and servings, so a 3-tier cake is priced in minutes
• Price per serving and your hourly earnings, not just a total
• Quotes, deposits and orders in the same file

━━━━━━━━━━━━━━━━━━━━
WHAT'S INCLUDED
━━━━━━━━━━━━━━━━━━━━
• Blank workbook (.xlsx) with 9 tabs: Start Here, Settings, Ingredients, Recipes, Cake Builder, Batch Pricing, Customer Quote, Order Tracker, Dashboard
• Sample workbook (.xlsx): a fictional bakery with priced ingredients, 9 recipes, a 3-tier wedding cake, a birthday cake, two batches and 15 orders
• Quick-start guide (PDF, 11 pages): your rate and margin, ingredients, recipes, a worked tiered cake, cupcakes by the dozen, quotes, orders, explaining your price, FAQ

━━━━━━━━━━━━━━━━━━━━
HOW DELIVERY WORKS
━━━━━━━━━━━━━━━━━━━━
1. Buy, then download the files from Etsy › You › Purchases and reviews. Nothing is shipped.
2. Open the .xlsx in Excel, or use the Google Sheets copy link in the guide (File › Make a copy).
3. Set your rate on Settings, add your ingredient prices, then build your first recipe.

━━━━━━━━━━━━━━━━━━━━
COMPATIBILITY
━━━━━━━━━━━━━━━━━━━━
• Microsoft Excel 2016 or later (Windows and Mac), Excel for the web
• Google Sheets (free Google account)
• US units (cups, oz, lb) or metric (g, kg, ml); US and metric cups
• Best on a computer; it opens in the phone apps but costing is easier on a laptop
• No macros, no add-ons

━━━━━━━━━━━━━━━━━━━━
FAQ
━━━━━━━━━━━━━━━━━━━━
My price comes out higher than the supermarket.
It should: your cake is designed and made to order, with your hours in it. The guide shows how to explain it with price per serving.

I bake in grams.
Set the unit system to Metric. Recipes can mix units; costs don't change.

Can I add my own pan sizes, decorations and supplies?
Yes, there are empty rows in each table on Settings.

Are ingredient prices included?
The sample file has example prices. The blank file has names and conversions ready for your own prices.

Can I get a refund?
Because this is a digital download, refunds aren't offered, but message me if anything doesn't work and I'll help.

━━━━━━━━━━━━━━━━━━━━
PLEASE NOTE
━━━━━━━━━━━━━━━━━━━━
Prices are estimates based on your inputs. Not financial, legal or tax advice. No specific earnings are promised.

Cottage food reminder: what you can sell from home, labelling and allergen rules, sales limits and permits vary by state and country. Check your local rules, and always ask customers about allergies.

Designed by Brass Ledger with help from AI tools; every formula was built and tested by the seller.

## Price
**Suggested: $17.00** (your range $14–19; competitors around $12).
- Clearly more than the $12 sheets: an ingredient library with conversion, a recipe library, a tier builder with servings, batch pricing, quotes and an order tracker. Pricing at $12 would undersell that.
- $17 matches the Lawn Care and Pressure Washing calculators, so the shop reads as one range.
- It leaves room for a 20–25 % launch sale (about $13) that still beats competitors on value, not price.
- A home baker recovers it on one cake priced correctly. Consider $19 once the listing has reviews.

## Etsy attributes
- Category: **Paper & Party Supplies › Paper › Stationery › Design & Templates › Templates** (the path Etsy suggests for spreadsheet templates; pick the closest "Templates" option it offers)
- Type: Digital download
- File types: XLSX, PDF
- Who made it: I did · What is it: A finished product · When was it made: 2020–2026
- Designed by seller: Yes
- Renewal: automatic
"""

conv = "\n".join(f"| {a} | {h} | {money(c) if c is not None else 'message: add grams per cup'} |" for a, h, c in RES["conversions"])
rec = "\n".join(f"| {n} | {money(v)} |" for n, v in RES["recipes"].items())
tiers = "\n".join(f"| {d[1]} {d[0].lower()} | {t['v'] / 236.588:.2f} cups | {t['w'] / 236.588:.2f} cups | {t['x'] / 236.588:.3f} cups | "
                  f"{t['y']:.0f} g | {money(t['cost'])} | {t['serv']} |" for d, t in zip(CFG.CAKES[0]["tiers"], RES["tiers"][0]))

REPORT = f"""# Test report: Cake Pricing Calculator

Result: **{RES['passed']} checks passed, {RES['failed']} failed.**
Formulas: blank file {RES['BrassLedger_Cake_Pricing_Calculator.xlsx']:,}, sample file {RES['BrassLedger_Cake_Pricing_Calculator_SAMPLE.xlsx']:,}.

## 1. Unit conversions (worked by hand, placed in a test recipe, compared with the workbook)
| Line | How | Cost |
|---|---|---|
{conv}

## 2. Recipes (independent Python model vs workbook, every line and total)
| Recipe | Cost |
|---|---|
{rec}

## 3. The 3-tier wedding cake (sample, cake 1)
| Tier | Batter | Filling | Frosting | Fondant | Ingredients | Wedding servings |
|---|---|---|---|---|---|---|
{tiers}

Ingredients {money(w['ing'])} + extras {money(w['dec'])} + supplies {money(w['sup'])} + labour {w['hours']:.1f} h × $25 = {money(w['lab'])}
+ overhead {money(w['oh'])} + delivery {money(w['deliv'])} = **cost {money(w['cost'])}**. ÷ (1 − 20 %), rounded up to $5:
**{money(w['price'])}**; {w['servings']} servings; **{money(w['per_serving'])} per serving**; profit {money(w['profit'])};
**hourly earnings {money(w['hourly'])}**; deposit {money(w['deposit'])}; balance {money(w['balance'])}.
Birthday cake (cake 2): cost {money(b['cost'])}, price {money(b['price'])}, {b['servings']} party servings, {money(b['per_serving'])} per serving.
Cupcakes: {cup['items']:.0f} items, cost {money(cup['cost'])} ({money(cup['cost_item'])} each), {money(cup['p_item'])} each,
{money(cup['p_half'])} per half dozen, **{money(cup['p_dozen'])} per dozen**.

## 4. Everything else checked
1. **Both files recalculated in LibreOffice headless:** 0 formula errors, no error value in any cell.
2. **All 48 ingredients:** cost per g, ml and item match the model.
3. **Both cakes and both batches:** every quantity, cost, servings, price, per serving, profit, hours, hourly earnings, deposit and
   balance; unused tiers blank.
4. **Metric switch:** every cost and price identical; quantities shown in ml and g; headers change; batch prices identical.
5. **Edge cases:** sprinkles (no grams per cup) used in cups shows "–" and a message, the recipe total goes blank (never understated),
   and the cake and batch using it show red warnings; margin 0 %; a pan size missing from the table ("no such pan" and a
   warning); an empty cake slot asks for a tier; your own price below cost turns the warning red.
6. **Ingredient price change** (butter $5 → $7 a pound): every recipe, both cakes, the cupcake cost per item and the customer
   quote total updated (wedding cake {money(RES['price_change']['cake1'][0])} → {money(RES['price_change']['cake1'][1])}).
7. **Customer quote:** total, deposit, balance, servings, tier lines, extras with quantities; switching to cake 2 shows its price
   and customer; prints on exactly **one letter page and one A4 page**; no "Brass Ledger" text.
8. **Order tracker and dashboard:** balance per order, upcoming list sorted by event date, balances and deposits tiles, all seven
   dashboard tiles (relative to the day the test ran), orders by type, 2 charts.
9. **Blank file:** names and grams per cup prefilled with no prices; ingredient costs, 40-recipe index, recipe lines, all three cake
   slots, batch outputs, 300 order rows and the upcoming list are blank (no zeros, no errors); the quote shows "Your bakery name".
10. **Structure and layout:** no macros, no Excel Tables, no external links, no LAMBDA/LET/XLOOKUP/FILTER/TEXT()/INDIRECT/OFFSET
    (the structure check flags 12 cells because "ISTEXT(" contains "TEXT("; ISTEXT is a standard function in both apps); every tab
    protected without a password; header rows frozen; dropdowns on every list field; layout lint: 0 problems in both files;
    no "###" in any printed tab.

## 5. How the costing works
- Units table (SETTINGS): every unit is a weight in g, a volume in ml or a count. cup = US cup 236.588 ml; metric cup 250 ml.
- Ingredient cost per g = price ÷ package grams (by weight), or price ÷ (package ml ÷ 236.588 × grams per cup) (by volume), or
  price ÷ (items × grams per item) (by count). Cost per ml and per item follow from cost per g with grams per cup / per item.
- Recipe line = quantity × unit size × the ingredient's cost per g, ml or item. Missing price or conversion → "–" and a message.
- Recipe yield (cups, ml, g, items) gives cost per ml, g or item.
- Tier: batter = layers × batter per 2" layer; filling = (layers − 1) × filling per layer; frosting = frosting to cover a 4" tier ×
  covering factor × layers ÷ 2; fondant (fondant coverings) = fondant to cover × layers ÷ 2; servings = chart × layers ÷ 2,
  rounded down.
- Labour = (task hours, decorating × level multiplier) × hourly rate. Overhead per hour or per order. Delivery = miles × rate
  (+ set-up fee).
- Price = cost ÷ (1 − margin) rounded up; hourly earnings = (price − costs other than labour) ÷ hours; deposit = price × deposit %.
- Batch: items = batches × items per batch; frosting = items × amount × unit × frosting cost per ml (or g); packaging per dozen;
  price per item, half dozen and dozen rounded up separately.

## 6. Default values and where they come from
All defaults are labelled "example values, check and adjust" (prices) or "typical values, adjust to your recipes and cutting
style" (pans and servings).

| Data | Source / reasoning |
|---|---|
| Grams per cup (48 ingredients) | King Arthur Baking ingredient weight chart (flour 120 g, granulated sugar 198 g, brown sugar 213 g, powdered sugar 113 g, butter 227 g, cocoa 84 g, milk 227 g, chocolate chips 170 g, baking powder 4 g/tsp, baking soda and table salt 6 g/tsp ...); large egg ≈ 50 g |
| US units | cup 236.588 ml, tbsp 14.787 ml, tsp 4.929 ml, fl oz 29.574 ml, oz 28.3495 g, lb 453.592 g (US customary definitions); metric cup 250 ml |
| Ingredient prices | Seller's example US supermarket prices (autumn 2026); replace with your own |
| Batter per 2" layer, round | Wilton baking chart for 2-inch pans (6" 2 cups, 8" 3, 9" 4.5, 10" 6, 12" 7.5, 14" 10, 16" 15); squares scaled by area (× 4/π); sheets and hearts typical values |
| Servings | Wilton cake serving charts: party (≈1.5 × 2 in slices) and wedding (≈1 × 2 in) for 4-inch-tall tiers, e.g. round 8" 20 / 24, 10" 28 / 38, 12" 40 / 56 |
| Filling, frosting, fondant | Calculated from pan area and sides: filling ¼ inch per layer; frosting ≈ 0.3 inch over top and sides of a 4-inch tier; fondant ≈ 4.5 g per square inch covered (8" round ≈ 680 g / 24 oz, in line with Wilton's fondant chart) |
| Coverings | Seller estimates: buttercream 1.0; fondant 0.5 (thin crumb coat) + fondant; semi-naked 0.6; naked 0.3 |
| Rates | $25/h, 20 % margin, $4.50 minimum per serving, 50 % deposit, overhead $2,000/yr over 800 h, $1/mile and $25 set-up: seller's starting points for a home bakery |

## 7. Google Sheets: what can differ, and how it's handled
| Feature | In Google Sheets | Handling |
|---|---|---|
| Icon sidebar (drawn shapes) | Dropped | Text links underneath |
| Sheet protection | Not carried over | Shaded cells clearly marked |
| Data bars | Dropped | Not used for key numbers |
| SMALL + MATCH upcoming list | Works the same | No SORT/FILTER needed |
| COUNTIFS with an array constant (open orders tile) | Supported | — |
| Dropdowns from ranges with blank rows | Show blank entries at the end | Fixed ranges so new ingredients and recipes appear automatically |
| Print settings (one page, letter or A4) | Not imported | Guide: File › Print, Scale "Fit to page" |
| Hyperlinks to recipe blocks | Work as internal links | — |

## 8. Choices made (no questions were needed)
- **Recipes layout:** an index at the top plus 40 fixed blocks of 16 lines on one tab (explained on START HERE). Fixed blocks keep
  every formula simple and identical in Excel and Google Sheets.
- **Three cake slots** on CAKE BUILDER, so the sample can hold the wedding and birthday cakes at once; CUSTOMER QUOTE picks one.
- **Shape and size are separate dropdowns** matched against the pan table; a missing combination says "no such pan".
- **Layers are 2-inch layers**; servings and covering scale with layers ÷ 2 (the charts are for 4-inch tiers).
- **Unit system** changes what is displayed (cups/oz vs ml/g); all costs are worked in g, ml and items, so they never change.
- **"Your own price"** lets a baker test an agreed price; it's what makes the hourly-earnings warning useful.
- Logo: the Brass Ledger logo PNG in the brand folder is used in the guide and images.
"""

(OUT / "etsy-listing.md").write_text(LISTING)
(OUT / "test-report.md").write_text(REPORT)
print("wrote etsy-listing.md and test-report.md")
