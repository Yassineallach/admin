#!/usr/bin/env python3
"""Generates Lexigo's illustration set as SVG.

Style rules (see docs/DESIGN.md):
  * built only from rounded rectangles, circles and rounded triangles
  * flat fills, no outlines, no gradients
  * one lighter highlight shape and one darker shade shape per form
  * light source top-left

Run:  python3 tools/art/make_art.py   (writes into assets/art/)
"""
import math
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "art")

# Palette (mirrors scripts/ui/ui.gd)
LEAF = "#58CC02"; LEAF_DARK = "#46A302"; LEAF_LIGHT = "#89E219"; LEAF_PALE = "#D7FFB8"
SKY = "#1CB0F6"; SKY_DARK = "#1899D6"; SKY_PALE = "#DDF4FF"
SUN = "#FFC800"; SUN_DARK = "#E5A500"
FLAME = "#FF9600"; FLAME_DARK = "#E08600"
BERRY = "#FF4B4B"; BERRY_DARK = "#EA2B2B"
GRAPE = "#CE82FF"; GRAPE_DARK = "#A560E8"
NAVY = "#2B70C9"
INK = "#4B4B4B"; STONE = "#777777"; MIST = "#AFAFAF"; CLOUD = "#E5E5E5"; SNOW = "#F7F7F7"; WHITE = "#FFFFFF"
BLUSH = "#FF9EB5"


def svg(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n{body}\n</svg>\n'


def rect(x, y, w, h, r, fill, extra=""):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r:.1f}" fill="{fill}" {extra}/>'


def circle(cx, cy, r, fill, extra=""):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" {extra}/>'


def ellipse(cx, cy, rx, ry, fill, extra=""):
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" {extra}/>'


def line(points, width, color, extra=""):
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in points)
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'


def path(d, fill, extra=""):
    return f'<path d="{d}" fill="{fill}" {extra}/>'


def tri(cx, cy, size, fill, rot=0.0, round_=0.18):
    """Rounded triangle: a triangle path with quadratic-rounded corners."""
    pts = []
    for i in range(3):
        a = math.radians(rot - 90 + i * 120)
        pts.append((cx + size * math.cos(a), cy + size * math.sin(a)))
    d = ""
    for i in range(3):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % 3]
        a = (p1[0] + (p0[0] - p1[0]) * round_, p1[1] + (p0[1] - p1[1]) * round_)
        b = (p1[0] + (p2[0] - p1[0]) * round_, p1[1] + (p2[1] - p1[1]) * round_)
        d += ("M" if i == 0 else "L") + f"{a[0]:.1f} {a[1]:.1f} Q{p1[0]:.1f} {p1[1]:.1f} {b[0]:.1f} {b[1]:.1f} "
    return path(d + "Z", fill)


def letter_A(x, y, s, color, w):
    return (line([(x, y + s), (x + s * 0.5, y), (x + s, y + s)], w, color)
            + line([(x + s * 0.22, y + s * 0.62), (x + s * 0.78, y + s * 0.62)], w, color))


def tile(x, y, s, glyph_fn, face=WHITE, lip=CLOUD):
    r = s * 0.22
    return rect(x, y + s * 0.08, s, s, r, lip) + rect(x, y, s, s, r, face) + glyph_fn(x + s * 0.24, y + s * 0.2, s * 0.52)


# --------------------------------------------------------------------------
# Mascot: Lexi the chameleon. Changes colour like you change language.
# --------------------------------------------------------------------------

def lexi(pose="happy", body=LEAF, dark=LEAF_DARK, light=LEAF_LIGHT):
    p = []
    p.append(ellipse(128, 236, 78, 10, "#000", 'opacity="0.08"'))
    # tail: a ring made of two circles
    p.append(rect(48, 168, 60, 34, 17, body))
    p.append(circle(52, 160, 34, body))
    p.append(circle(52, 160, 15, dark))
    p.append(circle(46, 154, 6, light, 'opacity="0.9"'))
    # body
    p.append(rect(70, 128, 128, 96, 48, body))
    p.append(rect(78, 196, 112, 28, 14, dark))          # shade
    p.append(rect(96, 168, 92, 46, 23, light))          # belly
    p.append(rect(86, 140, 34, 14, 7, WHITE, 'opacity="0.35"'))  # highlight
    # casque: the chameleon's rounded crest
    p.append(tri(148, 66, 30, dark, rot=-35, round_=0.3))
    # feet
    p.append(rect(92, 212, 34, 20, 10, dark))
    p.append(rect(150, 212, 34, 20, 10, dark))
    # head
    p.append(circle(176, 104, 54, body))
    p.append(rect(150, 136, 70, 22, 11, dark, 'opacity="0.55"'))  # jaw shade
    p.append(rect(146, 64, 30, 12, 6, WHITE, 'opacity="0.35"'))   # highlight
    p.append(circle(212, 126, 8, BLUSH, 'opacity="0.8"'))          # cheek

    # eye turret
    look = {"happy": (3, 0), "cheer": (2, -2), "think": (2, -7), "oops": (0, 0), "wave": (4, 1)}[pose]
    p.append(circle(186, 92, 30, light))
    p.append(circle(184, 88, 25, dark, 'opacity="0.25"'))
    if pose == "oops":
        p.append(line([(172, 92), (186, 84), (200, 92)], 7, INK))
    elif pose == "cheer":
        p.append(line([(172, 94), (186, 82), (200, 94)], 7, INK))
    else:
        p.append(circle(188, 90, 20, WHITE))
        p.append(circle(188 + look[0], 90 + look[1], 10, INK))
        p.append(circle(184 + look[0], 86 + look[1], 3.5, WHITE))

    # mouth
    if pose == "oops":
        p.append(line([(196, 140), (204, 136), (212, 140), (220, 136)], 5, INK))
        p.append(path("M226 70 Q236 84 226 92 Q216 84 226 70 Z", SKY))   # sweat drop
    elif pose == "think":
        p.append(line([(200, 140), (216, 138)], 5, INK))
    else:
        p.append(path("M194 132 Q208 150 224 132 Z", INK))
        p.append(path("M202 138 Q209 144 216 138 Z", BERRY))

    # arms + props: short limbs from the chest, hands as circles
    def arm(x, y, length, angle):
        a = math.radians(angle)
        ex, ey = x + length * math.cos(a), y + length * math.sin(a)
        return line([(x, y), (ex, ey)], 16, dark) + circle(ex, ey, 10, dark)

    if pose == "happy":
        p.append(tile(178, 148, 50, lambda x, y, s: letter_A(x, y, s, LEAF, 7)))
        p.append(arm(150, 186, 30, -15))
    elif pose == "wave":
        p.append(arm(158, 178, 44, -60))
    elif pose == "cheer":
        p.append(arm(116, 158, 46, -125))
        p.append(arm(166, 170, 50, -40))
        for (cx, cy, sz, c) in [(30, 64, 14, SUN), (232, 34, 12, SKY), (118, 40, 9, BERRY), (60, 104, 8, GRAPE)]:
            p.append(tri(cx, cy, sz, c, rot=15))
    elif pose == "think":
        p.append(arm(156, 184, 34, -70))
        p.append(rect(196, 18, 52, 40, 20, WHITE, f'stroke="{CLOUD}" stroke-width="2"'))
        p.append(circle(196, 66, 7, WHITE))
        p.append(circle(186, 80, 4, WHITE))
        p.append(path("M213 31 Q222 23 230 31 Q232 38 222 41 L222 45", "none", f'stroke="{SKY}" stroke-width="5" stroke-linecap="round"'))
        p.append(circle(222, 51, 3.2, SKY))
    elif pose == "oops":
        p.append(arm(150, 186, 28, 20))
    return svg(256, 256, "\n".join(p))


# --------------------------------------------------------------------------
# World badges (160x160), each from a handful of rounded shapes
# --------------------------------------------------------------------------

def badge(bg, inner):
    return svg(160, 160, rect(8, 14, 144, 144, 40, "#000", 'opacity="0.12"') + rect(8, 6, 144, 144, 40, bg)
               + rect(22, 16, 46, 12, 6, WHITE, 'opacity="0.3"') + inner)


def world_basics():
    s = rect(26, 40, 74, 54, 18, WHITE) + tri(46, 100, 12, WHITE, rot=180)
    s += circle(46, 67, 6, "#7C5CFF") + circle(63, 67, 6, "#7C5CFF") + circle(80, 67, 6, "#7C5CFF")
    s += rect(66, 78, 70, 52, 18, SUN) + tri(118, 134, 11, SUN, rot=180)
    s += letter_A(88, 92, 26, WHITE, 6)
    return badge("#7C5CFF", s)


def world_food():
    s = circle(68, 92, 34, BERRY) + circle(92, 92, 34, BERRY) + rect(54, 104, 54, 30, 15, BERRY_DARK, 'opacity="0.5"')
    s += rect(76, 40, 8, 22, 4, "#8B5A2B") + path("M84 52 Q104 34 116 50 Q100 62 84 52 Z", LEAF)
    s += rect(58, 70, 14, 10, 5, WHITE, 'opacity="0.5"')
    s += rect(98, 104, 44, 30, 12, "#F4C27A") + rect(98, 124, 44, 10, 5, "#D9A35B") + circle(110, 112, 3, WHITE, 'opacity="0.6"')
    return badge("#FF6B6B", s)


def world_animals():
    s = circle(80, 84, 46, "#F08C1A")                        # mane
    for a in range(0, 360, 45):
        x = 80 + 44 * math.cos(math.radians(a)); y = 84 + 44 * math.sin(math.radians(a))
        s += circle(x, y, 14, "#F08C1A")
    s += circle(80, 86, 32, SUN) + circle(58, 58, 9, SUN) + circle(102, 58, 9, SUN)
    s += circle(68, 80, 5, INK) + circle(92, 80, 5, INK) + circle(66, 78, 1.8, WHITE) + circle(90, 78, 1.8, WHITE)
    s += rect(72, 90, 16, 10, 5, "#8B5A2B") + path("M72 104 Q80 112 88 104", "none", f'stroke="{INK}" stroke-width="4" stroke-linecap="round"')
    s += rect(60, 64, 14, 6, 3, WHITE, 'opacity="0.5"')
    return badge("#FFA62B", s)


def world_home():
    s = tri(80, 62, 50, BERRY, round_=0.15)
    s += rect(44, 70, 72, 64, 12, WHITE) + rect(44, 120, 72, 14, 7, CLOUD)
    s += rect(70, 96, 22, 38, 8, "#8B5A2B") + circle(87, 116, 3, SUN)
    s += rect(52, 82, 14, 14, 4, SKY) + rect(96, 82, 14, 14, 4, SKY)
    s += rect(98, 42, 12, 24, 4, STONE)
    return badge("#2EC4B6", s)


def world_travel():
    s = rect(22, 104, 58, 26, 13, WHITE) + circle(44, 104, 17, WHITE) + circle(62, 108, 12, WHITE)
    s += tri(78, 92, 26, CLOUD, rot=180, round_=0.25)                 # lower wing
    s += tri(48, 62, 18, BERRY, rot=0, round_=0.25)                   # tail fin
    s += rect(36, 62, 96, 26, 13, WHITE)                              # fuselage
    s += tri(84, 60, 24, WHITE, rot=0, round_=0.25)                   # upper wing
    s += circle(76, 75, 4.5, SKY_DARK) + circle(90, 75, 4.5, SKY_DARK) + circle(104, 75, 4.5, SKY_DARK)
    s += rect(114, 66, 12, 12, 6, SKY_DARK)                           # cockpit
    s += rect(42, 66, 20, 5, 2.5, SNOW)
    return badge(SKY, s)


def world_body():
    s = circle(64, 70, 26, BERRY) + circle(96, 70, 26, BERRY) + tri(80, 92, 40, BERRY, rot=180, round_=0.2)
    s += rect(52, 56, 16, 8, 4, WHITE, 'opacity="0.55"')
    s += line([(34, 112), (58, 112), (68, 98), (80, 126), (92, 106), (126, 106)], 7, WHITE)
    return badge("#FF4D9D", s)


def world_nature():
    s = circle(118, 44, 18, SUN) + rect(110, 34, 8, 4, 2, WHITE, 'opacity="0.6"')
    s += rect(72, 92, 16, 46, 8, "#8B5A2B")
    s += circle(80, 72, 32, LEAF) + circle(58, 88, 20, LEAF) + circle(102, 88, 20, LEAF)
    s += rect(56, 96, 52, 14, 7, LEAF_DARK, 'opacity="0.6"') + rect(64, 52, 16, 8, 4, LEAF_LIGHT)
    s += rect(20, 128, 120, 12, 6, LEAF_DARK)
    return badge("#38B000", s)


def world_style():
    s = rect(46, 52, 68, 76, 16, SUN) + rect(26, 52, 34, 34, 12, SUN, 'transform="rotate(25 43 69)"')
    s += rect(100, 52, 34, 34, 12, SUN, 'transform="rotate(-25 117 69)"')
    s += circle(80, 52, 12, "#9D4EDD") + rect(46, 108, 68, 20, 10, SUN_DARK)
    s += circle(64, 78, 6, BERRY) + circle(80, 90, 6, SKY) + circle(96, 78, 6, LEAF)
    s += rect(54, 62, 16, 7, 3.5, WHITE, 'opacity="0.5"')
    return badge("#9D4EDD", s)


# --------------------------------------------------------------------------
# UI icons (64x64)
# --------------------------------------------------------------------------

def icon(body):
    return svg(64, 64, body)


ICONS = {
    "flame": icon(path("M32 4 Q52 22 50 40 Q48 58 32 60 Q16 58 14 40 Q13 28 22 20 Q24 30 30 30 Q26 16 32 4 Z", FLAME)
                  + path("M32 30 Q42 40 40 48 Q38 56 32 56 Q26 56 24 48 Q24 40 32 30 Z", SUN)),
    "gem": icon(path("M14 22 L24 10 L40 10 L50 22 L32 54 Z", SKY) + path("M14 22 L50 22 L32 54 Z", SKY_DARK)
                + path("M24 22 L32 10 L40 22 L32 54 Z", "#6FD3FF") + rect(22, 13, 8, 4, 2, WHITE, 'opacity="0.7"')),
    "coin": icon(circle(32, 34, 26, SUN_DARK) + circle(32, 30, 26, SUN) + circle(32, 30, 17, "#FFD84D")
                 + rect(28, 20, 8, 20, 4, SUN_DARK) + rect(18, 14, 12, 5, 2.5, WHITE, 'opacity="0.6"')),
    "star": icon(path("M32 6 L39.5 22 L57 24 L44 36 L47.5 53 L32 44.5 L16.5 53 L20 36 L7 24 L24.5 22 Z", SUN,
                      f'stroke="{SUN}" stroke-width="6" stroke-linejoin="round"')),
    "star_empty": icon(path("M32 6 L39.5 22 L57 24 L44 36 L47.5 53 L32 44.5 L16.5 53 L20 36 L7 24 L24.5 22 Z", CLOUD,
                            f'stroke="{CLOUD}" stroke-width="6" stroke-linejoin="round"')),
    "crown": icon(rect(10, 40, 44, 14, 6, SUN_DARK) + path("M10 44 L8 18 L22 30 L32 12 L42 30 L56 18 L54 44 Z", SUN,
                  'stroke="#FFC800" stroke-width="5" stroke-linejoin="round"') + circle(32, 34, 5, BERRY)),
    "lock": icon(path("M20 30 L20 22 Q20 10 32 10 Q44 10 44 22 L44 30", "none", f'stroke="{MIST}" stroke-width="7" stroke-linecap="round"')
                 + rect(12, 28, 40, 30, 10, MIST) + circle(32, 41, 5, WHITE) + rect(30, 42, 4, 9, 2, WHITE)),
    "speaker": icon(rect(8, 24, 16, 18, 5, SKY) + path("M20 24 L36 10 L36 56 L20 42 Z", SKY, 'stroke="#1CB0F6" stroke-width="4" stroke-linejoin="round"')
                    + path("M44 22 Q52 33 44 44", "none", f'stroke="{SKY}" stroke-width="5" stroke-linecap="round"')
                    + path("M50 14 Q64 33 50 52", "none", f'stroke="{SKY}" stroke-width="5" stroke-linecap="round"')),
    "bulb": icon(circle(32, 26, 18, SUN) + rect(23, 36, 18, 12, 6, SUN) + rect(24, 48, 16, 6, 3, STONE) + rect(26, 54, 12, 5, 2.5, MIST)
                 + rect(24, 16, 8, 6, 3, WHITE, 'opacity="0.7"')),
    "shuffle": icon(line([(8, 18), (22, 18), (42, 46), (54, 46)], 6, SKY) + line([(8, 46), (22, 46), (42, 18), (54, 18)], 6, SKY)
                    + tri(54, 46, 9, SKY, rot=90) + tri(54, 18, 9, SKY, rot=90)),
    "sparkle": icon(path("M32 4 Q36 28 60 32 Q36 36 32 60 Q28 36 4 32 Q28 28 32 4 Z", GRAPE) + circle(50, 12, 5, SUN) + circle(14, 52, 4, SKY)),
    "note": icon(rect(12, 8, 40, 50, 10, WHITE, f'stroke="{CLOUD}" stroke-width="3"') + rect(20, 20, 24, 5, 2.5, GRAPE)
                 + rect(20, 31, 24, 5, 2.5, CLOUD) + rect(20, 42, 16, 5, 2.5, CLOUD)),
    "book": icon(rect(8, 12, 24, 42, 8, NAVY) + rect(32, 12, 24, 42, 8, SKY) + rect(28, 12, 8, 42, 3, SKY_DARK)
                 + rect(14, 20, 12, 4, 2, WHITE, 'opacity="0.6"') + rect(38, 20, 12, 4, 2, WHITE, 'opacity="0.6"')),
    "gear": icon("".join(rect(27, 4, 10, 16, 4, STONE, f'transform="rotate({a} 32 32)"') for a in range(0, 360, 45))
                 + circle(32, 32, 20, STONE) + circle(32, 32, 9, WHITE)),
    "map": icon(rect(6, 12, 52, 42, 10, LEAF) + path("M6 30 Q20 20 32 32 Q44 44 58 30", "none", f'stroke="{SUN}" stroke-width="5" stroke-linecap="round" stroke-dasharray="1 9"')
                + circle(46, 24, 7, BERRY) + rect(12, 16, 12, 5, 2.5, WHITE, 'opacity="0.5"')),
    "close": icon(line([(16, 16), (48, 48)], 7, MIST) + line([(48, 16), (16, 48)], 7, MIST)),
    "check": icon(line([(14, 34), (27, 46), (50, 20)], 8, LEAF)),
    "review": icon(path("M12 30 A20 20 0 0 1 48 20", "none", f'stroke="{GRAPE}" stroke-width="7" stroke-linecap="round"')
                   + tri(50, 18, 9, GRAPE, rot=60)
                   + path("M52 34 A20 20 0 0 1 16 44", "none", f'stroke="{BERRY}" stroke-width="7" stroke-linecap="round"')
                   + tri(14, 46, 9, BERRY, rot=240)),
    "calendar": icon(rect(8, 12, 48, 44, 10, WHITE, f'stroke="{CLOUD}" stroke-width="3"') + rect(8, 12, 48, 14, 7, BERRY)
                     + rect(18, 6, 6, 12, 3, INK) + rect(40, 6, 6, 12, 3, INK) + rect(22, 32, 20, 18, 5, SUN)),
}


# --------------------------------------------------------------------------
# App icon (512) and store feature graphic (1024x500)
# --------------------------------------------------------------------------

def app_icon():
    inner = lexi("happy").split("\n", 1)[1].rsplit("</svg>", 1)[0]
    return svg(512, 512, rect(0, 0, 512, 512, 112, SKY) + circle(420, 80, 70, "#6FD3FF", 'opacity="0.6"')
               + circle(60, 470, 110, SKY_DARK, 'opacity="0.5"')
               + f'<g transform="translate(36 40) scale(1.75)">{inner}</g>')


def feature_graphic():
    inner = lexi("cheer").split("\n", 1)[1].rsplit("</svg>", 1)[0]
    tiles = ""
    for i, (x, y, c) in enumerate([(520, 150, LEAF), (612, 150, SKY), (704, 150, SUN), (796, 150, BERRY), (888, 150, GRAPE)]):
        tiles += rect(x, y + 10, 80, 80, 18, "#000", 'opacity="0.12"') + rect(x, y, 80, 80, 18, WHITE)
        tiles += rect(x + 10, y + 64, 60, 8, 4, c)
    tiles += rect(612, 250, 80, 80, 18, WHITE) + rect(612, 342, 80, 80, 18, WHITE)
    tiles += letter_A(636, 172, 32, LEAF, 8)
    return svg(1024, 500, rect(0, 0, 1024, 500, 0, SKY)
               + circle(900, 420, 160, SKY_DARK, 'opacity="0.5"') + circle(120, 60, 120, "#6FD3FF", 'opacity="0.5"')
               + f'<g transform="translate(70 40) scale(1.65)">{inner}</g>' + tiles)


def adaptive_foreground():
    """Android adaptive icon foreground: mascot inside the 66% safe zone."""
    inner = lexi("happy").split("\n", 1)[1].rsplit("</svg>", 1)[0]
    return svg(432, 432, f'<g transform="translate(86 80) scale(1.02)">{inner}</g>')


def adaptive_background():
    return svg(432, 432, rect(0, 0, 432, 432, 0, SKY) + circle(360, 70, 70, "#6FD3FF", 'opacity="0.6"')
               + circle(50, 400, 100, SKY_DARK, 'opacity="0.5"'))


def main():
    os.makedirs(os.path.join(OUT, "mascot"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "worlds"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "icons"), exist_ok=True)
    for pose in ["happy", "wave", "cheer", "think", "oops"]:
        open(os.path.join(OUT, "mascot", f"lexi_{pose}.svg"), "w").write(lexi(pose))
    worlds = {"basics": world_basics, "food": world_food, "animals": world_animals, "home": world_home,
              "travel": world_travel, "body": world_body, "nature": world_nature, "style": world_style}
    for k, fn in worlds.items():
        open(os.path.join(OUT, "worlds", f"{k}.svg"), "w").write(fn())
    for k, v in ICONS.items():
        open(os.path.join(OUT, "icons", f"{k}.svg"), "w").write(v)
    open(os.path.join(OUT, "app_icon.svg"), "w").write(app_icon())
    open(os.path.join(OUT, "feature_graphic.svg"), "w").write(feature_graphic())
    open(os.path.join(OUT, "adaptive_foreground.svg"), "w").write(adaptive_foreground())
    open(os.path.join(OUT, "adaptive_background.svg"), "w").write(adaptive_background())
    # Ship SVGs untouched so the game can rasterise them at any size.
    for root, _, files in os.walk(OUT):
        for f in files:
            if f.endswith(".svg"):
                open(os.path.join(root, f + ".import"), "w").write('[remap]\n\nimporter="keep"\n')
    print("art written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
