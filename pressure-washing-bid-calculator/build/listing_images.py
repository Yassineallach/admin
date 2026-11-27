"""Seven Etsy listing images (2700 x 2025 PNG) for the Pressure Washing Bid Calculator, from real screenshots (shoot.py).

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
import pw_config as CFG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "pressure-washing-bid-calculator" / "listing-images"
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
    hero_thumb.hero("pressure")


def hero_legacy():
    img = canvas()
    y = head(img, "Pressure washing · pricing", "Quote any pressure washing job in two minutes.", max_w=1120, size=108)
    y = checks(img, ["Prices each surface: flatwork, house, roof, wood", "Counts chemicals, setup, height and stains",
                     "Prints a quote with your business name"], M, y + 60, 1060, size=46, gap=30, color=GREEN)
    x = pill(img, (M, y + 34), "Excel + Google Sheets", 42)
    pill(img, (x + 24, y + 34), "Exterior cleaning", 42, fill=BR.rgb("F6EBD3"), color=GREEN)
    laptop(img, shot("quote", (0, 0, 1, 0.8)), (1320, 360, 2620, 1520))
    logo(img)
    save(img, "01_hero.png")


def included():
    img = canvas()
    y = head(img, "What's included", "Eight tabs and a quick-start guide.") + 70
    cols = [("Price a job", ["SETTINGS: costs, 20 services, rates, multipliers", "QUICK QUOTE: up to 10 services per job",
                             "CUSTOMER QUOTE: one printable page", "START HERE: quick start and reminders"]),
            ("Run the business", ["QUOTE LOG: 300 quotes, win rate", "JOB LOG: estimate vs actual hours",
                                  "MAINTENANCE PLANS: who is due next", "DASHBOARD: seven key numbers, three charts"]),
            ("Also in your download", ["Blank workbook with example costs", "Sample workbook: a fictional business's season",
                                       "Quick-start guide (PDF, 8 pages)", "Works in Excel and Google Sheets"])]
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
    y = head(img, "Quick quote", "Every service priced, and what you keep per hour.", max_w=2400) + 50
    full = shot("quote_top", (0, 0, 1, 1))
    tiles = green_boxes(full, 0.15, 0.3)
    sh = full.crop((int(full.width * 0.03), 0, full.width, full.height))
    box = frame(img, sh, (M + 640, y, W - M, H - M - 20), "tl")
    s = (box[2] - box[0] - 28) / sh.width
    ox = int(full.width * 0.03)
    d = ImageDraw.Draw(img)
    X = lambda x: box[0] + 14 + (x - ox) * s
    Y = lambda yy: box[1] + 14 + yy * s
    # 1: the service lines (between the services header band and the note under the lines)
    px = full.load()
    anyg = lambda p: (p[0] < 60 and 45 < p[1] < 80 and p[2] < 70) or (35 < p[0] < 60 and 70 < p[1] < 95 and 60 < p[2] < 85)
    band = [y for y in range(int(full.height * 0.4), full.height)
            if sum(anyg(px[x, y]) for x in range(0, full.width, 9)) > full.width / 9 * 0.5]
    h0, h1 = band[0], band[0]
    for yy in band[1:]:
        if yy - h1 > 3:
            break
        h1 = yy
    row_h = (h1 - h0) * 20 / 34                          # header row is 34 pt, line rows 20 pt
    filled = sum(1 for ln in CFG.QUOTE["lines"])
    lines_top, lines_bottom = h0, h1 + row_h * filled
    xs = [x for x in range(full.width) if anyg(px[x, h0 + 3])]
    hdr = (xs[0], h0, xs[-1], h1)
    marks = [((X(hdr[0]), Y(lines_top), X(hdr[2]), Y(lines_bottom)), "1"),
             ((X(tiles[1][0]), Y(tiles[1][1]), X(tiles[1][2]), Y(tiles[1][3])), "2")]
    for (x0, y0, x1, y1), num in marks:
        d.rounded_rectangle((x0 - 8, y0 - 8, x1 + 4, y1 + 8), 16, outline=BRASS, width=8)
        cx, cy = x1 + 10, y0 - 10
        d.ellipse((cx - 36, cy - 36, cx + 36, cy + 36), fill=BRASS)
        d.text((cx, cy), num, font=F(40, 700), fill=GREEN, anchor="mm")
    notes = [("1", "SERVICE LINES", "House wash, driveway, walkway, gutters: up to 10 per job, each with condition, height and stains."),
             ("2", "PROFIT PER JOB HOUR", "What the job earns per hour on top of your own pay, driving included.")]
    ty = y + 20
    for num, title, body in notes:
        d.rounded_rectangle((M, ty, M + 580, ty + 360), 20, fill=GREEN)
        BR.spaced(d, (M + 44, ty + 44), title, F(28, 700), BRASS, 0.2)
        para(img, (M + 44, ty + 100), body, F(36, 500), PAPER, 500, 1.3)
        d.ellipse((M + 580 - 36, ty - 36, M + 580 + 36, ty + 36), fill=BRASS)
        d.text((M + 580, ty), num, font=F(40, 700), fill=GREEN, anchor="mm")
        ty += 410
    para(img, (M, ty + 10), "Bundle discount, water hauling, travel surcharge and minimum charge built in.", F(38, 600), INK2, 580, 1.3)
    logo(img)
    save(img, "03_quick_quote.png")


def customer():
    img = canvas()
    y = head(img, "Customer quote", "Send a professional quote with your own business name.", max_w=1300) + 60
    frame(img, shot("customer"), (1450, y - 220, W - M, H - M), "tl")
    points(img, [("Your business, not ours", "Name, contact details and terms from SETTINGS. Space for your logo."),
                 ("Itemised and clear", "Each service with its details, the bundle discount and the total."),
                 ("Plan offer included", "A yearly maintenance plan in one line. Fits one letter page.")], M, y + 40, 1150, 50, 40, 60)
    logo(img)
    save(img, "04_customer_quote.png")


def plans_jobs():
    img = canvas()
    y = head(img, "Plans and job log", "Turn one-time jobs into yearly clients.") + 50
    a = shot("plans", (0, 0, 1, 1))
    b = shot("jobs_summary", (0, 0, 1, 1))
    boxa = frame(img, a, (M, y, W - M, y + 760), "tl")
    frame(img, b, (M + 640, boxa[3] + 40, W - M, H - M + 60), "tl")
    points(img, [("Who's due next", "Next clean dates and plan revenue."),
                 ("Real production rates", "Estimate vs actual tells you which rates to change.")], M, boxa[3] + 60, 560, 42, 34, 40)
    logo(img)
    save(img, "05_plans_job_log.png")


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
    files = [("BrassLedger_Pressure_Washing_Bid_Calculator.xlsx", "Blank, with example costs to replace"),
             ("…_Bid_Calculator_SAMPLE.xlsx", "A sample business to explore"),
             ("BrassLedger_Pressure_Washing_Quick_Start_Guide.pdf", "8 pages: set-up, worked example, FAQ")]
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
    for fn in (hero, included, quote_closeup, customer, plans_jobs, compat, receive):
        fn()
