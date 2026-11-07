"""Shared icon sidebar for every tab (dashboard included).

Excel edition: a dark-teal gradient bar (shape) with one clickable icon per tab, the current tab highlighted.
Google Sheets edition (no shapes): the sidebar column is filled dark teal and carries short text links.
Icon centres sit at the same pixel positions on every tab, so the bar looks identical everywhere.
"""
from __future__ import annotations

from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter as L

import icons
from common import NAVY, WHITE, fill

NAV = [("All-in-One Dashboard", "bar_chart", "Home"), ("Setup", "gear", "Setup"), ("Monthly Calendar", "calendar", "Month"),
       ("Weekly Calendar", "week", "Week"), ("Project Overview", "table", "Projects"), ("Project Manager", "people", "Manager"),
       ("Project Budget", "money", "Budget"), ("Variable Tasks", "clipboard", "Tasks"), ("Recurring Tasks", "repeat", "Repeat"),
       ("Task Schedule", "clock", "Schedule"), ("Task Filter", "filter", "Filter"), ("Decision Matrix", "scale", "Decide"),
       ("Kanban Board", "kanban", "Kanban"), ("Gantt Chart", "gantt", "Gantt"), ("Instructions", "question", "Help")]

BAR_W = 54          # px width of the drawn bar
ICON_Y0, ICON_STEP = 62, 66


def icon_centre(i):
    return ICON_Y0 + i * ICON_STEP


def cells(ws, T, quote, current, last_row, c1=1, c2=1, row_px=None):
    """Google Sheets fallback: dark column + short text links placed at the icon positions."""
    for r in range(1, last_row + 1):
        for c in range(c1, c2 + 1):
            ws.cell(row=r, column=c).fill = fill(NAVY)
    row_px = row_px or [round((ws.row_dimensions[r].height or 15) * 96 / 72) for r in range(1, last_row + 2)]
    tops, acc = [], 0
    for h in row_px:
        tops.append(acc)
        acc += h
    used = set()
    for i, (tab, _icon, short) in enumerate(NAV):
        target = icon_centre(i) - 8
        r = next((k + 1 for k, t in enumerate(tops) if t >= target and row_px[k] >= 14 and (k + 1) not in used), None)
        if r is None or r > last_row:
            continue
        used.add(r)
        if c2 > c1:
            ws.merge_cells(f"{L(c1)}{r}:{L(c2)}{r}")
        cell = ws.cell(row=r, column=c1)
        cell.value = f'=HYPERLINK("#{quote(tab)}!A1","{short}")'
        cell.font = T.font(8, True, "A9D8D1" if tab == current else WHITE)
        cell.alignment = Alignment(horizontal="center", vertical="center")


def draw(layer, current, height_px):
    """Excel: gradient bar + icons with hyperlinks/tooltips; the current tab's icon sits in a mint circle."""
    layer.shape(0, 0, BAR_W, height_px, radius=0.2, fill=None, grad=([(0, "0F6E68"), (100, "0B4F4C")], 90), name="Sidebar")
    for i, (tab, icon, _short) in enumerate(NAV):
        cy = icon_centre(i)
        if tab == current:
            layer.shape(6, cy - 21, 48, cy + 21, geom="ellipse", fill="E1F3F0", name="Active")
            png = icons.ICONS[icon](c="0F6E68", size=64)
        else:
            png = icons.ICONS[icon](c="FFFFFF", size=64)
        layer.picture(13, cy - 14, 41, cy + 14, png, link_sheet=None if tab == current else tab, tooltip=tab)
