"""Shots 12-16: map select + launch flight, Tokyo hero, target, logo, end card."""
import math
import random
import skia
from prim import *
from scenes import (ev, Runner, amb_wait, draw_line, draw_tokyo_terrain, TOK_COLS, TOK_WATER2, IVORY,
                    bg, panx)

CITIES = [
    ('London', ['e32017', '003688', '00782a', 'e0a800', 'b36305', '9b0056', '0098d4'], 'grey'),
    ('Paris', ['d3a600', '003ca6', '837902', 'cf009e', 'ff7e2e', '3fae7a', '704b1c'], 'grey'),
    ('New York City', ['ee352e', '00933c', 'b933ad', '0039a6', 'ff6319', '6cbe45', '996633'], 'cream'),
    ('Warsaw', ['1f5fa8', 'd6202c', '2e8b57', 'e39a00', '7a3e9d', '00a0b0', '8b5a2b'], 'grey'),
    ('Lisbon', ['4a8fcf', 'cea200', '00a88f', 'e3004f', 'f07c00', '6a3d9a', '7a8c00'], 'sand'),
    ('Tokyo', ['f39700', 'e60012', '00a7db', '009944', '8f76d6', 'b8954a', '9c5e31'], 'ivory'),
    ('Chicago', ['c60c30', '00a1de', '62361b', '009b3a', 'f9461c', '522398', 'e27ea6'], 'warm'),
    ('Budapest', ['d2a400', 'e41f18', '005ca5', '4cb03f', '8a4f9e', '8b5a2b', '00a3a6'], 'warm'),
    ('Berlin', ['7dad4c', 'da421e', '16683d', '7e5330', '8c6dab', '528dba', 'f3791d'], 'grey'),
    ('Melbourne', ['279fd5', 'be1014', '152c6b', 'e0a800', '028430', 'f178af', '7a5c9e'], 'ivory'),
    ('Hong Kong', ['0075c2', 'e2231a', '00ab4e', 'f7943e', '7d499d', '9a3b26', 'a8b000'], 'ivory'),
    ('Barcelona', ['e2001a', '9a3b8e', '00963f', 'd29d00', '0071b9', 'f07c10', '00a6d6'], 'sand'),
    ('Osaka', ['e5171f', '522886', '0078ba', '019a66', 'e44d93', '814721', 'ee7b1a'], 'ivory'),
    ('Stockholm', ['4ca85b', 'd71d24', '0089ca', 'ec619f', '7e5b9b', 'f28c00', 'a0522d'], 'grey'),
    ('Saint Petersburg', ['d6083b', '0078c9', '009a49', 'ea7125', '702785', 'd9a800', '8b5e3c'], 'grey'),
    ('Boston', ['da291c', 'ed8b00', '003da5', '00843d', '80276c', '6f7c85', '8b5a2b'], 'grey'),
]
DESC = {
    'Tokyo': ['Feed the bay with the heaviest', 'commuter flows on the list.'],
    'New York City': ['Two rivers and an island: bridge', 'Manhattan to its boroughs.'],
    'London': ['Follow the Thames as it winds', 'through the oldest underground.'],
}
NEEDS = {'London': 1000, 'Paris': 1000, 'New York City': 1000, 'Warsaw': 300, 'Lisbon': 400, 'Tokyo': 800}
PITCH = 768
RAIL_Y = 290
GOLD = 'dfc463'


def ghost_network(c, idx, cx, cy, w, h, alpha, panel=False):
    """A city's little sample network, drawn from its own seed."""
    name, cols, palk = CITIES[idx % len(CITIES)]
    pal = PAL[palk]
    rnd = random.Random(1001 + idx)
    if panel:
        c.drawRect(skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h), fillp(rgb('fdfbee', alpha)))
    # water: one octilinear band across the panel
    pts = []
    y0 = rnd.uniform(0.3, 0.7)
    for k in range(4):
        pts.append((cx - w / 2 - 20 + k * (w + 40) / 3, cy - h / 2 + h * min(0.9, max(0.1, y0 + rnd.uniform(-0.18, 0.18)))))
    _, wf = river_path(pts, h * 0.045, reach=18)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h))
    c.drawPath(wf, fillp(rgb('c5e3f2' if panel else pal['water'], alpha)))
    for li in range(3):
        n = rnd.randint(2, 3)
        stops = [(cx - w / 2 + w * rnd.uniform(0.12, 0.88), cy - h / 2 + h * rnd.uniform(0.15, 0.85)) for _ in range(n)]
        tr = Track(stops, reach=10)
        c.drawPath(tr.path, strokep(rgb(cols[li], alpha), 4.5 if panel else 3.5, cap=skia.Paint.kButt_Cap))
        for s in stops:
            kind = rnd.choice([CIRCLE, TRIANGLE, SQUARE])
            p = shape_path(kind, 7 if panel else 6, s)
            c.drawPath(p, fillp(rgb(WHITE, alpha)))
            c.drawPath(p, strokep(rgb(INK, alpha), 2.2, join=skia.Paint.kMiter_Join))
    c.restore()


def wrap_desc(name):
    return DESC.get(name, ['', ''])


def map_card(c, idx, x, k, best=None, badges=0):
    """The focused map card (screenshot 3_card): x is the card centre."""
    name, cols, palk = CITIES[idx]
    a = k
    left = x - 192
    c.drawRect(skia.Rect.MakeXYWH(left, 81, 384, 907), fillp(rgb('dedcd8', a)))
    c.drawPath(path_of([(left + 342, 81), (left + 384, 81), (left + 384, 123)], True), fillp(rgb('5a5f5a', a)))
    size = 52 if len(name) < 10 else 40
    text(c, name, left + 32, 225, size, 400, '333333', a)
    for i, col in enumerate(cols):
        c.drawCircle(left + 44 + i * 35, 267, 13, fillp(rgb(col, a)))
    ghost_network(c, idx, x, 475, 322, 326, a, panel=True)
    d = wrap_desc(name)
    text(c, d[0], left + 32, 700, 26, 400, '333333', a)
    text(c, d[1], left + 32, 738, 26, 400, '333333', a)
    text(c, 'Best', left + 32, 890, 27, 400, '333333', a)
    b = best if best is not None else '0 / %d' % NEEDS.get(name, 800)
    text(c, b, left + 32, 928, 27, 400, '333333', a)
    for j in range(badges):
        bx = left + 234 + j * 81
        c.drawCircle(bx, 905, 38, fillp(rgb('2f3133', a)))
        if j == 0:
            c.drawCircle(bx, 897, 14, fillp(rgb(WHITE, a)))
            c.drawPath(path_of([(bx - 8, 906), (bx + 8, 906), (bx, 926)], True), fillp(rgb(WHITE, a)))
        else:
            c.drawPath(path_of([(bx - 20, 895), (bx - 10, 905), (bx, 890), (bx + 10, 905), (bx + 20, 895), (bx + 20, 916), (bx - 20, 916)], True),
                       fillp(rgb(WHITE, a)))


def strip(c, f, focus_k=1.0, locked=None, unlock=0.0, buttons=1.0, green=1.0, best=None, badges=0, pinned=None):
    """Map select: the cards hang off the red rail. f = strip position."""
    c.drawRect(skia.Rect.MakeWH(W, H), fillp(rgb(PAPER)))
    # green line's corner piece
    if green > 0:
        gp = skia.Path(); gp.moveTo(-20, 865); gp.lineTo(160, 865); gp.quadTo(305, 865, 305, 1010); gp.lineTo(305, 1100)
        c.drawPath(gp, strokep(rgb('6bbe6b', green), 32, cap=skia.Paint.kButt_Cap))
    c.drawLine(-20, RAIL_Y, W + 20, RAIL_Y, strokep(rgb('dd6a6a'), 32, cap=skia.Paint.kButt_Cap))
    first = int(math.floor(f)) - 3
    for i in range(first, first + 8):
        if i < 0 or i >= len(CITIES):
            continue
        x = W / 2 + (i - f) * PITCH
        if x < -500 or x > W + 500:
            continue
        focus = pinned if pinned is not None else round(f)
        k = focus_k * clamp01(1 - abs(i - f) * 2.2) if i == focus else 0.0
        name = CITIES[i][0]
        ua = 1 - k
        if ua > 0.01:
            la = 1.0
            if locked is not None and i == locked:
                la = unlock
            text(c, name, x, 232, 52, 400, '8a8a8a', ua * lerp(0.6, 1.0, la), 'center')
            ghost_network(c, i, x, 650, 400, 230, 0.4 * ua * la)
            if locked is not None and i == locked and unlock < 1:
                la2 = (1 - unlock) * ua
                lx, ly = x, 620
                c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(lx - 30, ly - 10, 60, 46), 8, 8), fillp(rgb('9f9f9d', la2)))
                arc = skia.Path(); arc.addArc(skia.Rect.MakeXYWH(lx - 19, ly - 44, 38, 60), 180, 180)
                c.drawPath(arc, strokep(rgb('9f9f9d', la2), 9, cap=skia.Paint.kButt_Cap))
        if k > 0.01:
            map_card(c, i, x, k, best, badges)
    # a menu train on the rail with its riders
    tx = (W * 0.24 + f * 97) % (W + 200) - 100
    c.drawRect(skia.Rect.MakeXYWH(tx - 37, RAIL_Y - 25, 74, 50), fillp(rgb('c85555')))
    for j, kind in enumerate([CIRCLE, TRIANGLE, CIRCLE]):
        c.drawPath(shape_path(kind, 7, (tx - 21 + j * 21, RAIL_Y)), fillp(rgb(WHITE, 0.7)))
    # buttons
    if buttons > 0:
        a = buttons
        ox = 60 * (1 - buttons)
        for (y0, word) in ((794, 'Play'), (923, 'Mode')):
            c.drawRect(skia.Rect.MakeXYWH(1559 + ox, y0, 307, 108), fillp(rgb(GOLD, a)))
            text(c, word, 1585 + ox, y0 + 84, 92, 800, WHITE, a)
        # arrows: right for Play, down for Mode
        ay = 848
        c.drawRect(skia.Rect.MakeXYWH(1458 + ox, ay - 10, 50, 20), fillp(rgb('262626', a)))
        c.drawPath(path_of([(1500 + ox, ay - 26), (1540 + ox, ay), (1500 + ox, ay + 26)], True), fillp(rgb('262626', a)))
        c.drawRect(skia.Rect.MakeXYWH(1490 + ox, 935, 20, 50), fillp(rgb('262626', a)))
        c.drawPath(path_of([(1474 + ox, 978), (1500 + ox, 1018), (1526 + ox, 978)], True), fillp(rgb('262626', a)))
        c.drawRect(skia.Rect.MakeXYWH(78 - ox, 82, 55, 20), fillp(rgb('262626', a)))
        c.drawPath(path_of([(88 - ox, 66), (42 - ox, 92), (88 - ox, 118)], True), fillp(rgb('262626', a)))


# ============================================================ TOKYO ========
TS = {
    'A': (CIRCLE, (260, 300)), 'B': (TRIANGLE, (560, 220)), 'C': (SQUARE, (860, 300)), 'D': (CIRCLE, (1000, 520)),
    'E': (TRIANGLE, (700, 560)), 'F': (SQUARE, (420, 640)), 'G': (CIRCLE, (300, 880)), 'H': (TRIANGLE, (640, 900)),
    'I': (SQUARE, (940, 800)), 'J': (CIRCLE, (1400, 300)), 'K': (TRIANGLE, (1600, 200)), 'L': (SQUARE, (1560, 520)),
    'M': (CIRCLE, (1320, 690)), 'N': (STAR, (1000, 130)), 'O': (DIAMOND, (1750, 400)), 'P': (CIRCLE, (1700, 960)),
    'Q': (SQUARE, (180, 560)),
}
TL = [
    ('ABCDML', 0), ('QFEDJK', 1), ('GHIMP', 2), ('BEH', 3), ('AQG', 4), ('NJO', 5), ('KOLM', 6),
]
TOK_TRACKS = [(Track([TS[k][1] for k in s]), TOK_COLS[ci]) for s, ci in TL]
TOK_RUN = [Runner(tr, -5.0 - i * 1.3, speed=170, dwell=0.6, seed=40 + i, start=(i * 2) % len(tr.stops) if i % 2 else 0)
           for i, (tr, col) in enumerate(TOK_TRACKS)]
TOK_RUN2 = Runner(TOK_TRACKS[0][0], -2.0, speed=170, dwell=0.6, seed=60, start=len(TOK_TRACKS[0][0].stops) - 1, direction=-1)


def tokyo_board(c, t, count=742, hud=True):
    draw_tokyo_terrain(c)
    vignette(c)
    for tr, col in TOK_TRACKS:
        draw_line(c, tr, col, IVORY, TOK_WATER2)
    for (tr, col), r in zip(TOK_TRACKS, TOK_RUN):
        r.draw(c, t, col, 1)
    TOK_RUN2.draw(c, t, TOK_COLS[0], 1)
    for k, (kind, p) in TS.items():
        station(c, kind, p, ring=(k == 'D'))
    for i, k in enumerate(TS):
        kinds, sc = amb_wait(80 + i, t, 1, 3, 0.9)
        waiting(c, TS[k][1], kinds, sc)
    if hud:
        hud_controls(c)
        hud_clock(c, 'SAT', count, 0.35)
        hud_line_dots(c, TOK_COLS, 7)
        hud_dock(c, [('loco', 1, None), ('car', 2, None), ('inter', 0, None), ('bridge', 1, None)])


def feather_board(c, t, left, width_frac, count):
    """The board flying in: a full-screen picture whose edges dissolve."""
    fw = W * 0.24 * width_frac
    c.saveLayer(None, None)
    c.save()
    c.translate(left, 0)
    tokyo_board(c, t, count)
    c.restore()
    if fw > 1:
        for (x0, x1, a0, a1) in ((left, left + fw, 0, 255), (left + W - fw, left + W, 255, 0)):
            sh = skia.GradientShader.MakeLinear([(x0, 0), (x1, 0)], [skia.Color(0, 0, 0, a0), skia.Color(0, 0, 0, a1)])
            p = skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kDstIn)
            c.drawRect(skia.Rect.MakeXYWH(x0, -50, x1 - x0, H + 100), p)
    c.restore()


def shot12(c, t):
    t0 = bar(12)
    lt = t - t0
    browse_end, tap, tidy_end, fly0 = 1.05, 1.12, 1.46, 1.55
    fly1 = BAR
    if lt < browse_end:
        f = lerp(0, 5, both(lt / browse_end))
        buttons = 1.0
    elif lt < fly0:
        f = 5
        buttons = 1 - both(seg(lt, tap + 0.05, tidy_end))
    else:
        f = 5
        buttons = 0
    E = 13.0
    roll = 0
    if lt >= fly0:
        u = fly(seg(lt, fly0, fly1))
        f = lerp(5, E, u)
        roll = 1.6 * math.sin(math.pi * seg(lt, fly0, fly1))
    c.save()
    c.translate(W / 2, H / 2); c.rotate(roll); c.scale(1 + abs(roll) * 0.03, 1 + abs(roll) * 0.03); c.translate(-W / 2, -H / 2)
    strip(c, f, focus_k=1.0, buttons=buttons, green=1.0 if lt < fly0 else 1 - seg(lt, fly0, fly0 + 0.5),
          pinned=5 if lt >= browse_end else None)
    if lt >= fly0:
        sp = math.sin(math.pi * seg(lt, fly0, fly1))
        rnd = random.Random(int(lt * 30))
        for i in range(14):
            y = rnd.uniform(60, H - 60)
            x = rnd.uniform(-200, W)
            L = rnd.uniform(200, 600) * sp
            c.drawLine(x, y, x + L, y, strokep(rgb(INK, 0.10 * sp), rnd.uniform(1.5, 3.5)))
        left = W / 2 + (E - f) * PITCH - W / 2
        if left < W:
            feather_board(c, t, left, clamp01((left + 1) / (W * 0.6)), 742)
    c.restore()
    if lt < browse_end + 0.15:
        text(c, '34 CITIES', W / 2, 62, 54, 800, INK, seg(lt, 0.08, 0.25) * (1 - seg(lt, browse_end - 0.1, browse_end + 0.15)), 'center')
    if browse_end - 0.2 <= lt < tidy_end:
        finger(c, (960, 560), seg(lt, browse_end - 0.2, browse_end - 0.05) * (1 - seg(lt, tap + 0.1, tap + 0.35)),
               seg(lt, tap - 0.08, tap), (lt - tap) / 0.4 if lt >= tap else -1)


def shot13(c, t):
    t0 = bar(13)
    lt = t - t0
    z = lerp(1.0, 1.025, lt / BAR)
    cx, cy = clamp_cam(W / 2 + 12 * lt / BAR, H / 2 + 6 * lt / BAR, z)
    c.save(); camera(c, cx, cy, z)
    tokyo_board(c, t, 742 + int(lt * 10))
    c.restore()


# ============================================================ NYC / 14 ======
CREAM = PAL['cream']
NYC_W1 = river_path(band_pts([0.3, -0.05, 0.28, 0.3, 0.3, 0.6, 0.26, 0.85, 0.22, 1.05]), 30 * S)[1]
NYC_W2 = river_path(band_pts([0.62, -0.05, 0.6, 0.25, 0.54, 0.5, 0.48, 0.72, 0.4, 1.05]), 22 * S)[1]
NYC_COLS = ['ee352e', '00933c', 'b933ad', '0039a6', 'ff6319']


def nyc_board(c, t):
    bg(c, CREAM)
    for wf in (NYC_W1, NYC_W2):
        c.drawPath(wf, fillp(rgb(CREAM['water'])))
    vignette(c)
    wat = skia.Op(NYC_W1, NYC_W2, skia.PathOp.kUnion_PathOp)
    lines = [Track([(300, 300), (900, 260), (1500, 420)]), Track([(1250, 180), (1700, 620), (1400, 900)]),
             Track([(200, 700), (800, 640), (1250, 180)])]
    for tr, col in zip(lines, NYC_COLS):
        draw_line(c, tr, col, CREAM, wat)
    for p, kind in (((300, 300), SQUARE), ((900, 260), CIRCLE), ((1500, 420), TRIANGLE), ((1250, 180), CIRCLE),
                    ((1700, 620), SQUARE), ((1400, 900), CIRCLE), ((200, 700), TRIANGLE), ((800, 640), SQUARE)):
        station(c, kind, p)


def shot14(c, t):
    t0 = bar(14)
    lt = t - t0
    half = BAR / 2
    if lt < half:
        z = 2.5
        cx, cy = clamp_cam(1600, 150, z)
        c.save(); camera(c, cx, cy, z)
        nyc_board(c, t)
        ticks = [0.15, 0.45, 0.75, 1.05]
        n = 996 + sum(1 for tt in ticks if lt >= tt)
        hud_controls(c)
        hud_clock(c, 'SUN', n, 0.46 + lt * 0.01)
        hud_line_dots(c, NYC_COLS, 3)
        c.restore()
    else:
        l2 = lt - half
        unlock = both(seg(l2, 0.4, 0.62))
        strip(c, 2, best='1000 / 1000', badges=2, locked=3, unlock=unlock)


# ========================================================== SPLASH / END ====
BLUE_L, ORANGE_L, GOLD_L = '5c5cff', 'f15a29', 'e8ce6b'


def logo(c, cx, cy, s, lanes=1.0, ring=1.0, diag=1.0, top=-50, bg_col='efede7'):
    """icon.svg drawn about its ring centre; lanes run up off the top."""
    def X(v):
        return cx + (v - 540) * s

    def Y(v):
        return cy + (v - 540) * s
    lane_bottom = Y(335)
    if lanes > 0:
        bot = lerp(top, lane_bottom, lanes)
        for x0, col in ((368, BLUE_L), (550, ORANGE_L)):
            c.drawRect(skia.Rect.MakeLTRB(X(x0), top, X(x0 + 160), bot), fillp(rgb(col)))
    if diag > 0:
        L = 1400 * diag / s
        for (sx, sy, dx, col) in ((420, 660, -1, ORANGE_L), (660, 660, 1, BLUE_L)):
            c.drawLine(X(sx), Y(sy), X(sx + dx * L * 0.7071), Y(sy + L * 0.7071),
                       strokep(rgb(col), 160 * s, cap=skia.Paint.kButt_Cap))
    if ring > 0:
        rr = 250 * s
        c.drawCircle(cx, cy, rr, fillp(rgb(bg_col)))
        rect = skia.Rect.MakeXYWH(cx - rr, cy - rr, rr * 2, rr * 2)
        arc = skia.Path(); arc.addArc(rect, -90, 360 * ring)
        c.drawPath(arc, strokep(rgb('000000'), 100 * s, cap=skia.Paint.kButt_Cap if ring < 1 else skia.Paint.kButt_Cap))


def shot15_16(c, t, prev_frame=None):
    t15, t16 = bar(15), bar(16)
    c.drawRect(skia.Rect.MakeWH(W, H), fillp(rgb(PAPER)))
    s0 = 0.62
    if t < t16:
        st = t - (t15 + 0.3)
        lanes = both(seg(st, 0.10, 0.55))
        ring = both(seg(st, 0.45, 0.90))
        diag = both(seg(st, 0.80, 1.20))
        logo(c, W / 2, H / 2, s0, lanes, ring, diag)
    else:
        lt = t - t16
        u = glide(seg(lt, 0.0, 0.6))
        # the gold line lies under the mark
        g = both(seg(lt, 1.0, 1.4))
        gold = path_of([(705, 1080), (915, 870), (1605, 870), (1935, 540)])
        pm = skia.PathMeasure(gold, False)
        if g > 0:
            seg_p = skia.Path(); pm.getSegment(0, pm.getLength() * g, seg_p, True)
            c.drawPath(seg_p, strokep(rgb(GOLD_L), 24, cap=skia.Paint.kButt_Cap, join=skia.Paint.kMiter_Join))
        cx = lerp(W / 2, -105 + 540 * 1.08, u)
        cy = lerp(H / 2, -150 + 540 * 1.08, u)
        s = lerp(s0, 1.08, u)
        logo(c, cx, cy, s, 1, 1, 1, bg_col=PAPER)
        a1 = out(seg(lt, 0.6, 0.9))
        text(c, 'Transit', 960, 456, 252, 800, '000000', a1)
        text(c, 'Keep the city moving.', 972, 552, 66, 400, '4a4f55', out(seg(lt, 0.8, 1.1)))
        for i, (kind, x) in enumerate(((CIRCLE, 1080), (TRIANGLE, 1290), (SQUARE, 1501))):
            k = out(seg(lt, 1.3 + 0.12 * i, 1.5 + 0.12 * i))
            if k > 0:
                r = {CIRCLE: 28, TRIANGLE: 32, SQUARE: 33}[kind] * lerp(0.5, 1, k)
                p = shape_path(kind, r, (x, 870 + (6 if kind == TRIANGLE else 0)))
                c.drawPath(p, fillp(rgb(PAPER, k)))
                c.drawPath(p, strokep(rgb('000000', k), 12, join=skia.Paint.kMiter_Join))
        ba = out(seg(lt, 1.75, 2.05))
        if ba > 0:
            rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(972, 630, 354, 105), 15, 15)
            c.drawRRect(rr, fillp(rgb('000000', ba)))
            c.drawRRect(rr, strokep(rgb('a6a6a6', ba), 2.2))
            tri = path_of([(1004, 656), (1044, 682), (1004, 708)], True)
            c.drawPath(tri, strokep(rgb(WHITE, ba), 4, join=skia.Paint.kRound_Join))
            text(c, 'GET IT ON', 1068, 666, 19, 500, WHITE, ba)
            text(c, 'Google Play', 1066, 712, 42, 400, WHITE, ba)
    if prev_frame is not None and t < t15 + 0.27:
        a = 1 - seg(t, t15, t15 + 0.27)
        c.drawImage(prev_frame, 0, 0, skia.SamplingOptions(), skia.Paint(Alphaf=a))


def events12_16():
    t0 = bar(12)
    for i in range(5):
        ev(t0 + 0.12 + i * 0.2, 'plink', [0, 1, 2, 3, 4][i], 2, 0.55, 0.3 - i * 0.15)
    ev(t0 + 1.12, 'plink', 0, 3, 0.8); ev(t0 + 1.12, 'haptic')
    ev(t0 + 1.55, 'swell')
    ev(bar(13), 'chime', 0, 1, 1.0)
    t13 = bar(13)
    rnd = random.Random(21)
    for i in range(16):
        v = rnd.choice(['tik', 'tok', 'plink', 'pluck'])
        ev(t13 + i * SIX, v, rnd.randint(0, 4), 3 if v == 'tik' else 2, 0.45, rnd.uniform(-0.35, 0.35))
    for q in range(8):
        ev(t13 + q * BEAT / 2, 'pulse', 0 if q % 2 == 0 else 3, 0, 0.65)
    for i, tt in enumerate([0.0, 0.33, 0.65, 0.98, 1.3, 1.63, 1.96, 2.28]):
        ev(t13 + tt, 'pluck', [0, 2, 4, 3, 1, 2, 0, 4][i], 1, 0.4, (-0.3 if i % 2 else 0.3))
    t14 = bar(14)
    for i, tt in enumerate([0.15, 0.45, 0.75]):
        ev(t14 + tt, 'pluck', [0, 1, 2][i], 2, 0.9, 0.3)
    ev(t14 + 1.05, 'chime', 0, 1, 1.0, 0.3)
    ev(t14 + BAR / 2 + 0.4, 'chime', 0, 2, 0.9, 0.2)
    t15 = bar(15)
    st = t15 + 0.3
    ev(st + 0.10, 'pluck', 0, 2, 0.9); ev(st + 0.90, 'pluck', 3, 1, 0.9); ev(st + 1.20, 'pluck', 0, 1, 1.0)
    t16 = bar(16)
    for i in range(3):
        ev(t16 + 1.3 + 0.12 * i, 'plink', [0, 2, 4][i], 2, 0.6, 0.2 + 0.1 * i)
    ev(t16 + 1.75, 'chime', 0, 1, 1.0)
    ev(t16 + 1.76, 'chime', 0, 0, 0.6)
