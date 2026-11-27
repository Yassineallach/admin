"""Lawn care trade config for the Brass Ledger pricing engine (engine.py).

Everything trade-specific lives here: product name, the main service and its production methods (mowers), the time
multipliers, detail tasks, the optional extra (bagging), add-on services, default costs, and the sample business.
A pressure washing bid calculator would copy this file and change the values: methods become surface types with
sq ft per hour, multipliers become dirt level / height, the extra becomes chemical treatment, and so on.

All defaults are EXAMPLE VALUES. Sources and reasoning are in the test report.
"""
import datetime as dt

PRODUCT = "Lawn Care Pricing Calculator"
OUT_NAME = "BrassLedger_Lawn_Care_Pricing_Calculator"
TRADE = "lawn care"

# ---------------------------------------------------------------- main service
SERVICE = "Mowing"                      # the time-on-site line for the main service
SERVICE_DESC = "Lawn mowing"            # first words of the line on the customer quote
AREA_LABEL = "Lawn area"
METHOD_LABEL = "Mower"
RATE_LABEL = "Mowing speed (sq ft per hour)"
FUEL_LABEL = "Fuel use (gallons per hour)"
# (name, sq ft per hour, gallons per hour). Speeds: mph x deck inches / 99 = acres per hour at 100 %, times a
# residential-lawn efficiency of 50-60 % (turns, overlap, small areas). See the test report.
METHODS = [
    ('21" push mower', 13000, 0.15),
    ('36" walk-behind', 30000, 0.6),
    ('48" stand-on', 42000, 1.0),
    ('52" zero-turn', 57000, 1.2),
    ('61" zero-turn', 70000, 1.5),
]
# multiplier groups: the first applies to detail work too (obstacles mean more trimming)
MULTIPLIERS = [
    ("Obstacles", [("Low", 1.00), ("Medium", 1.15), ("High", 1.30)]),
    ("Slope", [("Flat", 1.00), ("Moderate", 1.15), ("Steep", 1.35)]),
    ("Grass condition", [("Normal", 1.00), ("Overgrown", 1.50)]),
]
FIRST_MULT_ON_DETAIL = True
# detail tasks: (name, minutes per 1,000 sq ft of lawn, minimum minutes per visit, wording on the customer quote)
DETAIL_TASKS = [
    ("Trimming", 1.5, 8, "trimming"),
    ("Edging", 1.0, 5, "edging"),
    ("Blowing", 0.75, 4, "blowing off hard surfaces"),
]
EXTRA = dict(label="Bag clippings", mult_label="Bagging time multiplier", mult=1.20,
             cost_label="Disposal cost per visit when bagging", cost=5.00, desc="clippings bagged and removed")

# ---------------------------------------------------------------- add-ons
UNITS = ["flat", "per hour", "per 1,000 sq ft", "per cubic yard", "per bag"]
ADDONS = [
    ("Leaf removal", "per hour", 60.00, "Or switch to per bag"),
    ("Spring cleanup", "flat", 200.00, "Beds, debris, first cut"),
    ("Fall cleanup", "flat", 250.00, "Leaves, beds, last cut"),
    ("Aeration", "per 1,000 sq ft", 12.00, "Core aeration"),
    ("Overseeding", "per 1,000 sq ft", 15.00, "Seed included"),
    ("Fertilising", "per 1,000 sq ft", 6.00, "Licence may be required"),
    ("Mulching", "per cubic yard", 70.00, "Material and install"),
    ("Hedge and shrub trimming", "per hour", 55.00, ""),
    ("Weed pulling", "per hour", 45.00, "Beds, by hand"),
    ("Gutter cleaning", "flat", 160.00, "Single storey"),
]
LICENCE_NOTE = ("Fertilising and weed control may require a pesticide applicator licence in many US states. "
                "Check your state's rules before offering them.")

# ---------------------------------------------------------------- default costs
TARGETS = dict(hours=1200, owner_pay=25.00, helper_wage=17.00, payroll=0.12, margin=0.25, target_profit_hr=10.00,
               min_charge=40.00, rounding=5, season_weeks=30, prepay=0.05, crew_loss=0.10, drive_warn=0.25,
               season_start="April", season_end="November", monthly_goal=6000, valid_days=30, currency="$")
FUEL = dict(fuel_price=4.00, mpg=14, wear_mile=0.30)
EQUIPMENT = [
    ('52" zero-turn mower', 12000, 6, 600),
    ('21" push mower', 500, 4, 75),
    ("String trimmer", 380, 3, 50),
    ("Stick edger", 350, 4, 40),
    ("Backpack blower", 550, 4, 60),
    ("6x12 utility trailer", 2800, 12, 120),
    ("Hand tools, safety gear, fuel cans", 400, 2, 0),
]
OVERHEAD = [
    ("General liability insurance", 1200),
    ("Business licence and registration", 150),
    ("Phone (business share)", 600),
    ("Software and apps", 360),
    ("Marketing (cards, website, ads)", 600),
    ("Accounting and tax preparation", 500),
    ("Vehicle insurance (business share)", 1000),
    ("Other", 300),
]
TERMS = ("Prices are per visit unless shown otherwise. Payment due within 15 days of invoice. Visits missed for rain are "
         "moved to the next dry day. Either party may end recurring service with 14 days' notice.")
FREQS = ["Weekly", "Bi-weekly", "Monthly", "One-time"]
STATUSES = ["Sent", "Accepted", "Declined", "No reply"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

# ================================================================ SAMPLE business (fictional)
BUSINESS = dict(name="Greenline Lawn Co.", contact="Sam Rivera", phone="(555) 014-2290", email="sam@greenlinelawn.example",
                website="greenlinelawn.example", street="418 Orchard Lane", city="Springfield, OH 45503")
SEASON_YEAR = 2026

# the quote shown on QUICK QUOTE in the sample file
QUOTE = dict(date=dt.date(2026, 4, 6), number="Q-1042", client="Dana Whitfield", address="27 Maple Ridge Drive",
             sqft=9500, acres=None, method='52" zero-turn', mults=["Medium", "Flat", "Normal"],
             tasks=["Yes", "Yes", "Yes"], extra="No", crew=1, drive=12, miles=6, freq="Weekly", going=55, override=None,
             addons=[("Spring cleanup", None), ("Aeration", None), ("Mulching", 3)])

# quote log: (date, client, address, sq ft, frequency, price per visit, monthly price, add-ons, status, follow-up, notes)
LOG = [
    (dt.date(2026, 3, 9), "Marcus Lee", "14 Birch Court", 6200, "Weekly", 45, 195.00, 0, "Accepted", None, "Corner lot"),
    (dt.date(2026, 3, 12), "Priya Shah", "302 Hillside Avenue", 14500, "Bi-weekly", 70, 151.67, 200, "Accepted", None,
     "Wants spring cleanup"),
    (dt.date(2026, 3, 18), "Tom Becker", "9 Willow Way", 22000, "Weekly", 95, 411.67, 0, "Declined", None,
     "Said too high; has a neighbour kid"),
    (dt.date(2026, 3, 25), "Hannah Ortiz", "61 Elm Street", 4800, "Weekly", 40, 173.33, 0, "Accepted", None, ""),
    (dt.date(2026, 4, 1), "Greg Novak", "1100 Ridge Road", 35000, "Weekly", 125, 541.67, 340, "Declined", None,
     "Steep back hill"),
    (dt.date(2026, 4, 6), "Dana Whitfield", "27 Maple Ridge Drive", 9500, "Weekly", 50, 216.67, 524, "Sent",
     dt.date(2026, 4, 13), "Call Monday"),
]

# route planner: (weekday, stop, client, area, price per visit, minutes on site, drive minutes from previous stop, frequency)
ROUTE = [
    ("Monday", 1, "Marcus Lee", "Birch Hill", 45, 30, 12, "Weekly"),
    ("Monday", 2, "Hannah Ortiz", "Birch Hill", 40, 25, 4, "Weekly"),
    ("Monday", 3, "Okafor family", "Birch Hill", 50, 35, 3, "Weekly"),
    ("Monday", 4, "R. Delgado", "Old Mill", 55, 40, 9, "Weekly"),
    ("Tuesday", 1, "Priya Shah", "Hillside", 70, 50, 15, "Bi-weekly"),
    ("Tuesday", 2, "Westview Church", "Hillside", 110, 75, 6, "Weekly"),
    ("Tuesday", 3, "J. Kim", "Lakeshore", 45, 30, 18, "Weekly"),
    ("Tuesday", 4, "Lakeshore HOA strip", "Lakeshore", 85, 60, 5, "Weekly"),
    ("Thursday", 1, "Dana Whitfield", "Maple Ridge", 50, 35, 12, "Weekly"),
    ("Thursday", 2, "Carter home", "Maple Ridge", 45, 30, 3, "Weekly"),
    ("Thursday", 3, "B. Lindqvist", "Maple Ridge", 60, 40, 4, "Bi-weekly"),
    ("Thursday", 4, "Fischer duplex", "Downtown", 40, 25, 22, "Weekly"),
    ("Friday", 1, "Rosewood Dental", "Commerce Park", 95, 60, 20, "Weekly"),
    ("Friday", 2, "Patel residence", "Far Hills", 65, 45, 28, "Weekly"),
    ("Friday", 3, "M. Greene", "Far Hills", 55, 40, 7, "Monthly"),
]

# season tracker: month -> (active clients, mowing revenue, add-on revenue, goal)
SEASON = {
    "January": (0, 0, 0, 0), "February": (0, 0, 0, 0), "March": (4, 0, 1450, 1500),
    "April": (11, 3480, 2650, 6000), "May": (14, 4820, 900, 6000), "June": (15, 5260, 420, 6000),
    "July": (15, 5180, 310, 6000), "August": (15, 5340, 260, 6000), "September": (15, 5110, 880, 6000),
    "October": (14, 4390, 2240, 6000), "November": (9, 1720, 3150, 4000), "December": (0, 0, 0, 0),
}
