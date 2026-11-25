"""Etsy shop banners for Brass Ledger.

  shop_banner_big.png   3360 x 840   Etsy "big banner". The Etsy app crops the sides, so the name and tagline sit in the
                                     central 2000 px (x 680..2680); real product screens fill the right and may be cut.
  shop_banner_mini.png  1200 x 160   Etsy "mini banner" (desktop only, used when no big banner is set).

Output: productivity-bundle/brand/ (not stored in git).  Usage: python shop_banner.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

import brand as BR
from brand_listing import BRASS, GREEN, PAPER, F, FH
from hero_thumb import BRASS_TINT, D, L, card, text_w, tracked

OUT = Path(__file__).resolve().parent.parent / "brand"
SAFE0, SAFE1 = 680, 2680


def crop(path, box):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    return im.crop(tuple(int(v * s) for v, s in zip(box, (w, h, w, h))))


def big():
    W, H = 3360, 840
    img = Image.new("RGB", (W, H), GREEN)
    d = ImageDraw.Draw(img)
    # a brass-tint slab behind the screens, on the right
    d.rectangle((2120, 0, W, H), fill=BR.rgb("2B4A42"))
    # real product screens: personal finance, planning and the trade calculators
    card(img, crop(L("04_Ultimate_Budget_Spreadsheet", "dashboard"), (0, 0.035, 0.62, 0.43)), 2780, 70, 560, 700)
    card(img, crop(D("lawn-care-pricing-calculator", "dash_top"), (0, 0, 0.62, 1)), 1980, 300, 600, 600)
    card(img, crop(D("cake-pricing-calculator", "cake1_price"), (0, 0, 0.6, 1)), 2340, 140, 600, 640)
    # name, rule, tagline and format line, inside the safe area
    x = SAFE0 + 60
    f = FH(176)
    tracked(d, (x, 110), "Brass Ledger", f, PAPER)
    BR.double_rule(d, x + 4, 350, text_w(d, "Brass Ledger", f), 150)
    d.multiline_text((x, 410), "Simple tools for\nsmall business numbers.", font=FH(74), fill=PAPER, spacing=10)
    BR.spaced(d, (x + 4, 635), "BUDGETS  ·  PLANNERS  ·  PRICING CALCULATORS", F(28, 700), BRASS, 0.2)
    d.text((x + 4, 692), "Excel and Google Sheets. Instant download.", font=F(34, 500), fill=BR.rgb("D6E0DC"))
    return img


def mini():
    W, H = 1200, 160
    img = Image.new("RGB", (W, H), GREEN)
    d = ImageDraw.Draw(img)
    f = FH(64)
    tracked(d, (48, 30), "Brass Ledger", f, PAPER)
    BR.double_rule(d, 50, 116, text_w(d, "Brass Ledger", f), 50)
    d.text((W - 48, 66), "Simple tools for small business numbers.", font=FH(34), fill=PAPER, anchor="rm")
    BR.spaced(d, (W - 48, 104), "EXCEL  ·  GOOGLE SHEETS", F(18, 700), BRASS, 0.22, anchor="r")
    return img


if __name__ == "__main__":
    BR.ensure_fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    big().save(OUT / "shop_banner_big.png", "PNG", optimize=True)
    mini().save(OUT / "shop_banner_mini.png", "PNG", optimize=True)
    print("wrote", OUT / "shop_banner_big.png", OUT / "shop_banner_mini.png")
