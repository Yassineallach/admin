"""Seven Etsy listing images (2700 x 2025 PNG) for the Lawn Care Pricing Calculator, from real screenshots (shoot.py).

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

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "lawn-care-pricing-calculator" / "listing-images"
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



def tiles_box(sh):
    """Find the two green result tiles (price per visit, profit per hour) on the QUICK QUOTE screenshot."""
    px = sh.load()
    green = lambda p: p[0] < 60 and 45 < p[1] < 80 and p[2] < 70
    w, h = sh.size
    # the tiles are the first green band below the title bar on the right half
    rows = [y for y in range(0, int(h * 0.4)) if sum(green(px[x, y]) for x in range(0, w, 9)) > w / 9 * 0.3]
    groups = []
    for y in rows:
        if groups and y - groups[-1][1] <= 3:
            groups[-1][1] = y
        else:
            groups.append([y, y])
    y0, y1 = groups[1] if groups[0][0] < h * 0.06 else groups[0]      # skip the title bar
    ym = y0 + 3                                           # just inside the top edge: no text there
    xs = [x for x in range(w) if green(px[x, ym])]
    runs, start, prev = [], xs[0], xs[0]
    for x in xs[1:]:
        if x - prev > 3:
            runs.append((start, prev))
            start = x
        prev = x
    runs.append((start, prev))
    runs = [r for r in runs if r[1] - r[0] > w * 0.05][:2]
    return [(a, y0, b, y1) for a, b in runs]


def hero():
    """Photo 1 comes from the shared thumbnail system (productivity-bundle/build/hero_thumb.py)."""
    import hero_thumb
    hero_thumb.hero("lawn")


def hero_legacy():
    img = canvas()
    y = head(img, "Lawn care · pricing", "Price every lawn for profit in two minutes.", max_w=1100, size=112)
    y = checks(img, ["Counts fuel, equipment wear, insurance and drive time", "Prices each visit, month and season",
                     "Prints a quote with your business name"], M, y + 60, 1060, size=46, gap=30, color=GREEN)
    x = pill(img, (M, y + 34), "Excel + Google Sheets", 42)
    pill(img, (x + 24, y + 34), "Built for lawn care", 42, fill=BR.rgb("F6EBD3"), color=GREEN)
    laptop(img, shot("quote_top", (0, 0, 1, 0.83)), (1250, 360, 2620, 1520))
    logo(img)
    save(img, "01_hero.png")


def included():
    img = canvas()
    y = head(img, "What's included", "Eight tabs and a quick-start guide.") + 70
    cols = [("Price a job", ["SETTINGS: your costs, mower speeds, add-on prices", "QUICK QUOTE: price per visit, monthly, season",
                             "CUSTOMER QUOTE: one printable page", "START HERE: 3-step quick start"]),
            ("Run the season", ["QUOTE LOG: 300 quotes, win rate", "ROUTE PLANNER: revenue per hour by day",
                                "SEASON TRACKER: revenue vs goal", "DASHBOARD: six key numbers, three charts"]),
            ("Also in your download", ["Blank workbook with example costs", "Sample workbook: a full season for a fictional business",
                                       "Quick-start guide (PDF, 9 pages)", "Works in Excel and Google Sheets"])]
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


def quote_closeup():
    img = canvas()
    y = head(img, "Quick quote", "The price, and what you keep, for every visit.") + 60
    sh = shot("quote_top", (0.4895, 0.08, 1.0, 0.62))
    box = frame(img, sh, (M + 700, y, W - M, H - M - 40), "tl")
    s = (box[2] - box[0] - 28) / sh.width
    d = ImageDraw.Draw(img)
    tiles = tiles_box(sh)
    notes = [("PRICE PER VISIT", "Cost ÷ (1 − your margin), rounded up, never below your minimum charge."),
             ("PROFIT PER JOB HOUR", "What the job earns per hour on top of your own pay, driving included.")]
    ty = y + 40
    for (x0, y0, x1, y1), (title, body) in zip(tiles, notes):
        X0, Y0 = box[0] + 14 + x0 * s, box[1] + 14 + y0 * s
        X1, Y1 = box[0] + 14 + x1 * s, box[1] + 14 + y1 * s
        d.rounded_rectangle((X0 - 12, Y0 - 12, X1 + 12, Y1 + 12), 16, outline=BRASS, width=8)
        d.rounded_rectangle((M, ty, M + 620, ty + 330), 20, fill=GREEN)
        BR.spaced(d, (M + 44, ty + 44), title, F(28, 700), BRASS, 0.2)
        para(img, (M + 44, ty + 100), body, F(38, 500), PAPER, 540, 1.3)
        num = "1" if title.startswith("PRICE") else "2"
        for cx, cy in ((X1 + 12, Y0 - 12), (M + 620, ty)):            # numbered badge on the tile and on the note
            d.ellipse((cx - 36, cy - 36, cx + 36, cy + 36), fill=BRASS)
            d.text((cx, cy), num, font=F(40, 700), fill=GREEN, anchor="mm")
        ty += 380
    para(img, (M, ty + 20), "Red warnings when a job is below break-even or under your profit target.", F(40, 600), INK2, 620, 1.3)
    logo(img)
    save(img, "03_quick_quote.png")


def customer():
    img = canvas()
    y = head(img, "Customer quote", "Send a professional quote with your own business name.", max_w=1300) + 60
    sh = shot("customer")
    frame(img, sh, (1450, y - 220, W - M, H - M), "tl")
    points(img, [("Your business, not ours", "Name, contact details and terms from SETTINGS. Space for your logo."),
                 ("Filled in for you", "Service, frequency, price per visit, monthly and season prices, add-ons."),
                 ("One letter page", "Print it, or save as PDF and email it. Signature line included.")], M, y + 40, 1150, 50, 40, 60)
    logo(img)
    save(img, "04_customer_quote.png")


def routes():
    img = canvas()
    y = head(img, "Route planner and dashboard", "See which days and clients pay best.") + 50
    a = shot("route_summary", (0, 0, 1, 0.72))
    b = shot("dash_lower", (0, 0.5, 1, 1))
    boxa = frame(img, a, (M, y, W - M, y + 760), "tl")
    frame(img, b, (M + 640, boxa[3] + 40, W - M, H - M + 60), "tl")
    points(img, [("Revenue per hour", "Each weekday, driving included."),
                 ("Driving warnings", "When driving eats over a quarter of the day.")], M, boxa[3] + 60, 560, 42, 34, 40)
    logo(img)
    save(img, "05_routes_dashboard.png")


def compat():
    img = canvas()
    y = head(img, "Compatibility", "Excel or Google Sheets. Best on a computer.") + 80
    rows = [("Yes", POS, "Microsoft Excel 2016 or later", "Windows and Mac. Formulas are locked against accidental edits."),
            ("Yes", POS, "Google Sheets", "Make a copy from the link in the guide, or upload the file to Google Drive."),
            ("Best on a computer", INK2, "Phones and tablets", "It opens in the apps, but quoting is easiest on a laptop."),
            ("No add-ons", INK2, "No macros, no extensions", "Plain formulas, so nothing to enable or install."),
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
    files = [("BrassLedger_Lawn_Care_Pricing_Calculator.xlsx", "Blank, with example costs to replace"),
             ("…_Pricing_Calculator_SAMPLE.xlsx", "A full sample season to explore"),
             ("BrassLedger_Lawn_Care_Quick_Start_Guide.pdf", "9 pages: set-up, worked examples, FAQ")]
    for i, (name, note) in enumerate(files):
        ry = y + i * 230
        d.rounded_rectangle((M, ry, 1640, ry + 200), 16, fill=WHITE, outline=BR.rgb(BR.BORDER), width=3)
        d.rectangle((M, ry, M + 16, ry + 200), fill=BRASS)
        d.text((M + 64, ry + 70), name, font=F(40, 700), fill=GREEN, anchor="lm")
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
    for fn in (hero, included, quote_closeup, customer, routes, compat, receive):
        fn()
