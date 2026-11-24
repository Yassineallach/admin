"""Seven Etsy listing images (2700 x 2025 PNG) for the Cake Pricing Calculator, from real screenshots (shoot.py).

Layout: paper background, brass kicker, large green Fraunces headline, short brass double rule, logo bottom-left.
Usage: python listing_images.py   (run shoot.py first)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, "/home/user/admin/productivity-bundle/build")
import brand as BR  # noqa: E402
import brand_listing as BL  # noqa: E402
from brand_listing import BRASS, GREEN, H, INK, INK2, M, PAPER, W, WHITE, F, FH, canvas, checks, frame, head, laptop, para, points  # noqa: E402

from brandimg import logo_rgba  # noqa: E402
import cake_config as CFG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "cake-pricing-calculator" / "listing-images"
POS = BR.rgb(BR.POSITIVE)


def shot(name, crop=None):
    im = Image.open(SCREENS / f"{name}.png").convert("RGB")
    if crop:
        w, h = im.size
        l, t, r, b = crop
        im = im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
    return im


_LOGO = None


def logo(img):
    global _LOGO
    if _LOGO is None:
        _LOGO = logo_rgba(560)
    img.paste(_LOGO, (M, H - M - _LOGO.height + 30), _LOGO)


def pill(img, xy, text, size=40, fill=GREEN, color=BRASS):
    d = ImageDraw.Draw(img)
    f = F(size, 700)
    w = d.textlength(text, font=f)
    x, y = xy
    d.rounded_rectangle((x, y, x + w + 2 * size, y + size * 2), size, fill=fill)
    d.text((x + size, y + size), text, font=f, fill=color, anchor="lm")
    return x + w + 2 * size


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / name, "PNG", optimize=True)
    print("wrote", name)




def green_boxes(sh, y_from=0.0, y_to=1.0, min_w=0.05):
    """Find horizontal runs of Ledger green on the first full green band in [y_from, y_to]: returns (x0, y0, x1, y1)."""
    px = sh.load()
    green = lambda p: p[0] < 60 and 45 < p[1] < 80 and p[2] < 70
    w, h = sh.size
    rows = [y for y in range(int(h * y_from), int(h * y_to)) if sum(green(px[x, y]) for x in range(0, w, 9)) > w / 9 * 0.25]
    y0 = rows[0]
    y1 = y0
    for y in rows[1:]:
        if y - y1 > 3:
            break
        y1 = y
    xs = [x for x in range(w) if green(px[x, y0 + 3])]
    runs, start, prev = [], xs[0], xs[0]
    for x in xs[1:]:
        if x - prev > 3:
            runs.append((start, prev))
            start = x
        prev = x
    runs.append((start, prev))
    return [(a, y0, b, y1) for a, b in runs if b - a > w * min_w]


def hero():
    """Photo 1 comes from the shared thumbnail system (productivity-bundle/build/hero_thumb.py)."""
    import hero_thumb
    hero_thumb.hero("cake")


def hero_legacy():
    img = canvas()
    y = head(img, "Cake pricing · home bakery", "Know what every cake really costs.", max_w=1100, size=112)
    y = checks(img, ["Costs every ingredient, recipe and tier", "Servings and price per serving for each cake",
                     "Quotes, deposits and orders in one file"], M, y + 60, 1060, size=46, gap=30, color=GREEN)
    x = pill(img, (M, y + 34), "Excel + Google Sheets", 42)
    pill(img, (x + 24, y + 34), "US + metric units", 42, fill=BR.rgb("F6EBD3"), color=GREEN)
    laptop(img, shot("cake1", (0, 0, 1, 0.62)), (1250, 360, 2620, 1520))
    logo(img)
    save(img, "01_hero.png")


def included():
    img = canvas()
    y = head(img, "What's included", "Nine tabs and a quick-start guide.") + 70
    cols = [("Cost it", ["INGREDIENTS: 48 with grams per cup", "RECIPES: 40 recipes, costed by line",
                         "SETTINGS: rates, pans, supplies, extras", "START HERE: 4-step quick start"]),
            ("Price and sell", ["CAKE BUILDER: up to 5 tiers, 3 cakes", "BATCH PRICING: per item and dozen",
                                "CUSTOMER QUOTE: one printable page", "ORDER TRACKER and DASHBOARD"]),
            ("Also in your download", ["Blank workbook, ready for your prices", "Sample workbook: a full fictional bakery",
                                       "Quick-start guide (PDF, 11 pages)", "Works in Excel and Google Sheets"])]
    d = ImageDraw.Draw(img)
    cw = (W - 2 * M - 120) // 3
    bottom = H - M - 230
    for i, (title, items) in enumerate(cols):
        x = M + i * (cw + 60)
        d.rounded_rectangle((x, y, x + cw, bottom), 18, fill=WHITE, outline=BR.rgb(BR.BORDER), width=3)
        d.rectangle((x, y, x + cw, y + 12), fill=GREEN)
        BR.spaced(d, (x + 48, y + 58), title.upper(), F(30, 700), BRASS, 0.2)
        yy = y + 140
        for it in items:
            d.rectangle((x + 48, yy + 24, x + 70, yy + 31), fill=BRASS)
            yy = para(img, (x + 92, yy), it, F(40, 500), INK, cw - 140, 1.22) + 30
    logo(img)
    save(img, "02_whats_included.png")


def builder():
    img = canvas()
    y = head(img, "Cake builder", "Servings, price per serving and your hourly earnings.", max_w=2400) + 70
    full = shot("cake1_price", (0, 0, 1, 1))
    ox = int(full.width * 0.03)
    sh = full.crop((ox, 0, full.width, full.height))
    box = frame(img, sh, (M, y, W - M, y + 900), "tl")
    s = (box[2] - box[0] - 28) / sh.width
    tiles = green_boxes(full, 0.0, 0.3)
    X = lambda x: box[0] + 14 + (x - ox) * s
    Y = lambda yy: box[1] + 14 + yy * s
    d = ImageDraw.Draw(img)
    for (x0, y0, x1, y1), num in [(tiles[3], "1"), (tiles[1], "2"), (tiles[2], "3")]:
        d.rounded_rectangle((X(x0) - 4, Y(y0) - 8, X(x1) + 4, Y(y1) + 8), 16, outline=BRASS, width=8)
        cx, cy = (X(x0) + X(x1)) / 2, Y(y0) - 8
        d.ellipse((cx - 36, cy - 36, cx + 36, cy + 36), fill=BRASS)
        d.text((cx, cy), num, font=F(40, 700), fill=GREEN, anchor="mm")
    notes = [("1", "SERVINGS", "From the pan table, by tier and layers, party or wedding."),
             ("2", "PRICE PER SERVING", "Checked against your own minimum. Red when it's too low."),
             ("3", "HOURLY EARNINGS", "What the cake pays you per hour, after every cost.")]
    ty = box[3] + 70
    cw = (W - 2 * M - 2 * 60) // 3
    for i, (num, title, body) in enumerate(notes):
        x = M + i * (cw + 60)
        d.rounded_rectangle((x, ty, x + cw, ty + 300), 20, fill=GREEN)
        BR.spaced(d, (x + 44, ty + 50), title, F(28, 700), BRASS, 0.2)
        para(img, (x + 44, ty + 105), body, F(38, 500), PAPER, cw - 88, 1.3)
        d.ellipse((x + cw - 36, ty - 36, x + cw + 36, ty + 36), fill=BRASS)
        d.text((x + cw, ty), num, font=F(40, 700), fill=GREEN, anchor="mm")
    logo(img)
    save(img, "03_cake_builder.png")


def library():
    img = canvas()
    y = head(img, "Ingredients and recipes", "Enter ingredients once. Every recipe is costed for you.", max_w=2420, size=104) + 50
    a = shot("ingredients", (0, 0, 0.86, 0.561))
    b = shot("recipe_block", (0, 0, 1, 1))
    boxa = frame(img, a, (M, y, W - M, y + 780), "tl")
    frame(img, b, (M + 700, boxa[3] + 40, W - M, H - M + 60), "tl")
    points(img, [("Any unit", "Cups, spoons, grams, ounces, ml, eggs."),
                 ("Converted for you", "Grams per cup for 48 ingredients.")], M, boxa[3] + 60, 620, 42, 34, 40)
    logo(img)
    save(img, "04_ingredients_recipes.png")


def quote_orders():
    img = canvas()
    y = head(img, "Quote and orders", "Send a professional quote and never miss a balance.", max_w=1500) + 50
    frame(img, shot("customer"), (M, y - 40, 1100, H - M - 210), "tl")
    frame(img, shot("orders", (0, 0, 0.8, 1)), (1160, y + 40, W - M, y + 860), "tl")
    points(img, [("Your bakery's name", "Tiers, flavours, servings, deposit and balance."),
                 ("Deposits and due dates", "Orders due this week and unpaid balances highlighted.")], 1160, y + 920, 1300, 44, 36, 34)
    logo(img)
    save(img, "05_quote_orders.png")


def compat():
    img = canvas()
    y = head(img, "Compatibility", "Excel or Google Sheets. US or metric.") + 80
    rows = [("Yes", POS, "Microsoft Excel 2016 or later", "Windows and Mac. Formulas are locked against accidental edits."),
            ("Yes", POS, "Google Sheets", "Make a copy from the link in the guide, or upload the file to Google Drive."),
            ("Both", POS, "US and metric units", "Cups, oz, lb or g, ml, kg. Metric cup (250 ml) included."),
            ("Best on a computer", INK2, "Phones and tablets", "It opens in the apps, but costing is easiest on a laptop."),
            ("Digital", INK2, "Instant download", "No physical item is shipped.")]
    d = ImageDraw.Draw(img)
    rh = (H - M - 260 - y) // len(rows)
    d.rounded_rectangle((M, y, W - M, y + rh * len(rows)), 18, fill=WHITE, outline=BR.rgb(BR.BORDER), width=3)
    for i, (tag, colr, name, note) in enumerate(rows):
        ry = y + i * rh
        if i:
            d.line((M + 50, ry, W - M - 50, ry), fill=BR.rgb(BR.BORDER), width=3)
        d.text((M + 60, ry + rh / 2), tag, font=F(40, 700), fill=colr, anchor="lm")
        d.text((M + 560, ry + rh / 2), name, font=F(48, 700), fill=GREEN, anchor="lm")
        nf = F(38, 400)
        lines = BL.wrap(d, note, nf, W - 2 * M - 1460)
        para(img, (M + 1400, ry + rh / 2 - len(lines) * 25 - 4), note, nf, INK2, W - 2 * M - 1460, 1.3)
    logo(img)
    save(img, "06_compatibility.png")


def receive():
    img = canvas()
    y = head(img, "What you receive", "Two workbooks and a guide.", max_w=1500) + 80
    d = ImageDraw.Draw(img)
    files = [("BrassLedger_Cake_Pricing_Calculator.xlsx", "Blank, ready for your prices"),
             ("…_Cake_Pricing_Calculator_SAMPLE.xlsx", "A full sample bakery to explore"),
             ("BrassLedger_Cake_Pricing_Quick_Start_Guide.pdf", "11 pages: set-up, worked examples, FAQ")]
    for i, (name, note) in enumerate(files):
        ry = y + i * 230
        d.rounded_rectangle((M, ry, 1640, ry + 200), 16, fill=WHITE, outline=BR.rgb(BR.BORDER), width=3)
        d.rectangle((M, ry, M + 16, ry + 200), fill=BRASS)
        nf = F(40, 700)
        while d.textlength(name, font=nf) > 1640 - M - 100:
            nf = F(nf.size - 2, 700)
        d.text((M + 64, ry + 70), name, font=nf, fill=GREEN, anchor="lm")
        d.text((M + 64, ry + 140), note, font=F(40, 400), fill=INK2, anchor="lm")
    d.rounded_rectangle((1740, y, W - M, y + 660), 18, fill=GREEN)
    BR.spaced(d, (1800, y + 64), "GOOD TO KNOW", F(30, 700), BRASS, 0.2)
    yy = y + 150
    for it in ["Instant download, no physical item shipped", "Prices are estimates based on your inputs", "No macros or add-ons"]:
        d.rectangle((1800, yy + 26, 1826, yy + 34), fill=BRASS)
        yy = para(img, (1856, yy), it, F(44, 500), PAPER, W - M - 1856 - 50, 1.25) + 40
    logo(img)
    save(img, "07_what_you_receive.png")


if __name__ == "__main__":
    BR.ensure_fonts()
    if OUT.exists():
        for f in OUT.glob("*.png"):
            f.unlink()
    for fn in (hero, included, builder, library, quote_orders, compat, receive):
        fn()
