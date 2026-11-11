"""Etsy listing images for PRODUCT 3 — Weekly Planner Pro (7 images, 2700x2025, Brass Ledger layout).

Screenshots are real renders of the DEMO workbooks: the builder runs with listing print areas (overview, one day
card, trackers, calendar, setup), LibreOffice recalculates and prints them, and each page becomes a PNG.

Usage: python listing_images_wp.py [--reshoot]
Output: listings/03_Weekly_Planner_Pro/images/01_hero.png ... 07_what_you_receive.png
"""
from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_weekly_planner as B  # noqa: E402
from common import solidify_databars  # noqa: E402
import brand_listing as BL  # noqa: E402
from brand_listings_content import MAINS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "listings" / "03_Weekly_Planner_Pro"
SCREENS = OUT / "screens"

# (screen name, sheet, print area)
SHOTS = [("setup", B.S_SETUP, "A1:L24"),
         ("week_top", "Week 2", f"A1:L{B.DAY_ROW[1] - 2}"),
         ("day_card", "Week 2", f"B{B.DAY_ROW[2]}:L{B.DAY_ROW[2] + 11}"),
         ("trackers", "Week 2", f"A{B.HT}:L{B.CH + B.CH_H}"),
         ("reflection", "Week 1", f"B{B.RF}:L{B.RF + 5}"),
         ("calendar", B.S_CAL, "A1:L38")]


def shoot(edition, folder):
    """Build the DEMO workbook with listing print areas, print it with LibreOffice and save one PNG per area."""
    folder.mkdir(parents=True, exist_ok=True)
    b = B.Builder(edition, True)
    wb = b.build()
    areas = {}
    for name, sheet, area in SHOTS:
        areas.setdefault(sheet, []).append(area)
    for n in B.ORDER:
        ws = b.ws[n]
        if n in areas:
            ws.print_area = areas[n]
            ws.page_setup.orientation = "portrait" if n in B.WEEKS else "landscape"
            ws.page_setup.fitToHeight = 0
        else:
            ws.print_area = "Z300:Z300"          # empty: LibreOffice prints no page for it
    wb.active = B.ORDER.index(B.S_SETUP)
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "s.xlsx"
    wb.save(p)
    solidify_databars(p)
    for name, lay in getattr(b, "side_layers", {}).items():
        if name in areas:
            lay.inject(p, name)
    rc = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
    subprocess.run([sys.executable, rc, str(p), "300"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(p)], capture_output=True)
    # identify every printed page by its text (page order is not reliable across LibreOffice versions)
    pdf = tmp / "s.pdf"
    n_pages = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    marks = {"setup": lambda t: t.startswith("WEEKLY PLANNER PRO"), "week_top": lambda t: t.startswith("WEEK 2"),
             "trackers": lambda t: "HABIT TRACKER" in t, "reflection": lambda t: "What went well" in t,
             "calendar": lambda t: t.startswith("MONTHLY CALENDAR"),
             "day_card": lambda t: "Task checklist" in t and "WEEK 2" not in t and "HABIT" not in t}
    found = {}
    for i in range(1, n_pages + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True, text=True).stdout
        t = " ".join(t.split()).replace("Setup Wk 1 Wk 2 Wk 3 Wk 4 Wk 5 Wk 6 Month ", "").lstrip("Setup ").strip()
        for name, f in marks.items():
            if name not in found and f(t):
                found[name] = i
    missing = [s_[0] for s_ in SHOTS if s_[0] not in found]
    if missing:
        raise SystemExit(f"pages not found for {missing}")
    for name, i in found.items():
        stem = tmp / name
        subprocess.run(["pdftoppm", "-f", str(i), "-l", str(i), "-r", "260", "-png", "-singlefile", str(pdf), str(stem)],
                       capture_output=True)
        subprocess.run(["convert", f"{stem}.png", "-trim", "+repage", str(folder / f"{name}.png")])
        crop_tail(folder / f"{name}.png")
    shutil.rmtree(tmp, ignore_errors=True)


def crop_tail(path):
    """Cut the empty page below the content (the sidebar shape runs past the print area)."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    x0 = int(w * 0.08)
    last = h - 1
    while last > 0 and all(min(px[x, last]) > 245 for x in range(x0, w, 7)):
        last -= 1
    im.crop((0, 0, w, min(h, last + 12))).save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reshoot", action="store_true")
    a = ap.parse_args()
    if a.reshoot or not (SCREENS / "week_top.png").exists():
        shoot("excel", SCREENS)
    print(BL.make(MAINS["wp"]))


if __name__ == "__main__":
    main()
