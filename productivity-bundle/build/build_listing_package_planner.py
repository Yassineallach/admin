"""Build the files a buyer downloads from Etsy for PRODUCT 2 (listings/02_Ultimate_OneNote_Planner/etsy_upload/).

  Ultimate_Planner_2027.onepkg            — OneNote notebook; only once the seller has exported it (see the Seller Guide)
                                            and put it in listings/02_Ultimate_OneNote_Planner/
  Ultimate_Planner_2027_Hyperlinked.pdf   — the PDF planner, dated 2027
  Ultimate_Planner_Undated_Hyperlinked.pdf — the same planner with blank dates (any year)
  Planner_User_Guide.pdf                  — buyer guide (without OneNote-notebook sections when no .onepkg is included)
  START_HERE.pdf                          — which file to open in which app

Four files (five with the .onepkg), within Etsy's limit of five files of 20 MB each.
Usage: python build_listing_package_planner.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import md_to_pdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "02_Ultimate_OneNote_Planner"
LST = ROOT / "listings" / "02_Ultimate_OneNote_Planner"
OUT = LST / "etsy_upload"
ONEPKG = "Ultimate_Planner_2027.onepkg"


def start_here_md(cfg, has_onepkg):
    thanks = f"Thank you for your purchase{' from ' + cfg['shop_name'] if cfg.get('shop_name') else ''}!"
    shared = cfg.get("onenote_shared_notebook_link", "")
    onenote_row = ("| **OneNote for Windows** (Microsoft 365 / desktop) | **Ultimate_Planner_2027.onepkg**: double-click it and choose where to keep the notebook (pick OneDrive to sync it to your phone) |\n"
                   if has_onepkg else "")
    shared_txt = (f"\n**OneNote on Mac, web, iPad or phone:** open this link while signed in to your Microsoft account "
                  f"and copy the notebook to your OneDrive: {shared}\n" if shared else "")
    return f"""# Start Here — Ultimate Planner 2027

{thanks} Here is which file to open for the app you use.

## Which file do I open?

| You use | Open this file |
|---|---|
{onenote_row}| **OneNote for Mac, web or iPad** | **Ultimate_Planner_2027_Hyperlinked.pdf**: insert it into a page with *Insert › File/PDF Printout* |
| **GoodNotes, Notability, Xodo, Drawboard, Samsung Notes** | **Ultimate_Planner_2027_Hyperlinked.pdf**: import it as a new notebook. The tabs and index links are clickable |
| **Paper** | Print **Ultimate_Planner_2027_Hyperlinked.pdf** in landscape, "fit to page" |

**Two editions are included.** *Ultimate_Planner_2027_Hyperlinked.pdf* is dated for 2027. *Ultimate_Planner_Undated_Hyperlinked.pdf* has the same pages with blank dates, so you can start any month and reuse it every year.
{shared_txt}
## First steps

1. Open the **General Index**: it's the first page of the Start section in OneNote, or page 2 of the PDF.
2. Tap any link to jump to a month, week, template or note page.
3. **⌂ Index** at the top of every page brings you back.

The full **User Guide** is in Planner_User_Guide.pdf.

## Need help?

Send me a message on Etsy. I'm happy to help you get set up.
"""


def pdf_only_guide(md: str) -> str:
    """The buyer guide for a download without the OneNote notebook: no .onepkg rows, notes or sections."""
    out, skip = [], False
    for ln in md.splitlines():
        if ln.startswith("## "):
            skip = ln.strip() == "## Using the OneNote notebook"
        if skip or ".onepkg" in ln:
            continue
        out.append(ln)
    text_ = "\n".join(out)
    text_ = text_.replace("A complete digital planner for OneNote and PDF note-taking apps:", "A complete hyperlinked digital planner for PDF note-taking apps:")
    text_ = text_.replace("**Can I change colours or add pages?** Yes. In OneNote everything is editable: add rows and pages, rename sections, change colours.",
                          "**Can I add pages?** Yes. Duplicate any page in your note app as often as you like.")
    return text_


def main():
    cfg = json.loads((LST / "listing_config.json").read_text())
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    src = next((p for p in (LST / ONEPKG, DIST / ONEPKG) if p.exists()), None)
    if src:
        shutil.copy2(src, OUT / ONEPKG)
    shutil.copy2(DIST / "PDF_Planner" / "Ultimate_Planner_2027_Hyperlinked.pdf", OUT)
    shutil.copy2(DIST / "PDF_Planner" / "Ultimate_Planner_Undated_Hyperlinked.pdf", OUT)
    guide = (DIST / "Guides" / "OneNote_Planner_User_Guide.md").read_text(encoding="utf-8")
    if not src:
        guide = pdf_only_guide(guide)
    gmd = OUT / "Planner_User_Guide.md"
    gmd.write_text(guide, encoding="utf-8")
    md_to_pdf.render(gmd, OUT / "Planner_User_Guide.pdf", footer="Ultimate Planner 2027 · User Guide")
    gmd.unlink()
    md = OUT / "START_HERE.md"
    md.write_text(start_here_md(cfg, bool(src)), encoding="utf-8")
    md_to_pdf.render(md, OUT / "START_HERE.pdf", footer="Ultimate Planner 2027 · Start Here")
    md.unlink()
    for f in sorted(OUT.iterdir()):
        mb = f.stat().st_size / 1e6
        print(f"{f.name}: {mb:.2f} MB", "(OVER Etsy's 20 MB limit!)" if mb > 20 else "")
    if not src:
        print(f"note: no {ONEPKG} — built the PDF-planner package. Use 'Version A' in LISTING.md. To sell the OneNote "
              f"notebook too, export it (Seller Guide), put it in {LST.relative_to(ROOT)}/, rerun this script and "
              f"listing_images_planner.py, then use 'Version B'.")


if __name__ == "__main__":
    main()
