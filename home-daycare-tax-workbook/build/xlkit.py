"""Brass Ledger spreadsheet styling: title bar, kickers, input/calculated cells, headers, notes, tiles, links, protection."""
from __future__ import annotations

from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.hyperlink import Hyperlink

GREEN, GREEN2, BRASS, PAPER, INK, INK2 = "1F3D36", "2B5148", "D29A3A", "FAF7F2", "222222", "444444"
BORDER, WHITE, POS, NEG = "E6E1D8", "FFFFFF", "2E7D4F", "B3261E"
CALC, BRASS_TINT, POS_TINT, NEG_TINT, MUTED, GREY = "F1ECE2", "F6EBD3", "E4EFE8", "F8E1DE", "C9D3CF", "8A877F"
BODY, TITLE = "Inter", "Georgia"                 # Fraunces is not available in Excel: Georgia for tab titles only

MONEY = '"$"#,##0.00;-"$"#,##0.00'
PCT2 = "0.00%"
HRS = "#,##0.00"
SQFT = "#,##0"
DATE = "mmm d, yyyy"
TIME = "h:mm AM/PM"

thin = Side(style="thin", color=BORDER)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)


def fill(c):
    return PatternFill("solid", start_color=c, end_color=c)


def font(size=10, bold=False, color=INK, name=BODY, italic=False):
    return Font(name=name, size=size, bold=bold, color=color, italic=italic)


def q(sheet):
    return f"'{sheet}'"


class Kit:
    product = ""

    def page(self, ws, widths: dict, last_col: int, last_row: int, tab_label: str, subtitle: str, landscape=True):
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 100
        ws.column_dimensions["A"].width = 2.5
        for col, w in widths.items():
            ws.column_dimensions[col].width = w
        for r in range(1, last_row + 1):
            for c in range(1, last_col + 2):
                x = ws.cell(row=r, column=c)
                x.fill = fill(PAPER)
                x.font = font()
        for r in (1, 2):
            for c in range(1, last_col + 2):
                ws.cell(row=r, column=c).fill = fill(GREEN)
        ws.row_dimensions[1].height = 34
        ws.row_dimensions[2].height = 22
        ws.row_dimensions[3].height = 10
        ws.merge_cells(f"B1:{L(last_col - 2)}1")
        t = ws["B1"]
        t.value = self.product
        t.font = Font(name=TITLE, size=17, bold=True, color=PAPER)
        t.alignment = Alignment(vertical="center")
        ws.merge_cells(f"{L(last_col - 1)}1:{L(last_col)}1")
        b = ws[f"{L(last_col - 1)}1"]
        b.value = "BRASS LEDGER"
        b.font = font(9, True, BRASS)
        b.alignment = Alignment(horizontal="right", vertical="center")
        ws.merge_cells(f"B2:{L(last_col)}2")
        k = ws["B2"]
        k.value = f"{tab_label.upper()}   ·   {subtitle}"
        k.font = font(9, True, MUTED)
        k.alignment = Alignment(vertical="center")
        ws.sheet_properties.tabColor = GREEN
        ws.page_setup.orientation = "landscape" if landscape else "portrait"
        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
        ws.page_margins.left = ws.page_margins.right = 0.4
        ws.page_margins.top = ws.page_margins.bottom = 0.5

    def kicker(self, ws, cell, text, color=BRASS, rule_to=None):
        c = ws[cell]
        c.value = text.upper()
        c.font = font(9, True, color)
        c.alignment = Alignment(vertical="bottom")
        if rule_to:
            r = c.row
            if rule_to > c.column:
                ws.merge_cells(start_row=r, start_column=c.column, end_row=r, end_column=rule_to)
            for col in range(c.column, rule_to + 1):
                ws.cell(row=r, column=col).border = Border(bottom=Side(style="medium", color=BRASS))
        ws.row_dimensions[c.row].height = 20

    def inp(self, c, fmt=None, align=None, value=None):
        c.fill = fill(WHITE)
        c.border = BOX
        c.font = font(10, color=INK)
        c.protection = Protection(locked=False)
        if fmt:
            c.number_format = fmt
        c.alignment = Alignment(horizontal=align, vertical="center") if align else Alignment(vertical="center")
        if value is not None:
            c.value = value

    def calc(self, c, fmt=None, bold=False, align=None, color=INK, value=None):
        c.fill = fill(CALC)
        c.border = BOX
        c.font = font(10, bold, color)
        c.protection = Protection(locked=True)
        if fmt:
            c.number_format = fmt
        c.alignment = Alignment(horizontal=align, vertical="center") if align else Alignment(vertical="center")
        if value is not None:
            c.value = value

    def sysval(self, c, value):
        c.value = value
        c.fill, c.font, c.border = fill(BRASS_TINT), font(9, color=INK2), BOX
        c.alignment = Alignment(vertical="center", wrap_text=False)

    def header(self, c, text, fill_color=GREEN, color=PAPER, align="center"):
        c.value = text
        c.fill = fill(fill_color)
        c.font = font(9, True, color)
        c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
        c.border = Border(left=Side(style="thin", color=fill_color), right=Side(style="thin", color=PAPER))

    def label(self, c, text, bold=True, color=INK, size=10, indent=0, wrap=False):
        c.value = text
        c.font = font(size, bold, color)
        c.alignment = Alignment(vertical="center", indent=indent, wrap_text=wrap)

    def note(self, ws, rng, text, tint=BRASS_TINT, height=None, size=9, color=INK2, bold=False):
        ws.merge_cells(rng)
        c = ws[rng.split(":")[0]]
        c.value = text
        c.font = font(size, bold, color)
        c.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        for row in ws[rng]:
            for x in row:
                x.fill = fill(tint)
        if height:
            ws.row_dimensions[c.row].height = height

    def link(self, c, text, sheet, cell="A1"):
        c.value = text
        c.hyperlink = Hyperlink(ref=c.coordinate, location=f"{q(sheet)}!{cell}")
        c.font = Font(name=BODY, size=10, bold=True, color=GREEN2, underline="single")

    def tile(self, ws, r, c1, c2, label, formula, fmt, size=17):
        for rr in (r, r + 1):
            ws.merge_cells(f"{L(c1)}{rr}:{L(c2)}{rr}")
            for cc in range(c1, c2 + 1):
                x = ws.cell(row=rr, column=cc)
                x.fill = fill(GREEN)
                x.border = Border(left=Side(style="medium", color=PAPER) if cc == c1 else None,
                                  right=Side(style="medium", color=PAPER) if cc == c2 else None)
        lc = ws.cell(row=r, column=c1, value=label)
        lc.font = font(8, True, MUTED)
        lc.alignment = Alignment(vertical="bottom", indent=1, shrink_to_fit=True)
        vc = ws.cell(row=r + 1, column=c1, value=formula)
        vc.font = font(size, True, BRASS)
        vc.alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
        vc.number_format = fmt
        ws.row_dimensions[r].height = 20
        ws.row_dimensions[r + 1].height = 32

    def protect(self, ws):
        p = ws.protection
        p.sheet = True
        for attr in ("formatColumns", "formatRows", "formatCells", "autoFilter", "sort", "selectLockedCells", "selectUnlockedCells"):
            setattr(p, attr, False)
