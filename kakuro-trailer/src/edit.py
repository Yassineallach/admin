"""Kakuro trailer editor: cuts the real-game capture to the game's own
menu music (110 BPM, 16 bars), adds text, touch markers and the end card,
and mixes the captured sound effects over the music."""
import math
import re
import subprocess
import sys
import wave
from functools import lru_cache

import numpy as np
import skia
import imageio_ffmpeg

ROOT = '/tmp/claude-0/-home-user-admin/514f0e2c-850f-56ce-b813-1947e6ccd4f5/scratchpad'
CAP = ROOT + '/cap/take1'
LOG = ROOT + '/cap/take1.log'
GAME = ROOT + '/kakuro'
W, H, FPS = 1080, 1920, 30
BPM = 110.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
FF = imageio_ffmpeg.get_ffmpeg_exe()


def bar(n):
    return (n - 1) * BAR


# --------------------------------------------------------------- the log --
MARKS, TAPS = {}, []
for line in open(LOG, errors='ignore'):
    m = re.match(r'MARK ([\d.]+) (\S+)', line)
    if m:
        MARKS.setdefault(m.group(2), float(m.group(1)))
    m = re.match(r'(TAP|DRAG) ([\d.]+) ([\d.-]+) ([\d.-]+) ?(\S*)', line)
    if m:
        TAPS.append((float(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(1), m.group(5)))
NFRAMES = None


def nframes():
    global NFRAMES
    if NFRAMES is None:
        import glob
        NFRAMES = len(glob.glob(CAP + '/f*.png'))
    return NFRAMES


@lru_cache(maxsize=48)
def src_frame(i):
    i = max(0, min(nframes() - 1, i))
    return skia.Image.open('%s/f%08d.png' % (CAP, i))


# ----------------------------------------------------------------- fonts --
_tf = {}


def font(size, weight='ExtraBold'):
    if weight not in _tf:
        _tf[weight] = skia.Typeface.MakeFromFile('%s/assets/fonts/Nunito-%s.ttf' % (GAME, weight))
    f = skia.Font(_tf[weight], size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def clamp01(x):
    return max(0.0, min(1.0, x))


def seg(t, a, b):
    return clamp01((t - a) / (b - a)) if b > a else float(t >= b)


def ease(u):
    u = clamp01(u)
    return u * u * (3 - 2 * u)


def back_out(u, s=1.6):
    u = clamp01(u) - 1
    return u * u * ((s + 1) * u + s) + 1


def col(h, a=1.0):
    h = h.lstrip('#')
    return skia.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(255 * clamp01(a)))


# ---------------------------------------------------------- the overlays --
def chunky_text(c, lines, cx, y, size, t_in, t, face='ffffff', lip='1b2433', ink='1b2433', t_out=None):
    """A caption in the game's chunky style: white card, darker lip, Nunito."""
    k = back_out(seg(t, t_in, t_in + 0.32))
    a = seg(t, t_in, t_in + 0.12)
    if t_out is not None:
        a *= 1 - seg(t, t_out - 0.12, t_out)
    if a <= 0:
        return
    f = font(size)
    widths = [f.measureText(s) for s in lines]
    pad_x, pad_y, lh = size * 0.55, size * 0.38, size * 1.12
    w = max(widths) + pad_x * 2
    h = lh * len(lines) + pad_y * 2 - size * 0.12
    c.save()
    c.translate(cx, y + h / 2)
    c.scale(lerp(0.7, 1.0, k), lerp(0.7, 1.0, k))
    c.translate(-cx, -(y + h / 2))
    lipd = size * 0.16
    r = skia.Rect.MakeXYWH(cx - w / 2, y, w, h)
    c.drawRRect(skia.RRect.MakeRectXY(r.makeOffset(0, lipd), size * 0.4, size * 0.4), skia.Paint(AntiAlias=True, Color=col(lip, a)))
    c.drawRRect(skia.RRect.MakeRectXY(r, size * 0.4, size * 0.4), skia.Paint(AntiAlias=True, Color=col(face, a)))
    for i, s in enumerate(lines):
        c.drawString(s, cx - widths[i] / 2, y + pad_y + size * 0.86 + i * lh, f, skia.Paint(AntiAlias=True, Color=col(ink, a)))
    c.restore()


def lerp(a, b, u):
    return a + (b - a) * u


def finger(c, x, y, a, press, ripple):
    if a <= 0.003:
        return
    r = lerp(34, 28, press)
    c.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Color=col('1b2433', 0.22 * a), Style=skia.Paint.kStroke_Style, StrokeWidth=16))
    c.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Color=col('ffffff', 0.92 * a), Style=skia.Paint.kStroke_Style, StrokeWidth=6))
    c.drawCircle(x, y, r - 5, skia.Paint(AntiAlias=True, Color=col('ffffff', 0.25 * a)))
    if 0 <= ripple < 1:
        q = 1 - (1 - ripple) ** 3
        c.drawCircle(x, y, lerp(34, 80, q), skia.Paint(AntiAlias=True, Color=col('ffffff', (1 - q) * 0.8 * a),
                                                       Style=skia.Paint.kStroke_Style, StrokeWidth=4))


def touches(c, s0, s1, ts, xf):
    """Finger markers for real taps logged during capture (source time ts)."""
    best = None
    for (tt, x, y, kind, sub) in TAPS:
        if s0 - 0.05 <= tt <= s1 and tt - 0.25 <= ts <= tt + 0.45:
            if best is None or abs(ts - tt) < abs(ts - best[0]):
                best = (tt, x, y, kind, sub)
    if best is None:
        return
    tt, x, y, kind, sub = best
    a = seg(ts, tt - 0.25, tt - 0.12) * (1 - seg(ts, tt + 0.22, tt + 0.42))
    press = seg(ts, tt - 0.12, tt)
    ripple = (ts - tt) / 0.4 if ts >= tt else -1
    px, py = xf(x, y)
    finger(c, px, py, a, press, ripple)


# --------------------------------------------------------------- clips ----
class Clip:
    def __init__(self, t0, dur, src, zoom=1.0, focus=None, zoom_to=None, focus_to=None, speed=1.0, fingers=True):
        self.t0, self.dur, self.src, self.speed = t0, dur, src, speed
        self.zoom, self.focus = zoom, focus or (W / 2, H / 2)
        self.zoom_to = zoom_to if zoom_to is not None else zoom
        self.focus_to = focus_to or self.focus
        self.fingers = fingers

    def src_time(self, t):
        return self.src + (t - self.t0) * self.speed

    def draw(self, c, t):
        ts = self.src_time(t)
        img = src_frame(int(round(ts * FPS)))
        u = ease((t - self.t0) / self.dur)
        z = lerp(self.zoom, self.zoom_to, u)
        fx = lerp(self.focus[0], self.focus_to[0], u)
        fy = lerp(self.focus[1], self.focus_to[1], u)
        # keep the crop inside the frame
        hw, hh = W / (2 * z), H / (2 * z)
        fx = min(max(fx, hw), W - hw)
        fy = min(max(fy, hh), H - hh)
        c.save()
        c.translate(W / 2, H / 2)
        c.scale(z, z)
        c.translate(-fx, -fy)
        c.drawImageRect(img, skia.Rect.MakeWH(img.width(), img.height()), skia.Rect.MakeWH(W, H),
                        skia.SamplingOptions(skia.CubicResampler.Mitchell()))
        c.restore()
        if self.fingers:
            sx, sy = W / img.width(), H / img.height()
            touches(c, self.src, self.src + self.dur * self.speed, ts,
                    lambda x, y: ((x * sx - fx) * z + W / 2, (y * sy - fy) * z + H / 2))


# ------------------------------------------------------------- timeline ---
M = MARKS
BOARD = (540, 950)          # board centre in the capture (game screen)
END = 16 * BAR               # the music: 16 bars of "Sunny Grid"
TAIL = 2.4
DURATION = END + TAIL


def timeline():
    h = BAR / 2
    clips = [
        # 1 hook: the fast, rhythmic fill (marimba digits + run sweeps), close on the board
        Clip(bar(1), BAR, M['finish'] + 0.35, zoom=1.38, focus=BOARD, zoom_to=1.3),
        # 2 the launch splash builds the logo
        Clip(bar(2), BAR, 0.55, fingers=False),
        # 3 title screen: Kaku, poke -> giggle
        Clip(bar(3), BAR, M['menu'] + 0.55, zoom=1.12, focus=(540, 560), zoom_to=1.0, focus_to=(540, 900)),
        # 4 level map -> tap the current level
        Clip(bar(4), BAR, M['levels'] + 0.25),
        # 5 playing: select, sums, marimba
        Clip(bar(5), BAR, M['game1'] - 0.2, zoom=1.0),
        # 6 the digit ring
        Clip(bar(6), BAR, M['ring'] - 0.15, zoom=1.12, focus=(560, 950)),
        # 7 a mistake: red, Kaku says oops, fixed
        Clip(bar(7), BAR, M['mistake'] - 0.1, zoom=1.25, focus=(540, 900)),
        # 8 a hint that explains the logic (Lumo)
        Clip(bar(8), BAR, M['hint'] + 0.15, zoom=1.22, focus=(540, 700)),
        # 9-10 bigger grids
        Clip(bar(9), h, M['medium'] + 0.2),
        Clip(bar(9) + h, h, M['hard'] + 0.2),
        Clip(bar(10), BAR, M['expert'] + 0.1, zoom=1.0, focus=BOARD, zoom_to=1.08),
        # 11 daily challenge (Blaze), quick play (Zip)
        Clip(bar(11), h, M['daily'] + 0.3),
        Clip(bar(11) + h, h, M['quick'] + 0.3),
        # 12 the last digits -> the win wave
        Clip(bar(12), BAR, M['win'] - 1.55, zoom=1.2, focus=BOARD, zoom_to=1.08),
        # 13 Solved! card, Kaku cheers
        Clip(bar(13), BAR, M['win'] + 1.45),
        # 14-15 chapter unlocked
        Clip(bar(14), 2 * BAR, M['unlock'] + 0.15),
        # 16 + tail: end card stage (logo drops in, Kaku hops)
        Clip(bar(16), BAR + TAIL, M['endcard'] + 0.0, fingers=False),
    ]
    return clips


CAPTIONS = [
    # (lines, t_in, t_out, y)
    (['EVERY CLUE', 'IS A SUM'], bar(5) + 0.1, bar(6), 96),
    (['LEARN THE LOGIC'], bar(8) + 0.05, bar(9), 1690),
    (['6×6 TO 12×12'], bar(9) + 0.05, bar(11), 96),
    (['NEW PUZZLE', 'EVERY DAY'], bar(11) + 0.05, bar(12), 96),
]


def badge(c, t, t_in):
    a = seg(t, t_in, t_in + 0.3)
    if a <= 0:
        return
    k = back_out(seg(t, t_in, t_in + 0.35))
    w, h = 420, 124
    x, y = W / 2 - w / 2, 1560
    c.save()
    c.translate(W / 2, y + h / 2); c.scale(lerp(0.8, 1, k), lerp(0.8, 1, k)); c.translate(-W / 2, -(y + h / 2))
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 18, 18)
    c.drawRRect(rr, skia.Paint(AntiAlias=True, Color=col('000000', a)))
    c.drawRRect(rr, skia.Paint(AntiAlias=True, Color=col('a6a6a6', a), Style=skia.Paint.kStroke_Style, StrokeWidth=3))
    tri = skia.Path(); tri.moveTo(x + 40, y + 34); tri.lineTo(x + 86, y + 62); tri.lineTo(x + 40, y + 90); tri.close()
    c.drawPath(tri, skia.Paint(AntiAlias=True, Color=col('ffffff', a), Style=skia.Paint.kStroke_Style, StrokeWidth=5, StrokeJoin=skia.Paint.kRound_Join))
    c.drawString('GET IT ON', x + 112, y + 50, font(24, 'Bold'), skia.Paint(AntiAlias=True, Color=col('ffffff', a)))
    c.drawString('Google Play', x + 110, y + 98, font(48, 'Bold'), skia.Paint(AntiAlias=True, Color=col('ffffff', a)))
    c.restore()


def end_overlay(c, t):
    t0 = bar(16)
    a = seg(t, t0 + 1.0, t0 + 1.35)
    if a > 0:
        f = font(44, 'ExtraBold')
        s = 'CROSS SUMS · PURE LOGIC'
        wv = f.measureText(s)
        c.drawString(s, W / 2 - wv / 2, 1430, f, skia.Paint(AntiAlias=True, Color=col('687487', a)))
    badge(c, t, t0 + 1.5)


def draw(c, t, clips):
    clip = None
    for cl in clips:
        if cl.t0 <= t < cl.t0 + cl.dur:
            clip = cl
    if clip is None:
        clip = clips[-1]
    clip.draw(c, t)
    for (lines, ti, to, y) in CAPTIONS:
        if ti <= t < to:
            chunky_text(c, lines, W / 2, y, 70, ti, t, t_out=to)
    end_overlay(c, t)


def render_video(out, audio):
    clips = timeline()
    cmd = [FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-i', audio, '-c:a', 'aac', '-b:a', '256k', '-shortest',
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
           '-movflags', '+faststart', out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    n = int(round(DURATION * FPS))
    for i in range(n):
        c = surf.getCanvas()
        c.clear(skia.ColorBLACK)
        draw(c, i / FPS, clips)
        proc.stdin.write(surf.makeImageSnapshot().tobytes())
        if i % 150 == 0:
            print('frame', i, '/', n, flush=True)
    proc.stdin.close()
    proc.wait()


def still(t, path):
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
    draw(surf.getCanvas(), t, timeline())
    surf.makeImageSnapshot().save(path)


# ----------------------------------------------------------------- audio --
SR = 48000


def load_audio(path):
    raw = subprocess.run([FF, '-loglevel', 'error', '-i', path, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype='<f4').reshape(-1, 2).copy()


def build_audio(out):
    n = int((DURATION + 0.1) * SR)
    mix = np.zeros((n, 2))
    music = load_audio(GAME + '/assets/audio/music/menu_loop.ogg')
    loop_n = int(round(END * SR))
    bed = np.zeros((n, 2))
    m = min(loop_n, len(music), n)
    bed[:m] = music[:m]
    # the tail: the loop's first bar again, fading out under the end card
    tail = min(n - loop_n, len(music))
    if tail > 0:
        fade = np.linspace(1, 0, tail) ** 1.5
        bed[loop_n:loop_n + tail] = music[:tail] * fade[:, None]
    # duck the music under the win jingle (as the game does) and the splash
    env = np.ones(n)
    def duck(t0, t1, level, ramp=0.25):
        a, b = int(t0 * SR), int(t1 * SR)
        r = int(ramp * SR)
        env[a:b] = np.minimum(env[a:b], level)
        env[max(0, a - r):a] = np.minimum(env[max(0, a - r):a], np.linspace(1, level, a - max(0, a - r)))
        env[b:b + r] = np.minimum(env[b:b + r], np.linspace(level, 1, len(env[b:b + r])))
    duck(bar(12) + BAR * 0.62, bar(13) + BAR * 0.9, 0.35)
    mix += bed * env[:, None] * 1.0
    # captured game sound effects, cut with the picture
    fx = np.zeros((n, 2))
    sfx = load_audio(CAP + '/f.wav')
    for cl in timeline():
        a = int(cl.t0 * SR)
        b = int(min(cl.t0 + cl.dur, DURATION) * SR)
        s0 = int(cl.src * SR)
        L = min(b - a, len(sfx) - s0)
        if L <= 0:
            continue
        seg_ = sfx[s0:s0 + L].copy()
        f = min(int(0.006 * SR), L // 2)
        seg_[:f] *= np.linspace(0, 1, f)[:, None]
        seg_[-f:] *= np.linspace(1, 0, f)[:, None]
        fx[a:a + L] += seg_
    # level the effects: a slow compressor so a burst of digits never shouts
    lvl = np.sqrt(np.convolve((fx ** 2).mean(1), np.ones(int(0.12 * SR)) / int(0.12 * SR), 'same'))
    thr = 10 ** (-24 / 20)
    gain = np.minimum(1.0, (thr / np.maximum(lvl, 1e-9)) ** 0.7)
    gain = np.convolve(gain, np.ones(int(0.03 * SR)) / int(0.03 * SR), 'same')
    mix += fx * gain[:, None] * 1.6
    # master: aim near -14 LUFS-ish, soft ceiling at -1 dBFS
    rms = np.sqrt(np.mean(mix ** 2))
    mix *= 10 ** (-15 / 20) / max(rms, 1e-9)
    ceil = 10 ** (-1 / 20)
    mix = np.tanh(mix / ceil) * ceil
    k = int(0.4 * SR)
    mix[-k:] *= np.linspace(1, 0, k)[:, None]
    pcm = (np.clip(mix, -1, 1) * 32767).astype('<i2')
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == '__main__':
    if sys.argv[1] == 'still':
        for a in sys.argv[3:]:
            still(float(a), '%s/s_%05.2f.png' % (sys.argv[2], float(a)))
    elif sys.argv[1] == 'audio':
        build_audio(sys.argv[2])
    else:
        render_video(sys.argv[2], sys.argv[3])
