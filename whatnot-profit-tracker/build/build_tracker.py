"""Brass Ledger — Whatnot Live Show Profit Tracker (Excel 2016+ and Google Sheets).

Builds two workbooks with openpyxl: a blank one for buyers and a SAMPLE one with 12 shows (Aug–Oct 2026).
Every calculated cell is a formula. No macros, no Excel Tables, no dynamic arrays, no TEXT() date formats.

Usage: python build_tracker.py [OUT_DIR]
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList  # noqa: F401
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.hyperlink import Hyperlink

from sample_data import ITEMS, SHOWS

sys.path.insert(0, "/home/user/admin/productivity-bundle/build")
import bl_polish as BP  # noqa: E402
from openpyxl.chart import DoughnutChart  # noqa: E402
from openpyxl.chart.series import DataPoint  # noqa: E402

PRODUCT = "Whatnot Live Show Profit Tracker"
SHORT = "Whatnot Profit Tracker"
OUT_NAME = "BrassLedger_Whatnot_Profit_Tracker"

# ---------------------------------------------------------------- brand
GREEN, GREEN2, BRASS, PAPER, INK, INK2 = "1F3D36", "2B5148", "D29A3A", "FAF7F2", "222222", "444444"
BORDER, WHITE, POS, NEG = "E6E1D8", "FFFFFF", "2E7D4F", "B3261E"
CALC, BRASS_TINT, POS_TINT, NEG_TINT, MUTED = "F1ECE2", "F6EBD3", "E4EFE8", "F8E1DE", "C9D3CF"
BODY, TITLE = "Inter", "Georgia"          # Fraunces is not available in Excel: Georgia for tab titles only

S_START, S_SET, S_LOG, S_ITEM, S_DASH, S_YEAR = "START HERE", "SETTINGS", "SHOW LOG", "ITEM SALES", "DASHBOARD", "YEAR SUMMARY"
ORDER = [S_START, S_SET, S_LOG, S_ITEM, S_DASH, S_YEAR]
NAV = [(S_DASH, "bar_chart", "Home"), (S_START, "question", "Start"), (S_SET, "gear", "Setup"), (S_LOG, "live", "Shows"),
       (S_ITEM, "box", "Items"), (S_YEAR, "calendar", "Year")]

MONEY = '#,##0.00;-#,##0.00'
MONEY0 = '#,##0;-#,##0'
PCT1 = '0.0%'
DATE = 'mmm d, yyyy'
TIME = 'h:mm AM/PM'

LOG_FIRST, LOG_N = 6, 300
LOG_LAST = LOG_FIRST + LOG_N - 1
ITEM_FIRST, ITEM_N = 6, 1000
ITEM_LAST = ITEM_FIRST + ITEM_N - 1
SUM_N = 100                               # shows in the ITEM SALES summary

thin = Side(style="thin", color=BORDER)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)


def fill(c):
    return PatternFill("solid", start_color=c, end_color=c)


def font(size=10, bold=False, color=INK, name=BODY, italic=False):
    return Font(name=name, size=size, bold=bold, color=color, italic=italic)


def q(sheet):
    return f"'{sheet}'"


# SETTINGS cells (absolute references used everywhere; nothing hard-coded elsewhere)
SET = {
    "cur": "$C$6", "comm": "$C$7", "proc": "$C$8", "fixed": "$C$9", "basis": "$C$10",
    "give": "$C$16", "goal": "$C$17",
}
CATS = ("$B$22", "$B$31")
SLOTS = ("$C$22", "$C$25")
FMTS = ("$D$22", "$D$24")
OPT = ("$B$36", "$B$37")                  # commission basis options
MONTHS = ("$C$36", "$C$47")


def sref(key):
    return f"{q(S_SET)}!{SET[key]}"


def srng(pair):
    return f"{q(S_SET)}!{pair[0]}:{pair[1]}"


CUR = sref("cur")


def money_text(expr):
    """Formula fragment: an amount as text with the currency symbol, e.g. $1,234 or -$56 (FIXED is locale-safe)."""
    return f'IF(({expr})<0,"-","")&{CUR}&FIXED(ABS({expr}),0)'


# SHOW LOG columns
C = dict(date="B", title="C", cat="D", slot="E", fmt="F", start="G", end="H", gross="I", orders="J", ship="K",
         cogs="L", gives="M", gover="N", supplies="O", other="P", viewers="Q", notes="R",
         wday="S", hours="T", gcost="U", comm="V", proc="W", fees="X", profit="Y", margin="Z", perhour="AA",
         aov="AB", gpct="AC",
         yr="AE", mo="AF", key="AG", wnum="AH", rank="AI", hprofit="AJ")
INPUT_COLS = ["date", "title", "cat", "slot", "fmt", "start", "end", "gross", "orders", "ship", "cogs", "gives", "gover",
              "supplies", "other", "viewers", "notes"]
CALC_COLS = ["wday", "hours", "gcost", "comm", "proc", "fees", "profit", "margin", "perhour", "aov", "gpct"]
HELPER_COLS = ["yr", "mo", "key", "wnum", "rank", "hprofit"]


def LR(col):
    """Whole data range of a SHOW LOG column, as seen from another sheet."""
    c = C[col]
    return f"{q(S_LOG)}!${c}${LOG_FIRST}:${c}${LOG_LAST}"


# DASHBOARD selector cells
D_MONTH, D_YEAR = "$C$6", "$F$6"
D_MNUM, D_KEY = "$P$6", "$P$7"            # hidden helpers


def style_chart(ch):
    """Keep text clear of the bars: category labels sit outside the plot (below or left of the lowest value, so a
    negative bar never runs over them), light gridlines, and a legend that never overlaps the plot."""
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.x_axis.tickLblPos = "low"
    ch.y_axis.tickLblPos = "nextTo"
    ch.y_axis.numFmt = "#,##0"
    ch.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill=BORDER))
    if ch.legend is not None:
        ch.legend.position = "b"
        ch.legend.overlay = False


def dref(cell):
    return f"{q(S_DASH)}!{cell}"


class Builder:
    def __init__(self, sample: bool):
        self.sample = sample
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in ORDER}

    # ------------------------------------------------------------ shared pieces
    def page(self, ws, widths: dict, last_col: int, last_row: int, tab_label: str, subtitle: str):
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 100
        ws.column_dimensions["A"].width = 2.5
        widths = dict(widths)
        widths[L(last_col)] = max(widths.get(L(last_col), 8.43), 17)    # room for BRASS LEDGER and the home link
        for col, w in widths.items():
            ws.column_dimensions[col].width = w
        for r in range(1, last_row + 1):
            for c in range(1, last_col + 2):
                ws.cell(row=r, column=c).fill = fill(PAPER)
                ws.cell(row=r, column=c).font = font()
        # title bar (as on the earlier products): tab name + product name in paper, BRASS LEDGER in brass on the right,
        # then a line with the sample marker, what the tab is for, and a link home
        lc = L(last_col)
        for r in (1, 2):
            for c in range(1, last_col + 2):
                ws.cell(row=r, column=c).fill = fill(GREEN)
        ws.row_dimensions[1].height = 36
        ws.row_dimensions[2].height = 22
        ws.row_dimensions[3].height = 10
        ws.merge_cells(f"B1:{L(last_col - 1)}1")
        t = ws["B1"]
        t.value = f"{tab_label.upper()}  ·  {PRODUCT}"
        t.font = Font(name=TITLE, size=17, bold=True, color=PAPER)
        t.alignment = Alignment(vertical="center")
        b = ws[f"{lc}1"]
        b.value = "BRASS LEDGER"
        b.font = font(9, True, BRASS)
        b.alignment = Alignment(horizontal="right", vertical="center")
        ws.merge_cells(f"B2:{L(last_col - 1)}2")
        k = ws["B2"]
        k.value = ("●  SAMPLE DATA   ·   " if self.sample else "") + subtitle
        k.font = font(9, True, MUTED)
        k.alignment = Alignment(vertical="center")
        home = ws[f"{lc}2"]
        target, label = (S_START, "Start here  →") if ws.title == S_DASH else (S_DASH, "←  Dashboard")
        home.value = label
        home.hyperlink = Hyperlink(ref=home.coordinate, location=f"{q(target)}!A1")
        home.font = Font(name=BODY, size=9, bold=True, color=BRASS, underline=None)
        home.alignment = Alignment(horizontal="right", vertical="center")
        ws.sheet_properties.tabColor = GREEN
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True

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

    def inp(self, c, fmt=None, align=None):
        c.fill = fill(WHITE)
        c.border = BOX
        c.font = font(10, color=INK)
        c.protection = Protection(locked=False)
        if fmt:
            c.number_format = fmt
        if align:
            c.alignment = Alignment(horizontal=align, vertical="center")
        elif fmt is None:                    # text: small indent so it never touches a number in the next column
            c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        else:
            c.alignment = Alignment(vertical="center")

    def calc(self, c, fmt=None, bold=False, align=None, color=INK):
        c.fill = fill(CALC)
        c.border = BOX
        c.font = font(10, bold, color)
        c.protection = Protection(locked=True)
        if fmt:
            c.number_format = fmt
        if align:
            c.alignment = Alignment(horizontal=align, vertical="center")
        elif fmt is None:                    # text: small indent so it never touches a number in the next column
            c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        else:
            c.alignment = Alignment(vertical="center")

    def header(self, c, text, fill_color=GREEN, color=PAPER, align="center"):
        c.value = text
        c.fill = fill(fill_color)
        c.font = font(9, True, color)
        c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
        c.border = Border(left=Side(style="thin", color=fill_color), right=Side(style="thin", color=PAPER))

    def note(self, ws, rng, text, tint=BRASS_TINT, height=None, size=9, color=INK2, bold=False):
        ws.merge_cells(rng)
        c = ws[rng.split(":")[0]]
        c.value = text
        c.font = font(size, bold, color)
        c.alignment = Alignment(wrap_text=True, vertical="center")
        for row in ws[rng]:
            for x in row:
                x.fill = fill(tint)
        if height:
            ws.row_dimensions[c.row].height = height

    def link(self, c, text, sheet, cell="A1"):
        c.value = text
        c.hyperlink = Hyperlink(ref=c.coordinate, location=f"{q(sheet)}!{cell}")
        c.font = Font(name=BODY, size=10, bold=True, color=GREEN2, underline="single")

    def tile(self, ws, r, c1, c2, label, formula, fmt):
        for rr in (r, r + 1):
            ws.merge_cells(f"{L(c1)}{rr}:{L(c2)}{rr}")
            for cc in range(c1, c2 + 1):
                x = ws.cell(row=rr, column=cc)
                x.fill = fill(GREEN)
                x.border = Border(left=Side(style="medium", color=PAPER) if cc == c1 else None,
                                  right=Side(style="medium", color=PAPER) if cc == c2 else None)
        lc = ws.cell(row=r, column=c1, value=label)
        lc.font = font(8, True, MUTED)
        lc.alignment = Alignment(vertical="bottom", indent=1, wrap_text=False, shrink_to_fit=True)
        vc = ws.cell(row=r + 1, column=c1, value=formula)
        vc.font = font(18, True, BRASS)
        vc.alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
        vc.number_format = fmt
        ws.row_dimensions[r].height = 20
        ws.row_dimensions[r + 1].height = 34

    def protect(self, ws):
        p = ws.protection
        p.sheet = True
        for attr in ("formatColumns", "formatRows", "formatCells", "autoFilter", "sort", "selectLockedCells", "selectUnlockedCells"):
            setattr(p, attr, False)

    # ------------------------------------------------------------ START HERE
    def build_start(self):
        ws = self.ws[S_START]
        self.page(ws, {"B": 4, "C": 30, "D": 30, "E": 30, "F": 22}, 6, 48, "Start here", "Read this first. It takes two minutes.")
        r = 4
        self.note(ws, f"B{r}:F{r}", "See the real profit from every show in two minutes.", tint=PAPER, height=30, size=15, color=GREEN, bold=True)
        ws[f"B{r}"].font = Font(name=TITLE, size=15, bold=True, color=GREEN)
        self.note(ws, f"B{r + 1}:F{r + 1}",
                  "After a show Whatnot shows your sales, not your profit. Log each show on one row: this workbook takes off "
                  "commission, processing fees, the cost of what you sold, giveaways and supplies, then shows which shows, days, "
                  "time slots and categories actually make money.", tint=PAPER, height=48, size=10, color=INK)
        r = 7
        self.kicker(ws, f"B{r}", "Quick start in 3 steps", rule_to=6)
        steps = [("1", "Check your fees", "Open SETTINGS. Check the commission and processing rates against your current Whatnot "
                  "seller fees, and set your default giveaway cost and monthly goal.", S_SET),
                 ("2", "Log a show", "Open SHOW LOG. After each show, fill one row: date, title, time, gross sales, orders, "
                  "what the items cost you, giveaways and supplies. Profit appears in the shaded columns.", S_LOG),
                 ("3", "Read the dashboard", "Open DASHBOARD and pick the month. See your profit, fees, giveaways and which "
                  "time slots, days and categories earn most.", S_DASH)]
        r = 8
        for num, head, body, sheet in steps:
            c = ws[f"B{r}"]
            c.value = num
            c.font = Font(name=TITLE, size=18, bold=True, color=BRASS)
            c.alignment = Alignment(horizontal="center", vertical="top")
            self.link(ws[f"C{r}"], f"{head}  ›", sheet)
            ws[f"C{r}"].alignment = Alignment(vertical="top")
            ws.merge_cells(f"D{r}:F{r}")
            d = ws[f"D{r}"]
            d.value = body
            d.font = font(10, color=INK)
            d.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 46
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Colour key", rule_to=6)
        r += 1
        keys = [("inp", "Type here", "White cell with a border: your numbers, or pick from the dropdown."),
                ("calc", "Calculated", "Shaded cell: a formula. It is locked so you can't overwrite it by accident."),
                ("tile", "Result", "Green block with a brass figure: a headline number."),
                ("neg", "Loss", "Red: the show lost money."),
                ("pos", "Top quarter", "Green: one of your most profitable shows (top 25 %).")]
        for kind, head, body in keys:
            c = ws[f"C{r}"]
            c.value = head
            if kind == "inp":
                self.inp(c)
            elif kind == "calc":
                self.calc(c)
            elif kind == "tile":
                c.fill, c.font = fill(GREEN), font(10, True, BRASS)
            elif kind == "neg":
                c.fill, c.font = fill(NEG_TINT), font(10, True, NEG)
            else:
                c.fill, c.font = fill(POS_TINT), font(10, True, POS)
            c.protection = Protection(locked=True)
            c.alignment = Alignment(indent=1, vertical="center")
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"].value = body
            ws[f"D{r}"].font = font(10, color=INK2)
            ws[f"D{r}"].alignment = Alignment(vertical="center", indent=1)
            ws.row_dimensions[r].height = 22
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Two ways to log", rule_to=6)
        r += 1
        modes = [("Quick mode", "Type each show's totals straight into SHOW LOG. Most sellers only ever need this."),
                 ("Detailed mode", "Track every item on ITEM SALES. Its summary on the right adds up sales and cost for each "
                  "show; copy those two totals into the show's row on SHOW LOG. SHOW LOG never reads ITEM SALES, so "
                  "leaving ITEM SALES empty causes no errors.")]
        for head, body in modes:
            ws[f"C{r}"].value = head
            ws[f"C{r}"].font = font(10, True, GREEN)
            ws[f"C{r}"].alignment = Alignment(vertical="top", indent=1)
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"].value = body
            ws[f"D{r}"].font = font(10, color=INK)
            ws[f"D{r}"].alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 46 if head == "Detailed mode" else 22
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Tabs", rule_to=6)
        r += 1
        tabs = [(S_SET, "Fee rates, giveaway cost, goal and your dropdown lists"), (S_LOG, "One row per show: the core of the workbook"),
                (S_ITEM, "Optional item-by-item tracking with a per-show summary"), (S_DASH, "Headline numbers, tables and charts"),
                (S_YEAR, "Month-by-month totals for the year")]
        for sheet, body in tabs:
            self.link(ws[f"C{r}"], f"{sheet}  ›", sheet)
            ws[f"C{r}"].alignment = Alignment(indent=1)
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"].value = body
            ws[f"D{r}"].font = font(10, color=INK2)
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Guide and Google Sheets", rule_to=6)
        r += 1
        self.note(ws, f"C{r}:F{r}", "Quick-start guide: BrassLedger_Whatnot_Quick_Start_Guide.pdf (in your download).   "
                  "Google Sheets copy: [GOOGLE SHEETS COPY LINK]", tint=PAPER, height=34, size=10, color=INK)
        r += 2
        self.note(ws, f"B{r}:F{r}", "Not affiliated with or endorsed by Whatnot. Fee rates change; check your current rates in "
                  "Settings. Not tax advice.", tint=BRASS_TINT, height=34, size=10, color=INK, bold=True)
        if self.sample:
            r += 2
            self.note(ws, f"B{r}:F{r}", "SAMPLE FILE: this copy holds 12 example shows (Aug–Oct 2026) so you can explore. "
                      "Use the blank file for your own shows.", tint=POS_TINT, height=30, size=10, color=POS, bold=True)
        ws.print_area = f"A1:G{r + 1}"
        self.protect(ws)

    # ------------------------------------------------------------ SETTINGS
    def build_settings(self):
        ws = self.ws[S_SET]
        self.page(ws, {"B": 40, "C": 18, "D": 26, "E": 60}, 5, 50, "Settings", "All rates and lists live here. Change a white cell; every tab updates.")
        self.kicker(ws, "B5", "Fees", rule_to=5)
        rows = [(6, "Currency symbol", "$", None, "Shown in headings and dashboard text."),
                (7, "Whatnot commission", 0.08, "0.0%", "Percent of each sale."),
                (8, "Payment processing", 0.029, "0.0%", "Percent of sale price plus shipping charged."),
                (9, "Processing fixed fee per order", 0.30, MONEY, "Added once per order."),
                (10, "Commission is charged on", "Sale price only", None, "Pick: sale price only, or sale price + shipping.")]
        for r, label, val, fmt, hint in rows:
            ws[f"B{r}"].value = label
            ws[f"B{r}"].font = font(10, True, INK)
            ws[f"B{r}"].alignment = Alignment(vertical="center")
            c = ws[f"C{r}"]
            c.value = val
            self.inp(c, fmt, "right" if fmt else "center")
            if r == 10:
                ws.merge_cells("C10:D10")
                ws["C10"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
                self.inp(ws["D10"])
            ws[f"E{r}"].value = hint
            ws[f"E{r}"].font = font(9, color=INK2)
            ws[f"E{r}"].alignment = Alignment(vertical="center")
            ws.row_dimensions[r].height = 20
        self.note(ws, "B11:E11", "Defaults are based on published rates as of 2025. Check Whatnot's current seller fees and update these cells.",
                  height=26, size=10, color=INK, bold=True)
        self.note(ws, "B12:E12", "Shipping charged to buyers pays for the shipping label, so it is not counted as profit. Enter it on "
                  "SHOW LOG only so fees charged on shipping are included. If you pay for labels yourself, add that under Other costs.",
                  tint=PAPER, height=40, size=9)
        self.kicker(ws, "B15", "Giveaways and goal", rule_to=5)
        for r, label, val, hint in [(16, "Default giveaway cost (per giveaway)", 3.00,
                                     "Item cost plus any shipping you cover. Used when a show's giveaway cost is left empty."),
                                    (17, "Monthly profit goal", 1500, "Used for the goal tile on DASHBOARD.")]:
            ws[f"B{r}"].value = label
            ws[f"B{r}"].font = font(10, True, INK)
            ws[f"B{r}"].alignment = Alignment(vertical="center")
            self.inp(ws[f"C{r}"], MONEY, "right")
            ws[f"C{r}"].value = val
            ws[f"E{r}"].value = hint
            ws[f"E{r}"].font = font(9, color=INK2)
            ws[f"E{r}"].alignment = Alignment(wrap_text=True, vertical="center")
            ws.row_dimensions[r].height = 28
        self.kicker(ws, "B20", "Your lists (used by the dropdowns)", rule_to=5)
        for col, head in (("B", "Categories"), ("C", "Time slots"), ("D", "Show formats")):
            self.header(ws[f"{col}21"], head, align="left")
        cats = ["Sports Cards", "Pokemon/TCG", "Sneakers", "Clothing", "Vintage", "Beauty", "Toys", "Collectibles", "Mystery Packs", "Other"]
        for i, v in enumerate(cats):
            ws[f"B{22 + i}"].value = v
            self.inp(ws[f"B{22 + i}"])
        for i, v in enumerate(["Morning", "Afternoon", "Evening", "Late night"]):
            ws[f"C{22 + i}"].value = v
            self.inp(ws[f"C{22 + i}"])
        for i, v in enumerate(["Auction", "Buy It Now", "Mixed"]):
            ws[f"D{22 + i}"].value = v
            self.inp(ws[f"D{22 + i}"])
        ws["E22"].value = "Rename any item to suit your shop. Keep each name unique."
        ws["E22"].font = font(9, color=INK2)
        ws["E23"].value = "Renaming a list item does not change rows you already logged."
        ws["E23"].font = font(9, color=INK2)
        self.kicker(ws, "B34", "System lists (please don't edit)", color=INK2, rule_to=5)
        self.header(ws["B35"], "Commission options", fill_color=BRASS_TINT, color=INK, align="left")
        self.header(ws["C35"], "Months", fill_color=BRASS_TINT, color=INK, align="left")
        for i, v in enumerate(["Sale price only", "Sale price + shipping"]):
            c = ws[f"B{36 + i}"]
            c.value = v
            c.fill, c.font, c.border = fill(BRASS_TINT), font(10, color=INK2), BOX
        for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September",
                               "October", "November", "December"]):
            c = ws[f"C{36 + i}"]
            c.value = m
            c.fill, c.font, c.border = fill(BRASS_TINT), font(10, color=INK2), BOX
        dv = DataValidation(type="list", formula1=f"={srng(OPT)}", allow_blank=False, showErrorMessage=True,
                            errorTitle="Pick an option", error="Choose one of the two options from the list.")
        ws.add_data_validation(dv)
        dv.add("C10")
        dv = DataValidation(type="decimal", operator="between", formula1="0", formula2="1", showErrorMessage=True,
                            errorTitle="Percent", error="Enter a percentage between 0% and 100%, for example 8%.")
        ws.add_data_validation(dv)
        dv.add("C7:C8")
        dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", showErrorMessage=True,
                            errorTitle="Amount", error="Enter an amount of 0 or more.")
        ws.add_data_validation(dv)
        dv.add("C9")
        dv.add("C16:C17")
        ws.freeze_panes = "A4"
        ws.print_area = "A1:F48"
        self.protect(ws)

    # ------------------------------------------------------------ SHOW LOG
    def build_log(self):
        ws = self.ws[S_LOG]
        widths = dict(B=13, C=28, D=17, E=12, F=12, G=11, H=11, I=12, J=9, K=12, L=12, M=10, N=13, O=11, P=11, Q=9, R=28,
                      S=9, T=8, U=11, V=12, W=12, X=12, Y=13, Z=9, AA=11, AB=11, AC=11)
        last_col = 29                                      # AC
        self.page(ws, widths, last_col, LOG_LAST + 2, "Show log",
                  "One row per show. Type in the white cells; the shaded columns calculate profit for you.")
        for col in HELPER_COLS:
            ws.column_dimensions[C[col]].hidden = True
            ws.column_dimensions[C[col]].width = 10
        # group band (row 4) and headers (row 5)
        ws.merge_cells("B4:R4")
        ws["B4"].value = "YOU TYPE THESE  ·  white cells"
        ws.merge_cells("S4:AC4")
        ws["S4"].value = "CALCULATED FOR YOU  ·  shaded cells"
        for c in ("B4", "S4"):
            ws[c].font = font(9, True, BRASS)
            ws[c].alignment = Alignment(vertical="center", indent=1)
        for col in range(2, 30):
            ws.cell(row=4, column=col).border = Border(bottom=Side(style="medium", color=BRASS))
        ws.row_dimensions[4].height = 20
        cur = lambda t: f'="{t} ("&{CUR}&")"'
        heads = dict(date="Date", title="Show title", cat="Category", slot="Time slot", fmt="Format", start="Start time",
                     end="End time", gross=cur("Gross sales"), orders="Orders", ship=cur("Shipping charged (optional)"),
                     cogs=cur("Cost of items sold"), gives="Giveaways (number)", gover=cur("Giveaway cost (blank = auto)"),
                     supplies=cur("Supplies / packaging"), other=cur("Other costs"), viewers="Peak viewers (optional)", notes="Notes",
                     wday="Weekday", hours="Hours live", gcost=cur("Giveaway cost"), comm=cur("Commission"), proc=cur("Processing fees"),
                     fees=cur("Total fees"), profit=cur("NET PROFIT"), margin="Profit margin", perhour=cur("Profit per hour"),
                     aov=cur("Average order"), gpct="Giveaways % of sales")
        for k, text in heads.items():
            self.header(ws[f"{C[k]}5"], text, GREEN if k in INPUT_COLS else GREEN2)
        ws[f"{C['profit']}5"].fill = fill(BRASS)
        ws[f"{C['profit']}5"].font = font(9, True, GREEN)
        ws.row_dimensions[5].height = 44
        fmts = dict(date=DATE, start=TIME, end=TIME, gross=MONEY, orders="0", ship=MONEY, cogs=MONEY, gives="0", gover=MONEY,
                    supplies=MONEY, other=MONEY, viewers="#,##0")
        aligns = {}                            # text columns get the default left + indent from inp()
        S = lambda k: sref(k)
        for r in range(LOG_FIRST, LOG_LAST + 1):
            for k in INPUT_COLS:
                self.inp(ws[f"{C[k]}{r}"], fmts.get(k), aligns.get(k))
            b, x = f"${C['date']}{r}", lambda k: f"${C[k]}{r}"
            f = {
                "wday": f'=IF({b}="","",CHOOSE(WEEKDAY({b},2),"Mon","Tue","Wed","Thu","Fri","Sat","Sun"))',
                "hours": f'=IF(OR({b}="",{x("start")}="",{x("end")}=""),"",MOD({x("end")}-{x("start")},1)*24)',
                "gcost": f'=IF({b}="","",IF({x("gover")}<>"",N({x("gover")}),N({x("gives")})*{S("give")}))',
                "comm": f'=IF({b}="","",{S("comm")}*(N({x("gross")})+IF({S("basis")}={q(S_SET)}!{OPT[1]},N({x("ship")}),0)))',
                "proc": f'=IF({b}="","",{S("proc")}*(N({x("gross")})+N({x("ship")}))+{S("fixed")}*N({x("orders")}))',
                "fees": f'=IF({b}="","",{x("comm")}+{x("proc")})',
                "profit": f'=IF({b}="","",N({x("gross")})-{x("fees")}-N({x("cogs")})-{x("gcost")}-N({x("supplies")})-N({x("other")}))',
                "margin": f'=IF(OR({b}="",N({x("gross")})=0),"",{x("profit")}/{x("gross")})',
                "perhour": f'=IF(OR({b}="",N({x("hours")})=0),"",{x("profit")}/{x("hours")})',
                "aov": f'=IF(OR({b}="",N({x("orders")})=0),"",N({x("gross")})/{x("orders")})',
                "gpct": f'=IF(OR({b}="",N({x("gross")})=0),"",{x("gcost")}/{x("gross")})',
                "yr": f'=IF({b}="","",YEAR({b}))',
                "mo": f'=IF({b}="","",MONTH({b}))',
                "key": f'=IF({b}="","",{x("yr")}*100+{x("mo")})',
                "wnum": f'=IF({b}="","",WEEKDAY({b},2))',
                "rank": f'=IF({b}="","",IF({x("yr")}={dref(D_YEAR)},{x("profit")}+ROW()/10000000,""))',
                "hprofit": f'=IF(N({x("hours")})>0,{x("profit")},"")',
            }
            cf = dict(wday=None, hours="0.0", gcost=MONEY, comm=MONEY, proc=MONEY, fees=MONEY, profit=MONEY, margin=PCT1,
                      perhour=MONEY, aov=MONEY, gpct=PCT1)
            for k, formula in f.items():
                c = ws[f"{C[k]}{r}"]
                c.value = formula
                if k in CALC_COLS:
                    self.calc(c, cf[k], bold=(k == "profit"), align="center" if k == "wday" else None)
                else:
                    c.protection = Protection(locked=True)
        # validation
        def dv(kind, rng, **kw):
            v = DataValidation(type=kind, showErrorMessage=True, allow_blank=True, **kw)
            ws.add_data_validation(v)
            v.add(rng)
        rows = lambda k: f"{C[k]}{LOG_FIRST}:{C[k]}{LOG_LAST}"
        dv("date", rows("date"), operator="between", formula1="36526", formula2="73051", errorTitle="Date",
           error="Enter a date, for example 10/24/2026.")
        dv("list", rows("cat"), formula1=f"={srng(CATS)}", errorTitle="Category", error="Pick a category from the list (edit the list on SETTINGS).")
        dv("list", rows("slot"), formula1=f"={srng(SLOTS)}", errorTitle="Time slot", error="Pick a time slot from the list.")
        dv("list", rows("fmt"), formula1=f"={srng(FMTS)}", errorTitle="Format", error="Pick a show format from the list.")
        for k in ("start", "end"):
            dv("time", rows(k), operator="between", formula1="0", formula2="0.999988", errorTitle="Time",
               error="Enter a time, for example 7:00 PM.")
        for k in ("gross", "ship", "cogs", "gover", "supplies", "other"):
            dv("decimal", rows(k), operator="greaterThanOrEqual", formula1="0", errorTitle="Amount", error="Enter an amount of 0 or more.")
        for k in ("orders", "gives", "viewers"):
            dv("whole", rows(k), operator="greaterThanOrEqual", formula1="0", errorTitle="Whole number", error="Enter a whole number of 0 or more.")
        # highlights on NET PROFIT
        p = C["profit"]
        rng = f"{p}{LOG_FIRST}:{p}{LOG_LAST}"
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'AND(${p}{LOG_FIRST}<>"",${p}{LOG_FIRST}<0)'],
                                                       fill=fill(NEG_TINT), font=Font(color=NEG, bold=True), stopIfTrue=True))
        ws.conditional_formatting.add(rng, FormulaRule(
            formula=[f'AND(${p}{LOG_FIRST}<>"",COUNT(${p}${LOG_FIRST}:${p}${LOG_LAST})>=4,${p}{LOG_FIRST}>=QUARTILE(${p}${LOG_FIRST}:${p}${LOG_LAST},3))'],
            fill=fill(POS_TINT), font=Font(color=POS, bold=True)))
        BP.databar(ws, f"{C['margin']}{LOG_FIRST}:{C['margin']}{LOG_LAST}", BRASS, max_value=1)
        ws.freeze_panes = f"D{LOG_FIRST}"
        ws.auto_filter.ref = f"B5:AC{LOG_LAST}"
        ws.print_area = f"A1:AC{LOG_LAST}"
        ws.print_title_rows = "4:5"
        if self.sample:
            for i, s in enumerate(SHOWS):
                r = LOG_FIRST + i
                for k in INPUT_COLS:
                    v = s.get(k)
                    if v is not None and v != "":
                        ws[f"{C[k]}{r}"].value = v
        self.protect(ws)

    # ------------------------------------------------------------ ITEM SALES
    def build_items(self):
        ws = self.ws[S_ITEM]
        widths = dict(B=13, C=26, D=26, E=15, F=11, G=11, H=18, I=9, J=3, K=10, L=6, M=6, N=3, O=13, P=26, Q=8, R=12, S=12, T=10, U=11)
        self.page(ws, widths, 21, ITEM_LAST + 2, "Item sales (optional)",
                  "Detailed mode: one row per item. The summary on the right totals each show; copy its sales and cost into SHOW LOG.")
        for col in ("K", "L", "M"):
            ws.column_dimensions[col].hidden = True
        ws.merge_cells("B4:I4")
        ws["B4"].value = "ITEMS  ·  one row per item sold"
        ws.merge_cells("O4:U4")
        ws["O4"].value = "SHOW SUMMARY  ·  copy Gross sales and Cost of items into SHOW LOG"
        for c in ("B4", "O4"):
            ws[c].font = font(9, True, BRASS)
            ws[c].alignment = Alignment(vertical="center", indent=1)
        for col in list(range(2, 10)) + list(range(15, 22)):
            ws.cell(row=4, column=col).border = Border(bottom=Side(style="medium", color=BRASS))
        cur = lambda t: f'="{t} ("&{CUR}&")"'
        for col, text in zip("BCDEFGHI", ["Show date", "Show title", "Item", "Category", cur("Item cost"), cur("Sold price"),
                                          "Buyer", "Shipped (Y/N)"]):
            self.header(ws[f"{col}5"], text)
        for col, text in zip(["O", "P", "Q", "R", "S", "T", "U"], ["Show date", "Show title", "Items", cur("Gross sales"),
                                                                   cur("Cost of items"), "Not shipped", "In SHOW LOG?"]):
            self.header(ws[f"{col}5"], text, GREEN2)
        ws.row_dimensions[5].height = 36
        fmts = dict(B=DATE, F=MONEY, G=MONEY)
        K = f"$K${ITEM_FIRST}:$K${ITEM_LAST}"
        for r in range(ITEM_FIRST, ITEM_LAST + 1):
            for col in "BCDEFGHI":
                self.inp(ws[f"{col}{r}"], fmts.get(col), "center" if col == "I" else None)
            ws[f"K{r}"] = f'=IF(OR($B{r}="",$C{r}=""),"",$B{r}&"|"&$C{r})'
            ws[f"L{r}"] = f'=IF($K{r}="","",IF(SUMPRODUCT(--($K${ITEM_FIRST}:$K{r}=$K{r}))=1,1,0))'
            ws[f"M{r}"] = f'=IF(N($L{r})=1,SUM($L${ITEM_FIRST}:$L{r}),"")'
        for i in range(SUM_N):
            r = ITEM_FIRST + i
            key = f'$O{r}&"|"&$P{r}'
            ws[f"O{r}"] = f'=IFERROR(INDEX($B${ITEM_FIRST}:$B${ITEM_LAST},MATCH(ROW()-{ITEM_FIRST - 1},$M${ITEM_FIRST}:$M${ITEM_LAST},0)),"")'
            ws[f"P{r}"] = f'=IFERROR(INDEX($C${ITEM_FIRST}:$C${ITEM_LAST},MATCH(ROW()-{ITEM_FIRST - 1},$M${ITEM_FIRST}:$M${ITEM_LAST},0)),"")'
            ws[f"Q{r}"] = f'=IF($O{r}="","",SUMPRODUCT(--({K}={key})))'
            ws[f"R{r}"] = f'=IF($O{r}="","",SUMPRODUCT(--({K}={key}),$G${ITEM_FIRST}:$G${ITEM_LAST}))'
            ws[f"S{r}"] = f'=IF($O{r}="","",SUMPRODUCT(--({K}={key}),$F${ITEM_FIRST}:$F${ITEM_LAST}))'
            ws[f"T{r}"] = f'=IF($O{r}="","",SUMPRODUCT(--({K}={key}),--($I${ITEM_FIRST}:$I${ITEM_LAST}<>"Y")))'
            ws[f"U{r}"] = (f'=IF($O{r}="","",IF(SUMPRODUCT(({LR("date")}=$O{r})*({LR("title")}=$P{r}))>0,"Yes","Not yet"))')
            for col, fm in zip("OPQRSTU", [DATE, None, "0", MONEY, MONEY, "0", None]):
                self.calc(ws[f"{col}{r}"], fm, align="center" if col in "QTU" else None)
        tr = ITEM_FIRST + SUM_N + 1
        ws[f"O{tr}"].value = "Total"
        ws[f"O{tr}"].font = font(10, True, GREEN)
        for col in "QRS":
            c = ws[f"{col}{tr}"]
            c.value = f"=SUM({col}{ITEM_FIRST}:{col}{ITEM_FIRST + SUM_N - 1})"
            c.font = font(10, True, GREEN)
            c.number_format = "0" if col == "Q" else MONEY
            c.border = Border(top=Side(style="medium", color=BRASS))
        self.note(ws, f"O{tr + 2}:U{tr + 2}", "A show is matched by its date and title, so type both exactly as on SHOW LOG. "
                  "\"Not yet\" means the show has no row on SHOW LOG yet.", height=34)
        # validation
        v = DataValidation(type="date", operator="between", formula1="36526", formula2="73051", allow_blank=True, showErrorMessage=True,
                           errorTitle="Date", error="Enter the show date, for example 10/24/2026.")
        ws.add_data_validation(v)
        v.add(f"B{ITEM_FIRST}:B{ITEM_LAST}")
        v = DataValidation(type="list", formula1=f"={srng(CATS)}", allow_blank=True, showErrorMessage=True,
                           errorTitle="Category", error="Pick a category from the list.")
        ws.add_data_validation(v)
        v.add(f"E{ITEM_FIRST}:E{ITEM_LAST}")
        v = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True, showErrorMessage=True,
                           errorTitle="Amount", error="Enter an amount of 0 or more.")
        ws.add_data_validation(v)
        v.add(f"F{ITEM_FIRST}:G{ITEM_LAST}")
        v = DataValidation(type="list", formula1='"Y,N"', allow_blank=True, showErrorMessage=True, errorTitle="Shipped", error="Pick Y or N.")
        ws.add_data_validation(v)
        v.add(f"I{ITEM_FIRST}:I{ITEM_LAST}")
        ws.freeze_panes = f"D{ITEM_FIRST}"
        ws.print_area = f"A1:U{ITEM_FIRST + SUM_N + 3}"
        if self.sample:
            for i, it in enumerate(ITEMS):
                r = ITEM_FIRST + i
                for col, v in zip("BCDEFGHI", it):
                    ws[f"{col}{r}"].value = v
        self.protect(ws)

    # ------------------------------------------------------------ DASHBOARD
    def build_dash(self):
        ws = self.ws[S_DASH]
        widths = {L(c): 14 for c in range(2, 14)}
        widths["B"] = 17
        widths["F"] = widths["L"] = 16
        self.page(ws, widths, 13, 112, "Dashboard", "Pick a month. Tiles show that month; tables and charts show the whole year.")
        ws.column_dimensions["P"].hidden = True
        ws.column_dimensions["Q"].hidden = True
        ws.column_dimensions["R"].hidden = True
        self.kicker(ws, "B5", "Choose the month", rule_to=13)
        ws["B6"].value = "Month"
        ws["B6"].font = font(10, True, INK)
        ws["B6"].alignment = Alignment(vertical="center")
        ws.merge_cells("C6:D6")
        self.inp(ws["C6"], align="center")
        self.inp(ws["D6"])
        ws["E6"].value = "Year"
        ws["E6"].font = font(10, True, INK)
        ws["E6"].alignment = Alignment(horizontal="right", vertical="center", indent=1)
        self.inp(ws["F6"], "0", "center")
        if self.sample:
            ws["C6"].value, ws["F6"].value = "October", 2026
        else:
            ws["C6"].value = f"=INDEX({srng(MONTHS)},MONTH(TODAY()))"
            ws["F6"].value = "=YEAR(TODAY())"
        ws.merge_cells("H6:M6")
        ws["H6"].value = "Tip: the dropdown lists the months. Type any year."
        ws["H6"].font = font(9, color=INK2)
        ws["H6"].alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[6].height = 22
        v = DataValidation(type="list", formula1=f"={srng(MONTHS)}", allow_blank=False, showErrorMessage=True,
                           errorTitle="Month", error="Pick a month from the list.")
        ws.add_data_validation(v)
        v.add("C6")
        v = DataValidation(type="whole", operator="between", formula1="2000", formula2="2099", showErrorMessage=True,
                           errorTitle="Year", error="Enter a year, for example 2026.")
        ws.add_data_validation(v)
        v.add("F6")
        ws["P6"] = f"=IFERROR(MATCH($C$6,{srng(MONTHS)},0),1)"
        ws["P7"] = "=$F$6*100+$P$6"
        yr, mn, key = "$F$6", "$P$6", "$P$7"
        Y, T, U, X, AE, AF, AG, AJ = (LR(k) for k in ("profit", "hours", "gcost", "fees", "yr", "mo", "key", "hprofit"))
        ytd = lambda col: f"SUMIFS({col},{AE},{yr},{AF},\"<=\"&{mn})"
        month = lambda col: f"SUMIFS({col},{AG},{key})"
        tiles1 = [("NET PROFIT THIS MONTH", f"={month(Y)}", MONEY),
                  ("PROFIT YEAR TO DATE", f"={ytd(Y)}", MONEY),
                  ("SHOWS THIS MONTH", f"=COUNTIFS({AG},{key})", "0"),
                  ("AVERAGE PROFIT PER SHOW", f'=IF(COUNTIFS({AG},{key})=0,"–",{month(Y)}/COUNTIFS({AG},{key}))', MONEY)]
        tiles2 = [("AVERAGE PROFIT PER HOUR", f'=IFERROR({month(AJ)}/{month(T)},"–")', MONEY),
                  ("FEES PAID YEAR TO DATE", f"={ytd(X)}", MONEY),
                  ("GIVEAWAY COST YEAR TO DATE", f"={ytd(U)}", MONEY),
                  ("MONTHLY GOAL PROGRESS", f'=IF(N({sref("goal")})=0,"–",{month(Y)}/{sref("goal")})', "0%")]
        for row, tiles in ((8, tiles1), (11, tiles2)):
            for i, (label, f, fm) in enumerate(tiles):
                self.tile(ws, row, 2 + i * 3, 4 + i * 3, label, f, fm)
        ws.row_dimensions[10].height = 6
        ws.merge_cells("B13:M13")
        ws["B13"] = (f'=IF(N({sref("goal")})=0,"Set a monthly profit goal on SETTINGS to track progress.",'
                     f'"Goal for "&$C$6&": "&{money_text(sref("goal"))}&".  Profit so far: "&{money_text(month(Y))}&'
                     f'IF({month(Y)}>={sref("goal")},".  Goal reached."," ("&{money_text(f"{sref("goal")}-{month(Y)}")}&" to go)."))')
        ws["B13"].font = font(10, True, GREEN)
        ws["B13"].alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[13].height = 22
        self.charts = []
        r = self.where_sales_went(ws, 15)
        self.dash_rows = {"slot": r}
        r = self.breakdown(ws, r, "Profit by time slot", "time slot", [f"={q(S_SET)}!$C${22 + i}" for i in range(4)], "slot")
        self.dash_rows["wday"] = r
        r = self.breakdown(ws, r, "Profit by weekday", "day",
                           ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "wnum")
        self.dash_rows["cat"] = r
        r = self.breakdown(ws, r, "Profit by category", "category", [f"={q(S_SET)}!$B${22 + i}" for i in range(10)], "cat")
        self.dash_rows["trend"] = r
        r = self.trend(ws, r)
        self.dash_rows["topbottom"] = r
        r = self.top_bottom(ws, r)
        self.dash_rows["end"] = r
        ws.print_area = f"A1:N{r}"
        self.protect(ws)

    def where_sales_went(self, ws, r):
        """This month's gross sales split into fees, item costs, giveaways, supplies and other costs, and net profit."""
        self.kicker(ws, f"B{r}", "Where this month's sales went", rule_to=13)
        hr = r + 1
        cur = lambda t: f'="{t} ("&{CUR}&")"'
        for c, text in zip("BCDE", ["Part of gross sales", cur("Amount"), "Share", ""]):
            if text:
                self.header(ws[f"{c}{hr}"], text, align="left" if c == "B" else "center")
        ws.merge_cells(f"D{hr}:E{hr}")
        ws.row_dimensions[hr].height = 26
        key = "$P$7"
        sm = lambda k: f"SUMIFS({LR(k)},{LR('key')},{key})"
        parts = [("Whatnot fees", sm("fees")), ("Item costs", sm("cogs")), ("Giveaways", sm("gcost")),
                 ("Supplies, other", f"{sm('supplies')}+{sm('other')}"), ("Net profit kept", f"MAX(0,{sm('profit')})")]
        first = hr + 1
        for i, (lab, f) in enumerate(parts):
            rr = first + i
            ws[f"B{rr}"] = lab
            ws[f"B{rr}"].font = font(10, True, INK)
            ws[f"B{rr}"].fill, ws[f"B{rr}"].border = fill(WHITE), BOX
            ws[f"C{rr}"] = f"={f}"
            self.calc(ws[f"C{rr}"], MONEY, bold=(lab == "Net profit kept"))
            ws[f"D{rr}"] = f'=IF(SUMIFS({LR("gross")},{LR("key")},{key})=0,"",C{rr}/SUMIFS({LR("gross")},{LR("key")},{key}))'
            self.calc(ws[f"D{rr}"], "0%", align="right")
            self.calc(ws[f"E{rr}"])
            ws.merge_cells(f"D{rr}:E{rr}")
        last = first + len(parts) - 1
        BP.databar(ws, f"D{first}:D{last}", BRASS, max_value=1)
        tr = last + 1
        ws[f"B{tr}"] = "Gross sales"
        ws[f"C{tr}"] = f"=SUMIFS({LR('gross')},{LR('key')},{key})"
        for c in "BC":
            x = ws[f"{c}{tr}"]
            x.fill, x.font = fill(GREEN), font(10, True, BRASS if c == "C" else PAPER)
            x.number_format = MONEY
        ws.merge_cells(f"D{tr}:F{tr}")
        ws[f"D{tr}"] = (f'=IF(C{tr}=0,"No shows in "&$C$6&" yet.",IF(SUMIFS({LR("profit")},{LR("key")},{key})<0,'
                        f'"This month lost money: costs were more than sales.","Net profit kept: "&FIXED(100*C{last}/C{tr},0)&"% of sales."))')
        ws[f"D{tr}"].font = font(10, True, GREEN)
        ws[f"D{tr}"].alignment = Alignment(horizontal="left", indent=1, vertical="center")
        ch = DoughnutChart(holeSize=55)
        ch.add_data(Reference(ws, min_col=3, min_row=first, max_row=last), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=first, max_row=last))
        colours = ["B3261E", "6B7F79", "D29A3A", "C9D3CF", "2E7D4F"]
        for i, colr in enumerate(colours):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.solidFill = "FFFFFF"
            ch.series[0].dPt.append(pt)
        BP.clean_chart(ch, legend=True, axes=False, legend_pos="r")
        ch.height, ch.width = 4.9, 15.5
        ch.anchor = f"H{r + 1}"
        ws.add_chart(ch)
        return tr + 3

    def breakdown(self, ws, r, title, noun, names, col):
        """Table (B:F) + chart (H:M) for one dimension, for the selected year. Returns the next free row."""
        yr = "$F$6"
        Y, T, AE, AJ = LR("profit"), LR("hours"), LR("yr"), LR("hprofit")
        self.kicker(ws, f"B{r}", f"{title}  ·  selected year", rule_to=13)
        hr = r + 1
        cur = lambda t: f'="{t} ("&{CUR}&")"'
        for c, text in zip("BCDEF", [noun.capitalize(), "Shows", cur("Net profit"), cur("Avg per show"), cur("Profit per hour")]):
            self.header(ws[f"{c}{hr}"], text, align="left" if c == "B" else "center")
        ws.row_dimensions[hr].height = 30
        first = hr + 1
        for i, name in enumerate(names):
            rr = first + i
            ws[f"B{rr}"] = name
            ws[f"B{rr}"].font = font(10, True, INK)
            ws[f"B{rr}"].fill = fill(WHITE)
            ws[f"B{rr}"].border = BOX
            crit = f"$B{rr}" if col != "wnum" else str(i + 1)
            data = LR(col if col != "wnum" else "wnum")
            guard = f'$B{rr}=""' if col != "wnum" else "FALSE"
            ws[f"C{rr}"] = f'=IF({guard},"",COUNTIFS({AE},{yr},{data},{crit}))'
            ws[f"D{rr}"] = f'=IF({guard},"",SUMIFS({Y},{AE},{yr},{data},{crit}))'
            ws[f"E{rr}"] = f'=IF(N($C{rr})=0,"",$D{rr}/$C{rr})'
            ws[f"F{rr}"] = f'=IFERROR(SUMIFS({AJ},{AE},{yr},{data},{crit})/SUMIFS({T},{AE},{yr},{data},{crit}),"")'
            for c, fm in zip("CDEF", ["0", MONEY, MONEY, MONEY]):
                self.calc(ws[f"{c}{rr}"], fm, bold=(c == "D"), align="center" if c == "C" else None)
        last = first + len(names) - 1
        rng_p, rng_n, rng_c = f"$D${first}:$D${last}", f"$B${first}:$B${last}", f"$C${first}:$C${last}"
        ir = last + 1
        ws.merge_cells(f"B{ir}:F{ir}")
        best = f"INDEX({rng_n},MATCH(MAX({rng_p}),{rng_p},0))"
        ws[f"B{ir}"] = (f'=IF(SUM({rng_c})=0,"Log a few shows to see which {noun} earns the most.",'
                        f'IF(MAX({rng_p})<=0,"No {noun} is in profit yet this year.",'
                        f'"Your most profitable {noun} is "&{best}&" ("&{money_text(f"MAX({rng_p})")}&" net profit this year)."))')
        ws[f"B{ir}"].font = font(10, True, GREEN)
        ws[f"B{ir}"].alignment = Alignment(vertical="center", indent=1, wrap_text=True)
        ws.row_dimensions[ir].height = 30
        ch = BarChart()
        ch.type = "bar" if len(names) > 7 else "col"
        ch.style = 10
        ch.title = None
        ch.legend = None
        ch.add_data(Reference(ws, min_col=4, min_row=first, max_row=last), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=first, max_row=last))
        s = ch.series[0]
        s.graphicalProperties.solidFill = BRASS
        s.graphicalProperties.line.solidFill = BRASS
        BP.clean_chart(ch, legend=False)
        if ch.type == "bar":
            ch.x_axis.scaling.orientation = "maxMin"
        ch.gapWidth = 60
        rows_span = max(ir - r + 1, 10)
        ch.height = rows_span * 0.53
        ch.width = 15.5
        ch.anchor = f"H{r + 1}"
        ws.add_chart(ch)
        return r + rows_span + 2

    def trend(self, ws, r):
        yr = "$F$6"
        Y, X, I, AE, AF = LR("profit"), LR("fees"), LR("gross"), LR("yr"), LR("mo")
        self.kicker(ws, f"B{r}", "Monthly profit trend  ·  selected year", rule_to=13)
        hr = r + 1
        cur = lambda t: f'="{t} ("&{CUR}&")"'
        for c, text in zip("BCDEF", ["Month", "Shows", cur("Gross sales"), cur("Total fees"), cur("Net profit")]):
            self.header(ws[f"{c}{hr}"], text, align="left" if c == "B" else "center")
        ws.row_dimensions[hr].height = 30
        first = hr + 1
        for m in range(1, 13):
            rr = first + m - 1
            ws[f"B{rr}"] = f"=LEFT({q(S_SET)}!$C${35 + m},3)"
            ws[f"B{rr}"].font = font(10, True, INK)
            ws[f"B{rr}"].fill, ws[f"B{rr}"].border = fill(WHITE), BOX
            ws[f"C{rr}"] = f"=COUNTIFS({AE},{yr},{AF},{m})"
            ws[f"D{rr}"] = f"=SUMIFS({I},{AE},{yr},{AF},{m})"
            ws[f"E{rr}"] = f"=SUMIFS({X},{AE},{yr},{AF},{m})"
            ws[f"F{rr}"] = f"=SUMIFS({Y},{AE},{yr},{AF},{m})"
            for c, fm in zip("CDEF", ["0", MONEY, MONEY, MONEY]):
                self.calc(ws[f"{c}{rr}"], fm, bold=(c == "F"), align="center" if c == "C" else None)
        last = first + 11
        ir = last + 1
        ws.merge_cells(f"B{ir}:F{ir}")
        rp, rn, rc = f"$F${first}:$F${last}", f"{q(S_SET)}!$C$36:$C$47", f"$C${first}:$C${last}"
        ws[f"B{ir}"] = (f'=IF(SUM({rc})=0,"Log a few shows to see your monthly trend.",'
                        f'"Your best month this year is "&INDEX({rn},MATCH(MAX({rp}),{rp},0))&" ("&{money_text(f"MAX({rp})")}&" net profit).")')
        ws[f"B{ir}"].font = font(10, True, GREEN)
        ws[f"B{ir}"].alignment = Alignment(vertical="center", indent=1, wrap_text=True)
        ws.row_dimensions[ir].height = 30
        ch = BarChart()
        ch.type = "col"
        ch.style = 10
        ch.add_data(Reference(ws, min_col=4, min_row=hr, max_row=last), titles_from_data=True)
        ch.add_data(Reference(ws, min_col=6, min_row=hr, max_row=last), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=first, max_row=last))
        for s, colr in zip(ch.series, (GREEN, BRASS)):
            s.graphicalProperties.solidFill = colr
            s.graphicalProperties.line.solidFill = colr
        BP.clean_chart(ch, legend=True)
        ch.gapWidth = 60
        ch.height = (ir - r + 1) * 0.53
        ch.width = 15.5
        ch.anchor = f"H{r + 1}"
        ws.add_chart(ch)
        return ir + 2

    def top_bottom(self, ws, r):
        RK, B, Cc, D, Y = LR("rank"), LR("date"), LR("title"), LR("cat"), LR("profit")
        for side, c0, label, fn in (("top", 2, "Top 5 shows by profit  ·  selected year", "LARGE"),
                                    ("bottom", 8, "Bottom 5 shows by profit  ·  selected year", "SMALL")):
            cols = [L(c0 + i) for i in range(6)]          # #, date, title(2 cols merged), category, profit
            self.kicker(ws, f"{cols[0]}{r}", label, rule_to=c0 + 5)
            hr = r + 1
            cur = f'="Net profit ("&{CUR}&")"'
            for c, text in zip([cols[0], cols[1], cols[2], cols[4], cols[5]], ["#", "Date", "Show", "Category", cur]):
                self.header(ws[f"{c}{hr}"], text, align="left" if c == cols[2] else "center")
            ws.merge_cells(f"{cols[2]}{hr}:{cols[3]}{hr}")
            ws.row_dimensions[hr].height = 30
            helper = "Q" if side == "top" else "R"
            for k in range(1, 6):
                rr = hr + k
                ws[f"{helper}{rr}"] = f'=IF({k}>COUNT({RK}),"",MATCH({fn}({RK},{k}),{RK},0))'
                hcell = f"${helper}{rr}"
                ws[f"{cols[0]}{rr}"] = k
                ws[f"{cols[1]}{rr}"] = f'=IF({hcell}="","",INDEX({B},{hcell}))'
                ws.merge_cells(f"{cols[2]}{rr}:{cols[3]}{rr}")
                ws[f"{cols[2]}{rr}"] = f'=IF({hcell}="","",INDEX({Cc},{hcell}))'
                ws[f"{cols[4]}{rr}"] = f'=IF({hcell}="","",INDEX({D},{hcell}))'
                ws[f"{cols[5]}{rr}"] = f'=IF({hcell}="","",INDEX({Y},{hcell}))'
                for c, fm in zip(cols, ["0", DATE, None, None, None, MONEY]):
                    self.calc(ws[f"{c}{rr}"], fm, bold=(c == cols[5]), align="center" if c == cols[0] else None)
                ws[f"{cols[5]}{rr}"].font = font(10, True, POS if side == "top" else INK)
            pr = f"{cols[5]}{hr + 1}:{cols[5]}{hr + 5}"
            ws.conditional_formatting.add(pr, FormulaRule(formula=[f'AND(N({cols[5]}{hr + 1})<0,{cols[5]}{hr + 1}<>"")'],
                                                          font=Font(color=NEG, bold=True)))
        ir = r + 7
        ws.merge_cells(f"B{ir}:M{ir}")
        ws[f"B{ir}"] = (f'=IF(COUNT({RK})=0,"Your best and weakest shows of the year will appear here.",'
                        f'"Your best show this year made "&{money_text(f"LARGE({RK},1)")}&" and your weakest made "&'
                        f'{money_text(f"SMALL({RK},1)")}&". Compare their time slots, giveaways and costs.")')
        ws[f"B{ir}"].font = font(10, True, GREEN)
        ws[f"B{ir}"].alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[ir].height = 24
        return ir + 1

    # ------------------------------------------------------------ YEAR SUMMARY
    def build_year(self):
        ws = self.ws[S_YEAR]
        widths = dict(B=14, C=8, D=14, E=14, F=14, G=14, H=14, I=14, J=14, K=11)
        self.page(ws, widths, 11, 30, "Year summary", "Month-by-month totals. Useful for your tax preparer. Not tax advice.")
        self.kicker(ws, "B5", "Year", rule_to=11)
        ws["B6"].value = "Year"
        ws["B6"].font = font(10, True, INK)
        self.inp(ws["C6"], "0", "center")
        ws.merge_cells("C6:D6")
        self.inp(ws["D6"])
        ws["C6"].value = f"={dref(D_YEAR)}"
        ws.merge_cells("E6:K6")
        ws["E6"].value = "Follows the DASHBOARD year until you type a different year here."
        ws["E6"].font = font(9, color=INK2)
        ws["E6"].alignment = Alignment(indent=1, vertical="center")
        v = DataValidation(type="whole", operator="between", formula1="2000", formula2="2099", showErrorMessage=True,
                           errorTitle="Year", error="Enter a year, for example 2026.")
        ws.add_data_validation(v)
        v.add("C6")
        cur = lambda t: f'="{t} ("&{CUR}&")"'
        heads = ["Month", "Shows", cur("Gross sales"), cur("Fees"), cur("Cost of items"), cur("Giveaways"), cur("Supplies"),
                 cur("Other costs"), cur("Net profit"), "Margin"]
        for c, t in zip("BCDEFGHIJK", heads):
            self.header(ws[f"{c}8"], t, GREEN if c != "J" else BRASS, PAPER if c != "J" else GREEN, align="left" if c == "B" else "center")
        ws.row_dimensions[8].height = 32
        AE, AF = LR("yr"), LR("mo")
        cols = dict(D="gross", E="fees", F="cogs", G="gcost", H="supplies", I="other", J="profit")
        for m in range(1, 13):
            r = 8 + m
            ws[f"B{r}"] = f"={q(S_SET)}!$C${35 + m}"
            ws[f"B{r}"].font = font(10, True, INK)
            ws[f"B{r}"].fill, ws[f"B{r}"].border = fill(WHITE), BOX
            ws[f"C{r}"] = f"=COUNTIFS({AE},$C$6,{AF},{m})"
            self.calc(ws[f"C{r}"], "0", align="center")
            for c, k in cols.items():
                ws[f"{c}{r}"] = f"=SUMIFS({LR(k)},{AE},$C$6,{AF},{m})"
                self.calc(ws[f"{c}{r}"], MONEY, bold=(c == "J"))
            ws[f"K{r}"] = f'=IF(N($D{r})=0,"",$J{r}/$D{r})'
            self.calc(ws[f"K{r}"], PCT1, align="center")
        tr = 21
        ws[f"B{tr}"].value = "Year total"
        for c in "CDEFGHIJ":
            ws[f"{c}{tr}"] = f"=SUM({c}9:{c}20)"
        ws[f"K{tr}"] = f'=IF(N($D{tr})=0,"",$J{tr}/$D{tr})'
        for c in "BCDEFGHIJK":
            x = ws[f"{c}{tr}"]
            x.fill, x.font = fill(GREEN), font(10, True, BRASS if c != "B" else PAPER)
            x.number_format = {"C": "0", "K": PCT1}.get(c, MONEY)
            x.alignment = Alignment(horizontal="center" if c in "CK" else None, vertical="center", indent=1 if c == "B" else 0)
        ws.row_dimensions[tr].height = 24
        BP.databar(ws, "J9:J20", "2E7D4F")
        p = f"J9:J{tr}"
        ws.conditional_formatting.add(p, FormulaRule(formula=["J9<0"], font=Font(color=NEG, bold=True)))
        self.note(ws, "B23:K23", "Net profit = gross sales − fees − cost of items − giveaways − supplies − other costs. Shipping "
                  "charged to buyers is not counted as income because it pays for the label. Useful for your tax preparer. "
                  "Not tax advice.", height=40)
        ws.freeze_panes = "A9"
        ws.print_area = "A1:L24"
        self.protect(ws)

    # ------------------------------------------------------------ assemble
    def add_sidebars(self):
        """Icon sidebar on every tab (Excel shapes, with text links underneath for Google Sheets)."""
        return BP.add_sidebars(self.wb, NAV, {S_START: 50, S_SET: 48, S_LOG: 120, S_ITEM: 120, S_DASH: 120, S_YEAR: 60})

    def build(self):
        self.build_start()
        self.build_settings()
        self.build_log()
        self.build_items()
        self.build_dash()
        self.build_year()
        self.wb.active = 0
        for ws in self.wb.worksheets:
            ws.sheet_view.tabSelected = ws.title == S_START
        self.wb.calculation.fullCalcOnLoad = True
        props = self.wb.properties
        props.title, props.creator, props.subject = PRODUCT, "Brass Ledger", "Simple tools for small business numbers."
        return self.wb


def main(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for sample in (False, True):
        b = Builder(sample)
        wb = b.build()
        layers = b.add_sidebars()
        p = out_dir / (OUT_NAME + ("_SAMPLE" if sample else "") + ".xlsx")
        wb.save(p)
        BP.finish(p, layers)
        paths.append(p)
        print("wrote", p)
    return paths


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "dist" / "whatnot-profit-tracker")
