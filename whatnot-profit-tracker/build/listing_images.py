"""Seven Etsy listing images (2700 x 2025 PNG) in the Brass Ledger layout, from real screenshots (shoot.py).

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

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "whatnot-profit-tracker" / "listing-images"
LOGO_PNG = Path("/home/user/admin/productivity-bundle/brand/logo_light.png")
NEG = BR.rgb("B3261E")
POS = BR.rgb(BR.POSITIVE)


def shot(name, crop=None):
    im = Image.open(SCREENS / f"{name}.png").convert("RGB")
    if crop:
        w, h = im.size
        l, t, r, b = crop
        im = im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
    return im


def logo_rgba(width):
    """The supplied logo PNG with its white background made transparent."""
    im = Image.open(LOGO_PNG).convert("RGBA")
    bbox = im.convert("L").point(lambda v: 255 if v < 245 else 0).getbbox()
    im = im.crop(bbox)
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            lum = min(r, g, b)
            if lum > 235:                                  # near-white -> transparent, edges keep partial alpha
                px[x, y] = (r, g, b, int(255 * max(0, 255 - lum) / 20))
    return im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)


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


# ---------------------------------------------------------------- 1 hero
def hero():
    """Photo 1 comes from the shared thumbnail system (productivity-bundle/build/hero_thumb.py)."""
    import hero_thumb
    hero_thumb.hero("whatnot")


def hero_legacy():
    img = canvas()
    y = head(img, "Whatnot sellers · profit tracker", "See the real profit from every show.", max_w=1060, size=128)
    y = checks(img, ["Fees, item costs, giveaways and supplies taken off for you",
                     "See which time slots, days and categories make money",
                     "One row per show. About two minutes to log"], M, y + 70, 1040, size=48, gap=34, color=GREEN)
    pill(img, (M, y + 40), "Excel + Google Sheets", 44)
    laptop(img, shot("dash_hero"), (1230, 330, 2610, 1500))
    logo(img)
    save(img, "01_hero.png")


# ---------------------------------------------------------------- 2 what's included
def included():
    img = canvas()
    y = head(img, "What's included", "Six tabs and a quick-start guide.") + 70
    cols = [("The workbook", ["START HERE: quick start and colour key", "SETTINGS: fee rates, giveaway cost, goal, your lists",
                              "SHOW LOG: one row per show, 300 rows", "ITEM SALES: optional item-by-item tracking",
                              "DASHBOARD: tiles, tables and charts", "YEAR SUMMARY: month-by-month totals"]),
            ("What it works out", ["Commission and processing fees", "Net profit and profit margin", "Profit per hour live",
                                   "Average order value", "Giveaway cost as % of sales", "Best and worst shows"]),
            ("Also in your download", ["Blank file for your shows", "Sample file with 12 example shows", "Quick-start guide (PDF)",
                                       "Works in Excel and Google Sheets"])]
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
            yy = para(img, (x + 92, yy), it, F(42, 500), INK, cw - 140, 1.22) + 30
    logo(img)
    save(img, "02_whats_included.png")


# ---------------------------------------------------------------- 3 show log close-up with a callout on net profit
def show_log():
    img = canvas()
    y = head(img, "The show log", "One row per show. Profit appears as you type.") + 60
    sh = shot("log_profit")
    box = frame(img, sh, (M, y, W - M, y + 1020), "tl")
    # find the brass NET PROFIT header: brass pixels inside the green header row of the real screenshot
    px = sh.load()
    green = lambda p: p[0] < 70 and 50 < p[1] < 100 and p[2] < 90
    brass = lambda p: abs(p[0] - 210) < 14 and abs(p[1] - 154) < 14 and abs(p[2] - 58) < 14
    band = [y for y in range(sh.height) if sum(green(px[x, y]) for x in range(0, sh.width, 9)) > sh.width / 9 * 0.45]
    hy = band[len(band) // 2]
    xs = [x for x in range(sh.width) if brass(px[x, hy])]
    s = (box[2] - box[0] - 28) / sh.width
    x0, x1 = box[0] + 14 + min(xs) * s, box[0] + 14 + max(xs) * s
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0 - 4, box[1] + 6, x1 + 9, box[3] - 6), 14, outline=BRASS, width=7)
    # callout below
    cy = box[3] + 60
    cx = (x0 + x1) / 2
    d.polygon([(cx - 28, cy), (cx + 28, cy), (cx, box[3] - 2)], fill=BRASS)
    tw = 1240
    bx0 = min(max(M, cx - tw / 2), W - M - tw)
    d.rounded_rectangle((bx0, cy, bx0 + tw, cy + 230), 20, fill=GREEN)
    BR.spaced(d, (bx0 + 48, cy + 44), "NET PROFIT", F(30, 700), BRASS, 0.22)
    para(img, (bx0 + 48, cy + 96), "Gross sales minus Whatnot fees, item costs, giveaways, supplies and other costs.",
         F(40, 500), PAPER, tw - 96, 1.25)
    d.text((M, cy + 40), "Red = a loss.", font=F(42, 700), fill=NEG)
    d.text((M, cy + 110), "Green = top 25 % of shows.", font=F(42, 700), fill=POS)
    logo(img)
    save(img, "03_show_log.png")


# ---------------------------------------------------------------- 4 dashboard close-up
def dashboard():
    img = canvas()
    y = head(img, "The dashboard", "Find the time slots and categories that pay.") + 60
    a, b = shot("dash_slot"), shot("dash_cat")
    stack = Image.new("RGB", (max(a.width, b.width), a.height + b.height + 40), PAPER)
    stack.paste(a, (0, 0))
    stack.paste(b, (0, a.height + 40))
    box = frame(img, stack, (M, y, W - M, y + 1180), "tl")
    items = [("Profit by time slot", "Shows, net profit, average per show and profit per hour."),
             ("Profit by category", "See which categories carry your shop."),
             ("A plain-English line", "Each table names your best time slot, day or category.")]
    cw = (W - 2 * M - 2 * 60) // 3
    for k, it in enumerate(items):
        x = M + k * (cw + 60)
        d = ImageDraw.Draw(img)
        d.text((x, box[3] + 64), f"{k + 1:02d}", font=F(34, 700), fill=BRASS)
        yy = para(img, (x + 90, box[3] + 58), it[0], F(44, 700), GREEN, cw - 90, 1.2)
        para(img, (x + 90, yy + 4), it[1], F(36, 400), INK2, cw - 90, 1.35)
    logo(img)
    save(img, "04_dashboard.png")


# ---------------------------------------------------------------- 5 how it works
def steps():
    img = canvas()
    y = head(img, "How it works", "Three steps after each show.") + 90
    d = ImageDraw.Draw(img)
    cw = (W - 2 * M - 2 * 70) // 3
    items = [("Set your fees", "Check commission and processing rates once on SETTINGS."),
             ("Log the show", "Date, times, sales, orders, item costs, giveaways and supplies. One row."),
             ("Read the dashboard", "Profit for the month, fees, giveaways and your best time slots.")]
    for i, (title, body) in enumerate(items):
        x = M + i * (cw + 70)
        d.rounded_rectangle((x, y, x + cw, H - M - 240), 18, fill=GREEN)
        d.text((x + 64, y + 50), str(i + 1), font=FH(250), fill=BRASS)
        BR.double_rule(d, x + 64, y + 380, 160, 110)
        yy = para(img, (x + 64, y + 460), title, FH(80), PAPER, cw - 128, 1.1)
        para(img, (x + 64, yy + 40), body, F(48, 400), (220, 226, 222), cw - 128, 1.38)
    logo(img)
    save(img, "05_how_it_works.png")


# ---------------------------------------------------------------- 6 compatibility
def compat():
    img = canvas()
    y = head(img, "Compatibility", "Works in Excel and Google Sheets.") + 80
    rows = [("Yes", POS, "Microsoft Excel 2016 or later", "Windows and Mac. Formulas are locked against accidental edits."),
            ("Yes", POS, "Google Sheets", "Upload the file to Google Drive and open it, or use the copy link in the guide."),
            ("Yes", POS, "Excel for the web", "Opens the same file in your browser."),
            ("Best on a computer", INK2, "Phones and tablets", "The sheets open in the apps, but logging is easiest on a laptop."),
            ("Digital", INK2, "Instant download", "No physical item is shipped.")]
    d = ImageDraw.Draw(img)
    rh = (H - M - 260 - y) // len(rows)
    d.rounded_rectangle((M, y, W - M, y + rh * len(rows)), 18, fill=WHITE, outline=BR.rgb(BR.BORDER), width=3)
    for i, (tag, colr, name, note) in enumerate(rows):
        ry = y + i * rh
        if i:
            d.line((M + 50, ry, W - M - 50, ry), fill=BR.rgb(BR.BORDER), width=3)
        d.text((M + 60, ry + rh / 2), tag, font=F(40, 700), fill=colr, anchor="lm")
        d.text((M + 560, ry + rh / 2), name, font=F(50, 700), fill=GREEN, anchor="lm")
        nf = F(40, 400)
        lines = BL.wrap(d, note, nf, W - 2 * M - 1460)
        para(img, (M + 1400, ry + rh / 2 - len(lines) * 26 - 4), note, nf, INK2, W - 2 * M - 1460, 1.3)
    logo(img)
    save(img, "06_compatibility.png")


# ---------------------------------------------------------------- 7 what you receive
def receive():
    img = canvas()
    y = head(img, "What you receive", "Two workbooks and a guide.", max_w=1500) + 80
    d = ImageDraw.Draw(img)
    files = [("BrassLedger_Whatnot_Profit_Tracker.xlsx", "Blank, for your shows"),
             ("…_Profit_Tracker_SAMPLE.xlsx", "12 example shows to explore"),
             ("BrassLedger_Whatnot_Quick_Start_Guide.pdf", "Set-up and FAQ")]
    for i, (name, note) in enumerate(files):
        ry = y + i * 230
        d.rounded_rectangle((M, ry, 1640, ry + 200), 16, fill=WHITE, outline=BR.rgb(BR.BORDER), width=3)
        d.rectangle((M, ry, M + 16, ry + 200), fill=BRASS)
        d.text((M + 64, ry + 70), name, font=F(44, 700), fill=GREEN, anchor="lm")
        d.text((M + 64, ry + 140), note, font=F(40, 400), fill=INK2, anchor="lm")
    d.rounded_rectangle((1740, y, W - M, y + 660), 18, fill=GREEN)
    BR.spaced(d, (1800, y + 64), "GOOD TO KNOW", F(30, 700), BRASS, 0.2)
    yy = y + 150
    for it in ["Instant download, no physical item shipped", "Not affiliated with Whatnot", "No macros or add-ons"]:
        d.rectangle((1800, yy + 26, 1826, yy + 34), fill=BRASS)
        yy = para(img, (1856, yy), it, F(44, 500), PAPER, W - M - 1856 - 50, 1.25) + 40
    logo(img)
    save(img, "07_what_you_receive.png")


if __name__ == "__main__":
    BR.ensure_fonts()
    if OUT.exists():
        for f in OUT.glob("*.png"):
            f.unlink()
    for fn in (hero, included, show_log, dashboard, steps, compat, receive):
        fn()
