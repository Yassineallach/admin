"""All-in-One Dashboard v3 — teal "floating cards" design with the full spec content.

Two layers (same idea as before):
  1. CELL LAYER (all editions): every number, list and control lives in cells; charts are openpyxl charts.
     In Google Sheets (which ignores Excel shapes) this layer *is* the dashboard.
  2. SHAPE LAYER (Excel edition only, drawing_inject.py): rounded cards with soft shadows, a gradient highlight tile,
     status pills, the icon sidebar, and text boxes linked live to the cell layer.

Content (top to bottom):
  KPI tiles      Projects · Task completion (highlight) · Remaining budget · This period
  Status strip   due today · due this week · overdue · recurring today
  Band A         tasks due vs completed by month · projects by status (donut) · project progress
  Band B         budget vs actual by project · open tasks by priority · period picker
  Band C         due today (incl. recurring) · upcoming deadlines · overdue tasks
  Band D         project performance table · team workload
  Band E         recent activity · project deadlines in period · recurring this week

Grid: columns 1-66 are 20 px wide; columns from 70 on hold the "dashboard engine".
"""
from __future__ import annotations

from openpyxl.chart import BarChart, DoughnutChart, LineChart, Reference
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.data_source import NumFmt
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.marker import Marker
from openpyxl.chart.series import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.text import RichText
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, Side
from openpyxl.utils import get_column_letter as L

import icons
import sidebar
from common import (BG, BORDER, DANGER, DANGER_BG, DARK, FMT_PCT, FMT_SDATE, INFO, LAVENDER, MIDNIGHT, NAVY, SECONDARY,
                    SOFT_BLUE, SOFT_LAV, SOFT_TEAL, TEAL, WARNING, WHITE, add_list_dv, fill, place_chart)
from drawing_inject import Layer, col_px_list, row_px_list

COLW = 2.86            # -> 20 px
NCOLS = 66
E0 = 70                # engine start column
GREY_BAR = "B4C1C0"
TASK_COLS = ["2F6FAA", "0F6E68", "CF3A43", "EE8A3A", "1FA99C"]
STATUS_COLS = ["9AAAA9", "9B7BE0", "14958B", "EE8A3A", "0B4F4C", "CF3A43"]
PRIORITY_COLS = ["CF3A43", "EE8A3A", "2F6FAA", "1FA99C"]

TILES = [(5, 18), (20, 33), (35, 48), (50, 63)]
LEFT, MID, RIGHT, WIDE = (5, 26), (28, 44), (46, 63), (5, 44)

# ---- row plan (px)
ROWS = {1: 34, 2: 12, 3: 20, 4: 24, 5: 26, 6: 22, 7: 18, 8: 50, 9: 12}
A_T, A0, A1, A_P = 10, 11, 22, 23                       # band A: title, chart rows, pad
B_T, B_P = 25, 38                                       # band B
C_T, C_H, C0, C_N, C_P = 40, 41, 42, 8, 50             # band C lists
D_T, D_H, D0, D_N, D_P = 52, 53, 54, 10, 64            # band D table
E_T, E_H, E0R, E_N, E_P = 66, 67, 68, 8, 76            # band E lists
LAST_ROW = 77
for r in range(A0, A1 + 1):
    ROWS[r] = 20
ROWS.update({A_T: 28, A_P: 14, 24: 18, B_T: 28, B_P: 14, 39: 18, C_T: 28, C_H: 20, C_P: 14, 51: 18,
             D_T: 28, D_H: 20, D_P: 14, 65: 18, E_T: 28, E_H: 20, E_P: 14, LAST_ROW: 18})
# band B: selector rows 26..37
ROWS.update({26: 18, 27: 24, 28: 10, 29: 24, 30: 10, 31: 24, 32: 24, 33: 24, 34: 24, 35: 10, 36: 18, 37: 20})
for r in range(C0, C0 + C_N):
    ROWS[r] = 22
for r in range(D0, D0 + D_N):
    ROWS[r] = 22
for r in range(E0R, E0R + E_N):
    ROWS[r] = 22

DASH = {}   # public cell map for the validator


def _rich(sz=800, color=SECONDARY, bold=False):
    cp = CharacterProperties(sz=sz, b=bold, solidFill=color)
    return RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=cp), endParaRPr=cp)])


def clean_chart(ch, legend=True, axes=True):
    ch.title = None
    ch.roundedCorners = False
    ch.graphical_properties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
    ch.plot_area.graphicalProperties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
    if legend:
        ch.legend.position = "t"
        ch.legend.txPr = _rich(800, SECONDARY)
    else:
        ch.legend = None
    if axes:
        for ax in (ch.x_axis, ch.y_axis):
            ax.delete = False
            ax.majorTickMark = "none"
            ax.minorTickMark = "none"
            ax.txPr = _rich(750, SECONDARY)
            ax.spPr = GraphicalProperties(ln=LineProperties(noFill=True))
        ch.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill="E3ECEB", w=6350)))
        ch.x_axis.majorGridlines = None


class DashV3:

    def __init__(self, b, ctx):
        self.b, self.T = b, b.T
        self.ws = b.ws[ctx["S_DASH"]]
        self.c = ctx
        self.excel = b.ed == "excel"
        self.layer = None
        self.texts = []        # (x0,y0,x1,y1 in grid coords, textlink, size, bold, color, align) for the shape layer
        self.titles = []       # (c1, c2, row, text, align)

    # ---------------------------------------------------------------- helpers
    def F(self, size=10, bold=False, color=DARK, italic=False):
        return self.T.font(size, bold, color, italic=italic)

    def put(self, c1, r1, c2, r2, value=None, font=None, align=None, numfmt=None, f=None, border=None):
        ws = self.ws
        if (c1, r1) != (c2, r2):
            ws.merge_cells(f"{L(c1)}{r1}:{L(c2)}{r2}")
        cell = ws.cell(row=r1, column=c1)
        if value is not None:
            cell.value = value
        if font is not None:
            cell.font = font
        cell.alignment = align or Alignment(vertical="center", indent=1)
        if numfmt:
            cell.number_format = numfmt
        if f is not None or border is not None:
            for rr in range(r1, r2 + 1):
                for cc in range(c1, c2 + 1):
                    if f is not None:
                        ws.cell(row=rr, column=cc).fill = f
                    if border is not None:
                        ws.cell(row=rr, column=cc).border = border
        return cell

    def eng(self, col, row, value, numfmt=None):
        c = self.ws.cell(row=row, column=E0 + col, value=value)
        c.font = self.F(8, color=SECONDARY)
        if numfmt:
            c.number_format = numfmt
        return f"${L(E0 + col)}${row}"

    def panel(self, c1, r1, c2, r2):
        if self.excel:
            return   # the rounded shape is the card; leave the canvas underneath so no square corner can show
        edge = Side(style="thin", color=BORDER)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                cell = self.ws.cell(row=r, column=c)
                cell.fill = fill(WHITE)
                cell.border = Border(left=edge if c == c1 else None, right=edge if c == c2 else None,
                                     top=edge if r == r1 else None, bottom=edge if r == r2 else None)

    def title(self, c1, c2, r, text, align="left"):
        self.put(c1, r, c2, r, text, self.F(11, True, NAVY), Alignment(horizontal=align, vertical="center", indent=1 if align == "left" else 0))
        self.titles.append((c1, c2, r, text, align))

    def list_col(self, c1, c2, r, formula, size=9, bold=False, color=DARK, align="left"):
        """A list cell in the cell layer + (Excel) a text box linked to it."""
        self.put(c1, r, c2, r, formula, self.F(size, bold, color),
                 Alignment(horizontal=align, vertical="center", indent=1 if align == "left" else 0, shrink_to_fit=False))
        self.texts.append((c1, r, c2, r, f"${L(c1)}${r}", size, bold, color, {"left": "l", "right": "r", "center": "c"}[align]))

    def head(self, r, spans):
        for (c1, c2, text, align) in spans:
            self.put(c1, r, c2, r, text, self.F(8, True, SECONDARY), Alignment(horizontal=align, vertical="center"))
            self.texts.append((c1, r, c2, r, None, 8, True, SECONDARY, {"left": "l", "right": "r", "center": "c"}[align], text))

    # ---------------------------------------------------------------- build
    def build(self):
        ws = self.ws
        ws.sheet_view.showGridLines = False
        ws.sheet_view.showRowColHeaders = False
        ws.sheet_view.zoomScale = 100
        for c in range(1, NCOLS + 1):
            ws.column_dimensions[L(c)].width = COLW
        for c in range(NCOLS + 1, E0):
            ws.column_dimensions[L(c)].width = COLW
        for c in range(E0, E0 + 40):
            ws.column_dimensions[L(c)].width = 12
        for r in range(1, LAST_ROW + 1):
            ws.row_dimensions[r].height = ROWS.get(r, 20) * 0.75
            for c in range(1, NCOLS + 1):
                ws.cell(row=r, column=c).fill = fill(BG)
        self.engine()
        self.sidebar_cells()
        self.header()
        self.kpis()
        self.strip()
        self.band_a()
        self.band_b()
        self.band_c()
        self.band_d()
        self.band_e()
        if self.excel:
            self.shapes()

    # ---------------------------------------------------------------- engine
    def engine(self):
        c = self.c
        VT, PB, POV, RT, SS, TODAY, DONE = c["VT"], c["PB"], c["POV"], c["RT"], c["SS"], c["TODAY"], c["DONE"]
        self.ws.cell(row=1, column=E0, value="⚙ DASHBOARD ENGINE — helper formulas and chart data (do not edit)").font = self.F(9, True, SECONDARY)
        self.in_year, self.in_from, self.in_to = "$AT$27", "$AZ$27", "$BF$27"
        e = {}
        lab = lambda r, t: self.eng(1, r, t)
        e["today"] = self.eng(0, 3, f"={TODAY}", FMT_SDATE); lab(3, "today")
        e["wk"] = self.eng(0, 4, f"={TODAY}-WEEKDAY({TODAY},2)+1", FMT_SDATE); lab(4, "week start")
        e["m_from"] = self.eng(0, 5, f'=IFERROR(MATCH({self.in_from},{SS("G")},0),1)'); lab(5, "from #")
        e["m_to"] = self.eng(0, 6, f'=IFERROR(MATCH({self.in_to},{SS("G")},0),12)'); lab(6, "to #")
        e["lo"] = self.eng(0, 7, f'=MIN({e["m_from"]},{e["m_to"]})'); lab(7, "lo")
        e["hi"] = self.eng(0, 8, f'=MAX({e["m_from"]},{e["m_to"]})'); lab(8, "hi")
        e["start"] = self.eng(0, 9, f'=DATE({self.in_year},{e["lo"]},1)', FMT_SDATE); lab(9, "period start")
        e["end"] = self.eng(0, 10, f'=EDATE(DATE({self.in_year},{e["hi"]},1),1)', FMT_SDATE); lab(10, "period end (excl.)")
        pj = POV("J")
        items = [
            ("total_projects", f'=COUNTIF({POV("C")},"?*")', None),
            ("active_projects", f'=COUNTIF({pj},{c["PSTAT"][1]})+COUNTIF({pj},{c["PSTAT"][2]})', None),
            ("completed_projects", f'=COUNTIF({pj},{c["P_DONE"]})', None),
            ("overdue_projects", f'=COUNTIF({POV("S")},"Overdue")', None),
            ("total_tasks", f'=COUNTIF({VT("C")},"?*")', None),
            ("done_tasks", f'=COUNTIFS({VT("C")},"?*",{VT("K")},{DONE})', None),
            ("pending_tasks", "=__total_tasks__-__done_tasks__", None),
            ("completion", '=IF(__total_tasks__=0,0,__done_tasks__/__total_tasks__)', FMT_PCT),
            ("overdue_tasks", f'=COUNTIF({VT("P")},"Overdue")', None),
            ("due_today", f'=COUNTIFS({VT("C")},"?*",{VT("I")},{TODAY})', None),
            ("due_week", f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&__wk__,{VT("I")},"<="&(__wk__+6),{VT("K")},"<>"&{DONE})', None),
            ("recurring_today", f'=COUNT({RT(c["RT_TODAY_COL"])})', None),
            ("planned", f'=SUM({PB("E")})', None),
            ("actual", f'=SUM({PB("F")})', None),
            ("remaining", "=__planned__-__actual__", None),
            ("used", '=IF(__planned__=0,0,__actual__/__planned__)', FMT_PCT),
            ("tasks_p", f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&__start__,{VT("I")},"<"&__end__)', None),
            ("spent_p", f'=SUMIFS({PB("F")},{PB("I")},">="&__start__,{PB("I")},"<"&__end__)', None),
            ("revenue", f'=SUM({POV("W")})', None),
        ]
        for i, (k, fm, nf) in enumerate(items):
            for kk, vv in e.items():
                fm = fm.replace(f"__{kk}__", vv)
            e[k] = self.eng(0, 12 + i, fm, nf)
            lab(12 + i, k.replace("_", " "))
        mon = '{"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"}'
        e["period_label"] = self.eng(0, 32, f'=CHOOSE({e["lo"]},"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec")&'
                                            f'IF({e["lo"]}={e["hi"]},"","–"&CHOOSE({e["hi"]},"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"))&" "&{self.in_year}')
        lab(32, "period label")
        cur = "TRIM(CurrencySymbol)"
        money = lambda x: f'{cur}&TEXT({x},"#,##0")'
        # tile texts (cell layer shows them; shapes link to these cells)
        e["t1_sub"] = self.eng(0, 34, f'={e["total_projects"]}&" total · "&{e["completed_projects"]}&" done · "&{e["overdue_projects"]}&" overdue"')
        e["t2_sub"] = self.eng(0, 35, f'={e["total_tasks"]}&" tasks · "&{e["done_tasks"]}&" done · "&{e["pending_tasks"]}&" pending"')
        e["t3_val"] = self.eng(0, 36, f"={money(e['remaining'])}")
        e["t3_sub"] = self.eng(0, 37, f'="of "&{money(e["planned"])}&" · "&{money(e["actual"])}&" spent"')
        e["t4_sub"] = self.eng(0, 38, f'={money(e["spent_p"])}&" spent · "&{e["period_label"]}')
        for i, t in enumerate(("tile 1 sub", "tile 2 sub", "tile 3 value", "tile 3 sub", "tile 4 sub")):
            lab(34 + i, t)
        # slider (budget used) on tile 3
        self.eng(14, 3, "Slider")
        self.eng(14, 4, f"=MIN(1,{e['used']})")
        self.eng(15, 4, f"=MAX(0,1-{e['used']})")
        # monthly series rows 41..52: month, in-period, other, completed (by completion date), (spare)
        for j, h in enumerate(["Month", "In period", "Other months", "Completed"]):
            self.eng(3 + j, 40, h)
        for m in range(12):
            r = 41 + m
            mc = f"${L(E0 + 3)}{r}"
            self.eng(3, r, f"=DATE({self.in_year},{m + 1},1)", "mmm")
            due = f'COUNTIFS({VT("C")},"?*",{VT("I")},">="&{mc},{VT("I")},"<"&EDATE({mc},1))'
            inr = f'AND({m + 1}>={e["lo"]},{m + 1}<={e["hi"]})'
            self.eng(4, r, f"=IF({inr},{due},0)")
            self.eng(5, r, f"=IF({inr},0,{due})")
            self.eng(6, r, f'=COUNTIFS({VT("AF")},">="&{mc},{VT("AF")},"<"&EDATE({mc},1))')
        # project status (rows 55..60)
        self.eng(3, 54, "Status"); self.eng(4, 54, "Projects")
        for i in range(6):
            r = 55 + i
            self.eng(3, r, f"={c['PSTAT'][i]}&\"\"")
            self.eng(4, r, f'=IF({L(E0 + 3)}{r}="",0,COUNTIF({pj},{L(E0 + 3)}{r}))')
        # project progress bars (rows 63..67), top-down order -> reversed rows
        self.eng(3, 62, "Project"); self.eng(4, 62, "Track"); self.eng(5, 62, "Progress")
        for i in range(5):
            r = 63 + i
            idx = f'MATCH({5 - i},{POV("U")},0)'
            self.eng(3, r, f'=IFERROR(INDEX({POV("C")},{idx}),"—")')
            self.eng(4, r, "=1")
            self.eng(5, r, f'=IFERROR(N(INDEX({POV("K")},{idx})),0)')
        # budget vs actual by project (rows 71..78), top-down -> reversed
        self.eng(3, 70, "Project"); self.eng(4, 70, "Budget"); self.eng(5, 70, "Actual")
        for i in range(8):
            r = 71 + i
            idx = f'MATCH({8 - i},{POV("U")},0)'
            self.eng(3, r, f'=IFERROR(INDEX({POV("C")},{idx}),"")')
            self.eng(4, r, f'=IFERROR(N(INDEX({POV("L")},{idx})),0)')
            self.eng(5, r, f'=IFERROR(N(INDEX({POV("M")},{idx})),0)')
        # open tasks by priority (rows 81..84)
        self.eng(3, 80, "Priority"); self.eng(4, 80, "Open tasks")
        for k, p in enumerate(c["PRI"].values()):
            r = 81 + k
            self.eng(3, r, f"={p}&\"\"")
            self.eng(4, r, f'=COUNTIFS({VT("J")},{p},{VT("C")},"?*",{VT("K")},"<>"&{DONE})')
        # team workload (rows 87..93)
        self.eng(3, 86, "Member"); self.eng(4, 86, "Open"); self.eng(5, 86, "Overdue")
        for i in range(7):
            r = 87 + i
            nm = f"INDEX({c['SL']('G')},{i + 1})"
            self.eng(3, r, f'=IF({nm}="","",{nm})')
            self.eng(4, r, f'=IF({L(E0 + 3)}{r}="",0,COUNTIFS({VT("G")},{L(E0 + 3)}{r},{VT("C")},"?*",{VT("K")},"<>"&{DONE}))')
            self.eng(5, r, f'=IF({L(E0 + 3)}{r}="",0,COUNTIFS({VT("G")},{L(E0 + 3)}{r},{VT("P")},"Overdue"))')
        self.e = e
        DASH.update({k: v.replace("$", "") for k, v in e.items()})
        DASH.update(month_first=f"{L(E0 + 3)}41", status_first=f"{L(E0 + 4)}55", proj_first=f"{L(E0 + 3)}63",
                    budget_first=f"{L(E0 + 3)}71", priority_first=f"{L(E0 + 4)}81", team_first=f"{L(E0 + 3)}87")

    # ---------------------------------------------------------------- sidebar + header
    def sidebar_cells(self):
        if not self.excel:   # Excel draws the shared sidebar as shapes (see shapes())
            sidebar.cells(self.ws, self.T, self.c["quote"], self.c["S_DASH"], LAST_ROW, 1, 3,
                          [ROWS.get(r, 20) for r in range(1, LAST_ROW + 2)])

    def header(self):
        c, SC = self.c, self.c["SC"]
        self.put(5, 1, 26, 1, f'=IF({SC("C", 13)}="","Project Command Center",{SC("C", 13)})', self.F(15, True, NAVY),
                 Alignment(vertical="center"))
        who = f'IF({SC("C", 12)}="","",{SC("C", 12)})&IF(OR({SC("C", 11)}="",{SC("C", 12)}=""),"","  ·  ")&IF({SC("C", 11)}="","",{SC("C", 11)})'
        demo = '"DEMO DATA  ·  "&' if self.b.demo else ""
        self.put(27, 1, 63, 1, f'={demo}{who}&IF({who}="","","  ·  ")&TEXT({c["TODAY"]},"dddd")&", "&TEXT({c["TODAY"]},"mmmm d, yyyy")',
                 self.F(10, False, SECONDARY), Alignment(horizontal="right", vertical="center"))
        DASH["header_title"], DASH["header_line"] = "E1", "AA1"

    # ---------------------------------------------------------------- KPI tiles + strip
    def kpis(self):
        e = self.e
        tiles = [
            ("Active projects", f"={e['active_projects']}", "#,##0", f"={e['t1_sub']}", False, "tile_projects", "stack"),
            ("Task completion", f"={e['completion']}", FMT_PCT, f"={e['t2_sub']}", True, "tile_completion", "donut"),
            ('="Remaining budget  ("&TRIM(CurrencySymbol)&")"', f"={e['t3_val']}", None, f"={e['t3_sub']}", False, "tile_budget", "money"),
            ("Tasks due this period", f"={e['tasks_p']}", "#,##0", f"={e['t4_sub']}", False, "tile_period", "calendar"),
        ]
        self.tile_cells = []
        for (c1, c2), (label, val, nf, sub, hl, key, icon) in zip(TILES, tiles):
            bg = fill("17A397") if hl else fill(WHITE)
            fg = WHITE if hl else NAVY
            self.panel(c1, 3, c2, 7)
            if not self.excel:
                for r in range(3, 8):
                    for cc in range(c1, c2 + 1):
                        self.ws.cell(row=r, column=cc).fill = bg
            self.put(c1, 7, c2, 7, label, self.F(9, True, fg), Alignment(horizontal="center", vertical="center"))
            self.put(c1, 4, c2, 5, val, self.F(22, True, fg), Alignment(horizontal="center", vertical="center"), nf)
            self.put(c1, 6, c2, 6, sub, self.F(8, False, "D9F2EE" if hl else SECONDARY), Alignment(horizontal="center", vertical="center"))
            DASH[key] = f"{L(c1)}4"
            DASH[key + "_sub"] = f"{L(c1)}6"
            self.tile_cells.append(((c1, c2), f"${L(c1)}$4", f"${L(c1)}$6", f"${L(c1)}$7", hl, icon))

    def strip(self):
        e = self.e
        pills = [(f'="●  "&{e["due_today"]}&" due today"', SOFT_TEAL, MIDNIGHT, "pill_today"),
                 (f'="●  "&{e["due_week"]}&" open, due this week"', SOFT_BLUE, MIDNIGHT, "pill_week"),
                 (f'="●  "&{e["overdue_tasks"]}&" overdue tasks"', DANGER_BG, DANGER, "pill_overdue"),
                 (f'="↻  "&{e["recurring_today"]}&" recurring today"', SOFT_LAV, "5B3FA8", "pill_recurring")]
        thick = Side(style="thick", color=BG)
        self.pills = []
        for (c1, c2), (fm, bg, fg, key) in zip(TILES, pills):
            self.put(c1, 8, c2, 8, fm, self.F(9, True, fg), Alignment(horizontal="center", vertical="center"), None,
                     None if self.excel else fill(bg),
                     Border(top=thick, bottom=thick))
            DASH[key] = f"{L(c1)}8"
            self.pills.append(((c1, c2), f"${L(c1)}$8", bg, fg))

    # ---------------------------------------------------------------- band A
    def band_a(self):
        ws, E = self.ws, E0
        self.panel(LEFT[0], A_T, MID[1], A_P)
        self.panel(RIGHT[0], A_T, RIGHT[1], A_P)
        self.title(*LEFT, A_T, "Tasks due vs completed", "center")
        self.title(*MID, A_T, "Projects by status", "center")
        self.title(*RIGHT, A_T, "Project progress", "center")
        bar = BarChart()
        bar.type = "col"
        bar.overlap = 100
        bar.gapWidth = 45
        bar.add_data(Reference(ws, min_col=E + 4, max_col=E + 5, min_row=40, max_row=52), titles_from_data=True)
        bar.set_categories(Reference(ws, min_col=E + 3, min_row=41, max_row=52))
        bar.series[0].graphicalProperties.solidFill = MIDNIGHT
        bar.series[1].graphicalProperties.solidFill = GREY_BAR
        for s in bar.series:
            s.graphicalProperties.line.noFill = True
        line = LineChart()
        line.add_data(Reference(ws, min_col=E + 6, min_row=40, max_row=52), titles_from_data=True)
        s = line.series[0]
        s.smooth = True
        s.graphicalProperties.line.solidFill = "2F7E9E"
        s.graphicalProperties.line.width = 28575
        s.marker = Marker(symbol="circle", size=6)
        s.marker.graphicalProperties = GraphicalProperties(solidFill=WHITE, ln=LineProperties(solidFill="2F7E9E", w=15875))
        clean_chart(bar)
        bar += line
        place_chart(ws, bar, LEFT[0], A0, LEFT[1], A1)
        d = DoughnutChart(holeSize=66)
        d.add_data(Reference(ws, min_col=E + 4, min_row=55, max_row=60), titles_from_data=False)
        d.set_categories(Reference(ws, min_col=E + 3, min_row=55, max_row=60))
        for i, colr in enumerate(STATUS_COLS):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.solidFill = WHITE
            d.series[0].dPt.append(pt)
        clean_chart(d, legend=True, axes=False)
        d.legend.position = "r"
        place_chart(ws, d, MID[0], A0, MID[1], A1)
        pb = BarChart()
        pb.type = "bar"
        pb.overlap = 100
        pb.gapWidth = 80
        pb.add_data(Reference(ws, min_col=E + 4, max_col=E + 5, min_row=62, max_row=67), titles_from_data=True)
        pb.set_categories(Reference(ws, min_col=E + 3, min_row=63, max_row=67))
        pb.series[0].graphicalProperties.solidFill = "E2F2EF"
        for s in pb.series:
            s.graphicalProperties.line.noFill = True
        for i, colr in enumerate(reversed(TASK_COLS)):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.noFill = True
            pb.series[1].dPt.append(pt)
        clean_chart(pb, legend=False)
        pb.y_axis.scaling.min = 0
        pb.y_axis.scaling.max = 1
        pb.y_axis.delete = True
        pb.y_axis.majorGridlines = None
        place_chart(ws, pb, RIGHT[0], A0, RIGHT[1], A1)

    # ---------------------------------------------------------------- band B
    def band_b(self):
        ws, E = self.ws, E0
        self.panel(LEFT[0], B_T, MID[1], B_P)
        self.title(*LEFT, B_T, "Budget vs actual by project", "center")
        self.title(*MID, B_T, "Open tasks by priority", "center")
        b = BarChart()
        b.type = "bar"
        b.gapWidth = 40
        b.overlap = -5
        b.add_data(Reference(ws, min_col=E + 4, max_col=E + 5, min_row=70, max_row=78), titles_from_data=True)
        b.set_categories(Reference(ws, min_col=E + 3, min_row=71, max_row=78))
        b.series[0].graphicalProperties.solidFill = "8ED6CC"
        b.series[1].graphicalProperties.solidFill = MIDNIGHT
        for s in b.series:
            s.graphicalProperties.line.noFill = True
        clean_chart(b)
        b.y_axis.numFmt = NumFmt(formatCode='#,##0,"K"', sourceLinked=False)
        place_chart(ws, b, LEFT[0], B_T + 1, LEFT[1], B_P - 1)
        p = BarChart()
        p.type = "col"
        p.gapWidth = 70
        p.add_data(Reference(ws, min_col=E + 4, min_row=80, max_row=84), titles_from_data=True)
        p.set_categories(Reference(ws, min_col=E + 3, min_row=81, max_row=84))
        for i, colr in enumerate(PRIORITY_COLS):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.noFill = True
            p.series[0].dPt.append(pt)
        p.series[0].dLbls = DataLabelList()
        p.series[0].dLbls.showVal = True
        for attr in ("showSerName", "showCatName", "showLegendKey", "showPercent"):
            setattr(p.series[0].dLbls, attr, False)
        p.series[0].dLbls.txPr = _rich(900, NAVY, True)
        clean_chart(p, legend=False)
        place_chart(ws, p, MID[0], B_T + 1, MID[1], B_P - 1)
        self.selector()

    def selector(self):
        ws, c = self.ws, self.c
        c1, c2 = RIGHT
        self.put(c1, B_T, c2, B_T, "Period", self.F(11, True, NAVY), Alignment(horizontal="left", vertical="center"))
        thick = Side(style="thick", color=BG)
        box = Border(left=thick, right=thick, top=thick, bottom=thick)
        spans = [(46, 51, "YEAR"), (52, 57, "FROM"), (58, 63, "TO")]
        defaults = [f"={c['SC']('C', 18)}",
                    f'=INDEX({c["SS"]("G")},INT((MONTH({c["TODAY"]})-1)/3)*3+1)',
                    f'=INDEX({c["SS"]("G")},MONTH({c["TODAY"]}))']
        for (a, b_, lab), dflt in zip(spans, defaults):
            self.put(a, 26, b_, 26, lab, self.F(8, True, SECONDARY), Alignment(horizontal="center", vertical="bottom"))
            self.put(a, 27, b_, 27, dflt, self.F(10, True, NAVY), Alignment(horizontal="center", vertical="center"),
                     f=fill(SOFT_BLUE), border=box)
            self.b.unlocked[c["S_DASH"]].append(f"{L(a)}27:{L(b_)}27")
        add_list_dv(ws, "AT27", c["SS"]("H"))
        add_list_dv(ws, "AZ27", c["SS"]("G"))
        add_list_dv(ws, "BF27", c["SS"]("G"))
        DASH.update(year="AT27", from_="AZ27", to="BF27")
        for i, (a, b_) in enumerate(((47, 50), (51, 54), (55, 58), (59, 62))):
            self.put(a, 29, b_, 29, f"={self.in_year}+{i - 1}", self.F(9, True, NAVY), Alignment(horizontal="center", vertical="center"),
                     "0", fill(WHITE), box)
            ws.conditional_formatting.add(f"{L(a)}29:{L(b_)}29", FormulaRule(formula=[f"{L(a)}29={self.in_year}"],
                                                                                fill=fill("17A397"), font=Font(color=WHITE, bold=True)))
        months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
        lo, hi = self.e["lo"], self.e["hi"]
        for i, m in enumerate(months):
            r = 31 + i // 3
            a = 46 + (i % 3) * 6
            self.put(a, r, a + 5, r, m, self.F(9, True, NAVY), Alignment(horizontal="center", vertical="center"), None, fill(WHITE), box)
            ws.conditional_formatting.add(f"{L(a)}{r}:{L(a + 5)}{r}", FormulaRule(
                formula=[f"AND({i + 1}>={lo},{i + 1}<={hi})"], fill=fill("17A397"), font=Font(color=WHITE, bold=True)))
        self.put(c1, 36, c2, 36, "Pick a year and month range with the ▾ cells above.", self.F(8, False, SECONDARY, italic=True),
                 Alignment(horizontal="center", vertical="center"))

    # ---------------------------------------------------------------- band C: due today / upcoming / overdue
    def band_c(self):
        c, E = self.c, E0
        VT, RT, DONE = c["VT"], c["RT"], c["DONE"]
        for span in (LEFT, MID, RIGHT):
            self.panel(span[0], C_T, span[1], C_P)
        self.title(*LEFT, C_T, "Due today")
        self.title(*MID, C_T, "Upcoming deadlines")
        self.title(*RIGHT, C_T, "Overdue tasks")
        self.head(C_H, [(6, 19, "TASK", "left"), (20, 23, "OWNER", "left"), (24, 25, "", "center"),
                        (29, 39, "TASK", "left"), (40, 43, "DUE", "right"),
                        (47, 58, "TASK", "left"), (59, 62, "LATE", "right")])
        ix_t, ix_r, ix_u, ix_o = E + 20, E + 21, E + 22, E + 23
        self.eng(20, C_H, "idx today task"); self.eng(21, C_H, "idx today recurring")
        self.eng(22, C_H, "idx upcoming"); self.eng(23, C_H, "idx overdue")
        n_today = self.e["due_today"]
        for k in range(1, C_N + 1):
            r = C0 + k - 1
            self.eng(20, r, f'=IFERROR(MATCH(INT({c["TODAY"]})&"|{k}",{VT("R")},0),"")')
            self.eng(21, r, f'=IF({k}<={n_today},"",IFERROR(MATCH({k}-{n_today},{RT(c["RT_TODAY_COL"])},0),""))')
            self.eng(22, r, f'=IFERROR(MATCH(SMALL({VT("T")},{k}),{VT("T")},0),"")')
            self.eng(23, r, f'=IFERROR(MATCH(SMALL({VT("U")},{k}),{VT("U")},0),"")')
            it, ir, iu, io = (f"${L(ix_t)}{r}", f"${L(ix_r)}{r}", f"${L(ix_u)}{r}", f"${L(ix_o)}{r}")
            empty_today = '"Nothing due today"' if k == 1 else '""'
            name = (f'=IF({it}<>"",INDEX({VT("C")},{it})&"",IF({ir}<>"","↻ "&INDEX({RT("C")},{ir}),{empty_today}))')
            owner_of = lambda rng, i: f'LEFT(INDEX({rng},{i})&"",FIND(" ",INDEX({rng},{i})&" ")-1)'
            owner = f'=IF({it}<>"",{owner_of(VT("G"), it)},IF({ir}<>"",{owner_of(RT("F"), ir)},""))'
            mark = f'=IF({it}<>"",IF(INDEX({VT("K")},{it})={DONE},"✓","○"),IF({ir}<>"","↻",""))'
            self.list_col(6, 19, r, name)
            self.list_col(20, 23, r, owner, 9, False, SECONDARY)
            self.list_col(24, 25, r, mark, 9, True, MIDNIGHT, "center")
            up_name = f'=IF({iu}="",{chr(34) + "No upcoming deadlines" + chr(34) if k == 1 else chr(34) * 2},INDEX({VT("C")},{iu})&"")'
            self.list_col(29, 39, r, up_name)
            self.list_col(40, 43, r, f'=IF({iu}="","",TEXT(INDEX({VT("I")},{iu}),"mmm d"))', 9, True, MIDNIGHT, "right")
            od_name = f'=IF({io}="",{chr(34) + "No overdue tasks" + chr(34) if k == 1 else chr(34) * 2},INDEX({VT("C")},{io})&"")'
            self.list_col(47, 58, r, od_name)
            self.list_col(59, 62, r, f'=IF({io}="","",-INDEX({VT("Q")},{io})&" d")', 9, True, DANGER, "right")
        DASH.update(today_first=f"F{C0}", today_mark_first=f"X{C0}", up_first=f"AC{C0}", up_due_first=f"AN{C0}",
                    od_first=f"AU{C0}", od_late_first=f"BG{C0}")

    # ---------------------------------------------------------------- band D: performance table + team workload
    def band_d(self):
        ws, c, E = self.ws, self.c, E0
        POV = c["POV"]
        self.panel(WIDE[0], D_T, WIDE[1], D_P)
        self.panel(RIGHT[0], D_T, RIGHT[1], D_P)
        self.title(*WIDE, D_T, "Project performance")
        self.title(*RIGHT, D_T, "Team workload")
        cols = [(6, 15, "PROJECT", "left"), (16, 18, "OWNER", "left"), (19, 22, "STATUS", "left"), (23, 28, "PROGRESS", "left"),
                (29, 32, "BUDGET", "right"), (33, 36, "SPENT", "right"), (37, 39, "MARGIN", "right"), (40, 43, "HEALTH", "right")]
        self.head(D_H, cols)
        ix = E + 24
        self.eng(24, D_H, "idx perf")
        cur = "TRIM(CurrencySymbol)"
        for k in range(D_N):
            r = D0 + k
            self.eng(24, r, f'=IFERROR(MATCH({k + 1},{POV("U")},0),"")')
            i = f"${L(ix)}{r}"
            g = lambda col: f'INDEX({POV(col)},{i})'
            first = '"No projects yet"' if k == 0 else '""'
            self.list_col(6, 15, r, f'=IF({i}="",{first},{g("C")}&"")', 9, True, DARK)
            self.list_col(16, 18, r, f'=IF({i}="","",LEFT({g("F")}&"",FIND(" ",{g("F")}&" ")-1))', 9, False, SECONDARY)
            self.list_col(19, 22, r, f'=IF({i}="","",{g("J")}&"")', 9, False, DARK)
            bar = f'REPT("█",ROUND(N({g("K")})*8,0))&REPT("░",8-ROUND(N({g("K")})*8,0))&"  "&TEXT(N({g("K")}),"0%")'
            self.list_col(23, 28, r, f'=IF({i}="","",{bar})', 9, False, TEAL)
            self.list_col(29, 32, r, f'=IF({i}="","",{cur}&TEXT(N({g("L")}),"#,##0"))', 9, False, DARK, "right")
            self.list_col(33, 36, r, f'=IF({i}="","",{cur}&TEXT(N({g("M")}),"#,##0"))', 9, False, DARK, "right")
            self.list_col(37, 39, r, f'=IF({i}="","",IF({g("Y")}="","—",TEXT({g("Y")},"0%")))', 9, False, DARK, "right")
            self.list_col(40, 43, r, f'=IF({i}="","",{g("S")}&"")', 9, True, MIDNIGHT, "right")
        DASH.update(perf_first=f"F{D0}", perf_progress_first=f"W{D0}", perf_margin_first=f"AK{D0}", perf_health_first=f"AN{D0}")
        t = BarChart()
        t.type = "col"
        t.gapWidth = 60
        t.add_data(Reference(ws, min_col=E + 4, max_col=E + 5, min_row=86, max_row=93), titles_from_data=True)
        t.set_categories(Reference(ws, min_col=E + 3, min_row=87, max_row=93))
        t.series[0].graphicalProperties.solidFill = "17A397"
        t.series[1].graphicalProperties.solidFill = WARNING
        for s in t.series:
            s.graphicalProperties.line.noFill = True
        clean_chart(t)
        place_chart(ws, t, RIGHT[0], D_H, RIGHT[1], D_P - 1)

    # ---------------------------------------------------------------- band E: recent / deadlines in period / recurring this week
    def band_e(self):
        c, E = self.c, E0
        VT, POV, RT = c["VT"], c["POV"], c["RT"]
        for span in (LEFT, MID, RIGHT):
            self.panel(span[0], E_T, span[1], E_P)
        self.title(*LEFT, E_T, "Recent activity")
        self.title(*MID, E_T, "Project deadlines in period")
        self.title(*RIGHT, E_T, "Recurring this week")
        self.head(E_H, [(6, 18, "TASK", "left"), (19, 25, "STATUS", "left"),
                        (29, 38, "PROJECT", "left"), (39, 43, "DUE", "right"),
                        (47, 57, "TASK", "left"), (58, 62, "NEXT", "right")])
        self.eng(25, E_H, "idx recent"); self.eng(26, E_H, "idx deadline"); self.eng(27, E_H, "idx recurring")
        st, en = self.e["start"], self.e["end"]
        glyph = lambda s: (f'IF({s}="","",IFERROR(CHOOSE(MATCH({s},{c["SL"]("E")},0),"■","○","►","◆","✓","‖")&"  ","")&{s})')
        for k in range(1, E_N + 1):
            r = E0R + k - 1
            self.eng(25, r, f'=IFERROR(MATCH(LARGE({VT("Y")},{k}),{VT("Y")},0),"")')
            v = f'SMALL({POV("V")},COUNTIF({POV("V")},"<"&{st})+{k})'
            self.eng(26, r, f'=IFERROR(IF({v}<{en},MATCH({v},{POV("V")},0),""),"")')
            self.eng(27, r, f'=IFERROR(MATCH(SMALL({RT("X")},{k}),{RT("X")},0),"")')
            ir, idl, irc = f"${L(E + 25)}{r}", f"${L(E + 26)}{r}", f"${L(E + 27)}{r}"
            q = lambda t_: chr(34) + t_ + chr(34) if k == 1 else chr(34) * 2
            self.list_col(6, 18, r, f'=IF({ir}="",{q("No activity yet")},INDEX({VT("C")},{ir})&"")')
            self.list_col(19, 25, r, f'=IF({ir}="","",{glyph("INDEX(" + VT("K") + "," + ir + ")")})', 9, False, MIDNIGHT)
            self.list_col(29, 38, r, f'=IF({idl}="",{q("No deadlines in this period")},INDEX({POV("C")},{idl})&"")')
            self.list_col(39, 43, r, f'=IF({idl}="","",TEXT(INDEX({POV("H")},{idl}),"mmm d"))', 9, True, MIDNIGHT, "right")
            self.list_col(47, 57, r, f'=IF({irc}="",{q("Nothing recurring this week")},"↻ "&INDEX({RT("C")},{irc}))', 9, False, "5B3FA8")
            self.list_col(58, 62, r, f'=IF({irc}="","",TEXT(INDEX({RT("N")},{irc}),"ddd d"))', 9, True, MIDNIGHT, "right")
        DASH.update(recent_first=f"F{E0R}", deadline_first=f"AC{E0R}", recurring_first=f"AU{E0R}", recurring_next_first=f"BF{E0R}")

    # ---------------------------------------------------------------- Excel shape layer
    def shapes(self):
        ws = self.ws
        lay = Layer(col_px_list(ws, NCOLS + 2), row_px_list(ws, LAST_ROW + 2), font=self.T.font_name)
        X, Y = lay.x, lay.y
        shadow = ("0F6E68", 16, 18, 4)
        G = 3   # grow cards a little past their cell box

        def card(x0, y0, x1, y1, **kw):
            lay.shape(x0 - G, y0 - G, x1 + G, y1 + G, **kw)
        sidebar.draw(lay, self.c["S_DASH"], Y(LAST_ROW + 1))
        # tiles
        for ((c1, c2), v, sub, lab, hl, icon) in self.tile_cells:
            x0, x1, y0, y1 = X(c1), X(c2 + 1), Y(3), Y(8)
            if hl:
                card(x0, y0 - 6, x1, y1 + 6, radius=0.16, fill=None, grad=([(0, "1EB5A6"), (100, "86DDD3")], 90),
                          shadow=("17A397", 45, 26, 6), name="Highlight")
                png = icons.donut(c="E1F3F0", size=96, accent="0B4F4C")
            else:
                card(x0, y0, x1, y1, radius=0.14, fill=WHITE, shadow=shadow, name="Tile")
                png = icons.ICONS[icon](c="0F6E68", size=96)
            fg = WHITE if hl else NAVY
            lay.picture(x0 + 16, y0 + 22, x0 + 60, y0 + 66, png)
            lay.text(x0 + 66, y0 + 12, x1 - 10, y0 + 56, textlink=v, size=24 if not hl else 26, bold=not hl, color=fg, align="c")
            lay.text(x0 + 66, y0 + 58, x1 - 10, y0 + 76, textlink=sub, size=9, color="E3F7F4" if hl else "5F7472", align="c")
            lay.text(x0 + 10, y1 - 28, x1 - 10, y1 - 8, textlink=lab, size=11, color=fg, align="c")
            if c1 == TILES[2][0]:
                pass
        # strip pills
        for ((c1, c2), link, bg, fg) in self.pills:
            x0, x1, y0, y1 = X(c1), X(c2 + 1), Y(8) + 19, Y(8) + 43   # >= 8 px clear of the tiles (incl. the taller highlight)
            lay.shape(x0, y0, x1, y1, radius=0.5, fill=bg, name="Pill")
            lay.text(x0 + 8, y0, x1 - 8, y1, textlink=link, size=10, bold=True, color=fg, align="c")
        # panels
        card(X(LEFT[0]), Y(A_T), X(MID[1] + 1), Y(A_P + 1), radius=0.05, fill=WHITE, shadow=shadow, name="Panel")
        card(X(RIGHT[0]), Y(A_T), X(RIGHT[1] + 1), Y(A_P + 1), radius=0.07, fill=WHITE, shadow=shadow, name="Panel")
        card(X(LEFT[0]), Y(B_T), X(MID[1] + 1), Y(B_P + 1), radius=0.05, fill=WHITE, shadow=shadow, name="Panel")
        for (c1, c2) in (LEFT, MID, RIGHT):
            card(X(c1), Y(C_T), X(c2 + 1), Y(C_P + 1), radius=0.07, fill=WHITE, shadow=shadow, name="Panel")
            card(X(c1), Y(E_T), X(c2 + 1), Y(E_P + 1), radius=0.07, fill=WHITE, shadow=shadow, name="Panel")
        card(X(WIDE[0]), Y(D_T), X(WIDE[1] + 1), Y(D_P + 1), radius=0.05, fill=WHITE, shadow=shadow, name="Panel")
        card(X(RIGHT[0]), Y(D_T), X(RIGHT[1] + 1), Y(D_P + 1), radius=0.07, fill=WHITE, shadow=shadow, name="Panel")
        # titles, headers, list rows
        for (c1, c2, r, text, align) in self.titles:
            if align == "center":
                lay.text(X(c1), Y(r) + 4, X(c2 + 1), Y(r + 1), text=text, size=12, color=NAVY, align="c")
            else:
                lay.text(X(c1) + 16, Y(r) + 4, X(c2 + 1) - 8, Y(r + 1), text=text, size=12, color=NAVY, align="l")
        for item in self.texts:
            c1, r1, c2, r2, link, size, bold, color, align = item[:9]
            x0, x1 = X(c1) + (4 if align == "l" else 0), X(c2 + 1) - (4 if align == "r" else 0)
            if link is None:
                lay.text(x0, Y(r1), x1, Y(r2 + 1), text=item[9], size=size, bold=bold, color=color, align=align)
            else:
                lay.text(x0, Y(r1), x1, Y(r2 + 1), textlink=link, size=size, bold=bold, color=color, align=align)
        # budget slider on tile 3
        sl = BarChart()
        sl.type = "bar"
        sl.grouping = "stacked"
        sl.overlap = 100
        sl.gapWidth = 0
        sl.add_data(Reference(ws, min_col=E0 + 14, max_col=E0 + 15, min_row=4, max_row=4), titles_from_data=False)
        sl.series[0].graphicalProperties.solidFill = NAVY
        sl.series[1].graphicalProperties.solidFill = "BFE7E1"
        for s in sl.series:
            s.graphicalProperties.line.noFill = True
        clean_chart(sl, legend=False)
        sl.x_axis.delete = True
        sl.y_axis.delete = True
        sl.y_axis.majorGridlines = None
        sl.y_axis.scaling.min = 0
        sl.y_axis.scaling.max = 1
        place_chart(ws, sl, TILES[2][0] + 4, 3, TILES[2][1] - 1, 3, pad=7)
        self.layer = lay
