"""Render shots to an MP4 with the narration laid in.

usage: python3 video/render.py OUT.mp4 [FIRST_SHOT LAST_SHOT]
"""
import os
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import FPS, H, ROOT, W, grain  # noqa: E402
from shots import SHOTS, VO_OFFSET  # noqa: E402

RATE = 48000


def select(first, last):
    ids = [s[0] for s in SHOTS]
    return SHOTS[ids.index(first): ids.index(last) + 1]


def build_audio(shots, path):
    total = sum(d for _, d, _ in shots)
    track = np.zeros(int(total * RATE) + RATE, dtype=np.float32)
    start = 0.0
    for shot_id, d, _ in shots:
        wav = os.path.join(ROOT, "narration", f"{shot_id}.wav")
        if os.path.exists(wav):
            with wave.open(wav) as w:
                assert w.getframerate() == RATE and w.getnchannels() == 1
                pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
            at = int((start + VO_OFFSET.get(shot_id, VO_OFFSET["default"])) * RATE)
            track[at: at + len(pcm)] += pcm[: len(track) - at]
        start += d
    track = track[: int(total * RATE)]
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(np.clip(track, -32768, 32767).astype(np.int16).tobytes())
    return total


def main():
    out = sys.argv[1]
    shots = select(sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else SHOTS
    audio = os.path.splitext(out)[0] + ".wav"
    total = build_audio(shots, audio)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    n = 0
    for shot_id, d, draw in shots:
        frames = round(d * FPS)
        for i in range(frames):
            frame = draw(i / FPS, d)
            ff.stdin.write(grain(frame, n).tobytes())
            n += 1
        print(f"{shot_id} done ({frames} frames)", flush=True)
    ff.stdin.close()
    ff.wait()
    os.remove(audio)
    print(f"wrote {out}: {n} frames, {total:.1f}s")


if __name__ == "__main__":
    main()
