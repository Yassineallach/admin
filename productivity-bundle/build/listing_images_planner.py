"""Etsy listing images for PRODUCT 2 — Ultimate OneNote Planner (7 images, 2700x2025, Brass Ledger layout).

Every screenshot is a real page of the hyperlinked PDF planner (rendered with pdftoppm), so the images never
show pages the product doesn't have. The footer says so: the OneNote notebook holds the same pages, but
OneNote draws them with its own fonts, so the PDF is what the pictures show.

Usage: python listing_images_planner.py
Output: listings/02_Ultimate_OneNote_Planner/images/01_hero.png ... 07_what_you_receive.png
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
import planner_pdf as PP  # noqa: E402
import brand_listing as BL  # noqa: E402
from brand_listings_content import MAINS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "dist" / "02_Ultimate_OneNote_Planner" / "PDF_Planner" / "Ultimate_Planner_2027_Hyperlinked.pdf"
OUT = ROOT / "listings" / "02_Ultimate_OneNote_Planner"
SCREENS = OUT / "screens"


def page_numbers():
    PP.MARKS.clear()
    PP.build_pdf(Path(tempfile.mkdtemp()) / "marks.pdf")
    return dict(PP.MARKS)


def render_pages(keys):
    SCREENS.mkdir(parents=True, exist_ok=True)
    marks = page_numbers()
    for k in keys:
        out = SCREENS / f"{k}.png"
        if not out.exists():
            n = str(marks[k])
            subprocess.run(["pdftoppm", "-f", n, "-l", n, "-r", "220", "-png", "-singlefile", str(PDF), str(out)[:-4]], check=True)


def main():
    for f in SCREENS.glob("*.png"):
        f.unlink()
    render_pages(["index", "w1", "m1_cal"])
    print(BL.make(MAINS["planner"]))


if __name__ == "__main__":
    main()
