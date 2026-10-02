"""Kakuro UI recreated in skia-python from the Godot project's source.

Every colour, size and layout rule here is taken from the game's scripts:
  scripts/autoload/palette.gd   (LIGHT palette, the default theme)
  scripts/ui/board_view.gd      (board, tiles, clue cells, pop/sweep/win animations)
  scripts/ui/combo_panel.gd     (combination helper)
  scripts/ui/number_pad.gd      (digit keys)
  scripts/ui/icon_button.gd     (tool "coins")
  scripts/ui/icons.gd           (vector icons on a 24x24 grid)
  scripts/ui/mascot.gd + kaku_shape.gd + assets/kaku/*.png (Kaku)
  scripts/ui/title_logo.gd, scripts/ui/win_stars.gd, scripts/ui/star_meter.gd
  scripts/screens/game_screen.gd (screen layout, win card)
Coordinates are the game's 720x1280 portrait viewport.
"""
import itertools
import json
import math
import os

import skia

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")


# ------------------------------------------------------------------ colours

def C(h, a=1.0):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r / 255.0, g / 255.0, b / 255.0, a)


def lerp(a, b, t):
    return a + (b - a) * t


def lerpc(c1, c2, t):
    return tuple(lerp(c1[i], c2[i], t) for i in range(4))


def alpha(c, a):
    return (c[0], c[1], c[2], c[3] * a)


def darkened(c, k):
    return (c[0] * (1 - k), c[1] * (1 - k), c[2] * (1 - k), c[3])


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


# palette.gd LIGHT (the default: GameData "dark": false)
P = {k: C(v) for k, v in {
    "bg": "ffffff", "bg2": "f7f7f7", "surface": "ffffff", "surface2": "f7f7f7",
    "line": "e5e5e5", "text": "4b4b4b", "muted": "777777", "disabled": "afafaf",
    "accent": "1cb0f6", "accent2": "58cc02", "error": "ff4b4b", "success": "58cc02",
    "primary": "58cc02", "primary_lip": "58a700", "board_bg": "ffffff",
    "block": "1cb0f6", "block_blank": "efefef", "block_text": "ffffff", "clue_line": "a5e0fb",
    "cell": "ffffff", "cell_hl": "eaf8ff", "cell_same": "c9eeff", "cell_text": "4b4b4b",
    "lip": "e5e5e5", "gold": "ffc800", "gold_lip": "e5a500", "board_lip": "e5e5e5",
    "block_lip": "1899d6", "cell_lip": "e5e5e5", "key": "ffffff", "key_lip": "e5e5e5",
    "key_ink": "4b4b4b", "sel": "ddf4ff", "sel_lip": "84d8ff", "sel_ink": "1899d6",
    "orange": "ff9600", "purple": "ce82ff",
}.items()}

# ------------------------------------------------------------------ fonts

_tf = {}


def typeface(w):
    if w not in _tf:
        name = {"semi": "Nunito-SemiBold.ttf", "bold": "Nunito-Bold.ttf", "xbold": "Nunito-ExtraBold.ttf"}[w]
        _tf[w] = skia.Typeface.MakeFromFile(os.path.join(A, "fonts", name))
    return _tf[w]


_fonts = {}


def font(w, size):
    k = (w, round(size * 4) / 4)
    if k not in _fonts:
        f = skia.Font(typeface(w), k[1])
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setSubpixel(True)
        _fonts[k] = f
    return _fonts[k]


def paint(col, stroke=None, aa=True):
    p = skia.Paint(AntiAlias=aa, Color4f=skia.Color4f(*col))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def text_w(w, size, s):
    return font(w, size).measureText(s)


def asc_desc(w, size):
    m = font(w, size).getMetrics()
    return -m.fAscent, m.fDescent


def draw_text(c, s, x, y, w, size, col):
    """Baseline-positioned text (Godot draw_string)."""
    if col[3] <= 0.003:
        return
    c.drawString(s, x, y, font(w, size), paint(col))


def text_centered(c, s, cx, cy, w, size, col, scale=1.0):
    """board_view._centered: centred on (cx, cy) using ascent/descent."""
    a, d = asc_desc(w, size)
    tw = text_w(w, size, s)
    if scale != 1.0:
        c.save()
        c.translate(cx, cy)
        c.scale(scale, scale)
        c.translate(-cx, -cy)
    draw_text(c, s, cx - tw / 2.0, cy + (a - d) / 2.0, w, size, col)
    if scale != 1.0:
        c.restore()


def text_left_center(c, s, x, cy, w, size, col):
    a, d = asc_desc(w, size)
    draw_text(c, s, x, cy + (a - d) / 2.0, w, size, col)


def rrect(c, x, y, w, h, r, col):
    if col[3] <= 0.003 or w <= 0 or h <= 0:
        return
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint(col))


def rrect_stroke(c, x, y, w, h, r, col, sw):
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint(col, sw))


def poly(c, pts, col):
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    path.close()
    c.drawPath(path, paint(col))


def polyline(c, pts, col, w):
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    c.drawPath(path, paint(col, w))


# ------------------------------------------------------------------ easing (motion.gd)

def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def in_out_sine(t):
    t = clamp(t)
    return -(math.cos(math.pi * t) - 1) / 2


def bump(t):
    if t <= 0 or t >= 1:
        return 0.0
    return math.sin(t * math.pi)


def drop(t):
    """TitleLogo._drop: back-out easing."""
    t = clamp(t)
    c1 = 1.9
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def smoothstep(a, b, x):
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ puzzle (core/puzzle.gd)

class Puzzle:
    ACROSS, DOWN = 0, 1

    def __init__(self, code):
        w, cells = code.split("|")[0].split(":")[:2]
        self.w = int(w)
        self.h = len(cells) // self.w
        n = self.w * self.h
        self.block = [1 if ch == "#" else 0 for ch in cells]
        self.solution = [0 if ch == "#" else int(ch) for ch in cells]
        self.across = [0] * n
        self.down = [0] * n
        self.run_a = [-1] * n
        self.run_d = [-1] * n
        self.runs = []
        for i in range(n):
            if not self.block[i]:
                continue
            x, y = i % self.w, i // self.w
            if x + 1 < self.w and not self.block[i + 1]:
                cs = []
                j = i + 1
                while j % self.w != 0 and not self.block[j]:
                    cs.append(j)
                    j += 1
                s = sum(self.solution[k] for k in cs)
                self.across[i] = s
                for k in cs:
                    self.run_a[k] = len(self.runs)
                self.runs.append({"cells": cs, "sum": s, "dir": 0, "clue": i})
            if y + 1 < self.h and not self.block[i + self.w]:
                cs = []
                j = i + self.w
                while j < n and not self.block[j]:
                    cs.append(j)
                    j += self.w
                s = sum(self.solution[k] for k in cs)
                self.down[i] = s
                for k in cs:
                    self.run_d[k] = len(self.runs)
                self.runs.append({"cells": cs, "sum": s, "dir": 1, "clue": i})
        self.white = [i for i in range(n) if not self.block[i]]

    def idx(self, x, y):
        return y * self.w + x


def load_bank():
    out = {}
    sec = None
    for line in open(os.path.join(A, "puzzle_bank.txt")):
        line = line.strip()
        if line.startswith("["):
            sec = int(line[1:-1])
            out[sec] = []
        elif line:
            out[sec].append(line)
    return out


def combos(n, s):
    out = []
    for comb in itertools.combinations(range(1, 10), n):
        if sum(comb) == s:
            m = 0
            for d in comb:
                m |= 1 << (d - 1)
            out.append(m)
    return out


def mask_str(m):
    return "".join(str(d + 1) for d in range(9) if m & (1 << d))


# ------------------------------------------------------------------ board state from a timeline

class BoardState:
    """Replays timed events: ('sel', t, cell) ('put', t, cell, digit[, revealed])
    ('win', t) ('intro', t). Everything the board draws is derived from it, as
    BoardView derives its animations from diffing GameState."""

    def __init__(self, puzzle, events, prefill=None):
        self.p = puzzle
        self.events = sorted(events, key=lambda e: e[1])
        self.prefill = prefill or {}

    def at(self, t):
        p = self.p
        vals = [0] * len(p.block)
        revealed = set()
        for k, v in self.prefill.items():
            vals[k] = v
        sel, sel_t0, prev_sel = -1, -10.0, -1
        pops, sweeps, completed = {}, {}, {}
        win_t0, intro_t0 = -10.0, -10.0

        def run_ok(r):
            cs = p.runs[r]["cells"]
            vs = [vals[c] for c in cs]
            return all(vs) and sum(vs) == p.runs[r]["sum"] and len(set(vs)) == len(vs)

        for r in range(len(p.runs)):
            if run_ok(r):
                completed[r] = -10.0
        for e in self.events:
            if e[1] > t:
                break
            if e[0] == "sel":
                prev_sel, sel, sel_t0 = sel, e[2], e[1]
            elif e[0] == "put":
                vals[e[2]] = e[3]
                if len(e) > 4 and e[4]:
                    revealed.add(e[2])
                pops[e[2]] = e[1]
                for r in (p.run_a[e[2]], p.run_d[e[2]]):
                    if r >= 0 and r not in completed and run_ok(r):
                        completed[r] = e[1]
                        sweeps[r] = e[1]
            elif e[0] == "win":
                win_t0 = e[1]
            elif e[0] == "intro":
                intro_t0 = e[1]
        return dict(vals=vals, sel=sel, sel_t0=sel_t0, prev_sel=prev_sel, pops=pops,
                    sweeps=sweeps, completed=completed, win_t0=win_t0, intro_t0=intro_t0,
                    revealed=revealed)


# ------------------------------------------------------------------ icons (icons.gd)

def icon(c, kind, x, y, size, col, stroke=2.0):
    s = size / 24.0
    w = stroke * s

    def Pt(px, py):
        return (x + px * s, y + py * s)

    if kind == "back":
        polyline(c, [Pt(15, 5), Pt(8, 12), Pt(15, 19)], col, w)
    elif kind in ("forward", "across"):
        polyline(c, [Pt(9, 5), Pt(16, 12), Pt(9, 19)], col, w)
    elif kind == "down":
        polyline(c, [Pt(5, 9), Pt(12, 16), Pt(19, 9)], col, w)
    elif kind == "undo":
        pts = [Pt(6, 9), Pt(14, 9)]
        for k in range(17):
            a = -math.pi / 2 + math.pi * k / 16.0
            pts.append(Pt(14 + math.cos(a) * 5, 14 + math.sin(a) * 5))
        pts.append(Pt(9, 19))
        polyline(c, pts, col, w)
        polyline(c, [Pt(9.5, 5.5), Pt(6, 9), Pt(9.5, 12.5)], col, w)
    elif kind == "erase":
        polyline(c, [Pt(9, 5.5), Pt(20.5, 5.5), Pt(20.5, 18.5), Pt(9, 18.5), Pt(3.5, 12), Pt(9, 5.5)], col, w)
        polyline(c, [Pt(11.5, 9), Pt(17, 15)], col, w)
        polyline(c, [Pt(17, 9), Pt(11.5, 15)], col, w)
    elif kind == "notes":
        polyline(c, [Pt(4, 20), Pt(5, 15), Pt(15.5, 4.5), Pt(19.5, 8.5), Pt(9, 19), Pt(4, 20)], col, w)
        polyline(c, [Pt(13, 7), Pt(17, 11)], col, w)
    elif kind == "hint":
        arc = []
        for k in range(25):
            a = math.radians(135 + 270.0 * k / 24.0)
            arc.append(Pt(12 + math.cos(a) * 6.5, 10 + math.sin(a) * 6.5))
        polyline(c, arc, col, w)
        polyline(c, [Pt(9.4, 14.6), Pt(9.4, 18)], col, w)
        polyline(c, [Pt(14.6, 14.6), Pt(14.6, 18)], col, w)
        polyline(c, [Pt(9.4, 18), Pt(14.6, 18)], col, w)
        polyline(c, [Pt(10.5, 21), Pt(13.5, 21)], col, w)
    elif kind == "check":
        polyline(c, [Pt(4.5, 12.5), Pt(9.5, 17.5), Pt(19.5, 6.5)], col, w * 1.1)
    elif kind == "pause":
        polyline(c, [Pt(9, 6), Pt(9, 18)], col, w * 1.25)
        polyline(c, [Pt(15, 6), Pt(15, 18)], col, w * 1.25)


def star_pts(cx, cy, r, inner=0.5):
    pts = []
    for k in range(10):
        ang = -math.pi / 2.0 + k * math.pi / 5.0
        rr = r if k % 2 == 0 else r * inner
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    return pts


# ------------------------------------------------------------------ board (board_view.gd)

T_SEL, T_POP, T_SWEEP, T_SWEEP_CELL, T_PULSE, T_INTRO, WIN_LEN = 0.14, 0.36, 0.22, 0.26, 0.45, 0.26, 1.4
BOARD_LIP = 9.0


def board_geometry(p, area):
    ax, ay, aw, ah = area
    pad = 10.0
    fit = math.floor(min((aw - pad * 2) / p.w, (ah - pad * 2 - BOARD_LIP) / p.h))
    fit = min(fit, 150.0)
    cell = fit
    bw, bh = p.w * cell, p.h * cell
    ox = math.floor(ax + (aw - bw) / 2.0)
    oy = math.floor(ay + (ah - BOARD_LIP - bh) / 2.0)
    return cell, ox, oy


def cell_center(p, area, i):
    cell, ox, oy = board_geometry(p, area)
    return ox + (i % p.w + 0.5) * cell, oy + (i // p.w + 0.5) * cell


def _tile(c, r, face, lipc, radius, cell):
    x, y, w, h = r
    lh = max(3.0, round(cell * 0.07))
    fr = (x, y, w, h - lh)
    if lum(face) > 0.75:
        rrect(c, x, y, w, h, radius, lipc)
        rrect(c, x + 2, y + 2, w - 4, h - lh - 4, max(1, radius - 2), face)
    else:
        rrect(c, x, y + lh, w, h - lh, radius, lipc)
        rrect(c, x, y, w, h - lh, radius, face)
    return fr


def _sweep_amount(p, st, r, cell_i, t):
    cells = p.runs[r]["cells"]
    n = len(cells)
    k = cells.index(cell_i)
    off = T_SWEEP * k / max(1, n - 1)
    return bump((t - st["sweeps"][r] - off) / T_SWEEP_CELL)


def draw_board(c, p, st, area, t, show_fade=True):
    vals = st["vals"]
    sel = st["sel"]
    cell, ox, oy = board_geometry(p, area)
    gap = max(2.0, round(cell * 0.06))
    radius = int(max(3.0, cell * 0.14))
    it = clamp((t - st["intro_t0"]) / T_INTRO)
    ik = out_cubic(it)
    a_all = ik if it < 1.0 else 1.0
    c.save()
    if it < 1.0:
        s = lerp(0.96, 1.0, ik)
        cx, cy = area[0] + area[2] / 2, area[1] + area[3] / 2
        c.translate(cx, cy)
        c.scale(s, s)
        c.translate(-cx, -cy)
    bw, bh = p.w * cell, p.h * cell
    pr = (ox - gap, oy - gap, bw + gap * 2, bh + gap * 2)
    rrect(c, pr[0] - 2, pr[1] - 2, pr[2] + 4, pr[3] + 4 + BOARD_LIP, radius * 1.8, alpha(P["board_lip"], a_all))
    rrect(c, *pr, radius * 1.8, alpha(P["board_bg"], a_all))

    def runs_of(i):
        if i < 0 or p.block[i]:
            return (-1, -1)
        return (p.run_a[i], p.run_d[i])

    sel_runs = runs_of(sel)
    prev_runs = runs_of(st["prev_sel"])
    sel_k = out_cubic((t - st["sel_t0"]) / T_SEL)
    sel_val = vals[sel] if sel >= 0 else 0
    clue_fs = int(cell * 0.27)
    val_fs = int(cell * 0.56)
    wt = t - st["win_t0"]
    win_on = 0 <= wt < WIN_LEN
    glow = 0.0
    if win_on:
        glow = clamp((wt - 0.12) / 0.33) * (1.0 - clamp((wt - 1.05) / 0.35))
        glow = in_out_sine(glow) * 0.22

    def clue_color(r, sel_run, prev_run):
        col = P["block_text"]
        if show_fade and r in st["completed"]:
            f = clamp((t - st["completed"][r] - T_PULSE) / 0.16) if st["completed"][r] > -5 else 1.0
            col = alpha(col, lerp(1.0, 0.32, f))
        ak = 0.0
        if r == sel_run and r == prev_run:
            ak = 1.0
        elif r == sel_run:
            ak = sel_k
        elif r == prev_run:
            ak = 1.0 - sel_k
        if ak > 0:
            col = lerpc(col, P["gold"], ak)
        if r in st["sweeps"]:
            pp = bump((t - st["sweeps"][r]) / T_PULSE)
            if pp > 0:
                a0 = col[3]
                col = lerpc(col, P["success"], pp * 0.9)
                col = (col[0], col[1], col[2], max(a0, lerp(a0, 1.0, pp)))
        return col

    for y in range(p.h):
        for x in range(p.w):
            i = y * p.w + x
            rx, ry = ox + x * cell + gap / 2, oy + y * cell + gap / 2
            r = (rx, ry, cell - gap, cell - gap)
            if p.block[i]:
                a, d = p.across[i], p.down[i]
                if a == 0 and d == 0:
                    rrect(c, rx + 1, ry + 1, cell - gap - 2, cell - gap - 2, radius, alpha(P["block_blank"], a_all * 0.85))
                    continue
                fr = _tile(c, r, alpha(P["block"], a_all), alpha(P["block_lip"], a_all), radius, cell)
                ins = cell * 0.1
                polyline(c, [(fr[0] + ins, fr[1] + ins), (fr[0] + fr[2] - ins, fr[1] + fr[3] - ins)],
                         alpha(P["clue_line"], a_all), max(1.5, cell * 0.03))
                if a > 0:
                    col = clue_color(p.run_a[i + 1], sel_runs[0], prev_runs[0])
                    text_centered(c, str(a), fr[0] + fr[2] * 0.70, fr[1] + fr[3] * 0.31, "xbold", clue_fs, alpha(col, a_all))
                if d > 0:
                    col = clue_color(p.run_d[i + p.w], sel_runs[1], prev_runs[1])
                    text_centered(c, str(d), fr[0] + fr[2] * 0.31, fr[1] + fr[3] * 0.71, "xbold", clue_fs, alpha(col, a_all))
                continue
            ra, rd = p.run_a[i], p.run_d[i]
            in_new = ra == sel_runs[0] or rd == sel_runs[1]
            in_old = ra == prev_runs[0] or rd == prev_runs[1]
            hl = 1.0 if (in_new and in_old) else (sel_k if in_new else (1.0 - sel_k if in_old else 0.0))
            bg = lerpc(P["cell"], P["cell_hl"], hl)
            v = vals[i]
            if v > 0 and sel_val > 0 and v == sel_val and i != sel:
                bg = lerpc(bg, P["cell_same"], sel_k)
            for rr in (ra, rd):
                if rr in st["sweeps"]:
                    bg = lerpc(bg, P["success"], _sweep_amount(p, st, rr, i, t) * 0.32)
            lipc = P["cell_lip"]
            cr = r
            if i == sel:
                sk2 = lerp(0.7, 1.0, sel_k)
                bg = lerpc(bg, P["sel"], sk2)
                lipc = lerpc(lipc, P["sel_lip"], sk2)
                g = -3.0 * (1.0 - sel_k)
                cr = (r[0] - g, r[1] - g, r[2] + 2 * g, r[3] + 2 * g)
            elif i == st["prev_sel"] and sel_k < 1.0:
                bg = lerpc(bg, P["sel"], 1.0 - sel_k)
                lipc = lerpc(lipc, P["sel_lip"], 1.0 - sel_k)
            wave = 0.0
            if win_on:
                bg = lerpc(bg, P["sel"], glow)
                diag = (x + y) / float(p.w + p.h - 2)
                wave = bump((wt - 0.35 - diag * 0.45) / 0.3)
                bg = lerpc(bg, P["sel"], wave * 0.8)
                lipc = lerpc(lipc, P["sel_lip"], wave * 0.8)
            bg = alpha(bg, a_all)
            lipc = alpha(lipc, a_all)
            fr = _tile(c, cr, bg, lipc, radius, cell)
            cx, cy = fr[0] + fr[2] / 2, fr[1] + fr[3] / 2
            if v > 0:
                col = P["accent2"] if i in st["revealed"] else P["cell_text"]
                if i == sel:
                    col = P["sel_ink"]
                if win_on and wave > 0:
                    col = lerpc(col, P["sel_ink"], wave)
                col = alpha(col, a_all)
                s = 1.0
                if i in st["pops"]:
                    pt = clamp((t - st["pops"][i]) / T_POP)
                    col = alpha(col, out_cubic(pt / 0.3))
                    s = lerp(0.4, 1.0, drop(pt * 1.4))
                    spk = alpha(P["gold"], (1.0 - pt))
                    for q in range(6):
                        ang = math.tau * q / 6.0 + float(i % 7)
                        dist = cell * (0.32 + 0.38 * out_cubic(pt))
                        sx, sy = cx + math.cos(ang) * dist, cy + math.sin(ang) * dist
                        sz = cell * 0.05 * (1.0 - pt)
                        if sz >= 0.25 and pt < 1:
                            poly(c, [(sx, sy - sz * 1.6), (sx + sz, sy), (sx, sy + sz * 1.6), (sx - sz, sy)], spk)
                text_centered(c, str(v), cx, cy, "xbold", val_fs, col, s)
    c.restore()


# ------------------------------------------------------------------ Kaku (mascot.gd at rest, turn 0)

_img = {}


def img(name):
    if name not in _img:
        _img[name] = skia.Image.open(os.path.join(A, name))
    return _img[name]


KAKU_BODY = [tuple(q) for q in json.load(open(os.path.join(A, "kaku_body.json")))]
ART = (600.0, 656.0)
ANCHOR = (300.0, 570.0)
FEET_Y = 640.0
EYES = [(218.0, 296.0), (382.0, 296.0)]
BROWS = [(218.0, 222.0), (382.0, 222.0)]
MOUTH = (300.0, 382.0)
PIVOT_L, PIVOT_R = (100.0, 372.0), (500.0, 372.0)
TILE_C = (300.0, 474.0)
BELLY, BELLY_R = (294.0, 500.0), (132.0, 108.0)
SIDE_R = 30.0          # _sr at rest: SIDE_DEPTH * sin(-REST_ANGLE) = 30
FL, FR = 94.0, 476.0   # front face edges at rest


def _po(x):
    return FL + (FR - FL) * (x - 94.0) / (506.0 - 94.0)


def _px(x):
    return FL + (FR - FL) * (x - 94.0) / (476.0 - 94.0)


def hop_curve(p):
    HOP = 0.95
    if p < 0 or p >= 1:
        return 0.0, 1.0
    t = p * HOP
    if t < 0.14:
        return 0.0, 1.0 - 0.08 * in_out_sine(t / 0.14)
    if t < 0.56:
        k2 = (t - 0.14) / 0.42
        return 4 * k2 * (1 - k2), 1.0 + 0.06 * max(0.0, 1.0 - k2 * 2.2)
    if t < 0.64:
        k3 = (t - 0.56) / 0.08
        return 0.0, 1.0 - 0.09 * math.sin(k3 * math.pi * 0.5)
    k4 = (t - 0.64) / (HOP - 0.64)
    return 0.0, 1.0 - 0.09 * math.exp(-4 * k4) * math.cos(k4 * math.pi * 2)


def _mouth(c, w, opn, smile, skew):
    n = 16
    top = []
    for i in range(n + 1):
        u = -1.0 + 2.0 * i / n
        top.append((MOUTH[0] + u * w, MOUTH[1] + smile * (1 - u * u) * 0.6 - smile * 0.35 + skew * u))
    ink = C("1f2a2e")
    if opn < 2.5:
        polyline(c, top, ink, 8.0)
        return
    bottom = []
    for i in range(n, -1, -1):
        u = -1.0 + 2.0 * i / n
        px, py = top[i]
        bottom.append((px, py + opn * math.sqrt(max(0.0, 1 - abs(u) ** 2.4))))
    poly(c, top + bottom, ink)
    if opn > 14:
        teeth = [(top[i][0], top[i][1] + 2) for i in range(3, n - 2)] + \
                [(top[i][0], top[i][1] + 9) for i in range(n - 3, 2, -1)]
        poly(c, teeth, (1, 1, 1, 1))


def draw_kaku(c, box, t, mood="idle", hop_t0=-10.0, hop_h=1.0, arms=0.0, digit=7, blink_t0=None, look=(0.0, 0.0)):
    """Kaku at its resting turn: shadow, feet, arms, body (side plane, front,
    belly, clue corner 16/7), belly tile, eyes (or happy ^ ^ eyes), brows, mouth."""
    bx, by, bw, bh = box
    s = min(bw / ART[0], (bh - 10.0) / ART[1])
    foot = (bx + bw / 2.0, by + bh - 8.0)
    happy = mood == "happy"
    breath = math.sin(t * 2.3)
    squash = 1.0 + breath * 0.011
    lift, hsq = hop_curve((t - hop_t0) / 0.95)
    lift *= hop_h
    squash *= lerp(1.0, hsq, clamp(hop_h, 0.4, 1.0))
    lift_px = lift * ART[1] * 0.13 * s
    # shadow
    sw = 1.0 - lift * 0.35
    c.drawOval(skia.Rect.MakeXYWH(foot[0] - ART[0] * 0.3 * s * sw, foot[1] + 1 - 9 * sw, 2 * ART[0] * 0.3 * s * sw, 18 * sw),
               paint((0, 0, 0, 0.08 * (1.0 - lift * 0.5))))
    # feet
    feet_lift = max(0.0, lift_px - 6.0 * s)
    c.save()
    c.translate(foot[0], foot[1] - feet_lift)
    c.scale(s, s)
    c.translate(-ANCHOR[0], -FEET_Y)
    for f in ("foot_r.png", "foot_l.png"):
        c.drawImage(img("kaku/" + f), 0, 0)
    c.restore()
    # body group
    sy = s * squash
    sx = s / math.sqrt(squash)
    bp = (foot[0], foot[1] + (ANCHOR[1] - FEET_Y) * s - lift_px)
    c.save()
    c.translate(*bp)
    c.scale(sx, sy)
    c.translate(-ANCHOR[0], -ANCHOR[1])
    # arms (behind the body at rest); raise 0 hangs, ~1.2 out, ~2 a "V"
    for tex, piv, ang in (("wing_l.png", PIVOT_L, arms), ("wing_r.png", PIVOT_R, -arms)):
        c.save()
        c.translate(*piv)
        c.rotate(math.degrees(ang))
        c.translate(-piv[0], -piv[1])
        c.drawImage(img("kaku/" + tex), 0, 0)
        c.restore()
    front = [(_po(x), y) for x, y in KAKU_BODY]
    back = [(x + SIDE_R, y) for x, y in front]
    poly(c, back, C("46a302"))
    poly(c, front, C("58cc02"))
    fpath = skia.Path()
    fpath.moveTo(*front[0])
    for q in front[1:]:
        fpath.lineTo(*q)
    fpath.close()
    c.save()
    c.clipPath(fpath, doAntiAlias=True)
    belly = [(_px(BELLY[0] + math.cos(math.tau * k / 48) * BELLY_R[0]), BELLY[1] + math.sin(math.tau * k / 48) * BELLY_R[1]) for k in range(48)]
    poly(c, belly, C("89e219"))
    poly(c, [(_px(340), 90), (_px(620), 90), (_px(620), 391)], C("3b8c02"))
    polyline(c, [(_px(340), 90), (_px(620), 391)], (1, 1, 1, 1), 6.0)
    c.restore()
    draw_text(c, "16", _px(412), 158, "xbold", 27, (1, 1, 1, 1))
    draw_text(c, "7", _px(362), 182, "xbold", 27, (1, 1, 1, 1))
    # belly tile + digit
    tc = (_px(TILE_C[0]), TILE_C[1])
    c.save()
    c.translate(*tc)
    c.rotate(math.degrees(-0.052))
    rrect(c, -50, -50, 100, 100, 16, (1, 1, 1, 1))
    c.restore()
    text_centered(c, str(digit), tc[0], tc[1], "xbold", 66, C("58a700"))
    # face
    c.save()
    c.translate(look[0] * 0.14, look[1] * 0.14)
    close = 0.0
    if blink_t0 is not None:
        bt = t - blink_t0
        if 0 <= bt < 0.17:
            close = clamp(bt / 0.07 if bt < 0.07 else 1.0 - (bt - 0.07) / 0.1)
    if happy:
        c.drawImage(img("kaku/eyes_happy.png"), 0, 0)
    else:
        for k in range(2):
            e = EYES[k]
            c.save()
            c.translate(e[0], e[1])
            c.scale(1.0, 1.0 - close * 0.12)
            c.translate(-e[0], -e[1])
            c.drawImage(img("kaku/eye_%s.png" % "lr"[k]), e[0] - 90, e[1] - 90)
            pc = (e[0] + look[0], e[1] + 5 + look[1])
            c.drawImage(img("kaku/iris.png"), pc[0] - 64, pc[1] - 64)
            c.drawImage(img("kaku/glint.png"), pc[0] - 64, pc[1] - 64)
            c.drawImage(img("kaku/lidrest_%s.png" % "lr"[k]), e[0] - 90, e[1] - 90)
            if close > 0.02:
                top = 90.0 - (54.0 + 8.0)
                c.save()
                c.translate(e[0] - 90, e[1] - 90 + top * (1 - close))
                c.scale(1.0, close)
                c.drawImage(img("kaku/lid_%s.png" % "lr"[k]), 0, 0)
                c.restore()
            c.restore()
    for k in range(2):
        bc = [BROWS[k][0], BROWS[k][1] + min(0.0, look[1]) * 0.35 + close * 5]
        if happy:
            bc[1] -= 12
        c.drawImage(img("kaku/brow_%s.png" % "lr"[k]), bc[0] - 55, bc[1] - 30)
    if happy:
        op = 20.0 + 8.0 * lift
        _mouth(c, 40.0, op, 10.0, -3.0)
    else:
        _mouth(c, 30.0, 0.0, 7.0, -6.0)
    c.restore()
    c.restore()


# ------------------------------------------------------------------ widgets

def draw_chunk(c, x, y, w, h, face, lipc, lip, rad, k=0.0):
    """PressCard.draw_chunk: lip behind, face on top (light faces outlined)."""
    dy = lip * k
    rrect(c, x, y + dy, w, h - dy, rad, lipc)
    fh = h - lip
    if lum(face) > 0.8:
        rrect(c, x + 2, y + dy + 2, w - 4, fh - 4, max(0, rad - 2), face)
    else:
        rrect(c, x, y + dy, w, fh, rad, face)
    return (x, y + dy, w, fh)


def draw_combo_panel(c, p, st, cell_i, rect, t, enter_t0, row_t0):
    x0, y0, w, h = rect
    et = out_cubic((t - enter_t0) / 0.22)
    dy = (1.0 - et) * 16.0
    a = et
    c.save()
    c.translate(x0, y0 + dy)
    rrect(c, 0, 0, w, h - 3, 18, alpha(P["lip"], a))
    rrect(c, 2, 2, w - 4, h - 11, 16, alpha(P["surface"], a))
    if cell_i < 0:
        text_left_center(c, "Tap a cell to see its combinations", 24, (h - 7) / 2, "bold", 22, alpha(P["muted"], a))
        c.restore()
        return
    vals = st["vals"]
    for k, r in enumerate((p.run_a[cell_i], p.run_d[cell_i])):
        if r < 0:
            continue
        run = p.runs[r]
        n, total = len(run["cells"]), run["sum"]
        placed = 0
        for cc in run["cells"]:
            if vals[cc]:
                placed |= 1 << (vals[cc] - 1)
        cy = (h - 7.0) * (0.29 if k == 0 else 0.71)
        icon(c, "across" if k == 0 else "down", 18, cy - 15, 30, alpha(P["accent"], a), 2.6)
        head = "%d in %d" % (total, n)
        text_left_center(c, head, 58, cy, "xbold", 24, alpha(P["text"], a))
        xx = 58 + text_w("xbold", 24, head) + 18
        cbs = combos(n, total)
        row_t = t - row_t0
        shown = 0
        for m in cbs:
            ck = 1.0 if (m & placed) == placed else 0.0
            txt = mask_str(m)
            tw = text_w("bold", 21, txt)
            chip = (xx, cy - 19, tw + 20, 38)
            if chip[0] + chip[2] > w - 70 and shown < len(cbs) - 1:
                text_left_center(c, "+%d" % (len(cbs) - shown), xx + 4, cy, "bold", 21, alpha(P["muted"], a))
                break
            ap = clamp((row_t - 0.025 * shown) / 0.12)
            ca = a * out_cubic(ap)
            bg = lerpc(alpha(P["line"], 0.35), alpha(P["accent"], 0.16), ck)
            rrect(c, *chip, 12, alpha(bg, ca))
            if len(cbs) == 1:
                g = bump(row_t / 0.6)
                if g > 0:
                    gg = 2.0 + 2.0 * g
                    rrect_stroke(c, chip[0] - gg, chip[1] - gg, chip[2] + 2 * gg, chip[3] + 2 * gg, 14, alpha(P["success"], 0.8 * g * ca), 2)
            col = lerpc(alpha(P["muted"], 0.6), P["text"], ck)
            text_left_center(c, txt, chip[0] + 10, cy, "bold", 21, alpha(col, ca))
            if ck < 1.0:
                polyline(c, [(chip[0] + 8, cy + 1), (chip[0] + chip[2] - 8, cy + 1)], alpha(P["muted"], 0.8 * ca), 2.0)
            xx = chip[0] + chip[2] + 8
            shown += 1
        if len(cbs) == 1:
            ua = a * clamp((row_t - 0.08) / 0.12)
            uw = text_w("bold", 18, "unique")
            text_left_center(c, "unique", w - 24 - uw, cy, "bold", 18, alpha(P["success"], ua))
    c.restore()


def draw_toast(c, text_lines, rect, kind_col, t, t0):
    """main.toast: tinted card, outline + lip in the message colour."""
    x, y, w, h = rect
    k = out_cubic((t - t0) / 0.25)
    if k <= 0:
        return
    y += (1 - k) * -20
    face = lerpc(kind_col, P["surface"], 0.84)
    rrect(c, x, y, w, h, 18, alpha(kind_col, k))
    rrect(c, x + 2, y + 2, w - 4, h - 9, 16, alpha(face, k))
    ink = darkened(kind_col, 0.25)
    ty = y + 16 + 2
    for ln in text_lines:
        a_, d_ = asc_desc("bold", 23)
        draw_text(c, ln, x + 26, ty + a_, "bold", 23, alpha(ink, k))
        ty += 33


def draw_tool(c, rect, kind, caption, tint, badge=None, badge_col=None, k=0.0):
    x, y, w, h = rect
    lip = 7.0
    cap_h = 28.0
    d = min(min(w - 10.0, h - cap_h - lip - 2.0), 84.0)
    cx, cy = x + w / 2.0, y + d / 2.0 + 2.0
    fcy = cy + (lip - 1.0) * k
    c.drawCircle(cx, cy + lip, d / 2.0, paint(P["key_lip"]))
    c.drawCircle(cx, fcy, d / 2.0, paint(P["key_lip"]))
    c.drawCircle(cx, fcy, d / 2.0 - 2.0, paint(P["key"]))
    isz = 30 * (1.0 - 0.08 * k)
    icon(c, kind, cx - isz / 2, fcy - isz / 2, isz, tint, 2.6)
    fs = 17
    tw = text_w("xbold", fs, caption)
    draw_text(c, caption, x + (w - tw) / 2.0, y + h - 4.0, "xbold", fs, alpha(P["text"], 0.92))
    if badge:
        fs2 = 15
        bw = max(28.0, text_w("xbold", fs2, badge) + 14)
        brx, bry = cx + d * 0.18, fcy - d / 2.0 - 6.0
        bc = badge_col or P["gold"]
        rrect(c, brx, bry + 3, bw, 26, 13, darkened(bc, 0.3))
        rrect(c, brx, bry, bw, 26, 13, bc)
        text_centered(c, badge, brx + bw / 2, bry + 13, "xbold", fs2, (1, 1, 1, 1))


def draw_pad(c, rect, t, avail=None, current=0, presses=None):
    """NumberPad: 9 digits + erase in 2 rows of 5."""
    x0, y0, w, h = rect
    LIP, GAP, KEY_H = 6.0, 8.0, 86.0
    cols = 5
    kw = (w - GAP * (cols - 1)) / cols
    presses = presses or {}
    for k in range(10):
        row, col = k // cols, k % cols
        rx, ry = x0 + col * (kw + GAP), y0 + row * (KEY_H + LIP + GAP)
        is_erase = k == 9
        av = 1.0 if (is_erase or avail is None) else (1.0 if avail & (1 << k) else 0.0)
        face, lipc, ink = P["key"], P["key_lip"], P["key_ink"]
        if is_erase:
            ink = P["error"]
        if current == k + 1 and not is_erase:
            face, lipc, ink = P["sel"], P["sel_lip"], P["sel_ink"]
        pk = 0.0
        sbump = 1.0
        if k in presses:
            pt = t - presses[k]
            if 0 <= pt < 0.21:
                pk = out_cubic(clamp(pt / 0.05)) if pt < 0.05 else 1.0 - clamp((pt - 0.05) / 0.16)
            if 0 <= pt < 0.3:
                sbump = lerp(0.8, 1.0, drop(pt / 0.3))
        sink = LIP * (1.0 - av)
        push = max(sink, (LIP - 2.0) * pk)
        if av < 1.0:
            face = lerpc(face, P["bg2"], 1 - av)
            lipc = lerpc(lipc, P["line"], 1 - av)
            ink = lerpc(ink, P["disabled"], 1 - av)
        fy = ry + push
        fh = KEY_H
        rad = int(min(18.0, kw * 0.24))
        rrect(c, rx, fy, kw, ry + KEY_H + LIP - fy, rad, lipc)
        rrect(c, rx + 2, fy + 2, kw - 4, fh - 4, max(2, rad - 2), face)
        cx, cy = rx + kw / 2, fy + fh / 2
        if is_erase:
            isz = fh * 0.46 * sbump
            icon(c, "erase", cx - isz / 2, cy - isz / 2, isz, ink, 3.0)
            continue
        fs = int(min(fh * 0.58, kw * 0.6))
        text_centered(c, str(k + 1), cx, cy, "xbold", fs, alpha(ink, lerp(0.45, 1.0, av)), sbump)


def draw_progress(c, x, y, w, h, value):
    rrect(c, x, y, w, h, 5, P["line"])
    if value > 0:
        fw = max(h, w * value)
        rrect(c, x, y, fw, h, 5, P["primary"])
        if fw > h:
            rrect(c, x + h * 0.4, y + h * 0.2, max(0, fw - h * 0.8), max(3, h * 0.25), 5, (1, 1, 1, 0.28))


def draw_star_meter(c, x, y, h, stars=3):
    for k in range(3):
        cx, cy = x + 20 + k * 40, y + h / 2
        poly(c, star_pts(cx, cy + 2, 16), P["line"])
        if k < stars:
            poly(c, star_pts(cx, cy + 3, 16), P["gold_lip"])
            poly(c, star_pts(cx, cy, 16), P["gold"])


# ------------------------------------------------------------------ screens

W, H = 720.0, 1280.0
M = 24.0                        # screen side margin
BAR = (0, 16, 720, 80)
COMBO = (M, 108, 720 - 2 * M, 131)
STATUS_Y = 251.0
STATUS_H = 120.0
DOCK_Y = 904.0
BOARD_AREA = (M, STATUS_Y + STATUS_H + 12, 720 - 2 * M, DOCK_Y - 12 - (STATUS_Y + STATUS_H + 12))
TOOLS = (M, DOCK_Y + 14, 720 - 2 * M, 118)
PAD = (M, DOCK_Y + 14 + 118 + 12, 720 - 2 * M, 192)


def size_label(p):
    return "%d×%d" % (p.w - 1, p.h - 1)


def draw_game_screen(c, t, g):
    """g: dict with puzzle, board (BoardState), title, sub, timer, combo (bool),
    combo_enter, kaku (dict), toast (dict|None), pad_presses, overlay (win card)."""
    p = g["puzzle"]
    st = g["board"].at(t)
    rrect(c, 0, 0, W, H, 0, P["bg"])
    # top bar
    icon(c, "back", M + 6, 16 + 40 - 18, 36, P["text"], 2.6)
    draw_text(c, g["title"], 92, 16 + 40 - 2, "xbold", 25, P["text"])
    draw_text(c, g["sub"], 92, 16 + 40 + 21, "bold", 17, P["muted"])
    draw_text(c, g["timer"], 720 - M - 64 - 12 - 92, 16 + 40 + 9, "xbold", 26, P["disabled"])
    icon(c, "pause", 720 - M - 52, 16 + 40 - 18, 36, P["text"], 2.4)
    # combo helper (or the hint card over it)
    sel = st["sel"]
    if g.get("combo", True):
        draw_combo_panel(c, p, st, sel, COMBO, t, g.get("combo_enter", -10.0), g.get("row_t0", lambda s: st["sel_t0"])(st))
    if g.get("toast") and t >= g["toast"]["t0"]:
        tt = g["toast"]
        draw_toast(c, tt["lines"], (M, 108, 720 - 2 * M, 36 + 33 * len(tt["lines"]) + 7), tt["col"], t, tt["t0"])
    # status row: host, stars, progress
    kk = g.get("kaku", {})
    draw_kaku(c, (M, STATUS_Y, 110, 120), t, kk.get("mood_fn", lambda t: "idle")(t), kk.get("hop_fn", lambda t: -10.0)(t),
              1.0, kk.get("arms_fn", lambda t: 0.0)(t), kk.get("digit", 1), kk.get("blink", None))
    draw_star_meter(c, M + 110 + 14, STATUS_Y + (STATUS_H - 44) / 2, 44, 3)
    filled = sum(1 for i in p.white if st["vals"][i])
    prog = filled / float(len(p.white))
    px0 = M + 110 + 14 + 122 + 14
    pw = 720 - M - 58 - 14 - px0
    draw_progress(c, px0, STATUS_Y + STATUS_H / 2 - 9, pw, 18, prog)
    pl = "%d%%" % round(prog * 100)
    text_left_center(c, pl, 720 - M - text_w("xbold", 20, pl), STATUS_Y + STATUS_H / 2, "xbold", 20, P["text"])
    # board
    draw_board(c, p, st, BOARD_AREA, t)
    # dock: white bottom sheet, 2 px line on top
    rrect(c, -60, DOCK_Y, W + 120, H - DOCK_Y + 80, 0, P["surface"])
    rrect(c, -60, DOCK_Y, W + 120, 2, 0, P["line"])
    tw = (TOOLS[2] - 4 * 3) / 4
    for k, (kind, cap, tint) in enumerate((("undo", "Undo", C("1cb0f6")), ("notes", "Notes", C("ce82ff")),
                                             ("hint", "Hint", C("ff9600")), ("check", "Check", C("58cc02")))):
        badge = "OFF" if kind == "notes" else None
        tk = 0.0
        tp = g.get("tool_press", {}).get(kind)
        if tp is not None and 0 <= t - tp < 0.2:
            tk = 1.0 - clamp((t - tp - 0.06) / 0.14)
        draw_tool(c, (TOOLS[0] + k * (tw + 4), TOOLS[1], tw, TOOLS[3]), kind, cap, tint,
                  badge, P["accent"] if badge else None, tk)
    cur = st["vals"][sel] if sel >= 0 else 0
    draw_pad(c, PAD, t, None, cur, g.get("pad_presses", {}))
    if g.get("overlay"):
        g["overlay"](c, t)


def draw_win_card(c, t, t0, kaku_hops, stars_t0, secs_text, logical):
    """game_screen._show_win for a level: cheering host, 3 WinStars, Solved!,
    message, TIME / LOGICAL / GUESSES boxes, Next level / Review solve / Main menu."""
    k = out_cubic((t - t0) / 0.3)
    if k <= 0:
        return
    rrect(c, 0, 0, W, H, 0, (0, 0, 0, 0.45 * k))
    cw, ch = 620.0, 860.0
    cx0, cy0 = (W - cw) / 2, 200.0
    s = lerp(0.9, 1.0, out_cubic((t - t0) / 0.3))
    c.save()
    c.translate(W / 2, cy0 + ch / 2)
    c.scale(s, s)
    c.translate(-W / 2, -(cy0 + ch / 2))
    c.saveLayerAlpha(None, int(255 * k))
    rrect(c, cx0, cy0, cw, ch + 6, 26, P["lip"])
    rrect(c, cx0, cy0, cw, ch, 26, P["surface"])
    y = cy0 + 26
    hop = max([h for h in kaku_hops if h <= t], default=-10.0)
    draw_kaku(c, (W / 2 - 85, y, 170, 180), t, "happy", hop, 1.0, 2.0, 1)
    y += 180 + 14
    # WinStars
    scx = W / 2
    for kk in range(3):
        big = kk == 1
        r = 46.0 if big else 36.0
        px, py = scx + (kk - 1) * 96.0, y + 60 + (-10.0 if big else 12.0)
        poly(c, star_pts(px, py + 4, r), (0.02, 0.06, 0.18, 0.12))
        poly(c, star_pts(px, py, r), alpha(P["line"], 0.9))
        st = clamp((t - stars_t0[kk]) / 0.42)
        if st <= 0:
            continue
        sc = drop(st)
        rot = (1.0 - st) * -0.6
        c.save()
        c.translate(px, py)
        c.rotate(math.degrees(rot))
        c.scale(sc, sc)
        poly(c, star_pts(0, 5, r), P["gold_lip"])
        poly(c, star_pts(0, 0, r), P["gold"])
        poly(c, star_pts(-r * 0.12, -r * 0.14, r * 0.42), (1, 1, 1, 0.35))
        c.restore()
        if st < 1.0:
            for q in range(6):
                a = math.tau * q / 6.0 + kk
                dist = r + 26.0 * st
                c.drawCircle(px + math.cos(a) * dist, py + math.sin(a) * dist, 4.0 * (1.0 - st), paint(alpha(P["gold"], 1 - st)))
    y += 120 + 14
    text_centered(c, "Solved!", W / 2, y + 26, "xbold", 50, darkened(P["gold"], 0.08))
    y += 52 + 14
    text_centered(c, "Pure logic: every digit was deduced.", W / 2, y + 14, "bold", 22, P["muted"])
    y += 28 + 18
    bw = (cw - 52 - 24) / 3
    for kk, (cap, val, col) in enumerate((("TIME", secs_text, C("1cb0f6")), ("LOGICAL", str(logical), C("58cc02")),
                                          ("GUESSES", "0", C("ff9600")))):
        bx = cx0 + 26 + kk * (bw + 12)
        rrect(c, bx, y, bw, 96, 16, col)
        text_centered(c, cap, bx + bw / 2, y + 17, "xbold", 16, (1, 1, 1, 1))
        rrect(c, bx + 2, y + 34, bw - 4, 60, 14, P["surface"])
        text_centered(c, val, bx + bw / 2, y + 63, "xbold", 26, col)
    y += 96 + 30
    fr = draw_chunk(c, cx0 + 26, y, cw - 52, 70, P["primary"], P["primary_lip"], 5, 16)
    text_centered(c, "NEXT LEVEL", W / 2, fr[1] + fr[3] / 2, "xbold", 24, (1, 1, 1, 1))
    y += 70 + 14
    fr = draw_chunk(c, cx0 + 26, y, cw - 52, 70, P["surface"], P["line"], 5, 16)
    text_centered(c, "REVIEW SOLVE", W / 2, fr[1] + fr[3] / 2, "xbold", 24, P["accent"])
    y += 70 + 14
    text_centered(c, "MAIN MENU", W / 2, y + 22, "xbold", 22, P["muted"])
    c.restore()
    c.restore()


def draw_title_logo(c, rect, t, t_land=None, ts=96.0, gap=12.0, white=None):
    """TitleLogo: KAKURO in chunky tiles, the U in puzzle blue, digits in the corner."""
    WORD, DIG, TILTS = "KAKURO", [3, 1, 4, 9, 7, 2], [-5.0, 3.0, -2.0, 4.0, -3.0, 2.5]
    x, y, w, h = rect
    n = 6
    ts = min(ts, (w - gap * (n - 1)) / n)
    lip = ts * 0.09
    total = ts * n + gap * (n - 1)
    x0 = x + (w - total) / 2.0
    y0 = y + (h - ts - lip) / 2.0 - 4.0
    fs = int(ts * 0.56)
    for i in range(n):
        start = t_land[i] if t_land else -10.0
        appear = clamp((t - start) / 0.5)
        if appear <= 0:
            continue
        yy = y0 - (1.0 - drop(appear)) * 150.0
        a = clamp(appear * 3.0)
        yy += math.sin(t * 1.7 + i * 0.9) * 3.0 * clamp(t - start - 0.6)
        r = (x0 + i * (ts + gap), yy, ts, ts + lip)
        cx, cy = r[0] + ts / 2, r[1] + r[3] / 2
        rot = TILTS[i] * clamp(appear * 1.4)
        c.save()
        c.translate(cx, cy)
        c.rotate(rot)
        blue = i == 3
        face = C("1cb0f6", a) if blue else alpha(white or P["surface"], a)
        lipc = C("1899d6", a) if blue else alpha(P["line"], a)
        fr = draw_chunk(c, -ts / 2, -r[3] / 2, ts, r[3], face, lipc, lip, int(ts * 0.2))
        ink = (1, 1, 1, a) if blue else alpha(P["text"], a)
        text_centered(c, WORD[i], fr[0] + fr[2] / 2, fr[1] + fr[3] / 2, "xbold", fs, ink)
        ds = int(ts * 0.17)
        dcol = (1, 1, 1, 0.85 * a) if blue else alpha(P["accent"], a)
        draw_text(c, str(DIG[i]), fr[0] + fr[2] - ts * 0.2, fr[1] + fr[3] - ts * 0.1, "xbold", ds, dcol)
        c.restore()
