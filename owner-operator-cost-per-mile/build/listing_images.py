"""Seven Etsy listing images (2700 x 2025 PNG) for the Owner-Operator Cost Per Mile calculator, from real screenshots.

Layout: paper background, brass kicker, large green Fraunces headline, short brass double rule, logo bottom-left.
Every screen is a real render of the SAMPLE workbook (shoot.py); nothing is drawn by hand except the device frames.
Usage: python listing_images.py   (run shoot.py first)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, "/home/user/admin/productivity-bundle/build")
import brand as BR  # noqa: E402
import brand_listing as BL  # noqa: E402
from brand_listing import BRASS, GREEN, H, INK, INK2, M, PAPER, W, WHITE, F, FH, canvas, checks, frame, head, laptop, para, points  # noqa: E402

from brandimg import logo_rgba  # noqa: E402
import truck_config as CFG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCREENS = ROOT / "dist" / "screens"
OUT = ROOT / "dist" / "owner-operator-cost-per-mile" / "listing-images"
POS, NEG = BR.rgb("2E7D4F"), BR.rgb("B3261E")
TINT = BR.rgb("F6EBD3")


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


def phone(img, sh, x, y, h):
    """A plain phone frame (no brand) around a real screenshot, screen height h."""
    sw = int(h * sh.width / sh.height)
    pad, r = 34, 90
    box = (x, y, x + sw + 2 * pad, y + h + 2 * pad + 60)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((box[0] + 14, box[1] + 30, box[2] + 14, box[3] + 30), r, fill=(0, 0, 0, 90))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(36))).convert("RGB"))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, r, fill=(28, 30, 32))
    img.paste(sh.resize((sw, h), Image.LANCZOS), (x + pad, y + pad + 40))
    d.rounded_rectangle((box[0] + (box[2] - box[0]) // 2 - 90, y + 22, box[0] + (box[2] - box[0]) // 2 + 90, y + 46), 12, fill=(10, 10, 12))
    return box


def save(img, name):
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / name, "PNG", optimize=True)
    print("wrote", name)


def hero():
    img = canvas()
    y = head(img, "Owner-operators · hotshot · box truck", CFG.PROMISE, max_w=1150, size=112)
    y = checks(img, ["Your real cost per mile, deadhead and your pay included", "TAKE, NEGOTIATE or PASS on any load, on your phone",
                     "Trip, fuel and monthly profit records"], M, y + 50, 1150, size=46, gap=30, color=GREEN)
    x = pill(img, (M, y + 30), "Excel + Google Sheets", 42)
    pill(img, (x + 24, y + 30), "Phone tab", 42, fill=TINT, color=GREEN)
    laptop(img, shot("settings_top", (0.045, 0.085, 1, 1.0)), (1380, 280, 2680, 1600))
    logo(img)
    save(img, "01_hero.png")


def included():
    img = canvas()
    y = head(img, "What's included", "Eight tabs and a quick-start guide.") + 70
    cols = [("Know your numbers", ["SETTINGS: presets, fixed and variable costs, your pay", "Cost per mile: fixed, operating, all-in, target",
                                    "Miles-per-month table: what idle weeks cost", "START HERE: 3-step quick start"]),
            ("Check the load", ["LOAD CHECK: one column for your phone", "TAKE, NEGOTIATE or PASS, with a counter-offer",
                                "LOAD COMPARE: five offers side by side", "Best profit per day marked"]),
            ("Keep the records", ["TRIP LOG: 500 loads, profit per load", "FUEL LOG: MPG, miles by state for IFTA records",
                                  "MONTHLY P&L and DASHBOARD", "Quick-start guide (PDF, 9 pages)"])]
    d = ImageDraw.Draw(img)
    cw = (W - 2 * M - 120) // 3
    bottom = y + 900
    for i, (title, items) in enumerate(cols):
        x = M + i * (cw + 60)
        d.rounded_rectangle((x, y, x + cw, bottom), 18, fill=WHITE, outline=BR.rgb(BR.BORDER), width=3)
        d.rectangle((x, y, x + cw, y + 12), fill=GREEN)
        BR.spaced(d, (x + 48, y + 58), title.upper(), F(30, 700), BRASS, 0.2)
        yy = y + 140
        for it in items:
            d.rectangle((x + 48, yy + 24, x + 70, yy + 31), fill=BRASS)
            yy = para(img, (x + 92, yy), it, F(50, 500), INK, cw - 140, 1.22) + 54
    logo(img)
    save(img, "02_whats_included.png")


def check():
    img = canvas()
    head(img, "Load check · on your phone", "Check any load in 30 seconds.", max_w=1400, size=112)
    sh = shot("check_top")
    phone(img, sh, 1700, 90, 1760)
    points(img, [("Four numbers", "Rate, loaded miles, deadhead, days."),
                 ("A clear verdict", "Green TAKE, amber NEGOTIATE, red PASS."),
                 ("The counter-offer", "The rate you need to hit your target."),
                 ("Deadhead counted", "$3.03 a loaded mile, and still a PASS.")], M, 560, 1350, 46, 40, 40)
    logo(img)
    save(img, "03_load_check_phone.png")


def compare():
    img = canvas()
    y = head(img, "Load compare", "Pick the load that pays best per day.", max_w=2400) + 60
    box = frame(img, shot("compare_out"), (M, y, W - M, y + 1240), "tl")
    points(img, [("Same costs for every load", "From your SETTINGS, so the numbers are fair."),
                 ("Profit per day", "A short load can beat a long one. The best is marked.")], M + 760, box[3] + 50, 1800, 44, 36, 36)
    logo(img)
    save(img, "04_load_compare.png")


def pnl():
    img = canvas()
    y = head(img, "Monthly P&L and dashboard", "See your real cost per mile every month.", max_w=2450, size=104) + 50
    a = frame(img, shot("dash_top", (0, 0, 1, 1)), (M + 640, y, W - M, H - M + 40), "tr")
    points(img, [("Actual against estimate", "Each month's real cost per mile, flagged when it runs 10 % over."),
                 ("Deadhead and revenue", "Deadhead % and revenue per mile against cost, by month."),
                 ("Unpaid invoices", "Every load not yet paid, in one figure.")], M, y + 60, 560, 44, 36, 50)
    logo(img)
    save(img, "05_monthly_pnl.png")


def compat():
    img = canvas()
    y = head(img, "Compatibility", "Laptop, Google Sheets and your phone.") + 80
    rows = [("Yes", POS, "Microsoft Excel 2016 or later", "Windows and Mac. Formulas are locked against accidental edits."),
            ("Yes", POS, "Google Sheets", "Make a copy from the link in the guide, or upload the file to Google Drive."),
            ("Yes", POS, "Google Sheets phone app", "LOAD CHECK is one narrow column: no sideways scrolling."),
            ("6 presets", INK2, "Dry van, reefer, flatbed", "Hotshot (CDL and non-CDL) and box truck. Every value editable."),
            ("Digital", INK2, "Instant download", "No physical item is shipped. No macros or add-ons.")]
    d = ImageDraw.Draw(img)
    rh = (H - M - 260 - y) // len(rows)
    d.rounded_rectangle((M, y, W - M, y + rh * len(rows)), 18, fill=WHITE, outline=BR.rgb(BR.BORDER), width=3)
    for i, (tag, colr, name, note) in enumerate(rows):
        ry = y + i * rh
        if i:
            d.line((M + 50, ry, W - M - 50, ry), fill=BR.rgb(BR.BORDER), width=3)
        d.text((M + 60, ry + rh / 2), tag, font=F(40, 700), fill=colr, anchor="lm")
        d.text((M + 420, ry + rh / 2), name, font=F(46, 700), fill=GREEN, anchor="lm")
        nf = F(38, 400)
        lines = BL.wrap(d, note, nf, W - 2 * M - 1460)
        para(img, (M + 1400, ry + rh / 2 - len(lines) * 25 - 4), note, nf, INK2, W - 2 * M - 1460, 1.3)
    logo(img)
    save(img, "06_compatibility.png")


def receive():
    img = canvas()
    y = head(img, "What you receive", "Two workbooks and a guide.", max_w=1500) + 80
    d = ImageDraw.Draw(img)
    files = [(f"{CFG.OUT_NAME}.xlsx", "Blank, ready for your own costs"),
             (f"…_CPM_Calculator_SAMPLE.xlsx", "A full sample owner-operator to explore"),
             (CFG.GUIDE_NAME, "9 pages: set-up, worked examples, FAQ")]
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
    for it in ["Instant download, no physical item shipped", "Estimates based on your inputs", "Not affiliated with any carrier, broker or load board"]:
        d.rectangle((1800, yy + 26, 1826, yy + 34), fill=BRASS)
        yy = para(img, (1856, yy), it, F(44, 500), PAPER, W - M - 1856 - 50, 1.25) + 40
    logo(img)
    save(img, "07_what_you_receive.png")


if __name__ == "__main__":
    BR.ensure_fonts()
    if OUT.exists():
        for f in OUT.glob("*.png"):
            f.unlink()
    for fn in (hero, included, check, compare, pnl, compat, receive):
        fn()
