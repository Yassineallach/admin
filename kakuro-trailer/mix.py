"""Mixes the trailer soundtrack from the game's own audio.

Music: assets/audio/menu_loop.ogg ("Sunny Grid", 110 bpm), entering on the
first cut after the hook. SFX: the game's synthesized effects, cued from the
event list trailer.py writes (every cue is an on-screen event).
    python3 trailer.py events > build/sfx.json && python3 mix.py build/sfx.json build/mix.wav
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.join(HERE, "assets", "audio")
B = 60.0 / 110.0


def load(name):
    path = os.path.join(AUD, name)
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    assert sr == SR, (name, sr)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    return x


def db(g):
    return 10 ** (g / 20.0)


def main():
    ev = json.load(open(sys.argv[1]))
    end = ev["end"]
    n = int(end * SR) + 1
    out = np.zeros((n, 2), np.float32)

    # music with gain automation (dB points, linear in dB between them)
    music = load("menu_loop.ogg")
    m0 = ev["music_start"]
    pts = [(0.0, -80), (m0 - 0.01, -80), (m0, 0), (39.75 * B, 0), (40.0 * B, -80),   # beat of silence before the last digit
           (43.6 * B, -80), (44.0 * B, -13), (47.0 * B, -13), (48.0 * B, 0),          # back in, ducked under the win jingle
           (55.9 * B, 0), (56.0 * B, -80), (end + 1, -80)]                            # stops on the final note
    t = np.arange(n) / SR
    g_db = np.interp(t, [p[0] for p in pts], [p[1] for p in pts])
    gain = db(g_db) * db(-1.0)
    gain[g_db <= -79] = 0.0
    idx = ((t - m0) * SR).astype(np.int64)
    ok = idx >= 0
    seg = np.zeros((n, 2), np.float32)
    seg[ok] = music[idx[ok] % len(music)]
    out += seg * gain[:, None]

    # sfx: one cue per on-screen event
    cache = {}
    for (ts, name, gdb) in ev["sfx"]:
        if name not in cache:
            cache[name] = load(name + ".wav")
        x = cache[name] * db(gdb)
        i0 = int(ts * SR)
        i1 = min(n, i0 + len(x))
        if i0 < n:
            out[i0:i1] += x[: i1 - i0]

    # 300 ms fade at the very end only (the final note has already rung out)
    f = int(0.3 * SR)
    out[-f:] *= np.linspace(1, 0, f)[:, None]
    sf.write(sys.argv[2], out, SR, subtype="FLOAT")
    print("peak %.2f dBFS" % (20 * np.log10(np.abs(out).max() + 1e-9)))


if __name__ == "__main__":
    main()
