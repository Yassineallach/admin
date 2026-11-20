"""Cake Pricing Calculator config: units, ingredients, pans, recipes, settings defaults and the sample bakery.

All prices and amounts are EXAMPLE VALUES. Sources are in the test report.
"""
import datetime as dt
import math

PRODUCT = "Cake Pricing Calculator"
OUT_NAME = "BrassLedger_Cake_Pricing_Calculator"
GUIDE_NAME = "BrassLedger_Cake_Pricing_Quick_Start_Guide.pdf"

# ---------------------------------------------------------------- units: (unit, type, amount in g / ml / items)
UNITS = [("g", "weight", 1), ("kg", "weight", 1000), ("oz", "weight", 28.3495), ("lb", "weight", 453.592),
         ("ml", "volume", 1), ("l", "volume", 1000), ("tsp", "volume", 4.92892), ("tbsp", "volume", 14.7868),
         ("cup", "volume", 236.588), ("metric cup", "volume", 250), ("fl oz", "volume", 29.5735),
         ("pt", "volume", 473.176), ("qt", "volume", 946.353), ("gal", "volume", 3785.41),
         ("each", "count", 1), ("dozen", "count", 12)]
UNIT_SYSTEMS = ["US", "Metric"]

# ---------------------------------------------------------------- ingredients
# (name, example price, package size, package unit, grams per cup, grams per item)
INGREDIENTS = [
    ("All-purpose flour", 4.50, 5, "lb", 120, None),
    ("Cake flour", 5.50, 2, "lb", 120, None),
    ("Bread flour", 5.00, 5, "lb", 120, None),
    ("Self-raising flour", 4.00, 2, "lb", 113, None),
    ("Almond flour", 9.00, 1, "lb", 96, None),
    ("Granulated sugar", 4.00, 4, "lb", 198, None),
    ("Light brown sugar", 3.50, 2, "lb", 213, None),
    ("Powdered sugar", 3.00, 2, "lb", 113, None),
    ("Unsalted butter", 5.00, 1, "lb", 227, None),
    ("Eggs, large", 4.20, 12, "each", None, 50),
    ("Egg whites (carton)", 4.50, 16, "fl oz", 243, None),
    ("Whole milk", 4.00, 1, "gal", 227, None),
    ("Buttermilk", 2.50, 1, "qt", 227, None),
    ("Heavy cream", 5.50, 1, "pt", 232, None),
    ("Sour cream", 2.50, 16, "oz", 227, None),
    ("Cream cheese", 3.00, 8, "oz", 227, None),
    ("Vegetable oil", 5.00, 48, "fl oz", 198, None),
    ("Vanilla extract", 12.00, 4, "fl oz", 208, None),
    ("Baking powder", 3.50, 8.1, "oz", 192, None),
    ("Baking soda", 1.50, 16, "oz", 288, None),
    ("Salt", 1.50, 26, "oz", 288, None),
    ("Cocoa powder", 6.00, 8, "oz", 84, None),
    ("Dark chocolate", 10.00, 1, "lb", 170, None),
    ("Semi-sweet chocolate chips", 4.00, 12, "oz", 170, None),
    ("White chocolate", 9.00, 1, "lb", 170, None),
    ("Brewed coffee", 0.50, 1, "l", 237, None),
    ("Espresso powder", 6.00, 2, "oz", None, None),
    ("Water", 0.00, 1, "l", 237, None),
    ("Honey", 7.00, 12, "oz", 336, None),
    ("Corn syrup", 4.00, 16, "fl oz", 312, None),
    ("Raspberries (frozen)", 4.50, 12, "oz", 140, None),
    ("Strawberries", 4.00, 1, "lb", 167, None),
    ("Lemons", 0.80, 1, "each", None, 100),
    ("Lemon juice", 3.00, 15, "fl oz", 227, None),
    ("Cornstarch", 2.50, 16, "oz", 112, None),
    ("Meringue powder", 9.00, 8, "oz", 128, None),
    ("Vegetable shortening", 5.00, 16, "oz", 184, None),
    ("Peanut butter", 4.00, 16, "oz", 270, None),
    ("Cream of tartar", 5.00, 1.5, "oz", 144, None),
    ("Gel food colouring", 3.00, 0.75, "oz", None, None),
    ("Fondant (white)", 14.00, 2, "lb", None, None),
    ("Shredded coconut", 4.00, 14, "oz", 85, None),
    ("Walnuts", 7.00, 16, "oz", 113, None),
    ("Pecans", 9.00, 16, "oz", 113, None),
    ("Ground cinnamon", 4.00, 2.37, "oz", 125, None),
    ("Sprinkles", 4.00, 4, "oz", None, None),
    ("Mini marshmallows", 2.50, 16, "oz", 50, None),
    ("Sweetened condensed milk", 2.50, 14, "oz", 306, None),
]

# ---------------------------------------------------------------- pans
# batter cups per 2" layer by shape and size; area and perimeter give filling, frosting and fondant defaults
ROUND_BATTER = {4: 1, 5: 1.5, 6: 2, 7: 2.5, 8: 3, 9: 4.5, 10: 6, 12: 7.5, 14: 10, 16: 15}
ROUND_SERV = {4: (4, 6), 5: (6, 8), 6: (12, 12), 7: (16, 18), 8: (20, 24), 9: (24, 32), 10: (28, 38), 12: (40, 56),
              14: (63, 78), 16: (77, 100)}
SQUARE_SERV = {6: (12, 18), 8: (20, 32), 10: (30, 50), 12: (48, 72), 14: (63, 98), 16: (80, 128)}
HEART_SERV = {6: (8, 12), 8: (14, 22), 10: (24, 36), 12: (34, 50)}
HEART_BATTER = {6: 1.5, 8: 2.5, 10: 4, 12: 6}
SHEETS = {"9x13": (9, 13, 8, (24, 54)), "11x15": (11, 15, 11, (35, 77)), "12x18": (12, 18, 14, (54, 108))}
CUP_IN3 = 14.4375


def q25(x):
    return round(x * 4) / 4


def pan_rows():
    rows = []

    def add(shape, label, cm, batter, area, perim, serv):
        fill = max(0.25, q25(area * 0.25 / CUP_IN3))
        frost = q25((area + perim * 4) * 0.30 / CUP_IN3)
        fondant = int(round((area + perim * 4) * 4.5, -1))
        rows.append((shape, label, cm, batter, fill, frost, fondant, serv[0], serv[1]))

    for s, b in ROUND_BATTER.items():
        add("Round", f'{s}"', f"{round(s * 2.54)} cm", b, math.pi * s * s / 4, math.pi * s, ROUND_SERV[s])
    for s, serv in SQUARE_SERV.items():
        add("Square", f'{s}"', f"{round(s * 2.54)} cm", round(ROUND_BATTER[s] * 4 / math.pi * 2) / 2, s * s, 4 * s, serv)
    for lab, (w, h, b, serv) in SHEETS.items():
        add("Sheet", f'{lab}"', f"{round(w * 2.54)}x{round(h * 2.54)} cm", b, w * h, 2 * (w + h), serv)
    for s, serv in HEART_SERV.items():
        add("Heart", f'{s}"', f"{round(s * 2.54)} cm", HEART_BATTER[s], 0.8 * s * s, 3.4 * s, serv)
    return rows


PANS = pan_rows()
SHAPES = ["Round", "Square", "Sheet", "Heart"]
SIZES = []
for p in PANS:
    if p[1] not in SIZES:
        SIZES.append(p[1])

# ---------------------------------------------------------------- settings lists
RECIPE_TYPES = ["Batter", "Filling", "Frosting", "Ganache", "Fondant", "Cookie dough", "Icing", "Other"]
COVERINGS = [("Buttercream", 1.0, "No"), ("Fondant", 0.5, "Yes"), ("Semi-naked", 0.6, "No"), ("Naked", 0.3, "No")]
LEVELS = [("Simple", 1.0), ("Moderate", 1.5), ("Detailed", 2.0), ("Showpiece", 3.0)]
EXTRAS = [("Sugar flowers (per stem)", 6.00), ("Fresh flowers (per stem, food-safe)", 3.00), ("Cake topper", 8.00),
          ("Chocolate drip (per tier)", 3.00), ("Gold leaf (per sheet)", 2.50), ("Fondant figurine", 12.00),
          ("Printed edible image", 10.00), ("Sprinkle mix (per cake)", 2.00), ("Macarons (each)", 1.20),
          ("Wafer paper decorations", 4.00)]
SUPPLIES = [('Cake board 6"', 0.60), ('Cake board 8"', 0.80), ('Cake board 10"', 1.00), ('Cake board 12"', 1.30),
            ('Cake drum 12"', 3.50), ('Cake drum 14"', 4.50), ("Cake box 10x10x5", 1.80), ("Cake box 12x12x6", 2.50),
            ("Tall cake box 14x14x16", 6.00), ("Dowel or support straw", 0.20), ("Ribbon (per metre)", 0.60),
            ("Cupcake liner", 0.05), ("Cupcake box (dozen)", 2.50), ("Cookie bag", 0.15), ("Cake pop stick", 0.05),
            ("Label or sticker", 0.10)]
TASKS = ["Consultation", "Baking", "Levelling and filling", "Crumb coat", "Decorating", "Packaging", "Delivery"]
DECOR_TASK = "Decorating"
SERVING_STYLES = ["Party", "Wedding"]
DELIVERY = ["Pickup", "Delivery", "Delivery + set-up"]
OVERHEAD_METHODS = ["Per hour", "Per order"]
ORDER_TYPES = ["Tiered cake", "Single cake", "Cupcakes", "Cookies", "Other"]
STATUSES = ["Enquiry", "Quoted", "Booked", "Baking", "Completed", "Cancelled"]
ACTIVE = ["Enquiry", "Quoted", "Booked", "Baking"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

TARGETS = dict(currency="$", units="US", rate=25.00, margin=0.20, min_serving=4.50, deposit=0.50, round_cake=5,
               round_dozen=1, round_item=0.25, valid_days=14, method="Per hour", hours_year=800, orders_year=120,
               mile_rate=1.00, setup_fee=25.00)
OVERHEAD = [("Electricity and gas (baking share)", 600), ("Equipment wear and replacement", 400),
            ("Licence or permit", 100), ("Insurance", 300), ("Marketing", 300), ("Website and software", 150),
            ("Other", 150)]
TERMS = ("A deposit of the amount shown books your date and is non-refundable. The balance is due 7 days before the "
         "event. Design changes are welcome up to 14 days before. Cancellations within 14 days forfeit the deposit.")
COMPLIANCE = [
    "Cottage food rules vary by state and country: what you can sell from home, labelling and allergen requirements, "
    "sales limits and permits. Check your local rules.",
    "Always ask customers about allergies. The quote has an allergen notes line.",
]

# ================================================================ SAMPLE bakery (fictional)
BUSINESS = dict(name="Willow & Whisk Bakery", contact="Emma Collins", phone="(555) 012-7788",
                email="hello@willowandwhisk.example", website="willowandwhisk.example", street="27 Bramble Lane",
                city="Asheville, NC 28801")
YEAR = 2026
PRICES_CHECKED = dt.date(2026, 10, 15)

# recipes: name, type, yield qty, yield unit, [(ingredient, qty, unit)]
RECIPES = [
    ("Vanilla sponge", "Batter", 6, "cup", [("Cake flour", 3, "cup"), ("Granulated sugar", 2, "cup"),
                                            ("Unsalted butter", 1, "cup"), ("Eggs, large", 4, "each"),
                                            ("Whole milk", 1, "cup"), ("Vanilla extract", 2, "tsp"),
                                            ("Baking powder", 1, "tbsp"), ("Salt", 0.5, "tsp")]),
    ("Chocolate fudge cake", "Batter", 6.5, "cup", [("All-purpose flour", 2, "cup"), ("Granulated sugar", 2, "cup"),
                                                    ("Cocoa powder", 0.75, "cup"), ("Baking soda", 2, "tsp"),
                                                    ("Baking powder", 1, "tsp"), ("Salt", 1, "tsp"),
                                                    ("Eggs, large", 2, "each"), ("Buttermilk", 1, "cup"),
                                                    ("Vegetable oil", 0.5, "cup"), ("Brewed coffee", 1, "cup"),
                                                    ("Vanilla extract", 2, "tsp")]),
    ("Vanilla cupcakes", "Batter", 24, "each", [("All-purpose flour", 3, "cup"), ("Granulated sugar", 2, "cup"),
                                                ("Unsalted butter", 1, "cup"), ("Eggs, large", 4, "each"),
                                                ("Whole milk", 1, "cup"), ("Baking powder", 1, "tbsp"),
                                                ("Vanilla extract", 2, "tsp"), ("Salt", 0.5, "tsp")]),
    ("Vanilla buttercream", "Frosting", 6, "cup", [("Unsalted butter", 2, "cup"), ("Powdered sugar", 900, "g"),
                                                   ("Heavy cream", 0.25, "cup"), ("Vanilla extract", 2, "tsp"),
                                                   ("Salt", 0.25, "tsp")]),
    ("Chocolate ganache", "Ganache", 3, "cup", [("Dark chocolate", 340, "g"), ("Heavy cream", 1.5, "cup")]),
    ("Raspberry filling", "Filling", 2, "cup", [("Raspberries (frozen)", 500, "g"), ("Granulated sugar", 0.75, "cup"),
                                                ("Cornstarch", 2, "tbsp"), ("Lemon juice", 1, "tbsp")]),
    ("Fondant (store-bought)", "Fondant", 1, "kg", [("Fondant (white)", 1, "kg")]),
    ("Sugar cookie dough", "Cookie dough", 24, "each", [("All-purpose flour", 3, "cup"), ("Unsalted butter", 1, "cup"),
                                                        ("Granulated sugar", 1, "cup"), ("Eggs, large", 1, "each"),
                                                        ("Vanilla extract", 1, "tsp"), ("Baking powder", 0.5, "tsp"),
                                                        ("Salt", 0.25, "tsp")]),
    ("Royal icing", "Icing", 3, "cup", [("Powdered sugar", 4, "cup"), ("Meringue powder", 3, "tbsp"),
                                        ("Water", 0.5, "cup")]),
]

# cake builder slots
CAKES = [
    dict(customer="Hannah & Luke Pierce", event=dt.date(2026, 12, 12), occasion="Wedding", style="Wedding",
         delivery="Delivery + set-up", miles=18, fondant="Fondant (store-bought)", own=None,
         design="Three tiers in ivory fondant with cascading sugar roses and gold leaf accents.",
         allergens="No nuts. One guest is egg-free: provide a separate small cake if needed.",
         tiers=[("Round", '10"', 2, "Vanilla sponge", "Raspberry filling", "Vanilla buttercream", "Fondant"),
                ("Round", '8"', 2, "Chocolate fudge cake", "Chocolate ganache", "Vanilla buttercream", "Fondant"),
                ("Round", '6"', 2, "Vanilla sponge", "Raspberry filling", "Vanilla buttercream", "Fondant")],
         level="Detailed", extras=[("Sugar flowers (per stem)", 8), ("Gold leaf (per sheet)", 2)],
         supplies=[('Cake drum 14"', 1), ('Cake board 10"', 1), ('Cake board 8"', 1), ('Cake board 6"', 1),
                   ("Dowel or support straw", 8), ("Tall cake box 14x14x16", 1), ("Ribbon (per metre)", 3)],
         hours=[1, 3, 2, 1.5, 4, 0.5, 1.5]),
    dict(customer="Priya Nair", event=dt.date(2026, 11, 28), occasion="10th birthday", style="Party",
         delivery="Pickup", miles=0, fondant=None, own=None,
         design="Chocolate drip cake with sprinkles and a 'Happy 10th Maya' topper.",
         allergens="None reported.",
         tiers=[("Round", '8"', 3, "Chocolate fudge cake", "Chocolate ganache", "Vanilla buttercream", "Buttercream")],
         level="Moderate", extras=[("Chocolate drip (per tier)", 1), ("Cake topper", 1), ("Sprinkle mix (per cake)", 1)],
         supplies=[('Cake board 8"', 1), ("Cake box 10x10x5", 1)],
         hours=[0.25, 1.5, 1, 0.75, 1.5, 0.25, 0]),
]
QUOTE_DATE = dt.date(2026, 10, 20)

# batch products: name, recipe, own items per batch, batches, frosting recipe, frosting qty, unit, level, extras/item,
#                 packaging per dozen, other hours, decorating hours
BATCHES = [
    ("Vanilla cupcakes", "Vanilla cupcakes", None, 2, "Vanilla buttercream", 2.5, "tbsp", "Simple", 0.15, 3.50, 2.0, 1.0),
    ("Decorated sugar cookies", "Sugar cookie dough", None, 1, "Royal icing", 1, "tbsp", "Moderate", 0.00, 3.00, 1.5, 1.5),
]

# orders: order date, customer, contact, event date, pickup/delivery, type, description, servings, price,
#         deposit paid, deposit date, paid in full, status, allergen notes
ORDERS = [
    (dt.date(2026, 5, 2), "Grace Holloway", "(555) 010-2231", dt.date(2026, 6, 13), "Delivery + set-up", "Tiered cake",
     "2-tier lemon and elderflower, buttercream", 50, 360, 180, dt.date(2026, 5, 4), "Yes", "Completed", ""),
    (dt.date(2026, 6, 1), "Marco Ruiz", "marco@example.com", dt.date(2026, 6, 20), "Pickup", "Cupcakes",
     "24 vanilla cupcakes, blue swirl", 24, 70, 35, dt.date(2026, 6, 2), "Yes", "Completed", ""),
    (dt.date(2026, 6, 15), "Aisha Bello", "(555) 010-8842", dt.date(2026, 7, 4), "Pickup", "Single cake",
     '8" chocolate drip, 3 layers', 30, 155, 75, dt.date(2026, 6, 16), "Yes", "Completed", "Nut-free"),
    (dt.date(2026, 7, 2), "Riverside School PTA", "pta@example.com", dt.date(2026, 7, 18), "Delivery", "Cookies",
     "48 decorated sugar cookies", 48, 168, 84, dt.date(2026, 7, 3), "Yes", "Completed", ""),
    (dt.date(2026, 7, 20), "Daniel Moss", "(555) 010-4410", dt.date(2026, 8, 8), "Pickup", "Single cake",
     '6" vanilla smash cake', 12, 65, 30, dt.date(2026, 7, 21), "Yes", "Completed", ""),
    (dt.date(2026, 8, 3), "Claire & Tom Barker", "(555) 010-5512", dt.date(2026, 9, 5), "Delivery + set-up",
     "Tiered cake", "3-tier naked cake with fresh flowers", 90, 540, 270, dt.date(2026, 8, 5), "Yes", "Completed", ""),
    (dt.date(2026, 9, 1), "Sofia Lind", "sofia@example.com", dt.date(2026, 9, 26), "Pickup", "Cupcakes",
     "36 cupcakes, gender reveal", 36, 105, 50, dt.date(2026, 9, 2), "Yes", "Completed", "Dairy-free x6"),
    (dt.date(2026, 9, 20), "Office of Dr. Reyes", "(555) 010-9073", dt.date(2026, 10, 9), "Delivery", "Single cake",
     "Quarter sheet, retirement", 24, 120, 60, dt.date(2026, 9, 21), "Yes", "Completed", ""),
    (dt.date(2026, 10, 1), "Ben Ortiz", "(555) 010-3349", dt.date(2026, 10, 24), "Pickup", "Single cake",
     '8" spooky drip cake', 20, 110, 0, None, "No", "Cancelled", ""),
    (dt.date(2026, 10, 10), "Lily Chen", "lily@example.com", dt.date(2026, 11, 14), "Pickup", "Cookies",
     "24 baby shower cookies", 24, 84, 40, dt.date(2026, 10, 11), "No", "Completed", ""),
    (dt.date(2026, 11, 2), "Priya Nair", "(555) 010-6650", dt.date(2026, 11, 28), "Pickup", "Single cake",
     "10th birthday chocolate drip cake", 30, 255, 0, None, "No", "Quoted", "None reported"),
    (dt.date(2026, 10, 20), "Hannah & Luke Pierce", "hannah@example.com", dt.date(2026, 12, 12), "Delivery + set-up",
     "Tiered cake", "3-tier ivory fondant, sugar roses", 74, 840, 420, dt.date(2026, 10, 22), "No", "Booked",
     "No nuts; egg-free guest"),
    (dt.date(2026, 11, 5), "Owen Price", "(555) 010-2207", dt.date(2026, 11, 22), "Pickup", "Cupcakes",
     "12 cupcakes, football theme", 12, 42, 20, dt.date(2026, 11, 6), "No", "Baking", ""),
    (dt.date(2026, 11, 12), "Maple Street Cafe", "orders@maplecafe.example", dt.date(2026, 11, 25), "Delivery",
     "Other", "Weekly brownie tray (24)", 24, 60, 0, None, "No", "Booked", "Contains walnuts"),
    (dt.date(2026, 11, 18), "Jess Turner", "(555) 010-1180", dt.date(2027, 1, 16), "Pickup", "Tiered cake",
     "2-tier winter wedding enquiry", 60, 0, 0, None, "No", "Enquiry", ""),
]
