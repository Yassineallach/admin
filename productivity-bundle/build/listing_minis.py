"""Etsy listings for the six mini-products: real screenshots, 7 brand-layout images each, LISTING.md and the etsy_upload package.

Usage: python listing_minis.py [--only debt funds ...] [--reshoot]
Output: listings/05_Minis/<Product>/{screens,screens_sheets,images,etsy_upload}/ and LISTING.md
"""
from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_minis as M  # noqa: E402
import md_to_pdf  # noqa: E402
from common import solidify_databars  # noqa: E402
import brand_listing as BL  # noqa: E402
from brand_listings_content import mini_spec  # noqa: E402
from minis_content import COMMON_NOTE, MINIS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


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
        w_ = Image.open(folder / f"{name}.png").width
        if w_ < 2000:                                  # tall tab fitted to one page: render again, sharper
            subprocess.run(["pdftoppm", "-f", str(i), "-l", str(i), "-r", str(int(220 * 2300 / w_)), "-png", "-singlefile", str(pdf), str(stem)],
                           capture_output=True)
            subprocess.run(["convert", f"{stem}.png", "-trim", "+repage", str(folder / f"{name}.png")])
        crop_tail(folder / f"{name}.png")
    shutil.rmtree(tmp, ignore_errors=True)


class Lister:
    def __init__(self, key):
        self.key, self.c = key, MINIS[key]
        self.name, self.slug, _ = M.PRODUCTS[key]
        self.out = ROOT / "listings" / "05_Minis" / self.slug
        self.screens = self.out / "screens"

    def images_all(self):
        self.spec = mini_spec(self.key)
        BL.make(self.spec)

    def listing_md(self):
        c = self.c
        tags = [t.strip() for t in c["tags"].split(",")]
        assert len(c["title"]) <= 140, (self.key, len(c["title"]))
        assert len(tags) == 13 and all(len(t) <= 20 for t in tags), (self.key, [t for t in tags if len(t) > 20])
        price, launch, market = c["price"]
        md = f"""# Etsy listing — {self.name}

Copy-paste ready. Every screenshot is a real render of the DEMO workbook.

{BL.photos_table(mini_spec(self.key))}
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
- [ ] Upload the 7 images in order and add the alt text.
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

Thank you for your purchase from Brass Ledger. Your download has this guide and **{self.slug}.zip**. Unzip it first (double-click on Mac; right-click › Extract All on Windows).

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

Every workbook opens on a **Start** tab with settings and instructions. White cells with a border are for your input; shaded cells calculate by themselves.

## Need help?

Send me a message on Etsy and I will help.
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
        L_.images_all()
        L_.listing_md()
        L_.package()
        print("done", key)


if __name__ == "__main__":
    main()
