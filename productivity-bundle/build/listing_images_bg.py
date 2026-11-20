"""Etsy listing images for PRODUCT 4 — Ultimate Budget Spreadsheet (7 images, 2700x2025, Brass Ledger layout).

Screenshots are real renders of the DEMO workbook: the builder runs with one print area per tab (fitted to one
page), LibreOffice recalculates and prints it, and each page is identified by its title text.

Usage: python listing_images_bg.py [--reshoot]
Output: listings/04_Ultimate_Budget_Spreadsheet/images/01_hero.png ... 07_what_you_receive.png
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
import build_budget as B  # noqa: E402
from common import solidify_databars  # noqa: E402
import brand_listing as BL  # noqa: E402
from brand_listings_content import MAINS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "listings" / "04_Ultimate_Budget_Spreadsheet"
SCREENS = OUT / "screens"

# (screen name, sheet, print area, title the page starts with)
SHOTS = [("dashboard", B.S_DASH, "A1:M63", "ALL-IN-ONE DASHBOARD"), ("month", "October", "A1:M57", "OCTOBER"),
         ("annual", B.S_AT, "A1:V41", "ANNUAL TOTALS"), ("calendar", B.S_CAL, "A1:K39", "AUTOMATED CALENDAR"),
         ("debt", B.S_DC, "A1:X24", "DEBT CALCULATOR"), ("funds", B.S_SF, "A1:N34", "SINKING FUNDS"),
         ("rule", B.S_503, "A1:K36", "50/30/20 DASHBOARD"), ("networth", B.S_NW, "A1:M43", "NET WORTH"),
         ("invest", B.S_IF, "A1:N41", "INVESTMENT FORECAST"), ("nospend", B.S_NS, "A1:R40", "NO-SPENDING CHALLENGE"),
         ("transactions", B.S_TR, "A1:K40", "VARIABLE TRANSACTIONS"), ("recurring", B.S_RT, "A1:M30", "RECURRING TRANSACTIONS"),
         ("setup", B.S_SET, "A1:K36", "EASY SETUP"), ("paycheck", B.S_PC, "A1:K30", "PAYCHECK DASHBOARD"),
         ("distribution", B.S_ED, "A1:N40", "EXPENSE DISTRIBUTION"), ("accounts", B.S_BA, "A1:J20", "BANK ACCOUNTS")]


def crop_tail(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    last = h - 1
    while last > 0 and all(min(px[x, last]) > 245 for x in range(int(w * 0.08), w, 7)):
        last -= 1
    im.crop((0, 0, w, min(h, last + 12))).save(path)


def shoot(edition, folder, only=None):
    folder.mkdir(parents=True, exist_ok=True)
    b = B.Builder(edition, True)
    wb = b.build()
    wanted = {s[1]: s for s in SHOTS if not only or s[0] in only}
    for n in B.ORDER:
        ws = b.ws[n]
        if n in wanted:
            ws.print_area = wanted[n][2]
            ws.page_setup.fitToHeight = 1
            ws.page_setup.fitToWidth = 1
        else:
            ws.print_area = "ZZ900:ZZ900"
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "s.xlsx"
    wb.save(p)
    solidify_databars(p)
    for name, lay in getattr(b, "side_layers", {}).items():
        lay.inject(p, name)
    rc = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
    subprocess.run([sys.executable, rc, str(p), "900"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(p)], capture_output=True)
    pdf = tmp / "s.pdf"
    n_pages = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    found = {}
    for i in range(1, n_pages + 1):
        t = " ".join(subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True, text=True).stdout.split())
        for name, _s, _a, mark in wanted.values():
            if name not in found and mark in t[:400]:
                found[name] = i
    missing = [s[0] for s in wanted.values() if s[0] not in found]
    if missing:
        raise SystemExit(f"pages not found for {missing}")
    for name, i in found.items():
        stem = tmp / name
        subprocess.run(["pdftoppm", "-f", str(i), "-l", str(i), "-r", "220", "-png", "-singlefile", str(pdf), str(stem)], capture_output=True)
        subprocess.run(["convert", f"{stem}.png", "-trim", "+repage", str(folder / f"{name}.png")])
        w_ = Image.open(folder / f"{name}.png").width
        if w_ < 2000:                                  # tall tab fitted to one page: render again, sharper
            subprocess.run(["pdftoppm", "-f", str(i), "-l", str(i), "-r", str(int(220 * 2300 / w_)), "-png", "-singlefile", str(pdf), str(stem)],
                           capture_output=True)
            subprocess.run(["convert", f"{stem}.png", "-trim", "+repage", str(folder / f"{name}.png")])
        crop_tail(folder / f"{name}.png")
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reshoot", action="store_true")
    a = ap.parse_args()
    if a.reshoot or not (SCREENS / "dashboard.png").exists():
        shoot("excel", SCREENS)
    print(BL.make(MAINS["bg"]))


if __name__ == "__main__":
    main()
