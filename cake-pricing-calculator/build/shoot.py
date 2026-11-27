"""Real screenshots of the SAMPLE cake pricing workbook (LibreOffice headless -> PDF -> PNG), for the listing images and the guide.

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

import cake_engine as B  # noqa: E402
import cake_config as CFG  # noqa: E402

RECALC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]

# name: (sheet, print area, columns to hide for this view, target width in px)
SHOTS = {
    "start": (B.S_START, "A1:G62", [], 2000, "portrait"),
    "settings1": (B.S_SET, "A1:L48", [], 2400, "landscape"),
    "pans": (B.S_SET, "A{pan_h}:L{pan_e}", [], 2400, "landscape"),
    "ingredients": (B.S_ING, "A1:N34", [], 3000, "landscape"),
    "recipes_index": (B.S_REC, "A1:J20", [], 2600, "landscape"),
    "recipe_block": (B.S_REC, "A{blk}:J{blk_e}", [], 2600, "landscape"),
    "cake1": (B.S_CAKE, "A1:P{s1_end}", [], 3000, "landscape"),
    "cake1_top": (B.S_CAKE, "A1:P{s1_tiers}", [], 3000, "landscape"),
    "cake1_price": (B.S_CAKE, "A{s1_pk}:P{s1_end}", [], 3000, "landscape"),
    "cake2": (B.S_CAKE, "A{s2}:P{s2_end}", [], 3000, "landscape"),
    "batch": (B.S_BATCH, "A1:H{batch_last}", [], 2600, "landscape"),
    "customer": (B.S_CQ, "A1:H{cq_last1}", [], 1700, "portrait"),
    "orders": (B.S_ORD, "A1:R24", [], 3400, "landscape"),
    "orders_up": (B.S_ORD, "V5:AB20", [], 2200, "landscape"),
    "dash_top": (B.S_DASH, "A1:N{types_1}", [], 2600, "landscape"),
    "dash_hero": (B.S_DASH, "A1:N{months_1}", [], 2600, "landscape"),
    "dash_lower": (B.S_DASH, "A{types}:N{end}", [], 2600, "landscape"),
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
    e = B.CakeEngine(CFG, sample=True)
    wb = e.build()
    rows = {k: v for k, v in e.rows.items() if isinstance(v, int)}
    rows.update(e.rows["dash"])
    p1, p2 = e.rows["pans"]
    rows["pan_h"], rows["pan_e"] = p1 - 3, p2 - 12
    rows["blk"], rows["blk_e"] = B.BLK_FIRST, B.BLK_FIRST + B.REC_BLOCK - 1
    a1, a2 = e.A[0], e.A[1]
    rows["s1_end"] = B.SLOT_FIRST + B.SLOT_SIZE - 4
    rows["s1_tiers"] = a1["tier_total"]
    rows["s1_pk"] = a1["pk"]
    rows["s2"], rows["s2_end"] = B.SLOT_FIRST + B.SLOT_SIZE, B.SLOT_FIRST + 2 * B.SLOT_SIZE - 4
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
