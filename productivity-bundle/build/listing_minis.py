"""Etsy listings for the six mini-products: real screenshots, 6 images each, LISTING.md and the etsy_upload package.

Usage: python listing_minis.py [--only debt funds ...] [--reshoot]
Output: listings/05_Minis/<Product>/{screens,screens_sheets,images,etsy_upload}/ and LISTING.md
"""
from __future__ import annotations

import argparse
import glob
import io
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_minis as M  # noqa: E402
import icons  # noqa: E402
import md_to_pdf  # noqa: E402
from common import solidify_databars  # noqa: E402
from listing_kit import (CORAL, DARK, GREY, MINT, NAVY, ORANGE, TEAL, W, WHITE, canvas, card, footer, framed,  # noqa: E402
                         heading, icon_bullet, laptop, pill, text)
from minis_content import COMMON_NOTE, MINIS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FOOT = "Instant download  ·  Excel + Google Sheets  ·  No macros"


def crop_tail(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    last = h - 1
    while last > 0 and all(min(px[x, last]) > 245 for x in range(int(w * 0.08), w, 7)):
        last -= 1
    im.crop((0, 0, w, min(h, last + 12))).save(path)


def shoot(key, edition, folder, only=None):
    folder.mkdir(parents=True, exist_ok=True)
    b = M.Mini(key, edition, True)
    wb = b.build()
    shots = [s for s in MINIS[key]["shots"] if not only or s[0] in only]
    areas = {}
    for name, sheet, area, mark in shots:
        areas.setdefault(sheet, []).append(area)
    for n in b.order:
        ws = b.ws[n]
        if n in areas:
            ws.print_area = areas[n]
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.page_setup.orientation = "landscape"
        else:
            ws.print_area = "ZZ900:ZZ900"
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "s.xlsx"
    wb.save(p)
    solidify_databars(p)
    for name, lay in b.side_layers.items():
        lay.inject(p, name)
    rc = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
    subprocess.run([sys.executable, rc, str(p), "300"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(p)], capture_output=True)
    pdf = tmp / "s.pdf"
    n_pages = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    found = {}
    for i in range(1, n_pages + 1):
        t = " ".join(subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True, text=True).stdout.split())
        for name, _s, _a, mark in sorted(shots, key=lambda x: -len(x[3])):     # most specific title first
            if name not in found and mark in t[:300]:
                found[name] = i
                break
    missing = [s[0] for s in shots if s[0] not in found]
    if missing:
        raise SystemExit(f"{key}: pages not found for {missing}")
    for name, i in found.items():
        stem = tmp / name
        subprocess.run(["pdftoppm", "-f", str(i), "-l", str(i), "-r", "220", "-png", "-singlefile", str(pdf), str(stem)], capture_output=True)
        subprocess.run(["convert", f"{stem}.png", "-trim", "+repage", str(folder / f"{name}.png")])
        crop_tail(folder / f"{name}.png")
    shutil.rmtree(tmp, ignore_errors=True)


class Lister:
    def __init__(self, key):
        self.key, self.c = key, MINIS[key]
        self.name, self.slug, _ = M.PRODUCTS[key]
        self.out = ROOT / "listings" / "05_Minis" / self.slug
        self.screens, self.sheets, self.images = self.out / "screens", self.out / "screens_sheets", self.out / "images"

    def shot(self, name, top=0.0, bottom=1.0, folder=None, left=0.0, right=1.0):
        im = Image.open((folder or self.screens) / f"{name}.png").convert("RGB")
        w, h = im.size
        return im.crop((int(w * left), int(h * top), int(w * right), int(h * bottom)))

    def save(self, img, name):
        self.images.mkdir(parents=True, exist_ok=True)
        img.save(self.images / name, "PNG", optimize=True)

    def ic(self, name):
        return icons.ICONS[name](c="FFFFFF", size=96)

    def hero(self):
        kicker, title, checks = self.c["hero"]
        img = canvas()
        text(img, (150, 170), kicker, 60, "SemiBold", TEAL)
        b = text(img, (150, 250), title, 104, "ExtraBold", NAVY, spacing=0)
        text(img, (150, b[3] + 50), "Excel & Google Sheets template", 46, "Medium", DARK)
        y = b[3] + 160
        for t_ in checks:
            img = card(img, (150, y, 860, y + 88), radius=44, shade=False, fill=WHITE)
            text(img, (200, y + 44), "✓", 40, "Bold", TEAL, anchor="lm")
            text(img, (260, y + 44), t_, 36, "SemiBold", DARK, anchor="lm")
            y += 110
        x_ = pill(img, (150, y + 40), "NO MACROS", 38, TEAL)
        pill(img, (x_ + 26, y + 40), "DEMO + BLANK", 38, ORANGE)
        t0, b0, l0, r0 = self.c.get("hero_crop", (0, 0.62, 0, 1))
        img, _ = laptop(img, self.shot("main", t0, b0, left=l0, right=r0), 1640, 330, 1300)
        footer(img, FOOT)
        self.save(img, "01_hero.png")

    def feature(self, spec, shot, fname):
        title, sub, bullets = spec
        img = canvas()
        heading(img, title, sub)
        img, _ = framed(img, self.shot(shot), 110, 360, 1450, 1330)
        y = 400
        for icon, t_, b_ in bullets:
            y = icon_bullet(img, (1640, y), self.ic(icon), t_, b_, w=680, title_size=40, body_size=29) + 46
        footer(img, FOOT)
        self.save(img, fname)

    def start_tab(self):
        img = canvas()
        heading(img, "Easy to start", "A Start tab with instructions, settings and links to every tab")
        img, _ = framed(img, self.shot("start"), 110, 360, 1450, 1330)
        steps = self.c["steps"]
        y = 420
        for i, s_ in enumerate(steps):
            d = ImageDraw.Draw(img)
            d.ellipse((1640, y, 1740, y + 100), fill=TEAL)
            text(img, (1690, y + 50), str(i + 1), 48, "Bold", WHITE, anchor="mm")
            text(img, (1770, y + 22), s_, 38, "SemiBold", DARK, max_w=540)
            y += 200
        footer(img, FOOT)
        self.save(img, "04_easy_start.png")

    def included(self):
        img = canvas()
        heading(img, "What you get", "Two editions, demo and blank, ready in minutes")
        img = card(img, (130, 380, W - 130, 900), radius=40)
        text(img, (190, 430), "YOU RECEIVE", 30, "Bold", TEAL)
        x, y = 190, 500
        for f_ in ("Excel – DEMO", "Excel – BLANK", "Google Sheets – DEMO", "Google Sheets – BLANK", "Start Here PDF"):
            x = pill(img, (x, y), f_, 34, MINT, NAVY) + 26
        text(img, (190, 640), "DEMO files show sample data so you can explore; BLANK files are ready for your own numbers.",
             34, "Medium", GREY, max_w=W - 400)
        img = card(img, (130, 980, W - 130, 1620), radius=40)
        text(img, (190, 1030), "WORKS WITH", 32, "Bold", TEAL)
        rows = [("Microsoft Excel (Windows & Mac)", "Clickable icon sidebar, protected formulas"),
                ("Excel for the web", "Opens the same Excel file"),
                ("Google Sheets", "Dedicated edition with the same formulas and charts"),
                ("Not for Apple Numbers", "Not supported")]
        y = 1100
        for t_, b_ in rows:
            mark, color = ("✗", CORAL) if t_.startswith("Not") else ("✓", TEAL)
            text(img, (200, y), mark, 44, "Bold", color)
            text(img, (270, y), t_, 38, "SemiBold", DARK)
            text(img, (1150, y + 4), b_, 32, "Regular", GREY, max_w=1050)
            y += 120
        footer(img, FOOT)
        self.save(img, "05_whats_included.png")

    def editions(self):
        img = canvas()
        heading(img, "Excel & Google Sheets editions", "Both included — pick the app you already use")
        img, _ = framed(img, self.shot("main", 0, 0.55), 110, 330, 1480, 1000)
        img, _ = framed(img, self.shot("main", 0, 0.55, folder=self.sheets), 1000, 800, 1290, 860)
        pill(img, (1640, 380), "Excel edition", 38, NAVY)
        pill(img, (140, 1230), "Google Sheets edition", 38, TEAL)
        footer(img, FOOT)
        self.save(img, "06_excel_and_sheets.png")

    def images_all(self):
        self.hero()
        self.feature(self.c["f1"], "main", "02_main_feature.png")
        second = [s[0] for s in self.c["shots"] if s[0] not in ("main", "start")]
        if self.c["f2"] and second:
            self.feature(self.c["f2"], second[0], "03_second_feature.png")
        else:
            self.feature(("Every detail at a glance", self.c["f1"][1], self.c["f1"][2][2:] or self.c["f1"][2]), "main", "03_second_feature.png")
        self.start_tab()
        self.included()
        self.editions()

    def listing_md(self):
        c = self.c
        tags = [t.strip() for t in c["tags"].split(",")]
        assert len(c["title"]) <= 140, (self.key, len(c["title"]))
        assert len(tags) == 13 and all(len(t) <= 20 for t in tags), (self.key, [t for t in tags if len(t) > 20])
        alts = {"01_hero.png": f"{self.name} spreadsheet shown on a laptop", "02_main_feature.png": f"{self.name}: {c['f1'][0].lower()}",
                "03_second_feature.png": f"{self.name}: {(c['f2'] or c['f1'])[0].lower()}",
                "04_easy_start.png": "Start tab with settings, instructions and links", "05_whats_included.png": "Files included and compatibility",
                "06_excel_and_sheets.png": "The Excel edition and the Google Sheets edition"}
        price, launch, market = c["price"]
        md = f"""# Etsy listing — {self.name}

Copy-paste ready. Every screenshot is a real render of the DEMO workbook.

## Photos (upload in this order)

| # | File | Alt text |
|---|---|---|
""" + "\n".join(f"| {i + 1} | {f} | {a} |" for i, (f, a) in enumerate(alts.items())) + f"""

## Title ({len(c['title'])} / 140 characters)

```
{c['title']}
```

## Listing details

| Field | Value |
|---|---|
| Who made it | I did |
| What is it | A finished product |
| When was it made | 2020 – 2026 |
| Type | Digital files |
| Category (suggested) | Paper & Party Supplies › Paper › Calendars & Planners (pick the closest current option) |
| Instant download | Yes |

## Tags (13 / 13)

```
{c['tags']}
```

## Materials

```
Microsoft Excel, Google Sheets, digital download, spreadsheet template
```

## Price

- **List {price}**. Launch at about **{launch}** with a sale until the first reviews arrive.
- {market} Small focused trackers are entry products: they bring buyers into the shop, where the full templates are.

## Description

```
{c['desc'].strip()}

{COMMON_NOTE}
```

> **AI disclosure (check Etsy's current policy).** Parts of this product and its listing images were made with AI assistance. If Etsy still asks for it, add *"Designed by me with the help of AI tools."* to the description.

## Files to upload

Upload everything in `etsy_upload/`: `{self.slug}.zip` and `START_HERE.pdf`.

## Seller checklist

- [ ] Open the Excel DEMO file in real Excel and the Google Sheets file in Google Sheets once.
- [ ] Upload the 6 images in order and add the alt text.
- [ ] Paste the title, tags, description and materials. Set the price.
- [ ] Upload the two files from `etsy_upload/`.
"""
        (self.out / "LISTING.md").write_text(md, encoding="utf-8")

    def package(self):
        up = self.out / "etsy_upload"
        if up.exists():
            shutil.rmtree(up)
        up.mkdir(parents=True)
        z = up / f"{self.slug}.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for ed in ("excel", "gsheets"):
                for demo in (True, False):
                    p = M.out_path(self.key, ed, demo)
                    zf.write(p, Path(self.slug) / p.parent.name / p.name)
        steps = "\n".join(f"{i + 1}. {s}." for i, s in enumerate(self.c["steps"]))
        md = up / "START_HERE.md"
        md.write_text(f"""# Start Here — {self.name}

Thank you for your purchase! Your download has this guide and **{self.slug}.zip**. Unzip it first (double-click on Mac; right-click › Extract All on Windows).

## Which file do I open?

| You use | Open this file |
|---|---|
| Microsoft Excel (Windows or Mac) | Excel / …_Excel_DEMO.xlsx to explore, …_Excel_BLANK.xlsx for your own numbers |
| Excel for the web | Upload the Excel file to OneDrive and open it there |
| Google Sheets | Google_Sheets / …_GoogleSheets_DEMO.xlsx or …_BLANK.xlsx (see below) |

## Excel

Double-click the file. If you see *Protected View*, click **Enable Editing**. The file has no macros.

## Google Sheets

1. Go to drive.google.com › **New › File upload** and choose a file from the Google_Sheets folder.
2. Right-click it › **Open with › Google Sheets**.
3. **File › Save as Google Sheets.** Work in that copy.

## Getting started

{steps}

Every workbook opens on a **Start** tab with settings and instructions. Light-mint cells are for your input; grey cells calculate by themselves.

## Need help?

Send me a message on Etsy. I'm happy to help.
""", encoding="utf-8")
        md_to_pdf.render(md, up / "START_HERE.pdf", footer=f"{self.name} · Start Here")
        md.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=list(MINIS))
    ap.add_argument("--reshoot", action="store_true")
    a = ap.parse_args()
    for key in a.only:
        L_ = Lister(key)
        if a.reshoot or not (L_.screens / "main.png").exists():
            shoot(key, "excel", L_.screens)
            shoot(key, "gsheets", L_.sheets, only={"main"})
        L_.images_all()
        L_.listing_md()
        L_.package()
        print("done", key)


if __name__ == "__main__":
    main()
