"""Brass Ledger listing images: one layout system for every listing.

Canvas 2700 x 2025 (4:3). Paper background, brass kicker, large green Fraunces headline, short brass double rule
under it, logo bottom-left. Seven images per listing, always in this order:
  1 hero with the product on screen   2 what's included   3 main tool close-up   4 dashboard / summary
  5 how it works in 3 steps           6 compatibility     7 what you receive
Only real screenshots of the finished product are used (taken by each product's shoot function).

A listing is described by a spec dict (see LISTINGS in brand_listings_content.py) and built with make(spec).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import brand as BR

W, H = 2700, 2025
M = 150                                   # outer margin
GREEN, BRASS, PAPER, INK, INK2, BORDER = (BR.rgb(x) for x in (BR.GREEN, BR.BRASS, BR.PAPER, BR.INK, BR.INK2, BR.BORDER))
WHITE = (255, 255, 255)
ROOT = Path(__file__).resolve().parent.parent / "listings"


def F(size, weight=400):
    return BR.pil_font(size, "inter", weight)


def FH(size):
    return BR.pil_font(size, "fraunces")


def canvas():
    return Image.new("RGB", (W, H), PAPER)


def wrap(d, s, font, max_w):
    lines = []
    for para in s.split("\n"):
        cur = ""
        for word in para.split():
            t = (cur + " " + word).strip()
            if d.textlength(t, font=font) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def para(img, xy, s, font, fill, max_w, leading=1.3):
    d = ImageDraw.Draw(img)
    x, y = xy
    for ln in wrap(d, s, font, max_w):
        d.text((x, y), ln, font=font, fill=fill)
        y += font.size * leading
    return y


def head(img, kicker, headline, x=M, y=M, max_w=W - 2 * M, size=124, ksize=34):
    """Brass kicker, green Fraunces headline (tracking -0.02em), short brass double rule. Returns y below the rule."""
    d = ImageDraw.Draw(img)
    BR.spaced(d, (x, y), kicker.upper(), F(ksize, 700), BRASS, 0.25)
    y += int(ksize * 2.35)
    f = FH(size)
    lines = wrap(d, headline, f, max_w)
    while len(lines) > 3 and size > 80:
        size -= 8
        f = FH(size)
        lines = wrap(d, headline, f, max_w)
    for ln in lines:
        cx = x
        for ch in ln:
            d.text((cx, y), ch, font=f, fill=GREEN)
            cx += d.textlength(ch, font=f) - 0.02 * size
        y += size * 1.06
    y += 22
    return int(BR.double_rule(d, x, y, 250, size))


def logo(img, on_green=False):
    BR.wordmark(img, (M, H - M - 92), 76, on_green=on_green)


def shot(prod, name, crop=None):
    im = Image.open(ROOT / prod / "screens" / f"{name}.png").convert("RGB")
    if crop:
        w, h = im.size
        l, t, r, b = crop
        im = im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
    return im


def frame(img, sh, box, align="tl"):
    """Screenshot on a white card with a border and a soft shadow, fitted inside box. Returns the card's box."""
    x0, y0, x1, y1 = (int(v) for v in box)
    pad = 14
    s = min((x1 - x0 - 2 * pad) / sh.width, (y1 - y0 - 2 * pad) / sh.height)
    w, h = int(sh.width * s), int(sh.height * s)
    cw, ch = w + 2 * pad, h + 2 * pad
    cx = x0 if "l" in align else (x1 - cw if "r" in align else x0 + (x1 - x0 - cw) // 2)
    cy = y0 if "t" in align else y0 + (y1 - y0 - ch) // 2
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((cx + 6, cy + 18, cx + cw + 6, cy + ch + 18), 14, fill=(31, 61, 54, 46))
    layer = layer.filter(ImageFilter.GaussianBlur(26))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((cx, cy, cx + cw, cy + ch), 14, fill=WHITE, outline=BORDER, width=3)
    img.paste(sh.resize((w, h), Image.LANCZOS), (cx + pad, cy + pad))
    return cx, cy, cx + cw, cy + ch


def laptop(img, sh, box):
    """Simple laptop: dark bezel, screen showing the top of the screenshot, base. Fitted to box width."""
    x0, y0, x1, y1 = box
    bw = x1 - x0
    sw = int(bw / 1.1)
    bez = int(sw * 0.028)
    sh_h = min(int(sw * 0.64), y1 - y0 - 2 * bez - 60)
    cx = (x0 + x1) // 2
    sx0, sy0 = cx - sw // 2, y0 + bez
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((sx0 - bez, y0 + 40, sx0 + sw + bez, sy0 + sh_h + bez + 60), 40, fill=(31, 61, 54, 70))
    layer = layer.filter(ImageFilter.GaussianBlur(40))
    img.paste(Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB"))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((sx0 - bez, y0, sx0 + sw + bez, sy0 + sh_h + bez), 34, fill=(34, 34, 34))
    if sh.width / sh.height > sw / sh_h:                 # wider than the screen: fit the height, show the left part
        s = sh.resize((int(sh.width * sh_h / sh.height), sh_h), Image.LANCZOS).crop((0, 0, sw, sh_h))
    else:
        s = sh.resize((sw, int(sh.height * sw / sh.width)), Image.LANCZOS).crop((0, 0, sw, sh_h))
    img.paste(s, (sx0, sy0))
    d.rounded_rectangle((x0, sy0 + sh_h + bez - 4, x1, sy0 + sh_h + bez + 34), 16, fill=(200, 196, 188))
    d.rounded_rectangle((cx - 150, sy0 + sh_h + bez - 4, cx + 150, sy0 + sh_h + bez + 10), 8, fill=(170, 166, 158))


def points(img, items, x, y, max_w, title_size=46, body_size=36, gap=46):
    """Numbered points: brass number, green title, ink body."""
    d = ImageDraw.Draw(img)
    for i, it in enumerate(items, 1):
        title, body = (it, "") if isinstance(it, str) else it
        d.text((x, y - 4), f"{i:02d}", font=F(34, 700), fill=BRASS)
        y = para(img, (x + 90, y - 8), title, F(title_size, 700), GREEN, max_w - 90, 1.2)
        if body:
            y = para(img, (x + 90, y + 6), body, F(body_size, 400), INK2, max_w - 90, 1.35)
        y += gap
    return y


def checks(img, items, x, y, max_w, size=44, gap=30, color=None):
    d = ImageDraw.Draw(img)
    for it in items:
        d.rectangle((x, y + size * 0.42, x + 26, y + size * 0.42 + 8), fill=BRASS)
        y = para(img, (x + 56, y), it, F(size, 500), color or INK, max_w - 56, 1.25) + gap
    return y


def save(img, prod, name):
    out = ROOT / prod / "images"
    out.mkdir(parents=True, exist_ok=True)
    img.save(out / name, "PNG", optimize=True)


# ---------------------------------------------------------------- the seven images
def img_hero(sp):
    img = canvas()
    h = sp["hero"]
    y = head(img, h["kicker"], h["headline"], max_w=1120, size=132)
    y = para(img, (M, y + 56), h["sub"], F(50, 400), INK2, 1020, 1.36)
    checks(img, h["facts"], M, y + 60, 1020, size=48, gap=26, color=GREEN)
    if sp.get("hero_shots"):                       # overlapping framed screenshots (planner, bundle)
        boxes = [(1560, 200, 2600, 960), (1250, 640, 2290, 1400), (1620, 1090, 2600, 1840)][:len(sp["hero_shots"])]
        for (prod, name, crop), box in zip(sp["hero_shots"], boxes):
            frame(img, shot(prod, name, crop), box, "tl")
    else:
        laptop(img, shot(sp["prod"], *sp["hero_shot"]), (1235, 500, 2640, 1640))
    logo(img)
    save(img, sp["prod"], "01_hero.png")


def img_included(sp):
    img = canvas()
    inc = sp["included"]
    y = head(img, "What's included", inc["headline"]) + 70
    cols = inc["columns"]
    cw = (W - 2 * M - 60 * (len(cols) - 1)) // len(cols)
    d = ImageDraw.Draw(img)
    bottom = H - M - 190
    for size in (50, 46, 42, 38, 34):                # largest type that fits the tallest column
        gap = int(size * 0.62)
        hmax = max(sum(len(wrap(d, it, F(size, 500), cw - 96)) * size * 1.25 + gap for it in items) for _t, items in cols)
        if y + 140 + hmax + 30 <= bottom:
            break
    card_b = int(min(bottom, y + 140 + hmax + 40))
    for i, (title, items) in enumerate(cols):
        x = M + i * (cw + 60)
        d.rounded_rectangle((x, y, x + cw, card_b), 18, fill=WHITE, outline=BORDER, width=3)
        d.rectangle((x, y, x + cw, y + 12), fill=GREEN)
        BR.spaced(d, (x + 48, y + 58), title.upper(), F(28, 700), BRASS, 0.2)
        yy = y + 140
        for it in items:
            yy = para(img, (x + 48, yy), it, F(size, 500), INK, cw - 96, 1.25) + gap
    logo(img)
    save(img, sp["prod"], "02_whats_included.png")


def img_shot(sp, key, fname):
    img = canvas()
    s = sp[key]
    y = head(img, s["kicker"], s["headline"]) + 60
    sh = shot(s.get("prod", sp["prod"]), s["shot"], s.get("crop"))
    wide = sh.width / sh.height > 2.1
    if wide:                                           # wide screenshot: full width, points in a row beneath
        box = frame(img, sh, (M, y, W - M, y + 900), "tl")
        n = len(s["points"])
        cw = (W - 2 * M - 60 * (n - 1)) // n
        for i, it in enumerate(s["points"]):
            points(img, [it], M + i * (cw + 60), box[3] + 80, cw, 40, 32)
            d = ImageDraw.Draw(img)
            d.rectangle((M + i * (cw + 60), box[3] + 66, M + i * (cw + 60) + 60, box[3] + 300), fill=PAPER)
            d.text((M + i * (cw + 60), box[3] + 76), f"{i + 1:02d}", font=F(34, 700), fill=BRASS)
    else:
        box = frame(img, sh, (M, y, 1720, H - M - 190), "tl")
        px = box[2] + 90
        points(img, s["points"], px, y + 20, min(W - M - px, 940), 50 if px < 1700 else 46, 40 if px < 1700 else 36)
    logo(img)
    save(img, sp["prod"], fname)


def img_steps(sp):
    img = canvas()
    y = head(img, "How it works", sp["steps"]["headline"]) + 90
    d = ImageDraw.Draw(img)
    cw = (W - 2 * M - 2 * 70) // 3
    for i, (title, body) in enumerate(sp["steps"]["steps"]):
        x = M + i * (cw + 70)
        d.rounded_rectangle((x, y, x + cw, H - M - 230), 18, fill=GREEN)
        d.text((x + 64, y + 50), str(i + 1), font=FH(250), fill=BRASS)
        BR.double_rule(d, x + 64, y + 380, 160, 110)
        tf = FH(84) if body else FH(72)
        yy = para(img, (x + 64, y + 460), title, tf, PAPER, cw - 128, 1.12)
        para(img, (x + 64, yy + 34), body, F(46, 400), (220, 226, 222), cw - 128, 1.4)
    logo(img)
    save(img, sp["prod"], "05_how_it_works.png")


def img_compat(sp):
    img = canvas()
    c = sp["compat"]
    y = head(img, "Compatibility", c["headline"]) + 80
    d = ImageDraw.Draw(img)
    rows = c["rows"]
    rh = min(270, (H - M - 230 - y) // len(rows))
    d.rounded_rectangle((M, y, W - M, y + rh * len(rows)), 18, fill=WHITE, outline=BORDER, width=3)
    for i, (ok, name, note) in enumerate(rows):
        ry = y + i * rh
        if i:
            d.line((M + 50, ry, W - M - 50, ry), fill=BORDER, width=3)
        colr = BR.rgb(BR.POSITIVE) if ok else BR.rgb(BR.NEGATIVE)
        d.text((M + 64, ry + rh / 2), "Yes" if ok else "No", font=F(42, 700), fill=colr, anchor="lm")
        d.text((M + 240, ry + rh / 2), name, font=F(50, 700), fill=GREEN, anchor="lm")
        nf = F(40, 400)
        nl = wrap(d, note, nf, W - 2 * M - 1290)
        para(img, (M + 1230, ry + rh / 2 - len(nl) * 52 / 2 - 4), note, nf, INK2, W - 2 * M - 1290, 1.3)
    logo(img)
    save(img, sp["prod"], "06_compatibility.png")


def img_receive(sp):
    img = canvas()
    r = sp["receive"]
    y = head(img, "What you receive", r["headline"], max_w=1500) + 80
    d = ImageDraw.Draw(img)
    for i, (name, note) in enumerate(r["files"]):
        ry = y + i * 165
        d.rounded_rectangle((M, ry, 1560, ry + 136), 14, fill=WHITE, outline=BORDER, width=3)
        d.rectangle((M, ry, M + 14, ry + 136), fill=BRASS)
        d.text((M + 60, ry + 68), name, font=F(44, 700), fill=GREEN, anchor="lm")
        d.text((1510, ry + 68), note, font=F(36, 400), fill=INK2, anchor="rm")
    # green block on the right with the practical facts
    d.rounded_rectangle((1680, y, W - M, y + 971), 18, fill=GREEN)
    BR.spaced(d, (1740, y + 60), "GOOD TO KNOW", F(28, 700), BRASS, 0.2)
    yy = y + 140
    for it in r["notes"]:
        d.rectangle((1740, yy + 24, 1766, yy + 32), fill=BRASS)
        yy = para(img, (1796, yy), it, F(42, 500), PAPER, W - M - 1796 - 50, 1.3) + 36
    logo(img)
    save(img, sp["prod"], "07_what_you_receive.png")


def make(sp):
    out = ROOT / sp["prod"] / "images"
    if out.exists():
        for f in out.glob("*.png"):
            f.unlink()
    img_hero(sp)
    img_included(sp)
    img_shot(sp, "main", "03_main_tool.png")
    img_shot(sp, "summary", "04_summary.png")
    img_steps(sp)
    img_compat(sp)
    img_receive(sp)
    return sorted(p.name for p in out.glob("*.png"))


ALT = ["{name}: {hero}", "What's included in {name}", "{main}", "{summary}", "How {name} works in three steps",
       "Which apps {name} works with", "The files you receive with {name}"]


def photos_table(sp):
    """Markdown table of the seven images with alt text, for LISTING.md."""
    files = ["01_hero.png", "02_whats_included.png", "03_main_tool.png", "04_summary.png", "05_how_it_works.png",
             "06_compatibility.png", "07_what_you_receive.png"]
    vals = dict(name=sp["name"], hero=sp["hero"]["headline"].rstrip("."), main=sp["main"]["headline"].rstrip("."),
                summary=sp["summary"]["headline"].rstrip("."))
    rows = "\n".join(f"| {i + 1} | {f} | {a.format(**vals)} |" for i, (f, a) in enumerate(zip(files, ALT)))
    return ("## Photos (upload in this order)\n\nFiles are in `images/`, 2700 × 2025 px (4:3), in the Brass Ledger layout. "
            "Every screenshot is a real render of the finished product.\n\n| # | File | Alt text |\n|---|---|---|\n" + rows + "\n")
