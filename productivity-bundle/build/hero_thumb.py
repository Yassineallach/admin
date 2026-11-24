"""Thumbnail-first hero image (listing photo 1) for the Brass Ledger catalogue.

Built for how buyers first see a listing: a small thumbnail in Etsy search (about 340 px wide on a laptop, 170 px on a
phone) and a squarer crop on the shop home page and in favourites. So:
  * the PRODUCT NAME is the headline, large and bold, with one short benefit line under it
  * one real screenshot, cropped to its most visual part, fills most of the frame
  * a solid Ledger-green panel behind the screenshot, so the image stands out on Etsy's white page
  * one badge row: "Excel + Google Sheets" (or the product's format) and one hook
  * everything that matters sits inside the centred square (x 337..2362), so any crop keeps it
  * each product's own name and screen make the six mini trackers easy to tell apart

Usage: python hero_thumb.py [key ...]     keys: see HEROES below (default: all)
Writes listings/<prod>/images/01_hero.png (the other six photos are unchanged).
"""
from __future__ import annotations

import sys

from PIL import Image, ImageDraw, ImageFilter

import brand as BR
import brand_listing as BL
from brand_listing import BRASS, GREEN, H, INK2, PAPER, W, WHITE, F, FH

SQ0, SQ1 = (W - H) // 2, (W + H) // 2          # centred square: x 337..2362
PANEL_Y = 860                                    # green panel starts here
BRASS_TINT = BR.rgb("F6EBD3")

HEROES = {
    "bg": dict(prod="04_Ultimate_Budget_Spreadsheet", title="Budget Spreadsheet",
               line="Know where your money went, and what is left.",
               badges=["Excel + Google Sheets", "28 tabs, any currency"],
               shot=("04_Ultimate_Budget_Spreadsheet", "dashboard", (0, 0.035, 1, 0.43))),
}


def tracked(d, xy, text, font, fill, track=-0.02):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + track * font.size
    return x


def text_w(d, text, font, track=-0.02):
    return sum(d.textlength(ch, font=font) + track * font.size for ch in text)


def pill(d, x, y, text, size, fill, color):
    f = F(size, 700)
    w = d.textlength(text, font=f)
    d.rounded_rectangle((x, y, x + w + 1.6 * size, y + 2 * size), size, fill=fill)
    d.text((x + 0.8 * size, y + size), text, font=f, fill=color, anchor="lm")
    return x + w + 1.6 * size


def card(img, sh, cx, top, max_w, max_h):
    """Screenshot on a white card with a soft shadow, centred on cx. Returns the card box."""
    pad = 18
    s = min((max_w - 2 * pad) / sh.width, (max_h - 2 * pad) / sh.height)
    w, h = int(sh.width * s), int(sh.height * s)
    x0, y0 = int(cx - (w + 2 * pad) / 2), top
    x1, y1 = x0 + w + 2 * pad, y0 + h + 2 * pad
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((x0 + 8, y0 + 26, x1 + 8, y1 + 26), 22, fill=(0, 0, 0, 90))
    layer = layer.filter(ImageFilter.GaussianBlur(34))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0, y0, x1, y1), 22, fill=WHITE)
    img.paste(sh.resize((w, h), Image.LANCZOS), (x0 + pad, y0 + pad))
    return x0, y0, x1, y1


def hero(key):
    h = HEROES[key]
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle((0, PANEL_Y, W, H), fill=GREEN)
    cx = W // 2
    ty = 40
    # product name: as large as fits inside the centred square
    size = 230
    while text_w(d, h["title"], FH(size)) > SQ1 - SQ0 + 160 and size > 120:
        size -= 6
    f = FH(size)
    tx = cx - text_w(d, h["title"], f) / 2
    tracked(d, (tx, ty + 120), h["title"], f, GREEN)
    yb = ty + 120 + size * 1.34                    # below the descenders (p, g, y)
    BR.double_rule(d, cx - 170, yb - 4, 340, size * 0.7)
    # benefit line
    lf = F(66, 500)
    d.text((cx, yb + 92), h["line"], font=lf, fill=INK2, anchor="mm")
    # badges, centred
    bs = 42
    widths = [d.textlength(b, font=F(bs, 700)) + 1.6 * bs for b in h["badges"]]
    gap = 28
    x = cx - (sum(widths) + gap * (len(widths) - 1)) / 2
    by = yb + 160
    for i, b in enumerate(h["badges"]):
        x = pill(d, x, by, b, bs, GREEN if i == 0 else BRASS_TINT, BRASS if i == 0 else GREEN) + gap
    # the screenshot, large, rising out of the green panel
    prod, name, crop = h["shot"]
    sh = BL.shot(prod, name, crop)
    top = int(by + 2 * bs + 60)
    card(img, sh, cx, top, 2380, H - top - 150)
    BR.wordmark(img, (BL.M, H - 104), 54, on_green=True)
    out = BL.ROOT / h["prod"] / "images"
    out.mkdir(parents=True, exist_ok=True)
    img.save(out / "01_hero.png", "PNG", optimize=True)
    return out / "01_hero.png"


if __name__ == "__main__":
    BR.ensure_fonts()
    for k in (sys.argv[1:] or list(HEROES)):
        print(hero(k))
