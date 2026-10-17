#!/usr/bin/env python3
"""Draws one illustration per vocabulary word (160 total) in Lexigo's
three-shape style, replacing emoji in clues, results and the word list.

Run:  python3 tools/art/make_words.py   (writes assets/art/words/<world>/<en>.svg)
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from make_art import (rect, circle, ellipse, line, path, tri, svg,  # noqa: E402
                      LEAF, LEAF_DARK, LEAF_LIGHT, SKY, SKY_DARK, SKY_PALE, SUN, SUN_DARK,
                      FLAME, BERRY, BERRY_DARK, GRAPE, GRAPE_DARK, NAVY, INK, STONE, MIST,
                      CLOUD, SNOW, WHITE, BLUSH)

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
OUT = os.path.join(ROOT, "assets", "art", "words")

BROWN = "#A0673A"; BROWN_DARK = "#7A4A26"; TAN = "#E8B77A"; CREAM = "#FFF4DC"
SKIN = "#F5C99B"; SKIN_DARK = "#E0A878"; HAIR = "#5A3A22"; BLOND = "#F2C14E"
ORANGE = "#FF9600"; ORANGE_DARK = "#E07B00"; GREY = "#9AA3AD"; GREY_DARK = "#6F7883"
PINK = "#FF86C8"; RED = BERRY; TEAL = "#2EC4B6"; PURPLE = "#7C5CFF"


OUT_LINE = f'stroke="{CLOUD}" stroke-width="4"'
WOOL = "#F1F1F1"


def hl(x, y, w, h):
    """Glossy highlight pill, top-left of a form."""
    return rect(x, y, w, h, h / 2, WHITE, 'opacity="0.45"')


def ground(cx=80, w=56):
    return ellipse(cx, 146, w, 7, "#000", 'opacity="0.08"')


def stroke(d, color, width=6, extra=""):
    return path(d, "none", f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" {extra}')


def eyes(cx, cy, gap=12, r=4):
    return circle(cx - gap, cy, r, INK) + circle(cx + gap, cy, r, INK) + circle(cx - gap - 1.2, cy - 1.4, 1.3, WHITE) + circle(cx + gap - 1.2, cy - 1.4, 1.3, WHITE)


def smile(cx, cy, w=10):
    return stroke(f"M{cx - w} {cy} Q{cx} {cy + w * 0.8} {cx + w} {cy}", INK, 4)


def person(cx, top, scale=1.0, shirt=SKY, hair=HAIR, style="short", skin=SKIN):
    s = scale
    head_r = 22 * s
    hy = top + head_r
    out = ""
    if style == "long":
        out += rect(cx - 26 * s, hy - 10 * s, 52 * s, 50 * s, 18 * s, hair)
    out += rect(cx - 30 * s, hy + 18 * s, 60 * s, 52 * s, 22 * s, shirt)
    out += rect(cx - 22 * s, hy + 24 * s, 14 * s, 8 * s, 4 * s, WHITE, 'opacity="0.35"')
    out += circle(cx, hy, head_r, skin)
    if style in ("short", "long", "boy"):
        out += path(f"M{cx - head_r} {hy - 2 * s} Q{cx - head_r} {hy - head_r - 4 * s} {cx} {hy - head_r - 2 * s} "
                    f"Q{cx + head_r} {hy - head_r - 4 * s} {cx + head_r} {hy - 2 * s} Q{cx} {hy - 14 * s} {cx - head_r} {hy - 2 * s} Z", hair)
    if style == "pigtails":
        out += circle(cx - head_r - 4 * s, hy - 4 * s, 9 * s, hair) + circle(cx + head_r + 4 * s, hy - 4 * s, 9 * s, hair)
        out += path(f"M{cx - head_r} {hy - 2 * s} Q{cx} {hy - head_r - 12 * s} {cx + head_r} {hy - 2 * s} Q{cx} {hy - 12 * s} {cx - head_r} {hy - 2 * s} Z", hair)
    if style == "cap":
        out += path(f"M{cx - head_r} {hy - 4 * s} Q{cx} {hy - head_r - 14 * s} {cx + head_r} {hy - 4 * s} Z", RED)
        out += rect(cx, hy - 8 * s, 26 * s, 7 * s, 3.5 * s, BERRY_DARK)
    if style == "bald":
        pass
    out += eyes(cx, hy + 2 * s, 8 * s, 2.8 * s) + smile(cx, hy + 10 * s, 6 * s)
    out += circle(cx - 14 * s, hy + 9 * s, 4 * s, BLUSH, 'opacity="0.7"') + circle(cx + 14 * s, hy + 9 * s, 4 * s, BLUSH, 'opacity="0.7"')
    return out


def bubble(x, y, w, h, fill=WHITE, tail_left=True):
    t = tri(x + (18 if tail_left else w - 18), y + h + 4, 10, fill, rot=180)
    return rect(x, y + 4, w, h, 22, CLOUD) + rect(x, y, w, h, 22, fill) + t


def heart(cx, cy, s, color, light=True):
    out = circle(cx - 11 * s, cy - 6 * s, 14 * s, color) + circle(cx + 11 * s, cy - 6 * s, 14 * s, color)
    out += tri(cx, cy + 6 * s, 22 * s, color, rot=180, round_=0.22)
    if light:
        out += hl(cx - 20 * s, cy - 15 * s, 10 * s, 5 * s)
    return out


def hand(cx, cy, s=1.0, color=SKIN, shade=SKIN_DARK):
    out = rect(cx - 22 * s, cy - 6 * s, 44 * s, 44 * s, 16 * s, color)
    for i, h in enumerate([30, 36, 34, 28]):
        out += rect(cx - 21 * s + i * 11 * s, cy - 6 * s - h * s + 8 * s, 10 * s, h * s, 5 * s, color)
    out += rect(cx + 14 * s, cy + 4 * s, 12 * s, 28 * s, 6 * s, color, f'transform="rotate(-40 {cx + 20 * s} {cy + 18 * s})"')
    out += rect(cx - 16 * s, cy + 26 * s, 32 * s, 8 * s, 4 * s, shade, 'opacity="0.6"')
    return out


def building(x, y, w, h, color, win=SKY_PALE, cols=3, rows=3, roof=None):
    out = rect(x, y, w, h, 8, color)
    gx = w / (cols + 1)
    gy = (h - 20) / (rows + 1)
    for r in range(rows):
        for c in range(cols):
            out += rect(x + gx * (c + 1) - 6, y + 10 + gy * (r + 1) - 6, 12, 12, 3, win)
    return out


def wheel(cx, cy, r):
    return circle(cx, cy, r, INK) + circle(cx, cy, r * 0.45, MIST)


def blob(color, dark):
    """Paint splat for colour words."""
    out = circle(80, 82, 44, color) + circle(124, 60, 12, color) + circle(36, 116, 10, color) + circle(122, 116, 8, color)
    out += circle(40, 52, 7, color) + rect(48, 110, 64, 18, 9, dark, 'opacity="0.35"') + hl(54, 52, 26, 10)
    return out


def bowl(color=WHITE, rim=CLOUD):
    return path("M28 92 L132 92 Q130 138 80 138 Q30 138 28 92 Z", color) + rect(24, 86, 112, 12, 6, rim)


def mug(liquid, cup=WHITE):
    return (rect(36, 58, 70, 78, 18, cup) + stroke("M104 76 Q130 78 128 98 Q126 116 104 114", cup, 10)
            + rect(42, 62, 58, 12, 6, liquid) + rect(40, 120, 62, 12, 6, CLOUD))


# ------------------------------------------------------------------ worlds

def basics():
    return {
        "hello": hand(80, 82, 1.2) + stroke("M28 40 Q20 54 28 68", SKY, 5) + stroke("M134 40 Q142 54 134 68", SKY, 5),
        "thanks": bubble(18, 24, 124, 90) + heart(80, 72, 1.05, RED),
        "friend": person(56, 22, 0.95, SKY, HAIR) + person(106, 26, 0.9, ORANGE, BLOND, "long") + ground(80, 60),
        "name": rect(24, 36, 112, 84, 16, CLOUD) + rect(24, 32, 112, 84, 16, WHITE) + rect(24, 32, 112, 28, 14, RED)
                + rect(24, 46, 112, 14, 0, RED) + rect(40, 76, 60, 9, 4.5, MIST) + rect(40, 94, 40, 9, 4.5, CLOUD) + circle(80, 22, 7, STONE),
        "day": "".join(tri(80 + 56 * math.cos(math.radians(a)), 80 + 56 * math.sin(math.radians(a)), 11, SUN_DARK, rot=a + 90) for a in range(0, 360, 45))
               + circle(80, 80, 38, SUN) + hl(56, 56, 22, 9),
        "night": rect(14, 14, 132, 132, 32, NAVY) + circle(78, 78, 36, SUN) + circle(96, 66, 32, NAVY)
                 + tri(118, 40, 7, WHITE) + tri(40, 116, 6, WHITE) + tri(120, 112, 5, WHITE),
        "morning": rect(14, 14, 132, 132, 32, "#FFE3B3") + circle(80, 104, 32, ORANGE) + rect(14, 100, 132, 46, 0, LEAF)
                   + path("M14 104 Q60 84 146 104 L146 146 L14 146 Z", LEAF) + rect(14, 130, 132, 16, 0, LEAF_DARK),
        "man": person(80, 18, 1.25, SKY, HAIR) + ground(),
        "woman": person(80, 18, 1.25, GRAPE, BROWN, "long") + ground(),
        "child": person(80, 42, 0.95, SUN, HAIR, "cap") + ground(80, 40),
        "family": person(44, 26, 0.85, SKY, HAIR) + person(116, 26, 0.85, GRAPE, BROWN, "long") + person(80, 58, 0.65, SUN, BLOND, "pigtails") + ground(80, 70),
        "mother": person(72, 18, 1.15, GRAPE, BROWN, "long") + circle(112, 98, 18, CREAM) + circle(112, 92, 11, SKIN) + rect(96, 100, 32, 18, 9, PINK) + ground(),
        "father": person(80, 18, 1.25, TEAL, HAIR) + rect(66, 64, 28, 7, 3.5, HAIR) + tri(80, 98, 9, RED, rot=180) + ground(),
        "brother": person(80, 28, 1.1, LEAF, HAIR, "boy") + ground(),
        "sister": person(80, 28, 1.1, PINK, BROWN, "pigtails") + ground(),
        "love": heart(80, 80, 2.0, RED) + heart(126, 34, 0.5, PINK, False) + heart(34, 40, 0.4, PINK, False),
        "time": rect(42, 22, 76, 12, 6, BROWN) + rect(42, 126, 76, 12, 6, BROWN)
                + path("M52 34 L108 34 Q108 64 84 80 Q108 96 108 126 L52 126 Q52 96 76 80 Q52 64 52 34 Z", SKY_PALE)
                + path("M60 44 L100 44 Q96 62 80 72 Q64 62 60 44 Z", SUN) + path("M64 118 Q80 100 96 118 Z", SUN)
                + rect(78, 76, 4, 30, 2, SUN),
        "word": bubble(16, 28, 128, 86) + "".join(rect(30 + i * 34, 52, 28, 34, 7, c) for i, c in enumerate([SKY, LEAF, SUN])),
        "question": bubble(22, 18, 116, 104, SKY) + stroke("M62 52 Q62 36 80 36 Q98 36 98 52 Q98 64 80 70 L80 82", WHITE, 10) + circle(80, 100, 6, WHITE),
        "answer": bubble(22, 18, 116, 104, LEAF, False) + stroke("M54 70 L74 90 L108 50", WHITE, 12),
    }


def food():
    return {
        "apple": circle(66, 88, 36, RED) + circle(94, 88, 36, RED) + rect(54, 104, 52, 22, 11, BERRY_DARK, 'opacity="0.4"')
                 + rect(76, 38, 8, 24, 4, BROWN) + path("M84 50 Q106 32 118 48 Q102 62 84 50 Z", LEAF) + hl(48, 64, 18, 9) + ground(),
        "bread": rect(22, 56, 116, 76, 34, TAN) + rect(22, 104, 116, 28, 14, "#D99A55") + stroke("M50 70 L62 92", "#C98A45", 6)
                 + stroke("M76 66 L88 90", "#C98A45", 6) + stroke("M102 70 L114 92", "#C98A45", 6) + hl(34, 64, 26, 9) + ground(),
        "water": path("M80 22 Q122 76 118 102 Q114 136 80 138 Q46 136 42 102 Q38 76 80 22 Z", SKY) + path("M80 96 Q96 122 80 128 Q68 124 72 112 Z", SKY_DARK, 'opacity="0.4"')
                 + hl(54, 84, 12, 26) + ground(),
        "milk": rect(46, 52, 68, 86, 10, WHITE, OUT_LINE) + path("M46 54 L62 26 L98 26 L114 54 Z", CLOUD) + rect(46, 80, 68, 30, 0, SKY)
                + rect(74, 18, 14, 12, 4, CLOUD) + circle(80, 95, 8, WHITE) + ground(),
        "cheese": path("M22 104 L130 60 L138 120 Q80 132 26 124 Z", SUN) + path("M22 104 L130 60 L120 56 Q60 66 22 98 Z", "#FFE066")
                  + circle(62, 108, 8, SUN_DARK) + circle(100, 98, 10, SUN_DARK) + circle(118, 112, 5, SUN_DARK) + ground(),
        "egg": ellipse(80, 84, 40, 52, CREAM) + ellipse(80, 100, 34, 26, "#F2E0B8", 'opacity="0.6"') + hl(56, 50, 14, 22) + ground(80, 40),
        "rice": circle(58, 86, 18, WHITE, OUT_LINE) + circle(80, 78, 22, WHITE, OUT_LINE) + circle(102, 86, 18, WHITE, OUT_LINE) + bowl(SKY, SKY_DARK)
                + stroke("M104 36 L128 82", BROWN, 6) + stroke("M118 30 L136 78", BROWN, 6) + ground(),
        "fish": ellipse(76, 82, 48, 30, SKY) + tri(132, 82, 22, SKY_DARK, rot=-90) + ellipse(76, 92, 40, 14, SKY_PALE, 'opacity="0.6"')
                + circle(48, 76, 6, WHITE) + circle(49, 76, 3.5, INK) + rect(72, 54, 20, 12, 6, SKY_DARK) + ground(),
        "meat": path("M30 76 Q32 42 76 44 Q128 44 130 82 Q132 122 84 124 Q34 124 30 76 Z", "#E2574C")
                + path("M44 78 Q48 58 76 58 Q114 58 116 82 Q116 108 82 110 Q46 108 44 78 Z", "#C8443A")
                + stroke("M58 82 Q80 72 102 86", "#F5A8A0", 7) + hl(44, 52, 20, 8) + ground(),
        "sugar": rect(30, 66, 50, 50, 10, WHITE, OUT_LINE) + rect(78, 54, 50, 50, 10, WHITE, OUT_LINE) + rect(54, 26, 46, 46, 10, WHITE, OUT_LINE)
                 + rect(36, 104, 38, 8, 4, CLOUD) + rect(84, 92, 38, 8, 4, CLOUD) + rect(60, 62, 34, 8, 4, CLOUD) + ground(),
        "salt": rect(48, 56, 64, 82, 18, WHITE, OUT_LINE) + rect(52, 118, 56, 14, 7, CLOUD) + path("M52 58 Q80 20 108 58 Z", GREY)
                + circle(72, 46, 3, INK) + circle(88, 46, 3, INK) + circle(80, 38, 3, INK) + ground(),
        "coffee": mug(BROWN_DARK, RED) + stroke("M58 46 Q52 36 58 26", MIST, 5) + stroke("M80 46 Q74 36 80 26", MIST, 5) + ground(),
        "tea": ellipse(76, 132, 60, 10, SKY) + path("M30 74 L122 74 Q118 128 76 128 Q34 128 30 74 Z", SKY_PALE, OUT_LINE) + rect(30, 70, 92, 12, 6, "#C8A04A")
               + stroke("M120 86 Q140 88 136 104 Q132 116 116 112", SKY_PALE, 8) + stroke("M60 72 L56 44", STONE, 3) + rect(46, 30, 20, 18, 4, SUN) + ground(),
        "olive": stroke("M20 52 Q80 30 140 50", BROWN, 6) + ellipse(56, 82, 18, 24, LEAF_DARK) + ellipse(98, 88, 18, 24, "#556B2F")
                 + path("M70 44 Q86 24 100 42 Q86 52 70 44 Z", LEAF) + path("M110 46 Q132 36 136 56 Q120 60 110 46 Z", LEAF) + hl(46, 66, 8, 14) + hl(88, 72, 8, 14),
        "orange": circle(80, 86, 48, ORANGE) + rect(46, 110, 68, 18, 9, ORANGE_DARK, 'opacity="0.4"') + path("M80 40 Q100 22 116 34 Q100 48 80 40 Z", LEAF)
                  + circle(80, 40, 5, LEAF_DARK) + hl(52, 58, 20, 9) + ground(),
        "banana": path("M30 50 Q40 128 128 118 Q136 110 128 104 Q60 108 46 46 Z", SUN) + path("M40 60 Q56 108 120 108 Q70 116 40 60 Z", SUN_DARK, 'opacity="0.5"')
                  + rect(24, 40, 18, 12, 4, BROWN) + ground(),
        "tomato": circle(80, 88, 46, RED) + "".join(tri(80 + 16 * math.cos(math.radians(a)), 46 + 10 * math.sin(math.radians(a)), 10, LEAF, rot=a + 90) for a in range(-180, 180, 72))
                  + rect(76, 30, 8, 16, 4, LEAF_DARK) + hl(54, 62, 18, 9) + ground(),
        "soup": bowl(RED, BERRY_DARK) + path("M30 92 L130 92 Q128 98 80 100 Q32 98 30 92 Z", ORANGE) + circle(62, 92, 5, LEAF) + circle(96, 93, 4, LEAF)
                + stroke("M62 70 Q56 58 62 46", MIST, 5) + stroke("M84 70 Q78 58 84 46", MIST, 5) + stroke("M106 70 Q100 58 106 46", MIST, 5),
        "cake": rect(30, 80, 100, 56, 14, PINK) + rect(30, 104, 100, 10, 0, CREAM) + rect(30, 76, 100, 16, 8, CREAM)
                + circle(46, 90, 7, CREAM) + circle(70, 92, 7, CREAM) + circle(94, 92, 7, CREAM) + circle(118, 90, 7, CREAM)
                + rect(74, 46, 12, 32, 5, SKY) + path("M80 26 Q90 38 80 46 Q70 38 80 26 Z", ORANGE) + ground(),
        "lemon": ellipse(80, 86, 54, 38, SUN) + circle(28, 86, 8, SUN) + circle(132, 86, 8, SUN) + ellipse(80, 102, 44, 16, SUN_DARK, 'opacity="0.35"')
                 + path("M82 48 Q100 30 116 42 Q100 56 82 48 Z", LEAF) + hl(52, 62, 22, 9) + ground(),
    }


def face_base(color, cx=80, cy=82, r=42):
    return circle(cx, cy, r, color) + hl(cx - r * 0.6, cy - r * 0.7, r * 0.5, r * 0.2)


def animals():
    return {
        "dog": rect(32, 44, 26, 58, 13, BROWN_DARK, 'transform="rotate(15 45 73)"') + rect(102, 44, 26, 58, 13, BROWN_DARK, 'transform="rotate(-15 115 73)"')
               + face_base(TAN) + ellipse(80, 104, 24, 18, CREAM) + ellipse(80, 94, 9, 7, INK) + eyes(80, 74, 16, 5)
               + stroke("M72 112 Q80 118 88 112", INK, 4) + ground(),
        "cat": tri(48, 50, 22, ORANGE, rot=-20) + tri(112, 50, 22, ORANGE, rot=20) + tri(50, 54, 11, PINK, rot=-20) + tri(110, 54, 11, PINK, rot=20)
               + face_base(ORANGE, 80, 88, 42) + eyes(80, 82, 16, 5) + tri(80, 98, 5, PINK, rot=180)
               + stroke("M26 96 L56 100", INK, 3) + stroke("M26 108 L56 106", INK, 3) + stroke("M134 96 L104 100", INK, 3) + stroke("M134 108 L104 106", INK, 3) + ground(),
        "horse": rect(52, 26, 60, 108, 30, BROWN, 'transform="rotate(-12 82 80)"') + ellipse(70, 118, 30, 22, TAN)
                 + rect(98, 20, 16, 64, 8, BROWN_DARK, 'transform="rotate(-12 106 52)"') + tri(98, 24, 12, BROWN, rot=-10)
                 + circle(84, 70, 5, INK) + circle(62, 118, 4, BROWN_DARK) + circle(78, 122, 4, BROWN_DARK) + ground(),
        "bird": circle(76, 86, 42, SKY) + ellipse(76, 104, 30, 20, SKY_PALE) + tri(124, 84, 12, ORANGE, rot=90) + circle(96, 74, 6, INK)
                + path("M40 82 Q50 112 82 104 Q60 92 40 82 Z", SKY_DARK) + tri(76, 42, 9, SKY_DARK) + stroke("M66 128 L66 140", ORANGE, 5) + stroke("M86 128 L86 140", ORANGE, 5),
        "cow": rect(28, 36, 22, 14, 7, CREAM, 'transform="rotate(-20 39 43)"') + rect(110, 36, 22, 14, 7, CREAM, 'transform="rotate(20 121 43)"')
               + ellipse(34, 64, 16, 10, WHITE) + ellipse(126, 64, 16, 10, WHITE) + rect(38, 40, 84, 96, 38, WHITE)
               + circle(56, 58, 12, INK) + circle(108, 72, 9, INK) + ellipse(80, 114, 34, 22, PINK) + circle(70, 114, 4, INK) + circle(90, 114, 4, INK) + eyes(80, 80, 18, 5) + ground(),
        "lion": "".join(circle(80 + 44 * math.cos(math.radians(a)), 82 + 44 * math.sin(math.radians(a)), 16, ORANGE_DARK) for a in range(0, 360, 36))
                + circle(80, 82, 44, ORANGE_DARK) + face_base(SUN, 80, 84, 34) + circle(56, 54, 9, SUN) + circle(104, 54, 9, SUN)
                + eyes(80, 78, 13, 4.5) + rect(72, 88, 16, 10, 5, BROWN) + smile(80, 102, 7),
        "mouse": circle(44, 52, 24, GREY) + circle(116, 52, 24, GREY) + circle(44, 52, 13, PINK) + circle(116, 52, 13, PINK)
                 + face_base(GREY, 80, 92, 38) + eyes(80, 86, 14, 4.5) + circle(80, 104, 6, PINK)
                 + stroke("M34 104 L60 106", INK, 3) + stroke("M126 104 L100 106", INK, 3) + ground(),
        "rabbit": rect(48, 10, 22, 70, 11, WOOL, 'transform="rotate(-10 59 45)" ' + OUT_LINE) + rect(90, 10, 22, 70, 11, WOOL, 'transform="rotate(10 101 45)" ' + OUT_LINE)
                  + rect(53, 18, 11, 50, 5.5, PINK, 'transform="rotate(-10 59 45)"') + rect(96, 18, 11, 50, 5.5, PINK, 'transform="rotate(10 101 45)"')
                  + circle(80, 98, 38, WOOL, OUT_LINE) + eyes(80, 92, 14, 4.5) + tri(80, 106, 5, PINK, rot=180) + rect(74, 112, 12, 12, 3, WHITE, f'stroke="{CLOUD}" stroke-width="2"') + ground(),
        "bear": circle(44, 48, 18, BROWN) + circle(116, 48, 18, BROWN) + circle(44, 48, 9, TAN) + circle(116, 48, 9, TAN)
                + face_base(BROWN, 80, 88, 44) + ellipse(80, 106, 22, 16, TAN) + ellipse(80, 98, 9, 6, INK) + eyes(80, 80, 16, 5) + ground(),
        "wolf": tri(48, 44, 24, GREY_DARK, rot=-15) + tri(112, 44, 24, GREY_DARK, rot=15) + face_base(GREY, 80, 82, 40)
                + path("M56 92 L104 92 L92 128 Q80 134 68 128 Z", WHITE) + ellipse(80, 118, 8, 6, INK) + eyes(80, 76, 15, 5)
                + path("M40 82 L56 92 L46 104 Z", GREY) + path("M120 82 L104 92 L114 104 Z", GREY) + ground(),
        "monkey": circle(34, 82, 16, BROWN) + circle(126, 82, 16, BROWN) + circle(34, 82, 8, TAN) + circle(126, 82, 8, TAN)
                  + face_base(BROWN, 80, 80, 42) + ellipse(68, 76, 16, 18, TAN) + ellipse(92, 76, 16, 18, TAN) + ellipse(80, 102, 26, 18, TAN)
                  + eyes(80, 74, 12, 4.5) + smile(80, 104, 9) + ground(),
        "elephant": ellipse(36, 78, 28, 36, GREY) + ellipse(124, 78, 28, 36, GREY) + ellipse(36, 78, 18, 24, PINK, 'opacity="0.5"') + ellipse(124, 78, 18, 24, PINK, 'opacity="0.5"')
                    + face_base(GREY, 80, 74, 36) + stroke("M80 92 Q80 124 96 128 Q104 128 104 120", GREY, 22) + eyes(80, 66, 14, 4.5) + ground(),
        "snake": stroke("M28 128 Q28 96 60 100 Q96 104 98 76 Q100 52 76 50", LEAF, 22) + stroke("M28 128 Q28 96 60 100 Q96 104 98 76 Q100 52 76 50", LEAF_LIGHT, 6, 'stroke-dasharray="2 14"')
                 + ellipse(70, 44, 26, 18, LEAF) + circle(62, 38, 4, INK) + circle(78, 38, 4, INK) + stroke("M46 48 L36 50 M36 50 L30 46 M36 50 L30 54", RED, 3),
        "frog": circle(54, 54, 18, LEAF) + circle(106, 54, 18, LEAF) + circle(54, 54, 11, WHITE) + circle(106, 54, 11, WHITE) + circle(56, 56, 6, INK) + circle(108, 56, 6, INK)
                + ellipse(80, 92, 54, 38, LEAF) + ellipse(80, 110, 40, 18, LEAF_LIGHT) + stroke("M54 94 Q80 112 106 94", LEAF_DARK, 5)
                + circle(58, 92, 5, BLUSH, 'opacity="0.7"') + circle(102, 92, 5, BLUSH, 'opacity="0.7"') + ground(),
        "sheep": "".join(circle(80 + 40 * math.cos(math.radians(a)), 82 + 32 * math.sin(math.radians(a)), 22, CLOUD) for a in range(0, 360, 40))
                 + "".join(circle(80 + 40 * math.cos(math.radians(a)), 82 + 32 * math.sin(math.radians(a)), 18, WOOL) for a in range(0, 360, 40))
                 + circle(80, 82, 40, WOOL) + ellipse(80, 88, 22, 28, INK) + ellipse(52, 78, 12, 6, INK) + ellipse(108, 78, 12, 6, INK)
                 + circle(72, 84, 4, WHITE) + circle(88, 84, 4, WHITE) + ground(),
        "goat": stroke("M62 50 Q52 24 40 30", TAN, 8) + stroke("M98 50 Q108 24 120 30", TAN, 8) + ellipse(40, 66, 18, 9, CREAM) + ellipse(120, 66, 18, 9, CREAM)
                + rect(50, 46, 60, 80, 28, CREAM) + ellipse(80, 108, 24, 18, "#F2E0B8") + tri(80, 130, 10, TAN, rot=180) + eyes(80, 76, 14, 4.5)
                + circle(74, 106, 3, INK) + circle(86, 106, 3, INK) + ground(),
        "camel": ellipse(78, 96, 46, 24, TAN) + circle(62, 74, 18, TAN) + circle(92, 74, 18, TAN) + stroke("M118 96 Q132 70 126 44", TAN, 18)
                 + ellipse(132, 42, 14, 10, TAN) + circle(134, 38, 3, INK) + rect(42, 110, 10, 30, 5, "#D9A35B") + rect(60, 110, 10, 30, 5, "#D9A35B")
                 + rect(90, 110, 10, 30, 5, "#D9A35B") + rect(106, 110, 10, 30, 5, "#D9A35B") + ground(),
        "duck": ellipse(76, 104, 50, 30, SUN) + circle(96, 62, 26, SUN) + ellipse(126, 68, 16, 8, ORANGE) + circle(102, 56, 5, INK)
                + path("M44 96 Q60 120 92 108 Q70 100 44 96 Z", SUN_DARK) + hl(84, 42, 14, 6) + ground(),
        "turtle": circle(128, 98, 16, LEAF_LIGHT) + rect(40, 112, 18, 22, 9, LEAF_LIGHT) + rect(100, 112, 18, 22, 9, LEAF_LIGHT)
                  + path("M28 116 Q30 56 78 56 Q126 56 128 116 Z", LEAF_DARK) + circle(60, 92, 10, LEAF) + circle(96, 92, 10, LEAF) + circle(78, 74, 10, LEAF)
                  + rect(24, 110, 108, 12, 6, LEAF) + circle(134, 94, 3.5, INK) + ground(),
        "bee": ellipse(54, 54, 18, 26, SKY_PALE, 'transform="rotate(-25 54 54)"') + ellipse(92, 50, 18, 26, SKY_PALE, 'transform="rotate(25 92 50)"')
               + ellipse(76, 92, 46, 34, SUN) + rect(62, 60, 12, 66, 6, INK) + rect(88, 62, 12, 62, 6, INK) + tri(30, 92, 8, INK, rot=-90)
               + circle(110, 86, 5, INK) + stroke("M110 60 Q116 44 126 42", INK, 3) + hl(96, 66, 14, 6),
    }


def home():
    return {
        "house": tri(80, 52, 56, RED, round_=0.12) + rect(36, 66, 88, 72, 10, CREAM) + rect(68, 98, 24, 40, 8, BROWN) + rect(46, 80, 16, 16, 4, SKY) + rect(98, 80, 16, 16, 4, SKY) + ground(),
        "door": rect(46, 20, 68, 120, 14, BROWN) + rect(54, 30, 52, 44, 8, BROWN_DARK, 'opacity="0.5"') + rect(54, 84, 52, 44, 8, BROWN_DARK, 'opacity="0.5"')
                + circle(98, 82, 6, SUN) + hl(52, 26, 14, 6) + ground(80, 40),
        "window": rect(26, 26, 108, 108, 14, WHITE) + rect(34, 34, 42, 42, 6, SKY) + rect(84, 34, 42, 42, 6, SKY) + rect(34, 84, 42, 42, 6, SKY) + rect(84, 84, 42, 42, 6, SKY)
                  + stroke("M40 66 L64 42", WHITE, 5, 'opacity="0.6"') + rect(20, 128, 120, 12, 6, CLOUD),
        "table": rect(16, 60, 128, 16, 8, BROWN) + rect(16, 70, 128, 8, 4, BROWN_DARK) + rect(30, 74, 12, 62, 6, BROWN) + rect(118, 74, 12, 62, 6, BROWN)
                 + rect(56, 40, 30, 22, 8, SKY) + circle(106, 50, 12, RED) + ground(80, 66),
        "chair": rect(46, 16, 16, 120, 8, ORANGE_DARK) + rect(46, 16, 64, 50, 14, ORANGE) + rect(46, 78, 72, 16, 8, ORANGE) + rect(102, 90, 14, 46, 7, ORANGE_DARK)
                 + rect(48, 90, 14, 46, 7, ORANGE_DARK) + hl(56, 24, 22, 7) + ground(),
        "bed": rect(16, 40, 18, 100, 9, BROWN) + rect(126, 74, 18, 66, 9, BROWN) + rect(24, 84, 112, 34, 10, SKY) + rect(32, 66, 40, 22, 10, WHITE)
               + rect(64, 76, 72, 42, 12, SKY_DARK) + rect(24, 112, 112, 12, 6, BROWN_DARK) + ground(),
        "kitchen": rect(28, 70, 104, 68, 12, WHITE) + rect(28, 66, 104, 12, 6, CLOUD) + rect(40, 92, 80, 34, 8, INK)
                   + path("M50 44 L110 44 L106 66 L54 66 Z", GREY) + rect(42, 40, 76, 8, 4, GREY_DARK) + stroke("M66 34 Q62 24 66 14", MIST, 4) + stroke("M90 34 Q86 24 90 14", MIST, 4) + ground(),
        "key": circle(48, 80, 28, SUN) + circle(48, 80, 12, WHITE) + rect(66, 72, 72, 16, 8, SUN) + rect(110, 84, 10, 22, 4, SUN) + rect(126, 84, 10, 16, 4, SUN) + hl(30, 60, 14, 6),
        "lamp": path("M46 70 L60 26 L100 26 L114 70 Z", SUN) + rect(46, 64, 68, 10, 5, SUN_DARK) + rect(74, 74, 12, 50, 6, GREY) + rect(52, 122, 56, 16, 8, GREY_DARK) + hl(64, 32, 14, 6) + ground(),
        "book": rect(26, 34, 108, 96, 10, NAVY) + rect(30, 30, 100, 92, 10, SKY) + rect(30, 30, 18, 92, 8, SKY_DARK) + rect(60, 52, 54, 10, 5, WHITE) + rect(60, 70, 38, 8, 4, SKY_PALE)
                + rect(40, 118, 94, 10, 4, CREAM) + ground(),
        "cup": rect(36, 52, 74, 80, 22, TEAL) + stroke("M108 70 Q134 72 132 94 Q130 114 108 112", TEAL, 10) + rect(42, 56, 62, 12, 6, BROWN_DARK) + hl(46, 74, 10, 26) + ground(),
        "plate": ellipse(80, 96, 66, 34, WHITE) + ellipse(80, 96, 66, 34, "none", f'stroke="{CLOUD}" stroke-width="4"') + ellipse(80, 94, 40, 18, SNOW)
                 + ellipse(80, 94, 40, 18, "none", f'stroke="{CLOUD}" stroke-width="3"') + ground(80, 60),
        "knife": rect(24, 68, 56, 22, 11, BROWN) + path("M78 68 L140 68 Q136 92 78 90 Z", MIST) + path("M78 68 L140 68 Q138 76 78 76 Z", WHITE, 'opacity="0.5"')
                 + circle(40, 79, 3, CREAM) + circle(60, 79, 3, CREAM),
        "spoon": ellipse(110, 54, 24, 32, MIST, 'transform="rotate(40 110 54)"') + ellipse(112, 52, 14, 20, WHITE, 'opacity="0.4" transform="rotate(40 112 52)"')
                 + stroke("M94 72 L34 132", GREY, 12),
        "garden": rect(14, 108, 132, 32, 12, LEAF) + "".join(rect(20 + i * 26, 70, 14, 52, 6, CREAM) for i in range(5))
                  + rect(16, 86, 128, 8, 4, CREAM) + stroke("M48 108 L48 60", LEAF_DARK, 4) + circle(48, 52, 12, PINK) + circle(48, 52, 5, SUN)
                  + stroke("M108 108 L108 50", LEAF_DARK, 4) + circle(108, 42, 12, RED) + circle(108, 42, 5, SUN),
        "roof": path("M14 108 L80 34 L146 108 Z", RED) + path("M34 86 L126 86 L117 76 L43 76 Z", BERRY_DARK) + path("M52 66 L108 66 L100 56 L60 56 Z", BERRY_DARK)
                + rect(104, 40, 18, 40, 4, BROWN) + rect(20, 104, 120, 12, 6, BERRY_DARK) + rect(30, 116, 100, 24, 4, CREAM),
        "wall": "".join(rect(14 + (i % 3) * 46 - (23 if (i // 3) % 2 else 0), 24 + (i // 3) * 30, 42, 26, 6, "#D9673A" if (i * 7) % 3 else "#C4572E") for i in range(15)),
        "mirror": ellipse(80, 70, 40, 54, SUN_DARK) + ellipse(80, 70, 32, 46, SKY_PALE) + stroke("M64 52 L80 36", WHITE, 6) + stroke("M66 72 L92 46", WHITE, 6)
                  + rect(74, 120, 12, 18, 4, SUN_DARK) + rect(56, 134, 48, 8, 4, SUN_DARK),
        "clock": circle(80, 80, 54, RED) + circle(80, 80, 44, WHITE) + stroke("M80 80 L80 50", INK, 6) + stroke("M80 80 L102 92", INK, 6) + circle(80, 80, 5, RED)
                 + "".join(circle(80 + 36 * math.cos(math.radians(a)), 80 + 36 * math.sin(math.radians(a)), 3, MIST) for a in range(0, 360, 30)),
        "soap": rect(28, 78, 104, 52, 22, PINK) + rect(28, 112, 104, 18, 9, "#E66BAE") + hl(42, 86, 30, 9) + circle(56, 52, 14, SKY_PALE) + circle(90, 40, 10, SKY_PALE)
                + circle(118, 58, 8, SKY_PALE) + circle(52, 48, 4, WHITE) + ground(),
    }


def travel():
    return {
        "city": building(14, 56, 40, 84, SKY_DARK, cols=2, rows=4) + building(58, 26, 46, 114, PURPLE, cols=2, rows=6) + building(108, 70, 38, 70, TEAL, cols=2, rows=3)
                + rect(10, 134, 140, 8, 4, GREY),
        "car": rect(22, 74, 116, 42, 18, RED) + path("M46 76 L60 46 L104 46 L120 76 Z", RED) + path("M56 74 L66 54 L80 54 L80 74 Z", SKY_PALE)
               + path("M86 74 L86 54 L100 54 L110 74 Z", SKY_PALE) + wheel(52, 116, 16) + wheel(108, 116, 16) + rect(124, 86, 12, 8, 4, SUN) + hl(32, 82, 22, 7) + ground(),
        "train": rect(30, 26, 100, 102, 24, SKY) + rect(42, 40, 76, 38, 10, SKY_PALE) + rect(30, 86, 100, 10, 0, WHITE) + circle(52, 108, 8, SUN) + circle(108, 108, 8, SUN)
                 + rect(40, 126, 24, 14, 6, INK) + rect(96, 126, 24, 14, 6, INK) + rect(64, 16, 32, 12, 6, SKY_DARK) + ground(),
        "plane": tri(40, 62, 22, RED, round_=0.25) + tri(84, 108, 34, SKY_DARK, rot=180, round_=0.25) + rect(20, 64, 124, 32, 16, SKY) + tri(80, 56, 30, SKY_DARK, round_=0.25)
                 + rect(28, 84, 112, 10, 5, SKY_DARK, 'opacity="0.5"')
                 + "".join(circle(64 + i * 16, 76, 5, WHITE) for i in range(4)) + path("M128 66 Q144 68 142 78 L128 78 Z", NAVY),
        "bus": rect(22, 34, 116, 92, 18, SUN) + rect(32, 46, 96, 36, 8, SKY_PALE) + stroke("M80 46 L80 82", SUN, 5) + rect(22, 92, 116, 10, 0, SUN_DARK)
               + wheel(50, 126, 14) + wheel(110, 126, 14) + rect(30, 106, 16, 10, 5, WHITE) + rect(114, 106, 16, 10, 5, WHITE) + ground(),
        "boat": rect(14, 120, 132, 22, 11, SKY) + path("M28 100 L132 100 Q122 128 80 128 Q38 128 28 100 Z", BROWN) + rect(76, 22, 8, 80, 4, BROWN_DARK)
                + path("M86 26 L86 92 L132 92 Z", WHITE) + path("M74 34 L74 92 L34 92 Z", RED),
        "bridge": rect(10, 116, 140, 30, 12, SKY) + rect(10, 78, 140, 14, 7, RED) + rect(30, 30, 14, 92, 6, BERRY_DARK) + rect(116, 30, 14, 92, 6, BERRY_DARK)
                  + stroke("M37 34 Q80 92 123 34", RED, 4) + "".join(stroke(f"M{x} {78} L{x} {60 + abs(80 - x) * 0.6}", RED, 2) for x in range(50, 116, 12)),
        "ticket": path("M18 52 L142 52 L142 70 Q132 80 142 90 L142 108 L18 108 L18 90 Q28 80 18 70 Z", SUN) + stroke("M108 56 L108 104", WHITE, 3, 'stroke-dasharray="4 6"')
                  + rect(34, 64, 56, 10, 5, WHITE) + rect(34, 84, 40, 8, 4, SUN_DARK) + circle(124, 80, 8, RED),
        "hotel": building(28, 30, 104, 110, PURPLE, cols=4, rows=5) + rect(58, 112, 44, 28, 6, SUN) + rect(46, 104, 68, 12, 6, RED) + rect(40, 14, 80, 20, 8, RED) + ground(80, 66),
        "market": rect(26, 78, 108, 60, 8, CREAM) + "".join(rect(18 + i * 31, 48, 31, 32, 0 if 0 < i < 3 else 8, RED if i % 2 == 0 else WHITE) for i in range(4))
                   + "".join(circle(24 + i * 31 + 15, 80, 15, RED if i % 2 == 0 else WHITE) for i in range(4))
                   + circle(52, 112, 10, ORANGE) + circle(76, 114, 9, LEAF) + circle(100, 112, 10, RED) + rect(26, 122, 108, 16, 4, BROWN) + ground(),
        "bank": tri(80, 38, 46, GREY, round_=0.12) + rect(30, 54, 100, 10, 4, GREY_DARK) + "".join(rect(38 + i * 24, 66, 12, 56, 4, CLOUD) for i in range(4))
                + rect(24, 120, 112, 16, 6, GREY_DARK) + circle(80, 40, 8, SUN),
        "school": rect(30, 62, 100, 76, 8, RED) + tri(80, 46, 50, BERRY_DARK, round_=0.12) + rect(70, 104, 20, 34, 6, BROWN) + circle(80, 70, 10, WHITE)
                  + rect(44, 82, 16, 16, 4, SKY_PALE) + rect(100, 82, 16, 16, 4, SKY_PALE) + rect(78, 12, 4, 22, 2, INK) + path("M82 12 L100 18 L82 24 Z", SUN) + ground(),
        "hospital": building(26, 40, 108, 100, WHITE, win=SKY_PALE, cols=3, rows=3) + rect(26, 40, 108, 100, 8, "none", f'stroke="{CLOUD}" stroke-width="4"')
                    + rect(66, 14, 28, 28, 6, WHITE) + rect(74, 18, 12, 20, 3, RED) + rect(70, 22, 20, 12, 3, RED) + rect(64, 108, 32, 32, 6, SKY) + ground(80, 60),
        "money": rect(16, 46, 108, 64, 12, LEAF) + rect(24, 54, 92, 48, 8, LEAF_LIGHT) + circle(70, 78, 16, LEAF) + circle(118, 112, 22, SUN_DARK) + circle(118, 108, 22, SUN)
                 + circle(118, 108, 13, "#FFE066") + hl(104, 92, 12, 5),
        "map": path("M18 40 L58 28 L102 40 L142 28 L142 120 L102 132 L58 120 L18 132 Z", CREAM) + path("M58 28 L102 40 L102 132 L58 120 Z", "#F2E0B8")
               + stroke("M30 110 Q60 80 82 96 Q106 112 124 66", RED, 4, 'stroke-dasharray="2 8"') + circle(124, 56, 12, RED) + circle(124, 56, 5, WHITE),
        "bicycle": circle(42, 104, 26, "none", f'stroke="{INK}" stroke-width="8"') + circle(118, 104, 26, "none", f'stroke="{INK}" stroke-width="8"')
                   + stroke("M42 104 L70 64 L106 64 L118 104 M70 64 L80 104 L106 64 M80 104 L42 104", LEAF, 7) + stroke("M64 54 L80 54", INK, 7) + stroke("M106 64 L102 48 L114 46", INK, 6),
        "road": rect(14, 14, 132, 132, 28, LEAF) + path("M62 14 L98 14 L134 146 L26 146 Z", GREY_DARK) + rect(76, 26, 8, 18, 4, WHITE) + rect(74, 62, 12, 24, 5, WHITE) + rect(72, 104, 16, 30, 6, WHITE),
        "station": rect(16, 46, 128, 14, 7, RED) + path("M10 50 L80 16 L150 50 Z", BERRY_DARK) + rect(28, 60, 10, 74, 5, GREY) + rect(122, 60, 10, 74, 5, GREY)
                   + circle(80, 82, 18, WHITE) + stroke("M80 82 L80 70 M80 82 L90 86", INK, 4) + rect(12, 132, 136, 12, 6, GREY_DARK),
        "airport": rect(64, 54, 32, 86, 8, CLOUD) + path("M44 54 L116 54 L104 30 L56 30 Z", SKY) + rect(50, 38, 60, 10, 4, SKY_PALE) + rect(76, 16, 8, 16, 4, RED)
                   + tri(122, 36, 12, WHITE, rot=90) + rect(110, 34, 22, 6, 3, WHITE) + rect(20, 130, 120, 10, 5, GREY),
        "passport": rect(34, 22, 92, 120, 12, NAVY) + circle(80, 72, 24, "none", f'stroke="{SUN}" stroke-width="5"') + stroke("M56 72 L104 72 M80 48 Q66 72 80 96 Q94 72 80 48", SUN, 3)
                    + rect(54, 108, 52, 8, 4, SUN) + hl(42, 30, 18, 6),
    }


def body():
    return {
        "head": circle(80, 78, 48, SKIN) + path("M32 72 Q32 22 80 24 Q128 22 128 72 Q100 52 32 72 Z", HAIR)
                + eyes(80, 82, 18, 5) + smile(80, 100, 10) + circle(30, 84, 9, SKIN_DARK) + circle(130, 84, 9, SKIN_DARK),
        "eye": ellipse(80, 80, 62, 36, WHITE) + ellipse(80, 80, 62, 36, "none", f'stroke="{SKIN_DARK}" stroke-width="6"') + circle(80, 80, 24, SKY) + circle(80, 80, 12, INK)
               + circle(72, 72, 6, WHITE) + stroke("M30 52 Q80 26 130 52", HAIR, 6),
        "ear": path("M60 30 Q122 26 118 82 Q114 116 92 122 Q78 126 76 136 Q60 140 56 124 Q40 80 60 30 Z", SKIN)
               + stroke("M74 54 Q100 50 98 78 Q96 96 80 96", SKIN_DARK, 8),
        "nose": path("M78 20 Q86 70 108 100 Q116 120 92 124 Q84 132 72 124 Q50 126 56 104 Q74 80 78 20 Z", SKIN) + ellipse(70, 112, 8, 5, SKIN_DARK) + ellipse(96, 112, 8, 5, SKIN_DARK) + hl(74, 40, 6, 22),
        "mouth": path("M24 76 Q50 50 80 64 Q110 50 136 76 Q110 92 80 88 Q50 92 24 76 Z", RED) + path("M24 78 Q80 90 136 78 Q110 124 80 122 Q50 124 24 78 Z", BERRY_DARK)
                 + rect(48, 82, 64, 10, 5, WHITE) + hl(54, 62, 18, 6),
        "hand": hand(80, 76, 1.35),
        "arm": stroke("M28 120 L80 116 L100 64", SKIN, 26) + circle(100, 56, 18, SKIN) + path("M60 112 Q80 88 100 100", "none", f'stroke="{SKIN_DARK}" stroke-width="3"')
               + rect(16, 102, 30, 36, 10, SKY) + ground(),
        "leg": rect(56, 16, 40, 96, 20, SKY_DARK) + rect(62, 100, 30, 26, 12, SKIN) + rect(48, 118, 64, 24, 12, RED) + rect(48, 134, 64, 8, 4, WHITE),
        "heart": heart(80, 76, 2.0, RED) + stroke("M26 82 L54 82 L64 64 L78 102 L90 74 L134 74", WHITE, 6),
        "tooth": path("M38 44 Q38 20 62 22 Q80 28 98 22 Q122 20 122 44 Q122 74 108 86 L102 130 Q96 140 90 130 L82 100 Q80 94 78 100 L70 130 Q64 140 58 130 L52 86 Q38 74 38 44 Z", WHITE)
                 + path("M38 44 Q38 20 62 22 Q80 28 98 22 Q122 20 122 44 Q122 74 108 86 L102 130 Q96 140 90 130 L82 100 Q80 94 78 100 L70 130 Q64 140 58 130 L52 86 Q38 74 38 44 Z", "none", f'stroke="{CLOUD}" stroke-width="5"')
                 + hl(52, 32, 18, 8) + ground(),
        "hair": path("M24 110 Q16 30 80 24 Q144 30 136 110 Q138 140 116 138 L44 138 Q22 140 24 110 Z", BROWN) + circle(80, 84, 38, SKIN)
                + path("M42 76 Q50 36 80 38 Q112 36 118 76 Q96 52 72 62 Q56 68 42 76 Z", BROWN) + eyes(80, 90, 14, 4) + smile(80, 104, 8),
        "back": rect(36, 70, 88, 70, 30, LEAF) + circle(80, 50, 30, SKIN) + path("M50 50 Q50 18 80 18 Q110 18 110 50 Q110 62 80 60 Q50 62 50 50 Z", HAIR)
                + stroke("M80 80 L80 132", LEAF_DARK, 4),
        "finger": rect(48, 70, 64, 66, 22, SKIN) + rect(70, 18, 22, 70, 11, SKIN) + rect(74, 22, 14, 14, 5, "#FBE3CC") + rect(50, 82, 20, 30, 10, SKIN_DARK, 'opacity="0.5"') + hl(56, 76, 16, 6),
        "knee": stroke("M30 40 L84 70", SKY_DARK, 32) + stroke("M84 70 L74 126", SKIN, 26) + circle(86, 74, 20, SKIN) + circle(90, 70, 8, SKIN_DARK, 'opacity="0.5"')
                 + rect(54, 122, 50, 18, 9, RED) + rect(54, 134, 50, 6, 3, WHITE),
        "doctor": person(80, 18, 1.25, WHITE, HAIR) + rect(78, 64, 4, 52, 2, CLOUD) + stroke("M62 66 Q60 100 80 104 Q100 100 98 66", GREY_DARK, 4) + circle(80, 106, 6, GREY) + rect(96, 92, 16, 10, 3, SKY) + ground(),
        "medicine": rect(26, 52, 36, 32, 15, RED, 'transform="rotate(-35 60 70)"') + rect(56, 52, 36, 32, 15, WHITE, 'transform="rotate(-35 60 70)"')
                    + rect(84, 58, 52, 78, 12, ORANGE) + rect(80, 46, 60, 18, 8, WHITE) + rect(94, 82, 32, 30, 6, WHITE) + rect(106, 86, 8, 22, 2, RED) + rect(99, 93, 22, 8, 2, RED) + ground(),
        "fever": circle(80, 82, 48, SKIN) + rect(40, 34, 80, 14, 7, SKY) + eyes(80, 80, 18, 4.5) + ellipse(60, 96, 10, 6, RED, 'opacity="0.45"') + ellipse(100, 96, 10, 6, RED, 'opacity="0.45"')
                 + rect(84, 100, 54, 12, 6, WHITE, 'transform="rotate(-25 84 106)"') + circle(86, 106, 8, RED) + path("M126 30 Q136 44 126 52 Q116 44 126 30 Z", SKY),
        "blood": path("M80 18 Q126 78 122 104 Q118 140 80 142 Q42 140 38 104 Q34 78 80 18 Z", RED) + hl(54, 88, 12, 26) + path("M80 104 Q98 126 80 132 Q66 126 72 112 Z", BERRY_DARK, 'opacity="0.4"'),
        "skin": rect(20, 52, 120, 70, 30, SKIN) + rect(20, 98, 120, 24, 12, SKIN_DARK, 'opacity="0.5"') + rect(46, 66, 68, 30, 12, "#F0D2AE", 'transform="rotate(-12 80 81)"')
                + rect(66, 70, 28, 22, 6, "#E2B989", 'transform="rotate(-12 80 81)"') + circle(54, 74, 2, SKIN_DARK) + circle(104, 92, 2, SKIN_DARK),
        "face": circle(80, 80, 56, SUN) + eyes(80, 70, 20, 7) + stroke("M50 92 Q80 124 110 92", INK, 7) + circle(46, 90, 9, ORANGE, 'opacity="0.5"') + circle(114, 90, 9, ORANGE, 'opacity="0.5"') + hl(46, 36, 26, 9),
    }


def nature():
    tree = lambda x, s, c=LEAF: rect(x - 6 * s, 96, 12 * s, 40 * s / 1.2, 5, BROWN) + circle(x, 74, 28 * s, c) + circle(x - 18 * s, 90, 18 * s, c) + circle(x + 18 * s, 90, 18 * s, c)
    return {
        "sun": "".join(tri(80 + 56 * math.cos(math.radians(a)), 80 + 56 * math.sin(math.radians(a)), 12, ORANGE, rot=a + 90) for a in range(0, 360, 30))
               + circle(80, 80, 40, SUN) + eyes(80, 76, 13, 4) + smile(80, 90, 8) + hl(56, 54, 20, 8),
        "moon": path("M100 22 A56 56 0 1 0 140 104 A44 44 0 0 1 100 22 Z", SUN) + circle(64, 92, 8, SUN_DARK, 'opacity="0.5"') + circle(50, 64, 5, SUN_DARK, 'opacity="0.5"') + circle(78, 120, 6, SUN_DARK, 'opacity="0.5"'),
        "star": path("M80 16 L96 56 L140 58 L106 86 L118 130 L80 106 L42 130 L54 86 L20 58 L64 56 Z", SUN, f'stroke="{SUN}" stroke-width="10" stroke-linejoin="round"')
                + eyes(80, 76, 12, 4) + smile(80, 88, 6),
        "rain": circle(54, 62, 24, MIST) + circle(84, 50, 30, MIST) + circle(112, 66, 22, MIST) + rect(30, 62, 104, 28, 14, MIST)
                + "".join(path(f"M{x} {y} Q{x + 8} {y + 14} {x} {y + 18} Q{x - 8} {y + 14} {x} {y} Z", SKY) for x, y in [(50, 104), (80, 112), (110, 102), (64, 128), (96, 128)]),
        "snow": "".join(stroke(f"M80 80 L{80 + 56 * math.cos(math.radians(a))} {80 + 56 * math.sin(math.radians(a))}", SKY, 9) for a in range(0, 360, 60))
                + "".join(stroke(f"M{80 + 34 * math.cos(math.radians(a)) + 14 * math.cos(math.radians(a + 60))} {80 + 34 * math.sin(math.radians(a)) + 14 * math.sin(math.radians(a + 60))} "
                                 f"L{80 + 34 * math.cos(math.radians(a))} {80 + 34 * math.sin(math.radians(a))} "
                                 f"L{80 + 34 * math.cos(math.radians(a)) + 14 * math.cos(math.radians(a - 60))} {80 + 34 * math.sin(math.radians(a)) + 14 * math.sin(math.radians(a - 60))}", SKY, 7)
                          for a in range(0, 360, 60)) + circle(80, 80, 10, SKY_PALE),
        "wind": stroke("M18 60 L100 60 Q124 60 122 40 Q118 24 102 30", SKY, 10) + stroke("M18 88 L120 88 Q142 88 140 108 Q136 126 118 118", SKY_DARK, 10) + stroke("M30 114 L80 114", SKY, 10),
        "cloud": circle(54, 84, 30, SKY_PALE) + circle(90, 66, 38, SKY_PALE) + circle(120, 88, 26, SKY_PALE) + rect(26, 84, 120, 36, 18, SKY_PALE)
                 + rect(26, 108, 120, 12, 6, "#B8E6FC") + rect(70, 40, 24, 9, 4.5, WHITE) + ground(86, 60),
        "tree": tree(80, 1.5) + hl(56, 46, 20, 8) + ground(),
        "flower": stroke("M80 140 L80 80", LEAF_DARK, 8) + path("M80 116 Q104 96 118 110 Q102 126 80 116 Z", LEAF)
                  + "".join(circle(80 + 26 * math.cos(math.radians(a)), 62 + 26 * math.sin(math.radians(a)), 20, PINK) for a in range(0, 360, 60)) + circle(80, 62, 18, SUN),
        "sea": rect(14, 14, 132, 132, 28, SKY_PALE) + path("M14 70 Q36 56 58 70 Q80 84 102 70 Q124 56 146 70 L146 146 L14 146 Z", SKY)
               + path("M14 102 Q36 88 58 102 Q80 116 102 102 Q124 88 146 102 L146 146 L14 146 Z", SKY_DARK) + circle(118, 40, 14, SUN),
        "river": rect(14, 14, 132, 132, 28, LEAF) + stroke("M60 14 Q20 60 80 80 Q140 100 100 146", SKY, 30) + stroke("M60 14 Q20 60 80 80 Q140 100 100 146", SKY_PALE, 4, 'stroke-dasharray="8 16"'),
        "mountain": tri(56, 92, 54, GREY, round_=0.15) + tri(108, 98, 44, GREY_DARK, round_=0.15) + tri(56, 58, 20, WHITE, round_=0.2) + tri(108, 74, 15, WHITE, round_=0.2)
                    + rect(10, 124, 140, 18, 9, LEAF),
        "forest": tree(40, 1.0, LEAF_DARK) + tree(120, 1.0, LEAF_DARK) + tree(80, 1.25, LEAF) + rect(12, 132, 136, 10, 5, LEAF_DARK),
        "desert": rect(14, 14, 132, 132, 28, "#FFE3B3") + circle(116, 44, 16, ORANGE) + path("M14 112 Q60 84 104 108 Q130 96 146 104 L146 146 L14 146 Z", SUN_DARK)
                  + rect(52, 54, 16, 64, 8, LEAF) + rect(34, 70, 12, 26, 6, LEAF) + rect(40, 88, 20, 10, 5, LEAF) + rect(74, 62, 12, 22, 6, LEAF) + rect(60, 80, 20, 10, 5, LEAF),
        "beach": rect(14, 14, 132, 132, 28, SKY_PALE) + rect(14, 74, 132, 30, 0, SKY) + path("M14 98 Q80 82 146 98 L146 146 L14 146 Z", "#FFE3A3")
                 + stroke("M104 128 L86 50", BROWN, 5) + path("M58 52 Q86 22 116 48 Z", RED) + path("M70 46 Q86 30 102 44 Z", WHITE, 'opacity="0.6"') + circle(40, 40, 14, SUN),
        "fire": path("M80 18 Q126 62 120 98 Q114 138 80 140 Q46 138 40 98 Q36 70 58 50 Q62 72 74 74 Q66 46 80 18 Z", ORANGE)
                + path("M80 68 Q104 96 100 112 Q96 132 80 132 Q64 132 60 112 Q58 96 80 68 Z", SUN) + rect(36, 132, 88, 12, 6, BROWN),
        "stone": ellipse(72, 102, 52, 34, GREY) + ellipse(112, 116, 30, 20, GREY_DARK) + ellipse(72, 118, 46, 14, GREY_DARK, 'opacity="0.5"') + hl(40, 80, 26, 9) + ground(),
        "sky": rect(14, 14, 132, 132, 28, SKY) + circle(50, 60, 18, WHITE) + circle(72, 52, 22, WHITE) + rect(34, 58, 64, 22, 11, WHITE)
               + circle(104, 106, 14, WHITE) + circle(122, 100, 16, WHITE) + rect(92, 104, 44, 16, 8, WHITE) + stroke("M40 108 Q46 102 52 108 Q58 102 64 108", INK, 3),
        "island": rect(14, 14, 132, 132, 28, SKY) + ellipse(80, 118, 52, 18, "#FFE3A3") + stroke("M80 116 Q76 80 90 50", BROWN, 8)
                  + path("M90 50 Q60 34 40 54 Q66 48 90 50 Z", LEAF) + path("M90 50 Q120 30 136 52 Q112 46 90 50 Z", LEAF) + path("M90 50 Q96 22 118 20 Q100 34 90 50 Z", LEAF_DARK)
                  + circle(90, 58, 6, BROWN_DARK),
        "lake": ellipse(80, 98, 66, 34, SKY) + ellipse(80, 96, 50, 22, SKY_PALE, 'opacity="0.5"') + stroke("M24 98 L20 56 M30 96 L32 62", LEAF_DARK, 5)
                + ellipse(20, 54, 4, 10, BROWN) + ellipse(32, 60, 4, 10, BROWN) + stroke("M60 98 Q70 92 80 98 Q90 92 100 98", WHITE, 3),
    }


def style():
    return {
        "red": blob(RED, BERRY_DARK), "blue": blob(SKY, SKY_DARK), "green": blob(LEAF, LEAF_DARK), "yellow": blob(SUN, SUN_DARK),
        "black": blob("#333333", "#111111"), "pink": blob(PINK, "#E05AA5"), "brown": blob(BROWN, BROWN_DARK), "gray": blob(GREY, GREY_DARK),
        "shirt": path("M54 24 L24 42 L36 70 L50 64 L50 138 L110 138 L110 64 L124 70 L136 42 L106 24 Q80 44 54 24 Z", SKY)
                 + path("M54 24 Q80 44 106 24 L96 22 Q80 34 64 22 Z", SKY_DARK) + "".join(circle(80, 60 + i * 20, 4, WHITE) for i in range(4)),
        "shoe": path("M20 108 Q18 70 40 64 Q60 60 70 76 Q100 86 132 96 Q144 102 140 116 L20 116 Z", RED) + rect(18, 112, 126, 16, 8, WHITE)
                + stroke("M52 74 L60 70 M60 82 L68 78 M70 88 L78 84", WHITE, 4) + hl(30, 74, 16, 6) + ground(),
        "hat": rect(48, 30, 64, 80, 10, INK) + rect(48, 88, 64, 14, 0, RED) + rect(20, 104, 120, 18, 9, INK) + hl(56, 36, 10, 26) + ground(),
        "dress": path("M62 20 L98 20 L102 60 L134 136 L26 136 L58 60 Z", PINK) + rect(54, 56, 52, 12, 6, "#E05AA5") + path("M62 20 Q80 34 98 20", "none", f'stroke="#E05AA5" stroke-width="5"')
                 + circle(60, 108, 5, WHITE) + circle(86, 96, 5, WHITE) + circle(104, 118, 5, WHITE),
        "coat": path("M52 20 L30 36 L26 136 L134 136 L130 36 L108 20 L80 40 Z", BROWN) + path("M52 20 L80 40 L64 70 Z", BROWN_DARK) + path("M108 20 L80 40 L96 70 Z", BROWN_DARK)
                + stroke("M80 40 L80 136", BROWN_DARK, 4) + circle(90, 80, 5, SUN) + circle(90, 104, 5, SUN) + rect(34, 96, 22, 8, 4, BROWN_DARK),
        "skirt": rect(46, 28, 68, 18, 9, GRAPE_DARK) + path("M48 42 L112 42 L136 132 L24 132 Z", GRAPE) + stroke("M66 46 L56 128 M94 46 L104 128 M80 46 L80 128", GRAPE_DARK, 4),
        "sock": path("M56 16 L100 16 L100 92 Q100 108 112 112 Q140 120 136 136 Q132 146 106 142 L66 134 Q52 130 56 112 Z", WHITE, OUT_LINE)
                + rect(56, 16, 44, 20, 6, RED) + rect(56, 46, 44, 8, 4, SKY) + rect(56, 60, 44, 8, 4, SKY) + path("M110 112 Q140 120 136 136 Q132 146 106 142 L104 116 Z", RED),
        "glove": rect(46, 60, 64, 72, 22, SKY) + "".join(rect(48 + i * 15, 26 + abs(i - 1.5) * 8, 14, 50, 7, SKY) for i in range(4))
                 + rect(98, 74, 16, 40, 8, SKY, 'transform="rotate(-35 106 94)"') + rect(42, 118, 72, 22, 10, SKY_DARK),
        "belt": rect(10, 66, 140, 28, 8, BROWN) + rect(58, 58, 44, 44, 10, SUN) + rect(68, 68, 24, 24, 5, BROWN) + rect(78, 64, 6, 22, 3, SUN_DARK)
                + "".join(circle(x, 80, 4, BROWN_DARK) for x in (114, 126, 138)),
        "pocket": rect(14, 14, 132, 132, 28, SKY_DARK) + path("M36 44 L124 44 L124 108 L80 132 L36 108 Z", SKY)
                  + path("M44 52 L116 52 L116 102 L80 122 L44 102 Z", "none", f'stroke="{SUN}" stroke-width="3" stroke-dasharray="6 6"'),
        "button": circle(80, 80, 52, RED) + circle(80, 80, 40, BERRY_DARK, 'opacity="0.4"') + circle(66, 66, 7, WHITE) + circle(94, 66, 7, WHITE) + circle(66, 94, 7, WHITE)
                  + circle(94, 94, 7, WHITE) + hl(46, 40, 22, 8),
        "scarf": rect(30, 40, 100, 34, 17, RED) + rect(84, 60, 30, 76, 12, RED) + "".join(rect(84, 82 + i * 18, 30, 8, 0, WHITE) for i in range(3))
                 + "".join(rect(36 + i * 22, 44, 8, 26, 0, WHITE) for i in range(4)) + "".join(rect(86 + i * 8, 134, 4, 10, 2, RED) for i in range(4)),
    }


WORLDS = {"basics": basics, "food": food, "animals": animals, "home": home, "travel": travel,
          "body": body, "nature": nature, "style": style}


def main():
    vocab = json.load(open(os.path.join(ROOT, "data", "vocab.json")))
    missing = []
    count = 0
    for w in vocab["worlds"]:
        art = WORLDS[w["id"]]()
        folder = os.path.join(OUT, w["id"])
        os.makedirs(folder, exist_ok=True)
        for row in w["words"]:
            en = row[1]
            if en not in art:
                missing.append(f'{w["id"]}:{en}')
                continue
            f = os.path.join(folder, en + ".svg")
            open(f, "w").write(svg(160, 160, art[en]))
            open(f + ".import", "w").write('[remap]\n\nimporter="keep"\n')
            count += 1
    print(f"{count} word illustrations written")
    if missing:
        print("MISSING:", ", ".join(missing))
        sys.exit(1)


if __name__ == "__main__":
    main()
