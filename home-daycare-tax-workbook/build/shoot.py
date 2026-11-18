"""Real screenshots of the SAMPLE daycare workbook (LibreOffice headless -> PDF -> PNG), for the listing images and the guide.

Each shot builds the sample workbook, prints one area of one tab (everything else prints nothing), recalculates it
in LibreOffice, converts it to PDF and rasterises the page. Nothing is drawn by hand.

Usage: python shoot.py [OUT_DIR]   -> OUT_DIR/<name>.png
"""
from __future__ import annotations

import glob
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, "/home/user/admin/productivity-bundle/build")
import brand  # noqa: E402

import build_workbook as B  # noqa: E402

RECALC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]

# name: (sheet, print area, columns to hide for this view, target width in px)
SHOTS = {
    "start": (B.S_START, "A1:G58", [], 2000),
    "settings": (B.S_SET, "A1:I43", [], 2600),
    "rooms": (B.S_ROOMS, "A1:F31", [], 2200),
    "hours": (B.S_HOURS, "A1:AC40", [], 3400),
    "hours_left": (B.S_HOURS, "A1:O40", [], 2800),
    "expenses": (B.S_EXP, "A1:M34", [], 3200),
    "meals": (B.S_MEALS, "A1:S36", [], 3000),
    "mileage": (B.S_MILES, "A1:H30", [], 2200),
    "summary1": (B.S_SUM, "A1:H47", [], 2200),
    "summary2": (B.S_SUM, "A48:H96", [], 2200),
    "statement": (B.S_STMT, "A1:G40", [], 2200),
    "preparer": (B.S_PREP, "A1:G58", [], 2200),
}


def shoot(name, out: Path, edit=None, area=None, as_name=None):
    sheet, area0, hide, width = SHOTS[name]
    area = area or area0
    B.SM.clear()
    b = B.Builder(sample=True)
    wb = b.build()
    if edit:
        edit(wb)
    for ws in wb.worksheets:
        if ws.title == sheet:
            ws.print_area = area
            ws.print_title_rows = None
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 1
            ws.page_setup.orientation = "landscape"
            for col in hide:
                ws.column_dimensions[col].hidden = True
        else:
            ws.print_area = "ZZ900:ZZ900"
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "s.xlsx"
    wb.save(p)
    subprocess.run([sys.executable, RECALC, str(p), "300"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(p)], capture_output=True)
    pdf = tmp / "s.pdf"
    # page 1 is the only page with content; find it by size of text to be safe
    n = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    best, best_len = 1, -1
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True, text=True).stdout
        if len(t.strip()) > best_len:
            best, best_len = i, len(t.strip())
    # render at a resolution that gives roughly the target width
    probe = tmp / "probe"
    subprocess.run(["pdftoppm", "-f", str(best), "-l", str(best), "-r", "100", "-png", "-singlefile", str(pdf), str(probe)], capture_output=True)
    subprocess.run(["convert", f"{probe}.png", "-trim", "+repage", f"{probe}_t.png"])
    w100 = Image.open(f"{probe}_t.png").width
    dpi = max(100, int(100 * width / w100))
    stem = tmp / "hi"
    subprocess.run(["pdftoppm", "-f", str(best), "-l", str(best), "-r", str(dpi), "-png", "-singlefile", str(pdf), str(stem)], capture_output=True)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{as_name or name}.png"
    subprocess.run(["convert", f"{stem}.png", "-trim", "+repage", "-bordercolor", "#FAF7F2", "-border", "12", str(dest)])
    shutil.rmtree(tmp, ignore_errors=True)
    return dest


if __name__ == "__main__":
    brand.ensure_fonts()
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "dist" / "screens"
    names = sys.argv[2:] or list(SHOTS)
    for n in names:
        d = shoot(n, out)
        im = Image.open(d)
        print(n, im.size)
