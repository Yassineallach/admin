"""Thumbnail-first hero image (listing photo 1) for every Brass Ledger listing.

Built for how buyers first see a listing: a small thumbnail in Etsy search (about 340 px wide on a laptop, 170 px on a
phone) and a squarer crop on the shop home page and in favourites. So:
  * the PRODUCT NAME is the headline, large and bold, with one short benefit line under it
  * real screenshots, cropped to their most visual part (charts, tiles, grids), fill most of the frame
  * a solid colour panel behind the screenshot, so the image stands out on Etsy's white page
  * one badge row: the format and one hook
  * everything that matters sits inside the centred square (x 337..2362), so any crop keeps it

Three families keep the shop consistent without every thumbnail looking the same:
  finance      paper top, Ledger-green panel                  (budget + mini money trackers)
  planning     Ledger-green top, brass-tint panel             (project manager, planners, bundle)
  business     paper top, brass panel + a sample-result chip  (trade and seller calculators)

Every screenshot is a real render of the sample file; chips quote figures visible in that screenshot.

Usage: python hero_thumb.py [key ...]     (default: all)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import brand as BR
from brand_listing import BRASS, GREEN, H, INK2, PAPER, W, WHITE, F, FH

ADMIN = Path(__file__).resolve().parents[2]
LIST = ADMIN / "productivity-bundle" / "listings"
SQ0, SQ1 = (W - H) // 2, (W + H) // 2          # centred square: x 337..2362
BRASS_TINT = BR.rgb("F6EBD3")
XS = "Excel + Google Sheets"


def L(prod, name):
    return LIST / prod / "screens" / f"{name}.png"


def D(proj, name):
    return ADMIN / proj / "dist" / "screens" / f"{name}.png"


def out_orig(prod):
    return LIST / prod / "images" / "01_hero.png"


def out_new(proj):
    return ADMIN / proj / "dist" / proj / "listing-images" / "01_hero.png"


MINI = "05_Minis/"
HEROES = {
    # ------------------------------------------------------------- finance
    "bg": dict(fam="finance", out=out_orig("04_Ultimate_Budget_Spreadsheet"), title="Budget Spreadsheet",
               line="Know where your money went, and what is left.", badges=[XS, "28 tabs, any currency"],
               shots=[(L("04_Ultimate_Budget_Spreadsheet", "dashboard"), (0, 0.035, 1, 0.43))]),
    "debt": dict(fam="finance", out=out_orig(MINI + "Debt_Payoff_Calculator"), title="Debt Payoff Calculator",
                 line="Know the date you will be debt-free.", badges=[XS, "Snowball or avalanche"],
                 shots=[(L(MINI + "Debt_Payoff_Calculator", "main"), (0.015, 0.155, 0.705, 0.80))],
                 inset=(L(MINI + "Debt_Payoff_Calculator", "main"), (0.738, 0.31, 1.0, 0.79), 1150)),
    "funds": dict(fam="finance", out=out_orig(MINI + "Sinking_Funds_Tracker"), title="Sinking Funds Tracker",
                  line="Save for each goal and see if you are on track.", badges=[XS, "Up to 15 goals"],
                  shots=[(L(MINI + "Sinking_Funds_Tracker", "main"), (0, 0, 1, 1))]),
    "networth": dict(fam="finance", out=out_orig(MINI + "Net_Worth_Tracker"), title="Net Worth Tracker",
                     line="See what you own, what you owe and the difference.", badges=[XS, "24-month history"],
                     shots=[(L(MINI + "Net_Worth_Tracker", "history"), (0, 0, 1, 1))]),
    "nospend": dict(fam="finance", out=out_orig(MINI + "No_Spend_Challenge_Tracker"), title="No-Spend Challenge",
                    line="Count your no-spend days and what they saved.", badges=[XS, "Streaks and savings"],
                    shots=[(L(MINI + "No_Spend_Challenge_Tracker", "main"), (0, 0, 1, 1))]),
    "invest": dict(fam="finance", out=out_orig(MINI + "Investment_Growth_Calculator"), title="Investment Calculator",
                   line="See what regular investing could be worth.", badges=[XS, "3 return scenarios"],
                   shots=[(L(MINI + "Investment_Growth_Calculator", "main"), (0, 0, 1, 1))]),
    "habits": dict(fam="finance", out=out_orig(MINI + "Habit_Tracker"), title="Habit Tracker",
                   line="See which habits you keep, month by month.", badges=[XS, "12 habits, 12 months"],
                   shots=[(L(MINI + "Habit_Tracker", "main"), (0, 0, 1, 1))]),
    # ------------------------------------------------------------- planning
    "pm": dict(fam="planning", out=out_orig("01_Ultimate_Project_Manager"), title="Project Manager",
               line="Every project, task and deadline in one place.", badges=[XS, "Gantt, Kanban, dashboard"],
               shots=[(L("01_Ultimate_Project_Manager", "AllinOne_Dashboard"), (0, 0, 1, 0.42))]),
    "wp": dict(fam="planning", out=out_orig("03_Weekly_Planner_Pro"), title="Weekly Planner",
               line="Plan the week and see what got done.", badges=[XS, "Undated, reuse every year"],
               shots=[(L("03_Weekly_Planner_Pro", "week_top"), (0, 0, 1, 0.75))]),
    "planner": dict(fam="planning", out=out_orig("02_Ultimate_OneNote_Planner"), title="OneNote Digital Planner",
                    line="Your year, your weeks and your work notes in one place.", badges=["OneNote + PDF", "2027 and undated"],
                    shots=[(L("02_Ultimate_OneNote_Planner", "m1_cal"), (0, 0, 1, 0.85)),
                           (L("02_Ultimate_OneNote_Planner", "index"), (0, 0, 1, 0.85)),
                           (L("02_Ultimate_OneNote_Planner", "w1"), (0, 0, 1, 0.85))]),
    "bundle": dict(fam="planning", out=out_orig("06_Ultimate_Productivity_Bundle"), title="Productivity Bundle",
                   line="Your projects, your week and your money: three templates.", badges=[XS, "3 templates, one price"],
                   shots=[(L("03_Weekly_Planner_Pro", "week_top"), (0, 0, 1, 1)),
                          (L("01_Ultimate_Project_Manager", "AllinOne_Dashboard"), (0, 0, 1, 0.52)),
                          (L("04_Ultimate_Budget_Spreadsheet", "dashboard"), (0, 0.035, 1, 0.5))]),
    # ------------------------------------------------------------- business
    "whatnot": dict(fam="business", out=out_new("whatnot-profit-tracker"), title="Whatnot Profit Tracker",
                    line="See the real profit from every live show.", badges=[XS, "Fees, costs, giveaways"],
                    shots=[(D("whatnot-profit-tracker", "dash_top"), (0, 0, 1, 1))]),
    "daycare": dict(fam="business", out=out_new("home-daycare-tax-workbook"), title="Home Daycare Tax Workbook",
                    line="Your time-space percentage, calculated and documented.", badges=[XS, "For US providers"],
                    shots=[(D("home-daycare-tax-workbook", "dash_top"), (0, 0, 1, 1))]),
    "lawn": dict(fam="business", out=out_new("lawn-care-pricing-calculator"), title="Lawn Care Pricing",
                 line="Price every lawn for profit in two minutes.", badges=[XS, "Quotes, routes, season"],
                 shots=[(D("lawn-care-pricing-calculator", "dash_top"), (0, 0, 1, 1))]),
    "pressure": dict(fam="business", out=out_new("pressure-washing-bid-calculator"), title="Pressure Washing Bids",
                     line="Quote any job in two minutes, without underpricing.", badges=[XS, "Up to 10 services a job"],
                     shots=[(D("pressure-washing-bid-calculator", "quote_top"), (0, 0, 0.88, 1))]),
    "cake": dict(fam="business", out=out_new("cake-pricing-calculator"), title="Cake Pricing Calculator",
                 line="Know what every cake really costs.", badges=[XS, "US + metric units"],
                 shots=[(D("cake-pricing-calculator", "cake1_price"), (0, 0, 0.6, 1))]),
}
CHIPS = {          # key -> (small label, big figure); each figure is visible in that product's screenshot
    "debt": ("DEBT-FREE (SAMPLE)", "Apr 2030"),
    "whatnot": ("PROFIT PER LIVE HOUR", "$139.94"),
    "daycare": ("TIME-SPACE PERCENTAGE", "35.48%"),
    "lawn": ("YOUR BREAK-EVEN RATE", "$32.14 / hour"),
    "pressure": ("SAMPLE 4-SERVICE JOB", "$531 quote"),
    "cake": ("SAMPLE WEDDING CAKE", "$11.35 / serving", "bottom"),
}

FAMILY = {  # top background, panel, title colour, line colour, first badge (fill, text), second badge (fill, text), logo on green
    "finance": dict(top=PAPER, panel=GREEN, title=GREEN, line=INK2, b1=(GREEN, BRASS), b2=(BRASS_TINT, GREEN), logo_green=True),
    "planning": dict(top=GREEN, panel=BRASS_TINT, title=PAPER, line=(214, 224, 220), b1=(BRASS, GREEN), b2=(PAPER, GREEN), logo_green=False),
    "business": dict(top=PAPER, panel=BRASS, title=GREEN, line=INK2, b1=(GREEN, BRASS), b2=(BRASS_TINT, GREEN), logo_green=False),
}
PANEL_Y = 860


def load(path, crop):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    l, t, r, b = crop
    return im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))


def text_w(d, text, font, track=-0.02):
    return sum(d.textlength(ch, font=font) + track * font.size for ch in text)


def tracked(d, xy, text, font, fill, track=-0.02):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + track * font.size


def pill(d, x, y, text, size, fill, color):
    f = F(size, 700)
    w = d.textlength(text, font=f)
    d.rounded_rectangle((x, y, x + w + 1.6 * size, y + 2 * size), size, fill=fill)
    d.text((x + 0.8 * size, y + size), text, font=f, fill=color, anchor="lm")
    return x + w + 1.6 * size


def shadow(img, box, radius=22, alpha=90, blur=34, dy=26):
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((x0 + 8, y0 + dy, x1 + 8, y1 + dy), radius, fill=(0, 0, 0, alpha))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(blur))).convert("RGB"))


def card(img, sh, x0, y0, w, h):
    """Screenshot scaled to fit w x h (keeps aspect), on a white card at x0, y0. Returns the card box."""
    pad = 18
    s = min((w - 2 * pad) / sh.width, (h - 2 * pad) / sh.height)
    sw, shh = int(sh.width * s), int(sh.height * s)
    box = (x0, y0, x0 + sw + 2 * pad, y0 + shh + 2 * pad)
    shadow(img, box)
    ImageDraw.Draw(img).rounded_rectangle(box, 22, fill=WHITE)
    img.paste(sh.resize((sw, shh), Image.LANCZOS), (x0 + pad, y0 + pad))
    return box


def card_centred(img, sh, cx, top, max_w, max_h):
    pad = 18
    s = min((max_w - 2 * pad) / sh.width, (max_h - 2 * pad) / sh.height)
    w = int(sh.width * s) + 2 * pad
    return card(img, sh, int(cx - w / 2), top, max_w, max_h)


def hero(key):
    h = HEROES[key]
    fam = FAMILY[h["fam"]]
    img = Image.new("RGB", (W, H), fam["top"])
    d = ImageDraw.Draw(img)
    d.rectangle((0, PANEL_Y, W, H), fill=fam["panel"])
    cx = W // 2
    # product name, as large as fits in the centred square (+ a little)
    size = 230
    while text_w(d, h["title"], FH(size)) > SQ1 - SQ0 - 60 and size > 120:
        size -= 6
    f = FH(size)
    ty = 40 + (230 - size) * 0.45
    tracked(d, (cx - text_w(d, h["title"], f) / 2, ty), h["title"], f, fam["title"])
    yb = ty + size * 1.34
    BR.double_rule(d, cx - 170, yb - 4, 340, min(size, 200) * 0.7)
    d.text((cx, 40 + 230 * 1.34 + 92), h["line"], font=F(66 if len(h["line"]) < 50 else 60, 500), fill=fam["line"], anchor="mm")
    bs, gap = 42, 28
    widths = [d.textlength(b, font=F(bs, 700)) + 1.6 * bs for b in h["badges"]]
    x = cx - (sum(widths) + gap * (len(widths) - 1)) / 2
    by = 40 + 230 * 1.34 + 160
    for i, b in enumerate(h["badges"]):
        fill, col = fam["b1"] if i == 0 else fam["b2"]
        x = pill(d, x, by, b, bs, fill, col) + gap
    top = int(by + 2 * bs + 60)
    shots = [load(p, c) for p, c in h["shots"]]
    bottom = H - 150
    if len(shots) == 1:
        box = card_centred(img, shots[0], cx, top, 2380, bottom - top)
    else:                                  # three cards fanned: sides behind, the middle one in front
        cw, ch = 1250, bottom - top
        card(img, shots[0], 110, top + 90, cw, ch - 90)
        card(img, shots[2], W - 110 - cw, top + 90, cw, ch - 90)
        box = card_centred(img, shots[1], cx, top - 10, 1700, ch + 60)
    if h.get("inset"):                     # a second real screen, overlapping the lower right of the main card
        ip, ic, iw = h["inset"]
        ish = load(ip, ic)
        ih = min(int(iw * ish.height / ish.width) + 36, bottom - box[1] - 120)
        ix1 = min(box[2] + 60, W - 70)
        card(img, ish, ix1 - iw, bottom - ih + 40, iw, ih)
    if key in CHIPS:                       # sample result, big enough to read on a phone
        lab, fig, *pos = CHIPS[key]
        fl, ff = F(34, 700), F(76, 800)
        wch = max(d.textlength(fig, font=ff), d.textlength(lab, font=fl) + 0.2 * 34 * len(lab)) + 110
        x1 = min(box[2] + 40, SQ1 - 20)
        cy = box[3] - 150 if pos == ["bottom"] else box[1] - 70
        cbox = (x1 - wch, cy, x1, cy + 220)
        shadow(img, cbox, 26, 110, 24, 16)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle(cbox, 26, fill=GREEN)
        BR.spaced(d, (cbox[0] + 55, cbox[1] + 50), lab, fl, BRASS, 0.2)
        d.text((cbox[0] + 55, cbox[1] + 150), fig, font=ff, fill=PAPER, anchor="ls")
    BR.wordmark(img, (150, H - 104), 54, on_green=fam["logo_green"])
    h["out"].parent.mkdir(parents=True, exist_ok=True)
    img.save(h["out"], "PNG", optimize=True)
    return h["out"]


if __name__ == "__main__":
    BR.ensure_fonts()
    for k in (sys.argv[1:] or list(HEROES)):
        print(hero(k))
