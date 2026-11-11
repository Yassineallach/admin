"""Brass Ledger brand: palette, fonts and logo drawing shared by spreadsheets, PDFs and listing images.

Brand rules (from the brand sheet):
  colours  Ledger green 1F3D36 · Brass D29A3A · Paper FAF7F2 · Ink 222222 · secondary 444444 · border E6E1D8 · positive 2E7D4F
  fonts    headings Fraunces 600 (optical size 144), body Inter; inside spreadsheets titles fall back to Georgia
  logo     wordmark "Brass Ledger" in Fraunces 600 with a brass double rule beneath, full width of the wordmark:
           thick rule 0.075em, gap 0.05em, thin rule 0.022em. Green on light, paper on green.
  voice    plain, direct, practical. Lead with the outcome. No hype words, no exclamation marks.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

NAME = "Brass Ledger"
TAGLINE = "Simple tools for small business numbers."
DESCRIPTOR = "SMALL BUSINESS TOOLS"

GREEN, BRASS, PAPER, INK, INK2, BORDER, WHITE, POSITIVE = "1F3D36", "D29A3A", "FAF7F2", "222222", "444444", "E6E1D8", "FFFFFF", "2E7D4F"
GREEN_2 = "2B5148"        # lighter green for secondary blocks
GREEN_TINT = "E7EDEA"     # pale green (positive / active backgrounds)
BRASS_DARK = "A87620"     # brass that stays readable as small text on paper
BRASS_TINT = "F6EBD3"     # pale brass (optional cells, highlights)
CALC = "F1ECE2"           # calculated cells: paper, one step darker
NEGATIVE, NEG_TINT = "B3382C", "F8E4E0"

FONT_DIR = Path(__file__).resolve().parent.parent / "brand" / "fonts"
FRAUNCES = FONT_DIR / "Fraunces-144-SemiBold.ttf"
INTER = {w: FONT_DIR / f"Inter-{w}.ttf" for w in (400, 500, 600, 700, 800)}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ensure_fonts():
    """Make the brand fonts visible to LibreOffice for test renders: Fraunces, plus Gelasio standing in for Georgia
    (Gelasio is metric-compatible with Georgia, which the Excel edition uses for titles)."""
    home = Path.home() / ".fonts"
    home.mkdir(exist_ok=True)
    changed = False
    for f in FONT_DIR.glob("*.ttf"):
        if f.name.startswith(("Fraunces", "Gelasio")) and not (home / f.name).exists():
            (home / f.name).write_bytes(f.read_bytes())
            changed = True
    conf = Path.home() / ".config" / "fontconfig" / "fonts.conf"
    if not conf.exists() or "Gelasio" not in conf.read_text():
        conf.parent.mkdir(parents=True, exist_ok=True)
        conf.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig>'
                        '<alias binding="same"><family>Georgia</family><prefer><family>Gelasio</family></prefer></alias>'
                        '</fontconfig>')
        changed = True
    if changed:
        subprocess.run(["fc-cache", "-f"], capture_output=True)


# ---------------------------------------------------------------- Pillow helpers
def pil_font(size, kind="inter", weight=400):
    from PIL import ImageFont
    return ImageFont.truetype(str(FRAUNCES if kind == "fraunces" else INTER[weight]), int(size))


def spaced(draw, xy, s, font, fill, spacing_em=0.25, anchor="l"):
    """Letter-spaced uppercase text (kickers, descriptor). Returns (x_end, width)."""
    gap = font.size * spacing_em
    widths = [draw.textlength(ch, font=font) for ch in s]
    total = sum(widths) + gap * (len(s) - 1)
    x, y = xy
    if anchor == "m":
        x -= total / 2
    elif anchor == "r":
        x -= total
    x0 = x
    for ch, w in zip(s, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += w + gap
    return x0 + total, total


def double_rule(draw, x0, y, width, em, color=None):
    """Brass double rule: thick 0.075em, gap 0.05em, thin 0.022em. Returns the y below it."""
    c = rgb(color or BRASS)
    t1, g, t2 = max(2, round(0.075 * em)), max(2, round(0.05 * em)), max(1, round(0.022 * em))
    draw.rectangle((x0, y, x0 + width, y + t1 - 1), fill=c)
    draw.rectangle((x0, y + t1 + g, x0 + width, y + t1 + g + t2 - 1), fill=c)
    return y + t1 + g + t2


def wordmark(img, xy, em, on_green=False, descriptor=False):
    """Draw the Brass Ledger wordmark with its double rule at top-left xy; em = font size in px. Returns (w, h)."""
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    f = pil_font(em, "fraunces")
    x, y = xy
    box = d.textbbox((x, y), NAME, font=f)
    # tighten tracking slightly (-0.02em) by drawing per glyph
    cx = x
    for ch in NAME:
        d.text((cx, y), ch, font=f, fill=rgb(PAPER if on_green else GREEN))
        cx += d.textlength(ch, font=f) - 0.02 * em
    w = cx - x
    yb = box[3] + round(0.06 * em)
    yb = double_rule(d, x, yb, w, em)
    if descriptor:
        fd = pil_font(em * 0.16, "inter", 700)
        _, tw = spaced(d, (x + w / 2, yb + em * 0.16), DESCRIPTOR, fd, rgb(PAPER if on_green else GREEN), 0.3, anchor="m")
        yb += em * 0.36
    return w, yb - y


def monogram(size=1000):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (size, size), rgb(GREEN))
    d = ImageDraw.Draw(img)
    em = size * 0.46
    f = pil_font(em, "fraunces")
    tw = d.textlength("BL", font=f)
    box = d.textbbox((0, 0), "BL", font=f)
    x = (size - tw) / 2
    y = size * 0.46 - (box[1] + box[3]) / 2
    d.text((x, y), "BL", font=f, fill=rgb(PAPER))
    double_rule(d, size * 0.24, y + box[3] + size * 0.09, size * 0.52, em * 0.85)
    return img
