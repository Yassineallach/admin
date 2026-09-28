"""Drawing primitives for the Transit trailer, ported from the game's own
drawing rules (scripts/main.gd, shapes.gd, config.gd). Game units are 1280x720;
the trailer renders at 1920x1080, so every game size is multiplied by S."""
import math
import skia

W, H = 1920, 1080
S = 1.5
BPM = 92.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
SIX = BEAT / 4


def bar(n):
    return (n - 1) * BAR


# ------------------------------------------------------------------ colour --
def rgb(h, a=1.0):
    h = h.lstrip('#')
    return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16),
                      int(round(255 * max(0.0, min(1.0, a)))))


def mix(h1, h2, u):
    h1 = h1.lstrip('#'); h2 = h2.lstrip('#')
    c = []
    for i in (0, 2, 4):
        a = int(h1[i:i + 2], 16); b = int(h2[i:i + 2], 16)
        c.append(int(round(a + (b - a) * max(0.0, min(1.0, u)))))
    return '%02x%02x%02x' % tuple(c)


PAPER = 'efede7'
INK = '262a2e'
MUTED = '8b9099'
WHITE = 'ffffff'
DANGER = 'd7263d'
BRIDGE = '9aa0a6'

PAL = {
    'grey':  {'bg': 'f0f0f0', 'water': 'd9ebf7', 'edge': 'ffffff', 'rock': 'ecd6c8', 'rock_edge': 'dcc0ad'},
    'cream': {'bg': 'f5edd8', 'water': '8fbde0', 'edge': 'f5edd8', 'rock': 'f2c4a8', 'rock_edge': 'e6ac8c'},
    'ivory': {'bg': 'fbfae8', 'water': 'cfe6f5', 'edge': '5aa8d0', 'rock': 'f7c9ab', 'rock_edge': 'e9b18c'},
    'sand':  {'bg': 'e9e5f0', 'water': 'bcdcf2', 'edge': 'f0e2c4', 'rock': 'f4c8b0', 'rock_edge': 'e3ab90'},
    'warm':  {'bg': 'f6ece0', 'water': 'dceaf3', 'edge': '9fc6dd', 'rock': 'f3c3a4', 'rock_edge': 'e0a682'},
}

# config.gd sizes, in trailer pixels
STATION_R = 17.0 * S
KEYLINE = 4.5 * S
ROUTE_W = 11.0 * S
ROUTE_CURVE = 30.0 * S
TRAIN_LEN = 34.0 * S
TRAIN_WID = 20.0 * S
CAR_LEN = 22.0 * S
CAR_GAP = 4.0 * S
RIDER_R = 4.0 * S
WAIT_R = 5.5 * S

CIRCLE, TRIANGLE, SQUARE, DIAMOND, CROSS, STAR, FAN, OVAL = range(8)


# ------------------------------------------------------------------ easing --
def clamp01(x):
    return max(0.0, min(1.0, x))


def both(t):
    u = clamp01(t)
    return u * u * (3 - 2 * u)


def glide(t):
    u = clamp01(t)
    return u * u * u * (u * (u * 6 - 15) + 10)


def out(t):
    u = 1 - clamp01(t)
    return 1 - u * u * u


def into(t):
    u = clamp01(t)
    return u * u * u


def fly(t, p=2.2):
    u = clamp01(t)
    a = u ** p
    b = (1 - u) ** p
    return a / max(a + b, 1e-5)


def seg(t, a, b):
    if b <= a:
        return 1.0 if t >= b else 0.0
    return clamp01((t - a) / (b - a))


def lerp(a, b, u):
    return a + (b - a) * u


def lerp2(p, q, u):
    return (p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u)


# ------------------------------------------------------------------ paints --
def fillp(c):
    return skia.Paint(AntiAlias=True, Color=c, Style=skia.Paint.kFill_Style)


def strokep(c, w, cap=skia.Paint.kRound_Cap, join=skia.Paint.kRound_Join):
    return skia.Paint(AntiAlias=True, Color=c, Style=skia.Paint.kStroke_Style,
                      StrokeWidth=w, StrokeCap=cap, StrokeJoin=join)


# ------------------------------------------------------------------- fonts --
_TF = None
_WEIGHTS = {}


def font(size, weight=400):
    global _TF
    if _TF is None:
        import os
        _TF = skia.Typeface.MakeFromFile(os.path.join(os.path.dirname(__file__), '..', 'game', 'fonts', 'Jost.ttf'))
    if weight not in _WEIGHTS:
        Cd = skia.FontArguments.VariationPosition.Coordinate
        coords = skia.FontArguments.VariationPosition.Coordinates([Cd(0x77676874, float(weight))])
        fa = skia.FontArguments()
        fa.setVariationDesignPosition(skia.FontArguments.VariationPosition(coords))
        _WEIGHTS[weight] = _TF.makeClone(fa)
    f = skia.Font(_WEIGHTS[weight], size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def text(c, s, x, y, size, weight=400, color=INK, alpha=1.0, align='left'):
    if alpha <= 0.003:
        return
    f = font(size, weight)
    w = f.measureText(s)
    if align == 'center':
        x -= w / 2
    elif align == 'right':
        x -= w
    c.drawString(s, x, y, f, fillp(rgb(color, alpha)))


def text_width(s, size, weight=400):
    return font(size, weight).measureText(s)


# ---------------------------------------------------------------- geometry --
def octi(a, b):
    dx = b[0] - a[0]; dy = b[1] - a[1]
    ax, ay = abs(dx), abs(dy)
    if ax > ay:
        mid = (a[0] + math.copysign(ax - ay, dx), a[1])
    else:
        mid = (a[0], a[1] + math.copysign(ay - ax, dy))
    return [a, mid, b]


def _dist(p, q):
    return math.hypot(q[0] - p[0], q[1] - p[1])


def round_corners(pts_in, keep_in, reach, steps=10):
    """shapes.gd round_corners: quadratic curve at each elbow, stations kept."""
    pts, squash = [], []
    for p in pts_in:
        if not pts or _dist(pts[-1], p) > 0.01:
            pts.append(p)
        squash.append(len(pts) - 1)
    keep = set(squash[k] for k in keep_in)
    outp = []
    n = len(pts)
    for i, p in enumerate(pts):
        corner = 0 < i < n - 1 and i not in keep
        if corner:
            a, b = pts[i - 1], pts[i + 1]
            la, lb = _dist(a, p), _dist(p, b)
            if la > 0.01 and lb > 0.01:
                din = ((p[0] - a[0]) / la, (p[1] - a[1]) / la)
                dout = ((b[0] - p[0]) / lb, (b[1] - p[1]) / lb)
                if din[0] * dout[0] + din[1] * dout[1] < 0.9995:
                    t = min(reach, min(la, lb) * 0.45)
                    p0 = (p[0] - din[0] * t, p[1] - din[1] * t)
                    p2 = (p[0] + dout[0] * t, p[1] + dout[1] * t)
                    for k in range(steps + 1):
                        u = k / steps
                        q = lerp2(lerp2(p0, p, u), lerp2(p, p2, u), u)
                        outp.append(q)
                    continue
        outp.append(p)
    return outp


def route(stops, reach=ROUTE_CURVE):
    if len(stops) < 2:
        return list(stops)
    pts = [stops[0]]
    keep = [0]
    for i in range(1, len(stops)):
        o = octi(stops[i - 1], stops[i])
        pts += [o[1], o[2]]
        keep.append(len(pts) - 1)
    return round_corners(pts, keep, reach)


def path_of(pts, close=False):
    p = skia.Path()
    if not pts:
        return p
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    return p


class Track:
    """A drawn route with arc-length lookups (for trains and partial drawing)."""

    def __init__(self, stops, reach=ROUTE_CURVE):
        self.stops = list(stops)
        self.pts = route(self.stops, reach)
        self.path = path_of(self.pts)
        self.pm = skia.PathMeasure(self.path, False)
        self.length = self.pm.getLength()
        # arc distance of each stop
        self.stop_d = []
        acc = 0.0
        j = 0
        cum = [0.0]
        for i in range(1, len(self.pts)):
            cum.append(cum[-1] + _dist(self.pts[i - 1], self.pts[i]))
        for s in self.stops:
            best, bd = 0, 1e9
            for i, q in enumerate(self.pts):
                d = _dist(q, s)
                if d < bd:
                    bd, best = d, i
            self.stop_d.append(cum[best])

    def pos(self, d):
        d = max(0.0, min(self.length, d))
        p, t = self.pm.getPosTan(d)
        return (p.x(), p.y()), math.atan2(t.y(), t.x())

    def part(self, d0, d1):
        dst = skia.Path()
        self.pm.getSegment(max(0, d0), min(self.length, d1), dst, True)
        return dst


# ---------------------------------------------------------------- shapes ----
def shape_pts(kind, r):
    if kind == TRIANGLE:
        return [(math.cos(-math.pi / 2 + i * 2 * math.pi / 3) * r * 1.18,
                 math.sin(-math.pi / 2 + i * 2 * math.pi / 3) * r * 1.18) for i in range(3)]
    if kind == SQUARE:
        s = r * 0.86
        return [(-s, -s), (s, -s), (s, s), (-s, s)]
    if kind == DIAMOND:
        d = r * 1.14
        return [(0, -d), (d, 0), (0, d), (-d, 0)]
    if kind == CROSS:
        a = r * 0.36; b = r * 1.02
        return [(-a, -b), (a, -b), (a, -a), (b, -a), (b, a), (a, a), (a, b), (-a, b), (-a, a), (-b, a), (-b, -a), (-a, -a)]
    if kind == STAR:
        out_ = []
        for i in range(10):
            rad = r * 1.18 if i % 2 == 0 else r * 0.5
            ang = -math.pi / 2 + i * math.pi / 5
            out_.append((math.cos(ang) * rad, math.sin(ang) * rad))
        return out_
    if kind == OVAL:
        return [(math.cos(2 * math.pi * i / 24) * r * 1.3, math.sin(2 * math.pi * i / 24) * r * 0.72) for i in range(24)]
    return [(math.cos(2 * math.pi * i / 26) * r, math.sin(2 * math.pi * i / 26) * r) for i in range(26)]


def shape_path(kind, r, at):
    return path_of([(at[0] + x, at[1] + y) for x, y in shape_pts(kind, r)], close=True)


def station(c, kind, at, k=1.0, alpha=1.0, ring=False):
    """_draw_stations: grows in from 70% size, white body, ink keyline."""
    if alpha <= 0.003:
        return
    r = STATION_R * lerp(0.70, 1.0, k)
    a = alpha * k if k < 1 else alpha
    if ring:
        c.drawCircle(at[0], at[1], STATION_R + 7.0 * S, strokep(rgb(INK, a), 3.0 * S))
    p = shape_path(kind, r, at)
    c.drawPath(p, fillp(rgb(WHITE, a)))
    c.drawPath(p, strokep(rgb(INK, a), KEYLINE, join=skia.Paint.kMiter_Join))


def waiting(c, at, kinds, scales=None, alpha=1.0):
    """_draw_waiting: rows of six beside the station, ink glyphs."""
    ox = at[0] + STATION_R + 12.0 * S
    oy = at[1] - STATION_R + 4.0 * S
    for i, kd in enumerate(kinds[:12]):
        k = 1.0 if scales is None else scales[i]
        if k <= 0.01:
            continue
        row, col = divmod(i, 6)
        p = (ox + col * 13.0 * S, oy + row * 14.0 * S)
        c.drawPath(shape_path(kd, WAIT_R * lerp(0.75, 1.0, k), p), fillp(rgb(INK, alpha * k)))


def crowding(c, at, frac, alpha=1.0):
    if frac <= 0.001:
        return
    frac = clamp01(frac)
    outer = STATION_R + 13.0 * S
    rect = skia.Rect.MakeXYWH(at[0] - outer, at[1] - outer, outer * 2, outer * 2)
    wedge = skia.Path()
    wedge.moveTo(*at)
    wedge.arcTo(rect, -90, 360 * frac, False)
    wedge.close()
    c.drawPath(wedge, fillp(rgb(DANGER, 0.28 * alpha)))
    arc = skia.Path()
    arc.addArc(rect, -90, 360 * frac)
    c.drawPath(arc, strokep(rgb(DANGER, alpha), 4.0 * S, cap=skia.Paint.kButt_Cap))


def body(c, at, ang, col, length, width, alpha=1.0):
    c.save()
    c.translate(*at)
    c.rotate(math.degrees(ang))
    c.drawRect(skia.Rect.MakeXYWH(-length / 2, -width / 2, length, width), fillp(rgb(col, alpha)))
    c.restore()


def riders_on(c, at, ang, kinds, scales=None, sc=1.0):
    fx, fy = math.cos(ang) * sc, math.sin(ang) * sc
    sx, sy = -fy, fx
    for k, kd in enumerate(kinds[:6]):
        s = 1.0 if scales is None else scales[k]
        if s <= 0.02:
            continue
        col, row = k % 3, k // 3
        ox = fx * (col - 1) * 9.5 * S + sx * (row - 0.5) * 9.0 * S
        oy = fy * (col - 1) * 9.5 * S + sy * (row - 0.5) * 9.0 * S
        c.drawPath(shape_path(kd, RIDER_R * sc * s, (at[0] + ox, at[1] + oy)), fillp(rgb(WHITE, 0.7)))


def train(c, track, d, col, cars=0, riders=None, rscales=None, direction=1, alpha=1.0):
    """Locomotive at arc distance d, carriages trailing behind."""
    at, ang = track.pos(d)
    if direction < 0:
        ang += math.pi
    body(c, at, ang, col, TRAIN_LEN, TRAIN_WID, alpha)
    riders = riders or []
    rscales = rscales or [1.0] * len(riders)
    riders_on(c, at, ang, riders[:6], rscales[:6])
    back = (TRAIN_LEN + CAR_LEN) * 0.5 + CAR_GAP
    for i in range(cars):
        dd = d - direction * (back + i * (CAR_LEN + CAR_GAP))
        p2, a2 = track.pos(dd)
        if direction < 0:
            a2 += math.pi
        body(c, p2, a2, col, CAR_LEN, TRAIN_WID * 0.9, alpha)
        riders_on(c, p2, a2, riders[6 * (i + 1):6 * (i + 2)], rscales[6 * (i + 1):6 * (i + 2)])


def line_stroke(c, path, col, alpha=1.0, width=ROUTE_W):
    c.drawPath(path, strokep(rgb(col, alpha), width, cap=skia.Paint.kButt_Cap))


def cap_ring(c, track, col, end=1, alpha=1.0, grow=1.0):
    """The round cap past a terminus that the player grabs to extend a line."""
    if len(track.pts) < 2 or grow <= 0:
        return
    if end > 0:
        a, b = track.pts[-2], track.pts[-1]
    else:
        a, b = track.pts[1], track.pts[0]
    L = _dist(a, b) or 1
    dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    off = 30.0 * S * grow
    p = (b[0] + dx * off, b[1] + dy * off)
    c.drawCircle(p[0], p[1], 7.0 * S, strokep(rgb(col, alpha), 3.4 * S))
    return p


def finger(c, at, alpha=1.0, press=0.0, ripple=-1.0):
    """The tutorial's guide finger: a white ring (ink halo for legibility)."""
    if alpha <= 0.003:
        return
    r = lerp(15.0, 12.5, press) * S
    c.drawCircle(at[0], at[1], r, strokep(rgb(INK, 0.16 * alpha), 8.0 * S))
    c.drawCircle(at[0], at[1], r, strokep(rgb(WHITE, alpha), 2.8 * S))
    c.drawCircle(at[0], at[1], r - 2.5 * S, fillp(rgb(WHITE, 0.22 * alpha)))
    if 0.0 <= ripple < 1.0:
        q = out(ripple)
        c.drawCircle(at[0], at[1], lerp(16.0, 38.0, q) * S, strokep(rgb(WHITE, alpha * (1 - q) * 0.9), 2.2 * S))


# ----------------------------------------------------------------- terrain --
def band_pts(flat, scale=(W, H)):
    return [(flat[i] * scale[0], flat[i + 1] * scale[1]) for i in range(0, len(flat) - 1, 2)]


def river_path(points, half, reach=60.0 * S):
    pts = [points[0]]
    keep = [0]
    for i in range(1, len(points)):
        o = octi(points[i - 1], points[i])
        pts += [o[1], o[2]]
        keep.append(len(pts) - 1)
    center = path_of(round_corners(pts, keep, reach))
    fill = skia.Path()
    strokep(0, half * 2, cap=skia.Paint.kButt_Cap).getFillPath(center, fill)
    return center, fill


def draw_water(c, fillpath, pal, edge_w=3.0 * S):
    c.drawPath(fillpath, strokep(rgb(pal['edge']), edge_w * 2, join=skia.Paint.kRound_Join))
    c.drawPath(fillpath, fillp(rgb(pal['water'])))


def draw_hill(c, center, half, pal, rings=3):
    c.drawPath(center, strokep(rgb(pal['rock']), half * 2))
    for i in range(1, rings + 1):
        w = (half - i * 11.0 * S) * 2
        if w <= 4:
            break
        ring = skia.Path()
        strokep(0, w).getFillPath(center, ring)
        ring = skia.Simplify(ring)
        c.drawPath(ring, strokep(rgb(pal['rock_edge'], 0.6), 1.3 * S))


def crossing(c, track_path, region, col, pal, kind='bridge', width=ROUTE_W, alpha=1.0):
    """Bridges: grey and thicker over water. Tunnels: dashes, hill between."""
    c.save()
    c.clipPath(region, skia.ClipOp.kIntersect, True)
    if kind == 'bridge':
        c.drawPath(track_path, strokep(rgb(BRIDGE, alpha), width * 1.38, cap=skia.Paint.kButt_Cap))
    else:
        c.drawPath(track_path, strokep(rgb(pal['rock']), width * 1.25, cap=skia.Paint.kButt_Cap))
        dash = strokep(rgb(col, alpha), width * 0.92, cap=skia.Paint.kButt_Cap)
        dash.setPathEffect(skia.DashPathEffect.Make([width * 1.15, width * 0.95], 0))
        c.drawPath(track_path, dash)
    c.restore()


def vignette(c, alpha=1.0):
    shader = skia.GradientShader.MakeRadial(
        (W / 2, H / 2), math.hypot(W, H) * 0.62,
        [rgb(INK, 0.0), rgb(INK, 0.0), rgb(INK, 0.075 * alpha)], [0.0, 0.55, 1.0])
    p = skia.Paint(AntiAlias=True, Shader=shader)
    c.drawRect(skia.Rect.MakeWH(W, H), p)


# --------------------------------------------------------------------- HUD --
DOCK_X = 69
DOCK_Y = [380, 487, 593, 698, 804]


def hud_controls(c, fast=False, alpha=1.0):
    y = 60
    mc = rgb(MUTED, alpha)
    ic = rgb(INK, alpha)
    pc = fillp(mc)
    c.drawRect(skia.Rect.MakeXYWH(60 - 12, y - 13.5, 9, 27), pc)
    c.drawRect(skia.Rect.MakeXYWH(60 + 3, y - 13.5, 9, 27), pc)
    tri = path_of([(135 - 10.5, y - 15), (135 + 13.5, y), (135 - 10.5, y + 15)], True)
    c.drawPath(tri, fillp(mc if fast else ic))
    fc = ic if fast else mc
    for dx in (0, 16):
        x = 196 + dx
        c.drawPath(path_of([(x, y - 13), (x + 16, y), (x, y + 13)], True), fillp(fc))
    c.drawCircle(285, y, 22.5, strokep(mc, 3.75))
    c.drawLine(285 - 7.5, y - 7.5, 285 + 7.5, y + 7.5, strokep(mc, 3.75))
    c.drawLine(285 + 7.5, y - 7.5, 285 - 7.5, y + 7.5, strokep(mc, 3.75))


def hud_clock(c, day, count, frac, night=0.0, alpha=1.0):
    cx, cy, r = 1845, 75, 48
    rim = 9
    for i in range(4):
        c.drawCircle(cx, cy + 3.5, r + 4.5 - i * 1.8, fillp(skia.Color(0, 0, 0, int(9 * alpha))))
    face = mix('f8f8f7', INK, night)
    mark = mix(INK, 'd1d1d1', night)
    hand = mix('45292a', 'dbdbdb', night)
    c.drawCircle(cx, cy, r, fillp(rgb(INK, alpha)))
    c.drawCircle(cx, cy, r - rim, fillp(rgb(face, alpha)))
    for i in range(12):
        a = 2 * math.pi * i / 12
        dx, dy = math.sin(a), -math.cos(a)
        c.drawLine(cx + dx * (r - rim - 13), cy + dy * (r - rim - 13), cx + dx * (r - rim - 4.5), cy + dy * (r - rim - 4.5),
                   strokep(rgb(mark, alpha), 3.9))
    ang = frac * 4 * math.pi
    tx, ty = math.sin(ang), -math.cos(ang)
    c.drawLine(cx - tx * 2, cy - ty * 2, cx + tx * (r - rim - 9), cy + ty * (r - rim - 9), strokep(rgb(hand, alpha), 7.5))
    right = cx - r - 21
    text(c, day, right, cy - 4, 57, 800, INK, alpha, 'right')
    text(c, str(count), right, cy + 58, 57, 800, INK, alpha, 'right')


def hud_line_dots(c, cols, used, alpha=1.0, pop=None):
    ys = [293, 375, 457, 540, 622, 704, 786]
    for i, y in enumerate(ys):
        if i < used:
            k = 1.0
            if pop is not None and pop[0] == i:
                k = 1.0 + 0.25 * math.sin(math.pi * clamp01(pop[1]))
            c.drawCircle(1841, y, 28 * k, fillp(rgb(cols[i], alpha)))
        else:
            c.drawCircle(1841, y, 15, fillp(rgb('b9b9b9', 0.85 * alpha)))


def coin_icon(c, kind, at, col, sc=1.0):
    x, y = at
    p = fillp(rgb(col))
    s = sc
    if kind == 'loco':
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - 13 * s, y - 17 * s, 26 * s, 28 * s), 5 * s, 5 * s), p)
        c.drawRect(skia.Rect.MakeXYWH(x - 9 * s, y - 13 * s, 18 * s, 9 * s), fillp(rgb(INK)))
        c.drawCircle(x - 6 * s, y + 4 * s, 2.6 * s, fillp(rgb(INK)))
        c.drawCircle(x + 6 * s, y + 4 * s, 2.6 * s, fillp(rgb(INK)))
        c.drawLine(x - 8 * s, y + 12 * s, x - 13 * s, y + 20 * s, strokep(rgb(col), 3 * s))
        c.drawLine(x + 8 * s, y + 12 * s, x + 13 * s, y + 20 * s, strokep(rgb(col), 3 * s))
    elif kind == 'car':
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - 20 * s, y - 11 * s, 40 * s, 19 * s), 4 * s, 4 * s), p)
        for i in range(3):
            c.drawRect(skia.Rect.MakeXYWH(x - 16 * s + i * 11.5 * s, y - 7 * s, 8 * s, 6 * s), fillp(rgb(INK)))
        c.drawCircle(x - 11 * s, y + 11 * s, 3.5 * s, p)
        c.drawCircle(x + 11 * s, y + 11 * s, 3.5 * s, p)
    elif kind == 'inter':
        c.drawCircle(x, y, 13 * s, strokep(rgb(col), 3.2 * s))
        c.drawCircle(x, y, 6 * s, p)
    elif kind == 'bridge':
        c.drawLine(x - 22 * s, y + 8 * s, x + 22 * s, y + 8 * s, strokep(rgb(col), 3.5 * s))
        for tx in (-10, 10):
            c.drawLine(x + tx * s, y - 14 * s, x + tx * s, y + 8 * s, strokep(rgb(col), 3.2 * s))
        cable = skia.Path(); cable.moveTo(x - 22 * s, y - 2 * s); cable.quadTo(x - 16 * s, y - 14 * s, x - 10 * s, y - 14 * s)
        cable.quadTo(x, y, x + 10 * s, y - 14 * s); cable.quadTo(x + 16 * s, y - 14 * s, x + 22 * s, y - 2 * s)
        c.drawPath(cable, strokep(rgb(col), 2.2 * s))
        for hx in (-5, 0, 5):
            c.drawLine(x + hx * s, y - 7 * s + abs(hx) * -0.9 * s, x + hx * s, y + 8 * s, strokep(rgb(col), 1.6 * s))
    elif kind == 'tunnel':
        m = path_of([(x - 22 * s, y + 12 * s), (x - 6 * s, y - 16 * s), (x + 4 * s, y - 4 * s), (x + 10 * s, y - 12 * s), (x + 22 * s, y + 12 * s)], True)
        c.drawPath(m, p)
        arch = skia.Path(); arch.moveTo(x - 7 * s, y + 12 * s); arch.lineTo(x - 7 * s, y + 3 * s)
        arch.arcTo(skia.Rect.MakeXYWH(x - 7 * s, y - 4 * s, 14 * s, 14 * s), 180, 180, False); arch.lineTo(x + 7 * s, y + 12 * s); arch.close()
        c.drawPath(arch, fillp(rgb(INK)))
    elif kind == 'line':
        c.drawLine(x - 12 * s, y + 8 * s, x - 2 * s, y - 4 * s, strokep(rgb(col), 4 * s))
        c.drawLine(x - 2 * s, y - 4 * s, x + 12 * s, y - 4 * s, strokep(rgb(col), 4 * s))
        c.drawCircle(x - 14 * s, y + 10 * s, 4.5 * s, fillp(rgb(INK)))
        c.drawCircle(x - 14 * s, y + 10 * s, 4.5 * s, strokep(rgb(col), 2.4 * s))
        c.drawCircle(x + 14 * s, y - 4 * s, 4.5 * s, fillp(rgb(INK)))
        c.drawCircle(x + 14 * s, y - 4 * s, 4.5 * s, strokep(rgb(col), 2.4 * s))


def hud_dock(c, slots, alpha=1.0):
    """slots: list of (kind, count, pop) ; a divider sits before permits."""
    n = len(slots)
    top = 325
    h = 70 + n * 106
    for i in range(6):
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(14 - i, top + 4 - i + 3, 110 + 2 * i, h + 2 * i), 18, 18),
                    fillp(skia.Color(0, 0, 0, int(4 * alpha))))
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(14, top, 110, h), 18, 18), fillp(rgb(WHITE, 0.96 * alpha)))
    for i, (kind, cnt, pop) in enumerate(slots):
        y = top + 55 + i * 106
        if kind in ('bridge', 'tunnel') and i > 0 and slots[i - 1][0] not in ('bridge', 'tunnel'):
            c.drawLine(34, y - 53, 104, y - 53, strokep(rgb('dddddd', alpha), 2))
        k = 1.0
        if pop is not None and 0 <= pop < 1:
            k = 1.0 + 0.16 * math.sin(math.pi * pop)
        on = cnt > 0
        coin = INK if on else 'd9d9d9'
        c.drawCircle(DOCK_X, y, 39 * k, fillp(rgb(coin, alpha)))
        coin_icon(c, kind, (DOCK_X, y), WHITE if on else 'f2f2f2', k)
        c.drawCircle(DOCK_X + 28, y + 30, 16 * k, fillp(rgb(WHITE, alpha)))
        c.drawCircle(DOCK_X + 28, y + 30, 16 * k, strokep(rgb('dadada', alpha), 2))
        text(c, str(cnt), DOCK_X + 28, y + 38, 22 * k, 600, INK if on else MUTED, alpha, 'center')


# ------------------------------------------------------------------ camera --
def camera(c, cx, cy, z, roll=0.0):
    c.translate(W / 2, H / 2)
    if roll:
        c.rotate(roll)
    c.scale(z, z)
    c.translate(-cx, -cy)


def clamp_cam(cx, cy, z):
    hw, hh = W / (2 * z), H / (2 * z)
    return (min(max(cx, hw), W - hw), min(max(cy, hh), H - hh))
