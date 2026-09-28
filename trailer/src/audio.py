"""Trailer score, built the way scripts/audio.gd builds the game's music:
gameplay events placed on a 92 BPM grid in A minor pentatonic, played by a
handful of synthesised voices, over a soft generative pad."""
import math
import random
import wave
import numpy as np
from prim import BEAT, BAR, SIX, bar
import scenes as A
import scenes2 as B
import render

SR = 44100
ROOT = 110.0
DEG = [0, 3, 5, 7, 10]


def freq(deg, octv):
    return ROOT * 2 ** ((DEG[deg % 5] + 12 * (octv + deg // 5)) / 12.0)


def tt(n):
    return np.arange(int(n * SR)) / SR


def partials(f, parts, taus, length, attack=0.004):
    t = tt(length)
    y = np.zeros_like(t)
    for (m, a), tau in zip(parts, taus):
        y += a * np.sin(2 * math.pi * f * m * t) * np.exp(-t / tau)
    env = np.minimum(1.0, t / attack)
    return y * env


def v_pluck(f):
    return 0.55 * partials(f, [(1, 1), (1.004, .85), (2, .34), (2.007, .28), (3, .10)],
                           [.30, .30, .12, .12, .06], 1.0, 0.006)


def v_tok(f):
    t = tt(0.22)
    y = 0.6 * np.sin(2 * math.pi * f * 2 * t) * np.exp(-t / 0.035)
    y += 0.25 * np.sin(2 * math.pi * f * 4.6 * t) * np.exp(-t / 0.015)
    rng = np.random.default_rng(int(f))
    n = rng.standard_normal(len(t)) * np.exp(-t / 0.006) * 0.12
    return (y + n) * np.minimum(1, t / 0.002)


def v_plink(f):
    return 0.35 * partials(f * 2, [(1, 1), (2.76, .35), (5.4, .1)], [.16, .07, .03], 0.6, 0.002)


def v_pulse(f):
    t = tt(0.7)
    y = np.sin(2 * math.pi * f * 0.5 * t) + 0.35 * np.sin(2 * math.pi * f * t)
    env = np.minimum(1, t / 0.025) * np.exp(-t / 0.22)
    return 0.7 * y * env


def v_chime(f):
    return 0.42 * partials(f * 2, [(1, 1), (2, .45), (2.76, .3), (4.07, .15), (5.4, .08)],
                           [1.6, 1.0, .6, .4, .25], 3.6, 0.003)


def v_tik(f):
    t = tt(0.06)
    return 0.22 * np.sin(2 * math.pi * f * 2 * t) * np.exp(-t / 0.012) * np.minimum(1, t / 0.001)


def v_tick(f):
    t = tt(0.12)
    y = 0.5 * np.sin(2 * math.pi * 850 * t) * np.exp(-t / 0.028) + 0.2 * np.sin(2 * math.pi * 1930 * t) * np.exp(-t / 0.012)
    rng = np.random.default_rng(7)
    y += rng.standard_normal(len(t)) * np.exp(-t / 0.007) * 0.15
    return y


def v_haptic(f):
    t = tt(0.06)
    return 0.35 * np.sin(2 * math.pi * 70 * t) * np.exp(-t / 0.018)


VOICES = {'pluck': v_pluck, 'tok': v_tok, 'plink': v_plink, 'pulse': v_pulse, 'chime': v_chime,
          'tik': v_tik, 'tick': v_tick, 'haptic': v_haptic}
LEVEL = {'pluck': 0.9, 'tok': 0.7, 'plink': 0.8, 'pulse': 0.8, 'chime': 0.85, 'tik': 0.9, 'tick': 0.8, 'haptic': 0.8}
SILENCE = (bar(11) - BEAT, bar(11) + 0.72)   # the held beat before the fix


def env_curve(points, n):
    xs = np.array([p[0] for p in points]) * SR
    ys = np.array([p[1] for p in points])
    return np.interp(np.arange(n), xs, ys)


def pad(n):
    t = np.arange(n) / SR
    notes = [110.0, 164.81, 220.0, 261.63, 329.63, 392.0]
    gains = [0.9, 0.55, 0.5, 0.35, 0.3, 0.18]
    bright = env_curve([(0, .3), (23.4, .3), (24.2, .05), (26.1, .05), (28.7, .35), (30.4, .85), (31.4, .45), (43.5, .4)], n)
    L = np.zeros(n); R = np.zeros(n)
    for i, (f, g) in enumerate(zip(notes, gains)):
        lfo = 0.6 + 0.4 * np.sin(2 * math.pi * (0.07 + 0.031 * i) * t + i * 1.7)
        for det, side in ((1.0, 0), (1.003, 1)):
            ph = 2 * math.pi * f * det * t
            y = np.sin(ph) + bright * (0.22 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph) + 0.05 * np.sin(4 * ph))
            if side == 0:
                L += g * lfo * y
            else:
                R += g * lfo * y
    level = env_curve([(0, 0), (5.1, 0), (5.9, .2), (7.8, .22), (20.8, .26), (23.5, .24), (SILENCE[0], .24),
                       (SILENCE[0] + 0.1, .06), (SILENCE[1], .06), (SILENCE[1] + 0.6, .22), (28.7, .3), (30.3, .8),
                       (31.3, .4), (36.5, .42), (41.7, .42), (43.2, 0.0), (50, 0)], n)
    hiss = np.convolve(np.random.default_rng(3).standard_normal(n), np.ones(6) / 6, 'same') * 0.004
    return L * level * 0.16 + hiss, R * level * 0.16 + hiss


def motifs():
    """Each line has its own little pattern (audio.gd _tick_motifs): soft
    plucks on the 16th grid, denser as the network grows."""
    out = []
    rnd = random.Random(92)
    spans = [(bar(4), bar(6), 3), (bar(6), bar(9), 5), (bar(9), bar(10), 6), (bar(10), SILENCE[0], 9),
             (bar(12), bar(13), 5), (bar(13), bar(15), 9)]
    for a, b, dens in spans:
        n = int(round((b - a) / SIX))
        pat = [rnd.random() < dens / 16 for _ in range(16)]
        degs = [rnd.randint(0, 4) for _ in range(16)]
        for k in range(n):
            if pat[k % 16]:
                out.append((a + k * SIX, 'pluck', degs[k % 16], 2 if k % 3 else 1, 0.22, rnd.uniform(-0.3, 0.3)))
    return out


def events():
    A.EV.clear()
    A.events_intro(); A.events04(); A.events05(); A.events06(); A.events07(); A.events08()
    A.events09(); A.events10_11(); B.events12_16()
    ev = list(A.EV) + motifs()
    return [e for e in ev if not (SILENCE[0] <= e[0] < SILENCE[1] - 0.05)]


def reverb(x, seconds=2.4, seed=1):
    n = int(seconds * SR)
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR / (seconds / 6.5))
    ir[:int(0.02 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]
    return y


def build(path):
    n = int((render.DURATION + 0.2) * SR)
    L = np.zeros(n); R = np.zeros(n)
    cache = {}
    grid = SIX / 2
    for (t, voice, deg, octv, gain, pan) in events():
        if voice not in VOICES:
            continue
        if voice != 'haptic':
            t = round(t / grid) * grid
        f = freq(deg, octv)
        key = (voice, round(f, 2))
        if key not in cache:
            cache[key] = VOICES[voice](f)
        y = cache[key] * gain * LEVEL[voice]
        i = int(t * SR)
        if i >= n:
            continue
        m = min(len(y), n - i)
        a = (pan + 1) * math.pi / 4
        L[i:i + m] += y[:m] * math.cos(a)
        R[i:i + m] += y[:m] * math.sin(a)
    pl, pr = pad(n)
    wetL = reverb(L + pl * 0.8, seed=1)
    wetR = reverb(R + pr * 0.8, seed=2)
    L = L + pl + 0.32 * wetL
    R = R + pr + 0.32 * wetR
    # level: aim the body of the mix near -16 dBFS RMS, then soft-limit peaks
    rms = np.sqrt(np.mean(np.concatenate([L, R]) ** 2))
    g = 10 ** (-16 / 20) / max(rms, 1e-9)
    L *= g; R *= g
    ceil_ = 10 ** (-1 / 20)
    L = np.tanh(L / ceil_) * ceil_
    R = np.tanh(R / ceil_) * ceil_
    fade = np.ones(n)
    k = int(0.3 * SR)
    fade[-k:] = np.linspace(1, 0, k)
    L *= fade; R *= fade
    data = np.stack([L, R], 1)
    pcm = (np.clip(data, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print('audio', path, 'rms dB %.1f' % (20 * math.log10(np.sqrt(np.mean(data ** 2)))))


if __name__ == '__main__':
    import sys
    build(sys.argv[1])
