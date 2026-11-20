"""Brass Ledger Pressure Washing Bid Calculator: multi-line bid engine built on the shared pricing engine (engine.py).

Reused from engine.py (the Lawn Care Pricing Calculator engine): page styling, title bars, tiles, dropdown and number
validation helpers, total rows, currency text, icon sidebar, protection and the build/finish flow. The cost-per-hour
block (business details, targets, fuel, equipment, overhead, break-even) follows the same layout and wording.

New here: a services table priced by surface, condition / height-access / stain multipliers, a 10-line quote with
shared job costs spread over the lines, bundle discount, water hauling and travel surcharge, maintenance plan value,
a job log comparing estimated and actual hours per service, and a maintenance plan tracker.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, Protection, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

import engine as base
from engine import BP, CUST, DATE, HRS, MINS, MONEY, MONEY0, PCT, SQFT
from xlkit import (BRASS, BRASS_TINT, GREEN, GREEN2, INK, INK2, NEG, NEG_TINT, PAPER, POS, POS_TINT, TITLE, WHITE,
                   fill, font, q)

S_START, S_SET, S_QQ, S_CQ, S_LOG, S_JOB, S_PLAN, S_DASH = (
    "START HERE", "SETTINGS", "QUICK QUOTE", "CUSTOMER QUOTE", "QUOTE LOG", "JOB LOG", "MAINTENANCE PLANS", "DASHBOARD")
ORDER = [S_START, S_SET, S_QQ, S_CQ, S_LOG, S_JOB, S_PLAN, S_DASH]
NAV = [(S_DASH, "bar_chart", "Home"), (S_START, "question", "Start"), (S_SET, "gear", "Setup"), (S_QQ, "calc", "Quote"),
       (S_CQ, "receipt", "Customer"), (S_LOG, "clipboard", "Log"), (S_JOB, "clock", "Jobs"), (S_PLAN, "repeat", "Plans")]
DISCLAIMER = base.DISCLAIMER
LINES = 10
LOG_FIRST, LOG_N = 8, 300
LOG_LAST = LOG_FIRST + LOG_N - 1
JOB_FIRST, JOB_N = 8, 300
JOB_LAST = JOB_FIRST + JOB_N - 1
PLAN_FIRST, PLAN_N = 8, 150
PLAN_LAST = PLAN_FIRST + PLAN_N - 1
SVC_ROWS = 30
NUM1 = "#,##0.0"


class PWEngine(base.Engine):
    def __init__(self, cfg, sample: bool):
        self.cfg = cfg
        self.product = cfg.PRODUCT
        self.sample = sample
        self.home_tab, self.start_tab = S_DASH, S_START
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in ORDER}
        self.S, self.Q, self.rows = {}, {}, {}

    def ref(self, key):
        return self.S[key].split("!")[1].replace("$", "")

    # ============================================================ SETTINGS
    def build_settings(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_SET]
        SQ = q(S_SET)
        widths = {"B": 42, "C": 16, "D": 14, "E": 14, "F": 16, "G": 16, "H": 14, "I": 40}
        self.page(ws, widths, 9, 220, "Settings", "Your costs, services, rates and multipliers. Every other tab reads from here.")
        self.note(ws, "B4:I4", "EXAMPLE VALUES: adjust every white cell to your area and equipment. Rates and prices "
                  "below are typical US figures, not advice.", height=30, size=10, color=INK, bold=True)
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
                    ws.merge_cells(f"G{r}:I{r}")
            elif note:
                self.label(ws[f"D{r}"], note, bold=False, color=INK2, size=9, indent=1)
                ws.merge_cells(f"D{r}:I{r}")
            ws.row_dimensions[r].height = 20
            S[key] = f"{SQ}!$C${r}"
            return cell

        r = 6
        self.kicker(ws, f"B{r}", "Your business  ·  shown on the customer quote", rule_to=9)
        r += 1
        for key, label in [("name", "Business name"), ("contact", "Contact name"), ("phone", "Phone"), ("email", "Email"),
                           ("website", "Website"), ("street", "Street address"), ("city", "City, state, ZIP")]:
            field(r, key, label, b.get(key), wide=True)
            r += 1
        T = c.TARGETS
        field(r, "currency", "Currency symbol", T["currency"], note="Shown before prices on the quote and tiles.")
        ws[f"C{r}"].alignment = Alignment(horizontal="center", vertical="center")
        r += 1
        field(r, "valid_days", "Quote valid for (days)", T["valid_days"], "0", "Sets the valid-until date on the quote.")
        r += 1
        self.label(ws[f"B{r}"], "Quote terms", bold=False)
        ws.merge_cells(f"C{r}:I{r}")
        self.inp(ws[f"C{r}"], value=c.TERMS)
        ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="top", indent=1)
        for col in "DEFGHI":
            self.inp(ws[f"{col}{r}"])
        ws.row_dimensions[r].height = 48
        S["terms"] = f"{SQ}!$C${r}"
        r += 2

        self.kicker(ws, f"B{r}", "Pricing targets", rule_to=9)
        r += 1
        rows = [("hours", "Working hours per year (incl. driving)", T["hours"], "#,##0",
                 "Example: 35 busy weeks x about 30 hours. Spreads equipment and overhead."),
                ("owner_pay", "Your target pay per hour", T["owner_pay"], MONEY, "What you want to earn for your own time."),
                ("helper_wage", "Helper wage per hour", T["helper_wage"], MONEY, "Only used when crew size is 2 or more."),
                ("payroll", "Payroll costs on helper wages", T["payroll"], PCT, "Employer taxes, workers' comp. Check with your accountant."),
                ("margin", "Target profit margin", T["margin"], PCT, "Share of the price kept as profit, after paying yourself."),
                ("target_profit_hr", "Target profit per job hour", T["target_profit_hr"], MONEY, "Quick Quote warns when a job earns less."),
                ("min_charge", "Minimum job charge", T["min_charge"], MONEY, "No job is priced below this."),
                ("rounding", "Round each line up to the nearest", T["rounding"], MONEY0, "Example: 5 rounds 147.20 up to 150."),
                ("setup_min", "Setup and breakdown per job (minutes)", T["setup_min"], "0", "Unloading, hoses, mixing, packing up."),
                ("bundle_disc", "Bundle discount (2 or more services)", T["bundle_disc"], PCT, "0 % if you don't offer one."),
                ("plan_disc", "Maintenance plan discount", T["plan_disc"], PCT, "Off each visit for clients on a yearly plan."),
                ("crew_loss", "Crew efficiency loss per extra person", T["crew_loss"], PCT, "Two people are a bit less than twice as fast."),
                ("year", "Year for year-to-date figures", c.YEAR if self.sample else None, "0", "Used on the dashboard.")]
        for key, label, val, fmt, note in rows:
            field(r, key, label, val, fmt, note)
            r += 1
        if not self.sample:
            ws[self.ref("year")] = "=YEAR(TODAY())"
        r += 1
        self.kicker(ws, f"B{r}", "Water and travel charges", rule_to=9)
        r += 1
        for key, label, val, fmt, note in [
                ("water_fee", "Water hauling charge (no water on site)", T["water_fee"], MONEY, "Added to the quote as its own line."),
                ("water_min", "Extra minutes when hauling water", T["water_min"], "0", "Filling and running the tank."),
                ("free_miles", "Miles included before a travel surcharge", T["free_miles"], "0", "Round trip or one way: be consistent."),
                ("surcharge_mile", "Travel surcharge per mile beyond that", T["surcharge_mile"], MONEY, "Added to the quote as its own line.")]:
            field(r, key, label, val, fmt, note)
            r += 1
        r += 1
        F = c.FUEL
        self.kicker(ws, f"B{r}", "Fuel and vehicle", rule_to=9)
        r += 1
        field(r, "fuel_price", "Fuel price per gallon", F["fuel_price"], MONEY, "Check your local pump price.")
        r += 1
        field(r, "machine_gph", "Pressure washer fuel (gallons per hour)", F["machine_gph"], "0.00", "While spraying.")
        r += 1
        field(r, "mpg", "Truck miles per gallon (towing)", F["mpg"], "0.0", "")
        r += 1
        field(r, "wear_mile", "Truck wear per mile (repairs, tyres)", F["wear_mile"], MONEY, "Everything except fuel.")
        r += 1
        field(r, "vehicle_mile", "Vehicle cost per mile", None, MONEY, "Fuel ÷ miles per gallon + wear per mile.",
              calc=f'=IF(N({S["mpg"]})=0,0,N({S["fuel_price"]})/{S["mpg"]})+N({S["wear_mile"]})')
        r += 2

        # ---- equipment (same layout as the lawn product)
        self.kicker(ws, f"B{r}", "Equipment", rule_to=9)
        r += 1
        for col, t in zip("BCDEF", ["Item", "Purchase price", "Life (years)", "Yearly maintenance", "Cost per year"]):
            self.header(ws[f"{col}{r}"], t, GREEN2 if col == "F" else GREEN, align="left" if col == "B" else "center")
        self.label(ws[f"G{r}"], "Cost per year = price ÷ life + maintenance", bold=False, color=INK2, size=9, indent=1)
        ws.merge_cells(f"G{r}:I{r}")
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
        self.kicker(ws, f"B{r}", "Overhead (yearly)", rule_to=9)
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
        self.kicker(ws, f"B{r}", "Cost per working hour  ·  calculated", rule_to=9)
        r += 1
        H = S["hours"]
        self.rows["cost_hr"] = r
        for key, label, f, note in [
                ("equip_hr", "Equipment cost per hour", f'=IF(N({H})=0,0,{S["equip_year"]}/{H})', "Equipment per year ÷ working hours."),
                ("over_hr", "Overhead per hour", f'=IF(N({H})=0,0,{S["over_year"]}/{H})', "Overhead per year ÷ working hours."),
                ("running_hr", "Total running cost per working hour", "=0", "Equipment + overhead, before your pay."),
                ("breakeven_hr", "Break-even hourly rate (solo)", "=0", "Running cost + your target pay. Charge less and you pay yourself less."),
                ("target_hr", "Hourly rate at your target margin", "=0", "Break-even ÷ (1 − target margin).")]:
            field(r, key, label, None, MONEY, note, calc=f)
            r += 1
        ws[self.ref("running_hr")] = f'={S["equip_hr"]}+{S["over_hr"]}'
        ws[self.ref("breakeven_hr")] = f'={S["running_hr"]}+N({S["owner_pay"]})'
        ws[self.ref("target_hr")] = f'=IF(N({S["margin"]})>=1,"",{S["breakeven_hr"]}/(1-N({S["margin"]})))'
        x = ws[self.ref("breakeven_hr")]
        x.fill, x.font = fill(GREEN), font(11, True, BRASS)
        ws[f"B{x.row}"].font = font(10, True, GREEN)
        r += 1

        # ---- services
        self.kicker(ws, f"B{r}", "Services and production rates", rule_to=9)
        r += 1
        self.note(ws, f"B{r}:I{r}", "One row per service. Units per hour = what one person cleans in an hour on a normal "
                  "job. Chemicals and materials are per 1,000 units (sealer, sand and stain included). Local going rate "
                  "is optional: what you believe others charge per unit.", tint=PAPER, height=34)
        r += 1
        heads = ["Service", "Category", "Unit", "Units per hour", "Chemicals per 1,000 units", "Local going rate per unit",
                 "Flatwork?", "Notes"]
        for col, t in zip("BCDEFGHI", heads):
            self.header(ws[f"{col}{r}"], t, align="left" if col in "BI" else "center")
        ws.row_dimensions[r].height = 34
        r += 1
        s1 = r
        for i in range(SVC_ROWS):
            row = c.SERVICES[i] if i < len(c.SERVICES) else (None,) * 7
            self.inp(ws[f"B{r}"], value=row[0])
            self.inp(ws[f"C{r}"], value=row[1])
            self.inp(ws[f"D{r}"], align="center", value=row[2])
            self.inp(ws[f"E{r}"], "#,##0", value=row[3])
            self.inp(ws[f"F{r}"], MONEY, value=row[4])
            self.inp(ws[f"G{r}"], "#,##0.00", value=row[5])
            self.inp(ws[f"H{r}"], align="center", value=row[6])
            self.inp(ws[f"I{r}"])
            r += 1
        s2 = r - 1
        col = lambda k: f"{SQ}!${k}${s1}:${k}${s2}"
        S.update(svc=col("B"), svc_cat=col("C"), svc_unit=col("D"), svc_rate=col("E"), svc_chem=col("F"),
                 svc_going=col("G"), svc_flat=col("H"))
        self.rows["svc"] = (s1, s2)
        self.dv_num(ws, f"E{s1}:E{s2}", "decimal", 0, 1e6)
        self.dv_num(ws, f"F{s1}:F{s2}")
        self.dv_num(ws, f"G{s1}:G{s2}")
        r += 1

        # ---- condition, access, stains
        self.kicker(ws, f"B{r}", "Condition", rule_to=9)
        r += 1
        for cc, t in zip("BCD", ["Condition", "Time multiplier", "Chemical multiplier"]):
            self.header(ws[f"{cc}{r}"], t, align="left" if cc == "B" else "center")
        self.label(ws[f"E{r}"], "1.00 = normal. Heavy growth or grime takes longer and uses more chemical.", bold=False,
                   color=INK2, size=9, indent=1)
        ws.merge_cells(f"E{r}:I{r}")
        ws.row_dimensions[r].height = 30
        r += 1
        c1 = r
        for name, tm, cm in c.CONDITIONS:
            self.inp(ws[f"B{r}"], value=name)
            self.inp(ws[f"C{r}"], "0.00", "center", value=tm)
            self.inp(ws[f"D{r}"], "0.00", "center", value=cm)
            r += 1
        S.update(cond=f"{SQ}!$B${c1}:$B${r - 1}", cond_t=f"{SQ}!$C${c1}:$C${r - 1}", cond_c=f"{SQ}!$D${c1}:$D${r - 1}")
        self.dv_num(ws, f"C{c1}:D{r - 1}", "decimal", 0.1, 10)
        r += 1
        self.kicker(ws, f"B{r}", "Height and access", rule_to=9)
        r += 1
        for cc, t in zip("BC", ["Height / access", "Time multiplier"]):
            self.header(ws[f"{cc}{r}"], t, align="left" if cc == "B" else "center")
        self.label(ws[f"D{r}"], "Use storeys for house washes, pitch for roofs, ladder or lift for gutters and high walls.",
                   bold=False, color=INK2, size=9, indent=1)
        ws.merge_cells(f"D{r}:I{r}")
        ws.row_dimensions[r].height = 26
        r += 1
        a1 = r
        for i in range(9):
            name, m = c.ACCESS[i] if i < len(c.ACCESS) else (None, None)
            self.inp(ws[f"B{r}"], value=name)
            self.inp(ws[f"C{r}"], "0.00", "center", value=m)
            r += 1
        S.update(acc=f"{SQ}!$B${a1}:$B${r - 1}", acc_m=f"{SQ}!$C${a1}:$C${r - 1}")
        self.dv_num(ws, f"C{a1}:C{r - 1}", "decimal", 0.1, 10)
        r += 1
        self.kicker(ws, f"B{r}", "Stain treatment", rule_to=9)
        r += 1
        for cc, t in zip("BCDE", ["Stain", "Unit", "Minutes per unit", "Material cost per unit"]):
            self.header(ws[f"{cc}{r}"], t, align="left" if cc == "B" else "center")
        self.label(ws[f"F{r}"], "Priced like the rest of the job: time at your rates plus materials, then your margin.",
                   bold=False, color=INK2, size=9, indent=1, wrap=True)
        ws.merge_cells(f"F{r}:I{r}")
        ws.row_dimensions[r].height = 30
        r += 1
        t1 = r
        for i in range(6):
            name, unit, mins, cost = c.STAINS[i] if i < len(c.STAINS) else (None,) * 4
            self.inp(ws[f"B{r}"], value=name)
            self.inp(ws[f"C{r}"], align="center", value=unit)
            self.inp(ws[f"D{r}"], "0.0", "center", value=mins)
            self.inp(ws[f"E{r}"], MONEY, value=cost)
            r += 1
        S.update(stain=f"{SQ}!$B${t1}:$B${r - 1}", stain_unit=f"{SQ}!$C${t1}:$C${r - 1}",
                 stain_min=f"{SQ}!$D${t1}:$D${r - 1}", stain_cost=f"{SQ}!$E${t1}:$E${r - 1}")
        self.dv_num(ws, f"D{t1}:E{r - 1}")
        r += 1
        self.kicker(ws, f"B{r}", "Reminders  ·  not legal advice", rule_to=9, color=NEG)
        r += 1
        for t in c.COMPLIANCE:
            self.note(ws, f"B{r}:I{r}", t, tint=NEG_TINT, height=22, size=9, color=NEG, bold=True)
            r += 1
        r += 1
        # ---- dropdown lists
        self.kicker(ws, f"B{r}", "Dropdown lists", rule_to=9)
        r += 1
        lists = [("B", "Units", c.UNITS, "units"), ("C", "Categories", c.CATEGORIES, "cats"), ("D", "Yes / No", ["Yes", "No"], "yesno"),
                 ("E", "Property type", c.PROPERTY, "property"), ("F", "Quote status", c.STATUSES, "statuses"),
                 ("G", "Plan frequency", [n for n, _v in c.PLAN_FREQ], "plan_freq"), ("H", "Visits per year", [v for _n, v in c.PLAN_FREQ], "plan_visits"),
                 ("I", "Plan status", c.PLAN_STATUS, "plan_status")]
        for cc, head, items, key in lists:
            self.header(ws[f"{cc}{r}"], head, align="left")
            for i, it in enumerate(items):
                self.sysval(ws[f"{cc}{r + 1 + i}"], it)
            S[key] = f"{SQ}!${cc}${r + 1}:${cc}${r + len(items)}"
        r += 1 + max(len(x[2]) for x in lists)
        self.header(ws[f"B{r}"], "Stain units", align="left")
        self.header(ws[f"C{r}"], "Plan visits on a quote", align="left")
        for i, it in enumerate(c.STAIN_UNITS):
            self.sysval(ws[f"B{r + 1 + i}"], it)
        for i, it in enumerate([0, 1, 2]):
            self.sysval(ws[f"C{r + 1 + i}"], it)
        S["stain_units"] = f"{SQ}!$B${r + 1}:$B${r + len(c.STAIN_UNITS)}"
        S["line_visits"] = f"{SQ}!$C${r + 1}:$C${r + 3}"
        last = r + 4
        self.dv_list(ws, f"C{s1}:C{s2}", f"={S['cats']}")
        self.dv_list(ws, f"D{s1}:D{s2}", f"={S['units']}")
        self.dv_list(ws, f"H{s1}:H{s2}", f"={S['yesno']}")
        self.dv_list(ws, f"C{t1}:C{t1 + 5}", f"={S['stain_units']}")
        for key in ("hours", "owner_pay", "helper_wage", "min_charge", "rounding", "setup_min", "water_fee", "water_min",
                    "free_miles", "surcharge_mile", "fuel_price", "machine_gph", "mpg", "wear_mile", "valid_days"):
            self.dv_num(ws, self.ref(key))
        for key in ("payroll", "bundle_disc", "plan_disc", "crew_loss"):
            self.dv_num(ws, self.ref(key), "decimal", 0, 1, "Percent", "Enter a percentage, e.g. 10%.")
        self.dv_num(ws, self.ref("margin"), "decimal", 0, 0.9, "Margin", "Enter 0% to 90%.")
        ws.freeze_panes = "A4"
        ws.print_area = f"A1:I{last}"
        self.rows["set_last"] = last
        self.protect(ws)

    # ============================================================ QUICK QUOTE
    def build_quote(self):
        c, S, Q = self.cfg, self.S, self.Q
        ws = self.ws[S_QQ]
        widths = {"B": 32, "C": 14, "D": 16, "E": 13, "F": 26, "G": 15, "H": 10, "I": 10, "J": 11, "K": 12, "L": 12,
                  "M": 12, "N": 11, "O": 18}
        self.page(ws, widths, 15, 80, "Quick quote", "Fill the white cells. Up to 10 services per job; the price builds below.")
        for k in range(17, 31):
            ws.column_dimensions[L(k)].hidden = True
            ws.column_dimensions[L(k)].width = 8

        def inrow(r, key, label, fmt=None, wide=False, align=None, hint=""):
            self.label(ws[f"B{r}"], label, bold=False)
            cell = ws[f"C{r}"]
            self.inp(cell, fmt, align or ("right" if fmt else None))
            if wide:
                ws.merge_cells(f"C{r}:F{r}")
                for col in "DEF":
                    self.inp(ws[f"{col}{r}"])
            elif hint:
                self.label(ws[f"D{r}"], hint, bold=False, color=INK2, size=9, indent=1)
                ws.merge_cells(f"D{r}:F{r}")
            ws.row_dimensions[r].height = 20
            Q[key] = f"$C${r}"

        r = 4
        self.kicker(ws, f"B{r}", "1  ·  Client and job", rule_to=6)
        r += 1
        inrow(r, "date", "Quote date", DATE, align="center"); r += 1
        inrow(r, "number", "Quote number (optional)", align="center"); r += 1
        inrow(r, "client", "Client name", wide=True); r += 1
        inrow(r, "address", "Address", wide=True); r += 1
        inrow(r, "property", "Property type", wide=True)
        self.dv_list(ws, f"C{r}", f"={S['property']}"); r += 1
        inrow(r, "crew", "Crew size (people on site)", "0", align="center", hint="1 = you alone.")
        self.dv_num(ws, f"C{r}", "whole", 1, 6, "Crew", "Enter 1 to 6 people."); r += 1
        inrow(r, "drive", "Drive time to the job (minutes)", "0", align="center", hint="One way, from the last job.")
        self.dv_num(ws, f"C{r}", "decimal", 0, 600); r += 1
        inrow(r, "miles", "Miles driven for this job", "0.0", align="center", hint="Used for vehicle cost and surcharge.")
        self.dv_num(ws, f"C{r}", "decimal", 0, 2000); r += 1
        inrow(r, "water", "Water tap on site?", align="center", hint="No = water hauling charge + time.")
        self.dv_list(ws, f"C{r}", f"={S['yesno']}"); r += 1
        inrow(r, "other", "Other job costs (permits, dump fees)", MONEY, hint="Your cost, not shown to the client.")
        self.dv_num(ws, f"C{r}"); r += 1
        top_end = r

        # ---------------- service lines
        r = top_end + 1
        self.kicker(ws, f"B{r}", "2  ·  Services", rule_to=15)
        r += 1
        heads = [("B", "Service"), ("C", "Quantity"), ("D", "Unit"), ("E", "Condition"), ("F", "Height / access"),
                 ("G", "Stain treatment"), ("H", "Stain qty"), ("I", "Plan visits a year"), ("J", "Minutes"),
                 ("K", "Chemicals"), ("L", "Line cost"), ("M", "Line price"), ("N", "Price per unit"), ("O", "vs going rate")]
        calc_cols = "DJKLMNO"
        for col, t in heads:
            self.header(ws[f"{col}{r}"], t, GREEN2 if col in calc_cols else GREEN, align="left" if col == "B" else "center")
        ws[f"M{r}"].fill = fill(BRASS)
        ws[f"M{r}"].font = font(9, True, GREEN)
        ws.row_dimensions[r].height = 34
        hr = r
        l1 = hr + 1
        l2 = l1 + LINES - 1
        Q["l1"], Q["l2"] = l1, l2
        A = lambda col: f"${col}${l1}:${col}${l2}"
        # job totals live in a block below; reference by name via placeholders filled after we know rows
        tot = {}
        for i in range(LINES):
            rr = l1 + i
            self.inp(ws[f"B{rr}"])
            self.inp(ws[f"C{rr}"], "#,##0", "right")
            self.inp(ws[f"E{rr}"], align="center")
            self.inp(ws[f"F{rr}"], align="center")
            self.inp(ws[f"G{rr}"], align="center")
            self.inp(ws[f"H{rr}"], "#,##0", "center")
            self.inp(ws[f"I{rr}"], "0", "center")
            m = lambda rng: f"MATCH($B{rr},{rng},0)"
            ws[f"Q{rr}"] = f'=IF(AND($B{rr}<>"",N($C{rr})>0),IF(ISNUMBER({m(S["svc"])}),1,0),0)'
            ws[f"R{rr}"] = f'=IF($Q{rr}=0,0,N(INDEX({S["svc_rate"]},{m(S["svc"])})))'
            cond = f'IF($E{rr}="","{c.DEFAULT_CONDITION}",$E{rr})'
            ws[f"S{rr}"] = f'=IFERROR(INDEX({S["cond_t"]},MATCH({cond},{S["cond"]},0)),1)'
            ws[f"T{rr}"] = f'=IFERROR(INDEX({S["cond_c"]},MATCH({cond},{S["cond"]},0)),1)'
            ws[f"U{rr}"] = f'=IF($F{rr}="",1,IFERROR(INDEX({S["acc_m"]},MATCH($F{rr},{S["acc"]},0)),1))'
            st = lambda rng: f'IF(OR($G{rr}="",N($H{rr})=0),0,N($H{rr})*IFERROR(INDEX({rng},MATCH($G{rr},{S["stain"]},0)),0))'
            ws[f"V{rr}"] = "=" + st(S["stain_min"])
            ws[f"W{rr}"] = "=" + st(S["stain_cost"])
            ws[f"X{rr}"] = f'=IF($Q{rr}=0,0,N(INDEX({S["svc_chem"]},{m(S["svc"])})))'
            ws[f"Y{rr}"] = f'=IF($Q{rr}=0,0,N(INDEX({S["svc_going"]},{m(S["svc"])})))'
            ws[f"Z{rr}"] = f'=IF($Q{rr}=0,0,IF(INDEX({S["svc_flat"]},{m(S["svc"])})="Yes",1,0))'
            ws[f"AA{rr}"] = f'=IF($Q{rr}=0,0,IF($R{rr}=0,0,$C{rr}/$R{rr}*60*$S{rr}*$U{rr})+$V{rr})'
            ws[f"AB{rr}"] = f'=IF($Q{rr}=0,0,$C{rr}/1000*$X{rr}*$T{rr}+$W{rr})'
            ws[f"AC{rr}"] = f'=IF($Q{rr}=0,0,N($M{rr})*N($I{rr}))'
            self.calc(ws[f"D{rr}"], align="center",
                      value=f'=IF($B{rr}="","",IFERROR(INDEX({S["svc_unit"]},{m(S["svc"])}),"not in SETTINGS"))')
            self.calc(ws[f"J{rr}"], NUM1, align="right", value=f'=IF($Q{rr}=0,"",$AA{rr})')
            self.calc(ws[f"K{rr}"], MONEY, align="right", value=f'=IF($Q{rr}=0,"",$AB{rr})')
            # L, M, N, O need the job totals: written after the totals block exists
        self.dv_list(ws, f"B{l1}:B{l2}", f"={S['svc']}")
        self.dv_list(ws, f"E{l1}:E{l2}", f"={S['cond']}")
        self.dv_list(ws, f"F{l1}:F{l2}", f"={S['acc']}")
        self.dv_list(ws, f"G{l1}:G{l2}", f"={S['stain']}")
        self.dv_list(ws, f"I{l1}:I{l2}", f"={S['line_visits']}")
        self.dv_num(ws, f"C{l1}:C{l2}")
        self.dv_num(ws, f"H{l1}:H{l2}")
        r = l2 + 1
        self.note(ws, f"B{r}:O{r}", "Blank condition = Normal; blank height = ground level. Stain qty is spots or sq ft "
                  "(see SETTINGS). Plan visits a year: 1 or 2 if this service is part of a maintenance plan.",
                  tint=PAPER, height=22)
        r += 2
        lines_end = r

        # ---------------- time and cost (left), price (right)
        def out(rr, key, label, f, fmt, bold=False, note="", col="B", vcol="F", ncol=None):
            self.label(ws[f"{col}{rr}"], label, bold=bold, indent=1)
            self.calc(ws[f"{vcol}{rr}"], fmt, bold=bold, align="right", value=f)
            if note and ncol:
                ws[f"{ncol}{rr}"] = note
                ws[f"{ncol}{rr}"].font = font(9, False, INK2)
                ws[f"{ncol}{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            Q[key] = f"${vcol}${rr}"
            ws.row_dimensions[rr].height = 20

        self.kicker(ws, f"B{r}", "3  ·  Time and cost", rule_to=6)
        self.kicker(ws, f"H{r}", "4  ·  Price", rule_to=15)
        r += 1
        t0 = r
        cv = lambda k: Q[k]
        crew = f"MAX(1,N({cv('crew')}))"
        cf = f"(1+N({S['crew_loss']})*({crew}-1))/{crew}"
        lab_rate = f"(N({S['owner_pay']})+({crew}-1)*N({S['helper_wage']})*(1+N({S['payroll']})))"
        n_lines = f"SUM({A('Q')})"
        for i, (key, label, f, fmt, bold) in enumerate([
                ("n", "Services on this quote", f"={n_lines}", "0", False),
                ("work", "Service time, one person", f"=SUM({A('AA')})", MINS, False),
                ("extra", "Setup, breakdown and water hauling",
                 f'=IF({n_lines}=0,0,N({S["setup_min"]})+IF({cv("water")}="No",N({S["water_min"]}),0))', MINS, False),
                ("onsite", "On site with your crew", "=0", MINS, False),
                ("drive_min", "Driving", f"=N({cv('drive')})", MINS, False),
                ("job_hours", "Total job time", "=0", HRS, True)]):
            out(t0 + i, key, label, f, fmt, bold)
        ws[cv("onsite").replace("$", "")] = f"=({cv('work')}+{cv('extra')})*{cf}"
        ws[cv("job_hours").replace("$", "")] = f"=IF({cv('n')}=0,0,({cv('onsite')}+{cv('drive_min')})/60)"
        r = t0 + 7
        costs = [("c_lab", "Labour on site", f"={cv('onsite')}/60*{lab_rate}"),
                 ("c_eq", "Equipment", f"={cv('job_hours')}*{S['equip_hr']}"),
                 ("c_ov", "Overhead", f"={cv('job_hours')}*{S['over_hr']}"),
                 ("c_fuel", "Pressure washer fuel", f"={cv('work')}*{cf}/60*N({S['machine_gph']})*N({S['fuel_price']})"),
                 ("c_chem", "Chemicals and materials", f"=SUM({A('AB')})"),
                 ("c_trav", "Travel (driving time + vehicle)", f"=IF({cv('n')}=0,0,{cv('drive_min')}/60*{lab_rate}+N({cv('miles')})*{S['vehicle_mile']})"),
                 ("c_fees", "Other job costs", f"=IF({cv('n')}=0,0,N({cv('other')}))")]
        for i, (key, label, f) in enumerate(costs):
            out(r + i, key, label, f, MONEY)
        c1 = r
        r += len(costs)
        out(r, "cost", "Cost of the job", f"=IF({cv('n')}=0,0,SUM(F{c1}:F{r - 1}))", MONEY, True)
        for col in "BCDEF":
            ws[f"{col}{r}"].fill = fill(GREEN)
        ws[f"B{r}"].font = font(10, True, PAPER)
        ws[f"F{r}"].font = font(11, True, BRASS)
        left_end = r

        # price block on the right (H label, M value, N:O note)
        r = t0
        inc, mg = f"N({S['rounding']})", f"N({S['margin']})"
        ptext = lambda rr, key, label, f, fmt, bold=False, note="": out(rr, key, label, f, fmt, bold, note, "H", "M", "N")
        ptext(r, "subtotal", "Services subtotal", f'=IF({cv("n")}=0,"",SUM({A("M")}))', MONEY, note="Sum of line prices")
        ptext(r + 1, "bundle", "Bundle discount",
              f'=IF({cv("n")}=0,"",IF({cv("n")}>=2,-ROUND({cv("subtotal")}*N({S["bundle_disc"]}),2),0))', MONEY,
              note="2 or more services")
        ptext(r + 2, "water_fee", "Water hauling",
              f'=IF({cv("n")}=0,"",IF({cv("water")}="No",N({S["water_fee"]}),0))', MONEY)
        ptext(r + 3, "travel_fee", "Travel surcharge",
              f'=IF({cv("n")}=0,"",ROUND(MAX(0,N({cv("miles")})-N({S["free_miles"]}))*N({S["surcharge_mile"]}),2))', MONEY)
        before = f'({cv("subtotal")}+{cv("bundle")}+{cv("water_fee")}+{cv("travel_fee")})'
        ptext(r + 4, "min_adj", "Minimum job charge top-up", f'=IF({cv("n")}=0,"",MAX(0,N({S["min_charge"]})-{before}))', MONEY)
        ptext(r + 5, "total", "Total price", f'=IF({cv("n")}=0,"",{before}+{cv("min_adj")})', MONEY, True)
        for col in "HIJKLM":
            ws[f"{col}{r + 5}"].fill = fill(GREEN)
        ws[f"H{r + 5}"].font = font(10, True, PAPER)
        ws[f"M{r + 5}"].font = font(11, True, BRASS)
        ptext(r + 6, "profit", "Profit", f'=IF({cv("n")}=0,"",{cv("total")}-{cv("cost")})', MONEY)
        ptext(r + 7, "profit_hr", "Profit per job hour",
              f'=IF(OR({cv("n")}=0,N({cv("job_hours")})=0),"",{cv("profit")}/{cv("job_hours")})', MONEY)
        ws[f"N{r + 7}"] = f'="Target "&{self.cur(S["target_profit_hr"])}'
        ws[f"N{r + 7}"].font = font(9, False, INK2)
        ws[f"N{r + 7}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ptext(r + 8, "price_hr", "Price per job hour", f'=IF(OR({cv("n")}=0,N({cv("job_hours")})=0),"",{cv("total")}/{cv("job_hours")})', MONEY)
        ptext(r + 9, "flat_sqft", "Flatwork sq ft on this quote", f'=SUMIFS({A("C")},{A("Z")},1)', "#,##0")
        ptext(r + 10, "flat_price", "Flatwork price per sq ft",
              f'=IF({cv("flat_sqft")}=0,"",SUMIFS({A("M")},{A("Z")},1)/{cv("flat_sqft")})', '#,##0.000')
        ws[f"N{r + 10}"] = "Before bundle discount"
        ws[f"N{r + 10}"].font = font(9, False, INK2)
        ws[f"N{r + 10}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ptext(r + 11, "plan_full", "Maintenance plan: services a year at full price", f'=SUM({A("AC")})', MONEY)
        ptext(r + 12, "plan", "Maintenance plan annual value",
              f'=IF(N({cv("plan_full")})=0,"",ROUND({cv("plan_full")}*(1-N({S["plan_disc"]})),2))', MONEY, True)
        ws[f"N{r + 12}"] = f'=IF({cv("plan")}="","No plan services marked",FIXED(100*N({S["plan_disc"]}),0)&"% plan discount")'
        ws[f"N{r + 12}"].font = font(9, False, INK2)
        ws[f"N{r + 12}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        right_end = r + 12
        # line cost, price, per unit, vs going (now that totals exist)
        shared = f"({cv('cost')}-{cv('c_chem')})"
        for i in range(LINES):
            rr = l1 + i
            self.calc(ws[f"L{rr}"], MONEY, align="right",
                      value=(f'=IF($Q{rr}=0,"",$AB{rr}+IF({cv("work")}=0,{shared}/{cv("n")},{shared}*$AA{rr}/{cv("work")}))'))
            raw = f"$L{rr}/(1-{mg})"
            self.calc(ws[f"M{rr}"], MONEY, bold=True, align="right",
                      value=f'=IF($Q{rr}=0,"",IF({inc}>0,ROUNDUP(ROUND({raw},6)/{inc},0)*{inc},ROUND({raw},2)))')
            self.calc(ws[f"N{rr}"], "#,##0.000", align="right", value=f'=IF($Q{rr}=0,"",$M{rr}/$C{rr})')
            g = f"($Y{rr}*$C{rr})"
            self.calc(ws[f"O{rr}"], align="center",
                      value=(f'=IF(OR($Q{rr}=0,$Y{rr}=0),"",IF($M{rr}>{g},FIXED(100*($M{rr}/{g}-1),0)&"% above",'
                             f'IF($M{rr}<{g},FIXED(100*(1-$M{rr}/{g}),0)&"% below","Same")))'))
        ws.conditional_formatting.add(f"O{l1}:O{l2}", FormulaRule(formula=[f'RIGHT($O{l1},5)="below"'], font=Font(color=GREEN, bold=True)))
        ws.conditional_formatting.add(f"O{l1}:O{l2}", FormulaRule(formula=[f'RIGHT($O{l1},5)="above"'], font=Font(color=NEG, bold=True)))

        # tiles at the top right
        self.kicker(ws, "H4", "Result", rule_to=15)
        P, PH, T = cv("total"), cv("profit_hr"), S["target_profit_hr"]
        self.tile(ws, 5, 8, 10, "TOTAL PRICE", f'=IF({P}="","–",{self.cur(P)})', "General", size=20)
        self.tile(ws, 5, 11, 13, "PROFIT PER JOB HOUR", f'=IF({PH}="","–",{self.cur(PH)})', "General", size=20)
        self.tile(ws, 5, 14, 15, "JOB TIME", f'=IF({cv("n")}=0,"–",FIXED({cv("job_hours")},1)&" h")', "General", size=20)
        ws.conditional_formatting.add("K6", FormulaRule(formula=[f'AND(ISNUMBER({PH}),{PH}<N({T}))'], font=Font(color="F2A79E")))
        # warning
        ws.merge_cells("H8:O9")
        w = ws["H8"]
        C_ = cv("cost")
        w.value = (f'=IF({cv("n")}=0,"Add a service and quantity to see a price.",'
                   f'IF({P}<{C_},"BELOW BREAK-EVEN: the price is "&{self.cur(f"{C_}-{P}")}&" under your cost for this job.",'
                   f'IF({PH}<N({T}),"LOW PROFIT: "&{self.cur(PH)}&" per job hour, below your target of "&{self.cur(T)}&".",'
                   f'"Priced for profit: "&{self.cur(PH)}&" profit per job hour on top of your own pay.")))')
        w.font = font(10, True, POS)
        w.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        for rr in (8, 9):
            for col in "HIJKLMNO":
                ws[f"{col}{rr}"].fill = fill(POS_TINT)
            ws.row_dimensions[rr].height = 22
        ws.conditional_formatting.add("H8:O9", FormulaRule(formula=['OR(LEFT($H$8,5)="BELOW",LEFT($H$8,3)="LOW")'],
                                                           font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add("H8:O9", FormulaRule(formula=['LEFT($H$8,3)="Add"'], font=Font(color=INK2, bold=True),
                                                           fill=fill(BRASS_TINT)))
        Q["warning"] = "$H$8"
        # fence / wall helper under the warning
        self.kicker(ws, "H11", "Area helper", rule_to=15)
        for i, (lab, key) in enumerate([("Length (ft): fence or house perimeter", "h_len"), ("Height (ft)", "h_ht"),
                                        ("Sides (fence: 1 or 2)", "h_sides")]):
            rr = 12 + i
            ws.merge_cells(f"H{rr}:L{rr}")
            self.label(ws[f"H{rr}"], lab, bold=False, indent=1)
            self.inp(ws[f"M{rr}"], "#,##0", "right")
            Q[key] = f"$M${rr}"
            self.dv_num(ws, f"M{rr}")
        ws.merge_cells("H15:L15")
        self.label(ws["H15"], "Area to enter as quantity (sq ft)", bold=True, indent=1)
        self.calc(ws["M15"], "#,##0", bold=True, align="right",
                  value='=IF(OR(N(M12)=0,N(M13)=0),"",M12*M13*MAX(1,N(M14)))')
        ws.merge_cells("N12:O15")
        ws["N12"] = "Fence: length × height × sides. House walls: perimeter × wall height (about 9-10 ft per storey)."
        ws["N12"].font = font(9, False, INK2)
        ws["N12"].alignment = Alignment(wrap_text=True, vertical="top", indent=1)

        # ---------------- save this quote
        r = max(left_end, right_end) + 2
        self.kicker(ws, f"B{r}", "Save this quote", rule_to=15)
        r += 1
        self.note(ws, f"B{r}:O{r}", "1. Select the green row below (B to J) and copy it.   2. On QUOTE LOG, click the first empty "
                  "Date cell.   3. Paste values only: Excel Ctrl+Alt+V then V (Mac: Cmd+Ctrl+V), Google Sheets "
                  "Ctrl+Shift+V.   4. Pick a status.", height=34, size=10, color=INK)
        r += 1
        heads = ["Date", "Client", "Address", "Property type", "Main services", "Total price", "Flatwork sq ft",
                 "Flatwork price", "Est. hours"]
        for i, t in enumerate(heads):
            self.header(ws[f"{L(2 + i)}{r}"], t)
        ws.row_dimensions[r].height = 30
        r += 1
        names = "&".join([f'IF($Q${l1}=1,$B${l1},"")'] + [f'IF($Q${l1 + k}=1," + "&$B${l1 + k},"")' for k in (1, 2)])
        main = f'=IF({cv("n")}=0,"",{names}&IF(SUM($Q${l1 + 3}:$Q${l2})>0," + more",""))'
        vals = [(f'=IF({cv("date")}="","",{cv("date")})', DATE), (f'=IF({cv("client")}="","",{cv("client")})', None),
                (f'=IF({cv("address")}="","",{cv("address")})', None), (f'=IF({cv("property")}="","",{cv("property")})', None),
                (main, None), (f"={P}", MONEY), (f'=IF({cv("n")}=0,"",{cv("flat_sqft")})', "#,##0"),
                (f'=IF({cv("n")}=0,"",SUMIFS({A("M")},{A("Z")},1))', MONEY),
                (f'=IF({cv("n")}=0,"",ROUND({cv("job_hours")},1))', "0.0")]
        for i, (f, fmt) in enumerate(vals):
            x = ws[f"{L(2 + i)}{r}"]
            self.calc(x, fmt, value=f)
            x.fill = fill(POS_TINT)
            x.font = font(10, True, INK)
            x.alignment = Alignment(horizontal="center" if i in (0, 3, 6, 8) else ("left" if i in (1, 2, 4) else None),
                                    vertical="center", wrap_text=True, indent=1 if i in (1, 2, 4) else 0)
        ws.row_dimensions[r].height = 46
        self.rows["save"] = r
        ws.freeze_panes = "A4"
        ws.print_area = f"A1:O{r}"
        ws.page_setup.orientation = "landscape"
        self.protect(ws)
        self.rows["qq_lines"] = (hr, l2)
        self.rows["qq_cost"] = (t0 - 1, max(left_end, right_end))
        # inputs
        d = c.QUOTE if self.sample else None
        setv = lambda k, v: ws.__setitem__(Q[k].replace("$", ""), v)
        if d:
            for k in ("date", "number", "client", "address", "property", "crew", "drive", "miles", "water", "other"):
                setv(k, d[k] if d[k] != 0 or k in ("crew", "drive", "miles") else None)
            for i, (svc, qty, cond, acc, stain, sq, pv) in enumerate(d["lines"]):
                rr = l1 + i
                ws[f"B{rr}"], ws[f"C{rr}"], ws[f"E{rr}"], ws[f"F{rr}"] = svc, qty, cond, acc
                ws[f"G{rr}"], ws[f"H{rr}"], ws[f"I{rr}"] = stain, sq, pv
        else:
            setv("date", "=TODAY()")
            setv("property", "Residential")
            setv("crew", 1)
            setv("water", "Yes")

    # ============================================================ CUSTOMER QUOTE
    def build_customer(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_CQ]
        QQ = q(S_QQ)
        Qr = lambda k: f"{QQ}!{self.Q[k]}"
        for col, w in {"A": 2, "B": 30, "C": 11, "D": 11, "E": 15, "F": 13, "G": 17, "H": 3, "I": 44}.items():
            ws.column_dimensions[col].width = w
        ws.sheet_view.showGridLines = False
        for r in range(1, 52):
            for col in range(1, 9):
                x = ws.cell(row=r, column=col)
                x.fill = fill(WHITE)
                x.font = Font(name=CUST, size=10, color="222222")
        f = lambda size=10, bold=False, color="222222", italic=False: Font(name=CUST, size=size, bold=bold, color=color, italic=italic)
        line, dark = Side(style="thin", color="BFBFBF"), Side(style="medium", color="222222")
        dash = Side(style="dashed", color="BFBFBF")
        ws.merge_cells("B2:B5")
        ws["B2"] = "Your logo here"
        ws["B2"].font = f(9, False, "9A9A9A", True)
        ws["B2"].alignment = Alignment(horizontal="center", vertical="center")
        for r in range(2, 6):
            ws[f"B{r}"].border = Border(left=dash, right=dash, top=dash if r == 2 else None, bottom=dash if r == 5 else None)
        right = Alignment(horizontal="right", vertical="center")
        for r, formula, ft in [(2, f'=IF({S["name"]}="","Your business name",{S["name"]})', f(16, True)),
                               (3, f'=IF({S["contact"]}="","",{S["contact"]})', f(10)),
                               (4, f'={S["phone"]}&IF(AND({S["phone"]}<>"",{S["email"]}<>""),"  ·  ","")&{S["email"]}', f(10)),
                               (5, f'={S["street"]}&IF(AND({S["street"]}<>"",{S["city"]}<>""),", ","")&{S["city"]}', f(10)),
                               (6, f'=IF({S["website"]}="","",{S["website"]})', f(10, False, "555555"))]:
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
        ws["B12"] = f'=IF({Qr("address")}="","",{Qr("address")})&IF({Qr("property")}="","","  ·  "&{Qr("property")})'
        ws["E11"] = f'=IF({Qr("date")}="","",{Qr("date")})'
        ws["F11"] = f'=IF({Qr("date")}="","",{Qr("date")}+N({S["valid_days"]}))'
        ws["G11"] = f'=IF({Qr("number")}="","",{Qr("number")})'
        for col in "EF":
            ws[f"{col}11"].number_format = DATE
            ws[f"{col}11"].alignment = Alignment(horizontal="left")
        ws["G11"].alignment = Alignment(horizontal="left")
        for col, t, al in (("B", "Service", "left"), ("E", "Quantity", "right"), ("G", "Price", "right")):
            ws[f"{col}14"] = t
            ws[f"{col}14"].font = f(9, True)
            ws[f"{col}14"].alignment = Alignment(horizontal=al, vertical="center")
        for col in "BCDEFG":
            ws[f"{col}14"].border = Border(bottom=dark)
            ws[f"{col}14"].fill = fill("F2F2F2")
        ws.row_dimensions[14].height = 22
        cur = lambda e: f'{S["currency"]}&FIXED({e},2)'
        l1 = self.Q["l1"]
        for i in range(LINES):
            r, src = 15 + i, l1 + i
            ok = f"{QQ}!$Q${src}=1"
            detail = (f'IF(OR({QQ}!$E${src}="",{QQ}!$E${src}="{c.DEFAULT_CONDITION}"),"",", "&LOWER({QQ}!$E${src})&" condition")'
                      f'&IF(OR({QQ}!$F${src}="",{QQ}!$F${src}="{c.ACCESS[0][0]}"),"",", "&LOWER({QQ}!$F${src}))'
                      f'&IF(OR({QQ}!$G${src}="",N({QQ}!$H${src})=0),"",", "&LOWER({QQ}!$G${src})&" stain treatment")')
            ws.merge_cells(f"B{r}:D{r}")
            ws[f"B{r}"] = f'=IF({ok},{QQ}!$B${src}&{detail},"")'
            ws[f"E{r}"] = f'=IF({ok},FIXED({QQ}!$C${src},0)&" "&{QQ}!$D${src},"")'
            ws[f"G{r}"] = f'=IF({ok},{cur(f"{QQ}!$M${src}")},"")'
            ws[f"B{r}"].alignment = Alignment(vertical="center", shrink_to_fit=True)
            for col in "EG":
                ws[f"{col}{r}"].alignment = Alignment(horizontal="right", vertical="center", shrink_to_fit=True)
            for col in "BCDEFG":
                ws[f"{col}{r}"].border = Border(bottom=line)
            ws.row_dimensions[r].height = 19
        r = 15 + LINES
        # totals: show only the lines that apply, with no gaps (k-th applicable item via a hidden helper list)
        items = [("Subtotal", "subtotal"), ("Bundle discount", "bundle"), ("Water hauling", "water_fee"),
                 ("Travel surcharge", "travel_fee"), ("Minimum job charge", "min_adj"), ("Total", "total")]
        h0 = 60                                                    # helper rows (outside the print area, column K:M)
        for i, (lab, key) in enumerate(items):
            v = Qr(key)
            hr_ = h0 + i
            ws[f"K{hr_}"] = lab
            ws[f"L{hr_}"] = f"=IF(ISNUMBER({v}),{v},0)"
            show = f"ISNUMBER({v})" if key in ("subtotal", "total") else f"AND(ISNUMBER({v}),{v}<>0)"
            ws[f"M{hr_}"] = f"=IF({show},1,0)+" + (f"M{hr_ - 1}" if i else "0")
        for col in "KLM":
            ws.column_dimensions[col].hidden = True
        K, Lr, M = (f"${cc}${h0}:${cc}${h0 + len(items) - 1}" for cc in "KLM")
        t_first = r
        for k in range(1, len(items) + 1):
            idx = f"MATCH({k},{M},0)"
            ws.merge_cells(f"B{r}:F{r}")
            ws[f"B{r}"] = f'=IFERROR(INDEX({K},{idx}),"")'
            v = f"INDEX({Lr},{idx})"
            ws[f"G{r}"] = f'=IFERROR(IF({v}<0,"–"&{cur(f"-{v}")},{cur(v)}),"")'
            ws[f"B{r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"G{r}"].alignment = Alignment(horizontal="right", vertical="center")
            ws[f"B{r}"].font = ws[f"G{r}"].font = f(10)
            ws.row_dimensions[r].height = 21
            r += 1
        rng = f"B{t_first}:G{r - 1}"
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'$B{t_first}="Total"'], font=Font(bold=True, size=11),
                                                       border=Border(top=dark)))
        r += 1
        # maintenance plan offer
        ws.merge_cells(f"B{r}:G{r + 1}")
        plan_lines = "&".join(
            f'IF(AND({QQ}!$Q${l1 + k}=1,N({QQ}!$I${l1 + k})>0),"; "&{QQ}!$B${l1 + k}&IF({QQ}!$I${l1 + k}=2," (twice a year)"," (once a year)"),"")'
            for k in range(LINES))
        ws[f"B{r}"] = (f'=IF({Qr("plan")}="","","Maintenance plan option: "&MID({plan_lines},3,500)&". "'
                       f'&{cur(Qr("plan"))}&" a year ("&FIXED(100*N({S["plan_disc"]}),0)&"% off each visit), billed per visit.")')
        ws[f"B{r}"].font = f(9.5, True, "222222")
        ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        self.rows["cq_plan"] = r
        for rr in (r, r + 1):
            ws.row_dimensions[rr].height = 20
        r += 3
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
        for col in "BCDFG":
            ws[f"{col}{r}"].border = Border(bottom=Side(style="thin", color="222222"))
        ws.row_dimensions[r].height = 26
        r += 1
        ws[f"B{r}"], ws[f"F{r}"] = "Customer signature", "Date"
        for col in "BF":
            ws[f"{col}{r}"].font = f(8, False, "666666")
        r += 2
        ws.merge_cells(f"B{r}:G{r}")
        ws[f"B{r}"] = (f'="Thank you for considering "&IF({S["name"]}="","us",{S["name"]})&". Questions? "'
                       f'&IF({S["phone"]}="",{S["email"]},{S["phone"]})')
        ws[f"B{r}"].font = f(9, False, "444444", True)
        ws[f"B{r}"].alignment = Alignment(horizontal="center")
        last = r
        ws["I2"] = "Printing this quote"
        ws["I2"].font = Font(name="Inter", size=10, bold=True, color=GREEN)
        ws.merge_cells("I3:I6")
        ws["I3"] = ("Everything here comes from QUICK QUOTE and SETTINGS. File > Print (or Save as PDF): it fits one "
                    "letter page. This column doesn't print.")
        ws.merge_cells("I8:I11")
        ws["I8"] = ("Logo: Insert > Picture and place it over the dashed box. If Excel blocks it, use Review > "
                    "Unprotect Sheet (no password).")
        for cc in ("I3", "I8"):
            ws[cc].alignment = Alignment(wrap_text=True, vertical="top")
            ws[cc].font = Font(name="Inter", size=9, color=INK2)
        ws.print_area = f"A1:H{last + 1}"
        ws.page_setup.orientation = "portrait"
        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
        ws.page_margins.left = ws.page_margins.right = 0.5
        ws.page_margins.top = ws.page_margins.bottom = 0.6
        ws.sheet_properties.tabColor = "BFBFBF"
        self.protect(ws)
        ws.protection.objects = False
        self.rows["cq_last"] = last

    # ============================================================ QUOTE LOG
    def build_log(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_LOG]
        widths = dict(B=13, C=20, D=22, E=12, F=58, G=12, H=11, I=12, J=10, K=12, L=13, M=28, N=15)
        self.page(ws, widths, 14, LOG_LAST + 1, "Quote log", "One row per quote. Paste the row from QUICK QUOTE, then track the answer.")
        R = lambda col: f"${col}${LOG_FIRST}:${col}${LOG_LAST}"
        st = R("K")
        dec = f'(COUNTIF({st},"Accepted")+COUNTIF({st},"Declined")+COUNTIF({st},"No reply"))'
        avg = lambda s: (f'IFERROR({self.cur(f"SUMIFS({R(chr(73))},{st},{chr(34)}{s}{chr(34)})/SUMIFS({R(chr(72))},{st},{chr(34)}{s}{chr(34)})")},"–")')
        tiles = [(2, 3, "QUOTES LOGGED", f'=COUNTA({R("C")})', "#,##0"),
                 (4, 5, "WIN RATE", f'=IF({dec}=0,"–",COUNTIF({st},"Accepted")/{dec})', "0%"),
                 (6, 6, "AVERAGE QUOTE", f'=IF(COUNT({R("G")})=0,"–",{self.cur(f"AVERAGEIF({R(chr(71))},{chr(34)}>0{chr(34)})")})', "General"),
                 (7, 10, "FLATWORK PER SQ FT · ACCEPTED", "=" + avg("Accepted").replace("FIXED(", "FIXED(", 1).replace(",2)", ",3)"), "General"),
                 (11, 14, "FLATWORK PER SQ FT · DECLINED", "=" + avg("Declined").replace(",2)", ",3)"), "General")]
        for c1, c2, lab, f, fmt in tiles:
            self.tile(ws, 4, c1, c2, lab, f, fmt)
        ws.merge_cells("B6:N6")
        acc = f'SUMIFS({R("I")},{st},"Accepted")/SUMIFS({R("H")},{st},"Accepted")'
        dcl = f'SUMIFS({R("I")},{st},"Declined")/SUMIFS({R("H")},{st},"Declined")'
        ws["B6"] = (f'=IFERROR(IF({dcl}>{acc}*1.15,"Declined quotes charge much more per sq ft of flatwork than accepted ones: '
                    f'check those jobs before cutting prices.",IF({acc}>{dcl}*1.15,"Accepted quotes charge more per sq ft of '
                    f'flatwork than declined ones: price is probably not why you lose jobs.","Accepted and declined quotes are '
                    f'priced about the same per sq ft of flatwork.")),"Mark quotes with flatwork Accepted or Declined to compare '
                    f'prices per sq ft.")')
        ws["B6"].font = font(9, True, GREEN)
        ws["B6"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[6].height = 24
        cur = f'" ("&{S["currency"]}&")"'
        heads = [("B", "Date"), ("C", "Client"), ("D", "Address"), ("E", "Property type"), ("F", "Main services"),
                 ("G", f'="Total price"&{cur}'), ("H", "Flatwork sq ft"), ("I", f'="Flatwork price"&{cur}'), ("J", "Est. hours"),
                 ("K", "Status"), ("L", "Follow-up date"), ("M", "Notes"), ("N", f'="Flatwork per sq ft"&{cur}')]
        for col, t in heads:
            self.header(ws[f"{col}7"], t, GREEN2 if col == "N" else GREEN, align="left" if col in "CDFM" else "center")
        ws.row_dimensions[7].height = 32
        for r in range(LOG_FIRST, LOG_LAST + 1):
            for col, fmt in (("B", DATE), ("C", None), ("D", None), ("E", None), ("F", None), ("G", MONEY), ("H", "#,##0"),
                             ("I", MONEY), ("J", "0.0"), ("K", None), ("L", DATE), ("M", None)):
                self.inp(ws[f"{col}{r}"], fmt, "center" if col in "BEJKL" else None)
            self.calc(ws[f"N{r}"], "#,##0.000", value=f'=IF(OR(N(H{r})=0,I{r}=""),"",I{r}/H{r})')
            ws[f"F{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
        rr = lambda col: f"{col}{LOG_FIRST}:{col}{LOG_LAST}"
        self.dv_list(ws, rr("E"), f"={S['property']}")
        self.dv_list(ws, rr("K"), f"={S['statuses']}")
        for col in "GHIJ":
            self.dv_num(ws, rr(col))
        v = DataValidation(type="date", operator="between", formula1="36526", formula2="73051", allow_blank=True,
                           showErrorMessage=True, errorTitle="Date", error="Enter a date, e.g. 4/6/2026.")
        ws.add_data_validation(v)
        v.add(rr("B"))
        v.add(rr("L"))
        ws.conditional_formatting.add(rr("K"), FormulaRule(formula=[f'$K{LOG_FIRST}="Accepted"'], font=Font(color=POS, bold=True), fill=fill(POS_TINT)))
        ws.conditional_formatting.add(rr("K"), FormulaRule(formula=[f'$K{LOG_FIRST}="Declined"'], font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add(rr("L"), FormulaRule(formula=[f'AND($K{LOG_FIRST}="Sent",$L{LOG_FIRST}<>"",$L{LOG_FIRST}<=TODAY())'],
                                                           font=Font(color=GREEN, bold=True), fill=fill(BRASS_TINT)))
        ws.freeze_panes = f"A{LOG_FIRST}"
        ws.auto_filter.ref = f"B7:N{LOG_LAST}"
        ws.print_area = f"A1:N{LOG_LAST}"
        ws.print_title_rows = "7:7"
        self.protect(ws)
        if self.sample:
            for i, row in enumerate(c.LOG):
                r = LOG_FIRST + i
                for col, val in zip("BCDEFGHIJKLM", row):
                    ws[f"{col}{r}"] = None if val == "" else val

    # ============================================================ JOB LOG
    def build_job(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_JOB]
        widths = dict(B=13, C=20, D=28, E=12, F=10, G=10, H=7, I=12, J=11, K=8, L=22, M=12, N=12, O=12, P=12, Q=3,
                      R=28, S=7, T=10, U=10, V=12, W=54)
        self.page(ws, widths, 23, JOB_LAST + 1, "Job log",
                  "Completed jobs: estimate vs actual. Over time this tunes your production rates.")
        R = lambda col: f"${col}${JOB_FIRST}:${col}${JOB_LAST}"
        yr = S["year"]
        hrs_tot = f"SUM({R('G')})"
        tiles = [(2, 3, "JOBS LOGGED", f'=COUNTA({R("C")})', "#,##0"),
                 (4, 5, "REVENUE (ALL JOBS)", f'={self.cur(f"SUM({R(chr(69))})")}', "General"),
                 (6, 9, "ACTUAL PROFIT PER HOUR", f'=IF(N({hrs_tot})=0,"–",{self.cur(f"SUM({R(chr(78))})/{hrs_tot}")})', "General"),
                 (10, 13, "TIME VS ESTIMATE (ALL JOBS)",
                  f'=IF(SUMIFS({R("F")},{R("G")},">0")=0,"–",IF({hrs_tot}>=SUMIFS({R("F")},{R("G")},">0"),"+","")&FIXED(100*({hrs_tot}/SUMIFS({R("F")},{R("G")},">0")-1),0)&"%")', "General"),
                 (14, 16, "UNPAID", f'={self.cur(f"SUMIFS({R(chr(69))},{R(chr(75))},{chr(34)}No{chr(34)})")}', "General")]
        for c1, c2, lab, f, fmt in tiles:
            self.tile(ws, 4, c1, c2, lab, f, fmt)
        cur = f'" ("&{S["currency"]}&")"'
        heads = [("B", "Date"), ("C", "Client"), ("D", "Main service"), ("E", f'="Quoted price"&{cur}'), ("F", "Est. hours"),
                 ("G", "Actual hours"), ("H", "Crew"), ("I", f'="Actual chemicals"&{cur}'), ("J", f'="Extra costs"&{cur}'),
                 ("K", "Paid?"), ("L", "Notes"), ("M", f'="Actual cost"&{cur}'), ("N", f'="Actual profit"&{cur}'),
                 ("O", f'="Profit per hour"&{cur}'), ("P", "Time vs estimate")]
        for col, t in heads:
            self.header(ws[f"{col}7"], t, GREEN2 if col in "MNOP" else GREEN, align="left" if col in "CDL" else "center")
        ws.row_dimensions[7].height = 32
        crew = lambda r: f"MAX(1,N(H{r}))"
        rate = lambda r: (f"(N({S['owner_pay']})+({crew(r)}-1)*N({S['helper_wage']})*(1+N({S['payroll']}))"
                          f"+{S['equip_hr']}+{S['over_hr']})")
        for r in range(JOB_FIRST, JOB_LAST + 1):
            for col, fmt in (("B", DATE), ("C", None), ("D", None), ("E", MONEY), ("F", "0.0"), ("G", "0.0"), ("H", "0"),
                             ("I", MONEY), ("J", MONEY), ("K", None), ("L", None)):
                self.inp(ws[f"{col}{r}"], fmt, "center" if col in "BFGHK" else None)
            done = f'AND(C{r}<>"",N(G{r})>0)'
            self.calc(ws[f"M{r}"], MONEY, value=f'=IF(NOT({done}),"",G{r}*{rate(r)}+N(I{r})+N(J{r}))')
            self.calc(ws[f"N{r}"], MONEY, bold=True, value=f'=IF(M{r}="","",N(E{r})-M{r})')
            self.calc(ws[f"O{r}"], MONEY, value=f'=IF(M{r}="","",N{r}/G{r})')
            self.calc(ws[f"P{r}"], '+0%;-0%;0%', align="center", value=f'=IF(OR(M{r}="",N(F{r})=0),"",G{r}/F{r}-1)')
        rr = lambda col: f"{col}{JOB_FIRST}:{col}{JOB_LAST}"
        self.dv_list(ws, rr("D"), f"={S['svc']}")
        self.dv_list(ws, rr("K"), f"={S['yesno']}")
        for col in "EFGIJ":
            self.dv_num(ws, rr(col))
        self.dv_num(ws, rr("H"), "whole", 1, 6, "Crew", "Enter 1 to 6 people.")
        ws.conditional_formatting.add(rr("K"), FormulaRule(formula=[f'$K{JOB_FIRST}="No"'], font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add(rr("N"), FormulaRule(formula=[f'AND(ISNUMBER($N{JOB_FIRST}),$N{JOB_FIRST}<0)'], font=Font(color=NEG, bold=True)))
        ws.conditional_formatting.add(rr("P"), FormulaRule(formula=[f'AND(ISNUMBER($P{JOB_FIRST}),ABS($P{JOB_FIRST})>0.15)'], font=Font(color=NEG, bold=True)))
        # ---- by service type
        self.kicker(ws, "R6", "Estimate vs actual by service", rule_to=23)
        for col, t in (("R", "Main service"), ("S", "Jobs"), ("T", "Est. hours"), ("U", "Actual hours"), ("V", "Difference"),
                       ("W", "What to do")):
            self.header(ws[f"{col}7"], t, align="left" if col in "RW" else "center")
        s1, s2 = self.rows["svc"]
        for i in range(SVC_ROWS):
            r = JOB_FIRST + i
            src = f"{q(S_SET)}!$B${s1 + i}"
            ws[f"R{r}"] = f'=IF({src}="","",{src})'
            ws[f"R{r}"].font = font(10, True, INK)
            ws[f"R{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
            cnt = f'COUNTIFS({R("D")},$R{r},{R("G")},">0",{R("F")},">0")'
            self.calc(ws[f"S{r}"], "0", align="center", value=f'=IF($R{r}="","",IF({cnt}=0,"",{cnt}))')
            self.calc(ws[f"T{r}"], "0.0", align="center", value=f'=IF(S{r}="","",SUMIFS({R("F")},{R("D")},$R{r},{R("G")},">0",{R("F")},">0"))')
            self.calc(ws[f"U{r}"], "0.0", align="center", value=f'=IF(S{r}="","",SUMIFS({R("G")},{R("D")},$R{r},{R("G")},">0",{R("F")},">0"))')
            self.calc(ws[f"V{r}"], '+0%;-0%;0%', bold=True, align="center", value=f'=IF(S{r}="","",U{r}/T{r}-1)')
            rate_ref = f"{q(S_SET)}!$E${s1 + i}"
            self.calc(ws[f"W{r}"], value=(f'=IF(S{r}="","",IF(V{r}>0.15,"Slower than estimated: try "'
                                         f'&FIXED(N({rate_ref})*T{r}/U{r},0)&" units/h on SETTINGS",IF(V{r}<-0.15,"Faster than estimated: try "'
                                         f'&FIXED(N({rate_ref})*T{r}/U{r},0)&" units/h on SETTINGS","On target.")))'))
            ws[f"W{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
        last = JOB_FIRST + SVC_ROWS - 1
        ws.conditional_formatting.add(f"W{JOB_FIRST}:W{last}", FormulaRule(formula=[f'LEFT($W{JOB_FIRST},6)="Slower"'], font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add(f"W{JOB_FIRST}:W{last}", FormulaRule(formula=[f'LEFT($W{JOB_FIRST},6)="Faster"'], font=Font(color=GREEN, bold=True), fill=fill(BRASS_TINT)))
        ws.conditional_formatting.add(f"W{JOB_FIRST}:W{last}", FormulaRule(formula=[f'$W{JOB_FIRST}="On target."'], font=Font(color=POS, bold=True)))
        self.note(ws, f"R{last + 2}:W{last + 4}", "Compares estimated and actual hours on jobs you've logged (by main service). "
                  "More than 15 % off suggests changing that service's units per hour on SETTINGS. Wait for at least 3 jobs "
                  "before changing a rate: one odd job can mislead.", tint=BRASS_TINT)
        # hidden helpers for the dashboard: month, year, category
        for r in range(JOB_FIRST, JOB_LAST + 1):
            ws[f"X{r}"] = f'=IF(OR(B{r}="",E{r}=""),"",MONTH(B{r}))'
            ws[f"Y{r}"] = f'=IF(OR(B{r}="",E{r}=""),"",YEAR(B{r}))'
            ws[f"Z{r}"] = f'=IF(D{r}="","",IFERROR(INDEX({S["svc_cat"]},MATCH(D{r},{S["svc"]},0)),""))'
        for col in "XYZ":
            ws.column_dimensions[col].hidden = True
        ws.freeze_panes = f"A{JOB_FIRST}"
        ws.print_area = f"A1:W{JOB_LAST}"
        ws.page_setup.orientation = "landscape"
        self.protect(ws)
        self.S["job"] = lambda col: f"{q(S_JOB)}!${col}${JOB_FIRST}:${col}${JOB_LAST}"
        if self.sample:
            for i, row in enumerate(c.JOBS):
                r = JOB_FIRST + i
                for col, val in zip("BCDEFGHIJK", row):
                    ws[f"{col}{r}"] = val if val != 0 or col in "GHI" else None

    # ============================================================ MAINTENANCE PLANS
    def build_plans(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_PLAN]
        widths = dict(B=20, C=20, D=44, E=14, F=12, G=13, H=11, I=20, J=10, K=13, L=13, M=17)
        self.page(ws, widths, 13, PLAN_LAST + 1, "Maintenance plans",
                  "Clients on recurring plans. Plans due in the next 30 days are highlighted.")
        R = lambda col: f"${col}${PLAN_FIRST}:${col}${PLAN_LAST}"
        due30 = f'COUNTIFS({R("H")},"Active",{R("L")},">="&TODAY(),{R("L")},"<="&TODAY()+30)'
        tiles = [(2, 3, "ACTIVE PLANS", f'=COUNTIF({R("H")},"Active")', "#,##0"),
                 (4, 5, "ANNUAL PLAN REVENUE", f'={self.cur(f"SUMIFS({R(chr(75))},{R(chr(72))},{chr(34)}Active{chr(34)})")}', "General"),
                 (6, 8, "DUE IN THE NEXT 30 DAYS", f"={due30}", "#,##0"),
                 (9, 13, "OVERDUE", f'=COUNTIFS({R("H")},"Active",{R("L")},"<"&TODAY())', "#,##0")]
        for c1, c2, lab, f, fmt in tiles:
            self.tile(ws, 4, c1, c2, lab, f, fmt)
        cur = f'" ("&{S["currency"]}&")"'
        heads = [("B", "Client"), ("C", "Address"), ("D", "Services"), ("E", "Frequency"), ("F", f'="Price per visit"&{cur}'),
                 ("G", "Last clean"), ("H", "Status"), ("I", "Notes"), ("J", "Visits a year"), ("K", f'="Annual value"&{cur}'),
                 ("L", "Next due"), ("M", "Due")]
        for col, t in heads:
            self.header(ws[f"{col}7"], t, GREEN2 if col in "JKLM" else GREEN, align="left" if col in "BCDI" else "center")
        ws.row_dimensions[7].height = 32
        for r in range(PLAN_FIRST, PLAN_LAST + 1):
            for col, fmt in (("B", None), ("C", None), ("D", None), ("E", None), ("F", MONEY), ("G", DATE), ("H", None), ("I", None)):
                self.inp(ws[f"{col}{r}"], fmt, "center" if col in "EGH" else None)
            self.calc(ws[f"J{r}"], "0", align="center",
                      value=f'=IF(OR(B{r}="",E{r}=""),"",IFERROR(INDEX({S["plan_visits"]},MATCH(E{r},{S["plan_freq"]},0)),""))')
            self.calc(ws[f"K{r}"], MONEY, value=f'=IF(OR(J{r}="",H{r}<>"Active"),"",N(F{r})*J{r})')
            self.calc(ws[f"L{r}"], DATE, align="center",
                      value=f'=IF(OR(J{r}="",G{r}="",H{r}<>"Active"),"",EDATE(G{r},12/J{r}))')
            self.calc(ws[f"M{r}"], align="center",
                      value=(f'=IF(L{r}="",IF(AND(B{r}<>"",H{r}<>"Active",H{r}<>""),H{r},""),IF(L{r}<TODAY(),"Overdue",'
                             f'IF(L{r}-TODAY()<=30,"Due in "&(L{r}-TODAY())&" days","Scheduled")))'))
        rr = lambda col: f"{col}{PLAN_FIRST}:{col}{PLAN_LAST}"
        self.dv_list(ws, rr("E"), f"={S['plan_freq']}")
        self.dv_list(ws, rr("H"), f"={S['plan_status']}")
        self.dv_num(ws, rr("F"))
        v = DataValidation(type="date", operator="between", formula1="36526", formula2="73051", allow_blank=True,
                           showErrorMessage=True, errorTitle="Date", error="Enter a date, e.g. 4/6/2026.")
        ws.add_data_validation(v)
        v.add(rr("G"))
        rng = f"B{PLAN_FIRST}:M{PLAN_LAST}"
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT($M{PLAN_FIRST},3)="Due"'], fill=fill(BRASS_TINT)))
        ws.conditional_formatting.add(rr("M"), FormulaRule(formula=[f'LEFT($M{PLAN_FIRST},3)="Due"'], font=Font(color=GREEN, bold=True)))
        ws.conditional_formatting.add(rr("M"), FormulaRule(formula=[f'$M{PLAN_FIRST}="Overdue"'], font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.freeze_panes = f"A{PLAN_FIRST}"
        ws.auto_filter.ref = f"B7:M{PLAN_LAST}"
        ws.print_area = f"A1:M{PLAN_LAST}"
        ws.page_setup.orientation = "landscape"
        self.protect(ws)
        self.S["plan"] = lambda col: f"{q(S_PLAN)}!${col}${PLAN_FIRST}:${col}${PLAN_LAST}"
        if self.sample:
            for i, row in enumerate(c.PLANS):
                r = PLAN_FIRST + i
                for col, val in zip("BCDEFGHI", row):
                    ws[f"{col}{r}"] = val if val != "" else None

    # ============================================================ DASHBOARD
    def build_dashboard(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_DASH]
        widths = {L(k): 12.5 for k in range(2, 14)}
        widths["B"] = 15
        self.page(ws, widths, 13, 80, "Dashboard", "Your break-even rate, quotes, jobs and plans at a glance.")
        J, P = S["job"], S["plan"]
        st = f"{q(S_LOG)}!$K${LOG_FIRST}:$K${LOG_LAST}"
        ws.merge_cells("B4:M4")
        self.label(ws["B4"], f'=IF({S["name"]}="","Your business",{S["name"]})&"  ·  "&{S["year"]}', color=GREEN, size=11)
        dec = f'(COUNTIF({st},"Accepted")+COUNTIF({st},"Declined")+COUNTIF({st},"No reply"))'
        ytd = f'SUMIFS({J("E")},{J("Y")},N({S["year"]}))'
        hrs = f"SUM({J('G')})"
        eom = "DATE(YEAR(TODAY()),MONTH(TODAY())+1,0)"
        tiles1 = [("BREAK-EVEN HOURLY RATE", f'={self.cur(S["breakeven_hr"])}'),
                  ("AVERAGE JOB PRICE", f'=IF(COUNT({J("E")})=0,"–",{self.cur(f"AVERAGE({J(chr(69))})")})'),
                  ("WIN RATE", f'=IF({dec}=0,"–",FIXED(100*COUNTIF({st},"Accepted")/{dec},0)&"%")'),
                  ("REVENUE YEAR TO DATE", f'={self.cur(ytd)}')]
        tiles2 = [("ACTUAL PROFIT PER HOUR", f'=IF(N({hrs})=0,"–",{self.cur(f"SUM({J(chr(78))})/{hrs}")})'),
                  ("ANNUAL PLAN REVENUE", f'={self.cur(f"SUMIFS({P(chr(75))},{P(chr(72))},{chr(34)}Active{chr(34)})")}'),
                  ("PLANS DUE THIS MONTH", f'=COUNTIFS({P("H")},"Active",{P("L")},"<="&{eom})')]
        for i, (lab, f) in enumerate(tiles1):
            self.tile(ws, 6, 2 + 3 * i, 4 + 3 * i, lab, f, "General")
        for i, (lab, f) in enumerate(tiles2):
            self.tile(ws, 9, 2 + 4 * i, 5 + 4 * i, lab, f, "General" if i < 2 else "0")
        ws.row_dimensions[8].height = 6

        def head(r, cols):
            for col, t in cols:
                self.header(ws[f"{col}{r}"], t, align="left" if col == "B" else "center")
            ws.row_dimensions[r].height = 24

        rows = {}
        r = 12
        rows["months"] = r
        self.kicker(ws, f"B{r}", "Monthly revenue  ·  job log", rule_to=13)
        hr = r + 1
        head(hr, [("B", "Month"), ("C", "Jobs"), ("D", "Revenue"), ("E", "Profit")])
        for m in range(12):
            rr = hr + 1 + m
            ws[f"B{rr}"] = c.MONTHS[m][:3]
            ws[f"B{rr}"].font = font(10, True, INK)
            ws[f"B{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            yrc = f"{J('Y')},N({S['year']})"
            self.calc(ws[f"C{rr}"], "0", align="center", value=f"=COUNTIFS({J('X')},{m + 1},{yrc})")
            self.calc(ws[f"D{rr}"], MONEY0, value=f"=SUMIFS({J('E')},{J('X')},{m + 1},{yrc})")
            self.calc(ws[f"E{rr}"], MONEY0, value=f"=SUMIFS({J('N')},{J('X')},{m + 1},{yrc})")
        ch = BarChart()
        ch.type, ch.style = "col", 10
        ch.add_data(Reference(ws, min_col=4, max_col=5, min_row=hr, max_row=hr + 12), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=hr + 1, max_row=hr + 12))
        for s_, colr in zip(ch.series, (GREEN, "E3C68F")):
            s_.graphicalProperties.solidFill = colr
            s_.graphicalProperties.line.solidFill = colr
        BP.clean_chart(ch, legend=True)
        ch.gapWidth, ch.overlap = 50, -10
        ch.height, ch.width = 7.0, 17.2
        ch.anchor = f"G{hr}"
        ws.add_chart(ch)
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
            ws[f"B{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
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
        r = q2 + 5
        rows["cats"] = r
        self.kicker(ws, f"B{r}", "Revenue by service type  ·  job log", rule_to=13)
        hr = r + 1
        head(hr, [("B", "Service type"), ("C", "Jobs"), ("D", "Revenue"), ("E", "Share")])
        d1 = hr + 1
        n = len(c.CATEGORIES)
        for i in range(n):
            rr = d1 + i
            ws[f"B{rr}"] = f"=INDEX({S['cats']},{i + 1})"
            ws[f"B{rr}"].font = font(10, True, INK)
            ws[f"B{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            self.calc(ws[f"C{rr}"], "0", align="center", value=f"=COUNTIFS({J('Z')},B{rr},{J('E')},\">0\")")
            self.calc(ws[f"D{rr}"], MONEY0, value=f"=SUMIFS({J('E')},{J('Z')},B{rr})")
            self.calc(ws[f"E{rr}"], "0%", align="center", value=f'=IF(SUM($D${d1}:$D${d1 + n - 1})=0,"",D{rr}/SUM($D${d1}:$D${d1 + n - 1}))')
        BP.databar(ws, f"E{d1}:E{d1 + n - 1}", BRASS, max_value=1)
        ch = BarChart()
        ch.type, ch.style = "bar", 10
        ch.add_data(Reference(ws, min_col=4, min_row=d1, max_row=d1 + n - 1), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=d1, max_row=d1 + n - 1))
        s_ = ch.series[0]
        s_.graphicalProperties.solidFill = BRASS
        s_.graphicalProperties.line.solidFill = BRASS
        BP.clean_chart(ch, legend=False)
        ch.x_axis.scaling.orientation = "maxMin"
        ch.gapWidth = 50
        ch.height, ch.width = 5.6, 17.2
        ch.anchor = f"G{hr}"
        ws.add_chart(ch)
        r = d1 + n + 2
        self.note(ws, f"B{r}:M{r}", DISCLAIMER, height=30, size=9, color=INK, bold=True)
        rows["end"] = r
        self.rows["dash"] = rows
        ws.print_area = f"A1:M{r}"
        self.protect(ws)

    # ============================================================ START HERE
    def build_start(self):
        c = self.cfg
        ws = self.ws[S_START]
        self.page(ws, {"B": 5, "C": 30, "D": 30, "E": 30, "F": 24}, 6, 80, "Start here",
                  "Read this first. Setting up takes about 15 minutes.", landscape=False)
        self.note(ws, "B4:F4", "Quote any pressure washing job in two minutes, without underpricing.", tint=PAPER, height=32,
                  size=15, color=GREEN, bold=True)
        ws["B4"].font = Font(name=TITLE, size=15, bold=True, color=GREEN)
        self.note(ws, "B5:F5", "Exterior cleaning is priced by surface and size, with extras for stains, growth, height "
                  "and access. This workbook adds up what each job really costs you (your time, setup, chemicals, fuel, "
                  "equipment, insurance, driving) and prices every service so you keep a profit on top of your own pay.",
                  tint=PAPER, height=48, size=10, color=INK)
        r = 7
        self.kicker(ws, f"B{r}", "Quick start in 3 steps", rule_to=6)
        r = 8
        for num, head, body, sheet in [
                ("1", "Settings (once)", "Your business details, pay, equipment, overhead, fuel, services with production "
                 "rates and chemical costs. Replace the example values with your own.", S_SET),
                ("2", "Quote a job", "Add up to 10 services with quantities, condition, height and stains. The total, profit "
                 "and warnings appear above. CUSTOMER QUOTE is ready to print.", S_QQ),
                ("3", "Save it to the log", "Copy the green row at the bottom of QUICK QUOTE into QUOTE LOG. After the job, "
                 "log actual hours on JOB LOG to tune your production rates.", S_LOG)]:
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
        self.link(ws[f"C{r}"], "Plans and jobs  ›", S_PLAN)
        ws[f"C{r}"].alignment = Alignment(vertical="top")
        ws.merge_cells(f"D{r}:F{r}")
        ws[f"D{r}"] = "Put repeat clients on MAINTENANCE PLANS to see who is due next; the DASHBOARD sums it all up."
        ws[f"D{r}"].font = font(10, color=INK2)
        ws[f"D{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 34
        r += 2
        self.kicker(ws, f"B{r}", "Colour key", rule_to=6)
        r += 1
        for kind, head, body in [("inp", "Type here", "White cell with a border: your numbers, or pick from the dropdown."),
                                 ("calc", "Calculated", "Shaded cell: a formula, locked so it can't be overwritten by accident."),
                                 ("tile", "Result", "Green block with a brass figure: a key number."),
                                 ("warn", "Check this", "Red: below break-even, low profit, overdue plans or slow production rates.")]:
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
        self.kicker(ws, f"B{r}", "Measuring surfaces", rule_to=6)
        r += 1
        tips = ["Driveways, patios, roofs: Google Maps on a computer (right-click > Measure distance, click around the "
                "area back to the start) or Google Earth's polygon ruler shows square feet.",
                "Roofs from above show the flat footprint: steeper roofs have more surface. Add about 10-20 % for a "
                "moderate pitch and pick Steep roof pitch for steep ones.",
                "House walls: perimeter × wall height (about 9-10 ft per storey), minus large garage doors. The area "
                "helper on QUICK QUOTE does the sum.",
                "Fences: length × height × sides (1 or 2). Gutters: measure the run in linear feet."]
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
        self.kicker(ws, f"B{r}", "Reminders  ·  not legal advice", rule_to=6, color=NEG)
        r += 1
        for t in c.COMPLIANCE:
            self.note(ws, f"B{r}:F{r}", t, tint=NEG_TINT, height=30, size=9.5, color=NEG, bold=True)
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Guide and Google Sheets", rule_to=6)
        r += 1
        self.note(ws, f"B{r}:F{r}", f"Quick-start guide: {c.GUIDE_NAME} (in your download).   "
                  "Google Sheets copy: [GOOGLE SHEETS COPY LINK]", tint=PAPER, height=30, size=10, color=INK)
        r += 2
        self.note(ws, f"B{r}:F{r}", DISCLAIMER, tint=BRASS_TINT, height=36, size=10, color=INK, bold=True)
        if self.sample:
            r += 2
            self.note(ws, f"B{r}:F{r}", "SAMPLE FILE: a fictional business, BrightSide Exterior Cleaning, with example quotes, "
                      "10 completed jobs and 8 maintenance plans. Use the blank file for your own business.", tint=POS_TINT,
                      height=34, size=10, color=POS, bold=True)
        ws.print_area = f"A1:G{r + 1}"
        self.protect(ws)

    # ============================================================ build
    def build(self):
        self.build_settings()
        self.build_quote()
        self.build_customer()
        self.build_log()
        self.build_job()
        self.build_plans()
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
        return BP.add_sidebars(self.wb, NAV, {S_START: 70, S_SET: self.rows["set_last"] + 2, S_QQ: 70, S_LOG: 120,
                                              S_JOB: 120, S_PLAN: 120, S_DASH: 70}, skip=(S_CQ,), max_last=220)


def main(cfg, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for sample in (False, True):
        e = PWEngine(cfg, sample)
        wb = e.build()
        layers = e.add_sidebars()
        p = out_dir / (cfg.OUT_NAME + ("_SAMPLE" if sample else "") + ".xlsx")
        wb.save(p)
        BP.finish(p, layers)
        paths.append(p)
        print("wrote", p)
    return paths
