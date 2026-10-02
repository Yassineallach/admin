"""Prints short-term loudness (EBU R128, 3 s window) and momentary loudness per
shot, plus integrated loudness and true peak, for a wav or mp4."""
import re
import subprocess
import sys

B = 60.0 / 110.0
SHOTS = [(0, 8, "1 hook (no music)"), (8, 16, "2 title"), (16, 24, "3 rules"), (24, 32, "4 gameplay"),
         (32, 36, "5a hint"), (36, 40, "5b packs"), (40, 41, "6 silence beat"), (41, 48, "6 payoff"),
         (48, 56, "7 end card"), (56, 60, "7 final note")]

out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", sys.argv[1], "-af", "ebur128=peak=true",
                      "-f", "null", "-"], capture_output=True, text=True).stderr
rows = []
for line in out.splitlines():
    m = re.search(r"t:\s*([\d.]+).*M:\s*([-\d.]+)\s+S:\s*([-\d.]+)", line)
    if m:
        rows.append(tuple(float(v) for v in m.groups()))
for a, b, name in SHOTS:
    seg = [r for r in rows if a * B <= r[0] < b * B]
    if not seg:
        continue
    mm = max(r[1] for r in seg)
    ms = sum(10 ** (r[1] / 10) for r in seg) / len(seg)
    import math
    print("%-18s %5.2f-%5.2fs  mean M %6.1f LUFS  max M %6.1f" % (name, a * B, b * B, 10 * math.log10(ms + 1e-12), mm))
summ = out[out.find("Summary"):]
i = re.search(r"I:\s*([-\d.]+) LUFS", summ)
tp = re.search(r"Peak:\s*([-\d.]+) dBFS", summ)
print("integrated %s LUFS, true peak %s dBFS" % (i.group(1), tp.group(1) if tp else "?"))
