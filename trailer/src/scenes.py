"""The 16 shots of the Transit trailer, timed to 92 BPM (1 bar = 2.609 s)."""
import math
import random
import skia
from prim import *

EV = []  # audio events: (time, voice, degree, octave, gain, pan)


def ev(t, voice, deg=0, octv=0, gain=1.0, pan=0.0):
    EV.append((t, voice, deg, octv, gain, pan))


def panx(x):
    return max(-0.35, min(0.35, (x - W / 2) / W * 0.7))


# ------------------------------------------------------------- train runner --
class Runner:
    """A train shuttling end to end with the game's brake-in / dwell / pull-away."""

    def __init__(self, track, t0, speed=150.0, dwell=0.8, start=0, direction=1, seed=1):
        self.track = track
        self.sched = []
        ds = track.stop_d
        t, i, dirn = t0, start, direction
        rnd = random.Random(seed)
        for n in range(120):
            self.sched.append((t, t + dwell, ds[i], ds[i], i, dirn, n))
            t += dwell
            j = i + dirn
            if j < 0 or j >= len(ds):
                dirn = -dirn
                j = i + dirn
            L = abs(ds[j] - ds[i])
            T = max(0.5, L / speed * 1.3)
            self.sched.append((t, t + T, ds[i], ds[j], j, dirn, n))
            t += T
            i = j
        self.loads = [[rnd.choice([CIRCLE, TRIANGLE, SQUARE, CIRCLE, SQUARE, TRIANGLE, STAR])
                       for _ in range(rnd.randint(1, 5))] for _ in range(130)]
        self.t0 = t0

    def at(self, t):
        if t <= self.sched[0][0]:
            s = self.sched[0]
            return s[2], s[5], 0, 0.0
        for s in self.sched:
            if s[0] <= t < s[1]:
                u = (t - s[0]) / (s[1] - s[0])
                if s[2] == s[3]:
                    return s[2], s[5], s[6], u
                e = u * u * (3 - 2 * u) * 0.6 + u * 0.4
                return lerp(s[2], s[3], e), s[5], s[6], -1
        s = self.sched[-1]
        return s[3], s[5], s[6], 0

    def draw(self, c, t, col, cars=0, alpha=1.0):
        d, dirn, n, dw = self.at(t)
        load = self.loads[n % len(self.loads)]
        train(c, self.track, d, col, cars, load, None, dirn, alpha)


def amb_wait(seed, t, base=2, amp=2, rate=0.5):
    """Ambient queue: slowly swells and empties, new arrivals scale in."""
    rnd = random.Random(seed)
    kinds = [rnd.choice([CIRCLE, TRIANGLE, SQUARE, CIRCLE, TRIANGLE, SQUARE, DIAMOND]) for _ in range(14)]
    ph = rnd.random() * 6.28
    x = base + amp * (0.5 + 0.5 * math.sin(t * rate + ph))
    n = int(x)
    f = x - n
    sc = [1.0] * n + [f]
    return kinds[:n + 1], sc


# ================================================================ LONDON ====
GREY = PAL['grey']
LON_COLS = ['e32017', '003688', '00782a', 'e0a800', 'b36305', '9b0056', '0098d4']
LON_RIVER = band_pts([-0.05, 0.42, 0.18, 0.46, 0.34, 0.58, 0.5, 0.6, 0.6, 0.52, 0.68, 0.62, 0.8, 0.56, 1.05, 0.5])
_, LON_WATER = river_path(LON_RIVER, 26 * S)

LS = {
    'a': (TRIANGLE, (640, 800)), 'b': (CIRCLE, (1120, 440)), 'c': (SQUARE, (400, 300)),
    'd': (CIRCLE, (700, 250)), 'e': (TRIANGLE, (1400, 280)), 'f': (SQUARE, (1560, 470)),
    'g': (CIRCLE, (1480, 820)), 'h': (SQUARE, (1000, 900)), 'i': (TRIANGLE, (330, 660)),
    'j': (CIRCLE, (250, 900)), 'k': (SQUARE, (1250, 850)), 't': (TRIANGLE, (1000, 470)),
}


def P(k):
    return LS[k][1]


RED = Track([P('a'), P('b')])
BLUE = Track([P('c'), P('d'), P('e')])
BLUE2 = Track([P('c'), P('d'), P('t'), P('e')])
GREEN = Track([P('e'), P('f'), P('g')])
YEL = Track([P('j'), P('h'), P('k'), P('g')])
BROWN = Track([P('i'), P('a'), P('h')])
PURP = Track([P('i'), P('c')])

R_BLUE = Runner(BLUE, -3.0, seed=2, start=0)
R_GREEN = Runner(GREEN, -1.5, seed=3, start=2, direction=-1)
R_RED = Runner(RED, 2.75, seed=4, start=0, dwell=0.5)
R_YEL = Runner(YEL, 18.0, seed=5)
R_BROWN = Runner(BROWN, 18.5, seed=6)
R_PURP = Runner(PURP, 19.0, seed=7)


def bg(c, pal):
    c.drawRect(skia.Rect.MakeWH(W, H), fillp(rgb(pal['bg'])))


def draw_line(c, tr, col, pal, water=None, hills=None, t_grow=None, caps=True, alpha=1.0):
    path = tr.path if t_grow is None else tr.part(0, tr.length * t_grow)
    line_stroke(c, path, col, alpha)
    if water is not None:
        crossing(c, path, water, col, pal, 'bridge', alpha=alpha)
    if hills is not None:
        crossing(c, path, hills, col, pal, 'tunnel', alpha=alpha)
    if caps and (t_grow is None or t_grow >= 1):
        cap_ring(c, tr, col, 1, alpha)
        cap_ring(c, tr, col, -1, alpha)


def london_intro(c, t):
    """Shots 01-03: the first line, the pull-back, the title."""
    # camera: macro 2.2 with a slow push, then a continuous glide out to 1.0
    t1 = bar(2)
    if t < t1:
        z = lerp(2.0, 2.08, t / t1)
        cx, cy = 880, 610
    else:
        u = glide(seg(t, t1, t1 + 2.45))
        z = lerp(2.08, 1.0, u)
        cx, cy = lerp(880, 960, u), lerp(610, 540, u)
    cx, cy = clamp_cam(cx, cy, z)
    c.save()
    camera(c, cx, cy, z)
    bg(c, GREY)
    draw_water(c, LON_WATER, GREY)
    vignette(c)
    draw_line(c, BLUE, LON_COLS[1], GREY, LON_WATER)
    draw_line(c, GREEN, LON_COLS[2], GREY, LON_WATER)
    g0, g1 = 0.35, 1.9
    grow = both(seg(t, g0, g1))
    if t >= g0:
        draw_line(c, RED, LON_COLS[0], GREY, LON_WATER, t_grow=grow)
        if grow >= 1:
            k = out(seg(t, g1, g1 + 0.3))
            cap_ring(c, RED, LON_COLS[0], 1, 1, k)
            cap_ring(c, RED, LON_COLS[0], -1, 1, k)
    R_BLUE.draw(c, t, LON_COLS[1], 1)
    R_GREEN.draw(c, t, LON_COLS[2])
    if t >= 2.75:
        R_RED.draw(c, t, LON_COLS[0], alpha=out(seg(t, 2.75, 3.0)))
    for key in 'abcdefghij':
        kind, p = LS[key]
        station(c, kind, p)
    kk = out(seg(t, 4.3, 4.6))
    if t >= 4.3:
        station(c, LS['k'][0], P('k'), kk, kk)
    for i, key in enumerate('cdefghij'):
        kinds, sc = amb_wait(10 + i, t, 1, 2, 0.6)
        waiting(c, P(key), kinds, sc)
    # finger
    fa = seg(t, 0.05, 0.25) * (1 - seg(t, 2.0, 2.3))
    fp = RED.pos(RED.length * grow)[0] if t >= g0 else P('a')
    ripple = -1
    if 0.25 <= t < 0.65:
        ripple = (t - 0.25) / 0.4
    if 1.9 <= t < 2.3:
        ripple = (t - 1.9) / 0.4
    finger(c, fp, fa, press=seg(t, 0.2, 0.35), ripple=ripple)
    # HUD (a crop of the real frame: it is part of the picture)
    hud_controls(c)
    frac = 0.015 + t * 0.004
    delivered = 0 if t < 4.0 else (1 if t < 5.6 else (2 if t < 6.8 else 3))
    hud_clock(c, 'MON', delivered, frac)
    hud_line_dots(c, LON_COLS, 3)
    bcount = 3 if t < 1.35 else 2
    hud_dock(c, [('loco', 0, None), ('car', 0, None), ('inter', 0, None),
                 ('bridge', bcount, seg(t, 1.35, 1.6) if 1.35 <= t < 1.6 else None)])
    c.restore()
    # SHOT 03: title over a paper wash
    t3, t4 = bar(3), bar(4)
    if t >= t3 - 0.1:
        a = seg(t, t3, t3 + 0.27) * (1 - seg(t, t4 - 0.2, t4 - 0.02))
        c.drawRect(skia.Rect.MakeWH(W, H), fillp(rgb(PAPER, 0.72 * a)))
        text(c, 'Transit', W / 2, 560, 138, 800, INK, a, 'center')
        text(c, 'Design the subway of a growing city.', W / 2, 628, 40, 400, '3a3f45', a, 'center')
        gl = both(seg(t, t3 + 0.35, t3 + 0.75))
        y = 700
        if gl > 0:
            c.drawLine(820, y, lerp(820, 1100, gl), y, strokep(rgb('e8ce6b', a), 9, cap=skia.Paint.kButt_Cap))
        for i, (kind, x) in enumerate(((CIRCLE, 875), (TRIANGLE, 960), (SQUARE, 1045))):
            k = out(seg(t, t3 + 0.75 + 0.12 * i, t3 + 0.95 + 0.12 * i))
            if k > 0:
                p = shape_path(kind, 13 * lerp(0.6, 1, k), (x, y))
                c.drawPath(p, fillp(rgb(PAPER, a * k)))
                c.drawPath(p, strokep(rgb(INK, a * k), 5, join=skia.Paint.kMiter_Join))


def events_intro():
    ev(0.25, 'pluck', 0, 0, 1.0, panx(640)); ev(0.25, 'haptic')
    ev(1.9, 'pluck', 1, 1, 1.0, panx(1120)); ev(1.9, 'haptic')
    ev(1.35, 'plink', 0, 1, 0.35, -0.3)
    ev(bar(2) + 0.15, 'pulse', 0, 0, 0.8)
    ev(4.3, 'chime', 2, 1, 0.7, panx(1250))
    for i, tt in enumerate([3.1, 3.6, 4.0, 4.6, 5.0]):
        ev(tt, 'tik', i % 5, 3, 0.6, ((i * 37) % 7 - 3) / 10)
    for q in range(12):
        ev(bar(2) + 0.15 + q * BEAT, 'pulse', 0, 0, 0.55 if q % 2 else 0.7)
    t3 = bar(3)
    ev(t3 + 0.05, 'chime', 0, 1, 0.9)
    for i in range(3):
        ev(t3 + 0.75 + 0.12 * i, 'plink', [0, 2, 4][i], 2, 0.5, (i - 1) * 0.2)


# ============================================================ SHOT 04 ======
S4_LINE = Track([(120, 560), (720, 560), (1640, 560)])


def shot04(c, t):
    t0 = bar(4)
    lt = t - t0
    z = 1.6
    # train: in from the right, brake to the square, dwell, pull away left
    d_st = S4_LINE.stop_d[1]
    arrive, leave = 1.05, 2.05
    if lt < arrive:
        u = lt / arrive
        d = lerp(S4_LINE.length - 60, d_st, 1 - (1 - u) ** 2)
    elif lt < leave:
        d = d_st
    else:
        u = lt - leave
        d = d_st - 60 * u * u - 20 * u
    follow = -40 * both(seg(lt, leave, leave + 0.55))
    cx, cy = clamp_cam(900 + follow, 560, z)
    c.save()
    camera(c, cx, cy, z)
    bg(c, GREY)
    vignette(c)
    line_stroke(c, S4_LINE.path, LON_COLS[1])
    # riders: squares get off, circles on
    riders = [SQUARE, SQUARE, CIRCLE, CIRCLE, CIRCLE]
    rs = [1 - out(seg(lt, arrive + 0.10, arrive + 0.30)),
          1 - out(seg(lt, arrive + 0.26, arrive + 0.46)),
          1.0,
          out(seg(lt, arrive + 0.55, arrive + 0.75)),
          out(seg(lt, arrive + 0.72, arrive + 0.92))]
    # once squares are gone the rest shuffle up
    if lt > arrive + 0.46:
        riders = [CIRCLE, CIRCLE, CIRCLE]
        rs = [1.0, rs[3], rs[4]]
    train(c, S4_LINE, d, LON_COLS[1], 1, riders, rs, -1)
    station(c, CIRCLE, (120, 560))
    station(c, SQUARE, (720, 560))
    station(c, TRIANGLE, (1640, 560))
    # queue at the square: circle, triangle ... two more arrive
    q = [CIRCLE, TRIANGLE, CIRCLE, TRIANGLE]
    qs = [1.0, 1.0, out(seg(lt, 0.30, 0.45)), out(seg(lt, 0.62, 0.77))]
    b1 = out(seg(lt, arrive + 0.55, arrive + 0.75))
    b2 = out(seg(lt, arrive + 0.72, arrive + 0.92))
    if lt > arrive + 0.92:
        q, qs = [TRIANGLE, TRIANGLE], [1.0, 1.0]
    else:
        qs[0] *= (1 - b1)
        qs[2] *= (1 - b2)
    waiting(c, (720, 560), q, qs)
    c.restore()


def events04():
    t0 = bar(4)
    ev(t0 + 0.30, 'tik', 4, 3, 0.8, -0.05)
    ev(t0 + 0.62, 'tik', 2, 3, 0.8, -0.05)
    ev(t0 + 1.05, 'pulse', 0, 0, 0.9, 0.1)
    ev(t0 + 1.15, 'plink', 1, 2, 0.4, 0.0); ev(t0 + 1.31, 'plink', 0, 2, 0.4, 0.0)
    ev(t0 + 1.60, 'tok', 0, 2, 1.0, -0.05); ev(t0 + 1.77, 'tok', 2, 2, 1.0, -0.05)
    ev(t0 + 2.1, 'pulse', 3, -1, 0.8, -0.1)
    for q in range(4):
        ev(t0 + q * BEAT, 'pulse', 0, 0, 0.45)


# ============================================================ SHOT 05 ======
S5 = {'y1': (CIRCLE, (560, 760)), 'y2': (SQUARE, (860, 760)), 'y3': (CIRCLE, (1060, 560)),
      'dm': (DIAMOND, (1340, 380)), 'q2': (SQUARE, (1300, 830)),
      'b1': (TRIANGLE, (330, 440)), 'b2': (CIRCLE, (680, 430)), 'b3': (SQUARE, (960, 370))}
S5_BLUE = Track([S5['b1'][1], S5['b2'][1], S5['b3'][1]])
S5_Y0 = Track([S5['y1'][1], S5['y2'][1], S5['y3'][1]])
S5_T = [0.25, 0.85, 1.55, 2.15]  # cap grab, diamond, square, loop close (local)


def shot05(c, t):
    t0 = bar(5)
    lt = t - t0
    z = 1.3
    cx, cy = clamp_cam(lerp(930, 990, both(lt / BAR)), 590, z)
    c.save()
    camera(c, cx, cy, z)
    bg(c, GREY)
    draw_water(c, LON_WATER, GREY)
    vignette(c)
    draw_line(c, S5_BLUE, LON_COLS[1], GREY, LON_WATER)
    y = LON_COLS[3]
    stops = [S5['y1'][1], S5['y2'][1], S5['y3'][1]]
    cap0 = cap_ring_pos(S5_Y0)
    waypoints = [cap0, S5['dm'][1], S5['q2'][1], S5['y1'][1]]
    times = S5_T
    fp = cap0
    if lt >= times[0]:
        added = [k for k, tt in zip(['dm', 'q2'], times[1:3]) if lt >= tt]
        stops2 = stops + [S5[k][1] for k in added]
        closed = lt >= times[3]
        # finger position along its drag
        for i in range(3):
            if times[i] <= lt < times[i + 1]:
                u = both((lt - times[i]) / (times[i + 1] - times[i]))
                fp = lerp2(waypoints[i], waypoints[i + 1], u)
                break
        else:
            fp = waypoints[-1]
        if closed:
            tr = Track(stops2 + [S5['y1'][1]])
            draw_line(c, tr, y, GREY, LON_WATER, caps=False)
        else:
            tr = Track(stops2)
            line_stroke(c, tr.path, y)
            crossing(c, tr.path, LON_WATER, y, GREY)
            cap_ring(c, tr, y, -1)
            prev = Track([stops2[-1], fp])
            line_stroke(c, prev.path, y, 0.9)
            crossing(c, prev.path, LON_WATER, y, GREY)
    else:
        draw_line(c, S5_Y0, y, GREY, LON_WATER)
    # a yellow train already running on the line
    d = lerp(S5_Y0.stop_d[0] + 40, S5_Y0.stop_d[1] + 120, both(lt / 2.4))
    train(c, S5_Y0, d, y, 0, [TRIANGLE, SQUARE])
    for k, (kind, p) in S5.items():
        station(c, kind, p)
    waiting(c, S5['dm'][1], [CIRCLE, SQUARE, TRIANGLE])
    waiting(c, S5['b2'][1], [SQUARE, DIAMOND])
    waiting(c, S5['y2'][1], [DIAMOND, TRIANGLE, CIRCLE])
    fa = seg(lt, 0.0, 0.2) * (1 - seg(lt, times[3] + 0.15, times[3] + 0.4))
    rip = -1
    for tt in times:
        if tt <= lt < tt + 0.4:
            rip = (lt - tt) / 0.4
    finger(c, fp, fa, seg(lt, times[0] - 0.1, times[0]), rip)
    hud_controls(c); hud_clock(c, 'TUE', 41, 0.3); hud_line_dots(c, LON_COLS, 3)
    hud_dock(c, [('loco', 0, None), ('car', 0, None), ('inter', 0, None), ('bridge', 3 if lt < 1.2 else 1, None)])
    c.restore()
    a = seg(lt, 0.15, 0.35)
    text(c, 'DRAW', 484, 170, 82, 800, INK, a)


def cap_ring_pos(tr):
    a, b = tr.pts[-2], tr.pts[-1]
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
    return (b[0] + (b[0] - a[0]) / L * 30 * S, b[1] + (b[1] - a[1]) / L * 30 * S)


def events05():
    t0 = bar(5)
    ev(t0 + S5_T[0], 'pluck', 0, 1, 0.8, 0.1); ev(t0 + S5_T[0], 'haptic')
    for i, (deg, oc) in enumerate([(1, 1), (2, 1), (0, 2)]):
        tt = t0 + S5_T[i + 1]
        ev(tt, 'pluck', deg, oc, 1.0, [0.2, 0.15, -0.2][i]); ev(tt, 'haptic')
    ev(t0 + S5_T[3], 'chime', 0, 1, 0.8)
    for q in range(4):
        ev(t0 + q * BEAT, 'pulse', 0, 0, 0.5)
    ev(t0 + 0.9, 'tok', 3, 2, 0.5, 0.2)


# ============================================================ SHOT 06 ======
S6_GREEN = Track([(560, 830), (980, 830), (1380, 760)])
S6_RED = Track([(420, 300), (860, 380)])
S6_BLUE = Track([(1200, 300), (1560, 450)])


def shot06(c, t):
    t0 = bar(6)
    lt = t - t0
    u = glide(seg(lt, 0.45, 1.25))
    z = lerp(1.5, 1.2, u)
    cx, cy = clamp_cam(lerp(640, 960, u), lerp(540, 640, u), z)
    c.save()
    camera(c, cx, cy, z)
    bg(c, GREY)
    draw_water(c, LON_WATER, GREY)
    vignette(c)
    draw_line(c, S6_RED, LON_COLS[0], GREY, LON_WATER)
    draw_line(c, S6_BLUE, LON_COLS[1], GREY, LON_WATER)
    draw_line(c, S6_GREEN, LON_COLS[2], GREY, LON_WATER)
    for kind, p in ((CIRCLE, (560, 830)), (SQUARE, (980, 830)), (TRIANGLE, (1380, 760)),
                    (TRIANGLE, (420, 300)), (CIRCLE, (860, 380)), (SQUARE, (1200, 300)), (CIRCLE, (1560, 450))):
        pass
    # locomotive token: pressed at 0.3, carried along an arc, dropped at 1.2
    coin = (DOCK_X, DOCK_Y[0])
    drop = (800, 830)
    dt, ddrop = 0.30, 1.20
    carp, cdrop = 1.45, 2.15
    loco_count = 1 if lt < ddrop else 0
    car_count = 1 if lt < cdrop else 0
    # the new train on the line
    if lt >= ddrop:
        d0 = S6_GREEN.stop_d[0] + (drop[0] - 560)
        dd = d0 + 110 * (lt - ddrop) ** 1.3
        cars = 1 if lt >= cdrop else 0
        train(c, S6_GREEN, dd, LON_COLS[2], cars, [CIRCLE, TRIANGLE])
    for kind, p in ((CIRCLE, (560, 830)), (SQUARE, (980, 830)), (TRIANGLE, (1380, 760)),
                    (TRIANGLE, (420, 300)), (CIRCLE, (860, 380)), (SQUARE, (1200, 300)), (CIRCLE, (1560, 450))):
        station(c, kind, p)
    waiting(c, (980, 830), [TRIANGLE, CIRCLE, TRIANGLE, TRIANGLE])
    waiting(c, (560, 830), [SQUARE, TRIANGLE])
    waiting(c, (860, 380), [SQUARE])
    hud_controls(c); hud_clock(c, 'WED', 67, 0.55); hud_line_dots(c, LON_COLS, 3)
    lp = seg(lt, ddrop, ddrop + 0.25) if ddrop <= lt < ddrop + 0.25 else None
    cp = seg(lt, cdrop, cdrop + 0.25) if cdrop <= lt < cdrop + 0.25 else None
    hud_dock(c, [('loco', loco_count, lp), ('car', car_count, cp), ('inter', 0, None), ('bridge', 2, None)])

    def carry(t_a, t_b, src, dst, kind):
        if t_a <= lt < t_b:
            u = both((lt - t_a) / (t_b - t_a))
            mid = ((src[0] + dst[0]) / 2, min(src[1], dst[1]) - 160)
            p = lerp2(lerp2(src, mid, u), lerp2(mid, dst, u), u)
            grow = out(seg(lt, t_a, t_a + 0.2))
            ang = 0.0
            if kind == 'loco':
                body(c, p, ang, LON_COLS[2], TRAIN_LEN * grow, TRAIN_WID * grow, 0.9)
            else:
                body(c, p, ang, LON_COLS[2], CAR_LEN * grow, TRAIN_WID * 0.9 * grow, 0.9)
            finger(c, p, 1.0, 0.6)
            return True
        return False

    if lt < dt:
        finger(c, (coin[0] + 90 * (1 - seg(lt, 0, dt)), coin[1] + 30), seg(lt, 0, 0.15))
    carry(dt, ddrop, coin, drop, 'loco')
    if ddrop <= lt < carp:
        finger(c, lerp2(drop, (DOCK_X, DOCK_Y[1]), both(seg(lt, ddrop + 0.05, carp))), 0.8)
    carry(carp, cdrop, (DOCK_X, DOCK_Y[1]), (drop[0] + 60, drop[1]), 'car')
    if lt >= cdrop:
        finger(c, (drop[0] + 60, drop[1]), 1 - seg(lt, cdrop, cdrop + 0.3), 0, seg(lt, cdrop, cdrop + 0.4))
    c.restore()


def events06():
    t0 = bar(6)
    ev(t0 + 0.30, 'pluck', 0, 2, 0.7, -0.3); ev(t0 + 0.30, 'haptic')
    ev(t0 + 1.20, 'pulse', 0, 0, 1.0, -0.05); ev(t0 + 1.25, 'plink', 0, 2, 0.5, -0.4)
    ev(t0 + 1.45, 'pluck', 3, 2, 0.7, -0.3); ev(t0 + 1.45, 'haptic')
    ev(t0 + 2.15, 'pulse', 3, 0, 1.0, 0.0); ev(t0 + 2.20, 'plink', 3, 2, 0.5, -0.4)
    for q in range(4):
        ev(t0 + q * BEAT, 'pulse', 0, 0, 0.45)


# ============================================================ SHOT 07 ======
HUB = (960, 560)
S7_RED = Track([(360, 600), HUB, (1600, 560)])
S7_BLUE = Track([(1300, 170), HUB, (720, 900)])


def shot07(c, t):
    t0 = bar(7)
    lt = t - t0
    z = lerp(1.0, 1.3, both(lt / BAR))
    cx, cy = clamp_cam(HUB[0], HUB[1], z)
    c.save()
    camera(c, cx, cy, z)
    bg(c, GREY)
    draw_water(c, LON_WATER, GREY)
    vignette(c)
    draw_line(c, S7_RED, LON_COLS[0], GREY, LON_WATER)
    draw_line(c, S7_BLUE, LON_COLS[1], GREY, LON_WATER)
    drop_t = 1.05
    # red train arrives from the left, triangles step off (transfer)
    ra, rl = 0.55, 1.55
    dh = S7_RED.stop_d[1]
    if lt < ra:
        dr = dh - 300 * (1 - lt / ra) ** 2
    elif lt < rl:
        dr = dh
    else:
        dr = dh + 90 * (lt - rl) ** 1.5 * 2
    off1 = out(seg(lt, ra + 0.1, ra + 0.3)); off2 = out(seg(lt, ra + 0.25, ra + 0.45))
    rr = [TRIANGLE, TRIANGLE, SQUARE, SQUARE]
    rsc = [1 - off1, 1 - off2, 1.0, 1.0]
    if lt > ra + 0.45:
        rr, rsc = [SQUARE, SQUARE], [1, 1]
    train(c, S7_RED, dr, LON_COLS[0], 0, rr, rsc, 1)
    # blue train comes down into the hub and takes the triangles on
    ba, bl = 1.25, 2.1
    dbh = S7_BLUE.stop_d[1]
    if lt < ba:
        db = dbh - 260 * (1 - lt / ba) ** 2
    elif lt < bl:
        db = dbh
    else:
        db = dbh + 120 * (lt - bl) ** 1.5 * 2
    on1 = out(seg(lt, ba + 0.2, ba + 0.4)); on2 = out(seg(lt, ba + 0.35, ba + 0.55))
    train(c, S7_BLUE, db, LON_COLS[1], 0, [CIRCLE, TRIANGLE, TRIANGLE], [1, on1, on2], 1)
    for kind, p in ((SQUARE, (360, 600)), (SQUARE, (1600, 560)), (SQUARE, (1300, 170)), (TRIANGLE, (720, 900))):
        station(c, kind, p)
    ring = lt >= drop_t
    rk = out(seg(lt, drop_t, drop_t + 0.25))
    if ring:
        c.drawCircle(HUB[0], HUB[1], STATION_R + 7.0 * S * rk, strokep(rgb(INK, rk), 3.0 * S))
    station(c, CIRCLE, HUB)
    # the queue at the hub: transferring triangles appear, then board blue
    q = [SQUARE, CIRCLE, TRIANGLE, TRIANGLE]
    qs = [1.0, 1.0, off1 * (1 - on1), off2 * (1 - on2)]
    waiting(c, HUB, q, qs)
    waiting(c, (360, 600), [CIRCLE, TRIANGLE])
    waiting(c, (1600, 560), [CIRCLE])
    hud_controls(c); hud_clock(c, 'THU', 108, 0.7); hud_line_dots(c, LON_COLS, 3)
    hud_dock(c, [('loco', 0, None), ('car', 0, None), ('inter', 1 if lt < drop_t else 0, None), ('bridge', 2, None)])
    # interchange token carried from the dock
    if lt < drop_t:
        src = (DOCK_X, DOCK_Y[2])
        u = both(seg(lt, 0.1, drop_t))
        mid = ((src[0] + HUB[0]) / 2, 380)
        p = lerp2(lerp2(src, mid, u), lerp2(mid, HUB, u), u)
        if lt >= 0.1:
            c.drawCircle(p[0], p[1], 20, strokep(rgb(INK, 0.9), 5))
            c.drawCircle(p[0], p[1], 8, fillp(rgb(INK, 0.9)))
        finger(c, p, seg(lt, 0.0, 0.1), 0.6)
    elif lt < drop_t + 0.4:
        finger(c, HUB, 1 - seg(lt, drop_t, drop_t + 0.35), 0, seg(lt, drop_t, drop_t + 0.4))
    c.restore()
    text(c, 'CONNECT', 484, 170, 82, 800, INK, seg(lt, 0.15, 0.35))


def events07():
    t0 = bar(7)
    ev(t0 + 0.1, 'pluck', 2, 1, 0.7, -0.3); ev(t0 + 0.1, 'haptic')
    ev(t0 + 1.05, 'chime', 3, 1, 0.9)
    ev(t0 + 0.55, 'pulse', 1, 0, 0.9, -0.1)
    ev(t0 + 0.65, 'plink', 1, 2, 0.35); ev(t0 + 0.80, 'plink', 2, 2, 0.35)
    ev(t0 + 1.25, 'pulse', 4, 0, 0.9, 0.05)
    ev(t0 + 1.45, 'tok', 1, 2, 0.9); ev(t0 + 1.60, 'tok', 3, 2, 0.9)
    # red and blue motifs interleave
    for i, tt in enumerate([0.0, 0.33, 0.65, 0.98, 1.63, 1.96, 2.28]):
        ev(t0 + tt, 'pluck', [0, 2, 1, 3, 4, 2, 0][i], 2, 0.35, (-0.25 if i % 2 else 0.25))
    for q in range(4):
        ev(t0 + q * BEAT, 'pulse', 0, 0, 0.5)


# ============================================================ SHOT 08 ======
def london_board(c, t, fast=1.0, extra=False, crowd=0.0, blue_insert=None, night=0.0,
                 day='MON', count=0, frac=0.1, dots=3, dock=None, t_run=None, tri=False):
    tr = t if t_run is None else t_run
    bg(c, GREY)
    draw_water(c, LON_WATER, GREY)
    vignette(c)
    if extra:
        draw_line(c, YEL, LON_COLS[3], GREY, LON_WATER)
        draw_line(c, BROWN, LON_COLS[4], GREY, LON_WATER)
        draw_line(c, PURP, LON_COLS[5], GREY, LON_WATER)
    blue = BLUE if blue_insert is None else blue_insert
    draw_line(c, blue, LON_COLS[1], GREY, LON_WATER)
    draw_line(c, GREEN, LON_COLS[2], GREY, LON_WATER)
    draw_line(c, RED, LON_COLS[0], GREY, LON_WATER)
    R_GREEN.draw(c, tr, LON_COLS[2], 1)
    R_RED.draw(c, tr, LON_COLS[0])
    if blue_insert is None:
        R_BLUE.draw(c, tr, LON_COLS[1], 1)
    if extra:
        R_YEL.draw(c, tr, LON_COLS[3], 1)
        R_BROWN.draw(c, tr, LON_COLS[4])
        R_PURP.draw(c, tr, LON_COLS[5])
    for key in 'abcdefghijk':
        kind, p = LS[key]
        station(c, kind, p)
    if tri:
        station(c, TRIANGLE, P('t'))
    for i, key in enumerate('abcdefghijk'):
        kinds, sc = amb_wait(30 + i, tr, 2 if extra else 1, 4 if extra else 2, 0.7)
        waiting(c, P(key), kinds, sc)


def shot08(c, t):
    t0 = bar(8)
    lt = t - t0
    mid = 0.55  # midnight: the week turns over
    tr = 14.0 + lt * (1.0 if lt < mid else 0.0) + (mid if lt >= mid else 0)
    frac = 0.49 + 0.01 * seg(lt, 0, mid)
    night = 1.0 if lt >= mid - 0.2 else 0.9
    london_board(c, t, t_run=tr, extra=False, tri=False)
    hud_controls(c)
    hud_clock(c, 'SUN' if lt < mid else 'MON', 176, frac + 0.5, night)
    tap = 1.3
    line_land = 1.95
    loco_land = 2.35
    dots = 3 if lt < line_land else 4
    hud_line_dots(c, LON_COLS, dots, pop=(3, seg(lt, line_land, line_land + 0.25)) if lt >= line_land else None)
    loco = 1 if lt >= loco_land else 0
    hud_dock(c, [('loco', loco, seg(lt, loco_land, loco_land + 0.25) if loco_land <= lt < loco_land + 0.25 else None),
                 ('car', 0, None), ('inter', 0, None), ('bridge', 2, None)])
    # the week page
    a = seg(lt, mid, mid + 0.25) * (1 - seg(lt, tap + 0.15, tap + 0.4))
    if a > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), fillp(rgb('fafaf9', 0.9 * a)))
        text(c, 'Week 1', 540, 178, 96, 400, INK, a)
        text(c, 'Which new asset would you like for your metro?', 540, 252, 40, 400, INK, a)
        for i, (x, kind, label) in enumerate(((690, 'line', 'Line'), (1228, 'loco', 'Locomotive'))):
            k = 1.0
            if i == 0 and lt >= tap:
                k = 1 - 0.06 * math.sin(math.pi * seg(lt, tap, tap + 0.2))
            for j in range(6):
                c.drawCircle(x, 598 + j, 138 * k + 4 - j, fillp(skia.Color(0, 0, 0, int(6 * a))))
            c.drawCircle(x, 593, 138 * k, fillp(rgb(INK, a)))
            c.save(); c.translate(x, 593); c.scale(3.2, 3.2); c.translate(-x, -593)
            coin_icon(c, kind, (x, 593), WHITE)
            c.restore()
            text(c, label, x, 830, 54, 400, INK, a, 'center')
        if lt < tap + 0.4:
            fp = lerp2((900, 800), (690, 600), both(seg(lt, mid + 0.3, tap)))
            finger(c, fp, seg(lt, mid + 0.3, mid + 0.45) * (1 - seg(lt, tap + 0.1, tap + 0.4)),
                   seg(lt, tap - 0.1, tap), (lt - tap) / 0.4 if lt >= tap else -1)
    # the chosen line flies to the colour column, then the free locomotive to the dock
    if tap + 0.35 <= lt < line_land:
        u = both(seg(lt, tap + 0.35, line_land))
        p = lerp2((690, 593), (1841, 622), u)
        s = lerp(2.4, 0.9, u)
        c.drawCircle(p[0], p[1], 40 * s, fillp(rgb(INK)))
        coin_icon(c, 'line', p, WHITE, s)
    if line_land + 0.1 <= lt < loco_land:
        u = both(seg(lt, line_land + 0.1, loco_land))
        p = lerp2((W / 2, H / 2), (DOCK_X, DOCK_Y[0]), u)
        c.drawCircle(p[0], p[1], 39, fillp(rgb(INK)))
        coin_icon(c, 'loco', p, WHITE)


def events08():
    t0 = bar(8)
    ev(t0 + 0.55, 'plink', 4, 2, 0.5)
    ev(t0 + 1.30, 'plink', 0, 3, 0.8); ev(t0 + 1.30, 'haptic')
    ev(t0 + 1.95, 'chime', 0, 1, 1.0, 0.3)
    ev(t0 + 2.35, 'chime', 3, 1, 0.9, -0.3)
    ev(t0, 'pulse', 0, 0, 0.5)


# ============================================================ SHOT 09 ======
SAND = PAL['sand']
LIS_MTN = band_pts([0.14, 0.3, 0.44, 0.24, 0.74, 0.32])
LIS_CENTER, LIS_HILL = river_path(LIS_MTN, 40 * S, reach=80 * S)
LIS_COAST = path_of(round_corners([(-20, 1030), (400, 1030), (560, 970), (1000, 970), (1160, 900), (1940, 900), (1940, 1100), (-20, 1100)],
                                  [0, 7], 70), True)
LIS_COLS = ['4a8fcf', 'cea200', '00a88f']
LIS_A = Track([(760, 800), (1000, 110)])
LIS_B = Track([(300, 740), (760, 800), (1300, 700)])

IVORY = PAL['ivory']
TOK_COLS = ['f39700', 'e60012', '00a7db', '009944', '8f76d6', 'b8954a', '9c5e31']
TOK_BAY = path_of(round_corners([(1150, 1100), (1150, 1080), (1400, 830), (1720, 830), (1940, 610), (1940, 1100)], [0, 5], 70), True)
_, TOK_RIVER = river_path([(1267, -60), (1190, 216), (1152, 486), (1114, 756), (1260, 930)], 18 * S)
TOK_ISLE = skia.Path()
TOK_ISLE.addOval(skia.Rect.MakeXYWH(1700 - 80, 960 - 52, 160, 104))
TOK_WATER = skia.Op(TOK_BAY, TOK_RIVER, skia.PathOp.kUnion_PathOp)
TOK_WATER2 = skia.Op(TOK_WATER, TOK_ISLE, skia.PathOp.kDifference_PathOp)


def draw_tokyo_terrain(c):
    bg(c, IVORY)
    c.drawPath(TOK_WATER2, strokep(rgb(IVORY['edge']), 3.0))
    c.drawPath(TOK_WATER2, fillp(rgb(IVORY['water'])))


def shot09(c, t):
    t0 = bar(9)
    lt = t - t0
    half = BAR / 2
    if lt < half:
        z = lerp(1.15, 1.19, lt / half)
        cx, cy = clamp_cam(900, 500, z)
        c.save(); camera(c, cx, cy, z)
        bg(c, SAND)
        c.drawPath(LIS_COAST, strokep(rgb(SAND['edge']), 6))
        c.drawPath(LIS_COAST, fillp(rgb(SAND['water'])))
        draw_hill(c, LIS_CENTER, 40 * S, SAND)
        vignette(c)
        draw_line(c, LIS_B, LIS_COLS[1], SAND, LIS_COAST, LIS_HILL)
        g = both(seg(lt, 0.12, 1.05))
        draw_line(c, LIS_A, LIS_COLS[0], SAND, None, LIS_HILL, t_grow=g)
        fp = LIS_A.pos(LIS_A.length * g)[0]
        for kind, p in ((CIRCLE, (760, 800)), (TRIANGLE, (1000, 110)), (SQUARE, (300, 740)), (CIRCLE, (1300, 700)), (SQUARE, (1320, 500))):
            station(c, kind, p)
        waiting(c, (1000, 110), [CIRCLE, SQUARE])
        waiting(c, (760, 800), [TRIANGLE, TRIANGLE, SQUARE])
        finger(c, fp, seg(lt, 0.0, 0.1) * (1 - seg(lt, 1.05, 1.25)), 0.5, (lt - 1.05) / 0.4 if lt > 1.05 else -1)
        hud_controls(c); hud_clock(c, 'TUE', 212, 0.3); hud_line_dots(c, LIS_COLS, 2 if lt < 1.05 else 2)
        hud_dock(c, [('loco', 0, None), ('car', 0, None), ('inter', 0, None), ('tunnel', 3 if lt < 0.6 else 2,
                     seg(lt, 0.6, 0.85) if 0.6 <= lt < 0.85 else None)])
        c.restore()
    else:
        l2 = lt - half
        z = lerp(1.3, 1.34, l2 / half)
        cx, cy = clamp_cam(1200, 660, z)
        c.save(); camera(c, cx, cy, z)
        draw_tokyo_terrain(c)
        vignette(c)
        other = Track([(700, 300), (1000, 520), (1400, 300)])
        draw_line(c, other, TOK_COLS[1], IVORY, TOK_WATER2)
        tr = Track([(760, 700), (1150, 600), (1700, 960)])
        g = both(seg(l2, 0.1, 1.0))
        base = Track([(760, 700), (1150, 600)])
        draw_line(c, base, TOK_COLS[0], IVORY, TOK_WATER2, caps=False)
        ext = Track([(1150, 600), (1700, 960)])
        line_stroke(c, ext.part(0, ext.length * g), TOK_COLS[0])
        crossing(c, ext.part(0, ext.length * g), TOK_WATER2, TOK_COLS[0], IVORY)
        fp = ext.pos(ext.length * g)[0]
        for kind, p in ((SQUARE, (760, 700)), (CIRCLE, (1150, 600)), (CIRCLE, (1700, 960)), (TRIANGLE, (700, 300)),
                        (CIRCLE, (1000, 520)), (SQUARE, (1400, 300))):
            station(c, kind, p)
        waiting(c, (1700, 960), [SQUARE, TRIANGLE, SQUARE])
        waiting(c, (1150, 600), [TRIANGLE, CIRCLE])
        finger(c, fp, seg(l2, 0.0, 0.1) * (1 - seg(l2, 1.0, 1.2)), 0.5, (l2 - 1.0) / 0.4 if l2 > 1.0 else -1)
        hud_controls(c); hud_clock(c, 'WED', 236, 0.6); hud_line_dots(c, TOK_COLS, 2)
        hud_dock(c, [('loco', 0, None), ('car', 0, None), ('inter', 0, None), ('bridge', 2 if l2 < 0.55 else 1, None)])
        c.restore()


def events09():
    t0 = bar(9)
    half = BAR / 2
    ev(t0 + 0.12, 'pluck', 0, 1, 0.8, 0.0)
    for i in range(4):
        ev(t0 + 0.45 + i * SIX, 'pluck', 2, 2, 0.35, 0.05)
    ev(t0 + 1.05, 'pluck', 3, 1, 0.9, 0.05)
    ev(t0 + 0.6, 'plink', 0, 1, 0.5, -0.4)
    ev(t0 + half + 0.1, 'pluck', 1, 1, 0.8)
    ev(t0 + half + 0.55, 'pluck', 4, 1, 0.8, 0.2)
    ev(t0 + half + 1.0, 'pluck', 0, 2, 0.9, 0.3)
    for q in range(8):
        ev(t0 + q * BEAT / 2, 'pulse', 0 if q % 2 == 0 else 3, 0, 0.55)


# ======================================================== SHOTS 10-11 ======
def shot10(c, t):
    t0 = bar(10)
    lt = t - t0
    half = BAR / 2
    tr = 20.0 + lt * 2.0
    crowd = lerp(0.35, 0.6, seg(lt, 0, half)) if lt < half else lerp(0.6, 0.8, seg(lt, half, BAR - BEAT))
    queue = [CIRCLE, SQUARE, CIRCLE, DIAMOND, SQUARE, CIRCLE, SQUARE, CIRCLE, SQUARE]
    if lt < half:
        z, cx, cy = 1.0, W / 2, H / 2
    else:
        z = lerp(1.0, 1.4, both(seg(lt, half, BAR)))
        cx, cy = clamp_cam(lerp(W / 2, P('t')[0], both(seg(lt, half, half + 0.6))),
                           lerp(H / 2, P('t')[1], both(seg(lt, half, half + 0.6))), z)
    c.save(); camera(c, cx, cy, z)
    london_board(c, t, t_run=tr, extra=True, tri=True)
    crowding(c, P('t'), crowd)
    waiting(c, P('t'), queue, [1.0] * 8 + [out(seg(lt, half + 0.3, half + 0.45))])
    hud_controls(c, fast=lt >= 0.25)
    hud_clock(c, 'THU', 412 + int(lt * 6), 0.78 + lt * 0.02, 1.0)
    hud_line_dots(c, LON_COLS, 6)
    hud_dock(c, [('loco', 0, None), ('car', 0, None), ('inter', 0, None), ('bridge', 1, None)])
    if lt < 0.55:
        finger(c, (204, 60), seg(lt, 0.0, 0.08) * (1 - seg(lt, 0.3, 0.55)), seg(lt, 0.15, 0.25), (lt - 0.25) / 0.4 if lt > 0.25 else -1)
    c.restore()


def shot11(c, t):
    t0 = bar(11)
    lt = t - t0
    z = 1.4
    cx, cy = clamp_cam(P('t')[0], P('t')[1], z)
    tr = 20.0 + BAR * 2.0 + lt * 1.0
    c.save(); camera(c, cx, cy, z)
    press, release = 0.15, 0.75
    # the blue line's middle is pulled down onto the crowded triangle
    grab = (1050, 250)
    if lt < press:
        blue = BLUE
    elif lt < release:
        fp = lerp2(grab, P('t'), both(seg(lt, press, release)))
        blue = Track([P('c'), P('d'), fp, P('e')])
    else:
        blue = BLUE2
    london_board(c, t, t_run=tr, extra=True, tri=True, blue_insert=blue)
    # blue train arrives at the triangle
    arr, dep = 1.15, 1.95
    dT = BLUE2.stop_d[2]
    if lt < release:
        db = BLUE2.stop_d[1] + 30
    elif lt < arr:
        u = seg(lt, release, arr)
        db = lerp(BLUE2.stop_d[1] + 30, dT, 1 - (1 - u) ** 2)
    elif lt < dep:
        db = dT
    else:
        db = dT + 150 * (lt - dep) ** 1.4
    queue = [CIRCLE, SQUARE, CIRCLE, DIAMOND, SQUARE, CIRCLE, SQUARE, CIRCLE, SQUARE]
    board_t = [arr + 0.08 + i * SIX * 0.5 for i in range(9)]
    qs = [1 - out(seg(lt, bt, bt + 0.12)) for bt in board_t]
    rs = [out(seg(lt, bt, bt + 0.12)) for bt in board_t]
    train(c, BLUE2, db, LON_COLS[1], 1, [TRIANGLE] + queue[:5] + queue[5:], [1.0] + rs[:5] + rs[5:], 1)
    station(c, TRIANGLE, P('t'))
    frac = 0.8 if lt < arr + 0.3 else lerp(0.8, 0.0, both(seg(lt, arr + 0.3, arr + 1.2)))
    crowding(c, P('t'), frac)
    waiting(c, P('t'), queue, qs)
    rip = (lt - release) / 0.4 if release <= lt < release + 0.4 else -1
    fpos = grab if lt < press else (lerp2(grab, P('t'), both(seg(lt, press, release))))
    finger(c, fpos, seg(lt, 0, 0.1) * (1 - seg(lt, release + 0.1, release + 0.4)), seg(lt, press - 0.1, press), rip)
    hud_controls(c, fast=False)
    hud_clock(c, 'THU', 420 + (9 if lt > arr + 0.8 else 0), 0.83, 1.0)
    hud_line_dots(c, LON_COLS, 6)
    hud_dock(c, [('loco', 0, None), ('car', 0, None), ('inter', 0, None), ('bridge', 1, None)])
    c.restore()
    text(c, 'RESHAPE', 484, 170, 82, 800, INK, seg(lt, release, release + 0.2))


def events10_11():
    t0 = bar(10)
    ev(t0 + 0.25, 'plink', 2, 2, 0.6, -0.4)
    # fast-forward: double density
    rnd = random.Random(9)
    for i in range(10):
        tt = t0 + 0.3 + i * SIX
        v = rnd.choice(['tik', 'tok', 'plink', 'tik'])
        ev(tt, v, rnd.randint(0, 4), 3 if v == 'tik' else 2, 0.6, rnd.uniform(-0.3, 0.3))
    for q in range(6):
        ev(t0 + q * BEAT / 2, 'pulse', 0 if q % 2 == 0 else 3, 0, 0.6)
    # the overcrowding clock on eighths, then one beat of nothing
    for i in range(5):
        ev(t0 + 0.33 + BEAT + i * BEAT / 2, 'tick', 0, 2, 0.9 + 0.1 * i, 0.05)
    t1 = bar(11)
    ev(t1 + 0.75, 'pluck', 0, 1, 1.0, 0.0); ev(t1 + 0.75, 'haptic')
    ev(t1 + 1.15, 'pulse', 0, 0, 0.9)
    for i in range(9):
        ev(t1 + 1.23 + i * SIX * 0.5, 'tok', [0, 1, 2, 3, 4, 3, 2, 1, 0][i], 2, 0.8, 0.02 * (i - 4))
    ev(t1 + 2.1, 'chime', 0, 1, 1.0)
    for q in range(2, 4):
        ev(t1 + q * BEAT, 'pulse', 0, 0, 0.5)
