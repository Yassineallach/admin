"""PRODUCT 3 — Weekly Planner Pro (8 tabs).

Usage:  python build_weekly_planner.py [--out DIR]
Builds four workbooks: Excel / Google-Sheets editions, each with DEMO data and BLANK.

Tabs: Setup · Week 1 … Week 6 (identical, independently reusable) · Monthly Calendar.

Formula policy (same as Product 1, valid in Excel 2013+, Excel 365, LibreOffice and Google Sheets):
  * INDEX/MATCH, SUMIFS/COUNTIFS, SUMPRODUCT; no spilled dynamic arrays, no LET/LAMBDA/XLOOKUP
  * conditional formatting only references cells on its own sheet (Google Sheets requirement), so every week tab
    keeps a few hidden helper cells (column N) that copy Setup values
  * every week's dates come from one cell ($N$3): Setup › Week 1 start + 7 × (n − 1), or the tab's own override
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, Protection
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName

from common import *  # noqa: F401,F403
from common import _cells
import common as _C
import icons
import sample_data_wp as SD

S_SETUP = "Setup"
WEEKS = [f"Week {i}" for i in range(1, 7)]
S_CAL = "Monthly Calendar"
ORDER = [S_SETUP, *WEEKS, S_CAL]
NAV = [(S_SETUP, "gear", "Setup")] + [(w, icons.week_num(i + 1), f"Wk {i + 1}") for i, w in enumerate(WEEKS)] + \
      [(S_CAL, "calendar", "Month")]

# ---------------------------------------------------------------- Setup geometry
LR1, LRN = 28, 39            # list slots (12)
HAB_N = 8                    # habits tracked (Setup F28:F35)
TODAY, WEEKSTART, WEEK1, WATER, EXGOAL, DONE = "PlannerToday", "WeekStartsOn", "Week1Start", "WaterGoal", "ExerciseGoal", "DoneStatus"
WSTART, WEND, SLOT = "WorkStart", "WorkEnd", "SlotMinutes"


def SL(c, n=LRN):
    return f"{S_SETUP}!${c}${LR1}:${c}${n}"


# ---------------------------------------------------------------- Week geometry
D0, DAY_H, BODY = 21, 13, 10             # first day card row, rows per day (12 + gap), task/schedule rows per day
DAY_ROW = [D0 + d * DAY_H for d in range(7)]
TASK_R1, TASK_RN = D0, D0 + 7 * DAY_H - 1
HT = D0 + 7 * DAY_H + 1                  # habit tracker section row (113)
DT = HT + HAB_N + 3                      # daily trackers section row
R_WATER, R_WMET, R_EXT, R_EXM, R_SCORE, R_TASKPCT = (DT + 2 + i for i in range(6))
CH = R_TASKPCT + 2                       # charts section
CH_H = 12
RF = CH + CH_H + 2                       # reflection section
LAST_W = RF + 6
DAYCOLS = "EFGHIJK"

# ---------------------------------------------------------------- Calendar geometry
G0 = 9                                   # first grid row
IMP1, IMPN = 43, 72                      # important dates / deadlines rows
MP1 = 77                                 # monthly priorities rows (12)


def qs(s):
    return quote(s)


class Builder:
    def __init__(self, edition: str, demo: bool):
        self.ed, self.demo = edition, demo
        self.T = Theme(edition)
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in ORDER}
        for n in ORDER:
            self.ws[n].sheet_properties.tabColor = LAVENDER if n == S_SETUP else (NAVY if n == S_CAL else BLUE)
        self.unlocked = {n: [] for n in ORDER}
        _C.TAB_ORDER[:] = ORDER

    # ------------------------------------------------------------ helpers
    def inp(self, sheet, rng_, numfmt=None, align=None):
        style_input(self.ws[sheet], rng_, self.T, numfmt, align)
        self.unlocked[sheet].append(rng_)

    def calc(self, sheet, rng_, numfmt=None, align=None, color=DARK):
        style_calc(self.ws[sheet], rng_, self.T, numfmt, align, color)

    def merge(self, ws, a, value=None):
        if ":" in a and a.split(":")[0] != a.split(":")[1]:
            ws.merge_cells(a)
        tl = a.split(":")[0]
        if value is not None:
            ws[tl] = value
        return ws[tl]

    def label(self, ws, a, text, size=10, bold=True, color=DARK, align=None):
        c = self.merge(ws, a, text)
        c.font = self.T.font(size, bold, color)
        c.alignment = align or Alignment(vertical="center", indent=1)
        return c

    def subhead(self, ws, a, text, color=MIDNIGHT, fill_="E2F2EF", align=None):
        c = self.merge(ws, a, text)
        paint(ws, a, f=fill(fill_), border=_C.CELL_BOX)
        c.font = self.T.font(9, True, color)
        c.alignment = align or Alignment(vertical="center", indent=1)

    def tile(self, ws, r, c1, c2, label, formula, numfmt=None, accent=BLUE):
        top = Side(style="medium", color=accent)
        for rr in (r, r + 1):
            if c2 > c1:
                ws.merge_cells(f"{L(c1)}{rr}:{L(c2)}{rr}")
            for cc in range(c1, c2 + 1):
                ws.cell(row=rr, column=cc).fill = FILL_WHITE
                ws.cell(row=rr, column=cc).border = Border(top=top if rr == r else None, bottom=THIN if rr == r + 1 else None,
                                                           left=THIN if cc == c1 else None, right=THIN if cc == c2 else None)
        lc = ws.cell(row=r, column=c1, value=label)
        lc.font = self.T.font(8, True, SECONDARY)
        lc.alignment = Alignment(vertical="bottom", indent=1)
        vc = ws.cell(row=r + 1, column=c1, value=formula)
        vc.font = self.T.font(15, True, DARK)
        vc.alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
        if numfmt:
            vc.number_format = numfmt
        ws.row_dimensions[r].height = 18
        ws.row_dimensions[r + 1].height = 30

    # ============================================================ SETUP
    def build_setup(self):
        ws, T, S = self.ws[S_SETUP], self.T, S_SETUP
        widths = {"B": 30, "C": 25, "D": 21, "E": 18, "F": 21, "G": 17, "H": 13, "I": 13, "J": 26, "K": 16, "L": 12}
        setup_sheet(ws, widths)
        title_bar(ws, T, "WEEKLY PLANNER PRO  ·  Setup", "Start here — your details, preferences and the lists every dropdown uses.",
                  12, home_link=None, demo=self.demo)
        c = self.merge(ws, "B5:L8", (
            "WELCOME TO WEEKLY PLANNER PRO.   1) Fill in your details and preferences below.   2) Set the date Week 1 starts "
            "(blank = this week). Weeks 2–6 follow on automatically.   3) Plan each week on the Week 1 … Week 6 tabs and see "
            "the month on Monthly Calendar.   Light-mint cells are for typing; grey cells calculate by themselves. "
            "To reuse a week tab later, type a new start date on it and clear its mint cells. "
            + ("This copy contains DEMO DATA — use the BLANK file to start fresh." if self.demo else "")))
        paint(ws, "B5:L8", f=fill(SOFT_BLUE))
        c.font = T.font(10, False, MIDNIGHT)
        c.alignment = LEFT_WRAP
        for r in range(5, 9):
            ws.row_dimensions[r].height = 17
        ws.row_dimensions[4].height = 12
        legend(ws, T, 9, 2)
        ws.row_dimensions[9].height = 24

        def rows(r0, items, c_lab, c_in, hint_rng):
            for i, (lab, val, kind, hint) in enumerate(items):
                r = r0 + i
                self.label(ws, f"{c_lab}{r}", lab)
                ws[f"{c_in.split(':')[0]}{r}"] = val
                rng_ = f"{c_in.split(':')[0]}{r}" if ":" not in c_in else f"{c_in.split(':')[0]}{r}:{c_in.split(':')[1]}{r}"
                if ":" in c_in:
                    ws.merge_cells(rng_)
                fmt = {"date": FMT_DATE, "time": "h:mm AM/PM", "int": "0"}.get(kind)
                if kind == "calc":
                    self.calc(S, rng_, FMT_DATE if "date" in lab.lower() or "start" in lab.lower() or "today" in lab.lower() else None)
                elif kind == "opt":
                    paint(ws, rng_, f=FILL_OPT, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
                    self.unlocked[S].append(rng_)
                else:
                    self.inp(S, rng_, numfmt=fmt)
                h = self.merge(ws, f"{hint_rng[0]}{r}:{hint_rng[1]}{r}", hint)
                h.font = T.font(9, False, SECONDARY, italic=True)
                h.alignment = Alignment(vertical="center", indent=1)
                ws.row_dimensions[r].height = 21

        section(ws, T, 10, 2, 5, "PERSONAL INFORMATION")
        rows(11, [("Your name", SD.NAME if self.demo else None, "text", "Shown on every week tab"),
                  ("Planner title", SD.TITLE if self.demo else "My Weekly Planner", "text", "Title on the week tabs"),
                  ("Email (optional)", SD.EMAIL if self.demo else None, "opt", "Optional"),
                  ("Focus word for the year", SD.MOTTO if self.demo else None, "opt", "Optional — a reminder on each week")],
             "B", "C", ("D", "E"))
        section(ws, T, 10, 7, 12, "WORKING HOURS")
        for i, (lab, val, kind, hint) in enumerate([("Day starts", dt.time(8, 0), "time", "First schedule slot"),
                                                    ("Day ends", dt.time(18, 0), "time", "Slots stop before this time"),
                                                    ("Slot length (minutes)", 60, "int", "30, 60, 90 or 120 — 10 slots per day")]):
            r = 11 + i
            self.label(ws, f"G{r}:H{r}", lab)
            ws[f"I{r}"] = val
            self.inp(S, f"I{r}", numfmt="h:mm AM/PM" if kind == "time" else "0", align=CENTER)
            h = self.merge(ws, f"J{r}:L{r}", hint)
            h.font = T.font(9, False, SECONDARY, italic=True)
            h.alignment = Alignment(vertical="center", indent=1)
        self.label(ws, "G14:H14", "Schedule shown")
        self.merge(ws, "I14:L14", '=TEXT(I11,"h:mm AM/PM")&" – "&TEXT(MIN(I12,I11+10*I13/1440),"h:mm AM/PM")&"  ·  "&'
                                  'MIN(10,ROUNDUP((I12-I11)*1440/I13,0))&" slots of "&I13&" min"')
        self.calc(S, "I14:L14")
        add_dv(ws, "I11:I12", "time", "between", "0", "0.999999", error="Enter a time such as 8:00 AM.")
        add_list_dv(ws, "I13", SL("I", LR1 + 3))

        section(ws, T, 16, 2, 5, "PLANNING PREFERENCES")
        rows(17, [("Week starts on", "Monday", "text", "Monday or Sunday — weeks and calendar follow"),
                  ("Week 1 starts on", SD.FIRST_WEEK if self.demo else None, "date", "Blank = the current week"),
                  ("Today's date override", SD.ANCHOR if self.demo else None, "date",
                   "DEMO date — clear it to use today" if self.demo else "Leave blank to use the real date"),
                  ("Effective today", '=IF(C19="",TODAY(),C19)', "calc", "Drives every 'today' highlight"),
                  ("Week 1 start (calculated)", '=IF(C18="",C20,C18)-MOD(WEEKDAY(IF(C18="",C20,C18))-IF(C17="Sunday",1,2),7)',
                   "calc", "Moved back to your week-start day"),
                  ("Daily water goal (glasses)", 8, "int", "Water tracker turns ✓ at this amount"),
                  ("Weekly exercise goal (min)", 150, "int", "150 min is the WHO guideline for adults"),
                  ('Status that means "done"', SD.DONE, "text", "Counts towards progress everywhere")],
             "B", "C", ("D", "E"))
        add_list_dv(ws, "C17", SL("H", LR1 + 1))
        add_dv(ws, "C18:C19", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a valid date, or leave blank.")
        add_dv(ws, "C22", "whole", "between", "1", "30")
        add_dv(ws, "C23", "whole", "between", "0", "3000")
        add_list_dv(ws, "C24", SL("E"))

        section(ws, T, 16, 7, 12, "YOUR SIX WEEKS")
        for c, h in zip("GHI", ("Week", "Starts", "Ends")):
            self.subhead(ws, f"{c}17", h, align=CENTER)
        self.subhead(ws, "J17:K17", "Main goal")
        self.subhead(ws, "L17", "Progress", align=CENTER)
        for i, w in enumerate(WEEKS):
            r = 18 + i
            ws[f"G{r}"] = f'=HYPERLINK("#{qs(w)}!A1","{w}  ›")'
            paint(ws, f"G{r}", f=FILL_WHITE, font=T.font(10, True, BLUE), border=_C.CELL_BOX, align=LEFT)
            ws[f"H{r}"] = f"={qs(w)}!$N$3"
            ws[f"I{r}"] = f"={qs(w)}!$N$3+6"
            self.calc(S, f"H{r}:I{r}", FMT_SDATE, CENTER)
            self.merge(ws, f"J{r}:K{r}", f'=IF({qs(w)}!$D$13="","—",{qs(w)}!$D$13)')
            self.calc(S, f"J{r}:K{r}", align=Alignment(vertical="center", indent=1, shrink_to_fit=True))
            ws[f"L{r}"] = f"={qs(w)}!$N$4"
            self.calc(S, f"L{r}", FMT_PCT, CENTER)
            ws.row_dimensions[r].height = 21
        cf_databar(ws, "L18:L23", TEAL)
        cf_formula(ws, "G18:L23", "AND($C$20>=$H18,$C$20<=$I18)", font_color=NAVY, bold=True)
        self.label(ws, "G24:L24", "The highlighted week contains today. Click a week to open it.", 9, False, SECONDARY)
        ws["G24"].font = T.font(9, False, SECONDARY, italic=True)

        section(ws, T, 26, 2, 7, "YOUR LISTS  —  edit freely (12 slots each; habits: 8)")
        section(ws, T, 26, 8, 12, "SYSTEM LISTS  —  used by formulas", color=LAVENDER)
        lists = {
            "B": ("Categories", SD.CATEGORIES),
            "C": ("Priority levels", [p for p, _ in SD.PRIORITIES]),
            "D": ("Priority meaning", [m for _, m in SD.PRIORITIES]),
            "E": ("Task statuses", SD.STATUSES),
            "F": ("Habits (tracked)", SD.HABITS if self.demo else SD.HABITS[:5]),
            "G": ("Exercise types", SD.EXERCISE),
        }
        system = {"H": ("Week starts", ["Monday", "Sunday"]), "I": ("Slot (min)", [30, 60, 90, 120]),
                  "J": ("Months", ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                                   "October", "November", "December"]),
                  "K": ("Marks", ["✓", "✗"]), "L": ("Years", list(range(2025, 2037)))}
        for c, (head, items) in {**lists, **system}.items():
            self.subhead(ws, f"{c}27", head, align=CENTER, fill_="E2F2EF" if c in lists else "EFEAFB")
            n = HAB_N if c == "F" else LRN - LR1 + 1
            for i in range(LRN - LR1 + 1):
                ws[f"{c}{LR1 + i}"] = items[i] if i < len(items) and i < n else None
            if c in lists:
                if c == "D":
                    paint(ws, f"D{LR1}:D{LRN}", f=FILL_OPT, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
                    self.unlocked[S].append(f"D{LR1}:D{LRN}")
                else:
                    self.inp(S, f"{c}{LR1}:{c}{LR1 + n - 1}")
            else:
                paint(ws, f"{c}{LR1}:{c}{LRN}", f=FILL_OPT, font=T.font(10), border=_C.CELL_BOX, align=CENTER)
        paint(ws, f"F{LR1 + HAB_N}:F{LRN}", f=FILL_WHITE, border=_C.CELL_BOX)
        ws[f"F{LR1 + HAB_N}"] = "(8 habits per week)"
        ws[f"F{LR1 + HAB_N}"].font = T.font(8, False, SECONDARY, italic=True)
        ws[f"F{LR1 + HAB_N}"].alignment = Alignment(vertical="center", indent=1)
        for r in range(LR1, LRN + 1):
            ws.row_dimensions[r].height = 19

        section(ws, T, 41, 2, 12, "HOW THIS PLANNER WORKS")
        tips = [
            "Week tabs — each has a week overview (goal, top 3 priorities, progress), seven day cards (priorities, tasks, schedule, "
            "appointments, notes) and trackers (habits, water, exercise, productivity score, weekly reflection).",
            "Dates — Week 1 starts on the date above; Week 2 is 7 days later and so on. Type a date in a week tab's "
            "'Week starts on (optional)' cell to give that tab any week you like.",
            "Progress — a task counts as done when its Status is the 'done' status above. Day cards, weekly tiles, the six-week "
            "table and the Monthly Calendar all update automatically.",
            "Schedule — each day card shows 10 time slots from your working hours (start time + slot length).",
            "Monthly Calendar — pick a year and month. It shows your important dates (★), deadlines (⚑), the tasks you planned "
            "on the week tabs (☑ done/total), each week's main goal and your priorities for that month.",
            "Reusing a week tab — type the new start date, then select its mint cells and press Delete. In Excel you can type "
            "the tab's name with '_Inputs' (e.g. Week1_Inputs) in the Name Box to select all of them at once."
            if self.ed == "excel" else
            "Reusing a week tab — type the new start date, then select its mint cells and press Delete. Grey cells hold "
            "formulas: leave them in place.",
            "Protection — " + ("tabs are protected (no password) so formulas can't be overwritten by accident: Review › "
                               "Unprotect Sheet if you want to change the layout." if self.ed == "excel" else
                               "nothing is locked in the Google Sheets edition; avoid typing over grey cells."),
        ]
        for i, t in enumerate(tips):
            r = 42 + i
            c = self.merge(ws, f"B{r}:L{r}", "•  " + t)
            c.font = T.font(10)
            c.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
            ws.row_dimensions[r].height = 30
        ws.freeze_panes = "A4"
        for r in (15, 25, 40):
            ws.row_dimensions[r].height = 12
        skin(ws, 12, 42 + len(tips), cards=[(2, 10, 5, 14), (7, 10, 12, 14), (2, 16, 5, 24), (7, 16, 12, 24),
                                               (2, 26, 12, LRN), (2, 41, 12, 41 + len(tips))], hide_headers=True)
        names = {TODAY: "$C$20", WEEKSTART: "$C$17", WEEK1: "$C$21", WATER: "$C$22", EXGOAL: "$C$23", DONE: "$C$24",
                 WSTART: "$I$11", WEND: "$I$12", SLOT: "$I$13",
                 "CategoryList": f"$B${LR1}:$B${LRN}", "PriorityList": f"$C${LR1}:$C${LRN}", "StatusList": f"$E${LR1}:$E${LRN}",
                 "HabitList": f"$F${LR1}:$F${LR1 + HAB_N - 1}", "ExerciseList": f"$G${LR1}:$G${LRN}"}
        for n, a in names.items():
            self.wb.defined_names[n] = DefinedName(n, attr_text=f"{S_SETUP}!{a}")

    # ============================================================ WEEK TABS
    def build_week(self, n: int):
        name = WEEKS[n - 1]
        ws, T = self.ws[name], self.T
        setup_sheet(ws, {L(c): 13.5 for c in range(2, 13)})
        title_bar(ws, T, f"WEEK {n}  ·  Weekly Planner", f'=IF({S_SETUP}!$C$12="","Weekly Planner Pro",{S_SETUP}!$C$12)&"   ·   "&'
                  f'TEXT($N$3,"mmm d")&" – "&TEXT($N$3+6,"mmm d, yyyy")&IF({S_SETUP}!$C$14="","","   ·   Focus: "&{S_SETUP}!$C$14)',
                  12, home_link=S_SETUP, home_label="⌂ Setup", demo=False)
        if self.demo:
            ws["B3"] = f'="●  DEMO DATA   ·   "&' + ws["B3"].value[1:]
        # hidden helpers (column N..P)
        helpers = {2: (f"={TODAY}", FMT_DATE), 3: (f'=IF($D$12="",{WEEK1}+7*({n}-1),$D$12-MOD(WEEKDAY($D$12)-IF({WEEKSTART}="Sunday",1,2),7))', FMT_DATE),
                   4: (f'=IF(COUNT($N${TASK_R1}:$N${TASK_RN})=0,"",COUNTIFS($N${TASK_R1}:$N${TASK_RN},">0",$I${TASK_R1}:$I${TASK_RN},$N$5)/COUNT($N${TASK_R1}:$N${TASK_RN}))', FMT_PCT),
                   5: (f"={DONE}", None), 6: (f"=INDEX(PriorityList,1)", None), 7: (f"={WATER}", "0"), 8: (f"={EXGOAL}", "0")}
        for r, (fm, nf) in helpers.items():
            ws[f"N{r}"] = fm
            if nf:
                ws[f"N{r}"].number_format = nf
            ws[f"M{r}"] = ["", "", "today", "week start", "progress", "done status", "top priority", "water goal", "exercise goal"][r]
        for c in "MNOP":
            ws.column_dimensions[c].hidden = True

        # ---- overview
        ws.row_dimensions[4].height = 10
        section(ws, T, 5, 2, 12, "WEEK OVERVIEW")
        total = f"COUNT($N${TASK_R1}:$N${TASK_RN})"
        done = f'COUNTIFS($N${TASK_R1}:$N${TASK_RN},">0",$I${TASK_R1}:$I${TASK_RN},$N$5)'
        hab = f"$E${HT + 2}:$K${HT + 1 + HAB_N}"
        self.tile(ws, 6, 2, 4, "WEEK NUMBER", '="Week "&INT((($N$3+3)-DATE(YEAR(($N$3+3)-WEEKDAY(($N$3+3)-1)+4),1,3)+WEEKDAY(DATE(YEAR(($N$3+3)-WEEKDAY(($N$3+3)-1)+4),1,3))+5)/7)&"  ·  "&YEAR(($N$3+3)-WEEKDAY(($N$3+3)-1)+4)', accent=NAVY)
        self.tile(ws, 6, 5, 7, "START – END", '=TEXT($N$3,"ddd mmm d")&" – "&TEXT($N$3+6,"ddd mmm d")', accent=BLUE)
        self.tile(ws, 6, 8, 9, "WEEKLY PROGRESS", f'=IF({total}=0,"No tasks yet",$N$4)', FMT_PCT, accent=TEAL)
        self.tile(ws, 6, 10, 12, "TASKS DONE", f'={done}&" of "&{total}', accent=TEAL)
        ws.row_dimensions[8].height = 6
        self.tile(ws, 9, 2, 4, "HABITS DONE", f'=COUNTIF({hab},"✓")&" of "&7*COUNTIF($B${HT + 2}:$B${HT + 1 + HAB_N},"?*")', accent=LAVENDER)
        self.tile(ws, 9, 5, 7, "WATER GOAL MET", f'=COUNTIF($E${R_WMET}:$K${R_WMET},"✓")&" of 7 days"', accent=BLUE)
        self.tile(ws, 9, 8, 9, "EXERCISE", f'=SUM($E${R_EXM}:$K${R_EXM})&" / "&$N$8&" min"', accent=WARNING)
        self.tile(ws, 9, 10, 12, "AVG PRODUCTIVITY",
                  f'=IF(COUNT($E${R_SCORE}:$K${R_SCORE})=0,"—",TEXT(AVERAGE($E${R_SCORE}:$K${R_SCORE}),"0.0")&" / 10")', accent=LAVENDER)
        cf_databar(ws, "H7", TEAL)
        ws.row_dimensions[11].height = 8
        r = 12
        self.label(ws, f"B{r}:C{r}", "Week starts on (optional)")
        self.inp(name, f"D{r}", FMT_SDATE, CENTER)
        add_dv(ws, f"D{r}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date, or leave blank.")
        h = self.label(ws, f"E{r}:G{r}", f"Blank = Week 1 + {n - 1} weeks" if n > 1 else "Blank = Setup › Week 1", 9, False, SECONDARY)
        h.font = T.font(9, False, SECONDARY, italic=True)
        self.label(ws, f"H{r}", "Start", 9, True, SECONDARY, RIGHT)
        ws[f"I{r}"] = "=$N$3"
        self.calc(name, f"I{r}", "ddd mmm d", CENTER)
        self.label(ws, f"J{r}", "End", 9, True, SECONDARY, RIGHT)
        self.merge(ws, f"K{r}:L{r}", "=$N$3+6")
        self.calc(name, f"K{r}:L{r}", "ddd mmm d", CENTER)
        r = 13
        self.label(ws, f"B{r}:C{r}", "Weekly main goal")
        self.merge(ws, f"D{r}:L{r}")
        self.inp(name, f"D{r}:L{r}")
        ws[f"D{r}"].font = T.font(11, True, NAVY)
        ws.row_dimensions[12].height = 22
        ws.row_dimensions[13].height = 24
        self.subhead(ws, "B14", "Done", align=CENTER)
        self.subhead(ws, "C14:L14", "Top 3 priorities this week")
        for i in range(3):
            r = 15 + i
            self.inp(name, f"B{r}", align=CENTER)
            self.merge(ws, f"C{r}:L{r}")
            self.inp(name, f"C{r}:L{r}")
            ws.row_dimensions[r].height = 20
        add_list_dv(ws, "B15:B17", SL("K", LR1 + 1))
        ws.row_dimensions[18].height = 8
        # jump links
        for d in range(7):
            cl = L(2 + d)
            ws[f"{cl}19"] = f'=HYPERLINK("#{qs(name)}!B{DAY_ROW[d]}",TEXT($N$3+{d},"ddd d"))'
        self.merge(ws, "I19:J19", f'=HYPERLINK("#{qs(name)}!B{HT}","Trackers ↓")')
        self.merge(ws, "K19:L19", f'=HYPERLINK("#{qs(name)}!B{RF}","Reflection ↓")')
        paint(ws, "B19:L19", f=fill(SOFT_BLUE), font=T.font(9, True, MIDNIGHT), align=CENTER,
              border=Border(left=Side(style="thin", color=WHITE), right=Side(style="thin", color=WHITE)))
        ws.row_dimensions[19].height = 22
        ws.row_dimensions[20].height = 10
        cf_formula(ws, "B19:H19", "$N$3+COLUMN(B19)-2=$N$2", TEAL, WHITE, True)

        # ---- day cards
        cards = [(2, 5, 12, 10), (2, 12, 12, 17)]
        st_rule_font = Font(color="8A9B99", strike=True)
        for d in range(7):
            r0 = DAY_ROW[d]
            rb1, rbn = r0 + 2, r0 + 1 + BODY
            self.merge(ws, f"B{r0}:D{r0}", f"=$N$3+{d}")
            ws[f"B{r0}"].number_format = "dddd"
            self.merge(ws, f"E{r0}:I{r0}", f"=$N$3+{d}")
            ws[f"E{r0}"].number_format = "mmmm d, yyyy"
            self.merge(ws, f"J{r0}:L{r0}", f'=IF(O{r0}=0,"No tasks yet",P{r0}&" of "&O{r0}&" done  ·  "&TEXT(P{r0}/O{r0},"0%"))')
            paint(ws, f"B{r0}:L{r0}", f=fill(MIDNIGHT))
            ws[f"B{r0}"].font = T.font(13, True, WHITE)
            ws[f"E{r0}"].font = T.font(10, False, HERO_SUB)
            ws[f"J{r0}"].font = T.font(9, True, WHITE)
            ws[f"B{r0}"].alignment = Alignment(vertical="center", indent=1)
            ws[f"E{r0}"].alignment = Alignment(vertical="center", indent=1)
            ws[f"J{r0}"].alignment = Alignment(horizontal="right", vertical="center", indent=1)
            ws.row_dimensions[r0].height = 26
            cf_formula(ws, f"B{r0}:L{r0}", f"$B${r0}=$N$2", TEAL, WHITE, True)
            ws[f"O{r0}"] = f'=COUNTIF($E${rb1}:$E${rbn},"?*")'
            ws[f"P{r0}"] = f'=COUNTIFS($E${rb1}:$E${rbn},"?*",$I${rb1}:$I${rbn},$N$5)'
            # sub headers
            h = r0 + 1
            self.subhead(ws, f"B{h}", "Done", align=CENTER)
            self.subhead(ws, f"C{h}:D{h}", "Top 3 priorities")
            self.subhead(ws, f"E{h}:F{h}", "Task checklist")
            for c, t in (("G", "Category"), ("H", "Priority"), ("I", "Status"), ("J", "Time")):
                self.subhead(ws, f"{c}{h}", t, align=CENTER)
            self.subhead(ws, f"K{h}:L{h}", "Schedule")
            ws.row_dimensions[h].height = 20
            for i in range(3):
                rr = r0 + 2 + i
                self.inp(name, f"B{rr}", align=CENTER)
                self.merge(ws, f"C{rr}:D{rr}")
                self.inp(name, f"C{rr}:D{rr}")
            add_list_dv(ws, f"B{r0 + 2}:B{r0 + 4}", SL("K", LR1 + 1))
            self.subhead(ws, f"B{r0 + 5}", "Time", align=CENTER, fill_="EFEAFB")
            self.subhead(ws, f"C{r0 + 5}:D{r0 + 5}", "Appointments", fill_="EFEAFB")
            for i in range(3):
                rr = r0 + 6 + i
                self.inp(name, f"B{rr}", "h:mm AM/PM", CENTER)
                self.merge(ws, f"C{rr}:D{rr}")
                self.inp(name, f"C{rr}:D{rr}")
            add_dv(ws, f"B{r0 + 6}:B{r0 + 8}", "time", "between", "0", "0.999999", error="Enter a time such as 9:30 AM.")
            self.subhead(ws, f"B{r0 + 9}:D{r0 + 9}", "Notes", fill_="EFEAFB")
            self.merge(ws, f"B{r0 + 10}:D{r0 + 11}")
            self.inp(name, f"B{r0 + 10}:D{r0 + 11}", align=LEFT_WRAP)
            for i in range(BODY):
                rr = rb1 + i
                self.merge(ws, f"E{rr}:F{rr}")
                self.inp(name, f"E{rr}:F{rr}")
                self.inp(name, f"G{rr}:I{rr}", align=CENTER)
                ws[f"N{rr}"] = f'=IF(E{rr}="","",$B${r0})'
                ws[f"J{rr}"] = f'=IF({WSTART}+{i}*{SLOT}/1440<{WEND}-0.00001,{WSTART}+{i}*{SLOT}/1440,"")'
                self.calc(name, f"J{rr}", "h:mm AM/PM", CENTER, color=SECONDARY)
                self.merge(ws, f"K{rr}:L{rr}")
                self.inp(name, f"K{rr}:L{rr}")
                ws.row_dimensions[rr].height = 19
            add_list_dv(ws, f"G{rb1}:G{rbn}", SL("B"))
            add_list_dv(ws, f"H{rb1}:H{rbn}", SL("C"))
            add_list_dv(ws, f"I{rb1}:I{rbn}", SL("E"))
            ws.conditional_formatting.add(f"E{rb1}:F{rbn}", FormulaRule(formula=[f'AND($E{rb1}<>"",$I{rb1}=$N$5)'], font=st_rule_font))
            cf_formula(ws, f"I{rb1}:I{rbn}", f'AND($I{rb1}<>"",$I{rb1}=$N$5)', SOFT_TEAL, TEAL, True)
            cf_formula(ws, f"H{rb1}:H{rbn}", f'AND($H{rb1}<>"",$H{rb1}=$N$6)', DANGER_BG, DANGER, True)
            cf_formula(ws, f"B{r0 + 2}:B{r0 + 4}", f'B{r0 + 2}="✓"', SOFT_TEAL, TEAL, True)
            cf_formula(ws, f"C{r0 + 2}:D{r0 + 4}", f'$B{r0 + 2}="✓"', font_color="8A9B99")
            ws.row_dimensions[r0 + 12].height = 12
            cards.append((2, r0, 12, rbn))
        cf_formula(ws, "B15:B17", 'B15="✓"', SOFT_TEAL, TEAL, True)

        # ---- habit tracker
        section(ws, T, HT, 2, 12, "HABIT TRACKER  —  pick ✓ or ✗ each day (habits come from Setup)", color=LAVENDER)
        self.subhead(ws, f"B{HT + 1}:D{HT + 1}", "Habit")
        for d, c in enumerate(DAYCOLS):
            ws[f"{c}{HT + 1}"] = f'=TEXT($N$3+{d},"ddd d")'
            self.subhead(ws, f"{c}{HT + 1}", ws[f"{c}{HT + 1}"].value, align=CENTER)
        self.subhead(ws, f"L{HT + 1}", "Done", align=CENTER)
        for i in range(HAB_N):
            r = HT + 2 + i
            self.merge(ws, f"B{r}:D{r}", f'=IF(INDEX(HabitList,{i + 1})="","",INDEX(HabitList,{i + 1}))')
            paint(ws, f"B{r}:D{r}", f=FILL_WHITE, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
            self.inp(name, f"E{r}:K{r}", align=CENTER)
            ws[f"L{r}"] = f'=IF(B{r}="","",COUNTIF(E{r}:K{r},"✓"))'
            self.calc(name, f"L{r}", '0" / 7"', CENTER, color=TEAL)
            ws.row_dimensions[r].height = 19
        add_list_dv(ws, f"E{HT + 2}:K{HT + 1 + HAB_N}", SL("K", LR1 + 1))
        cf_formula(ws, f"E{HT + 2}:K{HT + 1 + HAB_N}", f'E{HT + 2}="✓"', SOFT_TEAL, TEAL, True)
        cf_formula(ws, f"E{HT + 2}:K{HT + 1 + HAB_N}", f'E{HT + 2}="✗"', DANGER_BG, DANGER)
        cards.append((2, HT, 12, HT + 1 + HAB_N))

        # ---- daily trackers
        section(ws, T, DT, 2, 12, "DAILY TRACKERS  —  water, exercise and productivity", color=TEAL)
        self.subhead(ws, f"B{DT + 1}:D{DT + 1}", "Tracker")
        for d, c in enumerate(DAYCOLS):
            self.subhead(ws, f"{c}{DT + 1}", f'=TEXT($N$3+{d},"ddd d")', align=CENTER)
        self.subhead(ws, f"L{DT + 1}", "Week", align=CENTER)
        rows = [(R_WATER, "Water (glasses)", "inp", "0", "=IF(COUNT(E{r}:K{r})=0,\"\",SUM(E{r}:K{r}))", "0"),
                (R_WMET, '="Water goal met ("&$N$7&"+)"', "calc", None, '=COUNTIF(E{r}:K{r},"✓")', '0" / 7"'),
                (R_EXT, "Exercise type", "inp", None, "", None),
                (R_EXM, "Exercise (minutes)", "inp", "0", "=SUM(E{r}:K{r})", "0"),
                (R_SCORE, "Productivity score (1–10)", "inp", "0", '=IF(COUNT(E{r}:K{r})=0,"",AVERAGE(E{r}:K{r}))', "0.0"),
                (R_TASKPCT, "Tasks completed", "calc", FMT_PCT, "=$N$4", FMT_PCT)]
        for r, lab, kind, nf, wk, wnf in rows:
            self.merge(ws, f"B{r}:D{r}", lab)
            paint(ws, f"B{r}:D{r}", f=FILL_WHITE, font=T.font(10, True), border=_C.CELL_BOX, align=LEFT)
            if kind == "inp":
                self.inp(name, f"E{r}:K{r}", nf, CENTER)
            else:
                self.calc(name, f"E{r}:K{r}", nf, CENTER)
            ws[f"L{r}"] = wk.format(r=r) if wk else None
            self.calc(name, f"L{r}", wnf, CENTER, color=NAVY)
            ws.row_dimensions[r].height = 20
        for d, c in enumerate(DAYCOLS):
            ws[f"{c}{R_WMET}"] = f'=IF({c}{R_WATER}="","",IF({c}{R_WATER}>=$N$7,"✓","✗"))'
            r0 = DAY_ROW[d]
            ws[f"{c}{R_TASKPCT}"] = f'=IF(O{r0}=0,"",P{r0}/O{r0})'
        add_dv(ws, f"E{R_WATER}:K{R_WATER}", "whole", "between", "0", "40", error="Glasses: a whole number from 0 to 40.")
        add_list_dv(ws, f"E{R_EXT}:K{R_EXT}", SL("G"))
        add_dv(ws, f"E{R_EXM}:K{R_EXM}", "whole", "between", "0", "600", error="Minutes: 0 to 600.")
        add_dv(ws, f"E{R_SCORE}:K{R_SCORE}", "whole", "between", "1", "10", error="Score: a whole number from 1 to 10.")
        cf_formula(ws, f"E{R_WMET}:K{R_WMET}", f'E{R_WMET}="✓"', SOFT_TEAL, TEAL, True)
        cf_formula(ws, f"E{R_WMET}:K{R_WMET}", f'E{R_WMET}="✗"', DANGER_BG, DANGER)
        cf_formula(ws, f"E{R_SCORE}:K{R_SCORE}", f'AND(ISNUMBER(E{R_SCORE}),E{R_SCORE}>=8)', SOFT_TEAL, TEAL, True)
        cf_formula(ws, f"E{R_SCORE}:K{R_SCORE}", f'AND(ISNUMBER(E{R_SCORE}),E{R_SCORE}<=4)', DANGER_BG, DANGER)
        cf_formula(ws, f"L{R_EXM}", f"L{R_EXM}>=$N$8", SOFT_TEAL, TEAL, True)
        cf_databar(ws, f"E{R_TASKPCT}:K{R_TASKPCT}", TEAL)
        cards.append((2, DT, 12, R_TASKPCT))

        # ---- charts
        section(ws, T, CH, 2, 12, "THIS WEEK AT A GLANCE")
        for r in range(CH + 1, CH + CH_H + 1):
            ws.row_dimensions[r].height = 18
        self.chart(ws, R_SCORE, "Productivity score by day", BLUE, 2, 6, 10)
        self.chart(ws, R_TASKPCT, "Tasks completed by day", TEAL, 7, 12, 1, pct=True)
        cards.append((2, CH, 12, CH + CH_H))

        # ---- reflection
        section(ws, T, RF, 2, 12, "WEEKLY REFLECTION", color=LAVENDER)
        prompts = ["What went well?", "What was challenging?", "What did I learn?", "My focus for next week"]
        for i, p in enumerate(prompts):
            r = RF + 1 + i
            self.label(ws, f"B{r}:D{r}", p)
            paint(ws, f"B{r}:D{r}", f=FILL_WHITE, border=_C.CELL_BOX)
            self.merge(ws, f"E{r}:L{r}")
            self.inp(name, f"E{r}:L{r}", align=LEFT_WRAP)
            ws.row_dimensions[r].height = 34
        r = RF + 5
        self.label(ws, f"B{r}:D{r}", "Week rating (1–10)")
        paint(ws, f"B{r}:D{r}", f=FILL_WHITE, border=_C.CELL_BOX)
        self.inp(name, f"E{r}", "0", CENTER)
        add_dv(ws, f"E{r}", "whole", "between", "1", "10", error="Rating: 1 to 10.")
        self.merge(ws, f"F{r}:L{r}", f'=IF(E{r}="","",REPT("★",E{r})&REPT("☆",10-E{r}))')
        paint(ws, f"F{r}:L{r}", f=FILL_WHITE, font=T.font(14, False, WARNING), border=_C.CELL_BOX, align=LEFT)
        ws.row_dimensions[r].height = 26
        cards.append((2, RF, 12, RF + 5))

        ws.freeze_panes = "A4"
        skin(ws, 12, LAST_W, cards=cards, hide_headers=True)
        # demo content
        if self.demo:
            self.fill_week(ws, n)
        if self.ed == "excel":
            # whole merged areas only (Excel refuses to clear part of a merged cell)
            refs = ["$D$12", "$D$13:$L$13", "$B$15:$L$17"]
            for r0 in DAY_ROW:
                refs += [f"$B${r0 + 2}:$D${r0 + 4}", f"$B${r0 + 6}:$D${r0 + 8}", f"$B${r0 + 10}:$D${r0 + 11}",
                         f"$E${r0 + 2}:$I${r0 + 11}", f"$K${r0 + 2}:$L${r0 + 11}"]
            refs += [f"$E${HT + 2}:$K${HT + 1 + HAB_N}", f"$E${R_WATER}:$K${R_WATER}", f"$E${R_EXT}:$K${R_EXM}",
                     f"$E${R_SCORE}:$K${R_SCORE}", f"$E${RF + 1}:$L${RF + 4}", f"$E${RF + 5}"]
            nm = f"Week{n}_Inputs"
            self.wb.defined_names[nm] = DefinedName(nm, attr_text=",".join(f"{qs(name)}!{x}" for x in refs))

    def chart(self, ws, row, title, color, c1, c2, ymax, pct=False):
        ch = BarChart()
        ch.type = "col"
        ch.title = title
        ch.style = 10
        ch.legend = None
        ch.height, ch.width = 6, 12
        data = Reference(ws, min_col=5, max_col=11, min_row=row, max_row=row)
        cats = Reference(ws, min_col=5, max_col=11, min_row=DT + 1, max_row=DT + 1)
        ch.add_data(data, from_rows=True, titles_from_data=False)
        ch.set_categories(cats)
        s = ch.series[0]
        s.graphicalProperties.solidFill = color
        s.graphicalProperties.line.solidFill = color
        ch.y_axis.scaling.min = 0
        ch.y_axis.scaling.max = ymax
        ch.y_axis.majorGridlines = None
        ch.y_axis.number_format = "0%" if pct else "0"
        ch.y_axis.delete = False
        ch.x_axis.delete = False
        ch.gapWidth = 60
        place_chart(ws, ch, c1, CH + 1, c2, CH + CH_H)

    def fill_week(self, ws, n):
        w = SD.week(n)
        ws["D13"] = w["goal"]
        for i, (mark, txt) in enumerate(w["priorities"]):
            ws[f"B{15 + i}"] = mark
            ws[f"C{15 + i}"] = txt
        for d, day in enumerate(w["days"]):
            r0 = DAY_ROW[d]
            for i, (mark, txt) in enumerate(day["priorities"]):
                ws[f"B{r0 + 2 + i}"] = mark
                ws[f"C{r0 + 2 + i}"] = txt
            for i, (tm, txt) in enumerate(day["appts"][:3]):
                hh, mm = map(int, tm.split(":"))
                ws[f"B{r0 + 6 + i}"] = dt.time(hh, mm)
                ws[f"C{r0 + 6 + i}"] = txt
            if day["note"]:
                ws[f"B{r0 + 10}"] = day["note"]
            for i, (t, cat, pr, st) in enumerate(day["tasks"][:BODY]):
                rr = r0 + 2 + i
                ws[f"E{rr}"], ws[f"G{rr}"], ws[f"H{rr}"], ws[f"I{rr}"] = t, cat, pr, st
            for s, txt in day["schedule"].items():
                ws[f"K{r0 + 2 + s}"] = txt
        for i, row in enumerate(w["habits"]):
            for d, v in enumerate(row):
                ws[f"{DAYCOLS[d]}{HT + 2 + i}"] = v
        for d in range(7):
            c = DAYCOLS[d]
            ws[f"{c}{R_WATER}"] = w["water"][d]
            ws[f"{c}{R_EXT}"] = w["ex_type"][d]
            ws[f"{c}{R_EXM}"] = w["ex_min"][d]
            ws[f"{c}{R_SCORE}"] = w["score"][d]
        if w["reflection"]:
            for i, v in enumerate(w["reflection"]):
                ws[f"E{RF + 1 + i}"] = v

    # ============================================================ MONTHLY CALENDAR
    def build_cal(self):
        ws, T, S = self.ws[S_CAL], self.T, S_CAL
        setup_sheet(ws, {**{L(i): 17 for i in range(2, 9)}, "I": 25, "J": 3, "K": 28, "L": 11})
        title_bar(ws, T, "MONTHLY CALENDAR", "Pick a year and month. Important dates (★), deadlines (⚑), tasks from your week tabs (☑) "
                  "and each week's goal appear automatically.", 12, home_link=S_SETUP, home_label="⌂ Setup", demo=self.demo)
        ws.row_dimensions[4].height = 12
        for c, lab in (("B5", "YEAR"), ("D5", "MONTH"), ("F5", "TODAY")):
            self.label(ws, c, lab, 9, True, SECONDARY, RIGHT)
        ws["C5"] = f"=YEAR({TODAY})"
        ws["E5"] = f"=INDEX({SL('J')},MONTH({TODAY}))"
        self.inp(S, "C5", "0", CENTER)
        self.inp(S, "E5", None, CENTER)
        add_list_dv(ws, "C5", SL("L"))
        add_list_dv(ws, "E5", SL("J"))
        ws["G5"] = "=$Q$9"
        self.calc(S, "G5", FMT_DATE, CENTER)
        self.merge(ws, "H5:I5", '=HYPERLINK("#\'Monthly Calendar\'!B41","Add dates & deadlines ↓")')
        ws["H5"].font = T.font(9, True, BLUE)
        ws["H5"].alignment = Alignment(horizontal="right", vertical="center", indent=1)
        ws.row_dimensions[5].height = 26
        ws.row_dimensions[6].height = 10
        # hidden helpers
        hp = {5: f'=IFERROR(MATCH(E5,{SL("J")},0),MONTH($Q$9))', 6: "=DATE(C5,Q5,1)",
              7: f'=Q6-MOD(WEEKDAY(Q6)-IF({WEEKSTART}="Sunday",1,2),7)', 8: f"={DONE}", 9: f"={TODAY}"}
        for r, fm in hp.items():
            ws[f"Q{r}"] = fm
            ws[f"P{r}"] = {5: "month #", 6: "first of month", 7: "grid start", 8: "done status", 9: "today"}[r]
            ws[f"Q{r}"].number_format = FMT_DATE if r in (6, 7, 9) else "General"
        for i, w in enumerate(WEEKS):
            r = 5 + i
            ws[f"T{r}"] = i + 1
            ws[f"U{r}"] = f"={qs(w)}!$N$3"
            ws[f"V{r}"] = f'={qs(w)}!$D$13&""'
            ws[f"W{r}"] = f"={qs(w)}!$N$4"
        for c in "MNOPQRSTUVWX":
            ws.column_dimensions[c].hidden = True
        # banner + headers
        self.merge(ws, "B7:H7", "=Q6")
        ws["B7"].number_format = "mmmm yyyy"
        ws["B7"].font = T.font(16, True, NAVY)
        ws["B7"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[7].height = 30
        for d in range(7):
            c = L(2 + d)
            ws[f"{c}8"] = f"=Q7+{d}"
            ws[f"{c}8"].number_format = "dddd"
            paint(ws, f"{c}8", f=FILL_NAVY, font=T.font(10, True, WHITE), align=CENTER)
        ws["I8"] = "Week goal"
        paint(ws, "I8", f=fill(LAVENDER), font=T.font(10, True, WHITE), align=CENTER)
        ws.row_dimensions[8].height = 22
        wk_tab = lambda w, rng_: f"{qs(w)}!${rng_[0]}${TASK_R1}:${rng_[0]}${TASK_RN}"
        for wrow in range(6):
            base = G0 + wrow * 5
            for d in range(7):
                c = L(2 + d)
                date = f"{c}{base}"
                ws[date] = f"=$Q$7+{wrow * 7 + d}"
                ws[date].number_format = "d"
                ws[date].font = T.font(11, True, DARK)
                ws[date].alignment = Alignment(horizontal="right", vertical="top", indent=1)
                inm = f"MONTH({date})=$Q$5"
                ws[f"{c}{base + 1}"] = (f'=IF({inm},IFERROR("★ "&INDEX($C${IMP1}:$C${IMPN},MATCH(INT({date})&"|1",$R${IMP1}:$R${IMPN},0)),""),"")')
                ws[f"{c}{base + 2}"] = (f'=IF({inm},IFERROR("⚑ "&INDEX($G${IMP1}:$G${IMPN},MATCH(INT({date})&"|1",$S${IMP1}:$S${IMPN},0)),""),"")')
                cnt = "+".join(f"COUNTIF({wk_tab(w, 'N')},{date})" for w in WEEKS)
                dn = "+".join(f"COUNTIFS({wk_tab(w, 'N')},{date},{wk_tab(w, 'I')},$Q$8)" for w in WEEKS)
                ws[f"{c}{base + 3}"] = f'=IF({inm},IF(({cnt})=0,"","☑ "&({dn})&"/"&({cnt})&" tasks done"),"")'
                more = f"MAX(0,COUNTIF($B${IMP1}:$B${IMPN},{date})-1)+MAX(0,COUNTIF($F${IMP1}:$F${IMPN},{date})-1)"
                ws[f"{c}{base + 4}"] = f'=IF(AND({inm},{more}>0),"+"&({more})&" more","")'
                fonts = {1: T.font(9, True, "B26B00"), 2: T.font(9, True, LAVENDER), 3: T.font(9, False, TEAL), 4: T.font(8, False, SECONDARY)}
                for k in range(1, 5):
                    cell = ws[f"{c}{base + k}"]
                    cell.font = fonts[k]
                    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
                for k in range(5):
                    cell = ws[f"{c}{base + k}"]
                    cell.fill = FILL_WHITE
                    cell.border = Border(left=THIN, right=THIN, top=THIN if k == 0 else None, bottom=THIN if k == 4 else None)
            ws.row_dimensions[base].height = 18
            for k in range(1, 5):
                ws.row_dimensions[base + k].height = 16
            # week goal column
            idx = f"SUMPRODUCT(MAX(($U$5:$U$10>=B{base})*($U$5:$U$10<=B{base}+6)*$T$5:$T$10))"
            self.merge(ws, f"I{base}:I{base + 4}",
                       f'=IF({idx}=0,"",INDEX($V$5:$V$10,{idx})&CHAR(10)&"— Week "&{idx}&IF(INDEX($W$5:$W$10,{idx})="",""," · "&TEXT(INDEX($W$5:$W$10,{idx}),"0%")&" done"))')
            paint(ws, f"I{base}:I{base + 4}", f=fill(SOFT_LAV), font=T.font(9, True, "4B3A8C"),
                  align=Alignment(wrap_text=True, vertical="center", indent=1),
                  border=Border(left=THIN, right=THIN, top=THIN, bottom=THIN))
            cf_formula(ws, f"B{base}:H{base}", f"B{base}=$Q$9", BLUE, WHITE, True, stop=True)
            cf_formula(ws, f"B{base}:H{base}", f"MONTH(B{base})<>$Q$5", BG, MED_GRAY, stop=True)
            cf_formula(ws, f"B{base + 2}:H{base + 2}",
                       f'AND(B{base + 2}<>"",B{base}<$Q$9,COUNTIFS($F${IMP1}:$F${IMPN},B{base},$J${IMP1}:$J${IMPN},"<>"&$Q$8)>0)',
                       DANGER_BG, DANGER, True)
            cf_formula(ws, f"B{base + 1}:H{base + 4}", f"MONTH(B${base})<>$Q$5", BG)

        # ---- side panel
        section(ws, T, G0, 11, 12, "MONTHLY PRIORITIES", color=LAVENDER)
        for k in range(3):
            r = G0 + 1 + k
            self.merge(ws, f"K{r}:L{r}", f'=IF(INDEX(${L(3 + 2 * k)}${MP1}:${L(3 + 2 * k)}${MP1 + 11},$Q$5)="",'
                                         f'{chr(34) + ("Add priorities in the table below ↓" if k == 0 else "") + chr(34)},'
                                         f'"{k + 1}.  "&INDEX(${L(3 + 2 * k)}${MP1}:${L(3 + 2 * k)}${MP1 + 11},$Q$5))')
            paint(ws, f"K{r}:L{r}", f=FILL_WHITE, font=T.font(10, True, NAVY), border=_C.CELL_BOX,
                  align=Alignment(vertical="center", indent=1, wrap_text=True))
            ws.row_dimensions[r].height = 16
        section(ws, T, G0 + 5, 11, 12, "THIS MONTH")
        nxt = "EDATE($Q$6,1)"
        tasks = "+".join(f'COUNTIFS({wk_tab(w, "N")},">="&$Q$6,{wk_tab(w, "N")},"<"&{nxt})' for w in WEEKS)
        tdone = "+".join(f'COUNTIFS({wk_tab(w, "N")},">="&$Q$6,{wk_tab(w, "N")},"<"&{nxt},{wk_tab(w, "I")},$Q$8)' for w in WEEKS)
        dl = f'$F${IMP1}:$F${IMPN},">="&$Q$6,$F${IMP1}:$F${IMPN},"<"&{nxt}'
        stats = [("Important dates", f'=COUNTIFS($B${IMP1}:$B${IMPN},">="&$Q$6,$B${IMP1}:$B${IMPN},"<"&{nxt})', "0"),
                 ("Deadlines", f"=COUNTIFS({dl})", "0"),
                 ("Deadlines done", f"=COUNTIFS({dl},$J${IMP1}:$J${IMPN},$Q$8)", "0"),
                 ("Overdue deadlines", f'=COUNTIFS({dl},$J${IMP1}:$J${IMPN},"<>"&$Q$8,$F${IMP1}:$F${IMPN},"<"&$Q$9)', "0"),
                 ("Tasks planned (week tabs)", f"={tasks}", "0"),
                 ("Tasks done", f"={tdone}", "0"),
                 ("Task completion", f'=IF(L{G0 + 10}=0,"—",L{G0 + 11}/L{G0 + 10})', FMT_PCT)]
        for i, (lab, fm, nf) in enumerate(stats):
            r = G0 + 6 + i
            self.label(ws, f"K{r}", lab, 10, False)
            ws[f"K{r}"].border = _C.CELL_BOX
            ws[f"L{r}"] = fm
            self.calc(S, f"L{r}", nf, CENTER, color=BLUE)
            ws.row_dimensions[r].height = 18
        cf_formula(ws, f"L{G0 + 9}", f"L{G0 + 9}>0", DANGER_BG, DANGER, True)
        section(ws, T, G0 + 14, 11, 12, "LEGEND", color=LAVENDER)
        leg = [(BLUE, "Today", WHITE), (BG, "Other month", MED_GRAY), (WHITE, "★ Important date", "B26B00"),
               (WHITE, "⚑ Deadline", LAVENDER), (DANGER_BG, "⚑ Overdue deadline", DANGER), (WHITE, "☑ Tasks from week tabs", TEAL),
               (SOFT_LAV, "Week goal (from week tab)", "4B3A8C")]
        for i, (colr, t, fc) in enumerate(leg):
            r = G0 + 15 + i
            ws[f"K{r}"] = t
            ws[f"K{r}"].font = T.font(9, True, fc)
            ws[f"K{r}"].fill = fill(colr)
            ws[f"K{r}"].border = _C.CELL_BOX
            ws[f"K{r}"].alignment = Alignment(vertical="center", indent=1)
            ws.row_dimensions[r].height = 18
        ws.merge_cells(f"L{G0 + 15}:L{G0 + 21}")
        # ---- tables
        ws.row_dimensions[39].height = 12
        ws.row_dimensions[40].height = 12
        section(ws, T, 41, 2, 5, "IMPORTANT DATES  —  birthdays, holidays, events")
        section(ws, T, 41, 6, 12, "TASK DEADLINES", color=LAVENDER)
        self.subhead(ws, "B42", "Date", align=CENTER)
        self.subhead(ws, "C42:D42", "Event")
        self.subhead(ws, "E42", "Category", align=CENTER)
        self.subhead(ws, "F42", "Deadline", align=CENTER)
        self.subhead(ws, "G42:H42", "Task")
        self.subhead(ws, "I42", "Priority", align=CENTER)
        self.subhead(ws, "J42:K42", "Status", align=CENTER)
        self.subhead(ws, "L42", "Due", align=CENTER)
        for r in range(IMP1, IMPN + 1):
            self.inp(S, f"B{r}", FMT_SDATE, CENTER)
            self.merge(ws, f"C{r}:D{r}")
            self.inp(S, f"C{r}:D{r}")
            self.inp(S, f"E{r}", align=CENTER)
            self.inp(S, f"F{r}", FMT_SDATE, CENTER)
            self.merge(ws, f"G{r}:H{r}")
            self.inp(S, f"G{r}:H{r}")
            self.inp(S, f"I{r}", align=CENTER)
            self.merge(ws, f"J{r}:K{r}")
            self.inp(S, f"J{r}:K{r}", align=CENTER)
            ws[f"L{r}"] = (f'=IF(F{r}="","",IF(J{r}=$Q$8,"✓ Done",IF(F{r}<$Q$9,"Late "&($Q$9-F{r})&"d",'
                           f'IF(F{r}=$Q$9,"Today","In "&(F{r}-$Q$9)&"d"))))')
            self.calc(S, f"L{r}", None, CENTER)
            ws[f"R{r}"] = f'=IF(B{r}="","",INT(B{r})&"|"&COUNTIF($B${IMP1}:B{r},B{r}))'
            ws[f"S{r}"] = f'=IF(OR(F{r}="",G{r}=""),"",INT(F{r})&"|"&COUNTIF($F${IMP1}:F{r},F{r}))'
            ws.row_dimensions[r].height = 18
        add_dv(ws, f"B{IMP1}:B{IMPN}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date.")
        add_dv(ws, f"F{IMP1}:F{IMPN}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date.")
        add_list_dv(ws, f"E{IMP1}:E{IMPN}", SL("B"))
        add_list_dv(ws, f"I{IMP1}:I{IMPN}", SL("C"))
        add_list_dv(ws, f"J{IMP1}:J{IMPN}", SL("E"))
        cf_formula(ws, f"L{IMP1}:L{IMPN}", f'LEFT(L{IMP1},4)="Late"', DANGER_BG, DANGER, True)
        cf_formula(ws, f"L{IMP1}:L{IMPN}", f'L{IMP1}="✓ Done"', SOFT_TEAL, TEAL, True)
        cf_formula(ws, f"L{IMP1}:L{IMPN}", f'L{IMP1}="Today"', WARNING_BG, WARNING, True)
        # monthly priorities table
        ws.row_dimensions[IMPN + 1].height = 12
        ws.row_dimensions[IMPN + 2].height = 12
        section(ws, T, MP1 - 2, 2, 12, "MONTHLY PRIORITIES  —  three per month; the calendar shows the selected month's", color=LAVENDER)
        self.subhead(ws, f"B{MP1 - 1}", "Month", align=CENTER)
        for k, c in enumerate(("C", "E", "G")):
            self.subhead(ws, f"{c}{MP1 - 1}:{L(ord(c) - 63)}{MP1 - 1}", f"Priority {k + 1}")
        self.subhead(ws, f"I{MP1 - 1}:L{MP1 - 1}", "Notes")
        for i in range(12):
            r = MP1 + i
            ws[f"B{r}"] = f"=INDEX({SL('J')},{i + 1})"
            paint(ws, f"B{r}", f=FILL_WHITE, font=T.font(10, True), border=_C.CELL_BOX, align=LEFT)
            for c in ("C", "E", "G"):
                a = f"{c}{r}:{L(ord(c) - 63)}{r}"
                self.merge(ws, a)
                self.inp(S, a)
            self.merge(ws, f"I{r}:L{r}")
            paint(ws, f"I{r}:L{r}", f=FILL_OPT, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
            self.unlocked[S].append(f"I{r}:L{r}")
            ws.row_dimensions[r].height = 19
        cf_formula(ws, f"B{MP1}:B{MP1 + 11}", f"ROW(B{MP1})-{MP1 - 1}=$Q$5", SOFT_TEAL, TEAL, True)
        ws.freeze_panes = "A4"
        skin(ws, 12, MP1 + 12, cards=[(2, 5, 9, 5), (2, 7, 9, 38), (11, G0, 12, G0 + 3), (11, G0 + 5, 12, G0 + 12),
                                        (11, G0 + 14, 12, G0 + 21), (2, 41, 5, IMPN), (6, 41, 12, IMPN),
                                        (2, MP1 - 2, 12, MP1 + 11)], hide_headers=True)
        if self.demo:
            for i, (d, ev, cat) in enumerate(SD.IMPORTANT):
                r = IMP1 + i
                ws[f"B{r}"], ws[f"C{r}"], ws[f"E{r}"] = d, ev, cat
            for i, (t, d, pr, st) in enumerate(SD.DEADLINES):
                r = IMP1 + i
                ws[f"F{r}"], ws[f"G{r}"], ws[f"I{r}"], ws[f"J{r}"] = d, t, pr, st
            for m, items in SD.MONTH_PRIORITIES.items():
                for k, t in enumerate(items):
                    ws[f"{('C', 'E', 'G')[k]}{MP1 + m - 1}"] = t

    # ============================================================ finalize
    def add_sidebars(self):
        import io
        import sidebar
        from drawing_inject import Layer, col_px_list, row_px_list
        from openpyxl.drawing.image import Image as XLImage
        from PIL import Image as PILImage
        self.side_layers = {}
        for name in ORDER:
            ws = self.ws[name]
            ws.column_dimensions["A"].width = 9.43
            last = max(ws.max_row, 60)
            fp = ws.freeze_panes
            ws.freeze_panes = "B1" if fp is None else ("B" + fp[1:] if fp.startswith("A") else fp)
            if self.ed == "excel":
                if not ws._charts and not ws._images:
                    buf = io.BytesIO()
                    PILImage.new("RGBA", (1, 1), (0, 0, 0, 0)).save(buf, "PNG")
                    img = XLImage(io.BytesIO(buf.getvalue()))
                    img.width = img.height = 1
                    ws.add_image(img, "A1")
                lay = Layer(col_px_list(ws, 2), row_px_list(ws, last + 1), font=self.T.font_name)
                sidebar.draw(lay, name, lay.y(last + 1), nav=NAV)
                self.side_layers[name] = lay
            else:
                sidebar.cells(ws, self.T, quote, name, last, nav=NAV)

    def protect(self):
        if self.ed != "excel":
            return
        for name in ORDER:
            ws = self.ws[name]
            for rng_ in self.unlocked[name]:
                for c in _cells(ws, rng_):
                    c.protection = Protection(locked=False)
            ws.protection.sheet = True
            ws.protection.objects = True
            ws.protection.formatColumns = False
            ws.protection.formatRows = False
            ws.protection.formatCells = False

    def page_setup(self):
        areas = {S_SETUP: f"A1:L{48}", S_CAL: f"A1:L{MP1 + 11}", **{w: f"A1:L{LAST_W}" for w in WEEKS}}
        for n in ORDER:
            ws = self.ws[n]
            ws.page_setup.orientation = "portrait" if n in WEEKS else "landscape"
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            ws.print_options.horizontalCentered = True
            ws.page_margins.left = ws.page_margins.right = 0.4
            ws.page_margins.top = ws.page_margins.bottom = 0.5
            ws.print_area = areas[n]

    def build(self):
        self.build_setup()
        for i in range(1, 7):
            self.build_week(i)
        self.build_cal()
        self.add_sidebars()
        self.protect()
        self.page_setup()
        first = WEEKS[1] if self.demo else S_SETUP
        self.wb.active = ORDER.index(first)
        for n in ORDER:
            self.ws[n].sheet_view.tabSelected = (n == first)
        return self.wb


def main():
    from common import solidify_databars
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "dist" / "03_Weekly_Planner_Pro"))
    a = ap.parse_args()
    out = Path(a.out)
    files = []
    for ed, folder, suffix in (("excel", "Excel", "Excel"), ("gsheets", "Google_Sheets", "GoogleSheets")):
        for demo in (True, False):
            b = Builder(ed, demo)
            wb = b.build()
            if ed != "excel":
                _C.nativize_links(wb)
            p = out / folder / f"Weekly_Planner_Pro_{suffix}_{'DEMO' if demo else 'BLANK'}.xlsx"
            p.parent.mkdir(parents=True, exist_ok=True)
            wb.save(p)
            solidify_databars(p)
            for name, lay in getattr(b, "side_layers", {}).items():
                lay.inject(p, name)
            files.append(p)
            print("wrote", p)
    return files


if __name__ == "__main__":
    main()
