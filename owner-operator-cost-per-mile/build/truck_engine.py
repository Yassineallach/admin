"""Brass Ledger: Owner-Operator Cost Per Mile & Load Profit Calculator (openpyxl).

Tabs: START HERE, SETTINGS, LOAD CHECK (PHONE), LOAD COMPARE, TRIP LOG, FUEL LOG, MONTHLY P&L, DASHBOARD.

Every cost, rate and threshold lives on SETTINGS; the other tabs only reference it. Formulas use SUMIFS / COUNTIFS /
SUMPRODUCT / INDEX / MATCH / IFERROR only: no macros, Excel Tables, structured references, LAMBDA, dynamic arrays,
TEXT() codes or cross-sheet conditional formatting, so the file behaves the same in Excel 2016+, Google Sheets and the
Google Sheets phone app.
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, Protection, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.hyperlink import Hyperlink

HERE = Path(__file__).resolve().parent
for p in (HERE / "vendor", HERE.parents[1] / "productivity-bundle" / "build"):
    if p.exists():
        sys.path.insert(0, str(p))
import bl_polish as BP  # noqa: E402

from xlkit import (BOX, BRASS, BRASS_TINT, CALC, GREEN, GREEN2, INK, INK2, Kit, MUTED, NEG, NEG_TINT,  # noqa: E402
                   PAPER, POS, POS_TINT, TITLE, WHITE, fill, font, q)

AMBER, AMBER_TINT = "C77A1A", "F7E6CC"
MONEY = '"$"#,##0.00;-"$"#,##0.00'
MONEY0 = '"$"#,##0;-"$"#,##0'
CPM = '"$"0.000;-"$"0.000'
MILES = "#,##0"
MILES_Z = "#,##0;-#,##0;"            # zero shows as blank
MONEY_Z = '"$"#,##0.00;-"$"#,##0.00;'
MONEY0_Z = '"$"#,##0;-"$"#,##0;'
CPM_Z = '"$"0.000;-"$"0.000;'
PCT_Z = "0.0%;-0.0%;"
MPG = "0.0"
PCT = "0.0%"
DATE = "mmm d, yyyy"
GAL = "#,##0.0"

S_START, S_SET, S_CHECK, S_CMP, S_TRIP, S_FUEL, S_PNL, S_DASH = (
    "START HERE", "SETTINGS", "LOAD CHECK (PHONE)", "LOAD COMPARE", "TRIP LOG", "FUEL LOG", "MONTHLY P&L", "DASHBOARD")
ORDER = [S_START, S_SET, S_CHECK, S_CMP, S_TRIP, S_FUEL, S_PNL, S_DASH]
NAV = [(S_DASH, "bar_chart", "Home"), (S_START, "question", "Start"), (S_SET, "gear", "Setup"),
       (S_CHECK, "calc", "Check"), (S_CMP, "scale", "Compare"), (S_TRIP, "clipboard", "Trips"),
       (S_FUEL, "pin", "Fuel"), (S_PNL, "calendar", "P&L")]

TRIP_FIRST, TRIP_N = 8, 500
TRIP_LAST = TRIP_FIRST + TRIP_N - 1
FUEL_FIRST, FUEL_N = 8, 300
FUEL_LAST = FUEL_FIRST + FUEL_N - 1
SM_FIRST, SM_N = 8, 600                      # miles by state per trip
SM_LAST = SM_FIRST + SM_N - 1
AWAY_N = 60
CMP_N = 5

# load model inputs (key, label, format, kind) shared by the phone check and the compare tab
LOAD_MAIN = [("rate", "Total rate offered ($)", MONEY, "money"), ("loaded", "Loaded miles", MILES, "miles"),
             ("dh", "Deadhead miles to pickup", MILES, "miles"), ("days", "Days the load will take", "General", "days")]
LOAD_MORE = [("fuel", "Fuel $/gal on the route (blank = Settings)", MONEY, "money"),
             ("tolls", "Tolls ($)", MONEY, "money"),
             ("lumper", "Lumper ($)", MONEY, "money"),
             ("lumper_r", "Lumper reimbursed? (Y/N)", None, "yn"),
             ("stopcost", "Scales, washes, parking, other costs ($)", MONEY, "money"),
             ("stoppay", "Extra stop pay ($)", MONEY, "money"),
             ("det", "Detention pay expected ($)", MONEY, "money"),
             ("rhrs", "Reefer run hours (blank = days x Settings)", "0.0", "days"),
             ("fact", "Factoring % (blank = Settings)", PCT, "pct"),
             ("disp", "Dispatch fee % (blank = Settings)", PCT, "pct")]


class TruckEngine(Kit):
    def __init__(self, cfg, sample: bool):
        self.cfg = cfg
        self.product = cfg.PRODUCT
        self.sample = sample
        self.home_tab, self.start_tab = S_DASH, S_START
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in ORDER}
        self.S = {}           # settings key -> 'SETTINGS'!$X$n
        self.rows = {}        # anchors for screenshots and tests
        self.cells = {}       # other anchors (load check outputs etc.)

    # ------------------------------------------------------------ helpers
    def dv_list(self, ws, rng, source, title="Pick from the list"):
        v = DataValidation(type="list", formula1=source, allow_blank=True, showErrorMessage=True, errorTitle=title,
                           error="Pick a value from the dropdown list.")
        ws.add_data_validation(v)
        v.add(rng)

    def dv_num(self, ws, rng, lo=0, hi=1e9, msg="Enter a number of 0 or more."):
        v = DataValidation(type="decimal", operator="between", formula1=str(lo), formula2=str(hi), allow_blank=True,
                           showErrorMessage=True, errorTitle="Number", error=msg)
        ws.add_data_validation(v)
        v.add(rng)

    def dv_date(self, ws, rng):
        v = DataValidation(type="date", operator="between", formula1="36526", formula2="73051", allow_blank=True,
                           showErrorMessage=True, errorTitle="Date", error="Enter a date, e.g. 9/1/2026.")
        ws.add_data_validation(v)
        v.add(rng)

    def sset(self, key, ws, cell):
        self.S[key] = f"{q(ws.title)}!${cell.column_letter}${cell.row}"

    def head(self, ws, r, cols, height=30):
        for col, t in cols:
            self.header(ws[f"{col}{r}"], t, align="left" if col == "B" else "center")
        ws.row_dimensions[r].height = height

    def lbl(self, ws, cell, text, bold=True, color=INK, size=10, wrap=False):
        self.label(ws[cell], text, bold=bold, color=color, size=size, wrap=wrap)

    # ============================================================ SETTINGS
    def build_settings(self):
        c, ws, S = self.cfg, self.ws[S_SET], self.S
        D = c.SET
        widths = {"B": 45, "C": 15, "D": 15, "E": 15, "F": 15, "G": 15, "H": 19}
        self.page(ws, widths, 8, 140, "Settings", "Your costs, pay and targets. Every other tab uses these numbers.")
        self.note(ws, "B4:H4", "EXAMPLE VALUES, REPLACE WITH YOUR OWN NUMBERS.  The figures below are typical 2025-26 "
                  "industry numbers for a dry van owner-operator with their own authority (sources in the guide). They are "
                  "not your costs: type your own in the white cells.", tint=AMBER_TINT, height=44, size=9.5, color=INK, bold=True)
        # ---------------------------------------------------- business
        self.kicker(ws, "B6", "Your business", rule_to=8)
        self.lbl(ws, "B7", "Business name")
        ws.merge_cells("C7:E7")
        self.inp(ws["C7"], value=c.SAMPLE_NAME if self.sample else None)
        self.lbl(ws, "F7", "Year")
        self.inp(ws["G7"], "0", align="center", value=D["year"])
        self.sset("name", ws, ws["C7"])
        self.sset("year", ws, ws["G7"])
        self.lbl(ws, "B8", "Equipment type")
        ws.merge_cells("C8:E8")
        self.inp(ws["C8"], value=D["equipment"])
        self.sset("equip", ws, ws["C8"])
        self.lbl(ws, "F8", "Diesel $/gal")
        self.inp(ws["G8"], MONEY, value=D["fuel_price"])
        self.sset("fuel_price", ws, ws["G8"])
        self.dv_num(ws, "G7", 2000, 2100, "Enter a year, e.g. 2026.")
        self.dv_num(ws, "G8")
        ws.row_dimensions[7].height = ws.row_dimensions[8].height = 22

        # ---------------------------------------------------- inputs start below the summary
        r = 33
        rows = {}
        # presets
        rows["presets"] = r
        self.kicker(ws, f"B{r}", "Equipment presets  ·  the type you pick above fills in the variable costs", rule_to=8)
        r += 1
        self.head(ws, r, [("B", "Equipment"), ("C", "MPG"), ("D", "Maint. & repair $/mi"), ("E", "Tire set cost"),
                          ("F", "Tire life (miles)"), ("G", "DEF $/mi"), ("H", "Reefer fuel gal/hour")], 32)
        p1 = r + 1
        for i, pr in enumerate(c.PRESETS):
            rr = p1 + i
            self.calc(ws[f"B{rr}"], value=pr[0], bold=True)
            for j, (col, fmt) in enumerate(zip("CDEFGH", [MPG, CPM, MONEY0, MILES, CPM, "0.00"])):
                self.inp(ws[f"{col}{rr}"], fmt, value=pr[1 + j])
            self.dv_num(ws, f"C{rr}:H{rr}")
        p2 = p1 + len(c.PRESETS) - 1
        S["preset_names"] = f"{q(S_SET)}!$B${p1}:$B${p2}"
        self.dv_list(ws, "C8", S["preset_names"])
        rows["presets_end"] = p2
        r = p2 + 2
        # variable costs
        rows["var"] = r
        self.kicker(ws, f"B{r}", "Variable costs  ·  from the preset unless you type your own value", rule_to=8)
        r += 1
        self.head(ws, r, [("B", "Item"), ("C", "From preset"), ("D", "Your value (optional)"), ("E", "Used"), ("F", "Note")])
        ws.merge_cells(f"F{r}:H{r}")
        v1 = r + 1
        var_items = [("mpg", "Miles per gallon (MPG)", MPG, "C", ""),
                     ("maint", "Maintenance and repair reserve ($/mile)", CPM, "D", "Set aside every mile for repairs"),
                     ("tire_set", "Tire set cost ($)", MONEY0, "E", "All tires on the truck (and trailer if yours)"),
                     ("tire_life", "Expected tire life (miles)", MILES, "F", ""),
                     ("def", "DEF ($/mile)", CPM, "G", "Diesel exhaust fluid"),
                     ("gph", "Reefer fuel (gal/hour)", "0.00", "H", "Reefer only; 0 for other types")]
        for i, (key, text, fmt, col, note) in enumerate(var_items):
            rr = v1 + i
            self.lbl(ws, f"B{rr}", text, bold=False)
            self.calc(ws[f"C{rr}"], fmt, value=f"=IFERROR(INDEX($"+col+f"${p1}:${col}${p2},MATCH({S['equip']},{S['preset_names']},0)),0)")
            self.inp(ws[f"D{rr}"], fmt)
            self.calc(ws[f"E{rr}"], fmt, bold=True, value=f'=IF(D{rr}="",C{rr},D{rr})')
            self.dv_num(ws, f"D{rr}")
            ws.merge_cells(f"F{rr}:H{rr}")
            self.label(ws[f"F{rr}"], note, bold=False, color=INK2, size=9)
            self.sset(key, ws, ws[f"E{rr}"])
        rr = v1 + len(var_items)
        for key, text, fmt, val, note in [
                ("rhd", "Reefer run hours per load day", "0.0", D["reefer_hours_day"], "Used for reefer fuel; ignored if gal/hour is 0"),
                ("ldw", "Days with a load per week", "0.0", D["load_days_week"], "For reefer fuel per mile"),
                ("other_var", "Other variable cost ($/mile)", CPM, D["other_var"], "Anything else you spend per mile")]:
            self.lbl(ws, f"B{rr}", text, bold=False)
            ws[f"C{rr}"].fill = fill(CALC)
            ws[f"C{rr}"].border = BOX
            self.inp(ws[f"D{rr}"], fmt, value=val)
            self.calc(ws[f"E{rr}"], fmt, bold=True, value=f"=N(D{rr})")
            self.dv_num(ws, f"D{rr}")
            ws.merge_cells(f"F{rr}:H{rr}")
            self.label(ws[f"F{rr}"], note, bold=False, color=INK2, size=9)
            self.sset(key, ws, ws[f"E{rr}"])
            rr += 1
        rows["var_end"] = rr - 1
        r = rr + 1
        # fixed costs
        rows["fixed"] = r
        self.kicker(ws, f"B{r}", "Fixed costs  ·  you pay these whether the truck moves or not", rule_to=8)
        r += 1
        self.head(ws, r, [("B", "Item"), ("C", "Amount ($)"), ("D", "Per"), ("E", "Per month"), ("F", "Note")])
        ws.merge_cells(f"F{r}:H{r}")
        f1 = r + 1
        for i, (text, amt, per, note) in enumerate(c.FIXED):
            rr = f1 + i
            self.inp(ws[f"B{rr}"], value=text)
            self.inp(ws[f"C{rr}"], MONEY, value=amt)
            self.inp(ws[f"D{rr}"], align="center", value=per)
            self.calc(ws[f"E{rr}"], MONEY, value=f'=IF(D{rr}="Year",N(C{rr})/12,N(C{rr}))')
            ws.merge_cells(f"F{rr}:H{rr}")
            self.label(ws[f"F{rr}"], note, bold=False, color=INK2, size=9)
        f2 = f1 + len(c.FIXED) + 1                 # two spare rows for the user's own items
        for rr in range(f1 + len(c.FIXED), f2 + 1):
            self.inp(ws[f"B{rr}"])
            self.inp(ws[f"C{rr}"], MONEY)
            self.inp(ws[f"D{rr}"], align="center", value="Month")
            self.calc(ws[f"E{rr}"], MONEY, value=f'=IF(D{rr}="Year",N(C{rr})/12,N(C{rr}))')
            ws.merge_cells(f"F{rr}:H{rr}")
        self.dv_list(ws, f"D{f1}:D{f2}", '"Month,Year"')
        self.dv_num(ws, f"C{f1}:C{f2}")
        rt = f2 + 1
        self.lbl(ws, f"B{rt}", "Fixed costs per month", color=GREEN)
        self.calc(ws[f"E{rt}"], MONEY, bold=True, value=f"=SUM(E{f1}:E{f2})")
        self.sset("fixed_month", ws, ws[f"E{rt}"])
        rows["fixed_end"] = rt
        r = rt + 2
        # pay and miles
        rows["pay"] = r
        self.kicker(ws, f"B{r}", "Your pay and your miles", rule_to=8)
        r += 1
        for key, text, fmt, val, note in [
                ("weekly_pay", "Your target take-home pay per week ($)", MONEY, D["weekly_pay"], "What you want to pay yourself"),
                ("weekly_miles", "Expected miles per week (loaded + deadhead)", MILES, D["weekly_miles"], "In a normal working week"),
                ("weeks", "Weeks you work per year", "0", D["weeks_year"], "Leave out home time and shop weeks")]:
            self.lbl(ws, f"B{r}", text, bold=False)
            self.inp(ws[f"C{r}"], fmt, value=val)
            self.dv_num(ws, f"C{r}")
            ws.merge_cells(f"D{r}:H{r}")
            self.label(ws[f"D{r}"], note, bold=False, color=INK2, size=9)
            self.sset(key, ws, ws[f"C{r}"])
            r += 1
        self.lbl(ws, f"B{r}", "Expected miles per month", color=GREEN)
        self.calc(ws[f"C{r}"], MILES, bold=True, value=f"=N({S['weekly_miles']})*N({S['weeks']})/12")
        self.sset("month_miles", ws, ws[f"C{r}"])
        ws.merge_cells(f"D{r}:H{r}")
        self.label(ws[f"D{r}"], "Weekly miles x weeks worked / 12", bold=False, color=INK2, size=9)
        r += 1
        self.lbl(ws, f"B{r}", "Your pay per mile", color=GREEN)
        self.calc(ws[f"C{r}"], CPM, bold=True, value=f"=IFERROR(N({S['weekly_pay']})*52/(N({S['weekly_miles']})*N({S['weeks']})),0)")
        self.sset("paypm", ws, ws[f"C{r}"])
        ws.merge_cells(f"D{r}:H{r}")
        self.label(ws[f"D{r}"], "52 weeks of pay spread over the miles you run in the weeks you work", bold=False, color=INK2, size=9)
        r += 2
        # targets, fees, verdict
        rows["targets"] = r
        self.kicker(ws, f"B{r}", "Targets, fees and the load verdict", rule_to=8)
        r += 1
        for key, text, fmt, val, note in [
                ("margin", "Target profit margin", PCT, D["margin"], "Profit after your pay, as a share of the load's revenue"),
                ("fact", "Factoring fee", PCT, D["factoring"], "0 % if you don't factor"),
                ("disp", "Dispatch fee", PCT, D["dispatch"], "0 % if you book your own loads")]:
            self.lbl(ws, f"B{r}", text, bold=False)
            self.inp(ws[f"C{r}"], fmt, value=val)
            self.dv_num(ws, f"C{r}", 0, 0.9, "Enter a percentage from 0 % to 90 %.")
            ws.merge_cells(f"D{r}:H{r}")
            self.label(ws[f"D{r}"], note, bold=False, color=INK2, size=9)
            self.sset(key, ws, ws[f"C{r}"])
            r += 1
        for key, text, val, note in [("v1", "Verdict word: meets your target", D["verdicts"][0], "Shown when the load meets your target margin"),
                                     ("v2", "Verdict word: in between", D["verdicts"][1], "Covers the break-even line but not your target"),
                                     ("v3", "Verdict word: below break-even", D["verdicts"][2], "Does not cover the break-even line")]:
            self.lbl(ws, f"B{r}", text, bold=False)
            self.inp(ws[f"C{r}"], align="center", value=val)
            ws.merge_cells(f"D{r}:H{r}")
            self.label(ws[f"D{r}"], note, bold=False, color=INK2, size=9)
            self.sset(key, ws, ws[f"C{r}"])
            r += 1
        self.lbl(ws, f"B{r}", "Break-even line: the load must cover", bold=False)
        ws.merge_cells(f"C{r}:D{r}")
        self.inp(ws[f"C{r}"], value=D["pass_basis"])
        self.dv_list(ws, f"C{r}", '"' + ",".join(c.PASS_BASIS) + '"')
        ws.merge_cells(f"E{r}:H{r}")
        self.label(ws[f"E{r}"], "Operating costs = everything except your pay", bold=False, color=INK2, size=9)
        self.sset("basis", ws, ws[f"C{r}"])
        r += 1
        self.lbl(ws, f"B{r}", "Minimum profit per day for the top verdict ($)", bold=False)
        self.inp(ws[f"C{r}"], MONEY, value=D["min_ppd"])
        self.dv_num(ws, f"C{r}")
        ws.merge_cells(f"D{r}:H{r}")
        self.label(ws[f"D{r}"], "Optional. Blank = no minimum", bold=False, color=INK2, size=9)
        self.sset("min_ppd", ws, ws[f"C{r}"])
        rows["targets_end"] = r
        r += 2
        self.note(ws, f"B{r}:H{r}", c.DISCLAIMER, height=30, size=9, color=INK, bold=True)
        rows["end"] = r
        # lists (states / provinces), far right, out of the way
        ws.column_dimensions["K"].width = 6
        for i, st in enumerate(c.STATES):
            ws[f"K{51 + i}"] = st
            ws[f"K{51 + i}"].font = font(8, color=MUTED)
        ws["K50"].value = "Lists"
        ws["K50"].font = font(8, True, MUTED)
        S["states"] = f"{q(S_SET)}!$K$51:$K${50 + len(c.STATES)}"

        # ---------------------------------------------------- summary (rows 10-31)
        self.summary(ws, rows)
        self.rows["set"] = rows
        self.rows["set_last"] = r
        ws.freeze_panes = "A4"
        ws.print_area = f"A1:H{r}"
        self.protect(ws)

    def summary(self, ws, rows):
        S = self.S
        self.kicker(ws, "B10", "Your cost per mile  ·  calculated from the white cells below", rule_to=8)
        # per-mile parts
        parts = {
            "fuel_pm": f"=IFERROR({S['fuel_price']}/{S['mpg']},0)",
            "def_pm": f"={S['def']}",
            "maint_pm": f"={S['maint']}",
            "tire_pm": f"=IFERROR({S['tire_set']}/{S['tire_life']},0)",
            "reefer_pm": f"=IFERROR({S['gph']}*{S['rhd']}*{S['ldw']}*{S['fuel_price']}/{S['weekly_miles']},0)",
            "other_pm": f"={S['other_var']}",
        }
        r = 15
        self.head(ws, r - 1, [("B", "Cost per mile, part by part"), ("C", "$ per mile"), ("D", "Share")], 26)
        labels = [("fuel_pm", "Fuel (price / MPG)"), ("def_pm", "DEF"), ("maint_pm", "Maintenance and repair reserve"),
                  ("tire_pm", "Tires (set cost / tire life)"), ("reefer_pm", "Reefer fuel"), ("other_pm", "Other variable")]
        for key, text in labels:
            self.lbl(ws, f"B{r}", text, bold=False)
            self.calc(ws[f"C{r}"], CPM, value=parts[key])
            self.sset(key, ws, ws[f"C{r}"])
            r += 1
        tot_rows = []

        def total(key, text, formula, color=GREEN, big=False):
            nonlocal r
            self.lbl(ws, f"B{r}", text, color=color)
            self.calc(ws[f"C{r}"], CPM, bold=True, value=formula)
            ws[f"C{r}"].fill = fill(BRASS_TINT if big else CALC)
            self.sset(key, ws, ws[f"C{r}"])
            tot_rows.append(r)
            r += 1

        total("var_cpm", "Variable cost per mile", f"=SUM(C15:C{r - 1})")
        self.lbl(ws, f"B{r}", "Fixed cost per mile", bold=False)
        self.calc(ws[f"C{r}"], CPM, value=f"=IFERROR({S['fixed_month']}/{S['month_miles']},0)")
        self.sset("fixed_cpm", ws, ws[f"C{r}"])
        r += 1
        total("op_cpm", "Operating cost / mile (break-even)", f"={S['var_cpm']}+{S['fixed_cpm']}", big=True)
        self.lbl(ws, f"B{r}", "Your pay per mile", bold=False)
        self.calc(ws[f"C{r}"], CPM, value=f"={S['paypm']}")
        r += 1
        total("allin_cpm", "All-in cost / mile (incl. your pay)", f"={S['op_cpm']}+{S['paypm']}", big=True)
        self.lbl(ws, f"B{r}", "Fees (factoring + dispatch)", bold=False)
        self.calc(ws[f"C{r}"], PCT, value=f"={S['fact']}+{S['disp']}")
        self.sset("fees_pct", ws, ws[f"C{r}"])
        r += 1
        total("be_rate", "Break-even rate / mile (+ fees)",
              f"=IFERROR({S['op_cpm']}/(1-{S['fees_pct']}),0)")
        total("target_rate", "Target rate / mile (margin + fees)",
              f"=IFERROR({S['allin_cpm']}/(1-{S['margin']}-{S['fees_pct']}),0)", big=True)
        for rr in range(15, r):
            if ws[f"C{rr}"].number_format == CPM:
                ws[f"D{rr}"].value = f"=IFERROR(C{rr}/{S['allin_cpm']},0)"
                self.calc(ws[f"D{rr}"], PCT, align="center")
        for rr in tot_rows[-2:]:
            ws[f"D{rr}"].value = None
        # sensitivity
        self.head(ws, 14, [("E", "Miles a month"), ("F", "Fixed $/mi"), ("G", "All-in $/mi"), ("H", "Target rate $/mi")], 26)
        D = self.cfg.SET
        for i, m in enumerate(D["sens"]):
            rr = 15 + i
            self.inp(ws[f"E{rr}"], MILES, align="center", value=m)
            self.calc(ws[f"F{rr}"], CPM, value=f"=IFERROR({S['fixed_month']}/E{rr},\"\")")
            self.calc(ws[f"G{rr}"], CPM, bold=True,
                      value=f"=IFERROR({S['var_cpm']}+{S['fixed_month']}/E{rr}+N({S['weekly_pay']})*52/12/E{rr},\"\")")
            self.calc(ws[f"H{rr}"], CPM, value=f"=IFERROR(G{rr}/(1-{S['margin']}-{S['fees_pct']}),\"\")")
            self.dv_num(ws, f"E{rr}", 1, 1e7, "Enter miles a month, more than 0.")
        rr = 15 + len(D["sens"])
        self.lbl(ws, f"E{rr}", "Your plan", color=GREEN)
        ws[f"E{rr}"].alignment = Alignment(horizontal="center", vertical="center")
        self.calc(ws[f"F{rr}"], CPM, value=f"={S['fixed_cpm']}")
        self.calc(ws[f"G{rr}"], CPM, bold=True, value=f"={S['allin_cpm']}")
        self.calc(ws[f"H{rr}"], CPM, value=f"={S['target_rate']}")
        rows["sens"] = (15, rr)
        self.note(ws, f"E{rr + 1}:H{rr + 3}", "Fixed costs don't stop when the truck sits. Fewer miles a month means every "
                  "mile has to carry more of the truck payment and insurance, so idle weeks raise your cost per mile.",
                  height=None, size=9)
        ws.row_dimensions[rr + 1].height = 22
        # tiles across the top
        tiles = [("FIXED $/MILE", S["fixed_cpm"], 2, 2), ("VARIABLE $/MILE", S["var_cpm"], 3, 4),
                 ("BREAK-EVEN $/MILE", S["op_cpm"], 5, 6), ("ALL-IN $/MILE", S["allin_cpm"], 7, 7),
                 ("TARGET RATE $/MILE", S["target_rate"], 8, 8)]
        for lab, ref, c1, c2 in tiles:
            self.tile(ws, 11, c1, c2, lab, f"={ref}", CPM, size=18)
        ws.row_dimensions[13].height = 8
        rows["summary_end"] = r - 1
        assert r <= 32, r

    # ============================================================ load model
    def load_formulas(self, I, O):
        """Formulas for one load. I: input key -> cell ref; O: output key -> cell ref. Returns {key: formula}."""
        S = self.S
        g = f"AND(N({I['rate']})>0,N({I['loaded']})>0)"
        fuelp = f"IF(N({I['fuel']})>0,{I['fuel']},{S['fuel_price']})"
        factp = f"IF({I['fact']}=\"\",{S['fact']},{I['fact']})"
        dispp = f"IF({I['disp']}=\"\",{S['disp']},{I['disp']})"
        f = {
            "tot": f"=IF({g},N({I['loaded']})+N({I['dh']}),\"\")",
            "rev": f"=IF({g},N({I['rate']})+N({I['det']})+N({I['stoppay']}),\"\")",
            "fuelc": f"=IF({g},{O['tot']}/{S['mpg']}*{fuelp},\"\")",
            "reefer": f"=IF({g},IF(N({I['rhrs']})>0,{I['rhrs']},N({I['days']})*{S['rhd']})*{S['gph']}*{fuelp},\"\")",
            "permile": f"=IF({g},{O['tot']}*({S['def_pm']}+{S['maint_pm']}+{S['tire_pm']}+{S['other_pm']}),\"\")",
            "trip": f"=IF({g},N({I['tolls']})+IF(UPPER({I['lumper_r']})=\"Y\",0,N({I['lumper']}))+N({I['stopcost']}),\"\")",
            "fixed": f"=IF({g},{O['tot']}*{S['fixed_cpm']},\"\")",
            "feep": f"=IF({g},{factp}+{dispp},\"\")",
            "fees": f"=IF({g},{O['rev']}*{O['feep']},\"\")",
            "opcost": f"=IF({g},{O['fuelc']}+{O['reefer']}+{O['permile']}+{O['trip']}+{O['fixed']}+{O['fees']},\"\")",
            "pay": f"=IF({g},{O['tot']}*{S['paypm']},\"\")",
            "allin": f"=IF({g},{O['opcost']}+{O['pay']},\"\")",
            "profit": f"=IF({g},{O['rev']}-{O['allin']},\"\")",
            "profit_bp": f"=IF({g},{O['rev']}-{O['opcost']},\"\")",
            "ppd": f"=IF(AND({g},N({I['days']})>0),{O['profit']}/{I['days']},\"\")",
            "rpl": f"=IF({g},{I['rate']}/{I['loaded']},\"\")",
            "rpt": f"=IF({g},{O['rev']}/{O['tot']},\"\")",
            "cpm": f"=IF({g},{O['allin']}/{O['tot']},\"\")",
            "margin": f"=IF({g},IFERROR({O['profit']}/{O['rev']},\"\"),\"\")",
            "be_rev": f"=IF({g},IFERROR(({O['opcost']}-{O['fees']}+IF({S['basis']}=\"{self.cfg.PASS_BASIS[1]}\",{O['pay']},0))/(1-{O['feep']}),\"\"),\"\")",
            "target_rev": f"=IF({g},IFERROR(({O['allin']}-{O['fees']})/(1-{O['feep']}-{S['margin']}),\"\"),\"\")",
            "counter": f"=IF({g},IFERROR(ROUNDUP({O['target_rev']}-N({I['det']})-N({I['stoppay']}),0),\"\"),\"\")",
            "be_rate": f"=IF({g},IFERROR(ROUNDUP({O['be_rev']}-N({I['det']})-N({I['stoppay']}),0),\"\"),\"\")",
            "code": f"=IF({g},IF({O['rev']}<{O['be_rev']},3,IF(AND({O['rev']}>={O['target_rev']},OR({S['min_ppd']}=\"\",N({O['ppd']})>=N({S['min_ppd']}))),1,2)),0)",
            "verdict": f"=IF({O['code']}=0,\"\",CHOOSE({O['code']},{S['v1']},{S['v2']},{S['v3']}))",
        }
        return f

    def verdict_cf(self, ws, rng, code_ref):
        for code, fc, bg in ((1, WHITE, POS), (2, WHITE, AMBER), (3, WHITE, NEG)):
            ws.conditional_formatting.add(rng, FormulaRule(formula=[f"{code_ref}={code}"], fill=fill(bg),
                                                           font=Font(name="Inter", bold=True, color=fc)))

    # ============================================================ LOAD CHECK (PHONE)
    def build_check(self):
        c, ws = self.cfg, self.ws[S_CHECK]
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 100
        ws.column_dimensions["A"].width = 1.5
        ws.column_dimensions["B"].width = 27
        ws.column_dimensions["C"].width = 14.5
        ws.column_dimensions["D"].width = 1.5
        last = 75
        for rr in range(1, last + 1):
            for cc in range(1, 5):
                x = ws.cell(row=rr, column=cc)
                x.fill = fill(PAPER)
                x.font = font()
        for rr in (1, 2):
            for cc in range(1, 5):
                ws.cell(row=rr, column=cc).fill = fill(GREEN)
        ws.row_dimensions[1].height = 34
        ws.row_dimensions[2].height = 20
        ws["B1"].value = "LOAD CHECK"
        ws["B1"].font = Font(name=TITLE, size=17, bold=True, color=PAPER)
        ws["B1"].alignment = Alignment(vertical="center", indent=1)
        ws["C1"].value = "BRASS LEDGER"
        ws["C1"].font = font(8, True, BRASS)
        ws["C1"].alignment = Alignment(horizontal="right", vertical="center")
        ws["B2"].value = ("SAMPLE  ·  " if self.sample else "") + "Take it or not?"
        ws["B2"].font = font(9, True, MUTED)
        ws["B2"].alignment = Alignment(vertical="center", indent=1)
        home = ws["C2"]
        home.value = "Dashboard ›"
        home.hyperlink = Hyperlink(ref="C2", location=f"{q(S_DASH)}!A1")
        home.font = Font(name="Inter", size=8, bold=True, color=BRASS)
        home.alignment = Alignment(horizontal="right", vertical="center")
        ws.sheet_properties.tabColor = BRASS
        I, O = {}, {}
        r = 4

        def field(key, text, fmt, kind, val=None):
            nonlocal r
            ws.merge_cells(f"B{r}:C{r}")
            self.label(ws[f"B{r}"], text, bold=True, color=INK2, size=9, indent=0)
            ws.row_dimensions[r].height = 17
            r += 1
            ws.merge_cells(f"B{r}:C{r}")
            x = ws[f"B{r}"]
            self.inp(x, fmt, align="right" if fmt else "center", value=val)
            x.font = font(16, True, INK)
            ws[f"C{r}"].border = BOX
            ws.row_dimensions[r].height = 30
            I[key] = f"$B${r}"
            if kind == "yn":
                self.dv_list(ws, f"B{r}", '"Y,N"')
            elif kind == "pct":
                self.dv_num(ws, f"B{r}", 0, 0.9, "Enter a percentage from 0 % to 90 %.")
            else:
                self.dv_num(ws, f"B{r}")
            r += 1

        lc = c.LOAD_CHECK if self.sample else {}
        for key, text, fmt, kind in LOAD_MAIN:
            field(key, text, fmt, kind, lc.get(key))
        r += 1
        # verdict
        vr = r
        ws.merge_cells(f"B{vr}:C{vr}")
        ws.row_dimensions[vr].height = 50
        self.cells["verdict"] = f"B{vr}"
        r += 1
        ws.merge_cells(f"B{r}:C{r}")
        self.cells["verdict_note"] = f"B{r}"
        ws.row_dimensions[r].height = 30
        r += 2
        out_rows = [("rpl", "Rate per loaded mile", CPM), ("rpt", "All-in rate per total mile", CPM),
                    ("cpm", "Your cost per mile", CPM), ("allin", "Total cost of the load", MONEY),
                    ("profit", "Profit after your pay", MONEY), ("ppd", "Profit per day", MONEY),
                    ("counter", "Rate needed for your target", MONEY0), ("be_rate", "Break-even rate", MONEY0)]
        orow = {}
        for key, text, fmt in out_rows:
            orow[key] = r
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "More details  ·  optional", rule_to=3)
        r += 1
        for key, text, fmt, kind in LOAD_MORE:
            field(key, text, fmt, kind, lc.get(key))
        r += 1
        self.kicker(ws, f"B{r}", "How the cost adds up", rule_to=3)
        r += 1
        brk = [("tot", "Total miles", MILES), ("rev", "Revenue", MONEY),
               ("fuelc", "Fuel", MONEY), ("reefer", "Reefer fuel", MONEY), ("permile", "Maint., tires, DEF, other", MONEY),
               ("trip", "Tolls, lumper, stop costs", MONEY), ("fees", "Factoring and dispatch fees", MONEY),
               ("fixed", "Share of fixed costs", MONEY), ("opcost", "Operating cost", MONEY), ("pay", "Your pay", MONEY),
               ("margin", "Profit margin", PCT)]
        for key, text, fmt in brk:
            orow[key] = r
            r += 1
        hid = r + 4                              # hidden helpers, below the disclaimer
        for key in ("feep", "profit_bp", "be_rev", "target_rev", "code"):
            orow[key] = hid
            hid += 1
        for key, rr in orow.items():
            O[key] = f"$C${rr}" if rr < r else f"$C${rr}"
        F = self.load_formulas(I, O)
        bold_keys = {"profit", "ppd", "counter", "opcost"}
        for key, text, fmt in out_rows + brk:
            rr = orow[key]
            self.label(ws[f"B{rr}"], text, bold=key in bold_keys, color=INK if key in bold_keys else INK2, size=10, indent=0)
            self.calc(ws[f"C{rr}"], fmt, bold=key in bold_keys, align="right", value=F[key])
            ws.row_dimensions[rr].height = 22
        for key in ("profit", "ppd"):
            ws.conditional_formatting.add(f"C{orow[key]}", FormulaRule(formula=[f'AND(ISNUMBER(C{orow[key]}),C{orow[key]}<0)'],
                                                                     font=Font(name="Inter", bold=True, color=NEG)))
        for key in ("feep", "profit_bp", "be_rev", "target_rev", "code"):
            rr = orow[key]
            ws[f"C{rr}"].value = F[key]
            ws[f"B{rr}"].value = key
            ws[f"B{rr}"].font = ws[f"C{rr}"].font = font(7, color=PAPER)
            ws.row_dimensions[rr].hidden = True
        # verdict cell
        v = ws[f"B{vr}"]
        v.value = F["verdict"].replace("=IF(", "=IF(", 1)
        v.font = Font(name="Inter", size=28, bold=True, color=WHITE)
        v.alignment = Alignment(horizontal="center", vertical="center")
        v.fill = fill(MUTED)
        v.protection = Protection(locked=True)
        code = O["code"]
        self.verdict_cf(ws, f"B{vr}:C{vr}", code)
        n = ws[self.cells["verdict_note"]]
        n.value = (f'=IF({code}=0,"Type the rate and the loaded miles",IF({code}=1,"Meets your target margin",'
                   f'IF({code}=2,"Covers break-even, not your target. Counter-offer below","Below break-even: it loses money")))')
        n.font = font(10, True, INK2)
        n.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        self.cells.update({k: f"C{rr}" for k, rr in orow.items()})
        self.cells["inputs"] = {k: v[1:].replace("$", "") for k, v in I.items()}
        r += 1
        ws.merge_cells(f"B{r}:C{r}")
        self.note(ws, f"B{r}:C{r}", "Estimates from your SETTINGS. Not financial advice. Not affiliated with any carrier, "
                  "broker or load board.", tint=BRASS_TINT, height=44, size=8.5)
        self.rows["check_end"] = r
        self.rows["check"] = dict(verdict=vr, outs=orow["rpl"], outs_end=orow["be_rate"], more=orow["be_rate"] + 2)
        # nothing to scroll to on the right
        ws.column_dimensions.group("E", "Z", hidden=True)
        ws.print_area = f"A1:D{r}"
        ws.page_setup.orientation = "portrait"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        self.protect(ws)

    # ============================================================ LOAD COMPARE
    def build_compare(self):
        c, ws = self.cfg, self.ws[S_CMP]
        widths = {"B": 40, **{L(3 + k): 16 for k in range(CMP_N)}, "H": 4}
        last_col = 2 + CMP_N
        self.page(ws, widths, last_col, 70, "Load compare", "Up to five offers side by side. The best profit per day is marked.")
        r = 4
        self.kicker(ws, f"B{r}", "The offers", rule_to=last_col)
        r += 1
        self.header(ws[f"B{r}"], "Load", align="left")
        for k in range(CMP_N):
            self.header(ws[f"{L(3 + k)}{r}"], f"Load {k + 1}")
        ws.row_dimensions[r].height = 24
        r += 1
        name_r = r
        self.lbl(ws, f"B{r}", "Lane or name")
        for k in range(CMP_N):
            self.inp(ws[f"{L(3 + k)}{r}"], align="center")
        r += 1
        rows_in = {}
        for key, text, fmt, kind in LOAD_MAIN + LOAD_MORE:
            rows_in[key] = r
            self.lbl(ws, f"B{r}", text, bold=key in ("rate", "loaded", "dh", "days"), size=10)
            for k in range(CMP_N):
                self.inp(ws[f"{L(3 + k)}{r}"], fmt, align="center" if kind == "yn" else None)
            rng = f"C{r}:{L(2 + CMP_N)}{r}"
            if kind == "yn":
                self.dv_list(ws, rng, '"Y,N"')
            elif kind == "pct":
                self.dv_num(ws, rng, 0, 0.9, "Enter a percentage from 0 % to 90 %.")
            else:
                self.dv_num(ws, rng)
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "What each load pays", rule_to=last_col)
        r += 1
        outs = [("verdict", "Verdict", None), ("rpl", "Rate per loaded mile", CPM), ("rpt", "All-in rate per total mile", CPM),
                ("tot", "Total miles", MILES), ("rev", "Revenue", MONEY), ("allin", "Total cost (incl. your pay)", MONEY),
                ("profit", "Profit after your pay", MONEY), ("ppd", "Profit per day", MONEY),
                ("counter", "Rate needed for your target", MONEY0), ("be_rate", "Break-even rate", MONEY0)]
        hidden = ["fuelc", "reefer", "permile", "trip", "fixed", "feep", "fees", "opcost", "pay", "profit_bp", "cpm",
                  "margin", "be_rev", "target_rev", "code"]
        orow = {}
        for key, text, fmt in outs:
            orow[key] = r
            r += 1
        best_r = r
        r += 2
        hr = r + 1
        for key in hidden:
            orow[key] = hr
            hr += 1
        for k in range(CMP_N):
            col = L(3 + k)
            I = {key: f"{col}${rr}" for key, rr in rows_in.items()}
            O = {key: f"{col}${rr}" for key, rr in orow.items()}
            F = self.load_formulas(I, O)
            for key, text, fmt in outs:
                x = ws[f"{col}{orow[key]}"]
                self.calc(x, fmt, bold=key in ("verdict", "profit", "ppd"), align="center", value=F[key])
            for key in hidden:
                x = ws[f"{col}{orow[key]}"]
                x.value = F[key]
                x.font = font(7, color=PAPER)
            ppd = f"{col}{orow['ppd']}"
            rng = f"$C${orow['ppd']}:${L(2 + CMP_N)}${orow['ppd']}"
            bx = ws[f"{col}{best_r}"]
            bx.value = f'=IF(AND(ISNUMBER({ppd}),COUNT({rng})>1,{ppd}=MAX({rng})),"BEST PER DAY","")'
            bx.font = font(9, True, POS)
            bx.alignment = Alignment(horizontal="center", vertical="center")
            code = f"{col}${orow['code']}"
            self.verdict_cf(ws, f"{col}{orow['verdict']}", code)
            for key in ("profit", "ppd"):
                cc = f"{col}{orow[key]}"
                ws.conditional_formatting.add(cc, FormulaRule(formula=[f"AND(ISNUMBER({cc}),{cc}<0)"],
                                                              font=Font(name="Inter", bold=True, color=NEG)))
            ws.conditional_formatting.add(f"{col}{orow['ppd']}", FormulaRule(
                formula=[f"AND(ISNUMBER({ppd}),COUNT({rng})>1,{ppd}=MAX({rng}))"], fill=fill(POS_TINT)))
        for key, text, fmt in outs:
            self.lbl(ws, f"B{orow[key]}", text, bold=key in ("verdict", "profit", "ppd"))
            ws.row_dimensions[orow[key]].height = 22
        ws.row_dimensions[orow["verdict"]].height = 26
        for key in hidden:
            ws.row_dimensions[orow[key]].hidden = True
            ws[f"B{orow[key]}"].value = key
            ws[f"B{orow[key]}"].font = font(7, color=PAPER)
        self.note(ws, f"B{best_r + 1}:{L(last_col)}{best_r + 1}", "Uses the same costs as LOAD CHECK. Blank optional cells use "
                  "SETTINGS. Profit per day is the fairest way to compare a short load with a long one.", height=30)
        if self.sample:
            for k, (nm, rate, ld, dh, days, tolls, stoppay, det) in enumerate(c.COMPARE):
                col = L(3 + k)
                ws[f"{col}{name_r}"] = nm
                for key, val in (("rate", rate), ("loaded", ld), ("dh", dh), ("days", days), ("tolls", tolls or None),
                                 ("stoppay", stoppay or None), ("det", det or None)):
                    ws[f"{col}{rows_in[key]}"] = val
        ws[f"C{name_r}"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for k in range(CMP_N):
            ws[f"{L(3 + k)}{name_r}"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[name_r].height = 32
        self.rows["cmp"] = dict(name=name_r, inputs=rows_in, outs=orow, best=best_r, end=best_r + 1)
        ws.freeze_panes = "C6"
        ws.print_area = f"A1:{L(last_col)}{best_r + 1}"
        self.protect(ws)

    # ============================================================ TRIP LOG
    TRIP_COLS = [  # col, header, width, kind, fmt
        ("B", "Picked up", 13, "date", DATE), ("C", "Delivered", 13, "date", DATE), ("D", "Broker / customer", 29, "text", None),
        ("E", "Origin", 20, "text", None), ("F", "Destination", 20, "text", None), ("G", "Loaded miles", 10, "num", MILES),
        ("H", "Deadhead miles", 10, "num", MILES), ("I", "Linehaul ($)", 12, "num", MONEY), ("J", "Fuel surcharge ($)", 12, "num", MONEY),
        ("K", "Detention ($)", 11, "num", MONEY), ("L", "Other revenue ($)", 11, "num", MONEY), ("M", "Fuel cost ($)", 12, "num", MONEY),
        ("N", "Tolls ($)", 10, "num", MONEY), ("O", "Other trip costs ($)", 12, "num", MONEY), ("P", "Factored? (Y/N)", 9, "yn", None),
        ("Q", "Factoring fee", 11, "calc", MONEY), ("R", "Dispatch fee", 11, "calc", MONEY), ("S", "Paid? (Y/N)", 8, "yn", None),
        ("T", "Payment date", 13, "date", DATE), ("U", "Notes", 30, "text", None),
        ("V", "Total miles", 10, "calc", MILES), ("W", "Total revenue", 12, "calc", MONEY), ("X", "Revenue per loaded mile", 11, "calc", CPM),
        ("Y", "Revenue per total mile", 11, "calc", CPM), ("Z", "Per-mile reserve (maint., tires, DEF)", 13, "calc", MONEY),
        ("AA", "Fixed-cost share", 12, "calc", MONEY), ("AB", "Trip profit before your pay", 13, "calc", MONEY),
        ("AC", "Days", 7, "calc", "0"), ("AD", "Profit per day", 12, "calc", MONEY),
        ("AE", "Month", 7, "calc", "0;-0;"), ("AF", "Year", 7, "calc", "0;-0;")]

    def build_trips(self):
        c, ws, S = self.cfg, self.ws[S_TRIP], self.S
        widths = {col: w for col, _, w, _, _ in self.TRIP_COLS}
        self.page(ws, widths, 32, TRIP_LAST, "Trip log", "One row per load. White cells are yours; shaded cells calculate.")
        T = lambda col: f"{q(S_TRIP)}!${col}${TRIP_FIRST}:${col}${TRIP_LAST}"   # noqa: E731
        self.T = T
        yr = f"{T('AF')},{S['year']}"
        tiles = [("LOADS THIS YEAR", f"=COUNTIFS({yr})", "0"),
                 ("MILES THIS YEAR", f"=SUMIFS({T('V')},{yr})", MILES),
                 ("REVENUE THIS YEAR", f"=SUMIFS({T('W')},{yr})", MONEY0),
                 ("REVENUE / TOTAL MILE", f"=IFERROR(SUMIFS({T('W')},{yr})/SUMIFS({T('V')},{yr}),0)", CPM),
                 ("DEADHEAD %", f"=IFERROR(SUMIFS({T('H')},{yr})/SUMIFS({T('V')},{yr}),0)", PCT),
                 ("UNPAID INVOICES", f'=SUMIFS({T("W")},{T("S")},"<>Y",{T("B")},"<>")', MONEY0)]
        spans = [(2, 3), (4, 6), (7, 9), (10, 13), (14, 16), (17, 20)]
        for (lab, f, fmt), (c1, c2) in zip(tiles, spans):
            self.tile(ws, 4, c1, c2, lab, f, fmt, size=15)
        hr = TRIP_FIRST - 1
        ws.row_dimensions[6].height = 8
        for col, h, w, kind, fmt in self.TRIP_COLS:
            self.header(ws[f"{col}{hr}"], h, fill_color=GREEN if kind != "calc" else GREEN2,
                        align="left" if col in ("B", "D", "E", "F", "U") else "center")
        ws.row_dimensions[hr].height = 44
        for r in range(TRIP_FIRST, TRIP_LAST + 1):
            B = f"B{r}"
            for col, h, w, kind, fmt in self.TRIP_COLS:
                x = ws[f"{col}{r}"]
                if kind == "calc":
                    self.calc(x, fmt, align="center" if col in ("AC", "AE", "AF") else None)
                else:
                    self.inp(x, fmt, align="center" if kind in ("yn", "date") else None)
            f = {
                "Q": f'=IF(B{r}="","",IF(UPPER(P{r})="N",0,W{r}*{S["fact"]}))',
                "R": f'=IF(B{r}="","",W{r}*{S["disp"]})',
                "V": f'=IF(B{r}="","",N(G{r})+N(H{r}))',
                "W": f'=IF(B{r}="","",N(I{r})+N(J{r})+N(K{r})+N(L{r}))',
                "X": f'=IF(OR(B{r}="",N(G{r})=0),"",W{r}/G{r})',
                "Y": f'=IF(OR(B{r}="",N(V{r})=0),"",W{r}/V{r})',
                "Z": f'=IF(B{r}="","",V{r}*({S["def_pm"]}+{S["maint_pm"]}+{S["tire_pm"]}+{S["other_pm"]}))',
                "AA": f'=IF(B{r}="","",V{r}*{S["fixed_cpm"]})',
                "AB": f'=IF(B{r}="","",W{r}-N(M{r})-N(N{r})-N(O{r})-Q{r}-R{r}-Z{r}-AA{r})',
                "AC": f'=IF(OR(B{r}="",C{r}=""),"",C{r}-B{r}+1)',
                "AD": f'=IF(OR(B{r}="",N(AC{r})<=0),"",AB{r}/AC{r})',
                "AE": f'=IF(ISNUMBER({B}),MONTH({B}),0)',
                "AF": f'=IF(ISNUMBER({B}),YEAR({B}),0)',
            }
            for col, form in f.items():
                ws[f"{col}{r}"].value = form
        ws.conditional_formatting.add(f"AB{TRIP_FIRST}:AB{TRIP_LAST}", FormulaRule(
            formula=[f"AND(ISNUMBER(AB{TRIP_FIRST}),AB{TRIP_FIRST}<0)"], font=Font(name="Inter", bold=True, color=NEG)))
        ws.conditional_formatting.add(f"S{TRIP_FIRST}:S{TRIP_LAST}", FormulaRule(
            formula=[f'AND(B{TRIP_FIRST}<>"",UPPER(S{TRIP_FIRST})<>"Y")'], fill=fill(NEG_TINT), font=Font(name="Inter", bold=True, color=NEG)))
        rng = lambda col: f"{col}{TRIP_FIRST}:{col}{TRIP_LAST}"   # noqa: E731
        for col in ("B", "C", "T"):
            self.dv_date(ws, rng(col))
        for col in "GHIJKLMNO":
            self.dv_num(ws, rng(col))
        self.dv_list(ws, rng("P"), '"Y,N"')
        self.dv_list(ws, rng("S"), '"Y,N"')
        if self.sample:
            for i, t in enumerate(c.sample_trips()):
                r = TRIP_FIRST + i
                vals = dict(B=t["pu"], C=t["de"], D=t["broker"], E=t["origin"], F=t["dest"], G=t["loaded"], H=t["dh"],
                            I=t["lh"], J=t["fsc"], K=t["det"] or None, L=t["oth"] or None, M=t["fuel"], N=t["tolls"] or None,
                            O=t["ocost"] or None, P=t["factored"], S=t["paid"], T=t["paydate"], U=t["note"] or None)
                for col, v in vals.items():
                    ws[f"{col}{r}"].value = v
        ws.freeze_panes = f"C{TRIP_FIRST}"
        ws.print_area = f"A1:AF{TRIP_FIRST + 40}"
        ws.print_title_rows = f"{hr}:{hr}"
        self.protect(ws)

    # ============================================================ FUEL LOG
    def build_fuel(self):
        c, ws, S = self.cfg, self.ws[S_FUEL], self.S
        widths = {"B": 13, "C": 16, "D": 8, "E": 10, "F": 11, "G": 12, "H": 12, "I": 10, "J": 11, "K": 8, "L": 3,
                  "M": 13, "N": 31, "O": 8, "P": 10, "Q": 3, "R": 9, "S": 12, "T": 12, "U": 14}
        self.page(ws, widths, 21, FUEL_LAST, "Fuel log",
                  "Fill-ups, MPG and miles by state. Records to help with IFTA reporting; this sheet does not calculate IFTA tax.")
        F = lambda col: f"${col}${FUEL_FIRST}:${col}${FUEL_LAST}"   # noqa: E731
        tiles = [("GALLONS LOGGED", f"=SUM({F('E')})", GAL), ("FUEL SPENT", f"=SUM({F('G')})", MONEY0),
                 ("AVERAGE PRICE / GAL", f"=IFERROR(SUM({F('G')})/SUM({F('E')}),0)", MONEY),
                 ("AVERAGE MPG", f"=IFERROR((MAX({F('H')})-MIN({F('H')}))/(SUM({F('E')})-INDEX({F('E')},MATCH(MIN({F('H')}),{F('H')},0))),0)", MPG)]
        for (lab, f, fmt), (c1, c2) in zip(tiles, [(2, 3), (4, 6), (7, 8), (9, 11)]):
            self.tile(ws, 4, c1, c2, lab, f, fmt, size=15)
        self.S["avg_mpg"] = f"{q(S_FUEL)}!$I$5"
        ws.row_dimensions[6].height = 8
        hr = FUEL_FIRST - 1
        cols = [("B", "Date", "date", DATE), ("C", "City", "text", None), ("D", "State / prov.", "state", None),
                ("E", "Gallons", "num", GAL), ("F", "Price per gallon", "num", MONEY), ("G", "Total ($)", "calc", MONEY),
                ("H", "Odometer", "num", MILES), ("I", "DEF ($)", "num", MONEY), ("J", "Miles since last fill", "calc", MILES),
                ("K", "MPG", "calc", MPG)]
        for col, h, kind, fmt in cols:
            self.header(ws[f"{col}{hr}"], h, fill_color=GREEN2 if kind == "calc" else GREEN, align="left" if col == "B" else "center")
        ws.row_dimensions[hr].height = 40
        for r in range(FUEL_FIRST, FUEL_LAST + 1):
            for col, h, kind, fmt in cols:
                x = ws[f"{col}{r}"]
                if kind == "calc":
                    self.calc(x, fmt)
                else:
                    self.inp(x, fmt, align="center" if kind in ("date", "state") else None)
            ws[f"G{r}"].value = f'=IF(AND(E{r}="",F{r}=""),"",N(E{r})*N(F{r}))'
            if r == FUEL_FIRST:
                ws[f"J{r}"].value = '=""'
                ws[f"K{r}"].value = '=""'
            else:
                ws[f"J{r}"].value = f'=IF(OR(N(H{r})=0,N(H{r - 1})=0),"",H{r}-H{r - 1})'
                ws[f"K{r}"].value = f'=IF(OR(J{r}="",N(E{r})=0),"",J{r}/E{r})'
        self.dv_date(ws, f"B{FUEL_FIRST}:B{FUEL_LAST}")
        self.dv_list(ws, f"D{FUEL_FIRST}:D{FUEL_LAST}", S["states"])
        self.dv_num(ws, f"E{FUEL_FIRST}:F{FUEL_LAST}")
        self.dv_num(ws, f"H{FUEL_FIRST}:I{FUEL_LAST}")
        # miles by state per trip
        self.kicker(ws, f"M{hr - 1}", "Miles by state, per trip", rule_to=16)
        for col, h in (("M", "Trip date"), ("N", "Trip (origin to destination)"), ("O", "State / prov."), ("P", "Miles")):
            self.header(ws[f"{col}{hr}"], h, align="left" if col in ("M", "N") else "center")
        for r in range(SM_FIRST, SM_LAST + 1):
            self.inp(ws[f"M{r}"], DATE, align="center")
            self.inp(ws[f"N{r}"])
            self.inp(ws[f"O{r}"], align="center")
            self.inp(ws[f"P{r}"], MILES)
        self.dv_date(ws, f"M{SM_FIRST}:M{SM_LAST}")
        self.dv_list(ws, f"O{SM_FIRST}:O{SM_LAST}", S["states"])
        self.dv_num(ws, f"P{SM_FIRST}:P{SM_LAST}")
        # summary by jurisdiction for a quarter
        self.kicker(ws, "R4", "Totals by state  ·  for your IFTA records", rule_to=21)
        self.lbl(ws, "R5", "Period", size=9)
        ws.merge_cells("S5:T5")
        self.inp(ws["S5"], align="center", value="Full year")
        self.dv_list(ws, "S5", '"Full year,Q1,Q2,Q3,Q4"')
        self.calc(ws["U5"], DATE, align="center",
                  value=f'=IF(S5="Full year",DATE({S["year"]},1,1),DATE({S["year"]},3*N(RIGHT(S5,1))-2,1))')
        self.calc(ws["U6"], DATE, align="center",
                  value=f'=IF(S5="Full year",DATE({S["year"]},12,31),DATE({S["year"]},3*N(RIGHT(S5,1))+1,1)-1)')
        ws["T6"].value = "From / to"
        ws["T6"].font = font(8, color=INK2)
        ws["T6"].alignment = Alignment(horizontal="right", vertical="center")
        ws["U5"].value = f'=IF($S$5="Full year",DATE({S["year"]},1,1),DATE({S["year"]},3*VALUE(RIGHT($S$5,1))-2,1))'
        ws["U6"].value = f'=IF($S$5="Full year",DATE({S["year"]},12,31),DATE({S["year"]},3*VALUE(RIGHT($S$5,1))+1,1)-1)'
        ws.row_dimensions[6].height = 16
        for col, h in (("R", "State"), ("S", "Miles"), ("T", "Gallons bought"), ("U", "Fuel bought ($)")):
            self.header(ws[f"{col}{hr}"], h)
        for i, st in enumerate(c.STATES):
            r = FUEL_FIRST + i
            self.calc(ws[f"R{r}"], align="center", value=st)
            per_m = f'$M${SM_FIRST}:$M${SM_LAST},">="&$U$5,$M${SM_FIRST}:$M${SM_LAST},"<="&$U$6'
            per_f = f'$B${FUEL_FIRST}:$B${FUEL_LAST},">="&$U$5,$B${FUEL_FIRST}:$B${FUEL_LAST},"<="&$U$6'
            self.calc(ws[f"S{r}"], MILES_Z, value=f"=SUMIFS($P${SM_FIRST}:$P${SM_LAST},$O${SM_FIRST}:$O${SM_LAST},R{r},{per_m})")
            self.calc(ws[f"T{r}"], "#,##0.0;-#,##0.0;", value=f"=SUMIFS($E${FUEL_FIRST}:$E${FUEL_LAST},$D${FUEL_FIRST}:$D${FUEL_LAST},R{r},{per_f})")
            self.calc(ws[f"U{r}"], '"$"#,##0.00;-"$"#,##0.00;', value=f"=SUMIFS($G${FUEL_FIRST}:$G${FUEL_LAST},$D${FUEL_FIRST}:$D${FUEL_LAST},R{r},{per_f})")
        tr = FUEL_FIRST + len(c.STATES)
        self.lbl(ws, f"R{tr}", "Total", color=GREEN)
        self.calc(ws[f"S{tr}"], MILES, bold=True, value=f"=SUM(S{FUEL_FIRST}:S{tr - 1})")
        self.calc(ws[f"T{tr}"], GAL, bold=True, value=f"=SUM(T{FUEL_FIRST}:T{tr - 1})")
        self.calc(ws[f"U{tr}"], MONEY, bold=True, value=f"=SUM(U{FUEL_FIRST}:U{tr - 1})")
        ws.merge_cells(f"R{tr + 1}:U{tr + 3}")
        self.note(ws, f"R{tr + 1}:U{tr + 3}", "Records to help with IFTA reporting. This sheet does not calculate IFTA tax or "
                  "credits; your IFTA return uses your state's rates and rules.", size=8.5)
        if self.sample:
            for i, fl in enumerate(c.sample_fuel()):
                r = FUEL_FIRST + i
                for col, v in dict(B=fl["date"], C=fl["city"], D=fl["state"], E=fl["gal"], F=fl["price"], H=fl["odo"],
                                   I=fl["defc"]).items():
                    ws[f"{col}{r}"].value = v
            for i, (d, trip, st, m) in enumerate(c.sample_state_miles()):
                r = SM_FIRST + i
                ws[f"M{r}"], ws[f"N{r}"], ws[f"O{r}"], ws[f"P{r}"] = d, trip, st, m
        self.rows["fuel_states_total"] = tr
        ws.freeze_panes = f"A{FUEL_FIRST}"
        ws.print_area = f"A1:U{FUEL_FIRST + 30}"
        self.protect(ws)

    # ============================================================ MONTHLY P&L
    def build_pnl(self):
        c, ws, S = self.cfg, self.ws[S_PNL], self.S
        T = self.T
        widths = {"B": 14, "C": 14, "D": 11, "E": 10, "F": 13, "G": 12, "H": 13, "I": 12, "J": 11, "K": 13, "L": 12, "M": 13,
                  "N": 11, "O": 11, "P": 11, "Q": 24, "R": 10}
        self.page(ws, widths, 18, 110, "Monthly P&L", "Twelve months of revenue, costs and profit from the TRIP LOG and SETTINGS.")
        yr = f"{T('AF')},{S['year']}"
        # first and last month with a logged load: fixed costs count from one to the other
        self.lbl(ws, "B4", "Year", size=9)
        self.calc(ws["C4"], "0", align="center", value=f"={S['year']}")
        self.lbl(ws, "D4", "First month", size=9)
        self.calc(ws["F4"], "0;-0;", align="center",
                  value=f"=IF(COUNTIFS({yr})=0,0,SUMPRODUCT(MIN(({T('AF')}={S['year']})*({T('AE')}>0)*{T('AE')}+(({T('AF')}<>{S['year']})+({T('AE')}=0)>0)*99)))")
        self.lbl(ws, "G4", "Last month", size=9)
        self.calc(ws["H4"], "0;-0;", align="center", value=f"=SUMPRODUCT(MAX(({T('AF')}={S['year']})*{T('AE')}))")
        ws.merge_cells("I4:R4")
        self.label(ws["I4"], "Fixed costs count every month from your first to your last month with a logged load, "
                             "including idle months in between.", bold=False, color=INK2, size=9)
        hr = 6
        heads = [("B", "Month"), ("C", "Loads"), ("D", "Total miles"), ("E", "Deadhead %"), ("F", "Revenue"), ("G", "Fuel"),
                 ("H", "Other variable costs"), ("I", "Fixed costs"), ("J", "Fees"), ("K", "Profit before your pay"),
                 ("L", "Pay drawn (type)"), ("M", "Net profit"), ("N", "Revenue per mile"), ("O", "Actual cost per mile"),
                 ("P", "Estimate (Settings)"), ("Q", "Check"), ("R", "Days away from home")]
        for col, h in heads:
            self.header(ws[f"{col}{hr}"], h, fill_color=GREEN, align="left" if col == "B" else "center")
        ws.row_dimensions[hr].height = 40
        m1 = hr + 1
        aw1 = m1 + 12 + 5                        # away-from-home log first row
        aw2 = aw1 + AWAY_N - 1
        A, Bk = f"$B${aw1}:$B${aw2}", f"$C${aw1}:$C${aw2}"
        for m in range(1, 13):
            r = m1 + m - 1
            cond = f"{T('AE')},{m},{yr}"
            ws[f"B{r}"] = c.MONTHS[m - 1]
            ws[f"B{r}"].font = font(10, True, INK)
            ws[f"B{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            f = {
                "C": f"=COUNTIFS({cond})",
                "D": f"=SUMIFS({T('V')},{cond})",
                "E": f'=IF(D{r}=0,"",SUMIFS({T("H")},{cond})/D{r})',
                "F": f"=SUMIFS({T('W')},{cond})",
                "G": f"=SUMIFS({T('M')},{cond})",
                "H": f"=SUMIFS({T('N')},{cond})+SUMIFS({T('O')},{cond})+SUMIFS({T('Z')},{cond})",
                "I": f"=IF(AND($F$4>0,{m}>=$F$4,{m}<=$H$4),{S['fixed_month']},0)",
                "J": f"=SUMIFS({T('Q')},{cond})+SUMIFS({T('R')},{cond})",
                "K": f"=F{r}-G{r}-H{r}-I{r}-J{r}",
                "M": f"=K{r}-N(L{r})",
                "N": f'=IF(D{r}=0,"",F{r}/D{r})',
                "O": f'=IF(D{r}=0,"",(G{r}+H{r}+I{r})/D{r})',
                "P": f'=IF(D{r}=0,"",{S["op_cpm"]})',
                "Q": f'=IF(OR(O{r}="",N(P{r})=0),"",IF(O{r}>P{r}*1.1,"Above estimate by "&ROUND((O{r}/P{r}-1)*100,0)&"%","Within 10% of estimate"))',
                "R": (f"=SUMPRODUCT(({A}<>\"\")*({Bk}<>\"\")*((({Bk}-({Bk}>DATE({S['year']},{m}+1,0))*({Bk}-DATE({S['year']},{m}+1,0)))"
                      f"-({A}+({A}<DATE({S['year']},{m},1))*(DATE({S['year']},{m},1)-{A}))+1)>0)"
                      f"*(({Bk}-({Bk}>DATE({S['year']},{m}+1,0))*({Bk}-DATE({S['year']},{m}+1,0)))"
                      f"-({A}+({A}<DATE({S['year']},{m},1))*(DATE({S['year']},{m},1)-{A}))+1))"),
            }
            fmts = dict(C="0;-0;", D=MILES_Z, E=PCT, F=MONEY_Z, G=MONEY_Z, H=MONEY_Z, I=MONEY_Z, J=MONEY_Z, K=MONEY_Z, M=MONEY_Z, N=CPM,
                        O=CPM, P=CPM, Q=None, R="0;-0;")
            for col, form in f.items():
                self.calc(ws[f"{col}{r}"], fmts[col], bold=col in ("K", "M"), align="center" if col in ("C", "R") else None, value=form)
            self.inp(ws[f"L{r}"], MONEY, value=c.PAY_DRAWN.get(m) if self.sample else None)
            ws[f"Q{r}"].font = font(9, True, INK2)
        m2 = m1 + 11
        tr = m2 + 1
        self.lbl(ws, f"B{tr}", "Year", color=GREEN)
        for col in "CDFGHIJKLMR":
            self.calc(ws[f"{col}{tr}"], ws[f"{col}{m1}"].number_format if col != "L" else MONEY, bold=True,
                      align="center" if col in ("C", "R") else None, value=f"=SUM({col}{m1}:{col}{m2})")
        self.calc(ws[f"E{tr}"], PCT, bold=True, value=f'=IF(D{tr}=0,"",SUMIFS({T("H")},{yr})/D{tr})')
        self.calc(ws[f"N{tr}"], CPM, bold=True, value=f'=IF(D{tr}=0,"",F{tr}/D{tr})')
        self.calc(ws[f"O{tr}"], CPM, bold=True, value=f'=IF(D{tr}=0,"",(G{tr}+H{tr}+I{tr})/D{tr})')
        self.calc(ws[f"P{tr}"], CPM, bold=True, value=f'=IF(D{tr}=0,"",{S["op_cpm"]})')
        self.calc(ws[f"Q{tr}"], value=f'=IF(OR(O{tr}="",N(P{tr})=0),"",IF(O{tr}>P{tr}*1.1,"Above estimate by "&ROUND((O{tr}/P{tr}-1)*100,0)&"%","Within 10% of estimate"))')
        for col in "BCDEFGHIJKLMNOPQR":
            ws[f"{col}{tr}"].border = Border(top=Side(style="medium", color=GREEN), bottom=Side(style="thin", color=GREEN))
        for col in "KM":
            ws.conditional_formatting.add(f"{col}{m1}:{col}{tr}", FormulaRule(
                formula=[f"{col}{m1}<0"], font=Font(name="Inter", bold=True, color=NEG)))
        ws.conditional_formatting.add(f"Q{m1}:Q{tr}", FormulaRule(formula=[f'LEFT(Q{m1},5)="Above"'], fill=fill(NEG_TINT),
                                                                   font=Font(name="Inter", bold=True, color=NEG)))
        ws.conditional_formatting.add(f"O{m1}:O{tr}", FormulaRule(formula=[f'AND(ISNUMBER(O{m1}),O{m1}>P{m1}*1.1)'],
                                                                   font=Font(name="Inter", bold=True, color=NEG)))
        self.dv_num(ws, f"L{m1}:L{m2}")
        ws.merge_cells(f"B{tr + 1}:R{tr + 1}")
        self.label(ws[f"B{tr + 1}"], "Other variable costs = tolls + other trip costs + the per-mile reserve for maintenance, "
                   "tires and DEF. Actual cost per mile = fuel + other variable + fixed, per mile (before fees and your pay), "
                   "compared with the operating cost per mile on SETTINGS.", bold=False, color=INK2, size=9, wrap=True)
        ws.row_dimensions[tr + 1].height = 30
        # away from home log
        k = aw1 - 2
        self.kicker(ws, f"B{k}", "Days away from home  ·  records for your tax preparer, e.g. per diem; not tax advice", rule_to=10)
        for col, h in (("B", "Left home"), ("C", "Back home"), ("D", "Days")):
            self.header(ws[f"{col}{aw1 - 1}"], h)
        ws.merge_cells(f"F{aw1 - 1}:J{aw1 + 2}")
        self.note(ws, f"F{aw1 - 1}:J{aw1 + 2}", "One row per stretch on the road. Days count both the day you leave and the day "
                  "you get back. The column on the right of the P&L splits them by month.", size=9)
        for i in range(AWAY_N):
            r = aw1 + i
            self.inp(ws[f"B{r}"], DATE, align="center")
            self.inp(ws[f"C{r}"], DATE, align="center")
            self.calc(ws[f"D{r}"], "0", align="center", value=f'=IF(OR(B{r}="",C{r}=""),"",C{r}-B{r}+1)')
        self.dv_date(ws, f"B{aw1}:C{aw2}")
        if self.sample:
            import datetime as dt
            for i, (a, b) in enumerate(c.AWAY):
                ws[f"B{aw1 + i}"] = dt.date.fromisoformat(a)
                ws[f"C{aw1 + i}"] = dt.date.fromisoformat(b)
        self.rows["pnl"] = dict(m1=m1, total=tr, away=aw1)
        ws.freeze_panes = f"C{hr + 1}"
        ws.print_area = f"A1:R{tr + 1}"
        self.protect(ws)

    # ============================================================ DASHBOARD
    def build_dashboard(self):
        c, ws, S = self.cfg, self.ws[S_DASH], self.S
        T = self.T
        widths = {L(k): 13 for k in range(2, 15)}
        self.page(ws, widths, 14, 70, "Dashboard", "Your cost per mile, what you're earning per mile, and the year so far.")
        P = self.rows["pnl"]
        tr = P["total"]
        pnl = lambda col: f"{q(S_PNL)}!${col}${tr}"   # noqa: E731
        ws.merge_cells("B4:N4")
        self.label(ws["B4"], f'=IF({S["name"]}="","Your trucking business",{S["name"]})&"  ·  "&{S["year"]}&"  ·  "&{S["equip"]}',
                   color=GREEN, size=11)
        yr = f"{T('AF')},{S['year']}"
        tiles1 = [("BREAK-EVEN COST / MILE", f"={S['op_cpm']}", CPM),
                  ("ALL-IN COST / MILE", f"={S['allin_cpm']}", CPM),
                  ("AVG REVENUE / MILE", f"=IFERROR({pnl('F')}/{pnl('D')},0)", CPM),
                  ("DEADHEAD %", f"=IFERROR(SUMIFS({T('H')},{yr})/{pnl('D')},0)", PCT)]
        tiles2 = [("NET PROFIT YEAR TO DATE", f"={pnl('M')}", MONEY0),
                  ("PROFIT PER DAY (AVG)", f"=IFERROR(SUMIFS({T('AB')},{yr})/SUMIFS({T('AC')},{yr}),0)", MONEY0),
                  ("UNPAID INVOICES", f'=SUMIFS({T("W")},{T("S")},"<>Y",{T("B")},"<>")', MONEY0)]
        for i, (lab, f, fmt) in enumerate(tiles1):
            self.tile(ws, 6, 2 + 3 * i + (1 if i == 3 else 0) * 0, 4 + 3 * i, lab, f, fmt)
        for i, (lab, f, fmt) in enumerate(tiles2):
            self.tile(ws, 9, 2 + 4 * i, 5 + 4 * i, lab, f, fmt)
        ws.row_dimensions[8].height = 6
        ws.merge_cells("B11:N11")
        self.label(ws["B11"], "Profit per day is before your pay (TRIP LOG). Net profit is after the pay you drew (MONTHLY P&L).",
                   bold=False, color=INK2, size=9)
        # month table
        r = 13
        self.kicker(ws, f"B{r}", "Net profit by month", rule_to=14)
        hr = r + 1
        for col, h in (("B", "Month"), ("C", "Net profit"), ("D", "Revenue / mile"), ("E", "Cost / mile"), ("F", "Deadhead %")):
            self.header(ws[f"{col}{hr}"], h, align="left" if col == "B" else "center")
        ws.row_dimensions[hr].height = 30
        for m in range(12):
            rr = hr + 1 + m
            pr = P["m1"] + m
            ws[f"B{rr}"] = c.MONTHS[m][:3]
            ws[f"B{rr}"].font = font(10, True, INK)
            ws[f"B{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            self.calc(ws[f"C{rr}"], MONEY0_Z, value=f"={q(S_PNL)}!M{pr}")
            self.calc(ws[f"D{rr}"], CPM_Z, value=f"=N({q(S_PNL)}!N{pr})")
            self.calc(ws[f"E{rr}"], CPM_Z, value=f"=N({q(S_PNL)}!O{pr})")
            self.calc(ws[f"F{rr}"], PCT_Z, value=f"=N({q(S_PNL)}!E{pr})")
        d1, d2 = hr + 1, hr + 12
        ws.conditional_formatting.add(f"C{d1}:C{d2}", FormulaRule(formula=[f"C{d1}<0"], font=Font(name="Inter", bold=True, color=NEG)))

        def bar(cols, colors, anchor, w, h, fmt="#,##0", legend=False):
            ch = BarChart()
            ch.type, ch.style = "col", 10
            for col in cols:
                ch.add_data(Reference(ws, min_col=col, min_row=hr, max_row=d2), titles_from_data=True)
            ch.set_categories(Reference(ws, min_col=2, min_row=d1, max_row=d2))
            for s, colr in zip(ch.series, colors):
                s.graphicalProperties.solidFill = colr
                s.graphicalProperties.line.solidFill = colr
            BP.clean_chart(ch, legend=legend)
            ch.y_axis.numFmt = fmt
            ch.gapWidth = 60
            ch.height, ch.width = h, w
            ch.anchor = anchor
            ws.add_chart(ch)

        bar([3], [GREEN], f"H{hr}", 15.5, 6.2, '"$"#,##0')
        r2 = d2 + 2
        self.kicker(ws, f"B{r2}", "Revenue per mile against cost per mile", rule_to=7)
        self.kicker(ws, f"I{r2}", "Deadhead % by month", rule_to=14)
        bar([4, 5], [GREEN, BRASS], f"B{r2 + 1}", 13.5, 6.5, '"$"0.00', legend=True)
        bar([6], [BRASS], f"I{r2 + 1}", 12.5, 6.5, "0%")
        end = r2 + 15
        self.note(ws, f"B{end}:N{end}", c.DISCLAIMER, height=30, size=9, color=INK, bold=True)
        self.rows["dash"] = dict(months=r, charts=r2, end=end)
        ws.print_area = f"A1:N{end}"
        self.protect(ws)

    # ============================================================ START HERE
    def build_start(self):
        c, ws = self.cfg, self.ws[S_START]
        self.page(ws, {"B": 5, "C": 28, "D": 30, "E": 30, "F": 24}, 6, 80, "Start here",
                  "Read this first. Setting up takes about 15 minutes.", landscape=False)
        self.note(ws, "B4:F4", c.PROMISE, tint=PAPER, height=32, size=15, color=GREEN, bold=True)
        ws["B4"].font = Font(name=TITLE, size=15, bold=True, color=GREEN)
        self.note(ws, "B5:F5", "A load can look good on the rate and still lose money once deadhead, fuel, tolls, the truck "
                  "payment, insurance and your own pay are counted. Put your real costs in once, and this workbook tells you "
                  "what a mile costs you and whether a load covers it.", tint=PAPER, height=48, size=10, color=INK)
        r = 7
        self.kicker(ws, f"B{r}", "Quick start in 3 steps", rule_to=6)
        r += 1
        for num, head, body, sheet in [
                ("1", "Settings, once", "Pick your equipment type, then type your fuel price, fixed costs, the pay you want "
                 "to take home and the miles you run. Your cost per mile appears at the top.", S_SET),
                ("2", "Check a load", "On your phone or laptop: type the rate, loaded miles, deadhead and days. You get "
                 "TAKE, NEGOTIATE or PASS, the profit per day and the rate to counter with.", S_CHECK),
                ("3", "Log the trip", "One row per load on TRIP LOG, fill-ups on FUEL LOG. MONTHLY P&L and DASHBOARD show "
                 "your real cost per mile, revenue per mile and deadhead.", S_TRIP)]:
            x = ws[f"B{r}"]
            x.value = num
            x.font = Font(name=TITLE, size=18, bold=True, color=BRASS)
            x.alignment = Alignment(horizontal="center", vertical="top")
            self.link(ws[f"C{r}"], f"{head}  ›", sheet)
            ws[f"C{r}"].alignment = Alignment(vertical="top")
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"] = body
            ws[f"D{r}"].font = font(10, color=INK)
            ws[f"D{r}"].alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 48
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "On your phone (Google Sheets app)", rule_to=6)
        r += 1
        for t in ["Open your Google Sheets copy in the Google Sheets app (Android or iPhone).",
                  "Tap the LOAD CHECK (PHONE) tab at the bottom of the screen. It is one narrow column: no sideways scrolling.",
                  "Tap a white cell, type the number, tap the tick. The verdict changes colour: green TAKE, amber NEGOTIATE, red PASS.",
                  "Type over last load's numbers for the next one. Change your costs on a laptop; the phone tab uses them."]:
            ws.merge_cells(f"C{r}:F{r}")
            self.label(ws[f"C{r}"], "•  " + t, bold=False, size=10, wrap=True)
            ws.row_dimensions[r].height = 30
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Colour key", rule_to=6)
        r += 1
        for kind, head, body in [("inp", "Type here", "White cell with a border: your numbers, or pick from the dropdown."),
                                 ("calc", "Calculated", "Shaded cell: a formula, locked so it can't be overwritten by accident."),
                                 ("tile", "Result", "Green block with a brass figure: a key number."),
                                 ("take", "TAKE", "Meets your target margin."),
                                 ("neg", "NEGOTIATE", "Covers break-even but not your target: counter with the rate shown."),
                                 ("pass", "PASS", "Below break-even: it costs you money to haul it.")]:
            x = ws[f"C{r}"]
            if kind == "inp":
                self.inp(x)
            elif kind == "calc":
                self.calc(x)
            elif kind == "tile":
                x.fill, x.font = fill(GREEN), font(10, True, BRASS)
            else:
                x.fill = fill({"take": POS, "neg": AMBER, "pass": NEG}[kind])
                x.font = font(10, True, WHITE)
            x.value = head
            x.protection = Protection(locked=True)
            x.alignment = Alignment(indent=1, vertical="center")
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"] = body
            ws[f"D{r}"].font = font(10, color=INK2)
            ws[f"D{r}"].alignment = Alignment(vertical="center", indent=1)
            ws.row_dimensions[r].height = 22
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Good to know", rule_to=6)
        r += 1
        for t in ["Your own pay counts. A load that only covers the truck is not a good load; set the pay you need on SETTINGS.",
                  "Hotshot or box truck? Pick it in Equipment type on SETTINGS. The MPG, maintenance and tire numbers change; "
                  "check your fixed costs too.",
                  "FUEL LOG keeps records to help with IFTA reporting. It does not calculate IFTA tax.",
                  "Days away from home (MONTHLY P&L) are records for your tax preparer, e.g. per diem; not tax advice."]:
            ws.merge_cells(f"C{r}:F{r}")
            self.label(ws[f"C{r}"], "•  " + t, bold=False, size=10, wrap=True)
            ws.row_dimensions[r].height = 30
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Guide and Google Sheets", rule_to=6)
        r += 1
        self.note(ws, f"B{r}:F{r}", f"Quick-start guide: {c.GUIDE_NAME} (in your download).   "
                  "Google Sheets copy: [GOOGLE SHEETS COPY LINK]", tint=PAPER, height=30, size=10, color=INK)
        r += 2
        self.note(ws, f"B{r}:F{r}", c.DISCLAIMER, tint=BRASS_TINT, height=34, size=10, color=INK, bold=True)
        if self.sample:
            r += 2
            self.note(ws, f"B{r}:F{r}", "SAMPLE FILE: a fictional dry van owner-operator, Ridgeline Freight, with 35 loads, "
                      "12 fill-ups and 3 months of P&L (September to November 2026). Use the blank file for your own numbers.",
                      tint=POS_TINT, height=34, size=10, color=POS, bold=True)
        ws.print_area = f"A1:G{r + 1}"
        self.rows["start_end"] = r + 1
        self.protect(ws)

    # ============================================================ build
    def build(self):
        self.build_settings()
        self.build_check()
        self.build_compare()
        self.build_trips()
        self.build_fuel()
        self.build_pnl()
        self.build_dashboard()
        self.build_start()
        self.wb.active = 0
        for ws in self.wb.worksheets:
            ws.sheet_view.tabSelected = ws.title == S_START
        self.wb.calculation.fullCalcOnLoad = True
        p = self.wb.properties
        p.title, p.creator, p.subject = self.cfg.PRODUCT_LONG, "Brass Ledger", "Simple tools for small business numbers."
        return self.wb

    def add_sidebars(self):
        return BP.add_sidebars(self.wb, NAV, {S_START: self.rows["start_end"] + 2, S_SET: self.rows["set_last"] + 2,
                                              S_CMP: 60, S_TRIP: 120, S_FUEL: 120, S_PNL: 90, S_DASH: 70},
                               skip=(S_CHECK,), max_last=200)


def main(cfg, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for sample in (False, True):
        e = TruckEngine(cfg, sample)
        wb = e.build()
        layers = e.add_sidebars()
        p = out_dir / (cfg.OUT_NAME + ("_SAMPLE" if sample else "") + ".xlsx")
        wb.save(p)
        BP.finish(p, layers)
        paths.append(p)
        print("wrote", p)
    return paths
