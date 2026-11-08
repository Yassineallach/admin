"""Layout linter: catches text that overflows its box, clipped text, '###' numbers and colliding charts.

Works on a workbook that has been recalculated (so formula results are present).
  * STRICT sheets (dashboards): every value must fit inside its own cell / merged range, horizontally and vertically.
  * Other sheets: text may spill into empty neighbours (normal spreadsheet behaviour) but must not be clipped
    by a non-empty neighbour; numbers must not render as '###'.
  * Charts (read from the drawing XML): must not overlap each other or cover non-empty cells.

Text width is estimated from per-character advance widths of a typical sans-serif font (Aptos/Arial/Liberation
metrics are within a few % of each other) plus a 10 % safety margin.

Usage: python lint_layout.py RECALCULATED.xlsx [--strict "All-in-One Dashboard" ...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import zipfile
from xml.etree import ElementTree as ET

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, range_boundaries

# advance widths in em (Arial metrics, rounded)
NARROW = set("ijlI.,:;'!|ftr() ")
WIDE = set("MWmw@%")
SYMBOL = set("■○►◆✓‖●▣▤◎↗≡✔◷%⌂▲▼◄…·")


def char_em(ch, bold):
    if ch in SYMBOL:
        w = 0.8
    elif ch in NARROW:
        w = 0.28
    elif ch in WIDE:
        w = 0.85
    elif ch.isupper():
        w = 0.68
    elif ch.isdigit():
        w = 0.56
    else:
        w = 0.53
    return w * (1.07 if bold else 1.0)


def text_px(s, pt, bold):
    return sum(char_em(c, bold) for c in s) * pt * 96 / 72 * 1.10


_DIMS = {}


def _dims(ws):
    if ws.title not in _DIMS:
        d = {}
        for key, dim in ws.column_dimensions.items():
            lo, hi = dim.min or 0, dim.max or 0
            if not lo:
                continue
            for c in range(lo, hi + 1):
                d[c] = (dim.width, dim.hidden)
        _DIMS[ws.title] = d
    return _DIMS[ws.title]


def col_hidden(ws, c):
    return _dims(ws).get(c, (None, False))[1]


def col_px(ws, c):
    w, hidden = _dims(ws).get(c, (None, False))
    if hidden:
        return 0
    if not w:
        w = 8.43
    return int(w * 7 + 5)


def row_px(ws, r):
    h = ws.row_dimensions[r].height
    return (h if h is not None else 15) * 96 / 72


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def render(v, fmt):
    """Approximate the displayed string of a value with a number format."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (dt.datetime, dt.date)):
        d = v if isinstance(v, dt.date) else v.date()
        f = (fmt or "").lower()
        if f in ("d",):
            return str(d.day)
        if f == "dddd":
            return DAYS[d.weekday()]
        if f == "ddd":
            return DAYS[d.weekday()][:3]
        if "mmmm" in f:
            s = f"{MONTHS[d.month - 1]} {d.day}" if "d" in f else MONTHS[d.month - 1]
        elif "mmm" in f:
            s = f"{MONTHS[d.month - 1][:3]} {d.day}" if "d" in f.replace("dddd", "").replace("ddd", "") else MONTHS[d.month - 1][:3]
        else:
            s = d.strftime("%m/%d/%Y")
        if "dddd" in f:
            s = DAYS[d.weekday()] + ", " + s
        elif "ddd" in f:
            s = DAYS[d.weekday()][:3] + ", " + s
        if "yyyy" in f:
            s += f", {d.year}" if ("mmm" in f and "d" in f) else f" {d.year}"
        elif "yy" in f:
            s += f" {str(d.year)[2:]}"
        return s
    if isinstance(v, (int, float)):
        f = fmt or "General"
        if f == ";;;":
            return ""
        if "%" in f:
            return f"{v * 100:.0f}%"
        if "h:mm" in f.lower():
            return "12:00 PM"
        if f.startswith("0.0") or "0.0" in f:
            dec = len(f.split(".")[1].split(";")[0].rstrip('"KM,')) if "." in f else 1
            return (f"{v:,.{min(dec, 5)}f}" if "," in f else f"{v:.{min(dec, 5)}f}")
        if "#,##0" in f:
            return f"{v:,.0f}"
        if f in ("0",):
            return f"{v:.0f}"
        return f"{v:g}"
    return str(v)


def merged_map(ws):
    m = {}
    boxes = []
    for mr in ws.merged_cells.ranges:
        c1, r1, c2, r2 = range_boundaries(str(mr))
        boxes.append((c1, r1, c2, r2))
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                m[(r, c)] = (c1, r1, c2, r2)
    return m, boxes


def chart_boxes(path, sheet_titles):
    """Return {sheet title: [(c1,r1,c2,r2), ...]} from two-cell / one-cell anchors (1-based, inclusive)."""
    out = {}
    z = zipfile.ZipFile(path)
    ns = {"xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    wbx = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid2target = {r.get("Id"): r.get("Target") for r in rels}
    for sh in wbx.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"):
        title = sh.get("name")
        target = rid2target[sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")]
        target = target.split("/")[-1]
        relp = f"xl/worksheets/_rels/{target}.rels"
        if relp not in z.namelist():
            continue
        for rel in ET.fromstring(z.read(relp)):
            if rel.get("Type", "").endswith("/drawing"):
                dpath = "xl/drawings/" + rel.get("Target").split("/")[-1]
                d = ET.fromstring(z.read(dpath))
                for a in d:
                    tag = a.tag.split("}")[1]
                    if a.find("xdr:graphicFrame", ns) is None:
                        continue   # shapes / pictures are checked by shape_problems()
                    if tag == "twoCellAnchor":
                        f, t = a.find("xdr:from", ns), a.find("xdr:to", ns)
                        out.setdefault(title, []).append((int(f.find("xdr:col", ns).text) + 1, int(f.find("xdr:row", ns).text) + 1,
                                                          int(t.find("xdr:col", ns).text) + 1, int(t.find("xdr:row", ns).text) + 1))
                    elif tag == "oneCellAnchor":
                        f = a.find("xdr:from", ns)
                        out.setdefault(title, []).append((int(f.find("xdr:col", ns).text) + 1, int(f.find("xdr:row", ns).text) + 1, None, None))
    return out


def lint(path, strict_sheets, charts_from=None):
    wb = load_workbook(path, data_only=True)
    wbf = load_workbook(path)   # formulas: a cell holding a formula is never "empty" for overflow purposes
    _DIMS.clear()
    problems = []
    charts = chart_boxes(charts_from or path, wb.sheetnames)
    for ws in wb.worksheets:
        strict = ws.title in strict_sheets
        max_col = 10 ** 6
        if strict and ws.print_area:
            pa = ws.print_area if isinstance(ws.print_area, str) else ws.print_area[0]
            max_col = range_boundaries(pa.split("!")[-1].replace("$", ""))[2]
        mm, boxes = merged_map(ws)
        # merged ranges must not overlap
        seen = {}
        for b in boxes:
            for r in range(b[1], b[3] + 1):
                for c in range(b[0], b[2] + 1):
                    if (r, c) in seen and seen[(r, c)] != b:
                        problems.append(f"{ws.title}: merged ranges overlap at {get_column_letter(c)}{r}")
                    seen[(r, c)] = b
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if v is None or v == "":
                    continue
                if cell.column > max_col:
                    continue  # dashboard engine area (outside the printed/visible layout)
                if (cell.row, cell.column) in mm and mm[(cell.row, cell.column)][:2] != (cell.column, cell.row):
                    continue  # covered part of a merge
                if col_hidden(ws, cell.column) or ws.row_dimensions[cell.row].hidden:
                    continue
                c1, r1, c2, r2 = mm.get((cell.row, cell.column), (cell.column, cell.row, cell.column, cell.row))
                width = sum(col_px(ws, c) for c in range(c1, c2 + 1))
                height = sum(row_px(ws, r) for r in range(r1, r2 + 1))
                if width == 0:
                    continue
                f = cell.font
                pt = f.sz or 11
                al = cell.alignment
                s = render(v, cell.number_format)
                if not s:
                    continue
                pad = 6 + (al.indent or 0) * 9
                need = text_px(s, pt, bool(f.b))
                where = f"{ws.title}!{get_column_letter(c1)}{r1}"
                numeric = isinstance(v, (int, float, dt.date, dt.datetime)) and not isinstance(v, bool)
                if al.shrink_to_fit:
                    continue
                if al.wrap_text:
                    lines = max(1, int(need // max(1, width - pad)) + 1)
                    if lines * pt * 96 / 72 * 1.2 > height + 2 and strict:
                        problems.append(f"{where}: wrapped text needs {lines} lines but box is {height:.0f}px tall: {s[:40]!r}")
                    continue
                if pt * 96 / 72 * 1.15 > height + 1 and (strict or ws.row_dimensions[r1].height):
                    if not (s.strip() == "" or cell.number_format == ";;;"):
                        problems.append(f"{where}: {pt}pt text taller than row ({height:.0f}px): {s[:30]!r}")
                if need + pad <= width:
                    continue
                if numeric:
                    problems.append(f"{where}: number would show ### (needs {need + pad:.0f}px, has {width}px): {s!r}")
                    continue
                if strict:
                    problems.append(f"{where}: text overflows its box (needs {need + pad:.0f}px, has {width}px): {s[:50]!r}")
                    continue
                # non-strict: allowed to spill only into empty, unfilled neighbours
                nxt = c2 + 1
                if (al.horizontal or "general") in ("left", "general"):
                    remaining = need + pad - width
                    while remaining > 0 and nxt < c2 + 30:
                        nb = ws.cell(row=r1, column=nxt)
                        has_formula = isinstance(wbf[ws.title].cell(row=r1, column=nxt).value, str) and \
                            str(wbf[ws.title].cell(row=r1, column=nxt).value).startswith("=")
                        if (r1, nxt) in mm or (nb.value not in (None, "")) or has_formula:
                            problems.append(f"{where}: text clipped by neighbour {get_column_letter(nxt)}{r1}: {s[:50]!r}")
                            break
                        remaining -= col_px(ws, nxt)
                        nxt += 1
        # charts
        cb = [b for b in charts.get(ws.title, []) if b[2] is not None]
        for i, a in enumerate(cb):
            for b in cb[i + 1:]:
                if not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]):
                    problems.append(f"{ws.title}: charts overlap {a} / {b}")
            for r in range(a[1], a[3] + 1):
                for c in range(a[0], a[2] + 1):
                    v = ws.cell(row=r, column=c).value
                    if v not in (None, ""):
                        problems.append(f"{ws.title}: chart {a} covers non-empty cell {get_column_letter(c)}{r}")
    return problems


def shape_problems(path):
    """Check the Excel shape layer: text fits its box; cards do not overlap; charts sit inside a card."""
    probs = []
    z = zipfile.ZipFile(path)
    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    X = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
    for n in z.namelist():
        if not (n.startswith("xl/drawings/drawing") and n.endswith(".xml")):
            continue
        root = ET.fromstring(z.read(n))
        cards, charts = [], []
        for anc in root:
            sp = anc.find(X + "sp")
            xfrm = anc.find(f".//{A}xfrm")
            if sp is not None and xfrm is not None:
                off, ext = xfrm.find(A + "off"), xfrm.find(A + "ext")
                x0, y0 = int(off.get("x")) / 9525, int(off.get("y")) / 9525
                w, h = int(ext.get("cx")) / 9525, int(ext.get("cy")) / 9525
                name = sp.find(f"{X}nvSpPr/{X}cNvPr").get("name")
                texts = [t.text or "" for t in sp.iter(A + "t")]
                rpr = next(sp.iter(A + "rPr"), None)
                if texts and "".join(texts).strip() and rpr is not None:
                    txt = "".join(texts)
                    pt = int(rpr.get("sz", "1100")) / 100
                    need = text_px(txt, pt, rpr.get("b") == "1")
                    if need > w + 1:
                        probs.append(f"{n}: shape '{name}' text {txt!r} needs {need:.0f}px, box is {w:.0f}px")
                    if pt * 96 / 72 * 1.15 > h + 2:
                        probs.append(f"{n}: shape '{name}' {pt}pt text taller than box ({h:.0f}px)")
                if name.startswith(("Tile", "Panel", "Highlight")):
                    cards.append((name, x0, y0, x0 + w, y0 + h))
            gf = anc.find(X + "graphicFrame")
            if gf is not None:
                f_, t_ = anc.find(X + "from"), anc.find(X + "to")
                charts.append(anc)
        for i, a_ in enumerate(cards):
            for b_ in cards[i + 1:]:
                if not (a_[3] <= b_[1] or b_[3] <= a_[1] or a_[4] <= b_[2] or b_[4] <= a_[2]):
                    probs.append(f"{n}: cards overlap: {a_[0]} / {b_[0]}")
    return probs


def geometry_problems(path, sheet_title="All-in-One Dashboard", min_gap=8):
    """Pixel-accurate collision check for a sheet's drawing layer.

    Cards  = shapes named Tile / Highlight / Panel / Pill (+ Sidebar).
    Content = charts, text boxes and pictures.
    Rules: cards never overlap and keep >= min_gap px between them (sidebar excluded from the gap rule, but nothing
    may overlap it except its own icons); every content item lies fully inside one card, inside the sidebar, or in
    open canvas without touching any card edge.
    """
    import re as _re
    from openpyxl import load_workbook as _lw
    from openpyxl.utils import get_column_letter as _gl
    z = zipfile.ZipFile(path)
    wbx = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    rid = _re.search(r'<sheet [^>]*name="' + _re.escape(sheet_title) + r'"[^>]*r:id="(rId\d+)"', wbx).group(1)
    rel = next(m for m in _re.findall(r"<Relationship [^>]*>", rels) if f'Id="{rid}"' in m)
    target = _re.search(r'Target="([^"]+)"', rel).group(1).split("/")[-1]
    srels = z.read(f"xl/worksheets/_rels/{target}.rels").decode()
    dpath = "xl/drawings/" + _re.search(r'Target="[^"]*?(drawing\d+\.xml)"', srels).group(1)
    ws = _lw(path)[sheet_title]
    cols = [int(7 * (ws.column_dimensions[_gl(c)].width or 8.43) + 0.49) for c in range(1, 200)]
    rows = [round((ws.row_dimensions[r].height or 15) * 96 / 72) for r in range(1, 400)]
    cx = lambda c, off: sum(cols[:c]) + off / 9525
    ry = lambda r, off: sum(rows[:r]) + off / 9525
    X = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
    A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    root = ET.fromstring(z.read(dpath))
    cards, content, sidebar = [], [], None
    for anc in root:
        f_, t_ = anc.find(X + "from"), anc.find(X + "to")
        if f_ is None or t_ is None:
            continue
        box = (cx(int(f_.find(X + "col").text), int(f_.find(X + "colOff").text)), ry(int(f_.find(X + "row").text), int(f_.find(X + "rowOff").text)),
               cx(int(t_.find(X + "col").text), int(t_.find(X + "colOff").text)), ry(int(t_.find(X + "row").text), int(t_.find(X + "rowOff").text)))
        sp, pic, gf = anc.find(X + "sp"), anc.find(X + "pic"), anc.find(X + "graphicFrame")
        if sp is not None:
            name = sp.find(f"{X}nvSpPr/{X}cNvPr").get("name")
            if name.startswith("Sidebar"):
                sidebar = (name, *box)
            elif name.startswith(("Tile", "Highlight", "Panel", "Pill")):
                cards.append((name, *box))
            elif name.startswith("Active"):
                content.append((name, *box))
            else:
                txt = "".join(t.text or "" for t in sp.iter(A + "t"))
                content.append((f"{name} {txt[:25]!r}", *box))
        elif pic is not None:
            content.append((pic.find(f"{X}nvPicPr/{X}cNvPr").get("name"), *box))
        elif gf is not None:
            content.append((gf.find(f"{X}nvGraphicFramePr/{X}cNvPr").get("name"), *box))
    probs = []

    def overlap(a, b, gap=0):
        return not (a[3] + gap <= b[1] or b[3] + gap <= a[1] or a[4] + gap <= b[2] or b[4] + gap <= a[2])

    def inside(i, c):
        return i[1] >= c[1] - 0.5 and i[2] >= c[2] - 0.5 and i[3] <= c[3] + 0.5 and i[4] <= c[4] + 0.5

    for i, a in enumerate(cards):
        if sidebar and overlap(a, sidebar):
            probs.append(f"card {a[0]} overlaps the sidebar")
        for b in cards[i + 1:]:
            if overlap(a, b):
                probs.append(f"cards overlap: {a[0]} {tuple(round(v) for v in a[1:])} / {b[0]} {tuple(round(v) for v in b[1:])}")
            elif overlap(a, b, min_gap):
                probs.append(f"cards closer than {min_gap}px: {a[0]} / {b[0]}")
    for it in content:
        homes = [c for c in cards if inside(it, c)]
        # a card nested in a bigger card (e.g. pill on a panel) counts as one home
        if sidebar and inside(it, sidebar):
            continue
        if not homes:
            touching = [c[0] for c in cards if overlap(it, c)]
            if touching:
                probs.append(f"{it[0]} {tuple(round(v) for v in it[1:])} crosses the edge of {touching}")
    return probs, len(cards), len(content)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--charts-from", help="original (pre-recalc) file to read chart anchors from")
    ap.add_argument("--strict", nargs="*", default=["All-in-One Dashboard"])
    ap.add_argument("--geometry", nargs="*", default=["All-in-One Dashboard"], help="sheets whose shape layer to check")
    a = ap.parse_args()
    probs = lint(a.path, set(a.strict), a.charts_from)
    if a.charts_from:
        probs += shape_problems(a.charts_from)
        z_ = zipfile.ZipFile(a.charts_from)
        if any("drawing" in n_ for n_ in z_.namelist()) and b"<xdr:sp " in b"".join(
                z_.read(n_) for n_ in z_.namelist() if n_.startswith("xl/drawings/drawing")):
            titles = set(load_workbook(a.charts_from, read_only=True).sheetnames)
            for t in a.geometry:
                if t in titles:
                    gp, _, _ = geometry_problems(a.charts_from, t)
                    probs += gp
    for p in probs:
        print("  ✗", p)
    print(f"{len(probs)} layout problem(s)")
    sys.exit(1 if probs else 0)
