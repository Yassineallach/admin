"""Brass Ledger finishing kit shared by the newer single-file products (Whatnot tracker, Home Daycare workbook).

Gives them the same look as the earlier products:
  * icon sidebar on every tab: Excel shapes (gradient bar, clickable icons, current tab highlighted), with a dark
    column of text links underneath. Google Sheets drops the shapes and shows the text links, so ONE file works in both.
  * chart styling (no borders, light gridlines, small grey axis text), as on the earlier dashboards
  * solid data bars
  * finish(path): solid data bars + shape layers written into the saved .xlsx
"""
from __future__ import annotations

import io

from openpyxl.chart.layout import Layout, ManualLayout  # noqa: F401
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.text import RichText
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.hyperlink import Hyperlink
from PIL import Image, ImageDraw

import icons
import sidebar
from common import solidify_databars
from drawing_inject import Layer, col_px_list, row_px_list

GREEN, PAPER, INK2 = "1F3D36", "FAF7F2", "444444"
SIDE_W = 7.65                     # column A width: 54 px, the width of the drawn bar


# ---------------------------------------------------------------- extra icons (same drawing style as icons.py)
def _house(c="FFFFFF", size=64):
    im = icons._new(); d = ImageDraw.Draw(im); col = icons._rgb(c)
    d.polygon([(128, 22), (238, 116), (18, 116)], fill=col)
    d.rounded_rectangle((46, 104, 210, 232), 10, fill=col)
    d.rounded_rectangle((106, 156, 150, 232), 8, fill=(0, 0, 0, 0))
    return icons._out(im, size)


def _meal(c="FFFFFF", size=64):
    im = icons._new(); d = ImageDraw.Draw(im); col = icons._rgb(c)
    d.ellipse((58, 48, 218, 208), outline=col, width=20)
    d.ellipse((98, 88, 178, 168), fill=col)
    d.rounded_rectangle((18, 40, 34, 120), 6, fill=col)
    d.rounded_rectangle((22, 110, 38, 230), 7, fill=col)
    d.rounded_rectangle((226, 40, 244, 230), 8, fill=col)
    return icons._out(im, size)


def _car(c="FFFFFF", size=64):
    im = icons._new(); d = ImageDraw.Draw(im); col = icons._rgb(c)
    d.polygon([(64, 70), (192, 70), (226, 128), (30, 128)], fill=col)
    d.rounded_rectangle((16, 118, 240, 190), 22, fill=col)
    d.polygon([(84, 86), (124, 86), (124, 120), (66, 120)], fill=(0, 0, 0, 0))
    d.polygon([(134, 86), (176, 86), (196, 120), (134, 120)], fill=(0, 0, 0, 0))
    for x in (52, 164):
        d.ellipse((x, 166, x + 46, 212), fill=col)
        d.ellipse((x + 12, 178, x + 34, 200), fill=(0, 0, 0, 0))
    return icons._out(im, size)


def _box(c="FFFFFF", size=64):
    im = icons._new(); d = ImageDraw.Draw(im); col = icons._rgb(c)
    d.polygon([(128, 28), (232, 78), (128, 128), (24, 78)], fill=col)
    d.polygon([(24, 92), (120, 140), (120, 236), (24, 188)], fill=col)
    d.polygon([(136, 140), (232, 92), (232, 188), (136, 236)], fill=col)
    return icons._out(im, size)


def _live(c="FFFFFF", size=64):
    im = icons._new(); d = ImageDraw.Draw(im); col = icons._rgb(c)
    d.rounded_rectangle((20, 60, 180, 196), 26, fill=col)
    d.polygon([(186, 104), (240, 70), (240, 186), (186, 152)], fill=col)
    d.ellipse((50, 90, 90, 130), fill=(0, 0, 0, 0))
    return icons._out(im, size)


def _calc(c="FFFFFF", size=64):
    im = icons._new(); d = ImageDraw.Draw(im); col = icons._rgb(c)
    d.rounded_rectangle((44, 16, 212, 240), 22, fill=col)
    d.rounded_rectangle((70, 42, 186, 92), 8, fill=(0, 0, 0, 0))
    for r in range(3):
        for k in range(3):
            x, y = 70 + k * 42, 112 + r * 42
            d.rounded_rectangle((x, y, x + 30, y + 30), 6, fill=(0, 0, 0, 0))
    return icons._out(im, size)


def _pin(c="FFFFFF", size=64):
    im = icons._new(); d = ImageDraw.Draw(im); col = icons._rgb(c)
    d.ellipse((52, 16, 204, 168), fill=col)
    d.polygon([(66, 124), (190, 124), (128, 242)], fill=col)
    d.ellipse((98, 62, 158, 122), fill=(0, 0, 0, 0))
    return icons._out(im, size)


icons.ICONS.update({"house": _house, "meal": _meal, "car": _car, "box": _box, "live": _live, "calc": _calc, "pin": _pin})


# ---------------------------------------------------------------- sidebar
def sidebar_cells(ws, nav, current, last_row):
    """Dark sidebar column with short text links (what Google Sheets shows; Excel draws the icon bar on top)."""
    ws.column_dimensions["A"].width = SIDE_W
    green = PatternFill("solid", start_color=GREEN, end_color=GREEN)
    for r in range(1, last_row + 1):
        ws.cell(row=r, column=1).fill = green
    row_px = [round((ws.row_dimensions[r].height or 15) * 96 / 72) for r in range(1, last_row + 2)]
    tops, acc = [], 0
    for h in row_px:
        tops.append(acc)
        acc += h
    used = set()
    for i, (tab, _icon, short) in enumerate(nav):
        target = sidebar.icon_centre(i) - 8
        r = next((k + 1 for k, t in enumerate(tops) if t >= target and row_px[k] >= 14 and (k + 1) not in used), None)
        if r is None or r > last_row:
            continue
        used.add(r)
        cell = ws.cell(row=r, column=1)
        cell.value = short
        if tab != current:
            cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"'{tab}'!A1")
        cell.font = Font(name="Inter", size=7, bold=True, color="D29A3A" if tab == current else "FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", shrink_to_fit=True)


def sidebar_layer(ws, nav, current, last_row):
    """Excel shape layer for one tab: gradient bar + icons. Returns the Layer to inject after saving."""
    if not ws._charts and not ws._images:                   # injection needs a drawing part on the sheet
        from openpyxl.drawing.image import Image as XLImage
        buf = io.BytesIO()
        Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(buf, "PNG")
        img = XLImage(io.BytesIO(buf.getvalue()))
        img.width = img.height = 1
        ws.add_image(img, "B1")
    lay = Layer(col_px_list(ws, 2), row_px_list(ws, last_row + 1), font="Inter")
    sidebar.draw(lay, current, lay.y(last_row + 1), nav=nav)
    return lay


def fix_indents(wb):
    """An indent only shows when the cell has an explicit horizontal alignment (LibreOffice and Google Sheets ignore it
    otherwise), so text that touched the next column still touched it. Make indented text cells left-aligned."""
    from copy import copy
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                a = c.alignment
                if a is not None and a.indent and a.horizontal in (None, "general") and isinstance(c.value, str):
                    n = copy(a)
                    n.horizontal = "left"
                    c.alignment = n


def add_sidebars(wb, nav, last_rows: dict, default_last=80, skip=()):
    """Sidebar on every tab (except `skip`, e.g. a customer-facing page). Freezes column A so the bar stays visible when
    scrolling sideways. Returns {tab: Layer}."""
    fix_indents(wb)
    layers = {}
    for ws in wb.worksheets:
        if ws.title in skip:
            continue
        last = min(max(last_rows.get(ws.title, default_last), 60), 140)
        sidebar_cells(ws, nav, ws.title, last)
        fp = ws.freeze_panes
        if fp is None:
            ws.freeze_panes = "B1"
        elif fp.startswith("A"):
            ws.freeze_panes = "B" + fp[1:]
        layers[ws.title] = sidebar_layer(ws, nav, ws.title, last)
    return layers


def finish(path, layers):
    """After wb.save(path): solid data bars, then the sidebar shapes."""
    solidify_databars(path)
    for title, lay in layers.items():
        lay.inject(path, title)


# ---------------------------------------------------------------- charts and data bars
def _rich(sz=800, color=INK2, bold=False):
    cp = CharacterProperties(sz=sz, b=bold, solidFill=color)
    return RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=cp), endParaRPr=cp)])


def clean_chart(ch, legend=True, axes=True, legend_pos="t"):
    """Same chart style as the earlier dashboards: no frame, light gridlines, small grey axis text."""
    ch.title = None
    ch.roundedCorners = False
    ch.graphical_properties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
    ch.plot_area.graphicalProperties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
    if legend:
        ch.legend.position = legend_pos
        ch.legend.overlay = False
        ch.legend.txPr = _rich(800, INK2)
    else:
        ch.legend = None
    if axes:
        from openpyxl.chart.axis import ChartLines
        for ax in (ch.x_axis, ch.y_axis):
            ax.delete = False
            ax.majorTickMark = "none"
            ax.minorTickMark = "none"
            ax.txPr = _rich(750, INK2)
            ax.spPr = GraphicalProperties(ln=LineProperties(noFill=True))
        ch.x_axis.tickLblPos = "low"                         # labels never under a (negative) bar
        ch.y_axis.numFmt = "#,##0"
        ch.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill="EFEAE0", w=6350)))
        ch.x_axis.majorGridlines = None


def databar(ws, rng, color, max_value=None):
    """Solid data bar from 0 to the column's max (or a fixed max, e.g. 1 for percentages)."""
    end = ("num", max_value) if max_value is not None else ("max", None)
    ws.conditional_formatting.add(rng, DataBarRule(start_type="num", start_value=0, end_type=end[0], end_value=end[1],
                                                   color=color, showValue=True, minLength=0, maxLength=100))
