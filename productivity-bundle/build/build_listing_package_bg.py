"""Build the files a buyer downloads from Etsy for PRODUCT 4 (listings/04_Ultimate_Budget_Spreadsheet/etsy_upload/).

  Ultimate_Budget_Spreadsheet.zip  — Excel + Google Sheets editions (DEMO & BLANK) + PDF user guide
  START_HERE.pdf                — how to open the files; Google Sheets copy links from listing_config.json

Usage: python build_listing_package_bg.py
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import md_to_pdf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "04_Ultimate_Budget_Spreadsheet"
LST = ROOT / "listings" / "04_Ultimate_Budget_Spreadsheet"
OUT = LST / "etsy_upload"


def start_here_md(cfg):
    demo, blank = cfg.get("google_sheets_demo_copy_link", ""), cfg.get("google_sheets_blank_copy_link", "")
    thanks = f"Thank you for your purchase{' from ' + cfg['shop_name'] if cfg.get('shop_name') else ''}."
    if demo or blank:
        sheets = ("**Google Sheets: quickest way.** Click a link below while signed in to Google and choose *Make a copy*. "
                  "The copy is yours and saves in your Google Drive.\n\n"
                  + (f"- Demo version (sample data): {demo}\n" if demo else "")
                  + (f"- Blank version (start fresh): {blank}\n" if blank else ""))
    else:
        sheets = ""
    return f"""# Start Here — Ultimate Budget Spreadsheet

{thanks} Your download has two files: this guide and **Ultimate_Budget_Spreadsheet.zip**. Unzip it first (double-click on Mac; right-click › Extract All on Windows).

## Which file do I open?

| You use | Open this file |
|---|---|
| Microsoft Excel (Windows or Mac) | Excel / Ultimate_Budget_Spreadsheet_Excel_DEMO.xlsx to explore, …_BLANK.xlsx for real work |
| Excel for the web | The same Excel files: upload them to OneDrive and open them there |
| Google Sheets | Google_Sheets / …_GoogleSheets_DEMO.xlsx or …_BLANK.xlsx (see below) |

## Excel

1. Double-click the .xlsx file.
2. If you see *Protected View*, click **Enable Editing**. The file has no macros.
3. Start on the **Easy Setup** tab: currency, budget year, first month and categories. Then add accounts, recurring items and transactions.

## Google Sheets

{sheets}**Or upload the file yourself:**

1. Go to drive.google.com › **New › File upload** and choose a file from the Google_Sheets folder.
2. Right-click it › **Open with › Google Sheets**.
3. **File › Save as Google Sheets.** Work in that copy.

## Tips

- White cells with a border are for your input; shaded cells are formulas, so don't type over them.
- The DEMO file is fixed to a sample date (7 Nov 2026) so the demo always looks current. Clear Easy Setup › *Today's date override* to use the real date.
- Amounts are always positive: the category decides whether it's income, an expense, savings or a debt payment.
- The full **User Guide** (PDF) is inside the ZIP, in the Guides folder.

## Need help?

Send me a message on Etsy and I will help you get set up.
"""


def main():
    cfg = json.loads((LST / "listing_config.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    z = OUT / "Ultimate_Budget_Spreadsheet.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(DIST.rglob("*")):
            if f.is_file() and f.suffix in (".xlsx", ".pdf"):
                zf.write(f, Path("Ultimate_Budget_Spreadsheet") / f.relative_to(DIST))
    md = OUT / "START_HERE.md"
    md.write_text(start_here_md(cfg), encoding="utf-8")
    md_to_pdf.render(md, OUT / "START_HERE.pdf", footer="Ultimate Budget Spreadsheet · Start Here")
    md.unlink()
    for f in sorted(OUT.iterdir()):
        mb = f.stat().st_size / 1e6
        print(f"{f.name}: {mb:.2f} MB", "(OVER Etsy's 20 MB limit!)" if mb > 20 else "")
    if not (cfg.get("google_sheets_demo_copy_link") or cfg.get("google_sheets_blank_copy_link")):
        print("note: no Google Sheets copy links yet — START_HERE.pdf explains the upload route instead.")


if __name__ == "__main__":
    main()
