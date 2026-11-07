"""PRODUCT 1 — Ultimate Project Manager (15 tabs).

Usage:  python build_project_manager.py [--out DIR]
Builds four workbooks: Excel / Google-Sheets editions, each with DEMO data and BLANK.

Formula policy (keeps one formula set valid in Excel 2010+, Excel 365, LibreOffice and Google Sheets):
  * lookups: INDEX/MATCH; aggregation: SUMIFS/COUNTIFS/AVERAGEIFS; no spilled dynamic arrays
  * "filtered lists" use running-number helper columns + INDEX/MATCH (works everywhere)
  * conditional formatting only references cells on its own sheet (Google Sheets requirement)
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.styles import Alignment, Protection
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.table import Table, TableStyleInfo

from common import *  # noqa: F401,F403
from common import _cells
import sample_data_pm as SD

# ---------------------------------------------------------------- sheet names
S_SETUP = "Setup"
S_DASH = "All-in-One Dashboard"
S_MCAL = "Monthly Calendar"
S_WCAL = "Weekly Calendar"
S_POV = "Project Overview"
S_PM = "Project Manager"
S_PB = "Project Budget"
S_VT = "Variable Tasks"
S_RT = "Recurring Tasks"
S_TS = "Task Schedule"
S_TF = "Task Filter"
S_DM = "Decision Matrix"
S_KB = "Kanban Board"
S_GC = "Gantt Chart"
S_INS = "Instructions"
ORDER = [S_SETUP, S_DASH, S_MCAL, S_WCAL, S_POV, S_PM, S_PB, S_VT, S_RT, S_TS, S_TF, S_DM, S_KB, S_GC, S_INS]

HDR = 6          # header row of every database tab
R1 = 7           # first data row
POV_N, VT_N, PB_N, RT_N, TS_N, PD_N = 100, 500, 500, 200, 300, 300
POV_LAST, VT_LAST, PB_LAST, RT_LAST, TS_LAST = R1 + POV_N - 1, R1 + VT_N - 1, R1 + PB_N - 1, R1 + RT_N - 1, R1 + TS_N - 1

# Setup list geometry
LR1, LRN = 27, 46          # editable lists
SR1, SRN = 51, 70          # system lists


def rng(sheet, c, r1, r2):
    return f"{quote(sheet)}!${c}${r1}:${c}${r2}"


def VT(c): return rng(S_VT, c, R1, VT_LAST)
def POV(c): return rng(S_POV, c, R1, POV_LAST)
def PB(c): return rng(S_PB, c, R1, PB_LAST)
def RT(c): return rng(S_RT, c, R1, RT_LAST)
def TS(c): return rng(S_TS, c, R1, TS_LAST)
def SL(c): return f"{S_SETUP}!${c}${LR1}:${c}${LRN}"       # editable list
def SS(c): return f"{S_SETUP}!${c}${SR1}:${c}${SRN}"       # system list
def SC(c, r): return f"{S_SETUP}!${c}${r}"                 # single setup cell


# named single cells
DONE = "StatusDone"          # Setup!E31  (task status "Completed")
P_DONE = "ProjDone"          # Setup!F31
P_CANCEL = "ProjCancelled"   # Setup!F32
TODAY = "RefDate"            # Setup!C20

# list columns on Setup
LISTS = {
    "B": ("Project Categories", ["Marketing", "Product Development", "Information Technology", "Operations", "Finance", "Creative", "Customer Success", "Human Resources"]),
    "C": ("Task Categories", SD.TASK_CATS),
    "D": ("Priority Levels", ["Critical", "High", "Medium", "Low"]),
    "E": ("Task Statuses", ["Backlog", "To Do", "In Progress", "Review", "Completed", "On Hold"]),
    "F": ("Project Statuses", ["Not Started", "Planning", "In Progress", "On Hold", "Completed", "Cancelled"]),
    "G": ("Team Members", [t[0] for t in SD.TEAM]),
    "H": ("Member Role", [t[1] for t in SD.TEAM]),
    "I": ("Member Department", [t[2] for t in SD.TEAM]),
    "J": ("Departments", ["Operations", "Engineering", "Creative", "Marketing", "Finance", "Sales", "Customer Success"]),
    "K": ("Payment Categories", ["Labor", "Contractors", "Software", "Hardware", "Marketing", "Travel", "Training", "Other"]),
    "L": ("Project Detail Types", ["Objective", "Deliverable", "Milestone", "Dependency", "Risk", "Note"]),
}
CURRENCIES = [("USD", "$"), ("EUR", "€"), ("GBP", "£"), ("CAD", "CA$"), ("AUD", "A$"), ("JPY", "¥"), ("CHF", "CHF "),
              ("INR", "₹"), ("MAD", "MAD "), ("AED", "AED "), ("ZAR", "R"), ("BRL", "R$"), ("MXN", "MX$"), ("SGD", "S$")]
FREQ = [("Daily", "D", 1), ("Weekly", "D", 7), ("Biweekly", "D", 14), ("Monthly", "M", 1), ("Quarterly", "M", 3),
        ("Annually", "M", 12), ("Custom", "D", None)]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
SYSTEM = {
    "B": ("Currency Code", [c for c, _ in CURRENCIES]),
    "C": ("Symbol", [s for _, s in CURRENCIES]),
    "D": ("Frequency", [f for f, _, _ in FREQ]),
    "E": ("Unit (D/M)", [u for _, u, _ in FREQ]),
    "F": ("Step", [s for _, _, s in FREQ]),
    "G": ("Months", MONTHS),
    "H": ("Years", list(range(2024, 2036))),
    "I": ("Week Start", ["Monday", "Sunday"]),
    "J": ("Yes / No", ["Yes", "No"]),
    "K": ("Completion Filter", ["Complete", "Incomplete"]),
    "L": ("Overdue Filter", ["Overdue only", "Not overdue"]),
    "M": ("Gantt View", ["Daily", "Weekly"]),
    "N": ("Recurring Status", ["Active", "Paused"]),
    "O": ("Score (1-10)", list(range(1, 11))),
}
CUSTOM_FREQ = SC("D", SR1 + 6)
PAUSED = SC("N", SR1 + 1)
PRI = {p: SC("D", LR1 + i) for i, p in enumerate(LISTS["D"][1])}
TSTAT = [SC("E", LR1 + i) for i in range(6)]
PSTAT = [SC("F", LR1 + i) for i in range(6)]
DTYPES = [SC("L", LR1 + i) for i in range(6)]


class Builder:
    def __init__(self, edition: str, demo: bool):
        self.ed = edition
        self.demo = demo
        self.T = Theme(edition)
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in ORDER}
        tab = {S_SETUP: LAVENDER, S_DASH: BLUE, S_MCAL: BLUE, S_WCAL: BLUE, S_POV: NAVY, S_PM: NAVY, S_PB: NAVY,
               S_VT: TEAL, S_RT: TEAL, S_TS: TEAL, S_TF: TEAL, S_DM: LAVENDER, S_KB: LAVENDER, S_GC: LAVENDER, S_INS: MED_GRAY}
        for n, c in tab.items():
            self.ws[n].sheet_properties.tabColor = c
        self.unlocked: dict[str, list[str]] = {n: [] for n in ORDER}

    # ------------------------------------------------------------ utilities
    def F(self, *a, **k):
        return self.T.font(*a, **k)

    def inp(self, sheet, rngs, numfmt=None, align=None):
        style_input(self.ws[sheet], rngs, self.T, numfmt, align)
        self.unlocked[sheet].append(rngs)

    def calc(self, sheet, rngs, numfmt=None, align=None, color=DARK):
        style_calc(self.ws[sheet], rngs, self.T, numfmt, align, color)

    def fill_down(self, ws, c, r1, r2, template: str):
        """template uses {r} for the current row and {p} for the previous row."""
        for r in range(r1, r2 + 1):
            ws[f"{c}{r}"] = template.format(r=r, p=r - 1)

    def table(self, ws, name, ref):
        if self.ed == "excel":
            t = Table(displayName=name, ref=ref)
            t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False, showColumnStripes=False)
            ws.add_table(t)
        else:
            ws.auto_filter.ref = ref

    def kpi(self, ws, r, c, label, formula, numfmt="#,##0", color=BLUE, sub=None, width=2):
        """3-row KPI card at (r, c) spanning `width` columns."""
        T = self.T
        c2 = c + width - 1
        cl, cr = L(c), L(c2)
        for rr in range(r, r + 3):
            ws.merge_cells(f"{cl}{rr}:{cr}{rr}")
            paint(ws, f"{cl}{rr}:{cr}{rr}", f=FILL_WHITE)
        ws[f"{cl}{r}"] = label
        ws[f"{cl}{r}"].font = T.font(8, True, SECONDARY)
        ws[f"{cl}{r}"].alignment = CENTER
        ws[f"{cl}{r + 1}"] = formula
        ws[f"{cl}{r + 1}"].font = T.font(20, True, color)
        ws[f"{cl}{r + 1}"].alignment = CENTER
        ws[f"{cl}{r + 1}"].number_format = numfmt
        if sub:
            ws[f"{cl}{r + 2}"] = sub
        ws[f"{cl}{r + 2}"].font = T.font(8, False, SECONDARY, italic=True)
        ws[f"{cl}{r + 2}"].alignment = CENTER
        top = Side(style="medium", color=color)
        for cc in range(c, c2 + 1):
            ws.cell(row=r, column=cc).border = Border(top=top, left=THIN if cc == c else None, right=THIN if cc == c2 else None)
            ws.cell(row=r + 1, column=cc).border = Border(left=THIN if cc == c else None, right=THIN if cc == c2 else None)
            ws.cell(row=r + 2, column=cc).border = Border(bottom=THIN, left=THIN if cc == c else None, right=THIN if cc == c2 else None)

    def merge_style(self, ws, a, value=None, font=None, f=None, align=None, numfmt=None, border=BOX):
        if ":" in a and a.split(":")[0] != a.split(":")[1]:
            ws.merge_cells(a)
        paint(ws, a, f=f, border=border)
        first = a.split(":")[0]
        if value is not None:
            ws[first] = value
        if font is not None:
            ws[first].font = font
        if align is not None:
            ws[first].alignment = align
        if numfmt:
            ws[first].number_format = numfmt

    def nav_links(self, ws, r, c1, per_row, span, skip=None):
        T = self.T
        targets = [n for n in ORDER if n != skip]
        for i, n in enumerate(targets):
            rr = r + i // per_row
            cc = c1 + (i % per_row) * span
            a = f"{L(cc)}{rr}:{L(cc + span - 1)}{rr}"
            ws.merge_cells(a)
            paint(ws, a, f=fill(SOFT_BLUE), border=Border(left=Side(style="thin", color=WHITE), right=Side(style="thin", color=WHITE)))
            cell = ws[f"{L(cc)}{rr}"]
            cell.value = f'=HYPERLINK("#{quote(n)}!A1","{n}")'
            cell.font = T.font(9, True, MIDNIGHT)
            cell.alignment = CENTER

    # ================================================================ TAB 1 SETUP
    def build_setup(self):
        ws, T = self.ws[S_SETUP], self.T
        setup_sheet(ws, {"B": 26, "C": 26, **{L(i): 20 for i in range(4, 17)}})
        title_bar(ws, T, "SETUP  ·  Workspace Configuration", "Start here — every dropdown and calculation in the workbook reads from this tab.", 15, demo=self.demo)
        self.merge_style(ws, "B5:O8", border=None, f=fill(SOFT_BLUE),
                         value=("WELCOME TO THE ULTIMATE PROJECT MANAGER.   1) Fill in your workspace details below.   "
                                "2) Edit the dropdown lists (team members, categories…).   3) Add projects on 'Project Overview', "
                                "tasks on 'Variable Tasks' and 'Recurring Tasks'.   Dashboards, calendars, Kanban and Gantt update automatically.   "
                                "Light-blue cells are inputs; grey cells are formulas — don't type over them. "
                                + ("This copy contains DEMO DATA: see Instructions › 'Removing demo data'." if self.demo else "")),
                         font=T.font(10, False, MIDNIGHT), align=LEFT_WRAP)
        legend(ws, T, 9, 2)
        section(ws, T, 10, 2, 5, "WORKSPACE & PREFERENCES")
        prefs = [
            ("Your name", "Alex Morgan" if self.demo else None, None, "Shown on dashboards"),
            ("Workspace / company", "Northwind Studio (demo)" if self.demo else None, None, ""),
            ("Role / title", "Operations Director" if self.demo else None, None, ""),
            ("Email", "alex@example.com" if self.demo else None, None, ""),
            ("Currency", "USD", "cur", "Pick from list"),
            ("Currency symbol", f'=IFERROR(INDEX({SS("C")},MATCH(C15,{SS("B")},0)),"$")', "calc", "Automatic"),
            ("Week starts on", "Monday", "week", "Used by Monthly Calendar"),
            ("Default year", "=YEAR(C20)", "year", "Pre-selects calendar years (formula = current year; pick to override)"),
            ("Today's date override", None, "date", "Leave blank to use the real date"),
            ("Effective today", '=IF(C19="",TODAY(),C19)', "calc", "Drives every 'today' calculation"),
            ("Due-soon window (days)", 7, "int", "Tasks due within N days turn amber"),
            ("Budget alert threshold", 0.9, "pct", "Spend ≥ this % of plan = alert"),
            ("Date display format", "mmm d, yyyy", "info", "Change via Format Cells if needed"),
        ]
        for i, (lab, val, kind, hint) in enumerate(prefs):
            r = 11 + i
            ws[f"B{r}"] = lab
            ws[f"B{r}"].font = T.font(10, True)
            ws[f"B{r}"].border = BOX
            ws[f"C{r}"] = val
            if kind in ("calc",):
                self.calc(S_SETUP, f"C{r}", numfmt=FMT_DATE if "today" in lab.lower() else None)
            elif kind == "info":
                paint(ws, f"C{r}", f=FILL_WHITE, font=T.font(10), border=BOX, align=LEFT)
            else:
                self.inp(S_SETUP, f"C{r}", numfmt={"date": FMT_DATE, "pct": FMT_PCT, "int": "0"}.get(kind))
            ws.merge_cells(f"D{r}:E{r}")
            ws[f"D{r}"] = hint
            ws[f"D{r}"].font = T.font(9, False, SECONDARY, italic=True)
        add_list_dv(ws, "C15", SS("B"))
        add_list_dv(ws, "C17", SS("I"))
        add_list_dv(ws, "C18", SS("H"))
        add_dv(ws, "C19", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a valid date, or leave blank.")
        add_dv(ws, "C21", "whole", "between", "0", "60")
        add_dv(ws, "C22", "decimal", "between", "0", "2")

        # status logic reference box
        section(ws, T, 10, 7, 15, "HOW THE STATUS LISTS ARE USED", color=LAVENDER)
        txt = [
            "• Task Statuses: the first five entries become the five Kanban columns (in order). The 5th entry (default 'Completed') means DONE everywhere.",
            "• Project Statuses: 2nd + 3rd entries (Planning, In Progress) count as ACTIVE; 5th = completed; 6th = cancelled.",
            "• Priority Levels: 1st = Critical (‼ on Kanban), 2nd = High (▲). Rename freely — keep the order.",
            "• Team Members: names appear in every 'Assigned To' / 'Project Manager' dropdown.",
            "• Project Detail Types feed the Objectives / Deliverables / Milestones / Dependencies / Risks / Notes panels on 'Project Manager'.",
            "• You can rename any list item; existing rows keep the old text, so update them too (Find & Replace).",
            "• 20 slots per list. Leave unused slots empty.",
        ]
        for i, t in enumerate(txt):
            r = 11 + i
            ws.merge_cells(f"G{r}:O{r}")
            ws[f"G{r}"] = t
            ws[f"G{r}"].font = T.font(9, False, DARK)
            ws[f"G{r}"].alignment = Alignment(vertical="center", wrap_text=True)
            ws.row_dimensions[r].height = 26

        section(ws, T, 25, 2, 12, "DROPDOWN LISTS  —  edit freely (20 slots each)")
        for c, (head, items) in LISTS.items():
            ws[f"{c}26"] = head
            ws[f"{c}26"].font = T.font(10, True, WHITE)
            ws[f"{c}26"].fill = fill(MIDNIGHT)
            ws[f"{c}26"].alignment = CENTER
            if c in ("G", "H", "I") and not self.demo:
                items = ["Me"] if c == "G" else []
            for i in range(LRN - LR1 + 1):
                cell = ws[f"{c}{LR1 + i}"]
                cell.value = items[i] if i < len(items) else None
            self.inp(S_SETUP, f"{c}{LR1}:{c}{LRN}")
        add_list_dv(ws, f"I{LR1}:I{LRN}", SL("J"))
        for c, color in (("E", TEAL), ("F", TEAL)):
            ws[f"{c}{LR1 + 4}"].font = T.font(10, True, color)

        section(ws, T, 49, 2, 15, "SYSTEM LISTS  —  used by formulas; edit with care", color=LAVENDER)
        for c, (head, items) in SYSTEM.items():
            ws[f"{c}50"] = head
            ws[f"{c}50"].font = T.font(10, True, WHITE)
            ws[f"{c}50"].fill = fill(LAVENDER)
            ws[f"{c}50"].alignment = CENTER
            for i in range(SRN - SR1 + 1):
                ws[f"{c}{SR1 + i}"] = items[i] if i < len(items) else None
            paint(ws, f"{c}{SR1}:{c}{SRN}", f=FILL_OPT, font=T.font(10), border=BOX, align=LEFT)
        ws.freeze_panes = "A4"

        names = {
            TODAY: "$C$20", "CurrencySymbol": "$C$16", "DueSoonDays": "$C$21", "BudgetAlert": "$C$22", "WeekStart": "$C$17",
            DONE: f"$E${LR1 + 4}", P_DONE: f"$F${LR1 + 4}", P_CANCEL: f"$F${LR1 + 5}",
            "TaskStatusList": f"$E${LR1}:$E${LRN}", "PriorityList": f"$D${LR1}:$D${LRN}", "TeamList": f"$G${LR1}:$G${LRN}",
        }
        for n, a in names.items():
            self.wb.defined_names[n] = DefinedName(n, attr_text=f"{S_SETUP}!{a}")

    # ================================================================ TAB 5 PROJECT OVERVIEW
    def build_pov(self):
        ws, T = self.ws[S_POV], self.T
        heads = ["Project ID", "Project Name", "Description", "Category", "Project Manager", "Start Date", "Due Date", "Priority",
                 "Status", "Progress", "Budget", "Actual Cost", "Remaining Budget", "Days Remaining",
                 "Tasks", "Done Tasks", "Overdue Tasks", "Health", "Deadline Key", "Row No", "Due Rank"]
        widths = [10, 31, 54, 25, 18, 15, 15, 11, 13, 11, 13, 13, 14, 12, 9, 9, 10, 13, 12, 8, 12]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        title_bar(ws, T, "PROJECT OVERVIEW  ·  Portfolio", "One row per project. Progress, budget and task counts are calculated automatically.", 22, demo=self.demo)
        legend(ws, T, 4, 2)
        ws["P4"] = "Currency:"
        ws["Q4"] = "=CurrencySymbol"
        ws["P4"].font = ws["Q4"].font = T.font(9, True, SECONDARY)
        header_row(ws, T, HDR, 2, heads)
        for c in "PQRSTUV":
            ws[f"{c}{HDR}"].fill = fill(MED_GRAY)
        ws[f"P{HDR - 1}"] = "AUTOMATION HELPERS (calculated)"
        ws[f"P{HDR - 1}"].font = T.font(8, True, SECONDARY)
        last = POV_LAST
        for i in range(POV_N):
            ws[f"B{R1 + i}"] = f"P-{i + 1:03d}"
        self.calc(S_POV, f"B{R1}:B{last}", align=CENTER, color=SECONDARY)
        self.inp(S_POV, f"C{R1}:J{last}")
        for c, f_ in (("G", FMT_DATE), ("H", FMT_DATE)):
            paint(ws, f"{c}{R1}:{c}{last}", numfmt=f_)
        D = DONE
        self.fill_down(ws, "K", R1, last, f'=IF(C{{r}}="","",IF(J{{r}}={P_DONE},1,IFERROR(AVERAGEIFS({VT("Z")},{VT("E")},C{{r}}),0)))')
        self.fill_down(ws, "L", R1, last, f'=IF(C{{r}}="","",SUMIFS({PB("E")},{PB("B")},B{{r}}))')
        self.fill_down(ws, "M", R1, last, f'=IF(C{{r}}="","",SUMIFS({PB("F")},{PB("B")},B{{r}}))')
        self.fill_down(ws, "N", R1, last, '=IF(C{r}="","",L{r}-M{r})')
        self.fill_down(ws, "O", R1, last, f'=IF(OR(C{{r}}="",H{{r}}=""),"",IF(OR(J{{r}}={P_DONE},J{{r}}={P_CANCEL}),"—",H{{r}}-{TODAY}))')
        self.fill_down(ws, "P", R1, last, f'=IF(C{{r}}="","",COUNTIFS({VT("E")},C{{r}},{VT("C")},"?*"))')
        self.fill_down(ws, "Q", R1, last, f'=IF(C{{r}}="","",COUNTIFS({VT("E")},C{{r}},{VT("K")},{D}))')
        self.fill_down(ws, "R", R1, last, f'=IF(C{{r}}="","",COUNTIFS({VT("E")},C{{r}},{VT("P")},"Overdue"))')
        self.fill_down(ws, "S", R1, last,
                       f'=IF(C{{r}}="","",IF(J{{r}}={P_DONE},"Completed",IF(J{{r}}={P_CANCEL},"Cancelled",'
                       f'IF(AND(H{{r}}<>"",H{{r}}<{TODAY}),"Overdue",IF(AND(L{{r}}>0,M{{r}}>L{{r}}),"Over budget",'
                       f'IF(R{{r}}>0,"At risk","On track"))))))')
        self.fill_down(ws, "T", R1, last, '=IF(OR(C{r}="",H{r}=""),"",INT(H{r})&"|"&COUNTIFS(H$7:H{r},H{r},C$7:C{r},"?*"))')
        self.fill_down(ws, "U", R1, last, '=IF(C{r}="","",COUNTIF(C$7:C{r},"?*"))')
        self.fill_down(ws, "V", R1, last, '=IF(OR(C{r}="",H{r}=""),"",H{r}+ROW()/100000)')
        self.calc(S_POV, f"K{R1}:V{last}")
        paint(ws, f"V{R1}:V{last}", numfmt="0.00")
        paint(ws, f"K{R1}:K{last}", numfmt=FMT_PCT)
        paint(ws, f"L{R1}:N{last}", numfmt=FMT_CUR)
        paint(ws, f"O{R1}:R{last}", numfmt="0", align=CENTER)
        add_list_dv(ws, f"E{R1}:E{last}", SL("B"))
        add_list_dv(ws, f"F{R1}:F{last}", SL("G"))
        add_list_dv(ws, f"I{R1}:I{last}", SL("D"))
        add_list_dv(ws, f"J{R1}:J{last}", SL("F"))
        add_dv(ws, f"G{R1}:H{last}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a valid date.")
        cf_databar(ws, f"K{R1}:K{last}", TEAL)
        a = f"B{R1}:U{last}"
        cf_formula(ws, f"O{R1}:O{last}", f'AND(ISNUMBER(O{R1}),O{R1}<0)', DANGER_BG, DANGER, True)
        cf_formula(ws, f"N{R1}:N{last}", f'AND(ISNUMBER(N{R1}),N{R1}<0)', DANGER_BG, DANGER, True)
        for txt, bg, fg in (("Completed", SUCCESS_BG, SUCCESS), ("Overdue", DANGER_BG, DANGER), ("Over budget", DANGER_BG, DANGER),
                            ("At risk", WARNING_BG, WARNING), ("On track", INFO_BG, INFO), ("Cancelled", LIGHT_GRAY, SECONDARY)):
            cf_formula(ws, f"S{R1}:S{last}", f'S{R1}="{txt}"', bg, fg, True)
        ws.freeze_panes = f"D{R1}"
        self.table(ws, "tblProjects", f"B{HDR}:V{last}")
        if self.demo:
            for i, p in enumerate(SD.PROJECTS):
                r = R1 + i
                for c, v in zip("CDEFGHIJ", p):
                    ws[f"{c}{r}"] = v

    # ================================================================ TAB 8 VARIABLE TASKS
    def build_vt(self):
        ws, T = self.ws[S_VT], self.T
        heads = ["Task ID", "Task Name", "Description", "Project", "Category", "Assigned To", "Start Date", "Due Date", "Priority",
                 "Status", "Estimated Hours", "Actual Hours", "Progress", "Notes",
                 "Deadline Flag", "Days Left", "Due Key", "Status Key", "Upcoming Rank", "Overdue Rank", "Filter No",
                 "Gantt No", "Done", "Recent Rank", "Effective Progress"]
        widths = [9, 28, 54, 31, 14, 17, 15, 15, 10, 12, 10, 10, 10, 26, 11, 9, 11, 17, 12, 12, 8, 8, 6, 12, 10]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        title_bar(ws, T, "VARIABLE TASKS  ·  One-time task database", "Add one task per row. Everything else in the workbook reads from this table.", 26, demo=self.demo)
        legend(ws, T, 4, 2)
        header_row(ws, T, HDR, 2, heads)
        for i in range(15, 27):
            ws.cell(row=HDR, column=i).fill = fill(MED_GRAY)
        ws[f"P{HDR - 1}"] = "AUTOMATION HELPERS (calculated — do not edit)"
        ws[f"P{HDR - 1}"].font = T.font(8, True, SECONDARY)
        last = VT_LAST
        for i in range(VT_N):
            ws[f"B{R1 + i}"] = f"T-{i + 1:03d}"
        self.calc(S_VT, f"B{R1}:B{last}", align=CENTER, color=SECONDARY)
        self.inp(S_VT, f"C{R1}:O{last}")
        paint(ws, f"H{R1}:I{last}", numfmt=FMT_DATE)
        paint(ws, f"L{R1}:M{last}", numfmt=FMT_HRS, align=CENTER)
        paint(ws, f"N{R1}:N{last}", numfmt=FMT_PCT, align=CENTER)
        TF = quote(S_TF)
        GC = quote(S_GC)
        f_ = {
            "P": f'=IF(OR(C{{r}}="",I{{r}}="",K{{r}}={DONE}),"",IF(I{{r}}<{TODAY},"Overdue",IF(I{{r}}-{TODAY}<=DueSoonDays,"Due soon","")))',
            "Q": f'=IF(OR(C{{r}}="",I{{r}}=""),"",I{{r}}-{TODAY})',
            "R": '=IF(OR(C{r}="",I{r}=""),"",INT(I{r})&"|"&COUNTIFS(I$7:I{r},I{r},C$7:C{r},"?*"))',
            "S": '=IF(OR(C{r}="",K{r}=""),"",K{r}&"|"&COUNTIFS(K$7:K{r},K{r},C$7:C{r},"?*"))',
            "T": f'=IF(AND(C{{r}}<>"",I{{r}}<>"",K{{r}}<>{DONE}),IF(I{{r}}>={TODAY},I{{r}}+ROW()/100000,""),"")',
            "U": '=IF(P{r}="Overdue",I{r}+ROW()/100000,"")',
            "V": (f'=IF(AND(C{{r}}<>"",OR({TF}!$C$6="",E{{r}}={TF}!$C$6),OR({TF}!$C$7="",J{{r}}={TF}!$C$7),'
                  f'OR({TF}!$C$8="",K{{r}}={TF}!$C$8),OR({TF}!$C$9="",F{{r}}={TF}!$C$9),OR({TF}!$C$10="",G{{r}}={TF}!$C$10),'
                  f'OR({TF}!$C$11="",AND(I{{r}}<>"",I{{r}}>={TF}!$C$11)),OR({TF}!$C$12="",AND(I{{r}}<>"",I{{r}}<={TF}!$C$12)),'
                  f'OR({TF}!$C$13="",AND({TF}!$C$13="Complete",K{{r}}={DONE}),AND({TF}!$C$13="Incomplete",K{{r}}<>{DONE})),'
                  f'OR({TF}!$C$14="",AND({TF}!$C$14="Overdue only",P{{r}}="Overdue"),AND({TF}!$C$14="Not overdue",P{{r}}<>"Overdue")),'
                  f'OR({TF}!$C$15="",ISNUMBER(SEARCH({TF}!$C$15,C{{r}}&" "&D{{r}}&" "&O{{r}})))),MAX(V$6:V{{p}})+1,"")'),
            "W": (f'=IF(AND(C{{r}}<>"",H{{r}}<>"",I{{r}}<>"",OR({GC}!$C$5="",E{{r}}={GC}!$C$5),'
                  f'OR({GC}!$J$5<>"Yes",K{{r}}<>{DONE})),MAX(W$6:W{{p}})+1,"")'),
            "X": f'=IF(C{{r}}="","",IF(K{{r}}={DONE},1,0))',
            "Y": f'=IF(AND(C{{r}}<>"",H{{r}}<>""),IF(H{{r}}<={TODAY},H{{r}}+ROW()/100000,""),"")',
            "Z": f'=IF(C{{r}}="","",IF(K{{r}}={DONE},1,IF(N{{r}}="",0,N{{r}})))',
        }
        for c, tpl in f_.items():
            self.fill_down(ws, c, R1, last, tpl)
        self.calc(S_VT, f"P{R1}:Z{last}")
        paint(ws, f"Z{R1}:Z{last}", numfmt=FMT_PCT)
        paint(ws, f"T{R1}:U{last}", numfmt="0.00")
        paint(ws, f"Y{R1}:Y{last}", numfmt="0.00")
        add_list_dv(ws, f"E{R1}:E{last}", POV("C"))
        add_list_dv(ws, f"F{R1}:F{last}", SL("C"))
        add_list_dv(ws, f"G{R1}:G{last}", SL("G"))
        add_list_dv(ws, f"J{R1}:J{last}", SL("D"))
        add_list_dv(ws, f"K{R1}:K{last}", SL("E"))
        add_dv(ws, f"H{R1}:I{last}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a valid date.")
        add_dv(ws, f"N{R1}:N{last}", "decimal", "between", "0", "1", error="Progress is a percentage between 0% and 100%.")
        add_dv(ws, f"L{R1}:M{last}", "decimal", "greaterThanOrEqual", "0", error="Hours must be zero or more.")
        cf_databar(ws, f"N{R1}:N{last}", TEAL)
        cf_formula(ws, f"C{R1}:O{last}", f'$P{R1}="Overdue"', None, DANGER)
        cf_formula(ws, f"P{R1}:P{last}", f'P{R1}="Overdue"', DANGER_BG, DANGER, True)
        cf_formula(ws, f"P{R1}:P{last}", f'P{R1}="Due soon"', WARNING_BG, WARNING, True)
        cf_formula(ws, f"K{R1}:K{last}", f'$X{R1}=1', SUCCESS_BG, SUCCESS, True)
        for p, (bg, fg) in zip(LISTS["D"][1], ((DANGER_BG, DANGER), (WARNING_BG, WARNING), (INFO_BG, INFO), (SOFT_TEAL, SUCCESS))):
            cf_formula(ws, f"J{R1}:J{last}", f'J{R1}="{p}"', bg, fg, True)
        ws.freeze_panes = f"D{R1}"
        self.table(ws, "tblTasks", f"B{HDR}:Z{last}")
        if self.demo:
            for i, t in enumerate(SD.build_tasks()):
                r = R1 + i
                vals = [t["name"], t["desc"], t["project"], t["cat"], t["who"], t["start"], t["due"], t["pri"], t["status"],
                        t["est"], t["act"], t["prog"], t["notes"]]
                for c, v in zip("CDEFGHIJKLMNO", vals):
                    ws[f"{c}{r}"] = v

    # ================================================================ TAB 7 PROJECT BUDGET
    def build_pb(self):
        ws, T = self.ws[S_PB], self.T
        heads = ["Project ID", "Project Name", "Budget Category", "Planned Budget", "Actual Expenses", "Remaining Budget",
                 "Budget Utilization", "Expense Date", "Vendor", "Description", "Budget Alert"]
        widths = [11, 31, 16, 14, 14, 15, 12, 15, 20, 32, 14, 3, 20, 14, 14, 14, 12]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        title_bar(ws, T, "PROJECT BUDGET  ·  Planned vs actual", "One row per budget line or expense. Totals roll up to Project Overview and the Dashboard.", 18, demo=self.demo)
        legend(ws, T, 4, 2)
        header_row(ws, T, HDR, 2, heads)
        last = PB_LAST
        self.inp(S_PB, f"B{R1}:B{last}", align=CENTER)
        self.inp(S_PB, f"D{R1}:F{last}")
        self.inp(S_PB, f"I{R1}:K{last}")
        paint(ws, f"E{R1}:F{last}", numfmt=FMT_CUR)
        paint(ws, f"I{R1}:I{last}", numfmt=FMT_DATE)
        self.fill_down(ws, "C", R1, last, f'=IF(B{{r}}="","",IFERROR(INDEX({POV("C")},MATCH(B{{r}},{POV("B")},0)),"Unknown ID"))')
        self.fill_down(ws, "G", R1, last, '=IF(AND(E{r}="",F{r}=""),"",N(E{r})-N(F{r}))')
        self.fill_down(ws, "H", R1, last, '=IF(N(E{r})=0,"",N(F{r})/E{r})')
        self.fill_down(ws, "L", R1, last, '=IF(AND(E{r}="",F{r}=""),"",IF(N(F{r})>N(E{r}),"Over budget",IF(AND(N(E{r})>0,N(F{r})/N(E{r})>=BudgetAlert),"Near limit","OK")))')
        self.calc(S_PB, f"C{R1}:C{last}")
        self.calc(S_PB, f"G{R1}:H{last}")
        self.calc(S_PB, f"L{R1}:L{last}", align=CENTER)
        paint(ws, f"G{R1}:G{last}", numfmt=FMT_CUR)
        paint(ws, f"H{R1}:H{last}", numfmt=FMT_PCT, align=CENTER)
        add_list_dv(ws, f"B{R1}:B{last}", POV("B"))
        add_list_dv(ws, f"D{R1}:D{last}", SL("K"))
        add_dv(ws, f"E{R1}:F{last}", "decimal", "greaterThanOrEqual", "0", error="Amounts must be zero or more.")
        add_dv(ws, f"I{R1}:I{last}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a valid date.")
        cf_formula(ws, f"L{R1}:L{last}", f'L{R1}="Over budget"', DANGER_BG, DANGER, True)
        cf_formula(ws, f"L{R1}:L{last}", f'L{R1}="Near limit"', WARNING_BG, WARNING, True)
        cf_formula(ws, f"L{R1}:L{last}", f'L{R1}="OK"', SUCCESS_BG, SUCCESS, True)
        cf_formula(ws, f"G{R1}:G{last}", f'AND(ISNUMBER(G{R1}),G{R1}<0)', DANGER_BG, DANGER, True)
        cf_databar(ws, f"H{R1}:H{last}", BLUE)
        # summary panel N:R
        section(ws, T, HDR - 1, 14, 18, "BUDGET SUMMARY  (currency: see Setup)")
        tot = [("Total planned", f"=SUM(E{R1}:E{last})", FMT_CUR), ("Total actual", f"=SUM(F{R1}:F{last})", FMT_CUR),
               ("Remaining", f"=O{HDR}-O{HDR + 1}", FMT_CUR), ("Utilization", f'=IF(O{HDR}=0,0,O{HDR + 1}/O{HDR})', FMT_PCT),
               ("Lines over budget", f'=COUNTIF(L{R1}:L{last},"Over budget")', "0"), ("Lines near limit", f'=COUNTIF(L{R1}:L{last},"Near limit")', "0")]
        for i, (lab, fm, nf) in enumerate(tot):
            r = HDR + i
            ws[f"N{r}"] = lab
            ws[f"N{r}"].font = T.font(10, True)
            ws[f"N{r}"].border = BOX
            ws[f"O{r}"] = fm
            self.calc(S_PB, f"O{r}", numfmt=nf, align=RIGHT)
        cf_formula(ws, f"O{HDR + 2}", f"O{HDR + 2}<0", DANGER_BG, DANGER, True)
        header_row(ws, T, 14, 14, ["Category", "Planned", "Actual", "Remaining", "Used %"], color=MIDNIGHT)
        for i in range(10):
            r = 15 + i
            ws[f"N{r}"] = f"={SC('K', LR1 + i)}&\"\""
            ws[f"O{r}"] = f'=IF(N{r}="","",SUMIFS($E${R1}:$E${last},$D${R1}:$D${last},N{r}))'
            ws[f"P{r}"] = f'=IF(N{r}="","",SUMIFS($F${R1}:$F${last},$D${R1}:$D${last},N{r}))'
            ws[f"Q{r}"] = f'=IF(N{r}="","",O{r}-P{r})'
            ws[f"R{r}"] = f'=IF(OR(N{r}="",N(O{r})=0),"",P{r}/O{r})'
        self.calc(S_PB, "N15:R24")
        paint(ws, "O15:Q24", numfmt=FMT_CUR)
        paint(ws, "R15:R24", numfmt=FMT_PCT)
        cf_formula(ws, "Q15:Q24", 'AND(ISNUMBER(Q15),Q15<0)', DANGER_BG, DANGER, True)
        ws.freeze_panes = f"D{R1}"
        self.table(ws, "tblBudget", f"B{HDR}:L{last}")
        if self.demo:
            for i, (pi, cat, pl, ac, off, ven, desc) in enumerate(SD.BUDGET):
                r = R1 + i
                ws[f"B{r}"] = f"P-{pi:03d}"
                ws[f"D{r}"] = cat
                ws[f"E{r}"] = pl
                ws[f"F{r}"] = ac if ac else None
                ws[f"I{r}"] = SD.d(off)
                ws[f"J{r}"] = ven
                ws[f"K{r}"] = desc

    # ================================================================ TAB 9 RECURRING TASKS
    def build_rt(self):
        ws, T = self.ws[S_RT], self.T
        heads = ["Task ID", "Task Name", "Project", "Category", "Assigned To", "Frequency", "Custom Interval (days)", "Start Date",
                 "End Date", "Priority", "Status", "Last Completed", "Next Occurrence", "Days Until", "Occurrences This Month",
                 "Times Completed", "Notes", "Unit", "Step", "Base Date", "Month Steps", "Raw Next"]
        widths = [9, 26, 27, 14, 17, 12, 11, 15, 15, 10, 10, 15, 15, 9, 12, 11, 24, 6, 6, 14, 8, 14]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        title_bar(ws, T, "RECURRING TASKS  ·  Repeating work", "Daily, weekly, biweekly, monthly, quarterly, annual or custom (every N days). Next dates calculate automatically.", 23, demo=self.demo)
        legend(ws, T, 4, 2)
        ws["P4"] = "This month:"
        ws["Q4"] = f"=DATE(YEAR({TODAY}),MONTH({TODAY}),1)"
        ws["R4"] = f"=EOMONTH({TODAY},0)"
        ws["P4"].font = T.font(9, True, SECONDARY)
        for c in ("Q4", "R4"):
            ws[c].number_format = FMT_SDATE
            ws[c].font = T.font(9, False, SECONDARY)
        header_row(ws, T, HDR, 2, heads)
        for i in range(19, 24):
            ws.cell(row=HDR, column=i).fill = fill(MED_GRAY)
        last = RT_LAST
        for i in range(RT_N):
            ws[f"B{R1 + i}"] = f"R-{i + 1:03d}"
        self.calc(S_RT, f"B{R1}:B{last}", align=CENTER, color=SECONDARY)
        self.inp(S_RT, f"C{R1}:M{last}")
        self.inp(S_RT, f"Q{R1}:R{last}")
        paint(ws, f"I{R1}:J{last}", numfmt=FMT_DATE)
        paint(ws, f"M{R1}:M{last}", numfmt=FMT_DATE)
        paint(ws, f"H{R1}:H{last}", align=CENTER)
        F = {
            "S": f'=IF(G{{r}}="","",IFERROR(INDEX({SS("E")},MATCH(G{{r}},{SS("D")},0)),""))',
            "T": f'=IF(G{{r}}="","",IF(G{{r}}={CUSTOM_FREQ},IF(N(H{{r}})>0,H{{r}},""),IFERROR(INDEX({SS("F")},MATCH(G{{r}},{SS("D")},0)),"")))',
            "U": f'=IF(C{{r}}="","",MAX({TODAY},IF(M{{r}}="",0,M{{r}}+1)))',
            "V": '=IF(OR(S{r}<>"M",I{r}="",T{r}="",U{r}=""),"",MAX(0,INT(((YEAR(U{r})-YEAR(I{r}))*12+MONTH(U{r})-MONTH(I{r}))/T{r})))',
            "W": ('=IF(OR(C{r}="",I{r}="",T{r}="",U{r}=""),"",IF(S{r}="M",IF(EDATE(I{r},T{r}*V{r})>=U{r},EDATE(I{r},T{r}*V{r}),EDATE(I{r},T{r}*(V{r}+1))),'
                  'IF(I{r}>=U{r},I{r},I{r}+ROUNDUP((U{r}-I{r})/T{r},0)*T{r})))'),
            "N": f'=IF(C{{r}}="","",IF(L{{r}}={PAUSED},"Paused",IF(W{{r}}="","Check setup",IF(AND(J{{r}}<>"",W{{r}}>J{{r}}),"Ended",W{{r}}))))',
            "O": f'=IF(ISNUMBER(N{{r}}),N{{r}}-{TODAY},"")',
            "P": ('=IF(OR(C{r}="",I{r}="",T{r}="",L{r}=' + PAUSED + '),"",IF(S{r}="M",'
                  'IF(AND((YEAR($Q$4)-YEAR(I{r}))*12+MONTH($Q$4)-MONTH(I{r})>=0,MOD((YEAR($Q$4)-YEAR(I{r}))*12+MONTH($Q$4)-MONTH(I{r}),T{r})=0,'
                  'EDATE(I{r},(YEAR($Q$4)-YEAR(I{r}))*12+MONTH($Q$4)-MONTH(I{r}))<=IF(J{r}="",$R$4,MIN($R$4,J{r}))),1,0),'
                  'IF(IF(J{r}="",$R$4,MIN($R$4,J{r}))<I{r},0,MAX(0,INT((IF(J{r}="",$R$4,MIN($R$4,J{r}))-I{r})/T{r})-MAX(0,ROUNDUP(($Q$4-I{r})/T{r},0))+1))))'),
        }
        for c, tpl in F.items():
            self.fill_down(ws, c, R1, last, tpl)
        self.calc(S_RT, f"N{R1}:P{last}", align=CENTER)
        self.calc(S_RT, f"S{R1}:W{last}", align=CENTER)
        paint(ws, f"N{R1}:N{last}", numfmt=FMT_DATE)
        paint(ws, f"U{R1}:U{last}", numfmt=FMT_DATE)
        paint(ws, f"W{R1}:W{last}", numfmt=FMT_DATE)
        add_list_dv(ws, f"D{R1}:D{last}", POV("C"))
        add_list_dv(ws, f"E{R1}:E{last}", SL("C"))
        add_list_dv(ws, f"F{R1}:F{last}", SL("G"))
        add_list_dv(ws, f"G{R1}:G{last}", SS("D"))
        add_list_dv(ws, f"K{R1}:K{last}", SL("D"))
        add_list_dv(ws, f"L{R1}:L{last}", SS("N"))
        add_dv(ws, f"H{R1}:H{last}", "whole", "between", "1", "3650", error="Custom interval = number of days (1–3650).")
        add_dv(ws, f"I{R1}:J{last}", "date", "greaterThan", "DATE(2000,1,1)")
        add_dv(ws, f"M{R1}:M{last}", "date", "greaterThan", "DATE(2000,1,1)")
        cf_formula(ws, f"O{R1}:O{last}", f'AND(ISNUMBER(O{R1}),O{R1}=0)', WARNING_BG, WARNING, True)
        cf_formula(ws, f"O{R1}:O{last}", f'AND(ISNUMBER(O{R1}),O{R1}<=3)', INFO_BG, INFO, True)
        cf_formula(ws, f"N{R1}:N{last}", f'OR(N{R1}="Paused",N{R1}="Ended")', LIGHT_GRAY, SECONDARY)
        cf_formula(ws, f"N{R1}:N{last}", f'N{R1}="Check setup"', DANGER_BG, DANGER, True)
        ws.freeze_panes = f"D{R1}"
        self.table(ws, "tblRecurring", f"B{HDR}:W{last}")
        if self.demo:
            for i, (n, pr, cat, who, fq, cu, so, eo, pri, st, lc, cnt) in enumerate(SD.RECURRING):
                r = R1 + i
                vals = [n, pr, cat, who, fq, cu, SD.d(so), SD.d(eo) if eo is not None else None, pri, st, SD.d(lc)]
                for c, v in zip("CDEFGHIJKLM", vals):
                    ws[f"{c}{r}"] = v
                ws[f"Q{r}"] = cnt

    # ================================================================ TAB 10 TASK SCHEDULE
    def build_ts(self):
        ws, T = self.ws[S_TS], self.T
        heads = ["Date", "Start Time", "End Time", "Task", "Project", "Priority", "Status", "Duration (hrs)", "Assigned Person",
                 "Notes", "Slot Key"]
        widths = [15, 12, 12, 28, 22, 10, 12, 10, 17, 26, 12]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        title_bar(ws, T, "TASK SCHEDULE  ·  Time blocks", "Block time for tasks. Pick a task from the dropdown — project, priority, status and owner fill in automatically. Feeds the Weekly Calendar.", 12, demo=self.demo)
        legend(ws, T, 4, 2)
        header_row(ws, T, HDR, 2, heads)
        ws.cell(row=HDR, column=12).fill = fill(MED_GRAY)
        last = TS_LAST
        self.inp(S_TS, f"B{R1}:E{last}")
        self.inp(S_TS, f"K{R1}:K{last}")
        paint(ws, f"B{R1}:B{last}", numfmt=FMT_DATE)
        paint(ws, f"C{R1}:D{last}", numfmt=FMT_TIME, align=CENTER)
        for c, src in (("F", "E"), ("G", "J"), ("H", "K"), ("J", "G")):
            self.fill_down(ws, c, R1, last, f'=IF(E{{r}}="","",IFERROR(INDEX({VT(src)},MATCH(E{{r}},{VT("C")},0))&"",""))')
        self.fill_down(ws, "I", R1, last, '=IF(OR(C{r}="",D{r}=""),"",ROUND(MOD(D{r}-C{r},1)*24,2))')
        self.fill_down(ws, "L", R1, last, '=IF(OR(B{r}="",C{r}="",E{r}=""),"",INT(B{r})&"|"&HOUR(C{r}))')
        self.calc(S_TS, f"F{R1}:J{last}")
        self.calc(S_TS, f"L{R1}:L{last}")
        paint(ws, f"I{R1}:I{last}", numfmt=FMT_HRS, align=CENTER)
        add_dv(ws, f"B{R1}:B{last}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a valid date.")
        add_dv(ws, f"C{R1}:D{last}", "time", "between", "0", "0.999988", error="Enter a time such as 9:00 AM.")
        add_list_dv(ws, f"E{R1}:E{last}", VT("C"), prompt="Pick a task, or type any event name (e.g. 'Lunch with client').", strict=False)
        for p, (bg, fg) in zip(LISTS["D"][1], ((DANGER_BG, DANGER), (WARNING_BG, WARNING), (INFO_BG, INFO), (SOFT_TEAL, SUCCESS))):
            cf_formula(ws, f"G{R1}:G{last}", f'G{R1}="{p}"', bg, fg, True)
        ws.freeze_panes = f"C{R1}"
        self.table(ws, "tblSchedule", f"B{HDR}:L{last}")
        if self.demo:
            monday = SD.ANCHOR - dt.timedelta(days=SD.ANCHOR.weekday())
            for i, (dd, h, m, dur, task) in enumerate(SD.SCHEDULE):
                r = R1 + i
                ws[f"B{r}"] = monday + dt.timedelta(days=dd)
                ws[f"C{r}"] = dt.time(h, m)
                eh = h + dur
                ws[f"D{r}"] = dt.time(eh, m)
                ws[f"E{r}"] = task

    # ================================================================ TAB 2 DASHBOARD
    def build_dash(self):
        import dashboard_pm as DP
        S = {"DASH": S_DASH}
        DP.Dash(self, S, VT, POV, PB, TS, SL, SS, SC, PSTAT, PRI, TODAY, DONE, P_DONE, TSTAT, ORDER, quote).build()

    # ================================================================ TAB 3 MONTHLY CALENDAR
    def build_mcal(self):
        ws, T = self.ws[S_MCAL], self.T
        setup_sheet(ws, {**{L(i): 21 for i in range(2, 9)}, "I": 3, "J": 24, "K": 12, **{L(i): 4 for i in range(16, 23)}})
        title_bar(ws, T, "MONTHLY CALENDAR", "Pick a year and month. Tasks due (by category colour), project deadlines (▲) and scheduled blocks appear automatically.", 11, demo=self.demo)
        for c, lab in (("B5", "YEAR"), ("D5", "MONTH")):
            ws[c] = lab
            ws[c].font = T.font(9, True, SECONDARY)
            ws[c].alignment = RIGHT
        ws["C5"] = f"={SC('C', 18)}"
        ws["E5"] = f'=INDEX({SS("G")},MONTH({TODAY}))'
        self.inp(S_MCAL, "C5", align=CENTER)
        self.inp(S_MCAL, "E5", align=CENTER)
        add_list_dv(ws, "C5", SS("H"))
        add_list_dv(ws, "E5", SS("G"))
        ws["F5"] = "Today"
        ws["G5"] = f"={TODAY}"
        ws["F5"].font = T.font(9, True, SECONDARY)
        ws["F5"].alignment = RIGHT
        self.calc(S_MCAL, "G5", FMT_DATE, CENTER)
        # calc cells row 6 (hidden-ish helpers)
        ws["J5"] = "Month #"
        ws["K5"] = f'=IFERROR(MATCH(E5,{SS("G")},0),MONTH({TODAY}))'
        ws["J6"] = "First of month"
        ws["K6"] = "=DATE(C5,K5,1)"
        ws["J7"] = "Grid start"
        ws["K7"] = f'=K6-MOD(WEEKDAY(K6)-IF(WeekStart="Sunday",1,2),7)'
        for r in (5, 6, 7):
            ws[f"J{r}"].font = T.font(8, False, SECONDARY)
            self.calc(S_MCAL, f"K{r}", FMT_SDATE if r > 5 else "0", CENTER)
        # Month banner
        ws.merge_cells("B7:H7")
        ws["B7"] = "=K6"
        ws["B7"].number_format = "mmmm yyyy"
        ws["B7"].font = T.font(16, True, NAVY)
        ws["B7"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[7].height = 28
        # day headers
        for d in range(7):
            c = L(2 + d)
            ws[f"{c}8"] = f"=K7+{d}"
            ws[f"{c}8"].number_format = "dddd"
            ws[f"{c}8"].fill = fill(NAVY)
            ws[f"{c}8"].font = T.font(10, True, WHITE)
            ws[f"{c}8"].alignment = CENTER
        ws.row_dimensions[8].height = 22
        rows_per = 5
        for w in range(6):
            base = 9 + w * rows_per
            for d in range(7):
                c = L(2 + d)
                hc = L(16 + d)  # helper column
                date_ref = f"{c}{base}"
                ws[date_ref] = f"=$K$7+{w * 7 + d}"
                ws[date_ref].number_format = "d"
                ws[date_ref].font = T.font(11, True, DARK)
                ws[date_ref].alignment = Alignment(horizontal="right", vertical="top", indent=1)
                inm = f"MONTH({date_ref})=$K$5"
                for k in (1, 2):
                    rr = base + k
                    ws[f"{c}{rr}"] = f'=IF({inm},IFERROR(INDEX({VT("C")},MATCH(INT({date_ref})&"|{k}",{VT("R")},0)),""),"")'
                    ws[f"{hc}{rr}"] = (f'=IF({c}{rr}="","",IF(AND({date_ref}<$G$5,INDEX({VT("K")},MATCH(INT({date_ref})&"|{k}",{VT("R")},0))<>{DONE}),-1,'
                                       f'IFERROR(MATCH(INDEX({VT("F")},MATCH(INT({date_ref})&"|{k}",{VT("R")},0)),{SL("C")},0),0)))')
                rr = base + 3
                ws[f"{c}{rr}"] = f'=IF({inm},IFERROR("▲ "&INDEX({POV("C")},MATCH(INT({date_ref})&"|1",{POV("T")},0)),""),"")'
                rr = base + 4
                cnt_t = f'COUNTIFS({VT("I")},{date_ref},{VT("C")},"?*")'
                cnt_s = f'COUNTIF({TS("B")},{date_ref})'
                ws[f"{c}{rr}"] = (f'=IF({inm},TRIM(IF({cnt_t}>2,"+"&({cnt_t}-2)&" more  ","")&IF({cnt_s}>0,"⏱ "&{cnt_s}&" scheduled","")),"")')
                for k in range(1, 5):
                    cell = ws[f"{c}{base + k}"]
                    cell.font = T.font(8 if k == 4 else 9, k == 3, SECONDARY if k == 4 else DARK)
                    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
                ws[f"{c}{base + 3}"].font = T.font(9, True, LAVENDER)
                for k in range(rows_per):
                    cell = ws[f"{c}{base + k}"]
                    cell.fill = FILL_WHITE
                    cell.border = Border(left=THIN, right=THIN, top=THIN if k == 0 else None, bottom=THIN if k == rows_per - 1 else None)
            ws.row_dimensions[base].height = 18
            for k in range(1, rows_per):
                ws.row_dimensions[base + k].height = 15
        grid = "B9:H38"
        # same-sheet conditional formatting
        cf_formula(ws, grid, "AND(ROW(B9)>=9,MOD(ROW(B9)-9,5)=0,B9=$G$5)", BLUE, WHITE, True, stop=True)
        cf_formula(ws, grid, "AND(MOD(ROW(B9)-9,5)=0,MONTH(B9)<>$K$5)", BG, MED_GRAY, stop=True)
        cf_formula(ws, grid, "P9=-1", DANGER_BG, DANGER, True, stop=True)
        cat_cols = [SOFT_BLUE, SOFT_TEAL, SOFT_LAV, WARNING_BG, INFO_BG, "E8F6F3", "FDF0E6", "EEF0F4"]
        for i, colr in enumerate(cat_cols):
            cf_formula(ws, grid, f'AND(ISNUMBER(P9),P9>0,MOD(P9-1,8)={i})', colr)
        for c in range(16, 23):
            ws.column_dimensions[L(c)].hidden = True
        # side panel stats
        section(ws, T, 9, 10, 11, "THIS MONTH")
        stats = [
            ("Tasks due", f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&K6,{VT("I")},"<"&EDATE(K6,1))', "0"),
            ("Completed", f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&K6,{VT("I")},"<"&EDATE(K6,1),{VT("K")},{DONE})', "0"),
            ("Still open", "=K10-K11", "0"),
            ("Overdue", f'=COUNTIFS({VT("P")},"Overdue",{VT("I")},">="&K6,{VT("I")},"<"&EDATE(K6,1))', "0"),
            ("Completion", '=IF(K10=0,0,K11/K10)', FMT_PCT),
            ("Project deadlines", f'=COUNTIFS({POV("H")},">="&K6,{POV("H")},"<"&EDATE(K6,1),{POV("C")},"?*")', "0"),
            ("Scheduled blocks", f'=COUNTIFS({TS("B")},">="&K6,{TS("B")},"<"&EDATE(K6,1))', "0"),
            ("Scheduled hours", f'=SUMIFS({TS("I")},{TS("B")},">="&K6,{TS("B")},"<"&EDATE(K6,1))', FMT_HRS),
        ]
        for i, (lab, fm, nf) in enumerate(stats):
            r = 10 + i
            ws[f"J{r}"] = lab
            ws[f"J{r}"].font = T.font(10)
            ws[f"J{r}"].border = BOX
            ws[f"K{r}"] = fm
            self.calc(S_MCAL, f"K{r}", nf, CENTER, color=BLUE)
        cf_formula(ws, "K13", "K13>0", DANGER_BG, DANGER, True)
        section(ws, T, 20, 10, 11, "LEGEND", color=LAVENDER)
        leg = [(BLUE, "Today"), (DANGER_BG, "Overdue task"), (BG, "Other month"), ("FFFFFF", "▲ Project deadline")]
        for i, (colr, t) in enumerate(leg):
            r = 21 + i
            ws[f"K{r}"].fill = fill(colr)
            ws[f"K{r}"].border = BOX
            ws[f"J{r}"] = t
            ws[f"J{r}"].font = T.font(9)
        ws["J26"] = "Task category colours:"
        ws["J26"].font = T.font(9, True, SECONDARY)
        for i in range(8):
            r = 27 + i
            ws[f"J{r}"] = f"={SC('C', LR1 + i)}&\"\""
            ws[f"J{r}"].font = T.font(9)
            ws[f"K{r}"].fill = fill(cat_cols[i])
            ws[f"K{r}"].border = BOX

    # ================================================================ TAB 4 WEEKLY CALENDAR
    def build_wcal(self):
        ws, T = self.ws[S_WCAL], self.T
        setup_sheet(ws, {"B": 13, **{L(i): 20 for i in range(3, 10)}, "J": 3, **{L(i): 4 for i in range(12, 19)}})
        title_bar(ws, T, "WEEKLY CALENDAR", "Type any date to jump to that week (blank = this week). Time blocks come from 'Task Schedule'; due dates from 'Variable Tasks'.", 9, demo=self.demo)
        ws["B5"] = "Show week of"
        ws["B5"].font = T.font(9, True, SECONDARY)
        ws["C5"] = None
        self.inp(S_WCAL, "C5", FMT_DATE, CENTER)
        add_dv(ws, "C5", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date, or leave blank for this week.")
        ws["B6"] = "Week starts"
        ws["B6"].font = T.font(9, True, SECONDARY)
        ws["C6"] = f'=IF(C5="",{TODAY},C5)-WEEKDAY(IF(C5="",{TODAY},C5),2)+1'
        self.calc(S_WCAL, "C6", FMT_DATE, CENTER)
        ws["B7"] = "Week #"
        ws["B7"].font = T.font(9, True, SECONDARY)
        ws["C7"] = "=WEEKNUM(C6,21)"
        self.calc(S_WCAL, "C7", "0", CENTER)
        ws["K3"] = "Today"
        ws["K4"] = f"={TODAY}"
        ws["K4"].number_format = FMT_SDATE
        # stats strip
        stats = [
            ("SCHEDULED HOURS", f'=SUMIFS({TS("I")},{TS("B")},">="&C6,{TS("B")},"<="&(C6+6))', FMT_HRS, BLUE),
            ("TASKS DUE", f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&C6,{VT("I")},"<="&(C6+6))', "0", NAVY),
            ("COMPLETED", f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&C6,{VT("I")},"<="&(C6+6),{VT("K")},{DONE})', "0", SUCCESS),
            ("COMPLETION RATE", '=IF(F6=0,0,G6/F6)', FMT_PCT, TEAL),
            ("HIGH-PRIORITY DUE", f'=COUNTIFS({VT("C")},"?*",{VT("I")},">="&C6,{VT("I")},"<="&(C6+6),{VT("J")},{PRI["Critical"]})+COUNTIFS({VT("C")},"?*",{VT("I")},">="&C6,{VT("I")},"<="&(C6+6),{VT("J")},{PRI["High"]})', "0", DANGER),
        ]
        for i, (lab, fm, nf, colr) in enumerate(stats):
            c = L(5 + i)
            ws[f"{c}5"] = lab
            ws[f"{c}5"].font = T.font(8, True, SECONDARY)
            ws[f"{c}5"].alignment = CENTER
            ws[f"{c}6"] = fm
            ws[f"{c}6"].font = T.font(16, True, colr)
            ws[f"{c}6"].alignment = CENTER
            ws[f"{c}6"].number_format = nf
            ws[f"{c}5"].fill = ws[f"{c}6"].fill = FILL_WHITE
            ws[f"{c}5"].border = Border(top=Side(style="medium", color=colr), left=THIN, right=THIN)
            ws[f"{c}6"].border = Border(bottom=THIN, left=THIN, right=THIN)
        ws.row_dimensions[6].height = 28
        # headers
        ws["B9"] = "TIME"
        for d in range(7):
            c = L(3 + d)
            ws[f"{c}9"] = f"=$C$6+{d}"
            ws[f"{c}9"].number_format = "dddd"
            ws[f"{c}10"] = f"=$C$6+{d}"
            ws[f"{c}10"].number_format = "mmm d"
            for rr in (9, 10):
                ws[f"{c}{rr}"].fill = fill(NAVY if rr == 9 else MIDNIGHT)
                ws[f"{c}{rr}"].font = T.font(10 if rr == 9 else 9, rr == 9, WHITE)
                ws[f"{c}{rr}"].alignment = CENTER
        for rr in (9, 10):
            ws[f"B{rr}"].fill = fill(NAVY if rr == 9 else MIDNIGHT)
            ws[f"B{rr}"].font = T.font(9, True, WHITE)
            ws[f"B{rr}"].alignment = CENTER
        HOURS = list(range(7, 21))
        r0 = 11
        for i, h in enumerate(HOURS):
            r = r0 + i
            ws[f"B{r}"] = dt.time(h, 0)
            ws[f"B{r}"].number_format = "h AM/PM"
            ws[f"B{r}"].font = T.font(9, True, SECONDARY)
            ws[f"B{r}"].alignment = Alignment(horizontal="right", vertical="top", indent=1)
            ws[f"B{r}"].border = Border(bottom=THIN)
            ws.row_dimensions[r].height = 26
            for d in range(7):
                c = L(3 + d)
                hc = L(12 + d)
                key = f'INT({c}$10)&"|"&HOUR($B{r})'
                m = f'MATCH({key},{TS("L")},0)'
                ws[f"{c}{r}"] = (f'=IFERROR(INDEX({TS("E")},{m})&IF(INDEX({TS("F")},{m})="",""," · "&INDEX({TS("F")},{m})),'
                                 f'IF(COUNTIFS({TS("B")},{c}$10,{TS("C")},"<"&$B{r},{TS("D")},">"&$B{r})>0,"⋮",""))')
                ws[f"{hc}{r}"] = f'=IFERROR(MATCH(INDEX({TS("G")},{m}),{SL("D")},0),IF({c}{r}="⋮",9,IF({c}{r}="","",5)))'
                cell = ws[f"{c}{r}"]
                cell.font = T.font(8)
                cell.alignment = Alignment(horizontal="left", vertical="center", indent=1, wrap_text=True)
                cell.border = Border(left=THIN, right=THIN, bottom=Side(style="hair", color=BORDER))
        rN = r0 + len(HOURS) - 1
        grid = f"C{r0}:I{rN}"
        for v, bg, fg in ((1, DANGER_BG, DANGER), (2, WARNING_BG, "9A6512"), (3, INFO_BG, MIDNIGHT), (4, SOFT_TEAL, SUCCESS),
                          (5, SOFT_LAV, MIDNIGHT), (9, LIGHT_GRAY, SECONDARY)):
            cf_formula(ws, grid, f"L{r0}={v}", bg, fg)
        for c in range(12, 19):
            ws.column_dimensions[L(c)].hidden = True
        cf_formula(ws, f"C9:I10", "C$10=$K$4", BLUE, WHITE, True)
        # due tasks
        rD = rN + 2
        section(ws, T, rD, 2, 9, "TASKS DUE", color=LAVENDER)
        for k in range(1, 5):
            r = rD + k
            ws[f"B{r}"] = f"#{k}" if k < 4 else "more"
            ws[f"B{r}"].font = T.font(8, False, SECONDARY)
            ws[f"B{r}"].alignment = RIGHT
            for d in range(7):
                c = L(3 + d)
                if k < 4:
                    ws[f"{c}{r}"] = f'=IFERROR(INDEX({VT("C")},MATCH(INT({c}$10)&"|{k}",{VT("R")},0)),"")'
                else:
                    cnt = f'COUNTIFS({VT("I")},{c}$10,{VT("C")},"?*")'
                    ws[f"{c}{r}"] = f'=IF({cnt}>3,"+"&({cnt}-3)&" more","")'
                ws[f"{c}{r}"].font = T.font(9)
                ws[f"{c}{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
                ws[f"{c}{r}"].border = Border(left=THIN, right=THIN, bottom=Side(style="hair", color=BORDER))
        rW = rD + 6
        section(ws, T, rW, 2, 9, "DAILY WORKLOAD", color=TEAL)
        rows = [("Sched. hrs", lambda c: f'=SUMIFS({TS("I")},{TS("B")},{c}$10)', FMT_HRS),
                ("Blocks", lambda c: f'=COUNTIF({TS("B")},{c}$10)', "0"),
                ("Due", lambda c: f'=COUNTIFS({VT("I")},{c}$10,{VT("C")},"?*")', "0"),
                ("Done", lambda c: f'=COUNTIFS({VT("I")},{c}$10,{VT("C")},"?*",{VT("K")},{DONE})', "0"),
                ("Done %", lambda c: f'=IF({c}{rW + 3}=0,"",{c}{rW + 4}/{c}{rW + 3})', FMT_PCT)]
        for i, (lab, fn, nf) in enumerate(rows):
            r = rW + 1 + i
            ws[f"B{r}"] = lab
            ws[f"B{r}"].font = T.font(9, True, SECONDARY)
            for d in range(7):
                c = L(3 + d)
                ws[f"{c}{r}"] = fn(c)
                self.calc(S_WCAL, f"{c}{r}", nf, CENTER)
        ws.conditional_formatting.add(f"C{rW + 1}:I{rW + 1}", DataBarRule(start_type="num", start_value=0, end_type="num", end_value=8, color=BLUE, showValue=True))
        cf_databar(ws, f"C{rW + 5}:I{rW + 5}", TEAL)
        ws.freeze_panes = "C11"

    # ================================================================ TAB 6 PROJECT MANAGER
    def build_pm(self):
        ws, T = self.ws[S_PM], self.T
        setup_sheet(ws, {"B": 20, "C": 16, "D": 16, "E": 16, "F": 17, "G": 14, "H": 3, "I": 31, "J": 13, "K": 50, "L": 17, "M": 15,
                         "N": 13, "O": 22, "P": 3, "Q": 6, "R": 6})
        title_bar(ws, T, "PROJECT MANAGER  ·  Project detail view", "Select a project — the left panel updates instantly. Add objectives, milestones, risks… in the database on the right.", 15, demo=self.demo)
        ws["B5"] = "PROJECT ▸"
        ws["B5"].font = T.font(11, True, NAVY)
        ws.merge_cells("C5:E5")
        ws["C5"] = SD.PROJECTS[0][0] if self.demo else None
        self.inp(S_PM, "C5:E5", align=CENTER)
        ws["C5"].font = T.font(12, True, NAVY)
        add_list_dv(ws, "C5", POV("C"))
        ws["F5"] = "Today"
        ws["G5"] = f"={TODAY}"
        ws["F5"].font = T.font(9, True, SECONDARY)
        ws["F5"].alignment = RIGHT
        self.calc(S_PM, "G5", FMT_SDATE, CENTER)
        ws["Q5"] = f'=IFERROR(MATCH(C5,{POV("C")},0),"")'
        ws["Q4"] = "row"
        # info panel
        section(ws, T, 7, 2, 4, "PROJECT INFORMATION")
        info = [("Project ID", "B", None), ("Category", "E", None), ("Project manager", "F", None), ("Priority", "I", None),
                ("Status", "J", None), ("Health", "S", None), ("Start date", "G", FMT_DATE), ("Due date", "H", FMT_DATE),
                ("Days remaining", "O", "0"), ("Description", "D", None)]
        for i, (lab, c_, nf) in enumerate(info):
            r = 8 + i
            ws[f"B{r}"] = lab
            ws[f"B{r}"].font = T.font(10, True, SECONDARY)
            ws[f"B{r}"].border = BOX
            ws.merge_cells(f"C{r}:D{r}")
            ws[f"C{r}"] = f'=IF($Q$5="","",IF(INDEX({POV(c_)},$Q$5)="","",INDEX({POV(c_)},$Q$5)))'
            self.calc(S_PM, f"C{r}:D{r}", nf)
        ws.row_dimensions[17].height = 30
        ws["C17"].alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        for txt, bg, fg in (("Completed", SUCCESS_BG, SUCCESS), ("Overdue", DANGER_BG, DANGER), ("Over budget", DANGER_BG, DANGER),
                            ("At risk", WARNING_BG, WARNING), ("On track", INFO_BG, INFO)):
            cf_formula(ws, "C13", f'C13="{txt}"', bg, fg, True)
        cf_formula(ws, "C16", "AND(ISNUMBER(C16),C16<0)", DANGER_BG, DANGER, True)
        # metrics
        section(ws, T, 7, 6, 7, "PROGRESS & BUDGET", color=TEAL)
        met = [("Progress", f'=IF($Q$5="","",INDEX({POV("K")},$Q$5))', FMT_PCT),
               ('="Budget ("&CurrencySymbol&")"', f'=IF($Q$5="","",INDEX({POV("L")},$Q$5))', FMT_CUR),
               ('="Actual ("&CurrencySymbol&")"', f'=IF($Q$5="","",INDEX({POV("M")},$Q$5))', FMT_CUR),
               ('="Remaining ("&CurrencySymbol&")"', f'=IF($Q$5="","",INDEX({POV("N")},$Q$5))', FMT_CUR),
               ("Budget left %", f'=IF(OR($Q$5="",N(G9)=0),"",G11/G9)', FMT_PCT),
               ("Tasks (total)", f'=IF($Q$5="","",INDEX({POV("P")},$Q$5))', "0"),
               ("Tasks done", f'=IF($Q$5="","",INDEX({POV("Q")},$Q$5))', "0"),
               ("Tasks overdue", f'=IF($Q$5="","",INDEX({POV("R")},$Q$5))', "0"),
               ("Estimated hours", f'=IF($C$5="","",SUMIFS({VT("L")},{VT("E")},$C$5))', FMT_HRS),
               ("Actual hours", f'=IF($C$5="","",SUMIFS({VT("M")},{VT("E")},$C$5))', FMT_HRS)]
        for i, (lab, fm, nf) in enumerate(met):
            r = 8 + i
            ws[f"F{r}"] = lab
            ws[f"F{r}"].font = T.font(10, True, SECONDARY)
            ws[f"F{r}"].border = BOX
            ws[f"G{r}"] = fm
            self.calc(S_PM, f"G{r}", nf, RIGHT, color=BLUE)
        cf_databar(ws, "G8", TEAL)
        cf_formula(ws, "G11", "AND(ISNUMBER(G11),G11<0)", DANGER_BG, DANGER, True)
        cf_formula(ws, "G15", "AND(ISNUMBER(G15),G15>0)", DANGER_BG, DANGER, True)
        # timeline
        section(ws, T, 19, 2, 7, "PROJECT TIMELINE", color=LAVENDER)
        tl = [("Duration (days)", '=IF(OR(C14="",C15=""),"",C15-C14)', "0"),
              ("Days elapsed", '=IF(C14="","",MAX(0,MIN($G$5,C15)-C14))', "0"),
              ("Time elapsed %", '=IF(OR(N(C20)=0,C20=""),"",MIN(1,C21/C20))', FMT_PCT),
              ("Work progress %", "=G8", FMT_PCT),
              ("Schedule check", '=IF(OR(C22="",C23=""),"",IF(C23>=C22,"Ahead / on schedule",IF(C22-C23<0.15,"Slightly behind","Behind schedule")))', None)]
        for i, (lab, fm, nf) in enumerate(tl):
            r = 20 + i
            ws[f"B{r}"] = lab
            ws[f"B{r}"].font = T.font(10, True, SECONDARY)
            ws[f"B{r}"].border = BOX
            ws.merge_cells(f"C{r}:D{r}")
            ws[f"C{r}"] = fm
            self.calc(S_PM, f"C{r}:D{r}", nf)
        cf_databar(ws, "C22:C23", BLUE)
        cf_formula(ws, "C24", 'C24="Behind schedule"', DANGER_BG, DANGER, True)
        cf_formula(ws, "C24", 'C24="Slightly behind"', WARNING_BG, WARNING, True)
        cf_formula(ws, "C24", 'C24="Ahead / on schedule"', SUCCESS_BG, SUCCESS, True)
        # team panel
        section(ws, T, 19, 6, 7, "ASSIGNED TEAM", color=TEAL)
        ws["F20"], ws["G20"] = "Member", "Tasks"
        for c in ("F20", "G20"):
            ws[c].font = T.font(9, True, SECONDARY)
            ws[c].fill = FILL_CALC
        for i in range(20):
            r = 5 + i
            ws[f"R{r}"] = f'=IF(OR($C$5="",INDEX({SL("G")},{i + 1})=""),"",IF(COUNTIFS({VT("E")},$C$5,{VT("G")},INDEX({SL("G")},{i + 1}))>0,MAX(R$4:R{r - 1})+1,""))'
        ws["R4"] = 0
        for k in range(1, 8):
            r = 20 + k
            ws[f"F{r}"] = f'=IFERROR(INDEX({SL("G")},MATCH({k},$R$5:$R$24,0)),"")'
            ws[f"G{r}"] = f'=IF(F{r}="","",COUNTIFS({VT("E")},$C$5,{VT("G")},F{r})&" ("&COUNTIFS({VT("E")},$C$5,{VT("G")},F{r},{VT("K")},{DONE})&" done)")'
            paint(ws, f"F{r}:G{r}", f=FILL_WHITE, font=T.font(9), border=Border(bottom=THIN))
        ws.column_dimensions["Q"].hidden = True
        ws.column_dimensions["R"].hidden = True
        # details database (I..O)
        section(ws, T, 5, 9, 15, "PROJECT DETAILS DATABASE  —  one row per objective, deliverable, milestone, dependency, risk or note")
        header_row(ws, T, HDR, 9, ["Project", "Type", "Description", "Owner", "Target Date", "Status / Impact", "Key"])
        ws[f"O{HDR}"].fill = fill(MED_GRAY)
        pd_last = R1 + PD_N - 1
        self.inp(S_PM, f"I{R1}:N{pd_last}")
        paint(ws, f"M{R1}:M{pd_last}", numfmt=FMT_DATE)
        self.fill_down(ws, "O", R1, pd_last, '=IF(OR(I{r}="",J{r}="",K{r}=""),"",I{r}&"|"&J{r}&"|"&COUNTIFS(I$7:I{r},I{r},J$7:J{r},J{r},K$7:K{r},"?*"))')
        self.calc(S_PM, f"O{R1}:O{pd_last}")
        paint(ws, f"O{R1}:O{pd_last}", font=T.font(8, color=SECONDARY))
        add_list_dv(ws, f"I{R1}:I{pd_last}", POV("C"))
        add_list_dv(ws, f"J{R1}:J{pd_last}", SL("L"))
        add_list_dv(ws, f"L{R1}:L{pd_last}", SL("G"))
        add_dv(ws, f"M{R1}:M{pd_last}", "date", "greaterThan", "DATE(2000,1,1)")
        if self.demo:
            for i, (pi, ty, desc, own, off, st) in enumerate(SD.DETAILS):
                r = R1 + i
                ws[f"I{r}"] = SD.PROJECTS[pi - 1][0]
                ws[f"J{r}"] = ty
                ws[f"K{r}"] = desc
                ws[f"L{r}"] = own
                ws[f"M{r}"] = SD.d(off)
                ws[f"N{r}"] = st
        # detail sections on the left
        colors = [BLUE, TEAL, LAVENDER, INFO, DANGER, MED_GRAY]
        r = 30
        for ti in range(6):
            ws.merge_cells(f"B{r}:G{r}")
            ws[f"B{r}"] = f'=SUBSTITUTE(UPPER({DTYPES[ti]})&"S","YS","IES")'
            paint(ws, f"B{r}:G{r}", f=fill(colors[ti]))
            ws[f"B{r}"].font = T.font(10, True, WHITE)
            ws[f"B{r}"].alignment = Alignment(vertical="center", indent=1)
            for j, h in enumerate(["Item", None, None, "Owner", "Target date", "Status"]):
                if h:
                    ws.cell(row=r + 1, column=2 + j, value=h)
                ws.cell(row=r + 1, column=2 + j).font = T.font(8, True, SECONDARY)
                ws.cell(row=r + 1, column=2 + j).fill = FILL_CALC
            for k in range(1, 6):
                rr = r + 1 + k
                key = f'$C$5&"|"&{DTYPES[ti]}&"|{k}"'
                m = f"MATCH({key},$O${R1}:$O${pd_last},0)"
                ws.merge_cells(f"B{rr}:D{rr}")
                ws[f"B{rr}"] = (f'=IFERROR(INDEX($K${R1}:$K${pd_last},{m}),IF({k}=1,"— none yet: add rows in the database on the right —",""))')
                ws[f"E{rr}"] = f'=IFERROR(INDEX($L${R1}:$L${pd_last},{m})&"","")'
                ws[f"F{rr}"] = f'=IFERROR(IF(INDEX($M${R1}:$M${pd_last},{m})="","",INDEX($M${R1}:$M${pd_last},{m})),"")'
                ws[f"G{rr}"] = f'=IFERROR(INDEX($N${R1}:$N${pd_last},{m})&"","")'
                paint(ws, f"B{rr}:G{rr}", f=FILL_WHITE, font=T.font(9), border=Border(bottom=THIN))
                ws[f"F{rr}"].number_format = FMT_SDATE
                ws[f"F{rr}"].alignment = CENTER
                ws[f"B{rr}"].alignment = Alignment(indent=1, vertical="center", shrink_to_fit=True)
            cf_formula(ws, f"B{r + 2}:D{r + 2}", f'LEFT(B{r + 2},1)="—"', None, MED_GRAY)
            r += 8
        ws.freeze_panes = "A7"

    # ================================================================ TAB 11 TASK FILTER
    def build_tf(self):
        ws, T = self.ws[S_TF], self.T
        setup_sheet(ws, {"B": 18, "C": 24, "D": 28, "E": 27, "F": 13, "G": 16, "H": 12, "I": 10, "J": 12, "K": 9, "L": 10, "M": 5, "N": 5})
        title_bar(ws, T, "TASK FILTER  ·  Search & filter", "Set any combination of filters (blank = all). Matching tasks appear below instantly.", 12, demo=self.demo)
        section(ws, T, 5, 2, 3, "FILTERS")
        crit = [("Project", POV("C")), ("Priority", SL("D")), ("Status", SL("E")), ("Category", SL("C")), ("Assigned person", SL("G")),
                ("Due from", "date"), ("Due to", "date"), ("Completion", SS("K")), ("Overdue status", SS("L")), ("Keyword search", "text")]
        for i, (lab, src) in enumerate(crit):
            r = 6 + i
            ws[f"B{r}"] = lab
            ws[f"B{r}"].font = T.font(10, True)
            ws[f"B{r}"].border = BOX
            self.inp(S_TF, f"C{r}", FMT_DATE if src == "date" else None)
            if src == "date":
                add_dv(ws, f"C{r}", "date", "greaterThan", "DATE(2000,1,1)")
            elif src != "text":
                add_list_dv(ws, f"C{r}", src)
        ws["C13"] = "Incomplete" if self.demo else None
        note(ws, T, "B16", "Tip: select the blue filter cells and press Delete to clear them.")
        section(ws, T, 5, 5, 8, "RESULTS SUMMARY", color=TEAL)
        summ = [("Matching tasks", f"=MAX({VT('V')})", "0"),
                ("…completed", f'=COUNTIFS({VT("V")},">0",{VT("K")},{DONE})', "0"),
                ("…overdue", f'=COUNTIFS({VT("V")},">0",{VT("P")},"Overdue")', "0"),
                ("Estimated hours", f'=SUMIFS({VT("L")},{VT("V")},">0")', FMT_HRS),
                ("Average progress", f'=IFERROR(AVERAGEIFS({VT("Z")},{VT("V")},">0"),0)', FMT_PCT),
                ("Showing", '=IF(F6>100,"first 100 of "&F6,F6&" task(s)")', None)]
        for i, (lab, fm, nf) in enumerate(summ):
            r = 6 + i
            ws[f"E{r}"] = lab
            ws[f"E{r}"].font = T.font(10, True)
            ws[f"E{r}"].border = BOX
            ws[f"F{r}"] = fm
            self.calc(S_TF, f"F{r}", nf, CENTER, color=BLUE)
        legend(ws, T, 13, 5)
        heads = ["#", "Task ID", "Task Name", "Project", "Category", "Assigned To", "Due Date", "Priority", "Status", "Progress", "Flag"]
        header_row(ws, T, 18, 2, heads)
        for k in range(1, 101):
            r = 18 + k
            ws[f"N{r}"] = k
            ws[f"M{r}"] = f'=IFERROR(MATCH(N{r},{VT("V")},0),"")'
            ws[f"B{r}"] = f'=IF(M{r}="","",N{r})'
            for c, src in zip("CDEFGIJ", "BCEFGJK"):
                ws[f"{c}{r}"] = f'=IF($M{r}="","",INDEX({VT(src)},$M{r})&"")'
            ws[f"H{r}"] = f'=IF($M{r}="","",IF(INDEX({VT("I")},$M{r})="","",INDEX({VT("I")},$M{r})))'
            ws[f"K{r}"] = f'=IF($M{r}="","",INDEX({VT("Z")},$M{r}))'
            ws[f"L{r}"] = f'=IF($M{r}="","",INDEX({VT("P")},$M{r})&"")'
        ws["D19"] = f'=IF($M19="","No tasks match these filters.",INDEX({VT("C")},$M19)&"")'
        paint(ws, "B19:L118", f=FILL_WHITE, font=T.font(9), border=Border(bottom=THIN))
        paint(ws, "H19:H118", numfmt=FMT_SDATE, align=CENTER)
        paint(ws, "K19:K118", numfmt=FMT_PCT)
        paint(ws, "B19:C118", align=CENTER)
        paint(ws, "M19:N118", font=T.font(8, color=MED_GRAY))
        ws.column_dimensions["M"].hidden = True
        ws.column_dimensions["N"].hidden = True
        cf_databar(ws, "K19:K118", TEAL)
        cf_formula(ws, "L19:L118", 'L19="Overdue"', DANGER_BG, DANGER, True)
        cf_formula(ws, "L19:L118", 'L19="Due soon"', WARNING_BG, WARNING, True)
        cf_formula(ws, "B19:L118", 'AND($B19<>"",MOD($B19,2)=0)', BG)
        ws.freeze_panes = "A19"

    # ================================================================ TAB 12 DECISION MATRIX
    def build_dm(self):
        ws, T = self.ws[S_DM], self.T
        setup_sheet(ws, {"B": 30, "C": 11, **{L(i): 17 for i in range(4, 10)}, "J": 3, "K": 26, "L": 12})
        title_bar(ws, T, "DECISION MATRIX  ·  Weighted scoring", "Weight your criteria, score each option 1–10, and let the matrix recommend the winner.", 12, demo=self.demo)
        legend(ws, T, 4, 2)
        ws["B5"] = "Decision name"
        ws["B5"].font = T.font(11, True, NAVY)
        ws.merge_cells("C5:I5")
        self.inp(S_DM, "C5:I5")
        ws["B7"] = "Options ▸"
        ws["B7"].font = T.font(10, True, SECONDARY)
        for c in "DEF":
            self.inp(S_DM, f"{c}7", align=CENTER)
            ws[f"{c}7"].font = T.font(10, True, NAVY)
        header_row(ws, T, 9, 2, ["Criteria", "Weight", '=IF(D7="","Option A score",D7&" score")', '=IF(E7="","Option B score",E7&" score")',
                                 '=IF(F7="","Option C score",F7&" score")', "Weighted A", "Weighted B", "Weighted C"])
        for c in "GHI":
            ws[f"{c}9"].fill = fill(MED_GRAY)
        for i in range(10):
            r = 10 + i
            self.inp(S_DM, f"B{r}")
            self.inp(S_DM, f"C{r}", FMT_PCT, CENTER)
            self.inp(S_DM, f"D{r}:F{r}", "0", CENTER)
            for src, dst in zip("DEF", "GHI"):
                ws[f"{dst}{r}"] = f'=IF(OR($B{r}="",N($C{r})=0,{src}{r}="",$C$20=0),"",{src}{r}*$C{r}/$C$20)'
            self.calc(S_DM, f"G{r}:I{r}", "0.00", CENTER)
        add_list_dv(ws, "D10:F19", SS("O"))
        add_dv(ws, "C10:C19", "decimal", "between", "0", "1", error="Weight is a percentage (e.g. 25%).")
        ws["B20"] = "TOTAL"
        ws["B20"].font = T.font(10, True)
        ws["C20"] = "=SUM(C10:C19)"
        self.calc(S_DM, "C20", FMT_PCT, CENTER)
        for c in "GHI":
            ws[f"{c}20"] = f"=SUM({c}10:{c}19)"
            self.calc(S_DM, f"{c}20", "0.00", CENTER, color=BLUE)
            ws[f"{c}20"].font = T.font(12, True, BLUE)
        ws["B21"] = "Weight check"
        ws["C21"] = '=IF(C20=0,"Add weights",IF(ABS(C20-1)<0.0001,"✓ 100%","Weights total "&ROUND(C20*100,0)&"% — scores are normalised"))'
        ws.merge_cells("C21:F21")
        ws["C21"].font = T.font(9, True, SECONDARY)
        cf_formula(ws, "C21", 'LEFT(C21,1)="✓"', SUCCESS_BG, SUCCESS)
        cf_formula(ws, "C21", 'LEFT(C21,1)<>"✓"', WARNING_BG, WARNING)
        for c in "GHI":
            cf_formula(ws, f"{c}20", f"AND(MAX($G$20:$I$20)>0,{c}20=MAX($G$20:$I$20))", SUCCESS_BG, SUCCESS, True)
        # result
        section(ws, T, 23, 2, 9, "RESULT", color=TEAL)
        res = [("Recommended option", '=IF(MAX(G20:I20)=0,"Enter scores to see a recommendation",INDEX(D7:F7,MATCH(MAX(G20:I20),G20:I20,0))&"")'),
               ("Winning score (out of 10)", '=IF(MAX(G20:I20)=0,"",MAX(G20:I20))'),
               ("Runner-up margin", '=IF(MAX(G20:I20)=0,"",MAX(G20:I20)-LARGE(G20:I20,2))'),
               ("Confidence", '=IF(C26="","",IF(C26>=1,"Clear winner",IF(C26>=0.4,"Moderate — sanity-check the top two","Close call — consider more criteria")))')]
        for i, (lab, fm) in enumerate(res):
            r = 24 + i
            ws[f"B{r}"] = lab
            ws[f"B{r}"].font = T.font(10, True)
            ws[f"B{r}"].border = BOX
            ws.merge_cells(f"C{r}:F{r}")
            ws[f"C{r}"] = fm
            self.calc(S_DM, f"C{r}:F{r}", "0.00" if i in (1, 2) else None, color=NAVY)
        ws["C24"].font = T.font(13, True, SUCCESS)
        ws["K9"] = "Ranking"
        ws["K9"].font = T.font(10, True, WHITE)
        ws["K9"].fill = fill(NAVY)
        ws["L9"].fill = fill(NAVY)
        for i, (c, w) in enumerate(zip("DEF", "GHI")):
            r = 10 + i
            ws[f"K{r}"] = f'=IF({c}7="","Option "&CHAR(65+{i}),{c}7)'
            ws[f"L{r}"] = f"=N({w}20)"
            self.calc(S_DM, f"K{r}:L{r}", None)
            ws[f"L{r}"].number_format = "0.00"
        ch = BarChart()
        ch.type = "bar"
        ch.title = "Weighted total score"
        ch.add_data(Reference(ws, min_col=12, min_row=10, max_row=12), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=11, min_row=10, max_row=12))
        ch.series[0].graphicalProperties.solidFill = LAVENDER
        ch.legend = None
        ch.x_axis.delete = False
        ch.y_axis.delete = False
        ch.y_axis.majorGridlines = None
        ch.y_axis.scaling.min = 0
        ch.y_axis.scaling.max = 10
        ch.width, ch.height = 12, 6
        ws.add_chart(ch, "K14")
        if self.demo:
            ws["C5"] = SD.DECISION["name"]
            for c, o in zip("DEF", SD.DECISION["options"]):
                ws[f"{c}7"] = o
            for i, (cr, w, a, b, cc) in enumerate(SD.DECISION["criteria"]):
                r = 10 + i
                ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"], ws[f"F{r}"] = cr, w, a, b, cc
        note(ws, T, "B29", "How it works: weighted score = score × (weight ÷ total weight). The highest total wins; ties go to the left-most option.")

    # ================================================================ TAB 13 KANBAN
    def build_kb(self):
        ws, T = self.ws[S_KB], self.T
        widths = {}
        for j in range(5):
            c = 2 + j * 3
            widths[c], widths[c + 1], widths[c + 2] = 22, 12, 2
        for c in range(18, 23):
            widths[c] = 5
        setup_sheet(ws, widths)
        title_bar(ws, T, "KANBAN BOARD", "Cards move automatically when you change a task's Status on 'Variable Tasks'.  ‼ = Critical   ▲ = High priority", 16, demo=self.demo)
        ws["R4"] = f"={TODAY}"
        ws["R4"].number_format = FMT_SDATE
        col_colors = [(MED_GRAY, LIGHT_GRAY), (LAVENDER, SOFT_LAV), (BLUE, SOFT_BLUE), (WARNING, WARNING_BG), (TEAL, SOFT_TEAL)]
        CARDS = 15
        for j in range(5):
            c, c2 = L(2 + j * 3), L(3 + j * 3)
            hc = L(18 + j)
            dark, soft = col_colors[j]
            ws.merge_cells(f"{c}5:{c2}5")
            ws[f"{c}5"] = f"=UPPER({TSTAT[j]})"
            paint(ws, f"{c}5:{c2}5", f=fill(dark))
            ws[f"{c}5"].font = T.font(11, True, WHITE)
            ws[f"{c}5"].alignment = CENTER
            ws.merge_cells(f"{c}6:{c2}6")
            ws[f"{c}6"] = f'=COUNTIFS({VT("K")},{TSTAT[j]},{VT("C")},"?*")&" task(s)"&IF(COUNTIFS({VT("K")},{TSTAT[j]},{VT("C")},"?*")>{CARDS},"  ·  showing {CARDS}","")'
            paint(ws, f"{c}6:{c2}6", f=fill(soft))
            ws[f"{c}6"].font = T.font(9, True, dark)
            ws[f"{c}6"].alignment = CENTER
            for k in range(1, CARDS + 1):
                r1 = 8 + (k - 1) * 3
                ws[f"{hc}{r1}"] = f'=IFERROR(MATCH({TSTAT[j]}&"|{k}",{VT("S")},0),"")'
                ws[f"{hc}{r1 + 1}"] = f"={hc}{r1}"
                ws.merge_cells(f"{c}{r1}:{c2}{r1}")
                ws[f"{c}{r1}"] = (f'=IF(${hc}{r1}="","",IF(INDEX({VT("J")},${hc}{r1})={PRI["Critical"]},"‼ ",'
                                  f'IF(INDEX({VT("J")},${hc}{r1})={PRI["High"]},"▲ ",""))&INDEX({VT("C")},${hc}{r1}))')
                ws[f"{c}{r1 + 1}"] = f'=IF(${hc}{r1}="","",INDEX({VT("G")},${hc}{r1})&IF(INDEX({VT("E")},${hc}{r1})="",""," · "&INDEX({VT("E")},${hc}{r1})))'
                ws[f"{c2}{r1 + 1}"] = f'=IF(${hc}{r1}="","",IF(INDEX({VT("I")},${hc}{r1})="","",INDEX({VT("I")},${hc}{r1})))'
                ws[f"{c}{r1}"].font = T.font(10, True, DARK)
                ws[f"{c}{r1}"].alignment = Alignment(indent=1, vertical="center", shrink_to_fit=True)
                ws[f"{c}{r1 + 1}"].font = T.font(8, False, SECONDARY)
                ws[f"{c}{r1 + 1}"].alignment = Alignment(indent=1, vertical="center", shrink_to_fit=True)
                ws[f"{c2}{r1 + 1}"].font = T.font(8, True, SECONDARY)
                ws[f"{c2}{r1 + 1}"].number_format = FMT_SDATE
                ws[f"{c2}{r1 + 1}"].alignment = Alignment(horizontal="right", vertical="center", indent=1)
                ws.row_dimensions[r1].height = 20
                ws.row_dimensions[r1 + 1].height = 16
                ws.row_dimensions[r1 + 2].height = 6
            rngc = f"{c}8:{c2}{8 + CARDS * 3 - 1}"
            cf_formula(ws, rngc, f"${hc}8<>\"\"", soft)
            cf_formula(ws, f"{c2}8:{c2}{8 + CARDS * 3 - 1}", f'AND(ISNUMBER({c2}8),{c2}8<$R$4,{j}<4)', None, DANGER, True)
            cf_formula(ws, f"{c}8:{c}{8 + CARDS * 3 - 1}", f'LEFT({c}8,1)="‼"', None, DANGER, True)
            cf_formula(ws, f"{c}8:{c}{8 + CARDS * 3 - 1}", f'LEFT({c}8,1)="▲"', None, "B7791F", True)
        for c in range(18, 23):
            ws.column_dimensions[L(c)].hidden = True
        ws.freeze_panes = "A7"

    # ================================================================ TAB 14 GANTT
    def build_gc(self):
        ws, T = self.ws[S_GC], self.T
        NCOL = 60
        TL0 = 12  # column L
        widths = {"B": 4, "C": 26, "D": 31, "E": 14, "F": 11, "G": 11, "H": 6, "I": 8, "J": 11, "K": 9}
        for i in range(NCOL):
            widths[TL0 + i] = 3.3
        setup_sheet(ws, widths, zoom=90)
        last_tl = L(TL0 + NCOL - 1)
        helper = L(TL0 + NCOL + 1)
        title_bar(ws, T, "GANTT CHART  ·  Timeline", "Bars draw themselves from task start/due dates. Darker shading = progress. ◆ = milestone (start = due). ▼ = today.", 11, demo=self.demo)
        lab = [("B5", "Project"), ("E5", "Start"), ("G5", "View"), ("I5", "Hide done")]
        for a, t in lab:
            ws[a] = t
            ws[a].font = T.font(9, True, SECONDARY)
            ws[a].alignment = RIGHT
        ws["C5"] = None
        self.inp(S_GC, "C5:D5")
        ws.merge_cells("C5:D5")
        add_list_dv(ws, "C5", POV("C"), prompt="Blank = all projects")
        self.inp(S_GC, "F5", FMT_DATE, CENTER)
        add_dv(ws, "F5", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date, or leave blank for automatic.")
        ws["H5"] = "Weekly" if self.demo else "Daily"
        self.inp(S_GC, "H5", None, CENTER)
        add_list_dv(ws, "H5", SS("M"))
        ws["J5"] = "No"
        self.inp(S_GC, "J5", None, CENTER)
        add_list_dv(ws, "J5", SS("J"))
        for a, t in (("B6", "From"), ("E6", "Today"), ("G6", "Step"), ("I6", "Tasks")):
            ws[a] = t
            ws[a].font = T.font(9, True, SECONDARY)
            ws[a].alignment = RIGHT
        ws.merge_cells("C6:D6")
        ws["C6"] = f'=IF(F5<>"",F5-WEEKDAY(F5,2)+1,IF(COUNT(F10:F69)=0,{TODAY}-WEEKDAY({TODAY},2)+1,MIN(F10:F69)-WEEKDAY(MIN(F10:F69),2)+1))'
        self.calc(S_GC, "C6:D6", FMT_DATE, CENTER)
        ws["F6"] = f"={TODAY}"
        self.calc(S_GC, "F6", FMT_DATE, CENTER)
        ws["H6"] = '=IF(H5="Weekly",7,1)'
        self.calc(S_GC, "H6", "0", CENTER)
        ws["J6"] = f'=MAX({VT("W")})'
        self.calc(S_GC, "J6", "0", CENTER)
        header_row(ws, T, 9, 2, ["#", "Task", "Project", "Assigned", "Start", "End", "Days", "Progress", "Status", "Flag"], height=22)
        tl = L(TL0)
        for i in range(NCOL):
            c = L(TL0 + i)
            prev = L(TL0 + i - 1)
            ws[f"{c}9"] = "=$C$6" if i == 0 else f"={prev}9+$H$6"
            ws[f"{c}9"].number_format = "d"
            ws[f"{c}9"].font = T.font(8, True, WHITE)
            ws[f"{c}9"].fill = fill(NAVY)
            ws[f"{c}9"].alignment = Alignment(horizontal="center", vertical="center")
            mlabel = f'CHOOSE(MONTH({c}9),"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec")&" "&RIGHT(YEAR({c}9),2)'
            ws[f"{c}8"] = f"={mlabel}" if i == 0 else f'=IF(MONTH({c}9)<>MONTH({prev}9),{mlabel},"")'
            ws[f"{c}8"].font = T.font(8, True, MIDNIGHT)
            ws[f"{c}7"] = f'=IF(AND($F$6>={c}$9,$F$6<{c}$9+$H$6),"▼","")'
            ws[f"{c}7"].font = T.font(9, True, DANGER)
            ws[f"{c}7"].alignment = Alignment(horizontal="center")
        for k in range(1, 61):
            r = 9 + k
            ws[f"{helper}{r}"] = f'=IFERROR(MATCH({k},{VT("W")},0),"")'
            h = f"${helper}{r}"
            ws[f"B{r}"] = f'=IF({h}="","",{k})'
            for c, src in zip("CDEJ", "CEGK"):
                ws[f"{c}{r}"] = f'=IF({h}="","",INDEX({VT(src)},{h})&"")'
            ws[f"F{r}"] = f'=IF({h}="","",INDEX({VT("H")},{h}))'
            ws[f"G{r}"] = f'=IF({h}="","",INDEX({VT("I")},{h}))'
            ws[f"H{r}"] = f'=IF({h}="","",G{r}-F{r}+1)'
            ws[f"I{r}"] = f'=IF({h}="","",INDEX({VT("Z")},{h}))'
            ws[f"K{r}"] = f'=IF({h}="","",INDEX({VT("P")},{h})&"")'
            for i in range(NCOL):
                c = L(TL0 + i)
                ws[f"{c}{r}"] = f'=IF(AND($B{r}<>"",$F{r}=$G{r},$F{r}>={c}$9,$F{r}<{c}$9+$H$6),"◆","")'
            ws.row_dimensions[r].height = 18
        paint(ws, "B10:K69", f=FILL_WHITE, font=T.font(9), border=Border(bottom=Side(style="hair", color=BORDER)))
        paint(ws, "F10:G69", numfmt=FMT_SDATE, align=CENTER)
        paint(ws, "B10:B69", align=CENTER)
        paint(ws, "H10:H69", align=CENTER)
        paint(ws, "I10:I69", numfmt=FMT_PCT, align=CENTER)
        ws["C10"] = f'=IF(${helper}10="","No tasks to show — add tasks with start and due dates.",INDEX({VT("C")},${helper}10)&"")'
        bars = f"{tl}10:{last_tl}69"
        paint(ws, bars, font=T.font(9, True, NAVY), align=Alignment(horizontal="center", vertical="center"),
              border=Border(left=Side(style="hair", color=LIGHT_GRAY)))
        inbar = f"AND($B10<>\"\",{tl}$9+$H$6-1>=$F10,{tl}$9<=$G10)"
        cf_formula(ws, bars, f'{tl}10="◆"', WARNING_BG, NAVY, True, stop=True)
        cf_formula(ws, bars, f'AND({inbar},$J10=$K$7)', TEAL, stop=True)
        cf_formula(ws, bars, f'AND({inbar},$K10="Overdue",{tl}$9<$F10+($G10-$F10+1)*$I10)', "B8424A", stop=True)
        cf_formula(ws, bars, f'AND({inbar},$K10="Overdue")', DANGER, stop=True)
        cf_formula(ws, bars, f'AND({inbar},{tl}$9<$F10+($G10-$F10+1)*$I10)', BLUE, stop=True)
        cf_formula(ws, bars, inbar, "B9CBF6", stop=True)
        cf_formula(ws, bars, f"AND($F$6>={tl}$9,$F$6<{tl}$9+$H$6)", WARNING_BG)
        cf_formula(ws, bars, f"AND($H$6=1,WEEKDAY({tl}$9,2)>5)", BG)
        ws["K7"] = f"={DONE}"
        ws["K7"].font = T.font(8, False, MED_GRAY)
        cf_databar(ws, "I10:I69", TEAL)
        cf_formula(ws, "K10:K69", 'K10="Overdue"', DANGER_BG, DANGER, True)
        cf_formula(ws, "K10:K69", 'K10="Due soon"', WARNING_BG, WARNING, True)
        ws.column_dimensions[helper].hidden = True
        # legend
        leg = [(BLUE, "Progress"), ("B9CBF6", "Remaining"), (TEAL, "Completed"), (DANGER, "Overdue"), (WARNING_BG, "Today / ◆ milestone")]
        for i, (colr, t) in enumerate(leg):
            c = L(TL0 + i * 6)
            ws[f"{c}5"].fill = fill(colr)
            ws[f"{c}5"].border = BOX
            ws[f"{L(TL0 + i * 6 + 1)}5"] = t
            ws[f"{L(TL0 + i * 6 + 1)}5"].font = T.font(8, False, SECONDARY)
        ws.freeze_panes = f"{tl}10"

    # ================================================================ TAB 15 INSTRUCTIONS
    def build_ins(self):
        ws, T = self.ws[S_INS], self.T
        setup_sheet(ws, {"B": 4, "C": 110, "D": 16})
        title_bar(ws, T, "INSTRUCTIONS", "Everything you need to get started, plus formula notes and troubleshooting.", 4)
        blocks = [
            ("GETTING STARTED", [
                "1. Go to Setup. Enter your name/workspace, pick your currency and week start, and edit the dropdown lists (team, categories…).",
                "2. Go to Project Overview. Add one row per project (name, category, manager, dates, priority, status). IDs (P-001…) are pre-assigned.",
                "3. Go to Project Budget. Add budget lines: choose the Project ID, a category, a planned amount and (later) actual expenses.",
                "4. Go to Variable Tasks. Add one row per task and link it to a project with the Project dropdown.",
                "5. Optional: add repeating work on Recurring Tasks and time blocks on Task Schedule.",
                "6. Open the All-in-One Dashboard — every number, chart and list updates automatically.",
            ]),
            ("CELL COLOURS", [
                "Light blue = input (type or choose from a dropdown).  Light grey = formula (don't type over it).  White = information.",
                "Light teal = positive result.  Light red = warning / negative.  Lavender = optional or system list.",
                "Columns headed in grey ('AUTOMATION HELPERS') power the dashboards. Leave them in place; you may hide them (right-click › Hide).",
            ]),
            ("HOW TO ADD PROJECTS", [
                "Type the project name in the next empty row of Project Overview. Progress, budget, actual cost, remaining budget, days remaining, task counts and health fill in by themselves.",
                "Progress = average progress of the project's tasks (a task with the 'Completed' status counts as 100%). A project marked Completed shows 100%.",
                "Health: Completed / Cancelled / Overdue (past due date) / Over budget (actual > budget) / At risk (has overdue tasks) / On track.",
                "Add objectives, deliverables, milestones, dependencies, risks and notes in the database on the right of the 'Project Manager' tab.",
            ]),
            ("HOW TO CREATE TASKS", [
                "Variable Tasks: one-time tasks. Required for automation: Task Name. Recommended: Project, Assigned To, Start Date, Due Date, Priority, Status.",
                "Status drives the Kanban board (first five statuses in Setup = five Kanban columns). Changing a status moves the card automatically.",
                "Recurring Tasks: choose a frequency. For 'Custom', enter the interval in days. Update 'Last Completed' when you finish an occurrence — the next date moves forward.",
                "Task Schedule: pick a task from the dropdown (or type any event). Project, priority, status and owner fill in; the block appears on the Weekly Calendar.",
                "Need more rows? Excel edition: rows 7–506 are pre-built (500 tasks). Type directly below the last row of an Excel Table and it expands; copy the formulas of the row above into helper columns if they are not filled automatically.",
            ]),
            ("HOW THE DASHBOARDS WORK", [
                "All-in-One Dashboard: KPI cards use COUNTIF/COUNTIFS/SUM over the project, task and budget tables. Change 'Chart year' to re-draw the monthly productivity chart.",
                "Monthly Calendar: choose a year and month. Each day shows up to two tasks due (colour = task category; red = overdue), the first project deadline (▲) and a count of extra tasks / scheduled blocks.",
                "Weekly Calendar: type any date to view that week. Blocks show at their start hour; ⋮ marks the rest of a multi-hour block. Colour = priority.",
                "Task Filter: combine filters; blank = all. Up to 100 results are listed.",
                "Gantt Chart: choose a project (blank = all), Daily or Weekly view, and whether to hide completed tasks. The timeline starts on the Monday before the first task unless you type a start date.",
                "Kanban Board: up to 15 cards per column (the header shows the full count). ‼ = Critical, ▲ = High, a red date = overdue.",
            ]),
            ("FORMULA NOTES", [
                "'Today' everywhere comes from Setup › Effective today. Leave the override blank to use the real date, or type a date to see the workbook 'as of' that day.",
                "Filtered lists (dashboard lists, Task Filter, Kanban, Gantt, calendars) use helper columns that number matching rows 1, 2, 3… and INDEX/MATCH to fetch them. This works the same in Excel 2010+, Excel 365, Google Sheets and LibreOffice.",
                "Upcoming/overdue lists are sorted by due date using SMALL() on a 'rank' helper (due date + a tiny row offset so equal dates stay unique).",
                "Recurring next date: daily/weekly/biweekly/custom add whole intervals to the start date; monthly/quarterly/annual use EDATE so month-end dates stay valid.",
                "Currency: amounts are stored as plain numbers; the currency symbol from Setup is shown in headers and KPI labels.",
            ]),
            ("REMOVING DEMO DATA", [
                "Fastest: use the BLANK edition file supplied alongside this one — identical workbook, no demo rows.",
                "Manual: on Project Overview, Project Budget, Variable Tasks, Recurring Tasks, Task Schedule, the Project Manager database and Decision Matrix, select the light-blue input cells that contain data and press Delete. Never delete whole rows or grey columns.",
                "Then edit Setup › Team Members and the workspace details. Clear Setup › Today's date override if you set one.",
            ]),
            ("TROUBLESHOOTING", [
                "A dashboard shows blanks: check the task has a Task Name and (for date-based views) Start/Due dates; check the Project name matches exactly (use the dropdown).",
                "A dropdown is empty: the source list on Setup is empty — add items there.",
                "Kanban card missing: its Status must be one of the first five Task Statuses on Setup; only 15 cards per column are shown.",
                "Calendar shows '+N more': more than two tasks are due that day — use Task Filter with a date range to list them all.",
                "Dates show as numbers: format the cell as a Date (Home › Number › Short Date).",
                "Sheets are protected (Excel edition, display tabs only) to stop accidental overwrites. Review › Unprotect Sheet — no password.",
                "Google Sheets: if a chart looks different after import, click the chart › Edit chart to adjust colours; the data ranges are preserved.",
            ]),
        ]
        r = 5
        for head, lines in blocks:
            section(ws, T, r, 2, 4, head)
            r += 1
            for ln in lines:
                ws[f"C{r}"] = ln
                ws[f"C{r}"].font = T.font(10)
                ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="center")
                ws.row_dimensions[r].height = 30 if len(ln) > 120 else 18
                r += 1
            r += 1
        self.nav_links(ws, r, 3, 1, 1)

    # ================================================================ finalize
    def protect(self):
        if self.ed != "excel":
            return
        for name in (S_DASH, S_MCAL, S_WCAL, S_TF, S_KB, S_GC, S_DM, S_INS):
            ws = self.ws[name]
            for rng_ in self.unlocked[name]:
                for c in _cells(ws, rng_):
                    c.protection = Protection(locked=False)
            ws.protection.sheet = True
            ws.protection.formatColumns = False
            ws.protection.formatRows = False
            ws.protection.formatCells = False
        # Project Manager: lock only the formula panel; DB on right is unlocked
        ws = self.ws[S_PM]
        for rng_ in self.unlocked[S_PM]:
            for c in _cells(ws, rng_):
                c.protection = Protection(locked=False)
        ws.protection.sheet = True
        ws.protection.formatColumns = False
        ws.protection.formatRows = False

    def page_setup(self):
        areas = {S_DASH: "A1:Y93", S_MCAL: "A1:K39", S_WCAL: "A1:I41", S_KB: "A1:P53", S_GC: "A1:BS69", S_PM: "A1:G77",
                 S_DM: "A1:Q30", S_TF: "A1:L118", S_INS: "A1:D90", S_SETUP: "A1:O70"}
        for n in ORDER:
            ws = self.ws[n]
            ws.page_setup.orientation = "landscape"
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            ws.print_options.horizontalCentered = True
            ws.page_margins.left = ws.page_margins.right = 0.4
            ws.page_margins.top = ws.page_margins.bottom = 0.5
            if n in areas:
                ws.print_area = areas[n]
            else:
                ws.print_title_rows = f"{HDR}:{HDR}"

    def build(self):
        self.build_setup()
        self.build_pov()
        self.build_vt()
        self.build_pb()
        self.build_rt()
        self.build_ts()
        self.build_dash()
        self.build_mcal()
        self.build_wcal()
        self.build_pm()
        self.build_tf()
        self.build_dm()
        self.build_kb()
        self.build_gc()
        self.build_ins()
        self.protect()
        self.page_setup()
        self.wb.active = ORDER.index(S_DASH if self.demo else S_SETUP)
        for n in ORDER:
            self.ws[n].sheet_view.tabSelected = (n == (S_DASH if self.demo else S_SETUP))
        return self.wb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "dist" / "01_Ultimate_Project_Manager"))
    a = ap.parse_args()
    out = Path(a.out)
    files = []
    for ed, folder, suffix in (("excel", "Excel", "Excel"), ("gsheets", "Google_Sheets", "GoogleSheets")):
        for demo in (True, False):
            wb = Builder(ed, demo).build()
            p = out / folder / f"Ultimate_Project_Manager_{suffix}_{'DEMO' if demo else 'BLANK'}.xlsx"
            p.parent.mkdir(parents=True, exist_ok=True)
            wb.save(p)
            solidify_databars(p)
            files.append(p)
            print("wrote", p)
    return files


if __name__ == "__main__":
    main()
