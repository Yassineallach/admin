"""Shared design system + openpyxl helpers for every spreadsheet product in the bundle."""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl.formatting.rule import FormulaRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

TOKENS = json.loads((Path(__file__).resolve().parent.parent / "design-system" / "design-tokens.json").read_text())
_c = TOKENS["color"]


def _h(x: str) -> str:
    return x.lstrip("#").upper()


NAVY = _h(_c["primary"]["deep_navy"])
MIDNIGHT = _h(_c["primary"]["midnight_blue"])
BLUE = _h(_c["primary"]["professional_blue"])
SOFT_BLUE = _h(_c["primary"]["soft_blue"])
TEAL = _h(_c["accent"]["teal"])
SOFT_TEAL = _h(_c["accent"]["soft_teal"])
LAVENDER = _h(_c["accent"]["lavender"])
SOFT_LAV = _h(_c["accent"]["soft_lavender"])
BG = _h(_c["neutral"]["background"])
WHITE = "FFFFFF"
LIGHT_GRAY = _h(_c["neutral"]["light_gray"])
MED_GRAY = _h(_c["neutral"]["medium_gray"])
DARK = _h(_c["neutral"]["dark_text"])
SECONDARY = _h(_c["neutral"]["secondary_text"])
BORDER = _h(_c["neutral"]["border"])
SUCCESS = _h(_c["status"]["success"])
SUCCESS_BG = _h(_c["status"]["success_bg"])
WARNING = _h(_c["status"]["warning"])
WARNING_BG = _h(_c["status"]["warning_bg"])
DANGER = _h(_c["status"]["danger"])
DANGER_BG = _h(_c["status"]["danger_bg"])
INFO = _h(_c["status"]["info"])
INFO_BG = _h(_c["status"]["info_bg"])

FMT_DATE = "mmm d, yyyy"
FMT_SDATE = "mmm d"
FMT_CUR = "#,##0.00"
FMT_CUR0 = "#,##0"
FMT_PCT = "0%"
FMT_HRS = "0.0"
FMT_TIME = "h:mm AM/PM"


class Theme:
    """Edition-aware style factory (font differs between Excel and Google Sheets editions)."""

    def __init__(self, edition: str):
        self.edition = edition
        self.font_name = "Aptos" if edition == "excel" else "Arial"

    def font(self, size=10, bold=False, color=DARK, italic=False, underline=None):
        return Font(name=self.font_name, size=size, bold=bold, color=color, italic=italic, underline=underline)


def fill(color: str) -> PatternFill:
    return PatternFill("solid", start_color=color, end_color=color)


THIN = Side(style="thin", color=BORDER)
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BOTTOM = Border(bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=False, indent=1)
LEFT_WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True, indent=1)
RIGHT = Alignment(horizontal="right", vertical="center", indent=1)

FILL_INPUT = fill(SOFT_BLUE)
FILL_CALC = fill(LIGHT_GRAY)
FILL_POS = fill(SOFT_TEAL)
FILL_NEG = fill(DANGER_BG)
FILL_OPT = fill(SOFT_LAV)
FILL_WHITE = fill(WHITE)
FILL_BG = fill(BG)
FILL_NAVY = fill(NAVY)
FILL_MID = fill(MIDNIGHT)


def col(c) -> str:
    return c if isinstance(c, str) else get_column_letter(c)


def quote(sheet: str) -> str:
    return f"'{sheet}'"


def ref(sheet: str, rng: str) -> str:
    return f"{quote(sheet)}!{rng}"


def setup_sheet(ws, widths: dict, tab_color: str | None = None, zoom=100, bg=True, max_row=120, max_col=30):
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = zoom
    if tab_color:
        ws.sheet_properties.tabColor = tab_color
    ws.column_dimensions["A"].width = 2.5
    for k, v in widths.items():
        ws.column_dimensions[col(k)].width = v


def _cells(ws, rng: str):
    if ":" not in rng:
        return [ws[rng]]
    return [c for row in ws[rng] for c in row]


def paint(ws, rng: str, f=None, font=None, border=None, align=None, numfmt=None):
    for c in _cells(ws, rng):
        if True:
            if f is not None:
                c.fill = f
            if font is not None:
                c.font = font
            if border is not None:
                c.border = border
            if align is not None:
                c.alignment = align
            if numfmt is not None:
                c.number_format = numfmt


def title_bar(ws, T: Theme, title: str, subtitle: str, last_col: int, home_link: str | None = "All-in-One Dashboard",
              demo: bool = False):
    """Row 2 navy bar with title; row 3 subtitle + home link."""
    lc = get_column_letter(last_col)
    ws.row_dimensions[1].height = 8
    ws.row_dimensions[2].height = 38
    ws.row_dimensions[3].height = 20
    paint(ws, f"B2:{lc}2", f=FILL_NAVY)
    ws["B2"] = title
    ws["B2"].font = T.font(20, True, WHITE)
    ws["B2"].alignment = Alignment(vertical="center", indent=1)
    ws["B3"] = subtitle
    ws["B3"].font = T.font(10, False, SECONDARY, italic=True)
    ws["B3"].alignment = Alignment(vertical="center", indent=1)
    if home_link:
        c = ws.cell(row=2, column=last_col)
        c.value = f'=HYPERLINK("#{quote(home_link)}!A1","⌂ Dashboard")'
        c.font = T.font(10, True, WHITE, underline="single")
        c.alignment = Alignment(horizontal="right", vertical="center", indent=1)
    if demo:
        c = ws.cell(row=3, column=last_col)
        c.value = "DEMO DATA"
        c.font = T.font(9, True, WARNING)
        c.fill = fill(WARNING_BG)
        c.alignment = CENTER


def section(ws, T: Theme, r: int, c1: int, c2: int, text: str, color=MIDNIGHT, height=22, size=11):
    rng = f"{get_column_letter(c1)}{r}:{get_column_letter(c2)}{r}"
    paint(ws, rng, f=fill(color))
    cell = ws.cell(row=r, column=c1, value=text)
    cell.font = T.font(size, True, WHITE)
    cell.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[r].height = height


def header_row(ws, T: Theme, r: int, c1: int, headers: list[str], color=NAVY, height=30):
    for i, h in enumerate(headers):
        cell = ws.cell(row=r, column=c1 + i, value=h)
        cell.fill = fill(color)
        cell.font = T.font(10, True, WHITE)
        cell.alignment = CENTER
        cell.border = BOX
    ws.row_dimensions[r].height = height


def legend(ws, T: Theme, r: int, c: int, compact=False):
    """Six-entry cell-convention legend laid out horizontally from (r, c), each entry two cells wide."""
    items = [
        (FILL_INPUT, "Input"), (FILL_WHITE, "Info"), (FILL_CALC, "Calculated"),
        (FILL_POS, "Positive"), (FILL_NEG, "Warning"), (FILL_OPT, "Optional"),
    ]
    lab = ws.cell(row=r, column=c, value="LEGEND")
    lab.font = T.font(8, True, SECONDARY)
    for i, (f, t) in enumerate(items):
        sw = ws.cell(row=r, column=c + 1 + i * 2)
        sw.fill = f
        sw.border = BOX
        tx = ws.cell(row=r, column=c + 2 + i * 2, value=t)
        tx.font = T.font(8, False, SECONDARY)


def add_list_dv(ws, rng: str, source: str, prompt: str | None = None, allow_blank=True, strict=True):
    dv = DataValidation(type="list", formula1=source, allow_blank=allow_blank, showErrorMessage=strict)
    dv.error = "Please choose a value from the dropdown list (edit lists on the Setup tab)."
    dv.errorTitle = "Invalid entry"
    if prompt:
        dv.prompt = prompt
        dv.showInputMessage = True
    ws.add_data_validation(dv)
    dv.add(rng)
    return dv


def add_dv(ws, rng: str, type_: str, op: str | None = None, f1=None, f2=None, error=None):
    dv = DataValidation(type=type_, operator=op, formula1=f1, formula2=f2, allow_blank=True, showErrorMessage=True)
    dv.error = error or "Invalid value."
    ws.add_data_validation(dv)
    dv.add(rng)
    return dv


def cf_formula(ws, rng: str, formula: str, fill_color=None, font_color=None, bold=None, stop=False, T: Theme | None = None):
    kw = {}
    if fill_color:
        kw["fill"] = fill(fill_color)
    if font_color or bold:
        kw["font"] = Font(color=font_color, bold=bold)
    ws.conditional_formatting.add(rng, FormulaRule(formula=[formula], stopIfTrue=stop, **kw))


def cf_databar(ws, rng: str, color=BLUE):
    ws.conditional_formatting.add(
        rng, DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color=color, showValue=True)
    )


def style_input(ws, rng, T: Theme, numfmt=None, align=None):
    paint(ws, rng, f=FILL_INPUT, font=T.font(10), border=BOX, numfmt=numfmt, align=align or LEFT)


def style_calc(ws, rng, T: Theme, numfmt=None, align=None, color=DARK):
    paint(ws, rng, f=FILL_CALC, font=T.font(10, color=color), border=BOX, numfmt=numfmt, align=align or LEFT)


def note(ws, T: Theme, cellref: str, text: str, size=9, color=SECONDARY, italic=True):
    ws[cellref] = text
    ws[cellref].font = T.font(size, False, color, italic=italic)
    ws[cellref].alignment = Alignment(vertical="center", wrap_text=False)
