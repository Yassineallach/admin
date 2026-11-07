"""All-in-One Dashboard v2 — teal "floating cards" design.

Two layers:
  1. CELL LAYER (all editions): every number, list and control lives in cells; charts are openpyxl charts.
     In Google Sheets (which ignores Excel shapes) this layer *is* the dashboard: flat cards on a mint canvas.
  2. SHAPE LAYER (Excel edition only, see drawing_inject.py): rounded white cards with soft teal shadows, a gradient
     highlight tile, the dark sidebar with clickable icons, and text boxes linked live to the cell layer.

Grid: columns 1-66 are 20 px wide, so layout coordinates are simple pixel maths. Columns from 70 on hold the
"dashboard engine" (helper formulas + chart data).
"""
from __future__ import annotations

from openpyxl.chart import BarChart, DoughnutChart, LineChart, RadarChart, Reference
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.data_source import NumFmt
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
from common import (BG, BORDER, DANGER, DARK, FMT_PCT, FMT_SDATE, INFO, LAVENDER, LIGHT_GRAY, MED_GRAY, MIDNIGHT, NAVY,
                    SECONDARY, SOFT_BLUE, SOFT_TEAL, TEAL, BLUE, WARNING, WHITE, add_list_dv, cf_formula, fill, place_chart)
from drawing_inject import Layer, col_px_list, row_px_list

COLW = 2.86            # -> 20 px
NCOLS = 66
E0 = 70                # engine start column (BR)
MINT = "A6DCD5"
GREY_BAR = "B4C1C0"
TASK_COLS = ["2F6FAA", "0F6E68", "CF3A43", "EE8A3A", "1FA99C"]

# row heights in px (converted to pt = px * 0.75)
ROWS = {1: 34, 2: 12, 3: 20, 4: 24, 5: 26, 6: 22, 7: 18, 8: 18, 9: 28, 22: 14, 23: 18, 24: 28,
        25: 18, 26: 24, 27: 10, 28: 24, 29: 10, 30: 24, 31: 24, 32: 24, 33: 24, 34: 10, 35: 18, 36: 20, 37: 14, 38: 18,
        39: 28, 40: 20, 49: 14, 50: 18}
for r in range(10, 22):
    ROWS[r] = 20
for r in range(41, 49):
    ROWS[r] = 22
LAST_ROW = 50

TILES = [(5, 18), (20, 33), (35, 48), (50, 63)]
LEFT, MID, RIGHT = (5, 26), (28, 44), (46, 63)
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


class DashV2:
    def __init__(self, b, ctx):
        self.b, self.T = b, b.T
        self.ws = b.ws[ctx["S_DASH"]]
        self.c = ctx
        self.excel = b.ed == "excel"
        self.layer = None

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
        """Cell-layer card: white block (the Excel shape layer draws the rounded/shadowed version on top)."""
        edge = Side(style="thin", color=BORDER)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                cell = self.ws.cell(row=r, column=c)
                cell.fill = fill(WHITE)
                cell.border = Border(left=edge if c == c1 else None, right=edge if c == c2 else None,
                                     top=edge if r == r1 else None, bottom=edge if r == r2 else None)

    # ---------------------------------------------------------------- build
    def build(self):
        ws = self.ws
        ws.sheet_view.showGridLines = False
        ws.sheet_view.showRowColHeaders = False
        ws.sheet_view.zoomScale = 100
        for c in range(1, NCOLS + 1):
            ws.column_dimensions[L(c)].width = COLW
        for c in range(NCOLS + 1, E0):
            ws.column_dimensions[L(c)].width = 2.86
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
        self.band1()
        self.band2()
        self.band3()
        if self.excel:
            self.shapes()
        ws.freeze_panes = None

    # ---------------------------------------------------------------- engine (period + series)
    def engine(self):
        c = self.c
        VT, PB, POV, SS, SC, TODAY, DONE = c["VT"], c["PB"], c["POV"], c["SS"], c["SC"], c["TODAY"], c["DONE"]
        ws = self.ws
        ws.cell(row=1, column=E0, value="⚙ DASHBOARD ENGINE — helper formulas and chart data (do not edit)").font = self.F(9, True, SECONDARY)
        # period inputs live on the dashboard (selector card); engine converts them
        self.in_year, self.in_from, self.in_to = "$AT$26", "$AZ$26", "$BF$26"
        e = {}
        e["today"] = self.eng(0, 3, f"={TODAY}", FMT_SDATE)
        self.eng(1, 3, "today")
        e["m_from"] = self.eng(0, 4, f'=IFERROR(MATCH({self.in_from},{SS("G")},0),1)')
        e["m_to"] = self.eng(0, 5, f'=IFERROR(MATCH({self.in_to},{SS("G")},0),12)')
        e["lo"] = self.eng(0, 6, f'=MIN({e["m_from"]},{e["m_to"]})')
        e["hi"] = self.eng(0, 7, f'=MAX({e["m_from"]},{e["m_to"]})')
        e["start"] = self.eng(0, 8, f'=DATE({self.in_year},{e["lo"]},1)', FMT_SDATE)
        e["end"] = self.eng(0, 9, f'=EDATE(DATE({self.in_year},{e["hi"]},1),1)', FMT_SDATE)
        for i, lab in enumerate(["from #", "to #", "lo", "hi", "period start", "period end (excl.)"]):
            self.eng(1, 4 + i, lab)
        rng = lambda col: f'{VT(col)},">="&{e["start"]},{VT(col)},"<"&{e["end"]}'
        e["tasks_p"] = self.eng(0, 11, f'=COUNTIFS({VT("C")},"?*",{rng("I")})')
        e["done_p"] = self.eng(0, 12, f'=COUNTIFS({VT("C")},"?*",{rng("I")},{VT("K")},{DONE})')
        e["open_p"] = self.eng(0, 13, f'={e["tasks_p"]}-{e["done_p"]}')
        e["compl_p"] = self.eng(0, 14, f'=IF({e["tasks_p"]}=0,0,{e["done_p"]}/{e["tasks_p"]})', FMT_PCT)
        e["active_proj"] = self.eng(0, 15, f'=COUNTIF({POV("J")},{c["PSTAT"][1]})+COUNTIF({POV("J")},{c["PSTAT"][2]})')
        e["spent_p"] = self.eng(0, 16, f'=SUMIFS({PB("F")},{PB("I")},">="&{e["start"]},{PB("I")},"<"&{e["end"]})')
        e["planned"] = self.eng(0, 17, f'=SUM({PB("E")})')
        e["actual"] = self.eng(0, 18, f'=SUM({PB("F")})')
        e["used"] = self.eng(0, 19, f'=IF({e["planned"]}=0,0,{e["actual"]}/{e["planned"]})', FMT_PCT)
        e["overdue"] = self.eng(0, 20, f'=COUNTIF({VT("P")},"Overdue")')
        for i, lab in enumerate(["tasks due in period", "done in period", "open in period", "completion", "active projects",
                                 "spent in period", "planned (all)", "actual (all)", "budget used", "overdue (all)"]):
            self.eng(1, 11 + i, lab)
        # monthly series (row 24..35): month, due in-range, due other, completed, planned, actual
        heads = ["Month", "In period", "Other months", "Completed", "Planned", "Actual"]
        for j, h in enumerate(heads):
            self.eng(3 + j, 23, h)
        for m in range(12):
            r = 24 + m
            mc = f"${L(E0 + 3)}{r}"
            self.eng(3, r, f"=DATE({self.in_year},{m + 1},1)", "mmm")
            due = f'COUNTIFS({VT("C")},"?*",{VT("I")},">="&{mc},{VT("I")},"<"&EDATE({mc},1))'
            inr = f'AND({m + 1}>={e["lo"]},{m + 1}<={e["hi"]})'
            self.eng(4, r, f"=IF({inr},{due},0)")
            self.eng(5, r, f"=IF({inr},0,{due})")
            self.eng(6, r, f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&{mc},{VT("I")},"<"&EDATE({mc},1),{VT("K")},{DONE})')
            self.eng(7, r, f'=SUMIFS({PB("E")},{PB("I")},">="&{mc},{PB("I")},"<"&EDATE({mc},1))')
            self.eng(8, r, f'=SUMIFS({PB("F")},{PB("I")},">="&{mc},{PB("I")},"<"&EDATE({mc},1))')
        e["month_first_row"] = 24
        # donut (row 40-41)
        self.eng(3, 39, "Donut")
        self.eng(3, 40, "Done")
        self.eng(3, 41, "Open")
        self.eng(4, 40, f"={e['done_p']}")
        self.eng(4, 41, f"=IF({e['tasks_p']}=0,1,{e['open_p']})")
        # project progress bars (rows 44-48): name, track, progress
        self.eng(3, 43, "Project")
        self.eng(4, 43, "Track")
        self.eng(5, 43, "Progress")
        for i in range(5):
            r = 44 + i
            k = 5 - i   # reversed so project 1 is drawn at the top
            idx = f'MATCH({k},{POV("U")},0)'
            self.eng(3, r, f'=IFERROR(INDEX({POV("C")},{idx}),"—")')
            self.eng(4, r, "=1")
            self.eng(5, r, f'=IFERROR(N(INDEX({POV("K")},{idx})),0)')
        # radar: tasks by category (rows 52-59): category, open, done
        self.eng(3, 51, "Category")
        self.eng(4, 51, "Open")
        self.eng(5, 51, "Done")
        for i in range(8):
            r = 52 + i
            cat = f"INDEX({c['SL']('C')},{i + 1})"
            self.eng(3, r, f'=IF({cat}="","—",{cat})')
            self.eng(4, r, f'=COUNTIFS({VT("F")},{L(E0 + 3)}{r},{VT("C")},"?*",{VT("K")},"<>"&{DONE})')
            self.eng(5, r, f'=COUNTIFS({VT("F")},{L(E0 + 3)}{r},{VT("C")},"?*",{VT("K")},{DONE})')
        # team workload (rows 63-69)
        self.eng(3, 62, "Member")
        self.eng(4, 62, "Open")
        self.eng(5, 62, "Overdue")
        for i in range(7):
            r = 63 + i
            nm = f"INDEX({c['SL']('G')},{i + 1})"
            self.eng(3, r, f'=IF({nm}="","",{nm})')
            self.eng(4, r, f'=IF({L(E0 + 3)}{r}="",0,COUNTIFS({VT("G")},{L(E0 + 3)}{r},{VT("C")},"?*",{VT("K")},"<>"&{DONE}))')
            self.eng(5, r, f'=IF({L(E0 + 3)}{r}="",0,COUNTIFS({VT("G")},{L(E0 + 3)}{r},{VT("P")},"Overdue"))')
        # list indexes (rows 41-48 col 10/11)
        for k in range(1, 9):
            r = 40 + k
            self.eng(10, r, f'=IFERROR(MATCH(SMALL({VT("T")},{k}),{VT("T")},0),"")')
            self.eng(11, r, f'=IFERROR(MATCH(SMALL({VT("U")},{k}),{VT("U")},0),"")')
        self.eng(10, 40, "idx upcoming")
        self.eng(11, 40, "idx overdue")
        self.e = e
        DASH.update({k: v.replace("$", "") for k, v in e.items() if isinstance(v, str)})
        DASH["month_first"] = f"{L(E0 + 3)}24"
        DASH["proj_first"] = f"{L(E0 + 3)}44"
        DASH["radar_first"] = f"{L(E0 + 3)}52"
        DASH["team_first"] = f"{L(E0 + 3)}63"

    # ---------------------------------------------------------------- sidebar + header
    NAV = [("All-in-One Dashboard", "bar_chart", "Home"), ("Setup", "gear", "Setup"), ("Monthly Calendar", "calendar", "Month"),
           ("Weekly Calendar", "calendar", "Week"), ("Project Overview", "book", "Projects"), ("Project Manager", "people", "Manager"),
           ("Project Budget", "money", "Budget"), ("Variable Tasks", "clipboard", "Tasks"), ("Recurring Tasks", "donut", "Repeat"),
           ("Task Schedule", "calendar", "Schedule"), ("Task Filter", "filter", "Filter"), ("Decision Matrix", "scale", "Decide"),
           ("Kanban Board", "kanban", "Kanban"), ("Gantt Chart", "gantt", "Gantt"), ("Instructions", "book", "Help")]

    def sidebar_cells(self):
        for r in range(1, LAST_ROW + 1):
            for c in range(1, 4):
                self.ws.cell(row=r, column=c).fill = fill(NAVY)
        for i, (tab, _icon, short) in enumerate(self.NAV):
            r = 3 + i * 3
            self.put(1, r, 3, r + 1, f'=HYPERLINK("#{self.c["quote"](tab)}!A1","{short}")',
                     self.F(8, True, WHITE if i else "A9D8D1"), Alignment(horizontal="center", vertical="center"))

    def header(self):
        c, TODAY = self.c, self.c["TODAY"]
        self.put(5, 1, 30, 1, "Project Command Center", self.F(15, True, NAVY), Alignment(vertical="center"))
        demo = '"DEMO DATA  ·  "&' if self.b.demo else ""
        self.put(40, 1, 63, 1, f'={demo}TEXT({TODAY},"dddd")&", "&TEXT({TODAY},"mmmm d, yyyy")', self.F(10, False, SECONDARY),
                 Alignment(horizontal="right", vertical="center"))
        DASH["header_date"] = "AN1"

    # ---------------------------------------------------------------- KPI tiles (cell layer)
    def kpis(self):
        e, cur = self.e, "CurrencySymbol"
        tiles = [
            ("Tasks due", f"={e['tasks_p']}", "#,##0", f'={e["active_proj"]}&" active projects"', False, "tile_tasks"),
            ("Completion", f"={e['compl_p']}", FMT_PCT, f'={e["done_p"]}&" of "&{e["tasks_p"]}&" done"', True, "tile_completion"),
            ('="Spent  ("&TRIM(CurrencySymbol)&")"', f'=TRIM({cur})&TEXT({e["spent_p"]},"#,##0")', None,
             '="in the selected period"', False, "tile_spent"),
            ("Budget used", f"={e['used']}", FMT_PCT, f'=TEXT({e["actual"]},"#,##0")&" of "&TEXT({e["planned"]},"#,##0")', False, "tile_budget"),
        ]
        self.tile_cells = []
        for (c1, c2), (label, val, nf, sub, hl, key) in zip(TILES, tiles):
            bg = fill("17A397") if hl else fill(WHITE)
            fg = WHITE if hl else NAVY
            self.panel(c1, 3, c2, 7)
            for r in range(3, 8):
                for cc in range(c1, c2 + 1):
                    self.ws.cell(row=r, column=cc).fill = bg
            lab = self.put(c1, 7, c2, 7, label, self.F(9, True, fg), Alignment(horizontal="center", vertical="center"))
            v = self.put(c1, 4, c2, 5, val, self.F(22, True, fg), Alignment(horizontal="center", vertical="center"), nf)
            s = self.put(c1, 6, c2, 6, sub, self.F(8, False, "D9F2EE" if hl else SECONDARY), Alignment(horizontal="center", vertical="center"))
            DASH[key] = f"{L(c1)}4"
            DASH[key + "_sub"] = f"{L(c1)}6"
            self.tile_cells.append(((c1, c2), f"${L(c1)}$4", f"${L(c1)}$6", f"${L(c1)}$7", hl))
        # slider mini-chart data (budget used) for tile 4
        self.eng(14, 3, "Slider")
        self.eng(14, 4, f"=MIN(1,{e['used']})")
        self.eng(15, 4, f"=MAX(0,1-{e['used']})")

    # ---------------------------------------------------------------- band 1
    def band1(self):
        ws, E = self.ws, E0
        self.panel(LEFT[0], 9, MID[1], 37)
        self.panel(RIGHT[0], 9, RIGHT[1], 22)
        for (c1, c2), title in ((LEFT, "Tasks due by month"), (MID, "Completion in period"), (RIGHT, "Project progress")):
            self.put(c1, 9, c2, 9, title, self.F(11, True, NAVY), Alignment(horizontal="center", vertical="center"))
        # combo: bars (period highlight / other) + smooth completed line
        bar = BarChart()
        bar.type = "col"
        bar.grouping = "clustered"
        bar.overlap = 100
        bar.gapWidth = 45
        bar.add_data(Reference(ws, min_col=E + 4, max_col=E + 5, min_row=23, max_row=35), titles_from_data=True)
        bar.set_categories(Reference(ws, min_col=E + 3, min_row=24, max_row=35))
        bar.series[0].graphicalProperties.solidFill = MIDNIGHT
        bar.series[1].graphicalProperties.solidFill = GREY_BAR
        for s in bar.series:
            s.graphicalProperties.line.noFill = True
        line = LineChart()
        line.add_data(Reference(ws, min_col=E + 6, min_row=23, max_row=35), titles_from_data=True)
        s = line.series[0]
        s.smooth = True
        s.graphicalProperties.line.solidFill = "2F7E9E"
        s.graphicalProperties.line.width = 28575
        s.marker = Marker(symbol="circle", size=6)
        s.marker.graphicalProperties = GraphicalProperties(solidFill=WHITE, ln=LineProperties(solidFill="2F7E9E", w=15875))
        clean_chart(bar)
        bar += line
        place_chart(ws, bar, LEFT[0], 10, LEFT[1], 21)
        # donut
        d = DoughnutChart(holeSize=68)
        d.add_data(Reference(ws, min_col=E + 4, min_row=40, max_row=41), titles_from_data=False)
        d.set_categories(Reference(ws, min_col=E + 3, min_row=40, max_row=41))
        for i, colr in enumerate((NAVY, "8ED6CC")):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.solidFill = WHITE
            d.series[0].dPt.append(pt)
        clean_chart(d, legend=False, axes=False)
        if not self.excel:   # Sheets: no floating label in the hole, so show it as the chart title
            d.title = "Completion"
        place_chart(ws, d, MID[0], 10, MID[1], 21)
        DASH["donut_first"] = f"{L(E + 4)}40"
        # project progress bars
        pb = BarChart()
        pb.type = "bar"
        pb.overlap = 100
        pb.gapWidth = 80
        pb.add_data(Reference(ws, min_col=E + 4, max_col=E + 5, min_row=43, max_row=48), titles_from_data=True)
        pb.set_categories(Reference(ws, min_col=E + 3, min_row=44, max_row=48))
        pb.series[0].graphicalProperties.solidFill = "E2F2EF"
        pb.series[0].graphicalProperties.line.noFill = True
        pb.series[1].graphicalProperties.line.noFill = True
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
        place_chart(ws, pb, RIGHT[0], 10, RIGHT[1], 21)

    # ---------------------------------------------------------------- band 2 (budget, radar, period selector)
    def band2(self):
        ws, E = self.ws, E0
        for (c1, c2), title in ((LEFT, "Budget performance by month"), (MID, "Open vs done by category")):
            self.put(c1, 24, c2, 24, title, self.F(11, True, NAVY), Alignment(horizontal="center", vertical="center"))
        b = BarChart()
        b.type = "col"
        b.overlap = 100
        b.gapWidth = 35
        b.add_data(Reference(ws, min_col=E + 7, max_col=E + 8, min_row=23, max_row=35), titles_from_data=True)
        b.set_categories(Reference(ws, min_col=E + 3, min_row=24, max_row=35))
        b.series[0].graphicalProperties.solidFill = "7FD1C6"
        b.series[1].graphicalProperties.solidFill = MIDNIGHT
        for s in b.series:
            s.graphicalProperties.line.noFill = True
        clean_chart(b)
        b.y_axis.numFmt = NumFmt(formatCode='#,##0,"K"', sourceLinked=False)
        place_chart(ws, b, LEFT[0], 25, LEFT[1], 36)
        r = RadarChart()
        r.type = "marker"
        r.add_data(Reference(ws, min_col=E + 4, max_col=E + 5, min_row=51, max_row=59), titles_from_data=True)
        r.set_categories(Reference(ws, min_col=E + 3, min_row=52, max_row=59))
        for s, colr in zip(r.series, ("17A397", "B06FD6")):
            s.graphicalProperties.line.solidFill = colr
            s.graphicalProperties.line.width = 22225
            s.marker = Marker(symbol="circle", size=5)
            s.marker.graphicalProperties = GraphicalProperties(solidFill=colr, ln=LineProperties(solidFill=colr))
        r.title = None
        r.graphical_properties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
        r.plot_area.graphicalProperties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
        r.legend.position = "b"
        r.legend.txPr = _rich(800, SECONDARY)
        r.y_axis.delete = True
        r.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill="D5E5E2", w=6350)))
        r.x_axis.txPr = _rich(750, SECONDARY)
        place_chart(ws, r, MID[0], 25, MID[1], 36)
        self.selector()

    def selector(self):
        ws, c = self.ws, self.c
        c1, c2 = RIGHT
        self.put(c1, 24, c2, 24, "Period", self.F(11, True, NAVY), Alignment(horizontal="left", vertical="center"))
        thick = Side(style="thick", color=BG)
        box = Border(left=thick, right=thick, top=thick, bottom=thick)
        spans = [(46, 51, "YEAR"), (52, 57, "FROM"), (58, 63, "TO")]
        defaults = [f"={c['SC']('C', 18)}",
                    f'=INDEX({c["SS"]("G")},INT((MONTH({c["TODAY"]})-1)/3)*3+1)',
                    f'=INDEX({c["SS"]("G")},MONTH({c["TODAY"]}))']
        for (a, b_, lab), dflt in zip(spans, defaults):
            self.put(a, 25, b_, 25, lab, self.F(8, True, SECONDARY), Alignment(horizontal="center", vertical="bottom"))
            self.put(a, 26, b_, 26, dflt, self.F(10, True, NAVY), Alignment(horizontal="center", vertical="center"),
                     f=fill(SOFT_BLUE), border=box)
            self.b.unlocked[c["S_DASH"]].append(f"{L(a)}26:{L(b_)}26")
        add_list_dv(ws, "AT26", c["SS"]("H"))
        add_list_dv(ws, "AZ26", c["SS"]("G"))
        add_list_dv(ws, "BF26", c["SS"]("G"))
        DASH.update(year="AT26", from_="AZ26", to="BF26")
        # year buttons (selected year highlighted)
        for i, (a, b_) in enumerate(((47, 50), (51, 54), (55, 58), (59, 62))):
            cell = self.put(a, 28, b_, 28, f"={self.in_year}+{i - 1}", self.F(9, True, NAVY), Alignment(horizontal="center", vertical="center"),
                            "0", fill(WHITE), box)
            ws.conditional_formatting.add(f"{L(a)}28:{L(b_)}28", FormulaRule(formula=[f"{L(a)}28={self.in_year}"],
                                                                                fill=fill("17A397"), font=Font(color=WHITE, bold=True)))
        # month grid
        months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
        lo, hi = self.e["lo"], self.e["hi"]
        for i, m in enumerate(months):
            r = 30 + i // 3
            a = 46 + (i % 3) * 6
            self.put(a, r, a + 5, r, m, self.F(9, True, NAVY), Alignment(horizontal="center", vertical="center"), None, fill(WHITE), box)
            ws.conditional_formatting.add(f"{L(a)}{r}:{L(a + 5)}{r}", FormulaRule(
                formula=[f"AND({i + 1}>={lo},{i + 1}<={hi})"], fill=fill("17A397"), font=Font(color=WHITE, bold=True)))
        self.put(c1, 35, c2, 35, "Pick a year and month range with the ▾ cells above.", self.F(8, False, SECONDARY, italic=True),
                 Alignment(horizontal="center", vertical="center"))

    # ---------------------------------------------------------------- band 3 (lists + team chart)
    def band3(self):
        ws, c, E = self.ws, self.c, E0
        VT = c["VT"]
        self.panel(LEFT[0], 39, LEFT[1], 49)
        self.panel(MID[0], 39, MID[1], 49)
        self.panel(RIGHT[0], 39, RIGHT[1], 49)
        for (c1, c2), title in ((LEFT, "Upcoming deadlines"), (MID, "Overdue tasks"), (RIGHT, "Team workload")):
            self.put(c1, 39, c2, 39, title, self.F(11, True, NAVY), Alignment(horizontal="left", vertical="center", indent=1))
        heads = [((6, 20), "TASK"), ((21, 25), "DUE"), ((29, 39), "TASK"), ((40, 43), "LATE")]
        for (a, b_), h in heads:
            self.put(a, 40, b_, 40, h, self.F(8, True, SECONDARY),
                     Alignment(horizontal="left" if h == "TASK" else "right", vertical="center"))
        up, od = f"${L(E + 10)}$", f"${L(E + 11)}$"
        self.list_cells = []
        for k in range(8):
            r = 41 + k
            i1, i2 = f"{up}{r}", f"{od}{r}"
            first_up = '"No upcoming deadlines"' if k == 0 else '""'
            first_od = '"No overdue tasks"' if k == 0 else '""'
            self.put(6, r, 20, r, f'=IF({i1}="",{first_up},INDEX({VT("C")},{i1})&"")', self.F(9, False, DARK), Alignment(vertical="center"))
            self.put(21, r, 25, r, f'=IF({i1}="","",TEXT(INDEX({VT("I")},{i1}),"mmm d"))', self.F(9, True, MIDNIGHT),
                     Alignment(horizontal="right", vertical="center"))
            self.put(29, r, 39, r, f'=IF({i2}="",{first_od},INDEX({VT("C")},{i2})&"")', self.F(9, False, DARK), Alignment(vertical="center"))
            self.put(40, r, 43, r, f'=IF({i2}="","",-INDEX({VT("Q")},{i2})&" d")', self.F(9, True, DANGER),
                     Alignment(horizontal="right", vertical="center"))
            self.list_cells.append((r, f"$F${r}", f"$U${r}", f"$AC${r}", f"$AN${r}"))
        DASH.update(up_first="F41", up_due_first="U41", od_first="AC41", od_late_first="AN41")
        t = BarChart()
        t.type = "col"
        t.gapWidth = 60
        t.add_data(Reference(ws, min_col=E + 4, max_col=E + 5, min_row=62, max_row=69), titles_from_data=True)
        t.set_categories(Reference(ws, min_col=E + 3, min_row=63, max_row=69))
        t.series[0].graphicalProperties.solidFill = "17A397"
        t.series[1].graphicalProperties.solidFill = WARNING
        for s in t.series:
            s.graphicalProperties.line.noFill = True
        clean_chart(t)
        place_chart(ws, t, RIGHT[0], 40, RIGHT[1], 48)

    # ---------------------------------------------------------------- Excel shape layer
    def shapes(self):
        ws = self.ws
        lay = Layer(col_px_list(ws, NCOLS + 2), row_px_list(ws, LAST_ROW + 2), font=self.T.font_name)
        X, Y = lay.x, lay.y
        shadow = ("0F6E68", 16, 18, 4)
        # sidebar
        lay.shape(-30 + 30, 0, X(4) - 6, Y(LAST_ROW + 1), radius=0.35, fill=None,
                  grad=([(0, "0F6E68"), (100, "0B4F4C")], 90), name="Sidebar")
        for i, (tab, icon, _short) in enumerate(self.NAV):
            cy = 62 + i * 62
            if i == 0:
                lay.shape(X(1) + 9, cy - 21, X(1) + 51, cy + 21, geom="ellipse", fill="E1F3F0", name="Active")
                png = icons.ICONS[icon](c="0F6E68", size=64)
            else:
                png = icons.ICONS[icon](c="FFFFFF", size=64)
            lay.picture(X(1) + 16, cy - 14, X(1) + 44, cy + 14, png, link_sheet=None if i == 0 else tab, tooltip=tab)
        # KPI tiles
        for ((c1, c2), v, sub, lab, hl) in self.tile_cells:
            x0, x1, y0, y1 = X(c1), X(c2 + 1), Y(3), Y(8)
            if hl:
                lay.shape(x0, y0 - 6, x1, y1 + 6, radius=0.16, fill=None, grad=([(0, "1EB5A6"), (100, "86DDD3")], 90),
                          shadow=("17A397", 45, 26, 6), name="Highlight")
            else:
                lay.shape(x0, y0, x1, y1, radius=0.14, fill=WHITE, shadow=shadow, name="Tile")
            fg = WHITE if hl else NAVY
            lay.text(x0 + 70, y0 + 14, x1 - 12, y0 + 58, textlink=v, size=24 if not hl else 26, bold=not hl, color=fg, align="c")
            lay.text(x0 + 70, y0 + 58, x1 - 12, y0 + 76, textlink=sub, size=9, color="E3F7F4" if hl else SECONDARY, align="c")
            lay.text(x0 + 10, y1 - 30, x1 - 10, y1 - 8, textlink=lab, size=11, color=fg, align="c")
        t1, t2 = self.tile_cells[0][0], self.tile_cells[1][0]
        lay.picture(X(t1[0]) + 18, Y(3) + 24, X(t1[0]) + 62, Y(3) + 68, icons.people(c="0F6E68", size=96))
        lay.picture(X(t2[0]) + 16, Y(3) + 20, X(t2[0]) + 64, Y(3) + 68, icons.donut(c="E1F3F0", size=96, accent="0B4F4C"))
        lay.picture(X(TILES[2][0]) + 18, Y(3) + 26, X(TILES[2][0]) + 58, Y(3) + 66, icons.money(c="0F6E68", size=96))
        lay.picture(X(TILES[3][0]) + 18, Y(3) + 26, X(TILES[3][0]) + 58, Y(3) + 66, icons.bar_chart(c="0F6E68", size=96))
        # panels behind charts / lists
        lay.shape(X(LEFT[0]), Y(9), X(MID[1] + 1), Y(38), radius=0.04, fill=WHITE, shadow=shadow, name="Panel")
        lay.shape(X(RIGHT[0]), Y(9), X(RIGHT[1] + 1), Y(23), radius=0.07, fill=WHITE, shadow=shadow, name="Panel")
        for (c1, c2) in (LEFT, MID, RIGHT):
            lay.shape(X(c1), Y(39), X(c2 + 1), Y(50), radius=0.07, fill=WHITE, shadow=shadow, name="Panel")
        # titles (the panel covers the title cells)
        for (c1, c2), title, r in ((LEFT, "Tasks due by month", 9), (MID, "Completion in period", 9), (RIGHT, "Project progress", 9),
                                   (LEFT, "Budget performance by month", 24), (MID, "Open vs done by category", 24)):
            lay.text(X(c1), Y(r) + 4, X(c2 + 1), Y(r + 1), text=title, size=12, color=NAVY, align="c")
        for (c1, c2), title in ((LEFT, "Upcoming deadlines"), (MID, "Overdue tasks"), (RIGHT, "Team workload")):
            lay.text(X(c1) + 16, Y(39) + 4, X(c2 + 1) - 8, Y(40), text=title, size=12, color=NAVY, align="l")
        # donut centre label
        cx, cy = (X(MID[0]) + X(MID[1] + 1)) / 2, (Y(10) + Y(22)) / 2
        lay.text(cx - 70, cy - 18, cx + 70, cy + 18, textlink=self.e["compl_p"], size=22, color=NAVY, align="c")
        # list rows + headers
        for (a, b_), h in (((6, 20), "TASK"), ((21, 25), "DUE"), ((29, 39), "TASK"), ((40, 43), "LATE")):
            lay.text(X(a), Y(40), X(b_ + 1), Y(41), text=h, size=8, bold=True, color=SECONDARY, align="l" if h == "TASK" else "r")
        for (r, n1, d1, n2, d2) in self.list_cells:
            lay.text(X(6), Y(r), X(21) - 4, Y(r + 1), textlink=n1, size=10, color=DARK)
            lay.text(X(21), Y(r), X(26), Y(r + 1), textlink=d1, size=10, bold=True, color=MIDNIGHT, align="r")
            lay.text(X(29), Y(r), X(40) - 4, Y(r + 1), textlink=n2, size=10, color=DARK)
            lay.text(X(40), Y(r), X(44), Y(r + 1), textlink=d2, size=10, bold=True, color=DANGER, align="r")
        # budget slider (tile 4): a tiny chart drawn above the tile
        sl = BarChart()
        sl.type = "bar"
        sl.grouping = "stacked"
        sl.overlap = 100
        sl.gapWidth = 0
        sl.add_data(Reference(ws, min_col=E0 + 14, max_col=E0 + 15, min_row=4, max_row=4), titles_from_data=False, from_rows=False)
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
        place_chart(ws, sl, TILES[3][0] + 4, 3, TILES[3][1] - 1, 3, pad=7)
        self.layer = lay
