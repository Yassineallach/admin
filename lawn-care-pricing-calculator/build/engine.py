"""Brass Ledger service pricing engine: builds a quote-calculator workbook from a trade config.

Reusable parts (any trade that prices a job from an area, a production rate and multipliers):
  SETTINGS        business details, pricing targets, fuel and vehicle, equipment, overhead, cost per working hour,
                  production methods (sq ft per hour + fuel), time multipliers, detail tasks, an optional extra,
                  add-on price list, dropdown lists
  QUICK QUOTE     area -> time on site -> cost per visit -> price per visit, monthly, season, add-ons, warnings,
                  plus a values-ready row to copy into the quote log
  CUSTOMER QUOTE  one printable page with the USER's business identity only
  QUOTE LOG       300 rows, win rate and price per 1,000 sq ft for accepted vs declined quotes
  ROUTE PLANNER   recurring clients by weekday, revenue per hour, drive-time share
  SEASON TRACKER  12 months of revenue against a goal
  DASHBOARD       tiles and three charts

The trade config (e.g. lawn_config.py) supplies names, defaults and sample data. Every number the formulas use lives
on SETTINGS; nothing is hardcoded in the other tabs.

No macros, no Excel Tables, no dynamic arrays, no TEXT() date codes: works in Excel 2016+ and Google Sheets.
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.series import DataPoint
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

from xlkit import (BORDER, BOX, BRASS, BRASS_TINT, CALC, GREEN, GREEN2, GREY, INK, INK2, Kit, NEG, NEG_TINT,  # noqa: E402
                   PAPER, POS, POS_TINT, TITLE, WHITE, fill, font, q)

MONEY = "#,##0.00"
MONEY0 = "#,##0"
PCT = "0.0%"
SQFT = "#,##0"
ACRES = "0.00"
MINS = '#,##0.0" min"'
HRS = '0.00" h"'
DATE = "mmm d, yyyy"
NUM = "#,##0.00"

S_START, S_SET, S_QQ, S_CQ, S_LOG, S_ROUTE, S_SEASON, S_DASH = (
    "START HERE", "SETTINGS", "QUICK QUOTE", "CUSTOMER QUOTE", "QUOTE LOG", "ROUTE PLANNER", "SEASON TRACKER", "DASHBOARD")
ORDER = [S_START, S_SET, S_QQ, S_CQ, S_LOG, S_ROUTE, S_SEASON, S_DASH]
NAV = [(S_DASH, "bar_chart", "Home"), (S_START, "question", "Start"), (S_SET, "gear", "Setup"), (S_QQ, "calc", "Quote"),
       (S_CQ, "receipt", "Customer"), (S_LOG, "clipboard", "Log"), (S_ROUTE, "pin", "Routes"),
       (S_SEASON, "calendar", "Season")]
DISCLAIMER = ("Prices are estimates based on the numbers you enter. Adjust to your local market. "
              "Not financial, legal or tax advice.")

LOG_FIRST, LOG_N = 8, 300
LOG_LAST = LOG_FIRST + LOG_N - 1
RT_FIRST, RT_N = 8, 100
RT_LAST = RT_FIRST + RT_N - 1
ADD_N = 6                                     # add-on lines on a quote
CUST = "Arial"                                # neutral font for the customer-facing page


class Engine(Kit):
    def __init__(self, cfg, sample: bool):
        self.cfg = cfg
        self.product = cfg.PRODUCT
        self.sample = sample
        self.home_tab, self.start_tab = S_DASH, S_START
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in ORDER}
        self.S = {}           # settings name -> absolute reference
        self.Q = {}           # quick quote name -> absolute reference
        self.rows = {}        # anchors other scripts use (screenshots, tests)

    # ------------------------------------------------------------ helpers
    def dv_list(self, ws, rng, source, title="Pick from the list"):
        v = DataValidation(type="list", formula1=source, allow_blank=True, showErrorMessage=True, errorTitle=title,
                           error="Pick a value from the dropdown list.")
        ws.add_data_validation(v)
        v.add(rng)

    def dv_num(self, ws, rng, kind="decimal", lo=0, hi=1e9, title="Number", msg="Enter a number of 0 or more."):
        v = DataValidation(type=kind, operator="between", formula1=str(lo), formula2=str(hi), allow_blank=True,
                           showErrorMessage=True, errorTitle=title, error=msg)
        ws.add_data_validation(v)
        v.add(rng)

    def sref(self, key):
        return self.S[key]

    def note_cell(self, ws, rng, text, size=9, color=INK2, bold=False):
        ws.merge_cells(rng)
        c = ws[rng.split(":")[0]]
        c.value = text
        c.font = font(size, bold, color)
        c.alignment = Alignment(vertical="center", wrap_text=True, indent=1)

    def cur(self, expr):
        """Money as text with the currency symbol from SETTINGS (for tiles and the customer quote)."""
        return f'{self.S["currency"]}&FIXED({expr},2)'

    # ============================================================ SETTINGS
    def build_settings(self):
        c = self.cfg
        ws = self.ws[S_SET]
        SQ = q(S_SET)
        widths = {"B": 40, "C": 16, "D": 14, "E": 14, "F": 16, "G": 16, "H": 44}
        self.page(ws, widths, 8, 200, "Settings", "Your costs, rates and price list. Every other tab reads from here.")
        self.note(ws, "B4:H4", "EXAMPLE VALUES: adjust every white cell to your area and equipment. Rates and prices "
                  "below are typical US figures, not advice.", height=30, size=10, color=INK, bold=True)
        S = self.S
        b = c.BUSINESS if self.sample else {}

        def field(r, key, label, value, fmt=None, note="", wide=False, calc=None):
            self.label(ws[f"B{r}"], label, bold=False)
            cell = ws[f"C{r}"]
            if calc is not None:
                self.calc(cell, fmt, bold=True, align="right", value=calc)
            else:
                self.inp(cell, fmt, "right" if fmt else None, value=value)
            if wide:
                ws.merge_cells(f"C{r}:F{r}")
                for col in "DEF":
                    self.inp(ws[f"{col}{r}"])
                if note:
                    self.label(ws[f"G{r}"], note, bold=False, color=INK2, size=9, indent=1)
                    ws.merge_cells(f"G{r}:H{r}")
            elif note:
                self.label(ws[f"D{r}"], note, bold=False, color=INK2, size=9, indent=1)
                ws.merge_cells(f"D{r}:H{r}")
            ws.row_dimensions[r].height = 20
            S[key] = f"{SQ}!$C${r}"
            return cell

        r = 6
        self.kicker(ws, f"B{r}", "Your business  ·  shown on the customer quote", rule_to=8)
        r += 1
        for key, label in [("name", "Business name"), ("contact", "Contact name"), ("phone", "Phone"), ("email", "Email"),
                           ("website", "Website"), ("street", "Street address"), ("city", "City, state, ZIP")]:
            field(r, key, label, b.get(key), wide=True)
            r += 1
        field(r, "currency", "Currency symbol", c.TARGETS["currency"], note="Shown before prices on the quote and tiles.")
        ws[f"C{r}"].alignment = Alignment(horizontal="center", vertical="center")
        r += 1
        field(r, "valid_days", "Quote valid for (days)", c.TARGETS["valid_days"], "0", "Sets the valid-until date on the quote.")
        r += 1
        self.label(ws[f"B{r}"], "Quote terms", bold=False)
        ws.merge_cells(f"C{r}:H{r}")
        self.inp(ws[f"C{r}"], value=c.TERMS)
        ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="top", indent=1)
        for col in "DEFGH":
            self.inp(ws[f"{col}{r}"])
        ws.row_dimensions[r].height = 48
        S["terms"] = f"{SQ}!$C${r}"
        r += 2

        T = c.TARGETS
        self.kicker(ws, f"B{r}", "Pricing targets", rule_to=8)
        r += 1
        rows = [("hours", "Working hours per year (on site and driving)", T["hours"], "#,##0",
                 "Example: 30-week season x 40 hours. Used to spread equipment and overhead."),
                ("owner_pay", "Your target pay per hour", T["owner_pay"], MONEY, "What you want to earn for your own time."),
                ("helper_wage", "Helper wage per hour", T["helper_wage"], MONEY, "Only used when crew size is 2 or more."),
                ("payroll", "Payroll costs on helper wages", T["payroll"], PCT,
                 "Employer taxes, workers' comp. Check with your accountant."),
                ("margin", "Target profit margin", T["margin"], PCT, "Share of the price kept as profit, after paying yourself."),
                ("target_profit_hr", "Target profit per job hour", T["target_profit_hr"], MONEY,
                 "Quick Quote warns when a job earns less than this."),
                ("min_charge", "Minimum job charge", T["min_charge"], MONEY, "No visit is priced below this."),
                ("rounding", "Round prices up to the nearest", T["rounding"], MONEY0, "Example: 5 rounds 47.20 up to 50."),
                ("season_weeks", "Season length (weeks)", T["season_weeks"], "0", "Visits in a season contract."),
                ("prepay", "Discount for paying the season in advance", T["prepay"], PCT, "0 % if you don't offer it."),
                ("crew_loss", "Crew efficiency loss per extra person", T["crew_loss"], PCT,
                 "Two people are a bit less than twice as fast."),
                ("drive_warn", "Driving share that triggers a warning", T["drive_warn"], PCT,
                 "Used on ROUTE PLANNER."),
                ("season_year", "Season year", c.SEASON_YEAR if self.sample else None, "0", "For revenue year to date."),
                ("season_start", "First month of the mowing season", T["season_start"], None, "Months outside the season have no goal."),
                ("season_end", "Last month of the season", T["season_end"], None, ""),
                ("monthly_goal", "Monthly revenue goal (in season)", T["monthly_goal"], MONEY0, "Used on SEASON TRACKER.")]
        for key, label, val, fmt, note in rows:
            field(r, key, label, val, fmt, note)
            r += 1
        if not self.sample:
            ws[S["season_year"].split("!")[1].replace("$", "")].value = "=YEAR(TODAY())"
        r += 1
        F = c.FUEL
        self.kicker(ws, f"B{r}", "Fuel and vehicle", rule_to=8)
        r += 1
        field(r, "fuel_price", "Fuel price per gallon", F["fuel_price"], MONEY, "Check your local pump price.")
        r += 1
        field(r, "mpg", "Truck miles per gallon (towing the trailer)", F["mpg"], "0.0", "")
        r += 1
        field(r, "wear_mile", "Truck wear per mile (repairs, tyres)", F["wear_mile"], MONEY,
              "Everything except fuel.")
        r += 1
        field(r, "vehicle_mile", "Vehicle cost per mile", None, MONEY, "Fuel ÷ miles per gallon + wear per mile.",
              calc=f'=IF(N({S["mpg"]})=0,0,N({S["fuel_price"]})/{S["mpg"]})+N({S["wear_mile"]})')
        r += 2

        # ---- equipment
        self.kicker(ws, f"B{r}", "Equipment", rule_to=8)
        r += 1
        for col, t in zip("BCDEF", ["Item", "Purchase price", "Life (years)", "Yearly maintenance", "Cost per year"]):
            self.header(ws[f"{col}{r}"], t, GREEN2 if col == "F" else GREEN, align="left" if col == "B" else "center")
        self.label(ws[f"G{r}"], "Cost per year = price ÷ life + maintenance", bold=False, color=INK2, size=9, indent=1)
        ws.merge_cells(f"G{r}:H{r}")
        ws.row_dimensions[r].height = 30
        r += 1
        e1 = r
        for i in range(15):
            row = c.EQUIPMENT[i] if i < len(c.EQUIPMENT) else (None, None, None, None)
            self.inp(ws[f"B{r}"], value=row[0])
            self.inp(ws[f"C{r}"], MONEY, value=row[1])
            self.inp(ws[f"D{r}"], "0", "center", value=row[2])
            self.inp(ws[f"E{r}"], MONEY, value=row[3])
            self.calc(ws[f"F{r}"], MONEY, value=f'=IF(AND(C{r}="",E{r}=""),"",IF(N(D{r})>0,N(C{r})/D{r},N(C{r}))+N(E{r}))')
            r += 1
        e2 = r - 1
        self.dv_num(ws, f"C{e1}:C{e2}")
        self.dv_num(ws, f"E{e1}:E{e2}")
        self.dv_num(ws, f"D{e1}:D{e2}", "decimal", 0, 50, "Life", "Enter the expected life in years.")
        self.total_row(ws, r, "Equipment cost per year", "F", f"=SUM(F{e1}:F{e2})", MONEY, "BCDEF")
        S["equip_year"] = f"{SQ}!$F${r}"
        r += 2

        # ---- overhead
        self.kicker(ws, f"B{r}", "Overhead (yearly)", rule_to=8)
        r += 1
        for col, t in zip("BC", ["Item", "Cost per year"]):
            self.header(ws[f"{col}{r}"], t, align="left" if col == "B" else "center")
        ws.row_dimensions[r].height = 24
        r += 1
        o1 = r
        for i in range(10):
            row = c.OVERHEAD[i] if i < len(c.OVERHEAD) else (None, None)
            self.inp(ws[f"B{r}"], value=row[0])
            self.inp(ws[f"C{r}"], MONEY, value=row[1])
            r += 1
        o2 = r - 1
        self.dv_num(ws, f"C{o1}:C{o2}")
        self.total_row(ws, r, "Overhead per year", "C", f"=SUM(C{o1}:C{o2})", MONEY, "BC")
        S["over_year"] = f"{SQ}!$C${r}"
        r += 2

        # ---- cost per hour
        self.kicker(ws, f"B{r}", "Cost per working hour  ·  calculated", rule_to=8)
        r += 1
        H = S["hours"]
        blocks = [("equip_hr", "Equipment cost per hour", f'=IF(N({H})=0,0,{S["equip_year"]}/{H})', "Equipment per year ÷ working hours."),
                  ("over_hr", "Overhead per hour", f'=IF(N({H})=0,0,{S["over_year"]}/{H})', "Overhead per year ÷ working hours."),
                  ("running_hr", "Total running cost per working hour", None, "Equipment + overhead, before your pay."),
                  ("breakeven_hr", "Break-even hourly rate (solo)", None, "Running cost + your target pay. Charge less and you pay yourself less."),
                  ("target_hr", "Hourly rate at your target margin", None, "Break-even ÷ (1 − target margin).")]
        for key, label, f, note in blocks:
            field(r, key, label, None, MONEY, note, calc=f or "=0")
            r += 1
        cell = lambda k: S[k].split("!")[1].replace("$", "")
        ws[cell("running_hr")] = f'={S["equip_hr"]}+{S["over_hr"]}'
        ws[cell("breakeven_hr")] = f'={S["running_hr"]}+N({S["owner_pay"]})'
        ws[cell("target_hr")] = f'=IF(N({S["margin"]})>=1,"",{S["breakeven_hr"]}/(1-N({S["margin"]})))'
        for k in ("breakeven_hr",):
            x = ws[cell(k)]
            x.fill, x.font = fill(GREEN), font(11, True, BRASS)
            ws[f"B{x.row}"].font = font(10, True, GREEN)
        self.rows["cost_hr"] = r - 5
        r += 1

        # ---- methods
        self.kicker(ws, f"B{r}", f"{c.METHOD_LABEL}s and speed", rule_to=8)
        r += 1
        for col, t in zip("BCDE", [c.METHOD_LABEL, c.RATE_LABEL, "Acres per hour", c.FUEL_LABEL]):
            self.header(ws[f"{col}{r}"], t, GREEN2 if col == "D" else GREEN, align="left" if col == "B" else "center")
        self.label(ws[f"F{r}"], "Speed = typical mph × deck inches ÷ 99 acres per hour, times about 50-60 % on home "
                   "lawns for turns and overlap. Time yourself and adjust.", bold=False, color=INK2, size=9, indent=1, wrap=True)
        ws.merge_cells(f"F{r}:H{r}")
        ws.row_dimensions[r].height = 40
        r += 1
        m1 = r
        for i in range(8):
            row = c.METHODS[i] if i < len(c.METHODS) else (None, None, None)
            self.inp(ws[f"B{r}"], value=row[0])
            self.inp(ws[f"C{r}"], SQFT, value=row[1])
            self.calc(ws[f"D{r}"], ACRES, value=f'=IF(N(C{r})=0,"",C{r}/43560)')
            self.inp(ws[f"E{r}"], "0.00", value=row[2])
            r += 1
        m2 = r - 1
        self.dv_num(ws, f"C{m1}:C{m2}", "decimal", 0, 1e7)
        self.dv_num(ws, f"E{m1}:E{m2}", "decimal", 0, 20)
        S["methods"] = f"{SQ}!$B${m1}:$B${m2}"
        S["rates"] = f"{SQ}!$C${m1}:$C${m2}"
        S["fuel_use"] = f"{SQ}!$E${m1}:$E${m2}"
        r += 1

        # ---- multipliers
        self.kicker(ws, f"B{r}", "Time multipliers", rule_to=8)
        r += 1
        for col, t in zip("BCD", ["Factor", "Option", "Multiplier"]):
            self.header(ws[f"{col}{r}"], t, align="left" if col != "D" else "center")
        self.label(ws[f"E{r}"], f"1.00 = normal. 1.15 = 15 % more {c.SERVICE.lower()} time.", bold=False, color=INK2, size=9, indent=1)
        ws.merge_cells(f"E{r}:H{r}")
        ws.row_dimensions[r].height = 24
        r += 1
        S["mult_groups"] = []
        for g, (gname, opts) in enumerate(c.MULTIPLIERS):
            g1 = r
            for k, (oname, val) in enumerate(opts):
                self.label(ws[f"B{r}"], gname if k == 0 else "", bold=True)
                self.inp(ws[f"C{r}"], value=oname)
                self.inp(ws[f"D{r}"], "0.00", "center", value=val)
                r += 1
            S["mult_groups"].append((gname, f"{SQ}!$C${g1}:$C${r - 1}", f"{SQ}!$D${g1}:$D${r - 1}"))
            self.dv_num(ws, f"D{g1}:D{r - 1}", "decimal", 0.1, 10, "Multiplier", "Enter a multiplier such as 1.15.")
        r += 1

        # ---- detail tasks
        self.kicker(ws, f"B{r}", "Detail work per visit", rule_to=8)
        r += 1
        for col, t in zip("BCD", ["Task", "Minutes per 1,000 sq ft", "Minimum minutes"]):
            self.header(ws[f"{col}{r}"], t, align="left" if col == "B" else "center")
        self.label(ws[f"E{r}"], "Time = minutes per 1,000 sq ft × lawn area ÷ 1,000, but never less than the minimum. "
                   + ("Obstacles multiply this time too." if c.FIRST_MULT_ON_DETAIL else ""),
                   bold=False, color=INK2, size=9, indent=1, wrap=True)
        ws.merge_cells(f"E{r}:H{r}")
        ws.row_dimensions[r].height = 30
        r += 1
        S["tasks"] = []
        for name, per, mn, _desc in c.DETAIL_TASKS:
            self.label(ws[f"B{r}"], name, bold=True)
            self.inp(ws[f"C{r}"], "0.00", "center", value=per)
            self.inp(ws[f"D{r}"], "0", "center", value=mn)
            S["tasks"].append((f"{SQ}!$C${r}", f"{SQ}!$D${r}"))
            r += 1
        r += 1
        X = c.EXTRA
        self.kicker(ws, f"B{r}", X["label"], rule_to=8)
        r += 1
        field(r, "extra_mult", X["mult_label"], X["mult"], "0.00", f"Multiplies {c.SERVICE.lower()} time when chosen.")
        r += 1
        field(r, "extra_cost", X["cost_label"], X["cost"], MONEY, "Dump fees, bags.")
        r += 2

        # ---- add-ons
        self.kicker(ws, f"B{r}", "Add-on services price list", rule_to=8)
        r += 1
        for col, t in zip("BCDE", ["Service", "Unit", "Price per unit", "Notes"]):
            self.header(ws[f"{col}{r}"], t, align="left" if col in "BE" else "center")
        ws.merge_cells(f"E{r}:H{r}")
        ws.row_dimensions[r].height = 24
        r += 1
        a1 = r
        for i in range(12):
            row = c.ADDONS[i] if i < len(c.ADDONS) else (None, None, None, None)
            self.inp(ws[f"B{r}"], value=row[0])
            self.inp(ws[f"C{r}"], value=row[1])
            self.inp(ws[f"D{r}"], MONEY, value=row[2])
            self.inp(ws[f"E{r}"], value=row[3] or None)
            ws.merge_cells(f"E{r}:H{r}")
            for col in "FGH":
                self.inp(ws[f"{col}{r}"])
            r += 1
        a2 = r - 1
        S["addon_names"], S["addon_units"], S["addon_prices"] = (f"{SQ}!$B${a1}:$B${a2}", f"{SQ}!$C${a1}:$C${a2}",
                                                                 f"{SQ}!$D${a1}:$D${a2}")
        self.dv_num(ws, f"D{a1}:D{a2}")
        self.note(ws, f"B{r}:H{r}", c.LICENCE_NOTE, height=30, size=9, color=NEG, bold=True)
        ws[f"B{r}"].fill = fill(NEG_TINT)
        for col in "CDEFGH":
            ws[f"{col}{r}"].fill = fill(NEG_TINT)
        r += 2

        # ---- frequencies (calculated) and lists
        self.kicker(ws, f"B{r}", "Visit frequency  ·  calculated", rule_to=8)
        r += 1
        for col, t in zip("BCDE", ["Frequency", "Visits per month", "Visits per week", "Visits per season"]):
            self.header(ws[f"{col}{r}"], t, align="left" if col == "B" else "center")
        ws.row_dimensions[r].height = 24
        r += 1
        f1 = r
        W = S["season_weeks"]
        per_month = {"Weekly": "=52/12", "Bi-weekly": "=26/12", "Monthly": "=1", "One-time": "=0"}
        per_season = {"Weekly": f"=N({W})", "Bi-weekly": f"=ROUNDUP(N({W})/2,0)", "Monthly": f"=ROUND(N({W})*12/52,0)",
                      "One-time": "=1"}
        for name in c.FREQS:
            self.label(ws[f"B{r}"], name, bold=True)
            self.calc(ws[f"C{r}"], "0.000", align="center", value=per_month[name])
            self.calc(ws[f"D{r}"], "0.000", align="center", value=f"=C{r}*12/52")
            self.calc(ws[f"E{r}"], "0", align="center", value=per_season[name])
            r += 1
        self.label(ws[f"F{f1}"], "Weekly = 52 ÷ 12 visits a month; bi-weekly = 26 ÷ 12.", bold=False, color=INK2, size=9, indent=1)
        ws.merge_cells(f"F{f1}:H{f1}")
        S["freqs"], S["fpm"], S["fpw"], S["fps"] = (f"{SQ}!$B${f1}:$B${r - 1}", f"{SQ}!$C${f1}:$C${r - 1}",
                                                     f"{SQ}!$D${f1}:$D${r - 1}", f"{SQ}!$E${f1}:$E${r - 1}")
        r += 1
        self.kicker(ws, f"B{r}", "Dropdown lists", rule_to=8)
        r += 1
        lists = [("B", "Units", c.UNITS, "units"), ("C", "Yes / No", ["Yes", "No"], "yesno"),
                 ("D", "Quote status", c.STATUSES, "statuses"), ("E", "Weekdays", c.WEEKDAYS, "weekdays"),
                 ("F", "Months", c.MONTHS, "months")]
        for col, head, items, key in lists:
            self.header(ws[f"{col}{r}"], head, align="left")
            for i, it in enumerate(items):
                x = ws[f"{col}{r + 1 + i}"]
                self.sysval(x, it)
            S[key] = f"{SQ}!${col}${r + 1}:${col}${r + len(items)}"
        last = r + 12
        self.dv_list(ws, f"C{a1}:C{a2}", f"={S['units']}")
        for key in ("season_start", "season_end"):
            self.dv_list(ws, S[key].split("!")[1].replace("$", ""), f"={S['months']}")
        for key in ("hours", "owner_pay", "helper_wage", "min_charge", "rounding", "season_weeks", "fuel_price", "mpg",
                    "wear_mile", "monthly_goal", "valid_days", "extra_cost"):
            self.dv_num(ws, S[key].split("!")[1].replace("$", ""))
        for key in ("payroll", "prepay", "crew_loss", "drive_warn"):
            self.dv_num(ws, S[key].split("!")[1].replace("$", ""), "decimal", 0, 1, "Percent", "Enter a percentage, e.g. 10%.")
        self.dv_num(ws, S["margin"].split("!")[1].replace("$", ""), "decimal", 0, 0.9, "Margin", "Enter 0% to 90%.")
        self.dv_num(ws, S["extra_mult"].split("!")[1].replace("$", ""), "decimal", 0.1, 10)
        ws.freeze_panes = "A4"
        ws.print_area = f"A1:H{last}"
        self.protect(ws)
        self.rows["set_last"] = last

    def total_row(self, ws, r, label, col, formula, fmt, cols):
        ws[f"B{r}"] = label
        ws[f"{col}{r}"] = formula
        for cc in cols:
            x = ws[f"{cc}{r}"]
            x.fill = fill(GREEN)
            x.font = font(10, True, PAPER if cc == "B" else BRASS)
            x.number_format = fmt
            x.alignment = Alignment(vertical="center", indent=1 if cc == "B" else 0, horizontal="left" if cc == "B" else None)
        ws.row_dimensions[r].height = 22

    # ============================================================ QUICK QUOTE
    def build_quote(self):
        c, S, Q = self.cfg, self.S, self.Q
        ws = self.ws[S_QQ]
        QQ = q(S_QQ)
        widths = {"B": 36, "C": 15, "D": 22, "E": 18, "F": 40, "G": 16, "H": 20, "I": 17, "K": 10, "L": 10}
        self.page(ws, widths, 9, 60, "Quick quote", "Fill the white cells from top to bottom. The price builds on the right.")
        for col in ("K", "L"):
            ws.column_dimensions[col].hidden = True

        def inrow(r, key, label, fmt=None, wide=False, align=None, hint=""):
            self.label(ws[f"B{r}"], label, bold=False)
            cell = ws[f"C{r}"]
            self.inp(cell, fmt, align or ("right" if fmt else None))
            if wide:
                ws.merge_cells(f"C{r}:E{r}")
                for col in "DE":
                    self.inp(ws[f"{col}{r}"])
            elif hint:
                self.label(ws[f"D{r}"], hint, bold=False, color=INK2, size=9, indent=1)
                ws.merge_cells(f"D{r}:E{r}")
            ws.row_dimensions[r].height = 20
            Q[key] = f"$C${r}"
            return cell

        r = 4
        self.kicker(ws, f"B{r}", "1  ·  Client", rule_to=5)
        self.note(ws, "B5:E6", "Work down the white cells. Dropdowns come from SETTINGS. The price, cost breakdown and "
                  "warnings update on the right as you type.", tint=PAPER, size=9)
        r += 3
        inrow(r, "date", "Quote date", DATE, align="center")
        r += 1
        inrow(r, "number", "Quote number (optional)", align="center")
        r += 1
        inrow(r, "client", "Client name", wide=True)
        r += 1
        inrow(r, "address", "Address", wide=True)
        r += 2
        self.kicker(ws, f"B{r}", "2  ·  " + c.AREA_LABEL, rule_to=5)
        r += 1
        inrow(r, "sqft", f"{c.AREA_LABEL} (sq ft)", SQFT, hint="Or enter acres below.")
        r += 1
        inrow(r, "acres", "Or acres", ACRES, hint="1 acre = 43,560 sq ft.")
        r += 1
        self.label(ws[f"B{r}"], "Area used", bold=True)
        self.calc(ws[f"C{r}"], SQFT, bold=True, align="right",
                  value=f'=IF(N({Q["sqft"]})>0,{Q["sqft"]},IF(N({Q["acres"]})>0,ROUND({Q["acres"]}*43560,0),0))')
        Q["area"] = f"$C${r}"
        self.calc(ws[f"D{r}"], '0.00" acres"', align="right", value=f"=C{r}/43560")
        ws.row_dimensions[r].height = 20
        r += 1
        inrow(r, "method", c.METHOD_LABEL, wide=True)
        self.dv_list(ws, Q["method"].replace("$", ""), f"={S['methods']}")
        r += 1
        Q["mults"] = []
        for gname, opts, _vals in S["mult_groups"]:
            inrow(r, f"mult_{gname}", gname, wide=True)
            self.dv_list(ws, f"C{r}", f"={opts}")
            Q["mults"].append(f"$C${r}")
            r += 1
        Q["tasks"] = []
        for name, *_ in c.DETAIL_TASKS:
            inrow(r, f"task_{name}", name, align="center")
            self.dv_list(ws, f"C{r}", f"={S['yesno']}")
            Q["tasks"].append(f"$C${r}")
            r += 1
        inrow(r, "extra", c.EXTRA["label"], align="center")
        self.dv_list(ws, f"C{r}", f"={S['yesno']}")
        r += 2
        self.kicker(ws, f"B{r}", "3  ·  Crew and travel", rule_to=5)
        r += 1
        inrow(r, "crew", "Crew size (people on site)", "0", align="center", hint="1 = you alone.")
        self.dv_num(ws, f"C{r}", "whole", 1, 6, "Crew", "Enter 1 to 6 people.")
        r += 1
        inrow(r, "drive", "Drive time to the property (minutes)", "0", align="center", hint="From the previous job.")
        self.dv_num(ws, f"C{r}", "decimal", 0, 600)
        r += 1
        inrow(r, "miles", "Miles driven for this visit", "0.0", align="center")
        self.dv_num(ws, f"C{r}", "decimal", 0, 1000)
        r += 2
        self.kicker(ws, f"B{r}", "4  ·  Frequency and price checks", rule_to=5)
        r += 1
        inrow(r, "freq", "Frequency", wide=True)
        self.dv_list(ws, f"C{r}", f"={S['freqs']}")
        r += 1
        inrow(r, "going", "Local going rate per visit (optional)", MONEY, hint="What you think others charge.")
        self.dv_num(ws, f"C{r}")
        r += 1
        inrow(r, "override", "Your own price per visit (optional)", MONEY, hint="Blank = calculated price.")
        self.dv_num(ws, f"C{r}")
        r += 2
        self.kicker(ws, f"B{r}", "5  ·  Add-on services (one-time)", rule_to=5)
        r += 1
        for col, t in zip("BCDE", ["Add-on", "Quantity", "Unit", "Total"]):
            self.header(ws[f"{col}{r}"], t, GREEN2 if col in "DE" else GREEN, align="left" if col == "B" else "center")
        ws.row_dimensions[r].height = 22
        r += 1
        ad1 = r
        A = Q["area"]
        for i in range(ADD_N):
            self.inp(ws[f"B{r}"])
            self.inp(ws[f"C{r}"], "#,##0.0", "center")
            self.calc(ws[f"D{r}"], align="center",
                      value=f'=IF(B{r}="","",IFERROR(INDEX({S["addon_units"]},MATCH(B{r},{S["addon_names"]},0)),""))')
            # hidden helpers: quantity used (auto for flat and per 1,000 sq ft) and unit price
            ws[f"K{r}"] = (f'=IF(B{r}="","",IF(N(C{r})>0,C{r},IF(D{r}="per 1,000 sq ft",ROUND({A}/1000,1),'
                           f'IF(D{r}="flat",1,""))))')
            ws[f"L{r}"] = f'=IF(B{r}="","",IFERROR(INDEX({S["addon_prices"]},MATCH(B{r},{S["addon_names"]},0)),0))'
            self.calc(ws[f"E{r}"], MONEY, align="right",
                      value=f'=IF(B{r}="","",IF(K{r}="","enter qty",ROUND(K{r}*L{r},2)))')
            r += 1
        ad2 = r - 1
        self.dv_list(ws, f"B{ad1}:B{ad2}", f"={S['addon_names']}")
        self.dv_num(ws, f"C{ad1}:C{ad2}", "decimal", 0, 1e6)
        Q["ad1"], Q["ad2"] = ad1, ad2
        self.note(ws, f"B{r}:E{r}", "Leave Quantity blank for flat prices and per 1,000 sq ft (the lawn area is used). "
                  "Enter hours, cubic yards or bags for the rest.", tint=PAPER, height=30)
        left_end = r

        # ---------------- results
        def out(r, key, label, f, fmt, bold=False, note=""):
            self.label(ws[f"F{r}"], label, bold=bold, indent=1)
            self.calc(ws[f"G{r}"], fmt, bold=bold, align="right", value=f)
            if note is not None and note != "":
                ws[f"H{r}"] = note
                ws[f"H{r}"].font = font(9, False, INK2)
                ws[f"H{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            Q[key] = f"$G${r}"
            ws.row_dimensions[r].height = 20

        self.kicker(ws, "F4", "Result", rule_to=8)
        self.rows["tiles"] = 5
        r = 8
        self.kicker(ws, f"F{r}", "Time on site", rule_to=8)
        r += 1
        cv = lambda k: Q[k]
        mi = [f"IFERROR(INDEX({vals},MATCH({cell},{opts},0)),1)" for (g, opts, vals), cell in zip(S["mult_groups"], Q["mults"])]
        mult_all = "*".join(mi)
        mult_first = mi[0] if c.FIRST_MULT_ON_DETAIL else "1"
        rate = f'IFERROR(INDEX({S["rates"]},MATCH({cv("method")},{S["methods"]},0)),0)'
        extra = f'IF({cv("extra")}="Yes",N({S["extra_mult"]}),1)'
        out(r, "mow", f"{c.SERVICE} (one person)",
            f'=IF(OR({A}=0,N({rate})=0),0,{A}/{rate}*60*{mult_all}*{extra})', MINS)
        r += 1
        parts = [f'IF({t}="Yes",MAX(N({mn}),N({per})*{A}/1000),0)' for t, (per, mn) in zip(Q["tasks"], S["tasks"])]
        names = ", ".join(n.lower() for n, *_ in c.DETAIL_TASKS)
        out(r, "detail", f"{names[0].upper() + names[1:]}", f'=IF({A}=0,0,({"+".join(parts)})*{mult_first})', MINS)
        r += 1
        out(r, "work", "Total work, one person", f"={cv('mow')}+{cv('detail')}", MINS, bold=True)
        r += 1
        crew = f"MAX(1,N({cv('crew')}))"
        out(r, "onsite", "On site with your crew", f"={cv('work')}*(1+N({S['crew_loss']})*({crew}-1))/{crew}", MINS,
            note="Crew shares the work.")
        r += 1
        out(r, "drive_min", "Driving", f"=N({cv('drive')})", MINS)
        r += 1
        out(r, "job_hours", "Total job time", f"=({cv('onsite')}+{cv('drive_min')})/60", HRS, bold=True)
        r += 2
        self.kicker(ws, f"F{r}", "Cost per visit", rule_to=8)
        r += 1
        lab_rate = f"(N({S['owner_pay']})+({crew}-1)*N({S['helper_wage']})*(1+N({S['payroll']})))"
        Q["lab_rate"] = lab_rate
        fuel_use = f'IFERROR(INDEX({S["fuel_use"]},MATCH({cv("method")},{S["methods"]},0)),0)'
        rows = [("c_lab", "Labour on site", f"={cv('onsite')}/60*{lab_rate}", "Your pay + helpers."),
                ("c_eq", "Equipment", f"={cv('job_hours')}*{S['equip_hr']}", "Per job hour."),
                ("c_ov", "Overhead", f"={cv('job_hours')}*{S['over_hr']}", "Per job hour."),
                ("c_fuel", f"{c.METHOD_LABEL} fuel", f"={cv('mow')}/60*N({fuel_use})*N({S['fuel_price']})", ""),
                ("c_trav", "Travel (driving time + vehicle)",
                 f"={cv('drive_min')}/60*{lab_rate}+N({cv('miles')})*{S['vehicle_mile']}", ""),
                ("c_disp", "Disposal", f'=IF({cv("extra")}="Yes",N({S["extra_cost"]}),0)', "")]
        for key, label, f, note in rows:
            out(r, key, label, f, MONEY, note=note)
            r += 1
        out(r, "cost", "Cost per visit", f"=IF({A}=0,0,SUM(G{r - 6}:G{r - 1}))", MONEY, bold=True)
        for col in "FG":
            ws[f"{col}{r}"].fill = fill(GREEN)
        ws[f"F{r}"].font = font(10, True, PAPER)
        ws[f"G{r}"].font = font(11, True, BRASS)
        r += 2
        self.kicker(ws, f"F{r}", "Price", rule_to=8)
        r += 1
        inc, mg = f"N({S['rounding']})", f"N({S['margin']})"
        raw = f"{cv('cost')}/(1-{mg})"
        rounded = f"IF({inc}>0,ROUNDUP(ROUND({raw},6)/{inc},0)*{inc},ROUND({raw},2))"
        out(r, "calc_price", "Calculated price",
            f'=IF({A}=0,"",MAX(N({S["min_charge"]}),{rounded}))', MONEY)
        r += 1
        out(r, "price", "Price per visit", f'=IF({A}=0,"",IF(N({cv("override")})>0,{cv("override")},{cv("calc_price")}))',
            MONEY, bold=True)
        ws[f"H{r}"] = f'=IF({A}=0,"",IF(N({cv("override")})>0,"Your own price","Calculated"))'
        ws[f"H{r}"].font = font(9, False, INK2)
        ws[f"H{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        r += 1
        out(r, "profit", "Profit per visit", f'=IF({cv("price")}="","",{cv("price")}-{cv("cost")})', MONEY)
        r += 1
        out(r, "profit_hr", "Profit per job hour",
            f'=IF(OR({cv("price")}="",N({cv("job_hours")})=0),"",{cv("profit")}/{cv("job_hours")})', MONEY)
        ws[f"H{r}"] = f'="Target "&{self.cur(S["target_profit_hr"])}'
        ws[f"H{r}"].font = font(9, False, INK2)
        ws[f"H{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        r += 1
        out(r, "per1000", "Price per 1,000 sq ft", f'=IF({cv("price")}="","",{cv("price")}/{A}*1000)', MONEY)
        r += 1
        fidx = lambda rng: f'IFERROR(INDEX({rng},MATCH({cv("freq")},{S["freqs"]},0)),"")'
        out(r, "monthly", "Monthly price",
            f'=IF(OR({cv("price")}="",N({fidx(S["fpm"])})=0),"",ROUND({cv("price")}*{fidx(S["fpm"])},2))', MONEY)
        ws[f"H{r}"] = f'=IF({cv("monthly")}="","",FIXED({fidx(S["fpm"])},2)&" visits a month")'
        r += 1
        out(r, "season", "Season contract price",
            f'=IF(OR({cv("price")}="",{cv("freq")}="",{cv("freq")}="One-time"),"",{cv("price")}*{fidx(S["fps"])})', MONEY)
        ws[f"H{r}"] = f'=IF({cv("season")}="","",{fidx(S["fps"])}&" visits")'
        ws["K4"], ws["K5"] = f"=N({fidx(S['fpm'])})", f"=N({fidx(S['fps'])})"     # hidden helpers for the customer quote
        r += 1
        out(r, "prepaid", "Season contract, paid in advance",
            f'=IF({cv("season")}="","",ROUND({cv("season")}*(1-N({S["prepay"]})),2))', MONEY)
        ws[f"H{r}"] = f'=IF({cv("prepaid")}="","",FIXED(100*N({S["prepay"]}),0)&"% off")'
        r += 1
        out(r, "addons", "Add-ons total (one-time)", f'=SUM(E{ad1}:E{ad2})', MONEY)
        r += 1
        for rr in (r - 4, r - 3, r - 2):
            ws[f"H{rr}"].font = font(9, False, INK2)
            ws[f"H{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        self.label(ws[f"F{r}"], "Compared with the local going rate", bold=False, indent=1)
        ws.merge_cells(f"G{r}:H{r}")
        gr = cv("going")
        ws[f"G{r}"] = (f'=IF(OR({cv("price")}="",N({gr})=0),"No going rate entered",'
                       f'IF({cv("price")}>{gr},FIXED(100*({cv("price")}/{gr}-1),0)&"% above "&{self.cur(gr)},'
                       f'IF({cv("price")}<{gr},FIXED(100*(1-{cv("price")}/{gr}),0)&"% below "&{self.cur(gr)},"Same as the going rate")))')
        self.calc(ws[f"G{r}"], align="right")
        self.calc(ws[f"H{r}"])
        Q["vs_going"] = f"$G${r}"
        ws.row_dimensions[r].height = 20
        r += 2
        # warning box
        ws.merge_cells(f"F{r}:H{r + 1}")
        w = ws[f"F{r}"]
        P, C_, PH, T = cv("price"), cv("cost"), cv("profit_hr"), S["target_profit_hr"]
        w.value = (f'=IF({A}=0,"Enter the lawn area to see a price.",'
                   f'IF({P}<{C_},"BELOW BREAK-EVEN: the price is "&{self.cur(f"{C_}-{P}")}&" under your cost for this visit.",'
                   f'IF({PH}<N({T}),"LOW PROFIT: "&{self.cur(PH)}&" per job hour, below your target of "&{self.cur(T)}&".",'
                   f'"Priced for profit: "&{self.cur(PH)}&" profit per job hour on top of your own pay.")))')
        w.font = font(10, True, POS)
        w.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        for rr in (r, r + 1):
            for col in "FGH":
                ws[f"{col}{rr}"].fill = fill(POS_TINT)
            ws.row_dimensions[rr].height = 22
        rng = f"F{r}:H{r + 1}"
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'OR(LEFT($F${r},5)="BELOW",LEFT($F${r},3)="LOW")'],
                                                       font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT($F${r},5)="Enter"'],
                                                       font=Font(color=INK2, bold=True), fill=fill(BRASS_TINT)))
        Q["warning"] = f"$F${r}"
        right_end = r + 1
        # tiles (text with the currency symbol)
        self.tile(ws, 5, 6, 6, "PRICE PER VISIT", f'=IF({P}="","–",{self.cur(P)})', "General", size=20)
        self.tile(ws, 5, 7, 8, "PROFIT PER JOB HOUR", f'=IF({PH}="","–",{self.cur(PH)})', "General", size=20)
        ws.conditional_formatting.add("G6", FormulaRule(formula=[f'AND(ISNUMBER({PH}),{PH}<N({T}))'], font=Font(color="F2A79E")))

        # ---------------- save this quote
        r = max(left_end, right_end) + 2
        self.kicker(ws, f"B{r}", "Save this quote", rule_to=9)
        r += 1
        self.note(ws, f"B{r}:I{r}", "1. Select the green row below (B to I) and copy it.   2. On QUOTE LOG, click the first empty "
                  "Date cell.   3. Paste values only: Excel Ctrl+Alt+V then V (Mac: Cmd+Ctrl+V), Google Sheets "
                  "Ctrl+Shift+V.   4. Pick a status.", height=46, size=10, color=INK)
        r += 1
        heads = ["Date", "Client", "Address", "Lawn sq ft", "Frequency", "Price per visit", "Monthly price", "Add-ons total"]
        for i, t in enumerate(heads):
            self.header(ws[f"{L(2 + i)}{r}"], t)
        ws.row_dimensions[r].height = 22
        r += 1
        vals = [(f'=IF({cv("date")}="","",{cv("date")})', DATE), (f'=IF({cv("client")}="","",{cv("client")})', None),
                (f'=IF({cv("address")}="","",{cv("address")})', None), (f'=IF({A}=0,"",{A})', SQFT),
                (f'=IF({cv("freq")}="","",{cv("freq")})', None), (f"={P}", MONEY), (f"={cv('monthly')}", MONEY),
                (f'=IF({cv("addons")}=0,"",{cv("addons")})', MONEY)]
        for i, (f, fmt) in enumerate(vals):
            x = ws[f"{L(2 + i)}{r}"]
            self.calc(x, fmt, align="center" if i in (0, 3, 4) else None, value=f)
            x.fill = fill(POS_TINT)
            x.font = font(10, True, INK)
            x.alignment = Alignment(horizontal=x.alignment.horizontal, vertical="center", shrink_to_fit=True,
                                    indent=1 if i in (1, 2) else 0)
        ws.row_dimensions[r].height = 24
        self.rows["save"] = r
        ws.freeze_panes = "A4"
        ws.print_area = f"A1:I{r}"
        ws.page_setup.orientation = "landscape"
        self.protect(ws)
        if self.sample:
            d = c.QUOTE
            setv = lambda k, v: ws.__setitem__(Q[k].replace("$", ""), v)
            setv("date", d["date"]); setv("number", d["number"]); setv("client", d["client"]); setv("address", d["address"])
            setv("sqft", d["sqft"]); setv("acres", d["acres"]); setv("method", d["method"]); setv("extra", d["extra"])
            for cell, v in zip(Q["mults"], d["mults"]):
                ws[cell.replace("$", "")] = v
            for cell, v in zip(Q["tasks"], d["tasks"]):
                ws[cell.replace("$", "")] = v
            setv("crew", d["crew"]); setv("drive", d["drive"]); setv("miles", d["miles"]); setv("freq", d["freq"])
            setv("going", d["going"]); setv("override", d["override"])
            for i, (name, qty) in enumerate(d["addons"]):
                ws[f"B{ad1 + i}"] = name
                ws[f"C{ad1 + i}"] = qty
        else:
            ws[Q["date"].replace("$", "")] = "=TODAY()"
            ws[Q["method"].replace("$", "")] = c.METHODS[3][0]
            for cell, (g, opts) in zip(Q["mults"], c.MULTIPLIERS):
                ws[cell.replace("$", "")] = opts[0][0]
            for cell in Q["tasks"]:
                ws[cell.replace("$", "")] = "Yes"
            ws[Q["extra"].replace("$", "")] = "No"
            ws[Q["crew"].replace("$", "")] = 1
            ws[Q["freq"].replace("$", "")] = "Weekly"

    # ============================================================ CUSTOMER QUOTE
    def build_customer(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_CQ]
        Qr = lambda k: f"{q(S_QQ)}!{self.Q[k]}"
        widths = {"A": 2, "B": 30, "C": 11, "D": 11, "E": 14, "F": 14, "G": 17, "H": 3, "I": 44}
        for col, w in widths.items():
            ws.column_dimensions[col].width = w
        ws.sheet_view.showGridLines = False
        white = fill(WHITE)
        for r in range(1, 45):
            for col in range(1, 9):
                x = ws.cell(row=r, column=col)
                x.fill = white
                x.font = Font(name=CUST, size=10, color="222222")
        f = lambda size=10, bold=False, color="222222", italic=False: Font(name=CUST, size=size, bold=bold, color=color,
                                                                           italic=italic)
        line = Side(style="thin", color="BFBFBF")
        dark = Side(style="medium", color="222222")
        # logo placeholder
        ws.merge_cells("B2:B5")
        ws["B2"] = "Your logo here"
        ws["B2"].font = f(9, False, "9A9A9A", True)
        ws["B2"].alignment = Alignment(horizontal="center", vertical="center")
        dash = Side(style="dashed", color="BFBFBF")
        for r in range(2, 6):
            ws[f"B{r}"].border = Border(left=dash, right=dash, top=dash if r == 2 else None, bottom=dash if r == 5 else None)
        right = Alignment(horizontal="right", vertical="center")
        idn = [(2, f'=IF({S["name"]}="","Your business name",{S["name"]})', f(16, True)),
               (3, f'=IF({S["contact"]}="","",{S["contact"]})', f(10)),
               (4, f'={S["phone"]}&IF(AND({S["phone"]}<>"",{S["email"]}<>""),"  ·  ","")&{S["email"]}', f(10)),
               (5, f'={S["street"]}&IF(AND({S["street"]}<>"",{S["city"]}<>""),", ","")&{S["city"]}', f(10)),
               (6, f'=IF({S["website"]}="","",{S["website"]})', f(10, False, "555555"))]
        for r, formula, ft in idn:
            ws.merge_cells(f"C{r}:G{r}")
            ws[f"C{r}"] = formula
            ws[f"C{r}"].font = ft
            ws[f"C{r}"].alignment = right
        ws.row_dimensions[2].height = 26
        ws["B8"] = "QUOTE"
        ws["B8"].font = f(22, True)
        for col in "BCDEFG":
            ws[f"{col}8"].border = Border(bottom=dark)
        ws.row_dimensions[8].height = 34
        for col, lab in (("B", "Prepared for"), ("E", "Quote date"), ("F", "Valid until"), ("G", "Quote no.")):
            ws[f"{col}10"] = lab
            ws[f"{col}10"].font = f(8, True, "666666")
        ws["B11"] = f'=IF({Qr("client")}="","",{Qr("client")})'
        ws["B11"].font = f(11, True)
        ws["B12"] = f'=IF({Qr("address")}="","",{Qr("address")})'
        ws["E11"] = f'=IF({Qr("date")}="","",{Qr("date")})'
        ws["F11"] = f'=IF({Qr("date")}="","",{Qr("date")}+N({S["valid_days"]}))'
        ws["G11"] = f'=IF({Qr("number")}="","",{Qr("number")})'
        for col in "EF":
            ws[f"{col}11"].number_format = DATE
            ws[f"{col}11"].alignment = Alignment(horizontal="left")
        ws["G11"].alignment = Alignment(horizontal="left")
        # services
        def head(r, cols):
            for col, t, al in cols:
                ws[f"{col}{r}"] = t
                ws[f"{col}{r}"].font = f(9, True)
                ws[f"{col}{r}"].alignment = Alignment(horizontal=al, vertical="center")
            for col in "BCDEFG":
                ws[f"{col}{r}"].border = Border(bottom=dark)
                ws[f"{col}{r}"].fill = fill("F2F2F2")
            ws.row_dimensions[r].height = 22

        head(14, [("B", "Service", "left"), ("E", "Frequency", "left"), ("F", "", "right"), ("G", "Price", "right")])
        tasks = "".join(f'&IF({q(S_QQ)}!{cell}="Yes",", {desc}","")' for cell, (_n, _p, _m, desc) in zip(self.Q["tasks"], c.DETAIL_TASKS))
        desc = (f'=IF({Qr("price")}="","","{c.SERVICE_DESC}"{tasks}'
                f'&IF({Qr("extra")}="Yes",", {c.EXTRA["desc"]}",""))')
        P = Qr("price")
        cur = lambda e: f'{S["currency"]}&FIXED({e},2)'
        lines = [(15, desc, f'=IF({P}="","",{Qr("freq")})', f'=IF({P}="","","per visit")', f'=IF({P}="","",{cur(P)})'),
                 (16, f'=IF({Qr("monthly")}="","","Monthly price, averaged ("&FIXED({q(S_QQ)}!$K$4,2)&" visits a month)")',
                  "", f'=IF({Qr("monthly")}="","","per month")', f'=IF({Qr("monthly")}="","",{cur(Qr("monthly"))})'),
                 (17, f'=IF({Qr("season")}="","","Season contract: "&{q(S_QQ)}!$K$5&" visits over "&{S["season_weeks"]}&" weeks")',
                  "", f'=IF({Qr("season")}="","","per season")', f'=IF({Qr("season")}="","",{cur(Qr("season"))})'),
                 (18, f'=IF(OR({Qr("prepaid")}="",N({S["prepay"]})=0),"","Season contract paid in advance ("&FIXED(100*N({S["prepay"]}),0)&"% off)")',
                  "", f'=IF(OR({Qr("prepaid")}="",N({S["prepay"]})=0),"","per season")',
                  f'=IF(OR({Qr("prepaid")}="",N({S["prepay"]})=0),"",{cur(Qr("prepaid"))})')]
        for r, d, fr, unit, price in lines:
            ws.merge_cells(f"B{r}:D{r}")
            ws[f"B{r}"], ws[f"E{r}"], ws[f"F{r}"], ws[f"G{r}"] = d, fr, unit, price
            ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="center")
            ws[f"E{r}"].alignment = Alignment(vertical="center")
            ws[f"F{r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"F{r}"].font = f(9, False, "666666")
            ws[f"G{r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"G{r}"].font = f(10, r == 15)
            for col in "BCDEFG":
                ws[f"{col}{r}"].border = Border(bottom=line)
            ws.row_dimensions[r].height = 30 if r == 15 else 20
        head(20, [("B", "Add-on services (one-time)", "left"), ("E", "Quantity", "right"), ("F", "Unit price", "right"),
                  ("G", "Total", "right")])
        ad1 = self.Q["ad1"]
        QQ = q(S_QQ)
        for i in range(ADD_N):
            r = 21 + i
            src = ad1 + i
            ok = f'AND({QQ}!$B${src}<>"",ISNUMBER({QQ}!$E${src}))'
            ws.merge_cells(f"B{r}:D{r}")
            ws[f"B{r}"] = f'=IF({ok},{QQ}!$B${src},"")'
            k_, d_ = f"{QQ}!$K${src}", f"{QQ}!$D${src}"
            unit = (f'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({d_},"per hour","hours"),"per cubic yard","cu yd"),'
                    f'"per bag","bags"),"per 1,000 sq ft","x 1,000 sq ft")')
            ws[f"E{r}"] = f'=IF({ok},FIXED({k_},IF({k_}=INT({k_}),0,1))&IF({d_}="flat",""," "&{unit}),"")'
            ws[f"F{r}"] = f'=IF({ok},{cur(f"{QQ}!$L${src}")},"")'
            ws[f"B{r}"].alignment = Alignment(vertical="center")
            ws[f"G{r}"] = f'=IF({ok},{cur(f"{QQ}!$E${src}")},"")'
            for col in "EFG":
                ws[f"{col}{r}"].alignment = Alignment(horizontal="right", vertical="center", shrink_to_fit=True)
            for col in "BCDEFG":
                ws[f"{col}{r}"].border = Border(bottom=line)
            ws.row_dimensions[r].height = 19
        r = 21 + ADD_N
        ws.merge_cells(f"B{r}:F{r}")
        ws[f"B{r}"] = f'=IF(N({Qr("addons")})=0,"","Add-on services total")'
        ws[f"B{r}"].alignment = Alignment(horizontal="right", vertical="center")
        ws[f"B{r}"].font = f(10, True)
        ws[f"G{r}"] = f'=IF(N({Qr("addons")})=0,"",{cur(Qr("addons"))})'
        ws[f"G{r}"].font = f(10, True)
        ws[f"G{r}"].alignment = Alignment(horizontal="right", vertical="center")
        ws.row_dimensions[r].height = 22
        r += 2
        ws[f"B{r}"] = "Terms"
        ws[f"B{r}"].font = f(9, True)
        r += 1
        ws.merge_cells(f"B{r}:G{r + 2}")
        ws[f"B{r}"] = f'=IF({S["terms"]}="","",{S["terms"]})'
        ws[f"B{r}"].font = f(9, False, "444444")
        ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        r += 4
        ws[f"B{r}"] = "Accepted by"
        ws[f"B{r}"].font = f(9, True)
        r += 2
        for col in "BCD":
            ws[f"{col}{r}"].border = Border(bottom=Side(style="thin", color="222222"))
        for col in "FG":
            ws[f"{col}{r}"].border = Border(bottom=Side(style="thin", color="222222"))
        ws.row_dimensions[r].height = 26
        r += 1
        ws[f"B{r}"] = "Customer signature"
        ws[f"F{r}"] = "Date"
        for col in "BF":
            ws[f"{col}{r}"].font = f(8, False, "666666")
        r += 2
        ws.merge_cells(f"B{r}:G{r}")
        ws[f"B{r}"] = (f'="Thank you for considering "&IF({S["name"]}="","us",{S["name"]})&IF(RIGHT({S["name"]},1)=".","",".")&" Questions? "'
                       f'&IF({S["phone"]}="",{S["email"]},{S["phone"]})')
        ws[f"B{r}"].font = f(9, False, "444444", True)
        ws[f"B{r}"].alignment = Alignment(horizontal="center")
        last = r
        # help outside the printed page
        ws["I2"] = "Printing this quote"
        ws["I2"].font = Font(name="Inter", size=10, bold=True, color=GREEN)
        ws["I3"] = ("Everything here comes from QUICK QUOTE and SETTINGS. File > Print (or Save as PDF): it fits one "
                    "letter page. This column doesn't print.")
        ws["I3"].alignment = Alignment(wrap_text=True, vertical="top")
        ws["I3"].font = Font(name="Inter", size=9, color=INK2)
        ws.merge_cells("I3:I6")
        ws["I8"] = ("Logo: Insert > Picture and place it over the dashed box. If Excel blocks it, use Review > "
                    "Unprotect Sheet (no password).")
        ws["I8"].alignment = Alignment(wrap_text=True, vertical="top")
        ws["I8"].font = Font(name="Inter", size=9, color=INK2)
        ws.merge_cells("I8:I11")
        ws.print_area = f"A1:H{last + 1}"
        ws.page_setup.orientation = "portrait"
        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
        ws.page_margins.left = ws.page_margins.right = 0.5
        ws.page_margins.top = ws.page_margins.bottom = 0.6
        ws.oddHeader.center.text = ""
        ws.oddFooter.center.text = ""
        ws.sheet_properties.tabColor = "BFBFBF"
        self.protect(ws)
        ws.protection.objects = False                    # lets buyers place their logo picture
        self.rows["cq_last"] = last

    # ============================================================ QUOTE LOG
    def build_log(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_LOG]
        widths = dict(B=13, C=22, D=28, E=12, F=12, G=13, H=13, I=12, J=12, K=13, L=36, M=17)
        self.page(ws, widths, 13, LOG_LAST + 1, "Quote log", "One row per quote. Paste the row from QUICK QUOTE, then track the answer.")
        R = lambda col: f"${col}${LOG_FIRST}:${col}${LOG_LAST}"
        st = R("J")
        dec = f'(COUNTIF({st},"Accepted")+COUNTIF({st},"Declined")+COUNTIF({st},"No reply"))'
        tiles = [(2, 3, "QUOTES LOGGED", f'=COUNTA({R("C")})', "#,##0"),
                 (4, 5, "WIN RATE", f'=IF({dec}=0,"–",COUNTIF({st},"Accepted")/{dec})', "0%"),
                 (6, 7, "AVERAGE PRICE PER VISIT", f'=IFERROR({self.cur(f"AVERAGE({R(chr(71))})")},"–")', "General"),
                 (8, 9, "PER 1,000 SQ FT · ACCEPTED", f'=IFERROR({self.cur(f"AVERAGEIFS({R(chr(77))},{st},{chr(34)}Accepted{chr(34)})")},"–")', "General"),
                 (10, 12, "PER 1,000 SQ FT · DECLINED", f'=IFERROR({self.cur(f"AVERAGEIFS({R(chr(77))},{st},{chr(34)}Declined{chr(34)})")},"–")', "General")]
        for c1, c2, lab, f, fmt in tiles:
            self.tile(ws, 4, c1, c2, lab, f, fmt)
        ws.merge_cells("B6:M6")
        acc = f'AVERAGEIFS({R("M")},{st},"Accepted")'
        dcl = f'AVERAGEIFS({R("M")},{st},"Declined")'
        ws["B6"] = (f'=IFERROR(IF({acc}>{dcl}*1.15,"Accepted quotes are higher per 1,000 sq ft than declined ones: you may have room to raise prices.",'
                    f'IF({dcl}>{acc}*1.15,"Declined quotes are much higher per 1,000 sq ft than accepted ones: check those jobs before cutting prices.",'
                    f'"Accepted and declined quotes are priced about the same per 1,000 sq ft: price is probably not the main reason for a no.")),'
                    f'"Mark quotes Accepted or Declined to compare prices per 1,000 sq ft.")')
        ws["B6"].font = font(9, True, GREEN)
        ws["B6"].alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[6].height = 24
        cur = f'" ("&{S["currency"]}&")"'
        heads = [("B", "Date"), ("C", "Client"), ("D", "Address"), ("E", "Lawn sq ft"), ("F", "Frequency"),
                 ("G", f'="Price per visit"&{cur}'), ("H", f'="Monthly price"&{cur}'), ("I", f'="Add-ons"&{cur}'),
                 ("J", "Status"), ("K", "Follow-up date"), ("L", "Notes"), ("M", f'="Per 1,000 sq ft"&{cur}')]
        for col, t in heads:
            self.header(ws[f"{col}7"], t, GREEN2 if col == "M" else GREEN, align="left" if col in "CDL" else "center")
        ws.row_dimensions[7].height = 32
        for r in range(LOG_FIRST, LOG_LAST + 1):
            for col, fmt in (("B", DATE), ("C", None), ("D", None), ("E", SQFT), ("F", None), ("G", MONEY), ("H", MONEY),
                             ("I", MONEY), ("J", None), ("K", DATE), ("L", None)):
                self.inp(ws[f"{col}{r}"], fmt, "center" if col in "BFJK" else None)
            self.calc(ws[f"M{r}"], MONEY, value=f'=IF(OR(N(E{r})=0,G{r}=""),"",G{r}/E{r}*1000)')
        rr = lambda col: f"{col}{LOG_FIRST}:{col}{LOG_LAST}"
        self.dv_list(ws, rr("F"), f"={S['freqs']}")
        self.dv_list(ws, rr("J"), f"={S['statuses']}")
        for col in "EGHI":
            self.dv_num(ws, rr(col))
        v = DataValidation(type="date", operator="between", formula1="36526", formula2="73051", allow_blank=True,
                           showErrorMessage=True, errorTitle="Date", error="Enter a date, e.g. 4/6/2026.")
        ws.add_data_validation(v)
        v.add(rr("B"))
        v.add(rr("K"))
        ws.conditional_formatting.add(rr("J"), FormulaRule(formula=[f'$J{LOG_FIRST}="Accepted"'], font=Font(color=POS, bold=True), fill=fill(POS_TINT)))
        ws.conditional_formatting.add(rr("J"), FormulaRule(formula=[f'$J{LOG_FIRST}="Declined"'], font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add(rr("K"), FormulaRule(formula=[f'AND($J{LOG_FIRST}="Sent",$K{LOG_FIRST}<>"",$K{LOG_FIRST}<=TODAY())'],
                                                           font=Font(color=GREEN, bold=True), fill=fill(BRASS_TINT)))
        ws.freeze_panes = f"A{LOG_FIRST}"
        ws.auto_filter.ref = f"B7:M{LOG_LAST}"
        ws.print_area = f"A1:M{LOG_LAST}"
        ws.print_title_rows = "7:7"
        self.protect(ws)
        if self.sample:
            for i, row in enumerate(c.LOG):
                r = LOG_FIRST + i
                for col, v in zip("BCDEFGHIJKL", row):
                    ws[f"{col}{r}"] = v if v != "" else None

    # ============================================================ ROUTE PLANNER
    def build_route(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_ROUTE]
        widths = dict(B=12, C=7, D=22, E=18, F=12, G=11, H=11, I=12, J=10, K=24, L=6, M=6, N=6, O=3,
                      P=12, Q=8, R=14, S=11, T=11, U=11, V=13, W=11, X=34)
        self.page(ws, widths, 24, RT_LAST + 1, "Route planner",
                  "Recurring clients by weekday. See which days pay best per hour and where driving eats the day.")
        for col in "LMN":
            ws.column_dimensions[col].hidden = True
        self.kicker(ws, "B5", "Your recurring clients", rule_to=11)
        self.note(ws, "B6:K6", "Bi-weekly clients count half and monthly about a quarter, so each day's totals are an "
                  "average week.", tint=PAPER, height=22)
        cur = f'" ("&{S["currency"]}&")"'
        heads = [("B", "Weekday"), ("C", "Stop"), ("D", "Client"), ("E", "Area"), ("F", f'="Price per visit"&{cur}'),
                 ("G", "Minutes on site"), ("H", "Drive minutes from last stop"), ("I", "Frequency"),
                 ("J", "Visits per week"), ("K", "Notes")]
        for col, t in heads:
            self.header(ws[f"{col}7"], t, GREEN2 if col == "J" else GREEN, align="left" if col in "DEK" else "center")
        ws.row_dimensions[7].height = 44
        fpw = f'IFERROR(INDEX({S["fpw"]},MATCH($I{{r}},{S["freqs"]},0)),0)'
        for r in range(RT_FIRST, RT_LAST + 1):
            for col, fmt in (("B", None), ("C", "0"), ("D", None), ("E", None), ("F", MONEY), ("G", "0"), ("H", "0"),
                             ("I", None), ("K", None)):
                self.inp(ws[f"{col}{r}"], fmt, "center" if col in "BCGHI" else None)
            self.calc(ws[f"J{r}"], "0.00", align="center", value=f'=IF(OR($B{r}="",$D{r}=""),"",{fpw.format(r=r)})')
            ws[f"L{r}"] = f'=IF(J{r}="",0,N(F{r})*J{r})'
            ws[f"M{r}"] = f'=IF(J{r}="",0,N(G{r})*J{r})'
            ws[f"N{r}"] = f'=IF(J{r}="",0,N(H{r})*J{r})'
        rr = lambda col: f"{col}{RT_FIRST}:{col}{RT_LAST}"
        self.dv_list(ws, rr("B"), f"={S['weekdays']}")
        self.dv_list(ws, rr("I"), f"={S['freqs']}")
        for col in "CFGH":
            self.dv_num(ws, rr(col))
        # summary by weekday
        self.kicker(ws, "P5", "By weekday  ·  average week", rule_to=24)
        sh = [("P", "Weekday"), ("Q", "Stops"), ("R", f'="Revenue"&{cur}'), ("S", "On-site hours"), ("T", "Driving hours"),
              ("U", "Total hours"), ("V", f'="Revenue per hour"&{cur}'), ("W", "Driving share"), ("X", "Check")]
        for col, t in sh:
            self.header(ws[f"{col}7"], t, align="left" if col in "PX" else "center")
        A = lambda col: f"${col}${RT_FIRST}:${col}${RT_LAST}"
        for i, day in enumerate(c.WEEKDAYS):
            r = 8 + i
            ws[f"P{r}"] = f"=INDEX({S['weekdays']},{i + 1})"
            ws[f"P{r}"].font = font(10, True, INK)
            ws[f"P{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            self.calc(ws[f"Q{r}"], "0", align="center", value=f'=COUNTIFS({A("B")},$P{r},{A("D")},"<>")')
            self.calc(ws[f"R{r}"], MONEY, value=f'=IF(Q{r}=0,"",SUMIFS({A("L")},{A("B")},$P{r}))')
            self.calc(ws[f"S{r}"], "0.00", align="center", value=f'=IF(Q{r}=0,"",SUMIFS({A("M")},{A("B")},$P{r})/60)')
            self.calc(ws[f"T{r}"], "0.00", align="center", value=f'=IF(Q{r}=0,"",SUMIFS({A("N")},{A("B")},$P{r})/60)')
            self.calc(ws[f"U{r}"], "0.00", align="center", value=f'=IF(Q{r}=0,"",S{r}+T{r})')
            self.calc(ws[f"V{r}"], MONEY, bold=True, value=f'=IF(OR(Q{r}=0,N(U{r})=0),"",R{r}/U{r})')
            self.calc(ws[f"W{r}"], "0%", align="center", value=f'=IF(OR(Q{r}=0,N(U{r})=0),"",T{r}/U{r})')
            self.calc(ws[f"X{r}"], value=(f'=IF(Q{r}=0,"",IF(W{r}>N({S["drive_warn"]}),"Driving "&FIXED(100*W{r},0)&'
                                         f'"% of the day","OK"))'))
        ws.conditional_formatting.add("X8:X14", FormulaRule(formula=['LEFT($X8,7)="Driving"'], font=Font(color=NEG, bold=True),
                                                            fill=fill(NEG_TINT)))
        ws.conditional_formatting.add("X8:X14", FormulaRule(formula=['$X8="OK"'], font=Font(color=POS, bold=True)))
        BP.databar(ws, "V8:V14", BRASS)
        tr = 15
        ws[f"P{tr}"] = "Week"
        ws[f"Q{tr}"] = "=SUM(Q8:Q14)"
        for col in "RST":
            ws[f"{col}{tr}"] = f"=SUM({col}8:{col}14)"
        ws[f"U{tr}"] = "=S15+T15"
        ws[f"V{tr}"] = '=IF(N(U15)=0,"",R15/U15)'
        ws[f"W{tr}"] = '=IF(N(U15)=0,"",T15/U15)'
        for col in "PQRSTUVWX":
            x = ws[f"{col}{tr}"]
            x.fill, x.font = fill(GREEN), font(10, True, PAPER if col == "P" else BRASS)
            x.number_format = {"R": MONEY, "V": MONEY, "W": "0%", "Q": "0"}.get(col, "0.00")
            x.alignment = Alignment(horizontal="left" if col == "P" else ("center" if col in "QSTUW" else None),
                                    vertical="center", indent=1 if col == "P" else 0)
        self.S["best_day"] = f'IFERROR(INDEX({q(S_ROUTE)}!$P$8:$P$14,MATCH(MAX({q(S_ROUTE)}!$V$8:$V$14),{q(S_ROUTE)}!$V$8:$V$14,0)),"–")'
        self.note(ws, "P17:X19", "Revenue per hour counts on-site and driving time. A day with lots of driving earns less "
                  "per hour even at good prices: group clients by area, and price far-away jobs higher.", tint=BRASS_TINT)
        ws.freeze_panes = f"A{RT_FIRST}"
        ws.print_area = f"A1:X{RT_LAST}"
        ws.page_setup.orientation = "landscape"
        self.protect(ws)
        if self.sample:
            for i, row in enumerate(c.ROUTE):
                r = RT_FIRST + i
                for col, v in zip("BCDEFGHI", row):
                    ws[f"{col}{r}"] = v

    # ============================================================ SEASON TRACKER
    def build_season(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_SEASON]
        widths = dict(B=14, C=12, D=15, E=15, F=15, G=15, H=15, I=17, J=6)
        self.page(ws, widths, 9, 30, "Season tracker", "Month by month: clients and revenue against your goal.")
        ws.column_dimensions["J"].hidden = True
        cur = f'" ("&{S["currency"]}&")"'
        heads = [("B", "Month"), ("C", "Active clients"), ("D", f'="Mowing revenue"&{cur}'), ("E", f'="Add-on revenue"&{cur}'),
                 ("F", f'="Total"&{cur}'), ("G", f'="Goal"&{cur}'), ("H", f'="Difference"&{cur}'), ("I", "% of goal")]
        for col, t in heads:
            self.header(ws[f"{col}7"], t, GREEN2 if col in "FHI" else GREEN, align="left" if col == "B" else "center")
        ws.row_dimensions[7].height = 32
        mi = lambda name: f'MATCH({name},{S["months"]},0)'
        cut = (f'IF(N({S["season_year"]})<YEAR(TODAY()),12,IF(N({S["season_year"]})>YEAR(TODAY()),0,MONTH(TODAY())))')
        for m in range(12):
            r = 8 + m
            ws[f"B{r}"] = f"=INDEX({S['months']},{m + 1})"
            ws[f"B{r}"].font = font(10, True, INK)
            ws[f"B{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            self.inp(ws[f"C{r}"], "0", "center")
            self.inp(ws[f"D{r}"], MONEY)
            self.inp(ws[f"E{r}"], MONEY)
            self.calc(ws[f"F{r}"], MONEY, bold=True, value=f'=IF(AND(D{r}="",E{r}=""),"",N(D{r})+N(E{r}))')
            self.inp(ws[f"G{r}"], '#,##0.00;-#,##0.00;""',
                     value=(f'=IF(AND({m + 1}>=IFERROR({mi(S["season_start"])},1),{m + 1}<=IFERROR({mi(S["season_end"])},12)),'
                            f'N({S["monthly_goal"]}),0)'))
            self.calc(ws[f"H{r}"], MONEY, value=f'=IF(F{r}="","",F{r}-N(G{r}))')
            self.calc(ws[f"I{r}"], "0%", align="center", value=f'=IF(OR(F{r}="",N(G{r})=0),"",F{r}/G{r})')
            ws[f"J{r}"] = f"={m + 1}"
        BP.databar(ws, "I8:I19", BRASS, max_value=1)
        ws.conditional_formatting.add("H8:H19", FormulaRule(formula=['AND(ISNUMBER($H8),$H8<0)'], font=Font(color=NEG)))
        tr = 20
        ws[f"B{tr}"] = "Year"
        for col in "DEFG":
            ws[f"{col}{tr}"] = f"=SUM({col}8:{col}19)"
        ws[f"C{tr}"] = "=MAX(C8:C19)"
        ws[f"H{tr}"] = '=IF(COUNT(F8:F19)=0,"",F20-G20)'
        ws[f"I{tr}"] = '=IF(OR(COUNT(F8:F19)=0,N(G20)=0),"",F20/G20)'
        for col in "BCDEFGHI":
            x = ws[f"{col}{tr}"]
            x.fill, x.font = fill(GREEN), font(10, True, PAPER if col == "B" else BRASS)
            x.number_format = {"C": "0", "I": "0%"}.get(col, MONEY)
            x.alignment = Alignment(horizontal="left" if col == "B" else ("center" if col in "CI" else None),
                                    vertical="center", indent=1 if col == "B" else 0)
        self.note(ws, "B21:I21", "Year row: Active clients shows your busiest month. Goals fill in from SETTINGS for the "
                  "months of your season; type over any goal to change it.", tint=PAPER, height=30)
        ytd = f'=SUMIFS($F$8:$F$19,$J$8:$J$19,"<="&{cut})'
        tiles = [(2, 3, "REVENUE YEAR TO DATE", f'={self.cur(f"SUMIFS($F$8:$F$19,$J$8:$J$19,{chr(34)}<={chr(34)}&{cut})")}'),
                 (4, 5, "BEST MONTH", '=IF(MAX(F8:F19)<=0,"–",INDEX(B8:B19,MATCH(MAX(F8:F19),F8:F19,0)))'),
                 (6, 7, "YEAR TOTAL VS GOAL", '=IF(I20="","–",FIXED(100*I20,0)&"%")'),
                 (8, 9, "AVERAGE PER ACTIVE CLIENT", f'=IF(SUMIFS(C8:C19,C8:C19,">0")=0,"–",{self.cur("F20/SUMIFS(C8:C19,C8:C19,CHAR(62)&0)")}&" / month")')]
        for c1, c2, lab, f in tiles:
            self.tile(ws, 4, c1, c2, lab, f, "General")
        self.S["ytd"] = f"SUMIFS({q(S_SEASON)}!$F$8:$F$19,{q(S_SEASON)}!$J$8:$J$19,\"<=\"&{cut})"
        ws.freeze_panes = "A8"
        ws.print_area = "A1:I21"
        self.protect(ws)
        for col in "CDE":
            self.dv_num(ws, f"{col}8:{col}19")
        self.dv_num(ws, "G8:G19")
        if self.sample:
            for m, name in enumerate(c.MONTHS):
                a, mow, add, goal = c.SEASON[name]
                r = 8 + m
                if a or mow or add:
                    ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"] = a, mow, add
                ws[f"G{r}"] = goal

    # ============================================================ DASHBOARD
    def build_dashboard(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_DASH]
        widths = {L(k): 12.5 for k in range(2, 14)}
        widths["B"] = 15
        self.page(ws, widths, 13, 80, "Dashboard", "Your break-even rate, quotes, routes and season at a glance.")
        RQ, SQ, LQ = q(S_ROUTE), q(S_SEASON), q(S_LOG)
        ws.merge_cells("B4:M4")
        self.label(ws["B4"], f'=IF({S["name"]}="","Your business",{S["name"]})&"  ·  Season "&{S["season_year"]}', color=GREEN, size=11)
        st = f"{LQ}!$J${LOG_FIRST}:$J${LOG_LAST}"
        dec = f'(COUNTIF({st},"Accepted")+COUNTIF({st},"Declined")+COUNTIF({st},"No reply"))'
        tiles = [("BREAK-EVEN HOURLY RATE", f'={self.cur(S["breakeven_hr"])}'),
                 ("AVERAGE PRICE PER VISIT (ROUTE)", f'=IF(COUNTA({RQ}!$D${RT_FIRST}:$D${RT_LAST})=0,"–",{self.cur(f"AVERAGEIFS({RQ}!$F${RT_FIRST}:$F${RT_LAST},{RQ}!$D${RT_FIRST}:$D${RT_LAST},CHAR(60)&CHAR(62))")})'),
                 ("WIN RATE", f'=IF({dec}=0,"–",FIXED(100*COUNTIF({st},"Accepted")/{dec},0)&"%")'),
                 ("ACTIVE CLIENTS", f'=COUNTA({RQ}!$D${RT_FIRST}:$D${RT_LAST})'),
                 ("REVENUE YEAR TO DATE", f'={self.cur(S["ytd"])}'),
                 ("BEST DAY (REVENUE PER HOUR)", f'={S["best_day"]}')]
        for i, (lab, f) in enumerate(tiles):
            r = 6 if i < 3 else 9
            k = i % 3
            self.tile(ws, r, 2 + 4 * k, 5 + 4 * k, lab, f, "General" if i != 3 else "0")
        ws.row_dimensions[8].height = 6

        def head(r, cols):
            for col, t in cols:
                self.header(ws[f"{col}{r}"], t, align="left" if col == "B" else "center")
            ws.row_dimensions[r].height = 24

        rows = {}
        # ---- monthly revenue vs goal
        r = 12
        rows["months"] = r
        self.kicker(ws, f"B{r}", "Monthly revenue vs goal", rule_to=13)
        hr = r + 1
        head(hr, [("B", "Month"), ("C", "Revenue"), ("D", "Goal"), ("E", "% of goal")])
        for m in range(12):
            rr = hr + 1 + m
            ws[f"B{rr}"] = f"=LEFT(INDEX({S['months']},{m + 1}),3)"
            ws[f"B{rr}"].font = font(10, True, INK)
            self.calc(ws[f"C{rr}"], MONEY0, value=f"=N({SQ}!$F${8 + m})")
            self.calc(ws[f"D{rr}"], MONEY0, value=f"=N({SQ}!$G${8 + m})")
            self.calc(ws[f"E{rr}"], "0%", align="center", value=f'=IF(D{rr}=0,"",C{rr}/D{rr})')
        BP.databar(ws, f"E{hr + 1}:E{hr + 12}", BRASS, max_value=1)
        ch = BarChart()
        ch.type, ch.style = "col", 10
        ch.add_data(Reference(ws, min_col=3, max_col=4, min_row=hr, max_row=hr + 12), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=hr + 1, max_row=hr + 12))
        for s_, colr in zip(ch.series, (GREEN, "E3C68F")):
            s_.graphicalProperties.solidFill = colr
            s_.graphicalProperties.line.solidFill = colr
        BP.clean_chart(ch, legend=True)
        ch.gapWidth, ch.overlap = 50, -10
        ch.height, ch.width = 7.0, 17.2
        ch.anchor = f"G{hr}"
        ws.add_chart(ch)
        # ---- quotes by status
        r = hr + 15
        rows["quotes"] = r
        self.kicker(ws, f"B{r}", "Quotes by status", rule_to=13)
        hr = r + 1
        head(hr, [("B", "Status"), ("C", "Quotes"), ("D", "Share")])
        q1 = hr + 1
        for i, s_ in enumerate(c.STATUSES):
            rr = q1 + i
            ws[f"B{rr}"] = f"=INDEX({S['statuses']},{i + 1})"
            ws[f"B{rr}"].font = font(10, True, INK)
            self.calc(ws[f"C{rr}"], "0", align="center", value=f"=COUNTIF({st},B{rr})")
            self.calc(ws[f"D{rr}"], "0%", align="center",
                      value=f'=IF(SUM($C${q1}:$C${q1 + len(c.STATUSES) - 1})=0,"",C{rr}/SUM($C${q1}:$C${q1 + len(c.STATUSES) - 1}))')
        q2 = q1 + len(c.STATUSES) - 1
        BP.databar(ws, f"D{q1}:D{q2}", BRASS, max_value=1)
        ch = DoughnutChart(holeSize=55)
        ch.add_data(Reference(ws, min_col=3, min_row=q1, max_row=q2), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=q1, max_row=q2))
        for i, colr in enumerate(["C9D3CF", "2E7D4F", "B3261E", "D29A3A"]):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.solidFill = "FFFFFF"
            ch.series[0].dPt.append(pt)
        BP.clean_chart(ch, legend=True, axes=False, legend_pos="r")
        ch.height, ch.width = 4.4, 12.5
        ch.anchor = f"G{hr}"
        ws.add_chart(ch)
        # ---- revenue per hour by weekday
        r = q2 + 5
        rows["days"] = r
        self.kicker(ws, f"B{r}", "Revenue per hour by weekday", rule_to=13)
        hr = r + 1
        head(hr, [("B", "Weekday"), ("C", "Stops"), ("D", "Revenue"), ("E", "Per hour")])
        d1 = hr + 1
        for i in range(7):
            rr = d1 + i
            ws[f"B{rr}"] = f"=LEFT(INDEX({S['weekdays']},{i + 1}),3)"
            ws[f"B{rr}"].font = font(10, True, INK)
            self.calc(ws[f"C{rr}"], "0", align="center", value=f"={RQ}!$Q${8 + i}")
            self.calc(ws[f"D{rr}"], MONEY0, value=f"=N({RQ}!$R${8 + i})")
            self.calc(ws[f"E{rr}"], MONEY, bold=True, value=f"=N({RQ}!$V${8 + i})")
        BP.databar(ws, f"E{d1}:E{d1 + 6}", BRASS)
        ch = BarChart()
        ch.type, ch.style = "col", 10
        ch.add_data(Reference(ws, min_col=5, min_row=d1, max_row=d1 + 6), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=d1, max_row=d1 + 6))
        s_ = ch.series[0]
        s_.graphicalProperties.solidFill = BRASS
        s_.graphicalProperties.line.solidFill = BRASS
        BP.clean_chart(ch, legend=False)
        ch.gapWidth = 60
        ch.height, ch.width = 5.0, 17.2
        ch.anchor = f"G{hr}"
        ws.add_chart(ch)
        r = d1 + 9
        self.note(ws, f"B{r}:M{r}", DISCLAIMER, height=30, size=9, color=INK, bold=True)
        rows["end"] = r
        self.rows["dash"] = rows
        ws.print_area = f"A1:M{r}"
        self.protect(ws)

    # ============================================================ START HERE
    def build_start(self):
        c = self.cfg
        ws = self.ws[S_START]
        self.page(ws, {"B": 5, "C": 30, "D": 30, "E": 30, "F": 24}, 6, 70, "Start here",
                  "Read this first. Setting up takes about 15 minutes.", landscape=False)
        self.note(ws, "B4:F4", "Price every lawn for profit in two minutes.", tint=PAPER, height=32, size=15, color=GREEN, bold=True)
        ws["B4"].font = Font(name=TITLE, size=16, bold=True, color=GREEN)
        self.note(ws, "B5:F5", "Most new lawn businesses guess their prices. This workbook adds up what each visit really "
                  "costs you (your time, equipment wear, fuel, insurance, driving) and prices the job so you keep a "
                  "profit on top of your own pay.", tint=PAPER, height=48, size=10, color=INK)
        r = 7
        self.kicker(ws, f"B{r}", "Quick start in 3 steps", rule_to=6)
        steps = [("1", "Settings (once)", "Your business details, your pay, equipment, overhead, fuel and price list. "
                  "Replace the example values with your own.", S_SET),
                 ("2", "Quote a job", "Enter the lawn size, mower, obstacles, slope and drive time. The price per visit, "
                  "monthly and season prices appear on the right. The CUSTOMER QUOTE tab is ready to print.", S_QQ),
                 ("3", "Save it to the log", "Copy the green row at the bottom of QUICK QUOTE into QUOTE LOG. Mark it "
                  "Accepted or Declined later to see if your prices are too high or too low.", S_LOG)]
        r = 8
        for num, head, body, sheet in steps:
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
        self.link(ws[f"C{r}"], "Routes and season  ›", S_ROUTE)
        ws[f"C{r}"].alignment = Alignment(vertical="top")
        ws.merge_cells(f"D{r}:F{r}")
        ws[f"D{r}"] = "Once you have regular clients, list them on ROUTE PLANNER and fill SEASON TRACKER each month."
        ws[f"D{r}"].font = font(10, color=INK2)
        ws[f"D{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 34
        r += 2
        self.kicker(ws, f"B{r}", "Colour key", rule_to=6)
        r += 1
        for kind, head, body in [("inp", "Type here", "White cell with a border: your numbers, or pick from the dropdown."),
                                 ("calc", "Calculated", "Shaded cell: a formula, locked so it can't be overwritten by accident."),
                                 ("tile", "Result", "Green block with a brass figure: a key number."),
                                 ("warn", "Check this", "Red: below break-even, low profit, or too much driving.")]:
            x = ws[f"C{r}"]
            if kind == "inp":
                self.inp(x)
            elif kind == "calc":
                self.calc(x)
            elif kind == "tile":
                x.fill, x.font = fill(GREEN), font(10, True, BRASS)
            else:
                x.fill, x.font = fill(NEG_TINT), font(10, True, NEG)
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
        self.kicker(ws, f"B{r}", "Measuring a lawn with free map tools", rule_to=6)
        r += 1
        tips = ["Google Maps on a computer: right-click the lawn's corner, choose Measure distance, click around the "
                "edge back to the start. The area appears in square feet.",
                "Google Earth (web): use the ruler, choose Polygon, trace the lawn. Your county's free GIS parcel map "
                "often has a measuring tool too.",
                "Measure only the grass. Subtract the house, driveway, patio and planting beds; measure front and back "
                "separately and add them up.",
                "Check the first few on site with a measuring wheel or by timing yourself. Then adjust mowing speeds on SETTINGS."]
        for t in tips:
            ws[f"B{r}"] = "•"
            ws[f"B{r}"].font = font(12, True, BRASS)
            ws[f"B{r}"].alignment = Alignment(horizontal="center", vertical="top")
            ws.merge_cells(f"C{r}:F{r}")
            ws[f"C{r}"] = t
            ws[f"C{r}"].font = font(10, color=INK)
            ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 32
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Guide and Google Sheets", rule_to=6)
        r += 1
        self.note(ws, f"B{r}:F{r}", "Quick-start guide: BrassLedger_Lawn_Care_Quick_Start_Guide.pdf (in your download).   "
                  "Google Sheets copy: [GOOGLE SHEETS COPY LINK]", tint=PAPER, height=30, size=10, color=INK)
        r += 2
        self.note(ws, f"B{r}:F{r}", DISCLAIMER, tint=BRASS_TINT, height=36, size=10, color=INK, bold=True)
        if self.sample:
            r += 2
            self.note(ws, f"B{r}:F{r}", "SAMPLE FILE: a fictional business, Greenline Lawn Co., with example quotes, 15 "
                      "route clients and a season of figures. Use the blank file for your own business.", tint=POS_TINT,
                      height=34, size=10, color=POS, bold=True)
        ws.print_area = f"A1:G{r + 1}"
        self.protect(ws)

    # ============================================================ build
    def build(self):
        self.build_settings()
        self.build_quote()
        self.build_customer()
        self.build_log()
        self.build_route()
        self.build_season()
        self.build_dashboard()
        self.build_start()
        self.wb.active = 0
        for ws in self.wb.worksheets:
            ws.sheet_view.tabSelected = ws.title == S_START
        self.wb.calculation.fullCalcOnLoad = True
        p = self.wb.properties
        p.title, p.creator, p.subject = self.cfg.PRODUCT, "Brass Ledger", "Simple tools for small business numbers."
        return self.wb

    def add_sidebars(self):
        return BP.add_sidebars(self.wb, NAV, {S_START: 60, S_SET: self.rows["set_last"] + 2, S_QQ: 60, S_LOG: 120, S_ROUTE: 120,
                                              S_SEASON: 60, S_DASH: 70}, skip=(S_CQ,), max_last=200)


def main(cfg, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for sample in (False, True):
        e = Engine(cfg, sample)
        wb = e.build()
        layers = e.add_sidebars()
        p = out_dir / (cfg.OUT_NAME + ("_SAMPLE" if sample else "") + ".xlsx")
        wb.save(p)
        BP.finish(p, layers)
        paths.append(p)
        print("wrote", p)
    return paths
