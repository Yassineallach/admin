"""Real screenshots of the SAMPLE lawn care workbook (LibreOffice headless -> PDF -> PNG), for the listing images and the guide.

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

import engine as B  # noqa: E402
import lawn_config as CFG  # noqa: E402

RECALC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]

# name: (sheet, print area, columns to hide for this view, target width in px)
SHOTS = {
    # areas use the rows recorded by the engine (Engine.rows)
    "start": (B.S_START, "A1:G48", [], 2000, "portrait"),
    "settings1": (B.S_SET, "A1:I42", [], 2400, "landscape"),
    "settings2": (B.S_SET, "A42:I{cost_hr_end}", [], 2400, "landscape"),
    "settings3": (B.S_SET, "A{cost_hr_end}:I{set_last}", [], 2400, "landscape"),
    "quote": (B.S_QQ, "A1:J{save}", [], 3000, "landscape"),
    "quote_top": (B.S_QQ, "A1:J41", [], 3000, "landscape"),
    "customer": (B.S_CQ, "A1:H{cq_last1}", [], 1700, "portrait"),
    "log": (B.S_LOG, "A1:N20", [], 3000, "landscape"),
    "route": (B.S_ROUTE, "A1:Y24", [], 3400, "landscape"),
    "route_left": (B.S_ROUTE, "A1:K24", [], 2600, "landscape"),
    "route_summary": (B.S_ROUTE, "O4:Y20", [], 2400, "landscape"),
    "season": (B.S_SEASON, "A1:J22", [], 2400, "landscape"),
    "dash_top": (B.S_DASH, "A1:N{quotes_1}", [], 2600, "landscape"),
    "dash_hero": (B.S_DASH, "A1:N{months_1}", [], 2600, "landscape"),
    "dash_months": (B.S_DASH, "A{months}:N{quotes_1}", [], 2600, "landscape"),
    "dash_lower": (B.S_DASH, "A{quotes}:N{end}", [], 2600, "landscape"),
}


def crop_tail(path):
    """Cut the empty page below the content: the sidebar bar runs past the print area (as on the earlier products)."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    x0 = int(w * 0.06)
    last = h - 1
    while last > 0 and all(min(px[x, last]) > 240 for x in range(x0, w, 7)):
        last -= 1
    first = 0
    while first < last and all(min(px[x, first]) > 240 for x in range(x0, w, 7)):
        first += 1
    im.crop((0, max(0, first - 14), w, min(h, last + 14))).save(path)


def shoot(name, out: Path, edit=None, area=None, as_name=None):
    sheet, area0, hide, width, orient = SHOTS[name]
    area = area or area0
    e = B.Engine(CFG, sample=True)
    wb = e.build()
    rows = {k: v for k, v in e.rows.items() if isinstance(v, int)}
    rows.update(e.rows["dash"])
    rows["cost_hr_end"] = rows["cost_hr"] + 7
    rows["cq_last1"] = rows["cq_last"] + 1
    rows.update({k + "_1": v - 1 for k, v in list(rows.items())})
    area = area.format(**rows)
    layers = e.add_sidebars()
    if edit:
        edit(wb)
    for ws in wb.worksheets:
        if ws.title == sheet:
            ws.print_area = area
            ws.print_title_rows = None
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 1
            ws.page_setup.orientation = orient
            for col in hide:
                ws.column_dimensions[col].hidden = True
        else:
            ws.print_area = "ZZ900:ZZ900"
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "s.xlsx"
    wb.save(p)
    B.BP.finish(p, layers)
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
    subprocess.run(["convert", f"{stem}.png", "-trim", "+repage", str(dest)])
    crop_tail(dest)
    subprocess.run(["convert", str(dest), "-bordercolor", "#FAF7F2", "-border", "12", str(dest)])
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
