"""Listing video for each product: a 12-second silent slideshow of the listing images (Etsy accepts 5–15 s videos).

Usage: python listing_video.py        -> listings/<product>/video/listing_video.mp4
"""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "listings"
PICKS = {"01_Ultimate_Project_Manager": [1, 3, 5, 4, 2], "02_Ultimate_OneNote_Planner": [1, 3, 5, 6, 2],
         "03_Weekly_Planner_Pro": [1, 3, 4, 5, 6], "04_Ultimate_Budget_Spreadsheet": [1, 3, 4, 7, 2]}
SEC = 2.4

for prod, idx in PICKS.items():
    imgs = sorted((ROOT / prod / "images").glob("*.png"))
    chosen = [imgs[i - 1] for i in idx]
    out = ROOT / prod / "video"
    out.mkdir(exist_ok=True)
    lst = Path(tempfile.mkdtemp()) / "list.txt"
    lst.write_text("".join(f"file '{p}'\nduration {SEC}\n" for p in chosen) + f"file '{chosen[-1]}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-vf", "scale=1440:1080,format=yuv420p", "-r", "30", "-c:v", "libx264", "-crf", "20", "-an",
                    str(out / "listing_video.mp4")], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(out / "listing_video.mp4")], capture_output=True, text=True).stdout.strip()
    print(prod, f"{float(dur):.1f}s", f"{(out / 'listing_video.mp4').stat().st_size / 1e6:.1f} MB")
