"""All-in-One Dashboard for the Ultimate Project Manager — premium card layout.

Grid (all widths fixed so nothing can drift):
  A gutter | B C D card | E gutter | F G H card | I gutter | J K L card | M gutter | N O P card | Q gutter | R..X right panel | Y gutter
Rows are organised in horizontal bands; every band's row heights are set explicitly.
Charts are pinned with two-cell anchors computed from the real column widths / row heights, so each chart
sits inside its card with 6 px padding and cannot overlap anything.
Everything right of column Z is the "dashboard engine" (chart data and helper formulas).
"""
from __future__ import annotations

from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.axis import ChartLines
from openpyxl.chart.data_source import NumFmt
from openpyxl.chart.layout import Layout, ManualLayout
from openpyxl.chart.series import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.chart.text import RichText
from openpyxl.drawing.line import LineProperties
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, TwoCellAnchor
from openpyxl.drawing.text import CharacterProperties, Paragraph, ParagraphProperties
from openpyxl.styles import Alignment, Border, Side
from openpyxl.utils import get_column_letter as L

from common import (BG, BLUE, BORDER, DANGER, DANGER_BG, DARK, FMT_PCT, FMT_SDATE, INFO, INFO_BG, LAVENDER, LIGHT_GRAY,
                    MED_GRAY, MIDNIGHT, NAVY, SECONDARY, SOFT_BLUE, SOFT_LAV, SOFT_TEAL, SUCCESS, SUCCESS_BG, TEAL, WARNING,
                    WARNING_BG, WHITE, cf_formula, fill, paint)

# ------------------------------------------------------------------ grid
CARDS = [(2, 4), (6, 8), (10, 12), (14, 16)]      # four KPI slots in the centre
HALF_L, HALF_R, CENTER, RIGHT = (2, 8), (10, 16), (2, 16), (18, 24)
WIDTHS = {1: 2.4, 5: 2.4, 9: 2.4, 13: 2.4, 17: 2.4, 25: 2.4, 26: 2.4}
for a, b in CARDS:
    for c in range(a, b + 1):
        WIDTHS[c] = 9.2
for c in range(18, 25):
    WIDTHS[c] = 7.6
LAST_ROW = 93
ENGINE_COL = 28   # AB

FMT_COMPACT = '[>=1000000]#,##0.0,,"M";[>=1000]#,##0.0,"K";#,##0'
SOFT = {BLUE: SOFT_BLUE, TEAL: SOFT_TEAL, LAVENDER: SOFT_LAV, DANGER: DANGER_BG, WARNING: WARNING_BG, NAVY: "E4E8EF",
        SUCCESS: SUCCESS_BG, INFO: INFO_BG, MIDNIGHT: "E4E8EF"}

# band rows: (pad, label, value, sub, bar)
BANDS = [(8, 9, 10, 11, 12), (14, 15, 16, 17, 18), (20, 21, 22, 23, 24)]
CH = dict(title=26, top=27, bottom=39, pad=40)            # charts + calendar band
B2 = dict(title=42, first=43, last=54)                     # charts + priority band
LST = dict(title=56, head=57, first=58, n=8, pad=66)       # lists band
TBL = dict(title=68, head=69, first=70, n=10, pad=80)      # performance + team
LB = dict(title=82, head=83, first=84, n=8, pad=92)        # recent + status + deadlines

# public cell map (used by the validator)
DASH = {}


def compact(x, sign=False):
    """Locale-safe compact money text: 135700 -> 135.7K, -2500 -> -2.5K (works in Excel, Sheets, LibreOffice)."""
    plus = f'IF({x}>0,"+","")&' if sign else ""
    return (f'{plus}IF(ABS({x})>=1000000,TEXT({x}/1000000,"0.0")&"M",IF(ABS({x})>=1000,TEXT({x}/1000,"0.0")&"K",TEXT({x},"0")))')


def px_col(w):
    return int(w * 7 + 5)


def _rich(sz=800, color=SECONDARY, bold=False):
    cp = CharacterProperties(sz=sz, b=bold, solidFill=color)
    return RichText(p=[Paragraph(pPr=ParagraphProperties(defRPr=cp), endParaRPr=cp)])


def style_chart(ch, legend=True):
    ch.title = None
    ch.roundedCorners = False
    ch.graphical_properties = GraphicalProperties(solidFill=WHITE, ln=LineProperties(noFill=True))
    ch.plot_area.graphicalProperties = GraphicalProperties(noFill=True, ln=LineProperties(noFill=True))
    if legend:
        ch.legend.position = "t"
        ch.legend.overlay = False
        ch.legend.txPr = _rich(800, SECONDARY)
    else:
        ch.legend = None
    for ax in (getattr(ch, "x_axis", None), getattr(ch, "y_axis", None)):
        if ax is None:
            continue
        ax.delete = False
        ax.majorTickMark = "none"
        ax.minorTickMark = "none"
        ax.txPr = _rich(800, SECONDARY)
        ax.spPr = GraphicalProperties(ln=LineProperties(noFill=True))
    if hasattr(ch, "y_axis"):
        ch.y_axis.majorGridlines = ChartLines(spPr=GraphicalProperties(ln=LineProperties(solidFill=LIGHT_GRAY, w=6350)))
        ch.x_axis.majorGridlines = None
        ch.x_axis.spPr = GraphicalProperties(ln=LineProperties(solidFill=BORDER, w=6350))


class Dash:
    def __init__(self, b, S, VT, POV, PB, TS, SL, SS, SC, PSTAT, PRI, TODAY, DONE, P_DONE, TSTAT, ORDER, quote):
        self.b, self.ws, self.T = b, b.ws[S["DASH"]], b.T
        self.S, self.VT, self.POV, self.PB, self.TS, self.SL, self.SS, self.SC = S, VT, POV, PB, TS, SL, SS, SC
        self.PSTAT, self.PRI, self.TODAY, self.DONE, self.P_DONE, self.TSTAT, self.ORDER, self.quote = (
            PSTAT, PRI, TODAY, DONE, P_DONE, TSTAT, ORDER, quote)
        self.row_h = {}
        self.charts = []

    # -------------------------------------------------------------- primitives
    def F(self, *a, **k):
        return self.T.font(*a, **k)

    def h(self, r, pt):
        self.ws.row_dimensions[r].height = pt
        self.row_h[r] = pt

    def rng(self, c1, r1, c2=None, r2=None):
        c2 = c2 or c1
        r2 = r2 or r1
        return f"{L(c1)}{r1}:{L(c2)}{r2}"

    def put(self, c1, r1, c2, r2, value=None, font=None, align=None, numfmt=None, f=None):
        ws = self.ws
        if (c1, r1) != (c2, r2):
            ws.merge_cells(self.rng(c1, r1, c2, r2))
        cell = ws.cell(row=r1, column=c1)
        if value is not None:
            cell.value = value
        if font is not None:
            cell.font = font
        cell.alignment = align or Alignment(vertical="center", indent=1)
        if numfmt:
            cell.number_format = numfmt
        if f is not None:
            for rr in range(r1, r2 + 1):
                for cc in range(c1, c2 + 1):
                    ws.cell(row=rr, column=cc).fill = f
        return cell

    def card(self, c1, r1, c2, r2, title=None, accent=None, right_text=None):
        ws = self.ws
        edge = Side(style="thin", color=BORDER)
        top = Side(style="medium", color=accent) if accent else edge
        for rr in range(r1, r2 + 1):
            for cc in range(c1, c2 + 1):
                cell = ws.cell(row=rr, column=cc)
                cell.fill = fill(WHITE)
                cell.border = Border(left=edge if cc == c1 else None, right=edge if cc == c2 else None,
                                     top=top if rr == r1 else None, bottom=edge if rr == r2 else None)
        if title:
            split = c2 - 2 if right_text else c2
            self.put(c1, r1, split, r1, title, self.F(10, True, NAVY))
            if right_text:
                self.put(split + 1, r1, c2, r1, right_text, self.F(8, False, SECONDARY),
                         Alignment(horizontal="right", vertical="center", indent=1))

    def bar(self, c1, r, c2, value_formula, color):
        """Slim progress bar: grey track + solid data bar, value hidden."""
        cell = self.put(c1, r, c2, r, value_formula, self.F(6, color=LIGHT_GRAY), Alignment(vertical="center"),
                        f=fill(LIGHT_GRAY))
        cell.number_format = ";;;"
        from openpyxl.formatting.rule import DataBarRule
        self.ws.conditional_formatting.add(
            self.rng(c1, r, c2, r),
            DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color=color, showValue=False,
                        minLength=0, maxLength=100))

    def place(self, ch, c1, r1, c2, r2, pad=6):
        """Pin a chart inside the cell box (c1,r1)-(c2,r2) with `pad` px padding."""
        emu = 9525
        a = TwoCellAnchor()
        a._from = AnchorMarker(col=c1 - 1, colOff=pad * emu, row=r1 - 1, rowOff=pad * emu)
        wpx = px_col(WIDTHS.get(c2, 8.43))
        hpx = int(self.row_h.get(r2, 15) * 96 / 72)
        a.to = AnchorMarker(col=c2 - 1, colOff=max(0, wpx - pad) * emu, row=r2 - 1, rowOff=max(0, hpx - pad) * emu)
        ch.anchor = a
        self.ws.add_chart(ch)
        self.charts.append((c1, r1, c2, r2))

    def eng(self, col, r, value, numfmt=None):
        c = self.ws.cell(row=r, column=col, value=value)
        c.font = self.F(8, color=SECONDARY)
        if numfmt:
            c.number_format = numfmt
        return c

    def status_txt(self, expr):
        lst = self.SL("E")
        return (f'IF({expr}="","",IFERROR(CHOOSE(MATCH({expr},{lst},0),"■","○","►","◆","✓","‖")&"  ","")&{expr})')

    # -------------------------------------------------------------- build
    def build(self):
        ws, T = self.ws, self.T
        ws.sheet_view.showGridLines = False
        ws.sheet_view.showRowColHeaders = False
        ws.sheet_view.zoomScale = 100
        for c, w in WIDTHS.items():
            ws.column_dimensions[L(c)].width = w
        for c in range(ENGINE_COL, ENGINE_COL + 40):
            ws.column_dimensions[L(c)].width = 11
        # canvas
        for r in range(1, LAST_ROW + 1):
            for c in range(1, 27):
                ws.cell(row=r, column=c).fill = fill(BG)
        heights = {1: 8, 4: 10, 5: 22, 6: 22, 7: 12, 13: 12, 19: 12, 25: 12, 41: 12, 55: 12, 67: 12, 81: 12, LAST_ROW: 16}
        for (p, lab, val, sub, br) in BANDS:
            heights.update({p: 8, lab: 18, val: 34, sub: 18, br: 7})
        heights.update({CH["title"]: 26, CH["pad"]: 8})
        for r in range(CH["top"], CH["bottom"] + 1):
            heights[r] = 20
        heights.update({B2["title"]: 26, 43: 10})
        for k in range(4):   # priority items: label 22, bar 9, spacer 18
            base = 44 + k * 3
            heights.update({base: 22, base + 1: 9, base + 2: 18})
        heights[54] = 10
        for band in (LST, TBL, LB):
            heights.update({band["title"]: 26, band["head"]: 20, band["pad"]: 8})
            for r in range(band["first"], band["first"] + band["n"]):
                heights[r] = 21
        for r, hgt in heights.items():
            self.h(r, hgt)
        self.hero()
        self.nav()
        self.engine_scalars()
        self.kpis()
        self.charts_band()
        self.calendar()
        self.band2()
        self.lists()
        self.table()
        self.last_band()
        ws.freeze_panes = "A8"

    # -------------------------------------------------------------- hero + nav
    def hero(self):
        ws, T = self.ws, self.T
        self.h(2, 34)
        self.h(3, 20)
        for r in (2, 3):
            for c in range(2, 25):
                ws.cell(row=r, column=c).fill = fill(NAVY)
        self.put(2, 2, 12, 2, "Project Command Center", self.F(20, True, WHITE), f=fill(NAVY))
        SC = self.SC
        self.put(2, 3, 12, 3, f'="Workspace: "&IF({SC("C", 12)}="","—",{SC("C", 12)})&"     ·     Owner: "&IF({SC("C", 11)}="","—",{SC("C", 11)})',
                 self.F(9, False, "B9C6DA"), f=fill(NAVY))
        self.put(18, 2, 24, 2, f"={self.TODAY}", self.F(12, True, WHITE), Alignment(horizontal="right", vertical="center", indent=1),
                 "dddd, mmmm d, yyyy", fill(NAVY))
        demo = '"DEMO DATA  ·  "&' if self.b.demo else ""
        self.put(14, 3, 24, 3, f'={demo}"Week "&WEEKNUM({self.TODAY},21)&"  ·  All figures update automatically"',
                 self.F(9, False, "B9C6DA"), Alignment(horizontal="right", vertical="center", indent=1), f=fill(NAVY))

    def nav(self):
        T = self.T
        slots = [(2, 4), (6, 8), (10, 12), (14, 16), (18, 19), (20, 21), (22, 24)]
        targets = [n for n in self.ORDER if n != self.S["DASH"]]   # 14 chips
        for i, n in enumerate(targets):
            r = 5 + i // 7
            c1, c2 = slots[i % 7]
            here = False
            cell = self.put(c1, r, c2, r, f'=HYPERLINK("#{self.quote(n)}!A1","{n}")',
                            self.F(8, True, WHITE if here else MIDNIGHT, underline=None), Alignment(horizontal="center", vertical="center"),
                            f=fill(BLUE if here else WHITE))
            edge = Side(style="thin", color=BORDER)
            for cc in range(c1, c2 + 1):
                self.ws.cell(row=r, column=cc).border = Border(top=edge, bottom=edge, left=edge if cc == c1 else None,
                                                               right=edge if cc == c2 else None)

    # -------------------------------------------------------------- engine scalars
    def engine_scalars(self):
        ws, E = self.ws, ENGINE_COL
        self.put(E, 1, E + 10, 1, "⚙ DASHBOARD ENGINE — chart data and helper formulas (do not edit)", self.F(9, True, SECONDARY),
                 f=fill(LIGHT_GRAY))
        T = self.TODAY
        labels = [("Today", f"={T}", FMT_SDATE), ("Week start", f"={T}-WEEKDAY({T},2)+1", FMT_SDATE),
                  ("Due-soon days", "=DueSoonDays", "0")]
        for i, (lab, fm, nf) in enumerate(labels):
            self.eng(E, 3 + i, lab)
            self.eng(E + 1, 3 + i, fm, nf)
        self.today, self.wk = "$AC$3", "$AC$4"
        DASH["engine_today"] = "AC3"

    # -------------------------------------------------------------- KPI cards
    def kpi(self, band, c1, c2, icon, label, value, numfmt, accent, sub=None, bar=None, sub_color=SECONDARY, key=None):
        p, lab, val, sub_r, br = band
        self.card(c1, p, c2, br, accent=accent)
        self.put(c1, val, c1, val, icon, self.F(18, True, accent), Alignment(horizontal="center", vertical="center"),
                 f=fill(SOFT.get(accent, SOFT_BLUE)))
        edge = Side(style="thick", color=WHITE)
        ic = self.ws.cell(row=val, column=c1)
        ic.border = Border(left=Side(style="medium", color=WHITE), top=Side(style="thin", color=WHITE), bottom=Side(style="thin", color=WHITE),
                           right=edge)
        self.put(c1, lab, c2, lab, label, self.F(8, True, SECONDARY))
        cell = self.put(c1 + 1, val, c2, val, value, self.F(20, True, DARK), Alignment(horizontal="left", vertical="center", indent=1), numfmt)
        if sub:
            self.put(c1, sub_r, c2, sub_r, sub, self.F(8, False, sub_color), Alignment(vertical="center", indent=1))
        if bar:
            self.bar(c1, br, c2, bar, accent)
        if key:
            DASH[key] = f"{L(c1 + 1)}{val}"
        return cell

    def kpis(self):
        VT, POV, PB, D = self.VT, self.POV, self.PB, self.DONE
        pc, pj = POV("C"), POV("J")
        b1, b2, b3 = BANDS
        v = lambda band, i: f"{L(CARDS[i][0] + 1)}{band[2]}"
        # band 1 — projects
        self.kpi(b1, *CARDS[0], "▣", "TOTAL PROJECTS", f'=COUNTIF({pc},"?*")', "#,##0", NAVY,
                 f'=COUNTIF({pj},{self.PSTAT[3]})&" on hold  ·  "&COUNTIF({pj},{self.PSTAT[0]})&" not started"', key="total_projects")
        self.kpi(b1, *CARDS[1], "►", "ACTIVE PROJECTS", f'=COUNTIF({pj},{self.PSTAT[1]})+COUNTIF({pj},{self.PSTAT[2]})', "#,##0", BLUE,
                 f'=IF({v(b1, 0)}=0,"",ROUND({v(b1, 1)}/{v(b1, 0)}*100,0)&"% of portfolio")', key="active_projects")
        self.kpi(b1, *CARDS[2], "✓", "COMPLETED PROJECTS", f'=COUNTIF({pj},{self.P_DONE})', "#,##0", TEAL,
                 f'=IF({v(b1, 0)}=0,"",ROUND({v(b1, 2)}/{v(b1, 0)}*100,0)&"% delivered")',
                 bar=f'=IF({v(b1, 0)}=0,0,{v(b1, 2)}/{v(b1, 0)})', key="completed_projects")
        self.kpi(b1, *CARDS[3], "!", "OVERDUE PROJECTS", f'=COUNTIF({POV("S")},"Overdue")', "#,##0", DANGER,
                 f'=IF({v(b1, 3)}=0,"✓ all on schedule","past due date — review")', key="overdue_projects")
        # band 2 — tasks
        self.kpi(b2, *CARDS[0], "≡", "TOTAL TASKS", f'=COUNTIF({VT("C")},"?*")', "#,##0", NAVY,
                 f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&{self.wk},{VT("I")},"<="&({self.wk}+6))&" due this week"', key="total_tasks")
        self.kpi(b2, *CARDS[1], "✔", "COMPLETED TASKS", f'=COUNTIFS({VT("C")},"?*",{VT("K")},{D})', "#,##0", TEAL,
                 f'=COUNTIFS({VT("C")},"?*",{VT("K")},{D},{VT("I")},">="&{self.wk},{VT("I")},"<="&({self.wk}+6))&" completed this week"',
                 key="completed_tasks")
        self.kpi(b2, *CARDS[2], "○", "PENDING TASKS", f"={v(b2, 0)}-{v(b2, 1)}", "#,##0", WARNING,
                 f'=COUNTIF({VT("P")},"Overdue")&" overdue  ·  "&COUNTIF({VT("P")},"Due soon")&" due soon"', key="pending_tasks")
        self.kpi(b2, *CARDS[3], "%", "COMPLETION RATE", f'=IF({v(b2, 0)}=0,0,{v(b2, 1)}/{v(b2, 0)})', FMT_PCT, LAVENDER,
                 f'={v(b2, 1)}&" of "&{v(b2, 0)}&" tasks done"', bar=f"={v(b2, 3)}", key="completion_rate")
        # band 3 — budget (numbers live in the engine; cards show compact text such as 135.7K)
        E = ENGINE_COL
        for i, (lab, fm) in enumerate((("Budget", f"=SUM({PB('E')})"), ("Actual", f"=SUM({PB('F')})"),
                                       ("Remaining", "=AC8-AC9"), ("Used", '=IF(AC8=0,0,AC9/AC8)'))):
            self.eng(E, 8 + i, lab)
            self.eng(E + 1, 8 + i, fm)
        DASH.update(budget_num="AC8", actual_num="AC9", remaining_num="AC10", used_num="AC11")
        self.kpi(b3, *CARDS[0], "=CurrencySymbol", '="TOTAL BUDGET ("&TRIM(CurrencySymbol)&")"', "=" + compact("AC8"), None, BLUE,
                 f'="planned across "&COUNTIF({pc},"?*")&" projects"', key="total_budget")
        self.kpi(b3, *CARDS[1], "↗", '="ACTUAL SPENDING ("&TRIM(CurrencySymbol)&")"', "=" + compact("AC9"), None, LAVENDER,
                 '=IF(AC8=0,"",ROUND(AC9/AC8*100,0)&"% of budget spent")', key="actual_spending")
        self.kpi(b3, *CARDS[2], "◎", '="REMAINING BUDGET ("&TRIM(CurrencySymbol)&")"', "=" + compact("AC10"), None, TEAL,
                 '=IF(AC10<0,"▲ over budget","available to spend")', key="remaining_budget")
        self.kpi(b3, *CARDS[3], "▤", "BUDGET USED", "=AC11", FMT_PCT, MIDNIGHT,
                 f'=COUNTIF({PB("L")},"Over budget")&" line(s) over budget"', bar="=MIN(1,AC11)", key="budget_used")
        cf_formula(self.ws, self.rng(CARDS[2][0], b3[3], CARDS[2][1]), f'LEFT({L(CARDS[2][0])}{b3[3]},1)="▲"', None, DANGER, True)
        cf_formula(self.ws, self.rng(CARDS[3][0], b1[3], CARDS[3][1]), f'LEFT({L(CARDS[3][0])}{b1[3]},1)<>"✓"', None, DANGER, True)
        cf_formula(self.ws, self.rng(CARDS[3][0], b1[3], CARDS[3][1]), f'LEFT({L(CARDS[3][0])}{b1[3]},1)="✓"', None, SUCCESS, True)
        # right column — today / progress / this week
        c1, c2 = RIGHT
        due_today = f'COUNTIFS({VT("C")},"?*",{VT("I")},{self.today})'
        done_today = f'COUNTIFS({VT("C")},"?*",{VT("I")},{self.today},{VT("K")},{D})'
        self.kpi(b1, c1, c2, "◷", "TODAY", f"={self.today}", "dddd, mmm d", BLUE,
                 f'={due_today}&" task(s) due today  ·  week "&WEEKNUM({self.today},21)', key="today")
        self.ws[f"{L(c1 + 1)}{b1[2]}"].font = self.F(16, True, DARK)
        self.kpi(b2, c1, c2, "✔", "TODAY'S PROGRESS", f'=IF({due_today}=0,"Nothing due today",{done_today}&" of "&{due_today}&" done")', None, TEAL,
                 f'=IF({due_today}=0,"Enjoy the breathing room",ROUND({done_today}/{due_today}*100,0)&"% complete")',
                 bar=f"=IF({due_today}=0,0,{done_today}/{due_today})", key="today_progress")
        self.ws[f"{L(c1 + 1)}{b2[2]}"].font = self.F(16, True, DARK)
        week_open = f'COUNTIFS({VT("C")},"?*",{VT("I")},">="&{self.wk},{VT("I")},"<="&({self.wk}+6),{VT("K")},"<>"&{D})'
        self.kpi(b3, c1, c2, "≡", "THIS WEEK", f'={week_open}&" open task(s) due"', None, WARNING,
                 f'=COUNTIF({VT("P")},"Overdue")&" overdue overall  ·  "&TEXT(SUMIFS({self.TS("I")},{self.TS("B")},">="&{self.wk},{self.TS("B")},"<="&({self.wk}+6)),"0.0")&" h scheduled"',
                 key="this_week")
        self.ws[f"{L(c1 + 1)}{b3[2]}"].font = self.F(16, True, DARK)
        DASH["due_this_week"] = f"{L(c1 + 1)}{b3[2]}"

    # -------------------------------------------------------------- charts band (status donut, monthly, calendar)
    def charts_band(self):
        ws, E = self.ws, ENGINE_COL
        t, top, bot, pad = CH["title"], CH["top"], CH["bottom"], CH["pad"]
        pj = self.POV("J")
        # --- engine: status data (AB/AC rows 27..32)
        self.eng(E, top - 1, "Project status")
        self.eng(E + 1, top - 1, "Projects")
        for i in range(6):
            self.eng(E, top + i, f"={self.PSTAT[i]}&\"\"")
            self.eng(E + 1, top + i, f'=IF({L(E)}{top + i}="",0,COUNTIF({pj},{L(E)}{top + i}))')
        DASH["donut_first"] = f"{L(E + 1)}{top}"
        # --- donut card
        c1, c2 = HALF_L
        self.card(c1, t, c2, pad, "Projects by status", BLUE)
        ch = DoughnutChart(holeSize=62)
        ch.add_data(Reference(ws, min_col=E + 1, min_row=top, max_row=top + 5), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=E, min_row=top, max_row=top + 5))
        cols = [MED_GRAY, LAVENDER, BLUE, WARNING, TEAL, DANGER]
        for i, colr in enumerate(cols):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.solidFill = WHITE
            ch.series[0].dPt.append(pt)
        style_chart(ch, legend=False)
        self.place(ch, c1, top, 4, bot)
        tot = f"SUM({L(E + 1)}{top}:{L(E + 1)}{top + 5})"
        self.put(6, top + 1, 8, top + 1, "DELIVERED", self.F(8, True, SECONDARY))
        self.put(6, top + 2, 8, top + 3, f"=IF({tot}=0,0,{L(E + 1)}{top + 4}/{tot})", self.F(24, True, TEAL),
                 Alignment(horizontal="left", vertical="center", indent=1), FMT_PCT)
        self.put(6, top + 4, 8, top + 4, f'={L(E + 1)}{top + 4}&" of "&{tot}&" projects completed"', self.F(8, False, SECONDARY))
        for i in range(6):
            r = top + 6 + i
            self.put(5, r, 5, r, "●", self.F(10, False, cols[i]), Alignment(horizontal="right", vertical="center"))
            self.put(6, r, 7, r, f"={L(E)}{top + i}", self.F(8, False, DARK))
            self.put(8, r, 8, r, f'=IF({tot}=0,"0",{L(E + 1)}{top + i}&" ("&ROUND({L(E + 1)}{top + i}/{tot}*100,0)&"%)")',
                     self.F(8, True, DARK), Alignment(horizontal="right", vertical="center", indent=1))
        # --- monthly productivity (engine AE..AG)
        me = E + 3
        self.eng(me, top - 1, "Month")
        self.eng(me + 1, top - 1, "Tasks due")
        self.eng(me + 2, top - 1, "Completed")
        VT = self.VT
        for m in range(12):
            r = top + m
            self.eng(me, r, f"=DATE($U${top},{m + 1},1)", "mmm")
            self.eng(me + 1, r, f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&{L(me)}{r},{VT("I")},"<"&EDATE({L(me)}{r},1))')
            self.eng(me + 2, r, f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&{L(me)}{r},{VT("I")},"<"&EDATE({L(me)}{r},1),{VT("K")},{self.DONE})')
        DASH["monthly_first"] = f"{L(me)}{top}"
        c1, c2 = HALF_R
        self.card(c1, t, c2, pad, "Monthly productivity", TEAL, f'="Year "&$U${top}')
        ch = BarChart()
        ch.type = "col"
        ch.add_data(Reference(ws, min_col=me + 1, max_col=me + 2, min_row=top - 1, max_row=top + 11), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=me, min_row=top, max_row=top + 11))
        ch.series[0].graphicalProperties.solidFill = "C7D4F7"
        ch.series[1].graphicalProperties.solidFill = TEAL
        for s in ch.series:
            s.graphicalProperties.line.noFill = True
        ch.gapWidth = 55
        ch.overlap = -5
        style_chart(ch)
        self.place(ch, c1, top, c2, bot)

    # -------------------------------------------------------------- mini calendar
    def calendar(self):
        ws, E = self.ws, ENGINE_COL
        t, top, pad = CH["title"], CH["top"], CH["pad"]
        c1, c2 = RIGHT
        self.card(c1, t, c2, pad, "Calendar", LAVENDER)
        # selectors
        mcell = self.put(c1, top, c1 + 2, top, f'=INDEX({self.SS("G")},MONTH({self.TODAY}))', self.F(10, True, NAVY),
                         Alignment(horizontal="center", vertical="center"), f=fill(SOFT_BLUE))
        ycell = self.put(c1 + 3, top, c1 + 4, top, f"={self.SC('C', 18)}", self.F(10, True, NAVY),
                         Alignment(horizontal="center", vertical="center"), f=fill(SOFT_BLUE))
        self.b.unlocked[self.S["DASH"]] += [self.rng(c1, top, c1 + 2, top), self.rng(c1 + 3, top, c1 + 4, top)]
        from common import add_list_dv
        add_list_dv(ws, f"{L(c1)}{top}", self.SS("G"))
        add_list_dv(ws, f"{L(c1 + 3)}{top}", self.SS("H"))
        DASH["cal_month"], DASH["cal_year"] = f"{L(c1)}{top}", f"{L(c1 + 3)}{top}"
        # engine scalars (AO..AS row 27)
        g = E + 13    # AO
        self.eng(g, top - 1, "month#")
        self.eng(g + 1, top - 1, "first")
        self.eng(g + 2, top - 1, "grid start")
        self.eng(g + 3, top - 1, "next month")
        self.eng(g, top, f'=IFERROR(MATCH({L(c1)}{top},{self.SS("G")},0),MONTH({self.TODAY}))')
        self.eng(g + 1, top, f"=DATE({L(c1 + 3)}{top},{L(g)}{top},1)", FMT_SDATE)
        self.eng(g + 2, top, f'={L(g + 1)}{top}-MOD(WEEKDAY({L(g + 1)}{top})-IF(WeekStart="Sunday",1,2),7)', FMT_SDATE)
        self.eng(g + 3, top, f"=EDATE({L(g + 1)}{top},1)", FMT_SDATE)
        MN, FIRST, GS, NXT = (f"${L(g)}${top}", f"${L(g + 1)}${top}", f"${L(g + 2)}${top}", f"${L(g + 3)}${top}")
        self.put(c1, top + 1, c2, top + 1, f"={FIRST}", self.F(11, True, NAVY), Alignment(horizontal="center", vertical="center"),
                 "mmmm yyyy")
        for d in range(7):
            self.put(c1 + d, top + 2, c1 + d, top + 2,
                     f'=CHOOSE(WEEKDAY({GS}+{d}),"Su","Mo","Tu","We","Th","Fr","Sa")', self.F(8, True, SECONDARY),
                     Alignment(horizontal="center", vertical="center"))
        VT = self.VT
        first_day_row = top + 3
        for w in range(6):
            r = first_day_row + w
            for d in range(7):
                c = c1 + d
                self.put(c, r, c, r, f"={GS}+{w * 7 + d}", self.F(9, False, DARK), Alignment(horizontal="center", vertical="center"), "d")
                dc = f"{L(c)}{r}"
                self.eng(g + d, r, f'=COUNTIFS({VT("I")},{dc},{VT("C")},"?*")')
                self.eng(g + 8 + d, r, f'=IF({dc}<{self.today},COUNTIFS({VT("I")},{dc},{VT("C")},"?*",{VT("K")},"<>"&{self.DONE}),0)')
        grid = self.rng(c1, first_day_row, c2, first_day_row + 5)
        f0 = f"{L(c1)}{first_day_row}"
        cnt0 = f"{L(g)}{first_day_row}"
        od0 = f"{L(g + 8)}{first_day_row}"
        cf_formula(ws, grid, f"{f0}={self.today}", BLUE, WHITE, True, stop=True)
        cf_formula(ws, grid, f"MONTH({f0})<>{MN}", None, "C5CCD6", stop=True)
        cf_formula(ws, grid, f"{od0}>0", DANGER_BG, DANGER, True, stop=True)
        cf_formula(ws, grid, f"{cnt0}>0", SOFT_BLUE, BLUE, True)
        # legend + stats
        lr = first_day_row + 6
        self.put(c1, lr, c1, lr, "", f=fill(BLUE))
        self.put(c1 + 1, lr, c1 + 2, lr, "Today", self.F(8, False, SECONDARY))
        self.put(c1 + 3, lr, c1 + 3, lr, "", f=fill(SOFT_BLUE))
        self.put(c1 + 4, lr, c1 + 6, lr, "Tasks due", self.F(8, False, SECONDARY))
        self.put(c1, lr + 1, c1, lr + 1, "", f=fill(DANGER_BG))
        self.put(c1 + 1, lr + 1, c1 + 6, lr + 1, "Overdue (open tasks on a past day)", self.F(8, False, SECONDARY))
        for cc in (c1, c1 + 3):
            ws.cell(row=lr, column=cc).border = Border(top=Side(style="thick", color=WHITE), bottom=Side(style="thick", color=WHITE),
                                                      left=Side(style="thick", color=WHITE), right=Side(style="thick", color=WHITE))
        ws.cell(row=lr + 1, column=c1).border = ws.cell(row=lr, column=c1).border.copy()
        # month stats in the card's last content row (pad row stays empty)
        sr = CH["bottom"]
        due = f'COUNTIFS({VT("C")},"?*",{VT("I")},">="&{FIRST},{VT("I")},"<"&{NXT})'
        done = f'COUNTIFS({VT("C")},"?*",{VT("I")},">="&{FIRST},{VT("I")},"<"&{NXT},{VT("K")},{self.DONE})'
        od = f'COUNTIFS({VT("P")},"Overdue",{VT("I")},">="&{FIRST},{VT("I")},"<"&{NXT})'
        self.put(c1, sr, c2, sr, f'="This month:  "&{due}&" due  ·  "&{done}&" done  ·  "&{od}&" overdue"', self.F(8, True, NAVY),
                 Alignment(horizontal="center", vertical="center"), f=fill(SOFT_LAV))
        DASH["cal_first_day"] = f"{L(c1)}{first_day_row}"
        DASH["cal_stats"] = f"{L(c1)}{sr}"

    # -------------------------------------------------------------- band 2 (completion chart, budget chart, priority)
    def band2(self):
        ws, E = self.ws, ENGINE_COL
        t, first, last = B2["title"], B2["first"], B2["last"]
        POV = self.POV
        pe = E + 7   # AI..AM project data
        heads = ["Project", "Budget", "Actual", "Done", "Open"]
        for j, hd in enumerate(heads):
            self.eng(pe + j, first - 1, hd)
        for i in range(8):
            r = first + i
            idx = f'MATCH({i + 1},{POV("U")},0)'
            self.eng(pe, r, f'=IFERROR(INDEX({POV("C")},{idx}),"")')
            self.eng(pe + 1, r, f'=IFERROR(INDEX({POV("L")},{idx}),0)')
            self.eng(pe + 2, r, f'=IFERROR(INDEX({POV("M")},{idx}),0)')
            self.eng(pe + 3, r, f'=IFERROR(INDEX({POV("Q")},{idx}),0)')
            self.eng(pe + 4, r, f'=IFERROR(INDEX({POV("P")},{idx})-{L(pe + 3)}{r},0)')
        DASH["proj_chart_first"] = f"{L(pe)}{first}"
        c1, c2 = HALF_L
        self.card(c1, t, c2, last, "Task completion by project", TEAL)
        ch = BarChart()
        ch.type = "bar"
        ch.grouping = "stacked"
        ch.overlap = 100
        ch.gapWidth = 45
        ch.add_data(Reference(ws, min_col=pe + 3, max_col=pe + 4, min_row=first - 1, max_row=first + 7), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=pe, min_row=first, max_row=first + 7))
        ch.series[0].graphicalProperties.solidFill = TEAL
        ch.series[1].graphicalProperties.solidFill = "D9D3FA"
        for s in ch.series:
            s.graphicalProperties.line.noFill = True
        style_chart(ch)
        ch.x_axis.scaling.orientation = "maxMin"
        ch.x_axis.tickLblSkip = 1
        self.place(ch, c1, first, c2, last - 1)
        c1, c2 = HALF_R
        self.card(c1, t, c2, last, "Budget vs actual by project", BLUE, '="Currency: "&TRIM(CurrencySymbol)')
        ch = BarChart()
        ch.type = "bar"
        ch.gapWidth = 40
        ch.overlap = -10
        ch.add_data(Reference(ws, min_col=pe + 1, max_col=pe + 2, min_row=first - 1, max_row=first + 7), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=pe, min_row=first, max_row=first + 7))
        ch.series[0].graphicalProperties.solidFill = BLUE
        ch.series[1].graphicalProperties.solidFill = LAVENDER
        for s in ch.series:
            s.graphicalProperties.line.noFill = True
        style_chart(ch)
        ch.x_axis.scaling.orientation = "maxMin"
        ch.x_axis.tickLblSkip = 1
        ch.y_axis.numFmt = NumFmt(formatCode='#,##0,"K"', sourceLinked=False)
        self.place(ch, c1, first, c2, last - 1)
        # priority card (right)
        c1, c2 = RIGHT
        self.card(c1, t, c2, last, "Open tasks by priority", WARNING)
        VT = self.VT
        pcols = [DANGER, WARNING, BLUE, TEAL]
        pr_e = E + 19   # AU: counts
        names = list(self.PRI.values())
        for k in range(4):
            self.eng(pr_e, first + k, f'=COUNTIFS({VT("J")},{names[k]},{VT("C")},"?*",{VT("K")},"<>"&{self.DONE})')
        mx = f"MAX(${L(pr_e)}${first}:${L(pr_e)}${first + 3})"
        for k in range(4):
            r = 44 + k * 3
            self.put(c1, r, c1, r, "●", self.F(11, False, pcols[k]), Alignment(horizontal="center", vertical="center"))
            self.put(c1 + 1, r, c1 + 3, r, f"={names[k]}", self.F(9, True, DARK))
            od = f'COUNTIFS({VT("J")},{names[k]},{VT("P")},"Overdue")'
            self.put(c1 + 4, r, c2, r, f'={L(pr_e)}{first + k}&" open"&IF({od}>0,"  ·  "&{od}&" late","")', self.F(8, False, SECONDARY),
                     Alignment(horizontal="right", vertical="center", indent=1))
            self.bar(c1 + 1, r + 1, c2, f"=IF({mx}=0,0,{L(pr_e)}{first + k}/{mx})", pcols[k])
        DASH["priority_first"] = f"{L(pr_e)}{first}"

    # -------------------------------------------------------------- lists band
    def list_head(self, r, spans, color=SECONDARY):
        for (c1, c2, text, al) in spans:
            self.put(c1, r, c2, r, text, self.F(8, True, color),
                     Alignment(horizontal=al, vertical="center", indent=1 if al != "center" else 0), f=fill("F2F5F9"))

    def row_line(self, r, c1, c2):
        for cc in range(c1, c2 + 1):
            cell = self.ws.cell(row=r, column=cc)
            b = cell.border
            cell.border = Border(left=b.left, right=b.right, top=b.top, bottom=Side(style="hair", color=BORDER))

    def lists(self):
        ws, E, VT = self.ws, ENGINE_COL, self.VT
        t, hd, first, n, pad = LST["title"], LST["head"], LST["first"], LST["n"], LST["pad"]
        ix = E + 29  # BD.. index helpers
        self.eng(ix, hd, "idx up")
        self.eng(ix + 1, hd, "idx od")
        self.eng(ix + 2, hd, "idx today")
        for k in range(1, n + 1):
            r = first + k - 1
            self.eng(ix, r, f'=IFERROR(MATCH(SMALL({VT("T")},{k}),{VT("T")},0),"")')
            self.eng(ix + 1, r, f'=IFERROR(MATCH(SMALL({VT("U")},{k}),{VT("U")},0),"")')
            self.eng(ix + 2, r, f'=IFERROR(MATCH(INT({self.today})&"|{k}",{VT("R")},0),"")')

        def idx(col, r):
            return f"${L(col)}{r}"

        def get(col, src, r):
            return f'IF({idx(col, r)}="","",INDEX({VT(src)},{idx(col, r)})&"")'

        def first_name(col, r):
            return f'IF({idx(col, r)}="","",LEFT(INDEX({VT("G")},{idx(col, r)})&"",FIND(" ",INDEX({VT("G")},{idx(col, r)})&" ")-1))'

        # upcoming
        c1, c2 = HALF_L
        self.card(c1, t, c2, pad, "Upcoming deadlines", BLUE, "next 8 open tasks")
        self.list_head(hd, [(2, 4, "TASK", "left"), (6, 7, "PROJECT", "left"), (8, 8, "DUE", "center")])
        for k in range(n):
            r = first + k
            self.put(2, r, 4, r, f"={get(ix, 'C', r)}" if k else f'=IF({idx(ix, r)}="","No upcoming deadlines — nice!",INDEX({VT("C")},{idx(ix, r)})&"")',
                     self.F(9, False, DARK))
            self.put(6, r, 7, r, f"={get(ix, 'E', r)}", self.F(8, False, SECONDARY))
            self.put(8, r, 8, r, f'=IF({idx(ix, r)}="","",INDEX({VT("I")},{idx(ix, r)}))', self.F(9, True, BLUE),
                     Alignment(horizontal="center", vertical="center"), FMT_SDATE)
            self.row_line(r, 2, 8)
        cf_formula(ws, f"H{first}:H{first + n - 1}", f"AND(ISNUMBER(H{first}),H{first}-{self.today}<=$AC$5)", WARNING_BG, "9A6512", True)
        DASH["up_first"] = f"B{first}"
        DASH["up_due_first"] = f"H{first}"
        # overdue
        c1, c2 = HALF_R
        self.card(c1, t, c2, pad, "Overdue tasks", DANGER, f'=COUNTIF({VT("P")},"Overdue")&" total"')
        self.list_head(hd, [(10, 12, "TASK", "left"), (14, 15, "OWNER", "left"), (16, 16, "LATE", "center")])
        for k in range(n):
            r = first + k
            self.put(10, r, 12, r, f"={get(ix + 1, 'C', r)}" if k else f'=IF({idx(ix + 1, r)}="","No overdue tasks — great work!",INDEX({VT("C")},{idx(ix + 1, r)})&"")',
                     self.F(9, False, DARK))
            self.put(14, r, 15, r, f"={first_name(ix + 1, r)}", self.F(8, False, SECONDARY))
            self.put(16, r, 16, r, f'=IF({idx(ix + 1, r)}="","",-INDEX({VT("Q")},{idx(ix + 1, r)})&" d")', self.F(9, True, DANGER),
                     Alignment(horizontal="center", vertical="center"))
            self.row_line(r, 10, 16)
        DASH["od_first"] = f"J{first}"
        DASH["od_late_first"] = f"P{first}"
        # due today (right)
        c1, c2 = RIGHT
        self.card(c1, t, c2, pad, "Due today", TEAL, f'=COUNTIFS({VT("C")},"?*",{VT("I")},{self.today})&" task(s)"')
        self.list_head(hd, [(18, 21, "TASK", "left"), (22, 23, "OWNER", "left"), (24, 24, "", "center")])
        for k in range(n):
            r = first + k
            self.put(18, r, 21, r, f"={get(ix + 2, 'C', r)}" if k else f'=IF({idx(ix + 2, r)}="","Nothing due today",INDEX({VT("C")},{idx(ix + 2, r)})&"")',
                     self.F(9, False, DARK))
            self.put(22, r, 23, r, f"={first_name(ix + 2, r)}", self.F(8, False, SECONDARY))
            self.put(24, r, 24, r, f'=IF({idx(ix + 2, r)}="","",IF(INDEX({VT("K")},{idx(ix + 2, r)})={self.DONE},"✓","○"))',
                     self.F(11, True, MED_GRAY), Alignment(horizontal="center", vertical="center"))
            self.row_line(r, 18, 24)
        cf_formula(ws, f"X{first}:X{first + n - 1}", f'X{first}="✓"', SUCCESS_BG, SUCCESS, True)
        cf_formula(ws, f"R{first}:U{first + n - 1}", f'$X{first}="✓"', None, MED_GRAY)
        DASH["today_first"] = f"R{first}"

    # -------------------------------------------------------------- performance table + team
    def table(self):
        ws, E, POV, VT = self.ws, ENGINE_COL, self.POV, self.VT
        t, hd, first, n, pad = TBL["title"], TBL["head"], TBL["first"], TBL["n"], TBL["pad"]
        ix = E + 32
        c1, c2 = CENTER
        self.card(c1, t, c2, pad, "Project performance overview", NAVY, f'=COUNTIF({POV("C")},"?*")&" projects"')
        cols = [(2, 4, "PROJECT", "left"), (5, 6, "MANAGER", "left"), (7, 7, "STATUS", "center"), (8, 9, "PROGRESS", "left"),
                (10, 10, "", "center"), (11, 11, "BUDGET", "center"), (12, 12, "ACTUAL", "center"), (13, 14, "VARIANCE", "right"),
                (15, 15, "DUE", "center"), (16, 16, "HEALTH", "center")]
        self.list_head(hd, cols)
        self.eng(ix, hd, "idx perf")
        for k in range(n):
            r = first + k
            self.eng(ix, r, f'=IFERROR(MATCH({k + 1},{POV("U")},0),"")')
            i = f"${L(ix)}{r}"

            def pv(c, i=i):
                return f'IF({i}="","",INDEX({POV(c)},{i}))'
            self.put(2, r, 4, r, f'={pv("C")}&""' if k else f'=IF({i}="","No projects yet — add one",INDEX({POV("C")},{i})&"")',
                     self.F(9, True, DARK))
            self.put(5, r, 6, r, f'=IF({i}="","",LEFT(INDEX({POV("F")},{i})&"",FIND(" ",INDEX({POV("F")},{i})&" ")-1))', self.F(8, False, SECONDARY))
            self.put(7, r, 7, r, f'={pv("J")}&""', self.F(8, False, DARK), Alignment(horizontal="center", vertical="center"))
            self.bar(8, r, 9, f'=IF({i}="",0,N({pv("K")}))', TEAL)
            self.put(10, r, 10, r, f'={pv("K")}', self.F(8, True, DARK), Alignment(horizontal="left", vertical="center", indent=1), FMT_PCT)
            nv = lambda c: f'N(INDEX({POV(c)},{i}))'
            self.put(11, r, 11, r, f'=IF({i}="","",{compact(nv("L"))})', self.F(8, False, DARK), Alignment(horizontal="right", vertical="center", indent=1))
            self.put(12, r, 12, r, f'=IF({i}="","",{compact(nv("M"))})', self.F(8, False, DARK), Alignment(horizontal="right", vertical="center", indent=1))
            self.put(13, r, 14, r, f'=IF({i}="","",{compact(nv("N"), sign=True)})', self.F(8, True, DARK),
                     Alignment(horizontal="right", vertical="center", indent=1))
            self.put(15, r, 15, r, f'={pv("H")}', self.F(8, False, DARK), Alignment(horizontal="center", vertical="center"), FMT_SDATE)
            self.put(16, r, 16, r, f'={pv("S")}&""', self.F(8, True, DARK), Alignment(horizontal="center", vertical="center"))
            self.row_line(r, 2, 16)
        cf_formula(ws, f"M{first}:M{first + n - 1}", f'LEFT(M{first},1)="-"', None, DANGER, True)
        cf_formula(ws, f"H{first}:H{first + n - 1}", f'${L(ix)}{first}=""', WHITE)
        for txt, bg, fg in (("Completed", SUCCESS_BG, SUCCESS), ("Overdue", DANGER_BG, DANGER), ("Over budget", DANGER_BG, DANGER),
                            ("At risk", WARNING_BG, "9A6512"), ("On track", INFO_BG, INFO), ("Cancelled", LIGHT_GRAY, SECONDARY)):
            cf_formula(ws, f"P{first}:P{first + n - 1}", f'P{first}="{txt}"', bg, fg, True)
        DASH["perf_first"] = f"B{first}"
        # team workload (right)
        c1, c2 = RIGHT
        self.card(c1, t, c2, pad, "Team workload", LAVENDER, "open tasks")
        self.list_head(hd, [(18, 20, "MEMBER", "left"), (21, 21, "OPEN", "center"), (22, 22, "LATE", "center"),
                            (23, 23, "HRS", "center"), (24, 24, "DONE", "center")])
        tl = self.SL("G")
        for k in range(n):
            r = first + k
            nm = f"INDEX({tl},{k + 1})"
            self.put(18, r, 20, r, f'=IF({nm}="","",{nm})', self.F(9, False, DARK))
            m = f"R{r}"
            self.put(21, r, 21, r, f'=IF({m}="","",COUNTIFS({VT("G")},{m},{VT("C")},"?*",{VT("K")},"<>"&{self.DONE}))', self.F(9, True, DARK),
                     Alignment(horizontal="center", vertical="center"))
            self.put(22, r, 22, r, f'=IF({m}="","",COUNTIFS({VT("G")},{m},{VT("P")},"Overdue"))', self.F(9, True, DARK),
                     Alignment(horizontal="center", vertical="center"))
            self.put(23, r, 23, r, f'=IF({m}="","",SUMIFS({VT("L")},{VT("G")},{m},{VT("K")},"<>"&{self.DONE}))', self.F(8, False, SECONDARY),
                     Alignment(horizontal="center", vertical="center"), "0")
            self.put(24, r, 24, r, f'=IF({m}="","",COUNTIFS({VT("G")},{m},{VT("K")},{self.DONE}))', self.F(8, False, SECONDARY),
                     Alignment(horizontal="center", vertical="center"))
            self.row_line(r, 18, 24)
        cf_formula(ws, f"V{first}:V{first + n - 1}", f"AND(ISNUMBER(V{first}),V{first}>0)", DANGER_BG, DANGER, True)
        DASH["team_first"] = f"R{first}"

    # -------------------------------------------------------------- last band: recent, status, deadlines
    def last_band(self):
        ws, E, VT, POV = self.ws, ENGINE_COL, self.VT, self.POV
        t, hd, first, n, pad = LB["title"], LB["head"], LB["first"], LB["n"], LB["pad"]
        ix = E + 33
        self.eng(ix, hd, "idx recent")
        self.eng(ix + 1, hd, "idx deadline")
        FIRST, NXT = f"$AP${CH['top']}", f"$AR${CH['top']}"
        for k in range(1, n + 1):
            r = first + k - 1
            self.eng(ix, r, f'=IFERROR(MATCH(LARGE({VT("Y")},{k}),{VT("Y")},0),"")')
            v = f'SMALL({POV("V")},COUNTIF({POV("V")},"<"&{FIRST})+{k})'
            self.eng(ix + 1, r, f'=IFERROR(IF({v}<{NXT},MATCH({v},{POV("V")},0),""),"")')
        # recent activity
        c1, c2 = HALF_L
        self.card(c1, t, c2, pad, "Recent activity", LAVENDER, "latest task starts")
        self.list_head(hd, [(2, 4, "TASK", "left"), (6, 7, "STATUS", "left"), (8, 8, "DONE", "center")])
        for k in range(n):
            r = first + k
            i = f"${L(ix)}{r}"
            self.put(2, r, 4, r, f'=IF({i}="","",INDEX({VT("C")},{i})&"")' if k else f'=IF({i}="","No activity yet",INDEX({VT("C")},{i})&"")',
                     self.F(9, False, DARK))
            st = f'INDEX({VT("K")},{i})'
            self.put(6, r, 7, r, f'=IF({i}="","",{self.status_txt(st)})', self.F(8, False, DARK))
            self.put(8, r, 8, r, f'=IF({i}="","",INDEX({VT("Z")},{i}))', self.F(9, True, DARK), Alignment(horizontal="center", vertical="center"),
                     FMT_PCT)
            self.row_line(r, 2, 8)
        self.status_cf(f"F{first}:F{first + n - 1}", f"F{first}")
        DASH["recent_first"] = f"B{first}"
        # tasks by status
        c1, c2 = HALF_R
        self.card(c1, t, c2, pad, "Tasks by status", BLUE, f'=COUNTIF({VT("C")},"?*")&" tasks"')
        self.list_head(hd, [(10, 12, "STATUS", "left"), (14, 14, "TASKS", "center"), (15, 16, "SHARE", "left")])
        tot = f'COUNTIF({VT("C")},"?*")'
        for k in range(6):
            r = first + k
            s = self.TSTAT[k]
            self.put(10, r, 12, r, f"={self.status_txt(s)}", self.F(9, False, DARK))
            self.put(14, r, 14, r, f'=COUNTIFS({VT("K")},{s},{VT("C")},"?*")', self.F(9, True, DARK), Alignment(horizontal="center", vertical="center"))
            self.bar(15, r, 15, f"=IF({tot}=0,0,N(N{r})/{tot})", [MED_GRAY, LAVENDER, BLUE, WARNING, TEAL, DANGER][k])
            self.put(16, r, 16, r, f"=IF({tot}=0,0,N(N{r})/{tot})", self.F(8, False, SECONDARY),
                     Alignment(horizontal="right", vertical="center", indent=1), FMT_PCT)
            self.row_line(r, 10, 16)
        self.status_cf(f"J{first}:J{first + 5}", f"J{first}")
        DASH["status_first"] = f"N{first}"
        # project deadlines this month (right)
        c1, c2 = RIGHT
        self.card(c1, t, c2, pad, "Project deadlines", NAVY, f"=$AP${CH['top']}")
        ws.cell(row=t, column=23).number_format = "mmm yyyy"
        self.list_head(hd, [(18, 21, "PROJECT", "left"), (22, 23, "DUE", "center"), (24, 24, "DAYS", "center")])
        for k in range(n):
            r = first + k
            i = f"${L(ix + 1)}{r}"
            self.put(18, r, 21, r, f'=IF({i}="","",INDEX({POV("C")},{i})&"")' if k else f'=IF({i}="","No project deadlines this month",INDEX({POV("C")},{i})&"")',
                     self.F(9, False, DARK))
            self.put(22, r, 23, r, f'=IF({i}="","",INDEX({POV("H")},{i}))', self.F(8, True, NAVY), Alignment(horizontal="center", vertical="center"),
                     "ddd, mmm d")
            self.put(24, r, 24, r, f'=IF({i}="","",INDEX({POV("O")},{i}))', self.F(8, True, DARK), Alignment(horizontal="center", vertical="center"), "0")
            self.row_line(r, 18, 24)
        cf_formula(ws, f"X{first}:X{first + n - 1}", f"AND(ISNUMBER(X{first}),X{first}<0)", DANGER_BG, DANGER, True)
        DASH["deadline_first"] = f"R{first}"

    def status_cf(self, rng, first):
        for glyph, bg, fg in (("✓", SUCCESS_BG, SUCCESS), ("►", INFO_BG, INFO), ("◆", WARNING_BG, "9A6512"), ("‖", LIGHT_GRAY, SECONDARY)):
            cf_formula(self.ws, rng, f'LEFT({first},1)="{glyph}"', bg, fg)
