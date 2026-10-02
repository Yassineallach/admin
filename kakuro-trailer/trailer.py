"""Kakuro trailer: shot list, camera, captions, end card -> raw frames for ffmpeg.

Music grid: assets/audio/menu_loop.ogg ("Sunny Grid", 110 bpm, 16 bars) from
tools/kaku_music.py. Every cut lands on a beat (B = 60/110 s).

    python3 trailer.py frames  | ffmpeg ...      (see build.sh)
    python3 trailer.py still T out.png
    python3 trailer.py events  > sfx.json        (audio cue list for mix.py)
"""
import json
import math
import sys

import numpy as np
import skia

from kakuro_draw import *  # noqa: F401,F403

FPS = 60
VW, VH = 1920, 1080
B = 60.0 / 110.0
BAR = 4 * B
BASE = 1024.0 / 1280.0          # phone screen 720x1280 -> 576x1024 at zoom 1 (= the 9:16 safe column)
END = 56 * B + 1.75             # final note at 56B rings out
GREEN = C("58cc02")
GREEN_LIP = C("46a302")

bank = load_bank()
L1 = Puzzle(bank[0][0])          # Easy, Level 1 (6x6)
I = L1.idx
MED = Puzzle(bank[1][0])         # Medium, Level 1 (8x8)
PACKS = [(Puzzle(bank[0][5]), "Level 6", "Easy"), (MED, "Level 1", "Medium"),
         (Puzzle(bank[2][0]), "Level 1", "Hard"), (Puzzle(bank[3][0]), "Level 1", "Expert")]

SFX = []                         # (time, name, gain_db)


def sfx(t, name, db=0.0):
    SFX.append((round(t, 4), name, db))


# ------------------------------------------------------------------ boards / events

def puts(seq, t0, step=B, sel_lead=0.5 * B, db=-3.0):
    """seq of (cell, digit): select half a beat before, place on the beat."""
    ev, presses = [], {}
    for k, (cell, d) in enumerate(seq):
        tp = t0 + k * step
        ev.append(("sel", tp - sel_lead, cell))
        ev.append(("put", tp, cell, d))
        presses.setdefault(d - 1, []).append(tp)
        sfx(tp, "place_%d" % d, db)
    return ev, presses


def run_completions(p, events):
    """Times when a put completes a run (for the 'run' sparkle + host hop)."""
    st = BoardState(p, events)
    out = []
    for e in events:
        if e[0] == "put":
            s = st.at(e[1])
            if any(abs(v - e[1]) < 1e-6 for v in s["sweeps"].values()):
                out.append(e[1])
    return sorted(set(out))


def last_press(presses):
    def f(t):
        out = {}
        for k, ts in presses.items():
            past = [x for x in ts if x <= t]
            if past:
                out[k] = past[-1]
        return out
    return f


def hop_fn(times):
    def f(t):
        past = [x for x in times if x <= t]
        return past[-1] if past else -10.0
    return f


def mood_fn(times, hold=1.1, always=False):
    def f(t):
        if always:
            return "happy"
        return "happy" if any(0 <= t - x < hold for x in times) else "idle"
    return f


def timer_text(sec):
    sec = int(sec)
    return "%02d:%02d" % (sec // 60, sec % 60)


# S1 hook (0 - 8B): close-up, no music, the digits play a melody.
hook_seq = [(I(3, 1), 9), (I(4, 1), 7), (I(2, 2), 6), (I(3, 2), 8), (I(4, 2), 9)]
hook_ev, hook_press = puts(hook_seq, 1 * B, db=-7)
hook_done = run_completions(L1, hook_ev)
for tt in hook_done:
    sfx(tt + 0.05, "run", -9)
HOOK = dict(puzzle=L1, board=BoardState(L1, hook_ev), title="Level 1", sub="Easy · 6×6",
            kaku=dict(digit=1, hop_fn=hop_fn(hook_done), mood_fn=mood_fn(hook_done)),
            pad_presses=last_press(hook_press), t0=12)

# S3 + S4 (16B - 32B): one continuous solve of Level 1.
s3_ev = [("intro", 16 * B), ("sel", 17 * B, I(3, 1))]
e, pr1 = puts([(I(3, 1), 9)], 20 * B, sel_lead=3 * B)
s3_ev += e
e, pr2 = puts([(I(4, 1), 7)], 22 * B, sel_lead=1 * B)
s3_ev += e
gp_seq = [(I(2, 2), 6), (I(3, 2), 8), (I(4, 2), 9), (I(4, 3), 8), (I(5, 3), 9), (I(6, 3), 6), (I(1, 3), 9), (I(1, 4), 8)]
e, pr3 = puts(gp_seq, 24 * B, sel_lead=0.5 * B)
e[0] = ("sel", 23 * B, I(2, 2))
s3_ev += e + [("sel", 31.5 * B, I(2, 3))]
solve_done = run_completions(L1, s3_ev)
for tt in solve_done:
    sfx(tt + 0.05, "run", -4)
    sfx(tt + 0.12, "kaku_hop", -8)
press_all = {}
for prx in (pr1, pr2, pr3):
    for k, v in prx.items():
        press_all.setdefault(k, []).extend(v)
SOLVE = dict(puzzle=L1, board=BoardState(L1, s3_ev), title="Level 1", sub="Easy · 6×6",
             kaku=dict(digit=1, hop_fn=hop_fn(solve_done), mood_fn=mood_fn(solve_done)),
             pad_presses=last_press(press_all), combo_enter=16 * B + 0.1, t0=16 * B)
sfx(16 * B, "ui_open", -6)
sfx(17 * B, "ui_tap", -6)

# S5a hint (32B - 36B): Medium 8x8, the explained hint for the last cell of a run.
med_fill = {}
for i in MED.white:
    if (i * 7) % 10 < 4:
        med_fill[i] = MED.solution[i]
hint_cell = MED.idx(6, 1)
for i in (MED.idx(4, 1), MED.idx(5, 1)):
    med_fill[i] = MED.solution[i]
med_fill.pop(hint_cell, None)
run_r = MED.run_a[hint_cell]
others = sum(MED.solution[c] for c in MED.runs[run_r]["cells"] if c != hint_cell)
total = MED.runs[run_r]["sum"]
hint_digit = MED.solution[hint_cell]
# core/logic.gd explain(), Techniques.LAST
HINT_TEXT = "Across %d in %d: the other digits add up to %d, so the last cell is %d - %d = %d." % (
    total, len(MED.runs[run_r]["cells"]), others, total, others, hint_digit)
hint_ev = [("sel", 32 * B - 0.2, hint_cell), ("put", 34 * B, hint_cell, hint_digit, True)]
HINT = dict(puzzle=MED, board=BoardState(MED, hint_ev, med_fill), title="Level 1", sub="Medium · 8×8",
            kaku=dict(digit=1, mood_fn=lambda t: "idle"), tool_press={"hint": 32.6 * B}, t0=95,
            toast=dict(t0=33 * B, col=P["accent2"], text=HINT_TEXT))
sfx(32.6 * B, "ui_tap", -6)
sfx(33 * B, "hint", -2)
sfx(34 * B, "place_%d" % hint_digit)

# S5b packs (36B - 40B): one beat per difficulty, a digit lands on each cut.
PACK_SHOTS = []
for k, (pz, ttl, diff) in enumerate(PACKS):
    fill = {}
    for i in pz.white:
        if (i * 5 + k) % 9 < 4:
            fill[i] = pz.solution[i]
    empties = [i for i in pz.white if i not in fill]
    cell = empties[len(empties) // 2]
    tcut = (36 + k) * B
    d = pz.solution[cell]
    ev = [("sel", tcut - 0.3, cell), ("put", tcut + 0.08, cell, d)]
    sfx(tcut + 0.08, "place_%d" % d)
    PACK_SHOTS.append(dict(puzzle=pz, board=BoardState(pz, ev, fill), title=ttl, sub="%s · %s" % (diff, size_label(pz)),
                           kaku=dict(digit=k + 1), t0=20 + 30 * k))

# S6 payoff (40B - 48B): the last digit, the board's win wave, the win card.
fin_cell = I(4, 6)
fin_fill = {i: L1.solution[i] for i in L1.white if i != fin_cell}
FIN_T = 41 * B
WIN_T = FIN_T + 0.3
CARD_T = 43 * B
fin_ev = [("sel", 39 * B, fin_cell), ("put", FIN_T, fin_cell, L1.solution[fin_cell]), ("win", WIN_T)]
sfx(FIN_T, "place_%d" % L1.solution[fin_cell])
sfx(FIN_T + 0.05, "run", -4)
sfx(WIN_T, "win", -1)
sfx(CARD_T, "ui_open", -6)
STARS_T = [44 * B, 44.5 * B, 45 * B]
for k, ts in enumerate(STARS_T):
    sfx(ts + 0.12, "star_%d" % (k + 1), -2)
CARD_HOPS = [CARD_T + 0.15, 46 * B, 47.3 * B]
sfx(CARD_T + 0.2, "kaku_yay", -4)
FIN_TIME = 2 * 60 + 41


def fin_overlay(c, t):
    draw_win_card(c, t, CARD_T, CARD_HOPS, STARS_T, timer_text(FIN_TIME), len(L1.white))


FIN = dict(puzzle=L1, board=BoardState(L1, fin_ev, fin_fill), title="Level 1", sub="Easy · 6×6",
           kaku=dict(digit=1, hop_fn=hop_fn([FIN_T + 0.05]), mood_fn=lambda t: "happy" if t >= FIN_T else "idle",
                     arms_fn=lambda t: 2.0 * smoothstep(FIN_T, FIN_T + 0.4, t)),
           pad_presses=last_press({L1.solution[fin_cell] - 1: [FIN_T]}), overlay=fin_overlay, frozen=FIN_TIME)

# S2 title (8B - 16B)
LOGO_T = [9 * B + k * 0.5 * B for k in range(6)]
for k, d in enumerate([3, 1, 4, 9, 7, 2]):
    sfx(LOGO_T[k] + 0.22, "place_%d" % d, -8)
TITLE_HOP = 13 * B
sfx(TITLE_HOP + 0.1, "kaku_hop", -4)
PLAY_POP = 12 * B
PLAY_PRESS = 15.5 * B
sfx(PLAY_PRESS, "ui_tap", -2)

# S7 end card (48B - END)
END_ICON = 48 * B
END_LOGO = [49 * B + k * 0.5 * B for k in range(6)]
for k, d in enumerate([3, 1, 4, 9, 7, 2]):
    sfx(END_LOGO[k] + 0.22, "place_%d" % d, -3)
sfx(END_ICON + 0.1, "unlock", -4)
sfx(56 * B, "star_3", -1)


# ------------------------------------------------------------------ captions

CAPTIONS = [
    # (t_in, t_out, [(text, big?)...], side)
    (9.5 * B, 15.6 * B, [("Cross sums.", 1), ("Pure logic.", 1)], "left"),
    (17 * B, 23.7 * B, [("Every clue", 1), ("is a sum", 1), ("No digit repeats in a run", 0)], "left"),
    (24.5 * B, 31.7 * B, [("Every digit", 1), ("plays a note", 1)], "right"),
    (33 * B, 35.8 * B, [("Hints that", 1), ("explain why", 1)], "left"),
    (36 * B, 39.85 * B, [("Easy to", 1), ("Expert", 1), ("", 2)], "left"),
    (41.5 * B, 47.7 * B, [("One solution.", 1), ("No guessing.", 1)], "left"),
]
PACK_SUBS = ["6×6", "8×8", "10×10", "12×12"]
CAP_X = 96


def draw_caption(c, t, t_in, t_out, lines, side, zoom):
    if not (t_in - 0.01 <= t <= t_out + 0.25):
        return
    k_in = out_cubic((t - t_in) / 0.35)
    k_out = 1.0 - clamp((t - t_out) / 0.2)
    a = k_in * k_out
    dy = (1 - k_in) * 24
    edge = 288.0 * zoom                     # phone half-width on screen
    maxw = (VW / 2 - edge) - 44 - CAP_X
    x = CAP_X if side == "left" else VW / 2 + edge + 44
    spec = []
    for txt, big in lines:
        size = {1: 72, 0: 34, 2: 64}[big]
        w = "xbold" if big else "bold"
        if txt:
            size = min(size, size * maxw / max(1.0, text_w(w, size, txt)))
        spec.append((txt, size, w, big))
    hts = [s[1] * (1.12 if s[3] else 1.5) for s in spec]
    y = 540 - sum(hts) / 2 + dy
    for (txt, size, w, big), h in zip(spec, hts):
        base = y + size * 0.86 + (size * 0.3 if not big else 0)
        if big == 2:
            k = int((t - 36 * B) // B)
            if 0 <= k < 4:
                pa = a * out_cubic((t - (36 + k) * B) / 0.15)
                draw_text(c, PACK_SUBS[k], x, base + 5, "xbold", size, alpha(GREEN_LIP, pa))
                draw_text(c, PACK_SUBS[k], x, base, "xbold", size, alpha(C("ffc800"), pa))
        elif txt:
            draw_text(c, txt, x, base + (5 if big else 3), w, size, alpha(GREEN_LIP, a))
            draw_text(c, txt, x, base, w, size, (1, 1, 1, a))
        y += h


# ------------------------------------------------------------------ stage + camera

def draw_stage(c, t):
    """Feather green (the boot splash colour) with title_backdrop's tilted,
    drifting Kakuro grid in faint white."""
    c.clear(skia.Color4f(*GREEN))
    CELL = 150.0
    c.save()
    c.translate(VW / 2, VH / 2)
    c.rotate(math.degrees(-0.21))
    off = ((9.0 * t * 1.4) % (CELL * 2), (6.0 * t * 1.4) % (CELL * 2))
    line = (1, 1, 1, 0.07)
    fill = (1, 1, 1, 0.035)
    ink = (1, 1, 1, 0.11)
    reach = 9
    for gy in range(-reach, reach):
        for gx in range(-reach, reach):
            x, y = gx * CELL + off[0], gy * CELL + off[1]
            n = (gx * 73856093) ^ (gy * 19349663)
            n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
            hv = abs(n ^ (n >> 16))
            kind = hv % 11
            if kind in (0, 5):
                rrect(c, x + 4, y + 4, CELL - 8, CELL - 8, 0, fill)
                polyline(c, [(x + 4, y + 4), (x + CELL - 4, y + CELL - 4)], line, 3)
                draw_text(c, str(3 + hv % 40), x + CELL * 0.56, y + CELL * 0.4, "xbold", 34, ink)
                if kind == 0:
                    draw_text(c, str(4 + (hv >> 5) % 30), x + CELL * 0.14, y + CELL * 0.86, "xbold", 34, ink)
            elif kind == 3:
                draw_text(c, str(1 + (hv >> 3) % 9), x + CELL * 0.33, y + CELL * 0.72, "xbold", 74, (1, 1, 1, 0.075))
            rrect_stroke(c, x + 4, y + 4, CELL - 8, CELL - 8, 0, line, 3)
    c.restore()


def keyframes(t, keys):
    """keys: [(time, cx, cy, zoom)], eased in-out-sine between them."""
    if t <= keys[0][0]:
        return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= t <= b[0]:
            k = in_out_sine((t - a[0]) / (b[0] - a[0]))
            return tuple(lerp(a[i], b[i], k) for i in (1, 2, 3))
    return keys[-1][1:]


def phone(c, t, cam, draw_fn):
    cx, cy, z = cam
    s = BASE * z
    c.save()
    c.translate(VW / 2, VH / 2)
    c.scale(s, s)
    c.translate(-cx, -cy)
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(0, 0, 720, 1280), 52, 52)
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(0, 18, 720, 1280), 52, 52), paint(GREEN_LIP))
    c.save()
    c.clipRRect(rr, doAntiAlias=True)
    draw_fn(c, t)
    c.restore()
    c.restore()


def game_fn(g):
    def f(c, t):
        gg = dict(g)
        if "frozen" in g:
            gg["timer"] = timer_text(g["frozen"])
        else:
            gg["timer"] = timer_text(g.get("t0", 0) + max(0.0, t - g.get("tstart", 0)))
        if callable(g.get("pad_presses")):
            gg["pad_presses"] = g["pad_presses"](t)
        if g.get("toast"):
            gg["toast"] = dict(g["toast"])
            gg["toast"]["lines"] = wrap(g["toast"]["text"], "bold", 23, 720 - 2 * M - 52)
        draw_game_screen(c, t, gg)
    return f


def wrap(text, w, size, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        nxt = (cur + " " + wd).strip()
        if text_w(w, size, nxt) <= maxw:
            cur = nxt
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    return lines


def title_fn(c, t):
    """menu_screen (light theme): Kaku, KAKURO tiles, tagline, PLAY, mode tiles."""
    rrect(c, 0, 0, W, H, 0, P["bg"])
    draw_kaku(c, (245, 110, 230, 245), t, "happy" if 0 <= t - TITLE_HOP < 1.2 else "idle", TITLE_HOP, 1.0,
              1.2 * bump((t - TITLE_HOP) / 1.2), 1, blink_t0=11 * B)
    draw_title_logo(c, (0, 370, 720, 170), t, LOGO_T)
    ta = clamp((t - 12 * B) / 0.4)
    tag = "CROSS SUMS · PURE LOGIC"
    sp = 4.0
    tw = sum(text_w("xbold", 17, ch) + sp for ch in tag) - sp
    x = (720 - tw) / 2
    for ch in tag:
        draw_text(c, ch, x, 572, "xbold", 17, alpha(P["muted"], ta))
        x += text_w("xbold", 17, ch) + sp
    pk = clamp((t - PLAY_POP) / 0.35)
    if pk > 0:
        s = lerp(0.6, 1.0, drop(pk))
        press = 0.0
        if t >= PLAY_PRESS:
            press = 1.0 - clamp((t - PLAY_PRESS - 0.08) / 0.15)
        c.save()
        c.translate(360, 692)
        c.scale(s, s)
        c.translate(-360, -692)
        c.saveLayerAlpha(None, int(255 * clamp(pk * 3)))
        fr = draw_chunk(c, 24, 630, 672, 128, P["primary"], P["primary_lip"], 9, 26, press)
        text_centered(c, "PLAY", 360, fr[1] + fr[3] / 2 - 14, "xbold", 44, (1, 1, 1, 1))
        text_centered(c, "Level 1 · Easy", 360, fr[1] + fr[3] / 2 + 28, "bold", 20, (1, 1, 1, 0.78))
        c.restore()
        c.restore()
    for k, (ttl, cap) in enumerate((("Levels", "0 / 410"), ("Quick Play", "Endless"), ("Learn", "0 / 5"))):
        ak = clamp((t - 13.3 * B - k * 0.12) / 0.3)
        if ak <= 0:
            continue
        tx = 24 + k * (216 + 12)
        c.saveLayerAlpha(None, int(255 * ak))
        fr = draw_chunk(c, tx, 800 + (1 - out_cubic(ak)) * 30, 216, 210, P["surface"], P["line"], 7, 22)
        text_centered(c, ttl, tx + 108, fr[1] + 150, "xbold", 24, P["text"])
        text_centered(c, cap, tx + 108, fr[1] + 180, "bold", 18, P["muted"])
        c.restore()


def end_card(c, t):
    draw_stage(c, t)
    # app icon (assets/icons/icon_512.png) pops in with a squash
    k = clamp((t - END_ICON) / 0.5)
    if k > 0:
        s = drop(k)
        sq = 1.0 + 0.08 * bump(clamp((t - END_ICON - 0.25) / 0.3))
        im = img("icons/icon_512.png")
        size = 270.0
        c.save()
        c.translate(VW / 2, 290)
        c.scale(s * sq, s / sq)
        rrect(c, -size / 2 - 8, -size / 2 - 8 + 14, size + 16, size + 16, 70, GREEN_LIP)
        rrect(c, -size / 2 - 8, -size / 2 - 8, size + 16, size + 16, 70, (1, 1, 1, 1))
        c.drawImageRect(im, skia.Rect.MakeXYWH(-size / 2, -size / 2, size, size),
                        skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
        c.restore()
    draw_title_logo(c, (VW / 2 - 300, 470, 600, 130), t, END_LOGO, ts=88.0, gap=11.0)
    ta = clamp((t - 52 * B) / 0.4)
    tag = "CROSS SUMS · PURE LOGIC"
    sp = 6.0
    tw = sum(text_w("xbold", 30, ch) + sp for ch in tag) - sp
    x = (VW - tw) / 2
    for ch in tag:
        draw_text(c, ch, x, 655 + 4, "xbold", 30, alpha(GREEN_LIP, ta))
        draw_text(c, ch, x, 655, "xbold", 30, (1, 1, 1, ta))
        x += text_w("xbold", 30, ch) + sp
    ma = clamp((t - 53 * B) / 0.4)
    modes = "Levels · Quick Play · Daily Challenge"
    mw = text_w("bold", 30, modes)
    draw_text(c, modes, (VW - mw) / 2, 718, "bold", 30, (1, 1, 1, 0.92 * ma))
    # Store badge placeholder: replace with the official Google Play badge artwork.
    ba = clamp((t - 54 * B) / 0.4)
    if ba > 0:
        bw, bh = 300.0, 90.0
        bx, by = (VW - bw) / 2, 790 + (1 - out_cubic(ba)) * 20
        rrect_stroke(c, bx, by, bw, bh, 16, (1, 1, 1, 0.9 * ba), 3)
        text_centered(c, "STORE BADGE", VW / 2, by + bh / 2, "xbold", 26, (1, 1, 1, 0.9 * ba))


# ------------------------------------------------------------------ shots

def board_center(p, i=None):
    cell, ox, oy = board_geometry(p, BOARD_AREA)
    if i is None:
        return ox + p.w * cell / 2, oy + p.h * cell / 2
    return cell_center(p, BOARD_AREA, i)


hx, hy = board_center(L1, I(3, 2))
bcx, bcy = board_center(L1)

SHOTS = [
    # (start, end, kind, payload, camera keys)
    (0.0, 8 * B, "game", HOOK, [(0.0, bcx, bcy - 40, 1.95), (8 * B, bcx, bcy - 60, 1.72)]),
    (8 * B, 16 * B, "title", None, [(8 * B, 360, 600, 1.0), (16 * B, 360, 560, 1.08)]),
    (16 * B, 24 * B, "game", SOLVE, [(16 * B, 360, 640, 1.0), (17 * B, 360, 640, 1.0), (19 * B, 360, 520, 1.2), (24 * B, 360, 520, 1.24)]),
    (24 * B, 32 * B, "game", SOLVE, [(24 * B, 360, 690, 1.12), (32 * B, 360, 660, 1.2)]),
    (32 * B, 36 * B, "game", HINT, [(32 * B, 360, 520, 1.12), (36 * B, 360, 500, 1.18)]),
] + [((36 + k) * B, (37 + k) * B, "game", PACK_SHOTS[k], [((36 + k) * B, 360, 640, 1.0 + 0.02 * k), ((37 + k) * B, 360, 640, 1.03 + 0.02 * k)]) for k in range(4)] + [
    (40 * B, 48 * B, "game", FIN, [(40 * B, bcx, bcy, 1.22), (42.6 * B, bcx, bcy - 20, 1.26), (43.4 * B, 360, 640, 1.0), (48 * B, 360, 640, 1.03)]),
    (48 * B, END + 0.01, "end", None, None),
]


def render(c, t):
    zoom = 1.0
    for (a, b, kind, g, keys) in SHOTS:
        if a <= t < b:
            break
    if kind == "end":
        end_card(c, t)
    else:
        draw_stage(c, t)
        cam = keyframes(t, keys)
        zoom = cam[2]
        if kind == "title":
            phone(c, t, cam, title_fn)
        else:
            if "tstart" not in g:
                g["tstart"] = a
            phone(c, t, cam, game_fn(g))
    for cap in CAPTIONS:
        draw_caption(c, t, *cap, zoom)
    # final fade to green after the last note
    fa = clamp((t - (END - 0.5)) / 0.5)
    if fa > 0:
        rrect(c, 0, 0, VW, VH, 0, alpha(GREEN, fa))


def main():
    mode = sys.argv[1]
    if mode == "events":
        print(json.dumps(dict(end=END, bpm=110, music_start=8 * B, sfx=SFX,
                              music_duck=[(40 * B, 0.0), (44 * B, -9.0), (47 * B, 0.0)], music_stop=56 * B)))
        return
    surf = skia.Surface(VW, VH)
    c = surf.getCanvas()
    if mode == "still":
        t = float(sys.argv[2])
        render(c, t)
        surf.makeImageSnapshot().save(sys.argv[3])
        return
    n = int(math.ceil(END * FPS))
    out = sys.stdout.buffer
    for f in range(n):
        t = f / FPS
        c.save()
        render(c, t)
        c.restore()
        arr = surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
        out.write(np.ascontiguousarray(arr).tobytes())
        if f % 120 == 0:
            print("frame %d/%d" % (f, n), file=sys.stderr)


if __name__ == "__main__":
    main()
