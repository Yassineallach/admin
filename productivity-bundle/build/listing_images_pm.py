"""Etsy listing images for PRODUCT 1 — Ultimate Project Manager (7 images, 2700x2025, Brass Ledger layout).

Usage: python listing_images_pm.py   (renders screenshots first if missing)
Output: listings/01_Ultimate_Project_Manager/images/01_hero.png ... 07_what_you_receive.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_screens  # noqa: E402
import brand_listing as BL  # noqa: E402
from brand_listings_content import MAINS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "01_Ultimate_Project_Manager"
OUT = ROOT / "listings" / "01_Ultimate_Project_Manager"
SCREENS = OUT / "screens"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reshoot", action="store_true")
    a = ap.parse_args()
    if a.reshoot or not (SCREENS / "AllinOne_Dashboard.png").exists():
        render_screens.render(DIST / "Excel" / "Ultimate_Project_Manager_Excel_DEMO.xlsx", SCREENS, 220)
    print(BL.make(MAINS["pm"]))


if __name__ == "__main__":
    main()
