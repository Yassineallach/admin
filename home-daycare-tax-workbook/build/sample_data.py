"""Sample provider for the SAMPLE workbook: Little Acorns Family Child Care (fictional), tax year 2026.

Everything is invented but realistic. The same functions feed the workbook and the independent test model, so the test
compares the workbook's formulas with plain Python arithmetic on identical inputs.
"""
import datetime as dt

D, T = dt.date, dt.time
YEAR = 2026
BUSINESS = "Little Acorns Family Child Care"
RATES_CHECKED = D(2026, 11, 2)
CACFP_REIMB = 2450.00
HOME_SQFT = 2000

# Monday..Sunday: (children arrive, children leave, other business hours)
USUAL = [(T(7, 0), T(17, 30), 1.5)] * 5 + [(None, None, 2.0), (None, None, None)]

ROOMS = [
    ("Playroom (converted den)", 320, "Exclusive child care", "Toys and cots stored here; no family use"),
    ("Living room", 380, "Regular child care + family", "Circle time and reading"),
    ("Kitchen", 220, "Regular child care + family", "Meals and snacks"),
    ("Dining area", 160, "Regular child care + family", "Crafts and meals"),
    ("Guest bedroom (nap room)", 150, "Regular child care + family", "Naps every weekday"),
    ("Hall bathroom", 60, "Regular child care + family", ""),
    ("Entry and hallway", 90, "Regular child care + family", "Cubbies"),
    ("Laundry room", 50, "Regular child care + family", "Daily daycare laundry"),
    ("Primary bedroom", 310, "Not used for child care", ""),
    ("Child's bedroom", 170, "Not used for child care", ""),
    ("Primary bathroom", 70, "Not used for child care", ""),
    ("Storage closet", 20, "Not used for child care", ""),
]

CLOSED = {D(2026, 1, 1): "New Year's Day", D(2026, 2, 16): "Sick day", D(2026, 5, 25): "Memorial Day",
          D(2026, 7, 3): "Independence Day (observed)", D(2026, 9, 7): "Labor Day", D(2026, 10, 12): "Sick day",
          D(2026, 11, 26): "Thanksgiving", D(2026, 11, 27): "Day after Thanksgiving", D(2026, 12, 24): "Christmas Eve",
          D(2026, 12, 25): "Christmas Day", D(2026, 12, 31): "New Year's Eve"}
for i in range(5):
    CLOSED[D(2026, 7, 6) + dt.timedelta(days=i)] = "Summer vacation"
UNCONFIRMED_FROM = D(2026, 12, 28)          # the last few days are left for the provider to check


def days():
    d = D(YEAR, 1, 1)
    while d.year == YEAR:
        yield d
        d += dt.timedelta(days=1)


def is_late_friday(d):
    return d.weekday() == 4 and ((d - D(YEAR, 1, 2)).days // 7) % 2 == 0 and d not in CLOSED


def hours_rows():
    """Inputs for each row of the HOURS LOG, in date order."""
    rows = []
    first_monday_seen, first_sat_seen = set(), set()
    for d in days():
        row = {}
        wd = d.weekday()
        if d in CLOSED:
            row.update(closed="Y", notes=CLOSED[d])
        else:
            if is_late_friday(d):
                row.update(start=T(7, 0), end=T(18, 15), notes="Late pickup")
            if wd == 0 and d.month not in first_monday_seen:
                first_monday_seen.add(d.month)
                row.update(other=3.0, what="Parent meetings", notes="Enrollment interviews and parent conferences")
            if wd == 5 and d.month not in first_sat_seen:
                first_sat_seen.add(d.month)
                row.update(other=4.5, what="Cleaning", notes="Monthly deep clean of playroom and kitchen")
        if d < UNCONFIRMED_FROM and wd != 6:
            row["conf"] = "Yes"
        rows.append(row)
    return rows


def money(x):
    return round(x, 2)


EXPENSES = []          # (date, vendor, description, amount, type, category, receipt saved, notes)


def add(d, vendor, desc, amount, typ, cat, receipt="Y", notes=""):
    EXPENSES.append((d, vendor, desc, money(amount), typ, cat, receipt, notes))


ELEC = [212.40, 188.15, 164.90, 141.20, 138.75, 176.30, 224.85, 231.10, 189.60, 150.25, 158.40, 201.95]
GAS = [118.20, 104.75, 88.40, 61.30, 44.85, 38.20, 35.10, 36.40, 41.75, 58.90, 86.30, 109.60]
for m in range(12):
    add(D(YEAR, m + 1, 8), "City Power & Light", "Electric bill", ELEC[m], "Indirect home", "Utilities")
    add(D(YEAR, m + 1, 12), "Metro Gas", "Gas bill", GAS[m], "Indirect home", "Utilities")
    add(D(YEAR, m + 1, 15), "Valley Water", "Water and sewer", 58.40 + (m % 3) * 6.15, "Indirect home", "Utilities")
    add(D(YEAR, m + 1, 20), "Riverline Internet", "Internet service", 69.99, "Indirect home", "Utilities")
    add(D(YEAR, m + 1, 3), "Craft Corner", "Craft and art supplies", 38.50 + (m % 4) * 7.25, "Direct (business only)", "Craft and learning supplies")
    add(D(YEAR, m + 1, 6), "SaveMore Market", "Cleaning products and paper towels", 42.80 + (m % 3) * 4.10, "Shared household", "Household supplies")
    add(D(YEAR, m + 1, 26), "SaveMore Market", "Groceries for daycare meals", 318.40 + (m % 5) * 11.30, "Direct (business only)", "Food (actual receipts)",
        notes="Child care share only")
for q, mm in enumerate([1, 4, 7, 10]):
    add(D(YEAR, mm, 28), "County Waste", "Trash service (quarter)", 96.00, "Indirect home", "Utilities")
add(D(YEAR, 2, 14), "Kidstuff Supply", "Nap cots (4)", 179.96, "Direct (business only)", "Toys and play equipment")
add(D(YEAR, 3, 9), "Kidstuff Supply", "Toddler climber and blocks", 264.30, "Direct (business only)", "Toys and play equipment")
add(D(YEAR, 6, 2), "Book Barn", "Picture books", 86.45, "Direct (business only)", "Craft and learning supplies")
add(D(YEAR, 8, 18), "Kidstuff Supply", "Outdoor play set: sandbox toys", 74.20, "Direct (business only)", "Toys and play equipment")
add(D(YEAR, 1, 10), "State Licensing Office", "Family child care license renewal", 50.00, "Direct (business only)", "Licenses and permits")
add(D(YEAR, 1, 22), "Provider Mutual", "Child care liability insurance", 725.00, "Direct (business only)", "Liability insurance")
add(D(YEAR, 3, 21), "Red Cross", "Pediatric CPR and first aid", 65.00, "Direct (business only)", "Training and education")
add(D(YEAR, 9, 26), "Early Learning Assoc.", "Annual conference", 145.00, "Direct (business only)", "Training and education")
add(D(YEAR, 5, 14), "Discovery Museum", "Field trip admission", 48.00, "Direct (business only)", "Field trips and activities")
add(D(YEAR, 4, 4), "QuickPrint", "Enrollment flyers", 35.80, "Direct (business only)", "Advertising")
add(D(YEAR, 2, 27), "Office Depot", "Printer ink and binders", 52.35, "Direct (business only)", "Office expense")
add(D(YEAR, 3, 30), "Lane Tax Services", "Prior-year tax preparation", 275.00, "Direct (business only)", "Legal and professional fees")
add(D(YEAR, 12, 31), "Hometown Bank", "Mortgage interest (Form 1098)", 9840.00, "Indirect home", "Mortgage interest")
add(D(YEAR, 4, 10), "County Treasurer", "Property tax, first half", 1965.00, "Indirect home", "Real estate taxes")
add(D(YEAR, 10, 10), "County Treasurer", "Property tax, second half", 1965.00, "Indirect home", "Real estate taxes")
add(D(YEAR, 5, 1), "Harbor Insurance", "Homeowner's insurance", 1620.00, "Indirect home", "Home insurance")
add(D(YEAR, 3, 17), "Comfort HVAC", "Furnace service", 189.00, "Indirect home", "Home repairs and maintenance")
add(D(YEAR, 10, 24), "Clear Gutters", "Gutter cleaning", 150.00, "Indirect home", "Home repairs and maintenance")
add(D(YEAR, 6, 20), "Pro Painters", "Repaint playroom", 240.00, "Direct home: exclusive area", "Home repairs and maintenance")
add(D(YEAR, 8, 5), "Handy Fix", "Repair nap room door", 85.00, "Direct home: shared area", "Home repairs and maintenance")
add(D(YEAR, 9, 14), "Appliance Depot", "Washing machine", 650.00, "Shared household", "Equipment and furniture",
    notes="Used daily for daycare laundry")
add(D(YEAR, 5, 9), "Gift Shop", "Birthday gift for my sister", 40.00, "Personal", "Personal (not deductible)")
add(D(YEAR, 11, 2), "SaveMore Market", "Family groceries", 126.75, "Personal", "Personal (not deductible)")
add(D(YEAR - 1, 12, 20), "Kidstuff Supply", "Holiday toys (bought last year)", 60.00, "Direct (business only)", "Toys and play equipment",
    notes="Last year's receipt: not counted")
EXPENSES.sort(key=lambda e: e[0])

# MEALS
CHILDREN = [("Ava", "N", "N", "Full time"), ("Ben", "N", "N", "Full time"), ("Chloe", "N", "N", "Mon, Wed, Fri"),
            ("Diego", "N", "N", "Full time"), ("Ella", "N", "N", "Tue, Thu"), ("Finn", "N", "N", "Full time"),
            ("Mia (my daughter)", "Y", "N", "Lives here: not eligible"), ("Leo (nephew)", "N", "Y", "Care as a favour: not eligible")]
SCHEDULE = {"Ava": {0, 1, 2, 3, 4}, "Ben": {0, 1, 2, 3, 4}, "Chloe": {0, 2, 4}, "Diego": {0, 1, 2, 3, 4}, "Ella": {1, 3},
            "Finn": {0, 1, 2, 3, 4}}


def absent(child, d):
    return (d.toordinal() * 7 + len(child) * 13) % 53 == 0       # about one day in 53, deterministic


def meal_rows():
    rows = []
    for d in days():
        if d.weekday() > 4 or d in CLOSED:
            continue
        for child, wds in SCHEDULE.items():
            if d.weekday() in wds and not absent(child, d):
                late = is_late_friday(d) and child == "Finn"
                rows.append((d, child, 1, 1, 1 if late else 0, 3 if late else 2, "Stayed for dinner" if late else ""))
        if D(YEAR, 6, 15) <= d <= D(YEAR, 8, 14):
            rows.append((d, "Mia (my daughter)", 0, 1, 0, 1, "Summer"))
        if d.month == 3 and d.weekday() == 4:
            rows.append((d, "Leo (nephew)", 0, 1, 0, 1, ""))
    return rows


# MILEAGE: (date, purpose, from, to, miles)
TRIPS = []
for i, d in enumerate([D(YEAR, 1, 9)] + [D(YEAR, m, 3 + (m % 4)) for m in range(1, 13)]):
    TRIPS.append((d, "Groceries for daycare meals", "Home", "SaveMore Market", 6.2))
for m in range(1, 13):
    TRIPS.append((D(YEAR, m, 17), "Craft and toy supplies", "Home", "Craft Corner", 9.4))
TRIPS += [(D(YEAR, 3, 21), "CPR and first aid class", "Home", "Red Cross center", 18.5),
          (D(YEAR, 9, 26), "Early learning conference", "Home", "Convention center", 42.0),
          (D(YEAR, 5, 14), "Field trip", "Home", "Discovery Museum", 14.8),
          (D(YEAR, 1, 10), "License renewal", "Home", "State licensing office", 23.6),
          (D(YEAR, 8, 18), "Outdoor toys", "Home", "Kidstuff Supply", 11.3),
          (D(YEAR, 2, 14), "Nap cots", "Home", "Kidstuff Supply", 11.3)]
TRIPS.sort(key=lambda t: t[0])

PREPARER = dict(buy_date=D(2014, 6, 15), price=285000.00, land=60000.00, first_use=D(2019, 9, 3), prior_ts=0.3412,
                prior_simple="No", co_ops=0.0, co_dep=0.0, fees=58240.00, grants=1200.00, other_inc=None)
IMPROVEMENTS = [("New roof", D(2021, 5, 20), "Whole house", 12400.00), ("Fenced play yard", D(2023, 4, 11), "Yard", 4800.00)]
