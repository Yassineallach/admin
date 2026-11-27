"""Owner-Operator Cost Per Mile & Load Profit Calculator: names, presets, example settings and the sample operator.

Every number here is an EXAMPLE value, labelled as such in the workbook. Sources are listed in test-report.md.
"""
import datetime as dt

PRODUCT = "Owner-Operator Cost Per Mile"
PRODUCT_LONG = "Owner-Operator Cost Per Mile & Load Profit Calculator"
OUT_NAME = "BrassLedger_Owner_Operator_CPM_Calculator"
GUIDE_NAME = "BrassLedger_Owner_Operator_Quick_Start_Guide.pdf"
PROMISE = "Know your cost per mile before you take the load."
DISCLAIMER = ("Estimates based on the numbers you enter. Not financial, legal or tax advice. "
              "Not affiliated with any carrier, broker or load board.")
EXAMPLE = "Example values, replace with your own numbers."

# ------------------------------------------------------------------ equipment presets
# name, MPG, maintenance & repair $/mile, tire set cost $, tire life miles, DEF $/mile, reefer fuel gal/hour
PRESETS = [
    ("Dry van", 6.8, 0.200, 6000, 120000, 0.015, 0.0),
    ("Reefer", 6.4, 0.220, 6000, 120000, 0.015, 0.75),
    ("Flatbed", 6.5, 0.210, 6000, 120000, 0.015, 0.0),
    ("Hotshot (CDL)", 10.0, 0.130, 2800, 60000, 0.010, 0.0),
    ("Hotshot (non-CDL)", 11.5, 0.110, 2400, 60000, 0.010, 0.0),
    ("Box truck", 10.0, 0.120, 2400, 70000, 0.010, 0.0),
]

# ------------------------------------------------------------------ fixed costs (example: dry van, own authority)
# label, amount, per ("Month" or "Year"), hint
FIXED = [
    ("Truck payment", 2300, "Month", "Loan or lease payment on the tractor or pickup"),
    ("Trailer payment or lease", 650, "Month", "0 if you pull the carrier's trailer"),
    ("Insurance: primary liability", 7500, "Year", "Own authority. Leased on: usually the carrier's policy"),
    ("Insurance: cargo", 1500, "Year", ""),
    ("Insurance: physical damage", 4200, "Year", "Often 2-6 % of the truck's value a year"),
    ("Insurance: non-trucking / bobtail", 0, "Year", "Leased-on drivers; 0 under your own authority"),
    ("Insurance: occupational accident", 2000, "Year", ""),
    ("Plates and registration (IRP)", 2600, "Year", ""),
    ("Heavy vehicle use tax (Form 2290)", 550, "Year", "$550 a year for 75,000 lb and over"),
    ("UCR", 46, "Year", "2026 fee for 0-2 trucks; $55 for 2027"),
    ("IFTA licence and decals", 25, "Year", "Varies by base state"),
    ("Authority, BOC-3, drug testing consortium", 300, "Year", ""),
    ("ELD subscription", 45, "Month", ""),
    ("Load board subscriptions", 150, "Month", ""),
    ("Phone and data", 100, "Month", ""),
    ("Accounting / bookkeeping", 150, "Month", ""),
    ("Truck parking", 200, "Month", ""),
    ("Other fixed costs", 100, "Month", ""),
]

# ------------------------------------------------------------------ other settings (examples)
SET = dict(
    equipment="Dry van",
    fuel_price=5.90,          # $/gal, EIA US on-highway diesel, week ending Nov 16, 2026: $5.937
    other_var=0.00,           # $/mile, anything else per mile
    reefer_hours_day=10,      # reefer run hours per load day
    load_days_week=5,
    weekly_pay=1500,          # owner's target weekly take-home
    weekly_miles=2500,        # loaded + deadhead
    weeks_year=48,
    margin=0.10,
    factoring=0.03,
    dispatch=0.00,
    sens=(6000, 8000, 10000, 12000),
    verdicts=("TAKE", "NEGOTIATE", "PASS"),
    pass_basis="Operating costs",
    min_ppd=None,             # optional minimum profit per day for TAKE
    year=2026,
)
PASS_BASIS = ["Operating costs", "All-in costs incl. your pay"]

STATES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY",
          "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
          "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
          "AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

# ------------------------------------------------------------------ sample operator (fictional)
SAMPLE_NAME = "Ridgeline Freight LLC (sample)"
# lanes: origin, destination, [(state, miles)]
LANES = {
    "SGF-DAL": ("Springfield, MO", "Dallas, TX", [("MO", 70), ("OK", 250), ("TX", 115)]),
    "DAL-MEM": ("Dallas, TX", "Memphis, TN", [("TX", 180), ("AR", 265), ("TN", 7)]),
    "MEM-IND": ("Memphis, TN", "Indianapolis, IN", [("TN", 10), ("AR", 75), ("MO", 135), ("IL", 175), ("IN", 70)]),
    "IND-CMH": ("Indianapolis, IN", "Columbus, OH", [("IN", 70), ("OH", 105)]),
    "CMH-ATL": ("Columbus, OH", "Atlanta, GA", [("OH", 110), ("KY", 190), ("TN", 155), ("GA", 115)]),
    "ATL-JAX": ("Atlanta, GA", "Jacksonville, FL", [("GA", 315), ("FL", 30)]),
    "JAX-CLT": ("Jacksonville, FL", "Charlotte, NC", [("FL", 20), ("GA", 125), ("SC", 220), ("NC", 20)]),
    "CLT-STL": ("Charlotte, NC", "St. Louis, MO", [("NC", 120), ("TN", 210), ("KY", 230), ("IL", 150), ("MO", 10)]),
    "ATL-SGF": ("Atlanta, GA", "Springfield, MO", [("GA", 80), ("AL", 245), ("MS", 100), ("TN", 15), ("AR", 150), ("MO", 110)]),
    "DAL-ATL": ("Dallas, TX", "Atlanta, GA", [("TX", 190), ("LA", 190), ("MS", 155), ("AL", 215), ("GA", 30)]),
    "ATL-DAL": ("Atlanta, GA", "Dallas, TX", [("GA", 30), ("AL", 215), ("MS", 155), ("LA", 190), ("TX", 190)]),
    "CHI-DAL": ("Chicago, IL", "Dallas, TX", [("IL", 290), ("MO", 290), ("OK", 250), ("TX", 140)]),
    "CHI-ATL": ("Chicago, IL", "Atlanta, GA", [("IL", 75), ("IN", 285), ("KY", 190), ("TN", 155), ("GA", 10)]),
    "DEN-DAL": ("Denver, CO", "Dallas, TX", [("CO", 200), ("NM", 105), ("TX", 485)]),
    "STL-SGF": ("St. Louis, MO", "Springfield, MO", [("MO", 215)]),
    "SGF-CHI": ("Springfield, MO", "Chicago, IL", [("MO", 280), ("IL", 270)]),
    "CHI-SGF": ("Chicago, IL", "Springfield, MO", [("IL", 270), ("MO", 280)]),
    "SGF-DEN": ("Springfield, MO", "Denver, CO", [("MO", 160), ("KS", 420), ("CO", 200)]),
    "DEN-OKC": ("Denver, CO", "Oklahoma City, OK", [("CO", 180), ("KS", 140), ("OK", 300)]),
    "OKC-SGF": ("Oklahoma City, OK", "Springfield, MO", [("OK", 210), ("MO", 75)]),
}
BROKERS = ["Prairie Line Logistics", "Bluegate Freight", "Harbor & Main Brokerage", "Northstar Transport Group",
           "Redrock Shipping Co.", "Cedar Valley Foods (direct)"]
# rate per loaded mile on the linehaul by lane (before fuel surcharge); Florida outbound pays least
LANE_RATE = {"ATL-JAX": 2.05, "JAX-CLT": 1.45, "CHI-SGF": 1.75, "SGF-CHI": 2.15, "STL-SGF": 2.40, "IND-CMH": 2.90,
             "OKC-SGF": 2.10, "DEN-OKC": 1.55, "DEN-DAL": 1.60}
CHAINS = [  # each stretch on the road starts and ends at home (Springfield, MO)
    ["SGF-DAL", "DAL-ATL", "ATL-JAX", "JAX-CLT", "CLT-STL", "STL-SGF"],
    ["SGF-CHI", "CHI-DAL", "DAL-MEM", "MEM-IND", "IND-CMH", "CMH-ATL", "ATL-SGF"],
    ["SGF-DEN", "DEN-DAL", "DAL-ATL", "ATL-JAX", "JAX-CLT", "CLT-STL", "STL-SGF"],
    ["SGF-CHI", "CHI-ATL", "ATL-DAL", "DAL-MEM", "MEM-IND", "IND-CMH", "CMH-ATL", "ATL-SGF"],
    ["SGF-DAL", "DAL-ATL", "ATL-JAX", "JAX-CLT", "CLT-STL", "STL-SGF"],
    ["SGF-DEN", "DEN-OKC", "OKC-SGF", "SGF-CHI", "CHI-DAL", "DAL-MEM", "MEM-IND", "IND-CMH", "CMH-ATL", "ATL-SGF"],
    ["SGF-CHI", "CHI-SGF"],
]
DEADHEAD = [25, 40, 15, 60, 30, 0, 140, 20, 45, 35, 10, 85, 25, 50, 30, 110, 20, 15]
EXTRAS = {  # load number -> (detention, extra stop pay, tolls, other trip costs, note)
    2: (75, 0, 0, 0, "2 h detention paid"), 5: (0, 0, 0, 60, "Lumper $60, not reimbursed"),
    8: (0, 50, 28, 0, "Extra stop pay"), 11: (150, 0, 0, 0, "4 h detention paid"), 15: (0, 0, 0, 30, "Scale and wash"),
    19: (0, 0, 28, 45, "Lumper $45"), 24: (100, 0, 0, 0, "Detention paid"), 29: (0, 0, 28, 0, ""),
    33: (0, 0, 0, 25, "Washout"), 38: (0, 75, 0, 0, "Extra stop pay"), 43: (0, 0, 28, 0, "")}
FSC_PER_MILE = 0.72       # fuel surcharge paid per loaded mile in the sample (broker schedules vary)
TRIP_MPG = 6.7            # the sample truck's real-world MPG (used only to make the sample fuel costs)
PAID_BEFORE = dt.date(2026, 11, 14)   # sample: loads delivered before this date are paid
START = dt.date(2026, 9, 1)


def _price(state):
    """Sample pump price by state (a spread around the example average)."""
    return {"TX": 5.71, "OK": 5.68, "MO": 5.74, "AR": 5.77, "TN": 5.79, "IL": 6.19, "IN": 6.05, "OH": 6.02,
            "KY": 5.88, "GA": 5.83, "FL": 5.96, "SC": 5.80, "NC": 5.91, "KS": 5.75, "CO": 5.99, "AL": 5.74,
            "MS": 5.70, "LA": 5.69}.get(state, 5.90)


def _schedule():
    """Back-to-back loads: about 520 miles a driving day, next pickup the day after delivery, 2 days home between stretches."""
    out, day, k = [], START, 0
    for chain in CHAINS:
        for lane in chain:
            o, dest, states = LANES[lane]
            loaded = sum(m for _, m in states)
            dh = DEADHEAD[k % len(DEADHEAD)]
            days = max(1, -(-(loaded + dh) // 520))
            out.append((k, lane, day, days, dh))
            day += dt.timedelta(days=days)
            k += 1
        day += dt.timedelta(days=2)
    return out


def sample_trips():
    out = []
    for k, lane, pu, days, dh in _schedule():
        o, dest, states = LANES[lane]
        loaded = sum(m for _, m in states)
        de = pu + dt.timedelta(days=days - 1)
        if de > dt.date(2026, 11, 26):
            break
        det, oth, toll, ocost, note = EXTRAS.get(k, (0, 0, 0, 0, ""))
        lh = round(loaded * LANE_RATE.get(lane, 1.95) + 120, -1)
        fac = "N" if BROKERS[k % len(BROKERS)].endswith("(direct)") else "Y"
        total = loaded + dh
        paid = de < PAID_BEFORE
        out.append(dict(pu=pu, de=de, broker=BROKERS[k % len(BROKERS)], origin=o, dest=dest, loaded=loaded, dh=dh, lh=lh,
                        fsc=round(FSC_PER_MILE * loaded, 2), det=det, oth=oth, fuel=round(total / TRIP_MPG * 5.86, 2),
                        tolls=toll, ocost=ocost, factored=fac, paid="Y" if paid else "N",
                        paydate=(de + dt.timedelta(days=2 if fac == "Y" else 21)) if paid else None, note=note,
                        lane=lane, states=states))
    return out


def sample_fuel():
    """Fill-ups along the sample trips: roughly every 1,100 miles, gallons from the truck's real MPG."""
    odo, since, out, k = 412_380, 0, [], 0
    for t in sample_trips():
        miles = t["loaded"] + t["dh"]
        odo += miles
        since += miles
        if since >= 1100:
            k += 1
            st = t["states"][-1][0]
            mpg = TRIP_MPG + (0.25, -0.2, 0.1, -0.1, 0.3, -0.25)[k % 6]
            out.append(dict(date=t["de"], city=t["dest"].split(",")[0], state=st, gal=round(since / mpg, 1),
                            price=_price(st), odo=odo, defc=45.0 if k % 3 == 0 else None))
            since = 0
    return out


def sample_state_miles():
    """Miles by state per trip (loaded miles by lane; deadhead counted in the pickup state)."""
    rows = []
    for t in sample_trips():
        first = t["states"][0][0]
        for st, m in t["states"]:
            rows.append((t["pu"], f'{t["origin"].split(",")[0]} to {t["dest"].split(",")[0]}', st,
                         m + (t["dh"] if st == first else 0)))
    return rows


def sample_away():
    """Stretches away from home: first pickup to last delivery of each chain."""
    trips, out, i = sample_trips(), [], 0
    for chain in CHAINS:
        seg = trips[i:i + len(chain)]
        if seg:
            out.append((seg[0]["pu"].isoformat(), seg[-1]["de"].isoformat()))
        i += len(chain)
    return out


AWAY = sample_away()
PAY_DRAWN = {9: 6500, 10: 6500, 11: 6500}

# load check sample: pays well per loaded mile, fails once the deadhead is counted
LOAD_CHECK = dict(rate=1150, loaded=380, dh=300, days=2)
# load compare sample: five offers out of Springfield
COMPARE = [
    ("Springfield to Dallas", 1050, 435, 25, 2, 0, 0, 0),
    ("Springfield to Chicago", 1350, 550, 20, 2, 28, 0, 0),
    ("Joplin to Denver", 2150, 720, 75, 3, 0, 0, 0),
    ("Springfield to Little Rock", 720, 250, 40, 1, 0, 50, 0),
    ("Branson to Atlanta", 1520, 680, 55, 2, 0, 0, 75),
]
