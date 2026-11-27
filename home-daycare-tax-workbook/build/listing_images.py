"""Seven Etsy listing images (2700 x 2025 PNG) for the Home Daycare Tax Workbook, from real screenshots (shoot.py).

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
OUT = ROOT / "dist" / "home-daycare-tax-workbook" / "listing-images"
POS = BR.rgb(BR.POSITIVE)
# HOURS LOG column widths A..O (A = the sidebar column) (from build_workbook.py), used to place the callout on the real screenshot
H_WIDTHS = [w + 0.71 for w in (7.65, 13, 7, 11, 11, 11, 11, 24, 44, 9, 11, 11, 11, 11, 17)]   # columns A..O (+5 px padding each)


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


def hero():
    """Photo 1 comes from the shared thumbnail system (productivity-bundle/build/hero_thumb.py)."""
    import hero_thumb
    hero_thumb.hero("daycare")


def hero_legacy():
    img = canvas()
    y = head(img, "Home daycare · tax records", "Your time-space percentage, calculated and documented.", max_w=1080, size=112)
    y = checks(img, ["Counts prep, cleaning and paperwork hours", "Applies the right share to every expense",
                     "Prints a statement for your tax preparer"], M, y + 60, 1040, size=46, gap=30, color=GREEN)
    x = pill(img, (M, y + 34), "Excel + Google Sheets", 42)
    pill(img, (x + 24, y + 34), "For US providers", 42, fill=BR.rgb("F6EBD3"), color=GREEN)
    frame(img, shot("dash_top"), (1180, 330, W - M, 1700), "tl")
    logo(img)
    save(img, "01_hero.png")


def included():
    img = canvas()
    y = head(img, "What's included", "Eleven tabs and a quick-start guide.") + 70
    cols = [("Set up and log", ["START HERE: 4-step quick start", "SETTINGS: tax year, dates, rates, usual hours",
                                "ROOMS: square feet and use type", "HOURS LOG: every day of the year, prefilled",
                                "EXPENSES: 500 rows, share applied for you"]),
            ("Results and optional", ["DASHBOARD: key figures and four charts", "MEALS: standard meal and snack rates", "MILEAGE: two rates by date",
                                      "SUMMARY: step-by-step percentage and totals", "TIME-SPACE STATEMENT: one printable page",
                                      "FOR YOUR TAX PREPARER: home details and checklist"]),
            ("Also in your download", ["Blank workbook for your records", "Sample workbook: a full year for a fictional provider",
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
            yy = para(img, (x + 92, yy), it, F(40, 500), INK, cw - 140, 1.22) + 28
    logo(img)
    save(img, "02_whats_included.png")


def hours():
    img = canvas()
    y = head(img, "The hours log", "Every day of the year, prefilled from your usual hours.") + 60
    sh = shot("hours_left", (0, 0, 1, 0.58))
    box = frame(img, sh, (M, y, W - M, y + 1000), "tl")
    s = (box[2] - box[0] - 28) / sh.width
    # measure the real column borders: the header is the last full-width green band, the grid lines run below it
    px = sh.load()
    green = lambda p: p[0] < 70 and 50 < p[1] < 100 and p[2] < 90
    x_from = int(sh.width * 0.08)                            # skip the sidebar
    is_band = lambda y: sum(green(px[x, y]) for x in range(x_from, sh.width, 7)) > (sh.width - x_from) / 7 * 0.6
    runs, y0 = [], None
    for yy in range(int(sh.height * 0.1), sh.height):
        if is_band(yy) and y0 is None:
            y0 = yy
        elif not is_band(yy) and y0 is not None:
            runs.append((y0, yy))
            y0 = None
    hy, hy1 = runs[-1]                                       # header row: the last green band (title bar and tiles are above it)
    body = range(hy1 + 10, sh.height - 5)                    # vertical cell borders run through every body row
    line = lambda p: 200 <= p[0] <= 236 and abs(p[0] - p[2]) < 20
    seps = [x for x in range(x_from, sh.width) if sum(line(px[x, y]) for y in body) > len(body) * 0.8]
    cols = []
    for x in seps:                                           # cluster 1-2 px borders
        if not cols or x - cols[-1][-1] > 3:
            cols.append([x])
        else:
            cols[-1].append(x)
    seps = [sum(c) / len(c) for c in cols]
    edge = lambda x: box[0] + 14 + x * s

    def span(i):                                             # i = 0 for column B; seps[0] is the B|C border
        return edge(seps[i - 1]), edge(seps[i])
    top = box[1] + 14 + hy * s
    d = ImageDraw.Draw(img)
    for i in (5, 11):                                        # G: other business hours (typed), M: other hours (used)
        x0, x1 = span(i)
        d.rounded_rectangle((x0 + 1, top - 6, x1 + 8, box[3] - 8), 14, outline=BRASS, width=8)
    g0, g1 = span(5)
    cy = box[3] + 60
    cx = (g0 + g1) / 2
    d.polygon([(cx - 28, cy), (cx + 28, cy), (cx, box[3] - 2)], fill=BRASS)
    tw = 1400
    bx0 = max(M, cx - 200)
    d.rounded_rectangle((bx0, cy, bx0 + tw, cy + 230), 20, fill=GREEN)
    BR.spaced(d, (bx0 + 48, cy + 44), "COUNTS PREP AND CLEANING TIME TOO", F(30, 700), BRASS, 0.22)
    para(img, (bx0 + 48, cy + 96), "Add time you use the home for the business when children aren't there: preparing, "
         "cleaning, meal prep, paperwork.", F(38, 500), PAPER, tw - 96, 1.25)
    para(img, (bx0 + tw + 60, cy + 30), "Grey days are prefilled. They count once you confirm or edit them.", F(40, 600), INK2,
         W - M - (bx0 + tw + 60), 1.3)
    logo(img)
    save(img, "03_hours_log.png")


def rooms_summary():
    img = canvas()
    y = head(img, "Rooms and summary", "The calculation, step by step.") + 60
    a = shot("rooms", (0, 0.15, 0.66, 0.485))
    b = shot("summary1", (0, 0.07, 1, 0.524))
    boxa = frame(img, a, (M, y, 1040, H - M - 230), "tl")
    frame(img, b, (1100, y, W - M, H - M - 230), "tl")
    yy = boxa[3] + 50
    points(img, [("Space", "Exclusive rooms count in full; shared rooms × time."),
                 ("Time", "Business hours ÷ 8,760 hours (8,784 in a leap year)."),
                 ("Result", "Each step shown, so your preparer can follow it.")], M, yy, 900, 44, 36, 34)
    logo(img)
    save(img, "04_rooms_and_summary.png")


def steps():
    img = canvas()
    y = head(img, "How it works", "Four steps, then a little each week.") + 80
    d = ImageDraw.Draw(img)
    cw = (W - 2 * M - 3 * 50) // 4
    items = [("Settings", "Tax year, business dates, rates and your usual hours."),
             ("Rooms", "Square feet and use type for every room."),
             ("Hours, weekly", "Confirm the usual days, fix the rest, add prep and cleaning time."),
             ("Expenses", "One row per receipt. The share is applied for you.")]
    for i, (title, body) in enumerate(items):
        x = M + i * (cw + 50)
        d.rounded_rectangle((x, y, x + cw, H - M - 250), 18, fill=GREEN)
        d.text((x + 56, y + 40), str(i + 1), font=FH(220), fill=BRASS)
        BR.double_rule(d, x + 56, y + 340, 140, 100)
        yy = para(img, (x + 56, y + 410), title, FH(70), PAPER, cw - 112, 1.1)
        para(img, (x + 56, yy + 34), body, F(42, 400), (220, 226, 222), cw - 112, 1.36)
    logo(img)
    save(img, "05_how_it_works.png")


def compat():
    img = canvas()
    y = head(img, "Compatibility", "Excel or Google Sheets. Best on a computer.") + 80
    rows = [("Yes", POS, "Microsoft Excel 2016 or later", "Windows and Mac. Formulas are locked against accidental edits."),
            ("Yes", POS, "Google Sheets", "Make a copy from the link in the guide, or upload the file to Google Drive."),
            ("Best on a computer", INK2, "Phones and tablets", "It opens in the apps, but logging is easiest on a laptop."),
            ("US only", INK2, "For US providers", "Built around IRS Form 8829, Schedule C and Pub. 587. Not tax advice."),
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
    files = [("BrassLedger_Home_Daycare_Tax_Workbook.xlsx", "Blank, for your records"),
             ("…_Tax_Workbook_SAMPLE.xlsx", "A full sample year to explore"),
             ("…_Home_Daycare_Quick_Start_Guide.pdf", "9 pages: set-up, rules, FAQ")]
    for i, (name, note) in enumerate(files):
        ry = y + i * 230
        d.rounded_rectangle((M, ry, 1640, ry + 200), 16, fill=WHITE, outline=BR.rgb(BR.BORDER), width=3)
        d.rectangle((M, ry, M + 16, ry + 200), fill=BRASS)
        d.text((M + 64, ry + 70), name, font=F(42, 700), fill=GREEN, anchor="lm")
        d.text((M + 64, ry + 140), note, font=F(40, 400), fill=INK2, anchor="lm")
    d.rounded_rectangle((1740, y, W - M, y + 660), 18, fill=GREEN)
    BR.spaced(d, (1800, y + 64), "GOOD TO KNOW", F(30, 700), BRASS, 0.2)
    yy = y + 150
    for it in ["Instant download, no physical item shipped", "Not tax advice", "Rates change: check current rates"]:
        d.rectangle((1800, yy + 26, 1826, yy + 34), fill=BRASS)
        yy = para(img, (1856, yy), it, F(44, 500), PAPER, W - M - 1856 - 50, 1.25) + 40
    logo(img)
    save(img, "07_what_you_receive.png")


if __name__ == "__main__":
    BR.ensure_fonts()
    if OUT.exists():
        for f in OUT.glob("*.png"):
            f.unlink()
    for fn in (hero, included, hours, rooms_summary, steps, compat, receive):
        fn()
