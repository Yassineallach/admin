"""Pressure washing / soft washing trade config for the Brass Ledger pricing engine (pw_engine.py).

All defaults are EXAMPLE VALUES. Sources and reasoning are in the test report.
"""
import datetime as dt

PRODUCT = "Pressure Washing Bid Calculator"
OUT_NAME = "BrassLedger_Pressure_Washing_Bid_Calculator"
GUIDE_NAME = "BrassLedger_Pressure_Washing_Quick_Start_Guide.pdf"
TRADE = "pressure washing"

# ---------------------------------------------------------------- services
# (service, category, unit, units per hour, chemicals/materials per 1,000 units, local going rate per unit, flatwork)
SERVICES = [
    ("Concrete driveway", "Flatwork", "sq ft", 1000, 3.00, 0.20, "Yes"),
    ("Sidewalk / walkway", "Flatwork", "sq ft", 700, 3.00, 0.20, "Yes"),
    ("Patio", "Flatwork", "sq ft", 800, 3.00, 0.30, "Yes"),
    ("Pool deck", "Flatwork", "sq ft", 700, 4.00, 0.35, "Yes"),
    ("Garage floor", "Flatwork", "sq ft", 500, 8.00, 0.40, "Yes"),
    ("Pavers: clean only", "Pavers", "sq ft", 500, 4.00, 0.40, "Yes"),
    ("Pavers: clean + re-sand", "Pavers", "sq ft", 250, 350.00, 1.00, "Yes"),
    ("Pavers: clean + re-sand + seal", "Pavers", "sq ft", 150, 650.00, 1.90, "Yes"),
    ("House wash (soft wash)", "House wash", "wall sq ft", 1200, 10.00, 0.12, "No"),
    ("Roof soft wash", "Roof", "roof sq ft", 1200, 30.00, 0.45, "No"),
    ("Deck clean", "Wood", "sq ft", 300, 8.00, 0.60, "No"),
    ("Deck clean + stain/seal", "Wood", "sq ft", 100, 300.00, 2.25, "No"),
    ("Fence clean", "Wood", "face sq ft", 400, 8.00, 0.45, "No"),
    ("Gutter brightening", "Gutters", "linear ft", 120, 15.00, 1.00, "No"),
    ("Commercial flatwork", "Commercial", "sq ft", 1500, 2.00, 0.12, "Yes"),
    ("Dumpster pad", "Commercial", "sq ft", 300, 20.00, 0.60, "Yes"),
    ("Drive-thru lane", "Commercial", "sq ft", 1000, 8.00, 0.18, "Yes"),
    ("Window / screen rinse", "Add-on", "per item", 12, 0.00, 5.00, "No"),
    ("Outdoor furniture set", "Add-on", "per item", 3, 0.00, 25.00, "No"),
    ("Trash bin cleaning", "Add-on", "per item", 10, 0.00, 15.00, "No"),
]
UNITS = ["sq ft", "wall sq ft", "roof sq ft", "face sq ft", "linear ft", "per item", "flat"]
CATEGORIES = ["Flatwork", "Pavers", "House wash", "Roof", "Wood", "Gutters", "Commercial", "Add-on"]
# condition: (name, time multiplier, chemical multiplier)
CONDITIONS = [("Light", 0.80, 0.80), ("Normal", 1.00, 1.00), ("Heavy", 1.40, 1.50)]
DEFAULT_CONDITION = "Normal"
# height / access: (name, time multiplier)
ACCESS = [("Ground level", 1.00), ("2 storeys", 1.30), ("3 storeys", 1.60), ("Ladder work", 1.20),
          ("Steep roof pitch", 1.40), ("Lift needed", 1.50), ("Difficult access", 1.25)]
# stain treatment: (stain, unit, minutes per unit, material cost per unit)
STAINS = [("Oil", "per spot", 10, 3.00), ("Rust", "per sq ft", 0.5, 0.60), ("Gum", "per spot", 1, 0.05),
          ("Organic (leaves, berries)", "per sq ft", 0.1, 0.04)]
STAIN_UNITS = ["per spot", "per sq ft"]

COMPLIANCE = [
    "Wash water: many cities regulate runoff into storm drains. Check local rules; you may need to block drains and recover water.",
    "Soft wash chemicals can harm plants and surfaces: pre-wet, rinse well and protect plants.",
    "Older homes: washing painted surfaces may disturb lead-based paint. Check the rules that apply before taking these jobs.",
    "Carry liability insurance. Some areas also require a business licence.",
]

# ---------------------------------------------------------------- default costs
TARGETS = dict(hours=1100, owner_pay=35.00, helper_wage=18.00, payroll=0.12, margin=0.35, target_profit_hr=10.00,
               min_charge=150.00, rounding=5, setup_min=30, bundle_disc=0.10, plan_disc=0.10, crew_loss=0.10,
               water_fee=50.00, water_min=20, free_miles=15, surcharge_mile=1.50, valid_days=30, currency="$")
FUEL = dict(fuel_price=4.00, machine_gph=0.80, mpg=15, wear_mile=0.30)
EQUIPMENT = [
    ("4 GPM 4000 PSI pressure washer", 2200, 5, 250),
    ('20" surface cleaner', 450, 4, 60),
    ("12V soft wash pump system", 1200, 4, 100),
    ("200 ft hose, reel and soft wash hose", 650, 4, 50),
    ("Extension and step ladders", 500, 8, 0),
    ("6x12 utility trailer", 3000, 12, 150),
    ("525-gallon water tank", 600, 10, 0),
    ("Guns, tips, injector, PPE", 500, 2, 0),
]
OVERHEAD = [
    ("General liability insurance", 1500),
    ("Business licence and registration", 150),
    ("Phone (business share)", 600),
    ("Software and apps", 420),
    ("Marketing (cards, website, ads)", 900),
    ("Accounting and tax preparation", 500),
    ("Vehicle insurance (business share)", 1000),
    ("Other", 400),
]
TERMS = ("Work is weather permitting; rain days are moved to the next dry day. The client provides an outdoor water tap "
         "unless water hauling is quoted. Payment due on completion. Prices are valid until the date shown.")
PROPERTY = ["Residential", "Commercial"]
STATUSES = ["Sent", "Accepted", "Declined", "No reply"]
PLAN_FREQ = [("Yearly", 1), ("Twice a year", 2), ("Quarterly", 4)]
PLAN_STATUS = ["Active", "Paused", "Cancelled"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

# ================================================================ SAMPLE business (fictional)
BUSINESS = dict(name="BrightSide Exterior Cleaning", contact="Jordan Hayes", phone="(555) 017-4410",
                email="jordan@brightside.example", website="brightside.example", street="92 Mill Pond Road",
                city="Franklin, TN 37064")
YEAR = 2026

# the quote shown on QUICK QUOTE: (service, quantity, condition, access, stain, stain qty, plan visits per year)
QUOTE = dict(date=dt.date(2026, 4, 14), number="Q-2031", client="Rachel Moreno", address="15 Larkspur Court",
             property="Residential", crew=1, drive=15, miles=9, water="Yes", other=0,
             lines=[("House wash (soft wash)", 2600, "Normal", "2 storeys", None, None, 1),
                    ("Concrete driveway", 900, "Heavy", "Ground level", "Oil", 3, 1),
                    ("Sidewalk / walkway", 220, "Normal", None, None, None, 0),
                    ("Gutter brightening", 160, "Normal", "2 storeys", None, None, 0)])

# quote log: (date, client, address, property, main services, total, flatwork sq ft, flatwork price, est hours,
#             status, follow-up, notes)
LOG = [
    (dt.date(2026, 3, 10), "Tom Alvarez", "8 Cedar Bend", "Residential", "Concrete driveway + Sidewalk / walkway",
     265, 1100, 265, 2.1, "Accepted", None, ""),
    (dt.date(2026, 3, 17), "Hillcrest Dental", "400 Main Street", "Commercial", "Commercial flatwork + Dumpster pad",
     610, 4800, 610, 5.6, "Accepted", None, "Wants quarterly"),
    (dt.date(2026, 3, 24), "Megan Price", "71 Oak Hollow", "Residential", "House wash (soft wash) + Patio",
     420, 350, 110, 4.4, "Declined", None, "Went with a cheaper quote"),
    (dt.date(2026, 4, 2), "Luis Ortega", "3 Brook Lane", "Residential", "Pavers: clean + re-sand + seal",
     1450, 600, 1450, 6.8, "Declined", None, "Price too high"),
    (dt.date(2026, 4, 7), "Anna Fischer", "122 Ridge Road", "Residential", "Roof soft wash",
     690, None, None, 3.6, "Accepted", None, ""),
    (dt.date(2026, 4, 14), "Rachel Moreno", "15 Larkspur Court", "Residential",
     "House wash + driveway + walkway + gutters", 531, 1120, 190, 7.4, "Accepted",
     None, "Booked for May 2"),
    (dt.date(2026, 4, 20), "Greenway Plaza", "900 Commerce Drive", "Commercial", "Commercial flatwork + Drive-thru lane",
     1240, 12000, 1240, 9.2, "No reply", dt.date(2026, 4, 27), "Ask for the manager"),
    (dt.date(2026, 5, 5), "Sam Whitaker", "40 Pine Street", "Residential", "Deck clean + stain/seal",
     980, None, None, 5.9, "Accepted", None, ""),
]

# job log: (date, client, main service, quoted price, est hours, actual hours, crew, actual chemicals, extra costs, paid)
JOBS = [
    (dt.date(2026, 3, 21), "Tom Alvarez", "Concrete driveway", 265, 2.1, 1.6, 1, 4.50, 0, "Yes"),
    (dt.date(2026, 4, 4), "Hillcrest Dental", "Commercial flatwork", 610, 5.6, 5.4, 1, 14.00, 0, "Yes"),
    (dt.date(2026, 4, 18), "Anna Fischer", "Roof soft wash", 690, 3.6, 3.7, 1, 52.00, 0, "Yes"),
    (dt.date(2026, 5, 2), "Rachel Moreno", "House wash (soft wash)", 531, 7.4, 9.0, 1, 44.00, 0, "Yes"),
    (dt.date(2026, 5, 16), "Sam Whitaker", "Deck clean + stain/seal", 980, 5.9, 6.2, 1, 128.00, 15, "Yes"),
    (dt.date(2026, 6, 6), "Kara Lin", "Concrete driveway", 210, 1.7, 1.3, 1, 3.50, 0, "Yes"),
    (dt.date(2026, 6, 20), "Dev Patel", "House wash (soft wash)", 380, 4.2, 5.3, 1, 26.00, 0, "Yes"),
    (dt.date(2026, 7, 11), "Hillcrest Dental", "Commercial flatwork", 610, 5.6, 5.5, 1, 13.00, 0, "Yes"),
    (dt.date(2026, 8, 22), "Oak Street Cafe", "Dumpster pad", 175, 1.2, 1.3, 1, 9.00, 20, "No"),
    (dt.date(2026, 9, 12), "Ben Carter", "Concrete driveway", 240, 1.9, 1.5, 1, 4.00, 0, "No"),
]

# maintenance plans: (client, address, services, frequency, price per visit, last clean, status, notes)
PLANS = [
    ("Rachel Moreno", "15 Larkspur Court", "House wash each spring, driveway each fall", "Twice a year", 189,
     dt.date(2026, 5, 2), "Active", ""),
    ("Hillcrest Dental", "400 Main Street", "Front walks and dumpster pad", "Quarterly", 520, dt.date(2026, 10, 3),
     "Active", "Before 7 am"),
    ("Anna Fischer", "122 Ridge Road", "Roof soft wash", "Yearly", 620, dt.date(2026, 4, 18), "Active", ""),
    ("Tom Alvarez", "8 Cedar Bend", "Driveway and walkway", "Yearly", 240, dt.date(2025, 12, 6), "Active", ""),
    ("Dev Patel", "19 Elm Court", "House wash", "Yearly", 345, dt.date(2026, 6, 20), "Active", ""),
    ("Oak Street Cafe", "77 Oak Street", "Dumpster pad and patio", "Quarterly", 160, dt.date(2026, 8, 22), "Active",
     "Grease on pad"),
    ("Sam Whitaker", "40 Pine Street", "Deck clean (re-seal every 2 years)", "Yearly", 300, dt.date(2026, 5, 16),
     "Active", ""),
    ("Kara Lin", "5 Willow Trace", "Driveway", "Yearly", 190, dt.date(2026, 6, 6), "Paused", "Moving in spring"),
]
