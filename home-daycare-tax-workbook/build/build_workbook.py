"""Brass Ledger — Home Daycare Tax Workbook (time-space percentage calculator and expense tracker).

Builds a blank workbook and a SAMPLE workbook (a fictional provider, tax year 2026) with openpyxl. Every calculated cell
is a formula. No macros, no Excel Tables, no dynamic arrays, no TEXT() date codes. Works in Excel 2016+ and Google Sheets.

Tax rules (checked against IRS Pub. 587 (2025), Instructions for Form 8829 (2025), Form 8829 (2025 and 2026 draft),
Schedule C (2026)) are listed in the test report.

Usage: python build_workbook.py [OUT_DIR]
"""
from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, Protection, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "productivity-bundle" / "build"))
import bl_polish as BP  # noqa: E402
from openpyxl.chart import BarChart, DoughnutChart, Reference  # noqa: E402
from openpyxl.chart.series import DataPoint  # noqa: E402

from xlkit import (BORDER, BOX, BRASS, BRASS_TINT, CALC, DATE, GREEN, GREEN2, GREY, HRS, INK, INK2, Kit, MONEY, NEG,
                   NEG_TINT, PAPER, PCT2, POS, POS_TINT, SQFT, TIME, TITLE, WHITE, fill, font, q)

PRODUCT = "Home Daycare Tax Workbook"
OUT_NAME = "BrassLedger_Home_Daycare_Tax_Workbook"
S_DASH = "DASHBOARD"
S_START, S_SET, S_ROOMS, S_HOURS, S_EXP, S_MEALS, S_MILES, S_SUM, S_STMT, S_PREP = (
    "START HERE", "SETTINGS", "ROOMS", "HOURS LOG", "EXPENSES", "MEALS", "MILEAGE", "SUMMARY", "TIME-SPACE STATEMENT",
    "FOR YOUR TAX PREPARER")
ORDER = [S_START, S_DASH, S_SET, S_ROOMS, S_HOURS, S_EXP, S_MEALS, S_MILES, S_SUM, S_STMT, S_PREP]

# icon sidebar: (tab, icon, short label shown in Google Sheets)
NAV = [(S_DASH, "bar_chart", "Home"), (S_START, "question", "Start"), (S_SET, "gear", "Setup"), (S_ROOMS, "house", "Rooms"),
       (S_HOURS, "clock", "Hours"), (S_EXP, "receipt", "Costs"), (S_MEALS, "meal", "Meals"), (S_MILES, "car", "Miles"),
       (S_SUM, "pie", "Summary"), (S_STMT, "clipboard", "Statement"), (S_PREP, "people", "Preparer")]
DONUT = ["1F3D36", "D29A3A", "6B7F79", "2E7D4F", "C9D3CF"]

DISCLAIMER = ("For record keeping and estimates only. Not tax or legal advice. Tax rules and rates change; confirm with IRS "
              "Publication 587, the Form 8829 instructions, or a tax professional. For US providers.")

# ---------------------------------------------------------------- SETTINGS cells
SETQ = q(S_SET)
SC = dict(name="$C$6", year="$C$7", start="$C$8", stop="$C$9", first="$C$10", last="$C$11", days="$C$12", hours="$C$13",
          leap="$C$14", caldays="$C$15", srate="$C$20", smax="$C$21", mile1="$C$22", mchange="$C$23", mile2="$C$24",
          bfast="$C$25", lunch="$C$26", dinner="$C$27", snack="$C$28", food="$C$29", reimb="$C$30")
USUAL_FIRST = 36                                       # Mon..Sun rows 36..42
SYS_FIRST = 47                                         # system lists start
TYPES = ["Direct (business only)", "Direct home: exclusive area", "Direct home: shared area", "Indirect home",
         "Shared household", "Personal"]
USES = ["Exclusive child care", "Regular child care + family", "Not used for child care"]
ACTIVITIES = ["Preparation and setup", "Cleaning", "Meal preparation", "Paperwork and records", "Parent meetings",
              "Planning activities", "Training or inspection at home", "Other business use"]
FOODS = ["Standard meal and snack rates", "Actual food receipts"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
# (category, goes on, line, note). Lines: Schedule C (2026 form), Form 8829 (2025 form; 2026 draft has the same lines).
CATS = [
    ("Advertising", "Schedule C", "8", ""),
    ("Car and truck (actual costs)", "Schedule C", "9", "Don't use with the standard mileage rate"),
    ("Contract labor", "Schedule C", "11", ""),
    ("Equipment and furniture", "Schedule C", "13", "May be depreciated or expensed: your preparer decides"),
    ("Liability insurance", "Schedule C", "15", "Business insurance, not home insurance"),
    ("Legal and professional fees", "Schedule C", "17", "Tax preparation, legal advice"),
    ("Office expense", "Schedule C", "18", ""),
    ("Equipment rental", "Schedule C", "20a", ""),
    ("Repairs to equipment", "Schedule C", "21", "Not home repairs"),
    ("Toys and play equipment", "Schedule C", "22", "Supplies"),
    ("Craft and learning supplies", "Schedule C", "22", "Supplies"),
    ("Household supplies", "Schedule C", "22", "Cleaning products, paper goods (usually Shared household)"),
    ("Licenses and permits", "Schedule C", "23", "Taxes and licenses"),
    ("Travel", "Schedule C", "24a", ""),
    ("Wages", "Schedule C", "26", ""),
    ("Training and education", "Schedule C", "27b", "Other expenses (Part V)"),
    ("Field trips and activities", "Schedule C", "27b", "Other expenses (Part V)"),
    ("Other business expense", "Schedule C", "27b", "Other expenses (Part V)"),
    ("Food (actual receipts)", "Food", "27b", "Counted only if Food method = Actual food receipts"),
    ("Mortgage interest", "Form 8829", "10", "Part may belong on line 16: your preparer decides"),
    ("Real estate taxes", "Form 8829", "11", "Part may belong on line 17: your preparer decides"),
    ("Home insurance", "Form 8829", "18", "Homeowner's or renter's insurance"),
    ("Rent", "Form 8829", "19", ""),
    ("Home repairs and maintenance", "Form 8829", "20", ""),
    ("Utilities", "Form 8829", "21", "Electric, gas, water, trash, internet"),
    ("Other home expenses", "Form 8829", "22", "HOA fees, security system"),
    ("Personal (not deductible)", "Personal", "", "Recorded but never counted"),
]
CAT_FIRST = SYS_FIRST + 14                             # category table rows
CAT_LAST = CAT_FIRST + len(CATS) - 1


def S(key):
    return f"{SETQ}!{SC[key]}"


def srng(c1, r1, c2, r2):
    return f"{SETQ}!${c1}${r1}:${c2}${r2}"


T_RNG = srng("B", SYS_FIRST + 2, "B", SYS_FIRST + 1 + len(TYPES))
U_RNG = srng("C", SYS_FIRST + 2, "C", SYS_FIRST + 1 + len(USES))
A_RNG = srng("D", SYS_FIRST + 2, "D", SYS_FIRST + 1 + len(ACTIVITIES))
F_RNG = srng("E", SYS_FIRST + 2, "E", SYS_FIRST + 1 + len(FOODS))
CAT_NAMES = srng("B", CAT_FIRST, "B", CAT_LAST)
CAT_FORM = srng("C", CAT_FIRST, "C", CAT_LAST)
CAT_LINE = srng("D", CAT_FIRST, "D", CAT_LAST)


def TYPE(i):
    return f"{SETQ}!$B${SYS_FIRST + 2 + i}"


# ---------------------------------------------------------------- ROOMS
R_FIRST, R_N = 18, 30
R_LAST = R_FIRST + R_N - 1
RM = dict(total="$C$6", excl="$C$7", reg="$C$8", none="$C$9", listed="$C$10", home="$C$11", excl_pct="$C$13",
          reg_pct="$C$14", space_pct="$C$15")


def RMQ(k):
    return f"{q(S_ROOMS)}!{RM[k]}"


# ---------------------------------------------------------------- HOURS LOG
H_FIRST = 9
H_LAST = H_FIRST + 366 - 1
HC = dict(date="B", day="C", start="D", end="E", typed="F", other="G", what="H", notes="I", closed="J", conf="K",
          child="L", oth="M", total="N", status="O", inbiz="Q", counted="R", chours="S", proj="T", month="U", edited="V")
H_INPUTS = ["start", "end", "typed", "other", "what", "notes", "closed", "conf"]


def HR(k):
    c = HC[k]
    return f"{q(S_HOURS)}!${c}${H_FIRST}:${c}${H_LAST}"


# ---------------------------------------------------------------- EXPENSES
E_FIRST, E_N = 8, 500
E_LAST = E_FIRST + E_N - 1
EC = dict(date="B", vendor="C", desc="D", amount="E", type="F", cat="G", receipt="H", notes="I",
          goes="J", share="K", ded="L", check="M", inyear="O", colb="P", form="Q")


def ER(k):
    c = EC[k]
    return f"{q(S_EXP)}!${c}${E_FIRST}:${c}${E_LAST}"


# ---------------------------------------------------------------- MEALS
M_FIRST, M_N = 9, 2500
M_LAST = M_FIRST + M_N - 1
KID_FIRST, KID_N = 9, 20
KID_LAST = KID_FIRST + KID_N - 1
MC = dict(date="B", child="C", b="D", l="E", d="F", s="G", notes="H", elig="I", value="J", dup="L", valid="M")


def MR(k):
    c = MC[k]
    return f"{q(S_MEALS)}!${c}${M_FIRST}:${c}${M_LAST}"


# ---------------------------------------------------------------- MILEAGE
MI_FIRST, MI_N = 8, 300
MI_LAST = MI_FIRST + MI_N - 1


def MIR(c):
    return f"{q(S_MILES)}!${c}${MI_FIRST}:${c}${MI_LAST}"


# ---------------------------------------------------------------- SUMMARY anchors (filled in build_summary)
SUMQ = q(S_SUM)
SM = {}


class Builder(Kit):
    product = PRODUCT

    def __init__(self, sample: bool):
        self.sample = sample
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in ORDER}
        if sample:
            import sample_data
            self.data = sample_data

    def dv(self, ws, kind, rng, **kw):
        v = DataValidation(type=kind, showErrorMessage=True, allow_blank=True, **kw)
        ws.add_data_validation(v)
        v.add(rng)
        return v

    def yn(self, ws, rng, opts="Y,N", title="Y or N"):
        self.dv(ws, "list", rng, formula1=f'"{opts}"', errorTitle=title, error=f"Pick {opts.replace(',', ' or ')}.")

    # ============================================================ START HERE
    def build_start(self):
        ws = self.ws[S_START]
        self.page(ws, {"B": 5, "C": 30, "D": 30, "E": 30, "F": 24}, 6, 70, "Start here", "Read this first. Set-up takes about 20 minutes.", landscape=False)
        self.note(ws, "B4:F4", "Your time-space percentage, calculated and documented.", tint=PAPER, height=30, size=15, color=GREEN, bold=True)
        ws["B4"].font = Font(name=TITLE, size=15, bold=True, color=GREEN)
        self.note(ws, "B5:F5", "Family child care providers can deduct part of their home costs and shared household items. The "
                  "deductible share is your time-space percentage. Log your rooms, your hours and your receipts here; the "
                  "workbook works out the percentage step by step and prints a statement for your tax preparer.",
                  tint=PAPER, height=48, size=10, color=INK)
        r = 7
        self.kicker(ws, f"B{r}", "Quick start in 4 steps", rule_to=6)
        steps = [("1", "Settings", "Tax year, business dates, your usual opening hours, and the rates (mileage, meals, simplified "
                  "method). Check each rate and note the date you checked it.", S_SET),
                 ("2", "Rooms", "List every room and area with its square feet and how it is used: exclusive child care, "
                  "regular child care shared with family, or not used.", S_ROOMS),
                 ("3", "Hours log (weekly)", "Each day is prefilled from your usual hours. Once a week, fix any day that "
                  "was different and mark the rest Confirmed. Add time spent preparing, cleaning or doing paperwork.", S_HOURS),
                 ("4", "Expenses", "One row per receipt. Pick the expense type (direct, indirect home, shared household or "
                  "personal) and a category. The deductible share is applied for you.", S_EXP)]
        r = 8
        for num, head, body, sheet in steps:
            c = ws[f"B{r}"]
            c.value = num
            c.font = Font(name=TITLE, size=18, bold=True, color=BRASS)
            c.alignment = Alignment(horizontal="center", vertical="top")
            self.link(ws[f"C{r}"], f"{head}  ›", sheet)
            ws[f"C{r}"].alignment = Alignment(vertical="top")
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"].value = body
            ws[f"D{r}"].font = font(10, color=INK)
            ws[f"D{r}"].alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 48
            r += 1
        self.link(ws[f"C{r}"], "Dashboard  ›", S_DASH)
        ws.merge_cells(f"D{r}:F{r}")
        ws[f"D{r}"].value = "Then see where your year stands: key figures and charts. Use the bar on the left to move between tabs."
        ws[f"D{r}"].font = font(10, color=INK2)
        ws.row_dimensions[r].height = 24
        r += 2
        self.kicker(ws, f"B{r}", "How the hours log counts", rule_to=6)
        r += 1
        self.note(ws, f"B{r}:F{r}", "Every day starts prefilled from your usual hours in grey. A day counts toward your time "
                  "percentage once you mark it Confirmed, change any of its hours, or mark it Closed. Days you haven't checked "
                  "yet are shown as \"Not yet confirmed\" and don't count. The SUMMARY shows both: the percentage from "
                  "checked days, and a projection if the unchecked days match your usual hours.", tint=PAPER, height=62,
                  size=10, color=INK)
        r += 2
        self.kicker(ws, f"B{r}", "Colour key", rule_to=6)
        r += 1
        keys = [("inp", "Type here", "White cell with a border: your information, or pick from the dropdown."),
                ("calc", "Calculated", "Shaded cell: a formula, locked so it can't be overwritten by accident."),
                ("pre", "Prefilled", "Grey text on the hours log: your usual hours, not yet confirmed."),
                ("tile", "Result", "Green block with a brass figure: a key number."),
                ("warn", "Check this", "Red text: something to fix, such as rooms that don't add up.")]
        for kind, head, body in keys:
            c = ws[f"C{r}"]
            c.value = head
            if kind == "inp":
                self.inp(c)
            elif kind == "calc":
                self.calc(c)
            elif kind == "pre":
                self.calc(c)
                c.font = font(10, False, GREY, italic=True)
            elif kind == "tile":
                c.fill, c.font = fill(GREEN), font(10, True, BRASS)
            else:
                c.fill, c.font = fill(NEG_TINT), font(10, True, NEG)
            c.protection = Protection(locked=True)
            c.value = head
            c.alignment = Alignment(indent=1, vertical="center")
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"].value = body
            ws[f"D{r}"].font = font(10, color=INK2)
            ws[f"D{r}"].alignment = Alignment(vertical="center", indent=1)
            ws.row_dimensions[r].height = 22
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "What to give your tax preparer", rule_to=6)
        r += 1
        for text, sheet in [("The SUMMARY tab: the step-by-step percentage and your totals", S_SUM),
                            ("The TIME-SPACE STATEMENT: one printable page", S_STMT),
                            ("FOR YOUR TAX PREPARER: home details, carryovers and a checklist", S_PREP),
                            ("This file itself, so your preparer can see the logs behind the numbers", S_HOURS)]:
            self.link(ws[f"C{r}"], "›", sheet)
            ws[f"C{r}"].alignment = Alignment(horizontal="right")
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"].value = text
            ws[f"D{r}"].font = font(10, color=INK)
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Optional tabs", rule_to=6)
        r += 1
        self.note(ws, f"B{r}:F{r}", "MEALS: a daily food log to use the standard meal and snack rates instead of food receipts. "
                  "MILEAGE: business trips at the standard mileage rate. Skip either if you don't need it; nothing breaks.",
                  tint=PAPER, height=34, size=10, color=INK)
        r += 2
        self.kicker(ws, f"B{r}", "Guide and Google Sheets", rule_to=6)
        r += 1
        self.note(ws, f"B{r}:F{r}", "Quick-start guide: BrassLedger_Home_Daycare_Quick_Start_Guide.pdf (in your download).   "
                  "Google Sheets copy: [GOOGLE SHEETS COPY LINK]", tint=PAPER, height=30, size=10, color=INK)
        r += 2
        self.note(ws, f"B{r}:F{r}", DISCLAIMER, tint=BRASS_TINT, height=48, size=10, color=INK, bold=True)
        if self.sample:
            r += 2
            self.note(ws, f"B{r}:F{r}", "SAMPLE FILE: a fictional provider, Little Acorns Family Child Care, for tax year 2026, "
                      "so you can see every tab working. Use the blank file for your own records.", tint=POS_TINT, height=34,
                      size=10, color=POS, bold=True)
        ws.print_area = f"A1:G{r + 1}"
        self.protect(ws)

    # ============================================================ SETTINGS
    def build_settings(self):
        ws = self.ws[S_SET]
        self.page(ws, {"B": 50, "C": 28, "D": 30, "E": 30, "F": 17, "G": 17, "H": 46}, 8, CAT_LAST + 3, "Settings",
                  "Your business details, the rates the workbook uses, and your usual hours. Check every rate yearly.")
        self.kicker(ws, "B5", "Your business", rule_to=8)
        d = self.data if self.sample else None
        rows = [(6, "Provider or business name", d.BUSINESS if d else None, None, "inp", "Shown on the statement and summary."),
                (7, "Tax year", 2026, "0", "inp", "Change it and the hours log dates and total hours update."),
                (8, "Business start date (optional)", None, DATE, "inp", "Only if you started during the tax year."),
                (9, "Business stop date (optional)", None, DATE, "inp", "Only if you stopped during the tax year."),
                (10, "First business day this year", f'=IF(AND(ISNUMBER({SC["start"]}),{SC["start"]}>DATE({SC["year"]},1,1)),{SC["start"]},DATE({SC["year"]},1,1))', DATE, "calc", ""),
                (11, "Last business day this year", f'=IF(AND(ISNUMBER({SC["stop"]}),{SC["stop"]}<DATE({SC["year"]},12,31)),{SC["stop"]},DATE({SC["year"]},12,31))', DATE, "calc", ""),
                (12, "Days available for daycare", f'=MAX(0,{SC["last"]}-{SC["first"]}+1)', "#,##0", "calc", "From the first to the last business day."),
                (13, "Total hours available (24 × days)", f'=24*{SC["days"]}', "#,##0", "calc", "Form 8829 line 5: 8,760, or 8,784 in a leap year, or 24 × days if you started or stopped."),
                (14, "Leap year?", f'=IF(DAY(DATE({SC["year"]},3,0))=29,"Yes","No")', None, "calc", ""),
                (15, "Days in the tax year", f'=DATE({SC["year"]}+1,1,1)-DATE({SC["year"]},1,1)', "#,##0", "calc", "")]
        for r, label, val, fmt, kind, hint in rows:
            self.label(ws[f"B{r}"], label)
            c = ws[f"C{r}"]
            c.value = val
            (self.inp if kind == "inp" else self.calc)(c, fmt, "center" if r != 6 else None)
            if r == 6:
                ws.merge_cells("C6:E6")
                for col in "DE":
                    self.inp(ws[f"{col}6"])
            ws.merge_cells(f"F{r}:H{r}") if r != 6 else ws.merge_cells("F6:H6")
            self.label(ws[f"F{r}"], hint, bold=False, color=INK2, size=9, indent=1)
        self.dv(ws, "whole", "C7", operator="between", formula1="2000", formula2="2099", errorTitle="Tax year", error="Enter a year, for example 2026.")
        self.dv(ws, "date", "C8:C9", operator="between", formula1="36526", formula2="73051", errorTitle="Date", error="Enter a date, for example 3/15/2026.")
        ws["C9"].number_format = ws["C8"].number_format = DATE
        if d:
            ws["C6"].value = d.BUSINESS
        # rates
        self.kicker(ws, "B18", "Rates  ·  check current rates", rule_to=8)
        for col, t in zip("BCDEF", ["Rate", "Value", "Last checked", "", "Source to check"]):
            pass
        self.header(ws["B19"], "Rate", align="left")
        self.header(ws["C19"], "Value")
        self.header(ws["D19"], "Last checked")
        ws.merge_cells("E19:H19")
        self.header(ws["E19"], "Note", align="left")
        rates = [(20, "Simplified method rate per sq ft", 5.00, MONEY, "Check current rate. Pub. 587 (2025): $5 per square foot."),
                 (21, "Simplified method maximum sq ft", 300, SQFT, "Check current rate. Pub. 587 (2025): 300 square feet."),
                 (22, "Standard mileage rate", 0.725, '"$"0.000', "Check the current IRS rate. 2026: 72.5¢ (Jan 1 to Jun 30)."),
                 (23, "Mileage rate changes on (optional)", None, DATE, "2026: the IRS raised the rate from July 1, 2026. Leave blank if one rate all year."),
                 (24, "Standard mileage rate from that date", 0.76, '"$"0.000', "2026: 76¢ from July 1 (IRS Announcement 2026-11)."),
                 (25, "Standard rate: breakfast", 1.70, MONEY, "Rates change each year. Check the current standard meal and snack rates for your state before using."),
                 (26, "Standard rate: lunch", 3.22, MONEY, "2026 defaults: contiguous states (CACFP Tier I rates in effect Dec 31, 2025)."),
                 (27, "Standard rate: dinner", 3.22, MONEY, "Alaska, Hawaii and US territories have higher rates."),
                 (28, "Standard rate: snack", 0.96, MONEY, "Up to 1 breakfast, 1 lunch, 1 dinner and 3 snacks per eligible child per day."),
                 (29, "Food method this year", FOODS[0], None, "Use one method for the whole year: standard rates OR food receipts, not both."),
                 (30, "Food program (CACFP) reimbursements received", None, MONEY, "Subtracted from your food deduction (Pub. 587).")]
        for r, label, val, fmt, hint in rates:
            self.label(ws[f"B{r}"], label)
            self.inp(ws[f"C{r}"], fmt, "center" if r == 29 else "right", value=val)
            self.inp(ws[f"D{r}"], DATE, "center")
            ws.merge_cells(f"E{r}:H{r}")
            self.label(ws[f"E{r}"], hint, bold=False, color=INK2, size=9, indent=1)
            ws.row_dimensions[r].height = 20
        ws["C23"].value = __import__("datetime").date(2026, 7, 1)
        ws.merge_cells("C29:D29")
        ws["C29"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        self.inp(ws["D29"])
        self.dv(ws, "list", "C29", formula1=f"={F_RNG}", errorTitle="Food method", error="Pick one of the two methods.")
        self.dv(ws, "decimal", "C20:C22", operator="greaterThanOrEqual", formula1="0", errorTitle="Rate", error="Enter 0 or more.")
        self.dv(ws, "decimal", "C24:C28", operator="greaterThanOrEqual", formula1="0", errorTitle="Rate", error="Enter 0 or more.")
        self.dv(ws, "decimal", "C30", operator="greaterThanOrEqual", formula1="0", errorTitle="Amount", error="Enter 0 or more.")
        self.dv(ws, "date", "C23", operator="between", formula1="36526", formula2="73051", errorTitle="Date", error="Enter a date.")
        self.dv(ws, "date", "D20:D30", operator="between", formula1="36526", formula2="73051", errorTitle="Date", error="Enter the date you checked the rate.")
        self.note(ws, "B31:H31", "Rates change; check current rates. Mileage and the simplified method: IRS.gov. Meals: Pub. 587 "
                  "Table 3 for the year, or your food program sponsor. Write the date you checked each rate in Last checked.",
                  height=30)
        if d:
            for r in range(20, 29):
                ws[f"D{r}"].value = d.RATES_CHECKED
            ws["C30"].value = d.CACFP_REIMB
        # usual hours
        self.kicker(ws, "B34", "Usual opening hours  ·  these prefill the hours log", rule_to=8)
        for col, t in zip("BCDEFG", ["Weekday", "Children arrive", "Children leave", "Other business hours", "Children present (hrs)", "Expected total (hrs)"]):
            self.header(ws[f"{col}35"], t, GREEN if col in "BCDE" else GREEN2, align="left" if col == "B" else "center")
        ws.row_dimensions[35].height = 30
        for i, day in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
            r = USUAL_FIRST + i
            self.label(ws[f"B{r}"], day)
            self.inp(ws[f"C{r}"], TIME, "center")
            self.inp(ws[f"D{r}"], TIME, "center")
            self.inp(ws[f"E{r}"], HRS, "center")
            self.calc(ws[f"F{r}"], HRS, align="center", value=f'=IF(OR(C{r}="",D{r}=""),0,MOD(D{r}-C{r},1)*24)')
            self.calc(ws[f"G{r}"], HRS, align="center", value=f"=F{r}+N(E{r})")
            if d:
                a, b_, o = d.USUAL[i]
                ws[f"C{r}"].value, ws[f"D{r}"].value, ws[f"E{r}"].value = a, b_, o
        self.label(ws["H36"], "Other business hours: time you use the home", bold=False, color=INK2, size=9, indent=1)
        self.label(ws["H37"], "for the business when children aren't there:", bold=False, color=INK2, size=9, indent=1)
        self.label(ws["H38"], "preparing, cleaning, meal prep, paperwork.", bold=False, color=INK2, size=9, indent=1)
        last_u = USUAL_FIRST + 6
        self.dv(ws, "time", f"C{USUAL_FIRST}:D{last_u}", operator="between", formula1="0", formula2="0.999988", errorTitle="Time", error="Enter a time, for example 7:00 AM.")
        self.dv(ws, "decimal", f"E{USUAL_FIRST}:E{last_u}", operator="between", formula1="0", formula2="24", errorTitle="Hours", error="Enter hours between 0 and 24.")
        # system lists
        self.kicker(ws, f"B{SYS_FIRST - 2}", "System lists (please don't edit)", color=INK2, rule_to=8)
        for col, t in zip("BCDE", ["Expense types", "Room use types", "Other-hours activities", "Food methods"]):
            self.header(ws[f"{col}{SYS_FIRST + 1}"], t, BRASS_TINT, INK, align="left")
        for col, items in zip("BCDE", [TYPES, USES, ACTIVITIES, FOODS]):
            for i, v in enumerate(items):
                self.sysval(ws[f"{col}{SYS_FIRST + 2 + i}"], v)
        for col, t in zip("BCDE", ["Category", "Goes on", "Line", "Note"]):
            self.header(ws[f"{col}{CAT_FIRST - 1}"], t, BRASS_TINT, INK, align="left")
        ws.merge_cells(f"E{CAT_FIRST - 1}:H{CAT_FIRST - 1}")
        for i, (cat, form, line, note) in enumerate(CATS):
            r = CAT_FIRST + i
            self.sysval(ws[f"B{r}"], cat)
            self.sysval(ws[f"C{r}"], form)
            self.sysval(ws[f"D{r}"], line)
            ws[f"D{r}"].alignment = Alignment(horizontal="center")
            ws.merge_cells(f"E{r}:H{r}")
            self.sysval(ws[f"E{r}"], note)
        self.note(ws, f"B{CAT_LAST + 2}:H{CAT_LAST + 2}", "Line numbers: Schedule C from the 2026 form; Form 8829 from the 2025 form "
                  "(the 2026 draft uses the same lines). Check the form for your tax year.", height=28)
        ws.freeze_panes = "A4"
        ws.print_area = f"A1:I{CAT_LAST + 2}"
        self.protect(ws)

    # ============================================================ ROOMS
    def build_rooms(self):
        ws = self.ws[S_ROOMS]
        self.page(ws, {"B": 40, "C": 15, "D": 32, "E": 44}, 5, R_LAST + 3, "Rooms",
                  "One row per room: square feet and use type set your space %.", landscape=False)
        self.kicker(ws, "B5", "Your home", rule_to=5)
        self.label(ws["B6"], "Total square feet of the home")
        self.inp(ws["C6"], SQFT, "right")
        self.label(ws["D6"], "Measure inside the walls.", bold=False, color=INK2, size=9, indent=1)
        U = f"$D${R_FIRST}:$D${R_LAST}"
        A = f"$C${R_FIRST}:$C${R_LAST}"
        rows = [(7, "Exclusive child care", f'=SUMIFS({A},{U},{SETQ}!$C${SYS_FIRST + 2})', SQFT),
                (8, "Regular child care + family", f'=SUMIFS({A},{U},{SETQ}!$C${SYS_FIRST + 3})', SQFT),
                (9, "Not used for child care", f'=SUMIFS({A},{U},{SETQ}!$C${SYS_FIRST + 4})', SQFT),
                (10, "Rooms listed (total)", f"=SUM({A})", SQFT),
                (11, "Home square feet used", "=IF(N($C$6)>0,$C$6,$C$10)", SQFT),
                (13, "Exclusive-use share", '=IF(N($C$11)=0,0,$C$7/$C$11)', PCT2),
                (14, "Regular-use share", '=IF(N($C$11)=0,0,$C$8/$C$11)', PCT2),
                (15, "Space percentage (exclusive + regular)", '=IF(N($C$11)=0,0,($C$7+$C$8)/$C$11)', PCT2)]
        for r, label, f, fmt in rows:
            self.label(ws[f"B{r}"], label, bold=(r in (11, 15)))
            self.calc(ws[f"C{r}"], fmt, bold=(r in (11, 15)), align="right", value=f)
        ws.merge_cells("D7:E11")
        ws["D7"] = ('=IF(AND(N($C$6)=0,$C$10=0),"Enter the home\'s total square feet and list each room below.",'
                    'IF(N($C$6)=0,"Enter the home\'s total square feet in the white cell above.",'
                    'IF(SUMPRODUCT(($C$' + str(R_FIRST) + ':$C$' + str(R_LAST) + '<>"")*($D$' + str(R_FIRST) + ':$D$' + str(R_LAST) + '=""))>0,'
                    '"Some rooms have no use type. Pick one for every room.",'
                    'IF($C$10<>$C$6,"Check: the rooms add up to "&FIXED($C$10,0)&" sq ft but the home is "&FIXED($C$6,0)&" sq ft. List every area, including hallways, bathrooms and areas not used for child care.",'
                    '"The rooms add up to the home\'s total square feet."))))')
        ws["D7"].alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        ws["D7"].font = font(10, True, POS)
        ws.conditional_formatting.add("D7:E11", FormulaRule(formula=['LEFT($D$7,5)<>"The r"'], font=Font(color=NEG, bold=True),
                                                            fill=fill(NEG_TINT)))
        self.note(ws, "B16:E16", "Exclusive: used only for child care. Regular: available for child care throughout each business "
                  "day and used regularly, also used by the family. A room used only occasionally for the business doesn't count.",
                  height=34)
        for col, t in zip("BCDE", ["Room or area", "Square feet", "Use type", "Notes"]):
            self.header(ws[f"{col}{R_FIRST - 1}"], t, align="left" if col != "C" else "center")
        ws.row_dimensions[R_FIRST - 1].height = 24
        for r in range(R_FIRST, R_LAST + 1):
            self.inp(ws[f"B{r}"])
            self.inp(ws[f"C{r}"], SQFT, "right")
            self.inp(ws[f"D{r}"])
            self.inp(ws[f"E{r}"])
        self.dv(ws, "list", f"D{R_FIRST}:D{R_LAST}", formula1=f"={U_RNG}", errorTitle="Use type", error="Pick a use type from the list.")
        self.dv(ws, "whole", f"C{R_FIRST}:C{R_LAST}", operator="between", formula1="0", formula2="100000", errorTitle="Square feet", error="Enter whole square feet.")
        self.dv(ws, "whole", "C6", operator="between", formula1="0", formula2="100000", errorTitle="Square feet", error="Enter whole square feet.")
        if self.sample:
            for i, (name, sqft, use, note) in enumerate(self.data.ROOMS):
                r = R_FIRST + i
                ws[f"B{r}"].value, ws[f"C{r}"].value, ws[f"D{r}"].value, ws[f"E{r}"].value = name, sqft, use, note
            ws["C6"].value = self.data.HOME_SQFT
        ws.freeze_panes = f"A{R_FIRST}"
        ws.print_area = f"A1:F{R_LAST}"
        self.protect(ws)

    # ============================================================ HOURS LOG
    def build_hours(self):
        ws = self.ws[S_HOURS]
        widths = dict(B=13, C=7, D=11, E=11, F=11, G=11, H=24, I=44, J=9, K=11, L=11, M=11, N=11, O=17, P=3,
                      W=12, X=11, Y=11, Z=13, AA=12, AB=13, AC=12)
        self.page(ws, widths, 29, H_LAST + 2, "Hours log",
                  "One row per day. Prefilled days (grey) count once confirmed or edited. Add prep, cleaning and paperwork time.")
        for k in ("inbiz", "counted", "chours", "proj", "month", "edited"):
            ws.column_dimensions[HC[k]].hidden = True
            ws.column_dimensions[HC[k]].width = 8
        tm = lambda k: f"{SUMQ}!{SM[k]}"
        tiles = [("HOURS COUNTED", f"=SUM({HC['chours']}{H_FIRST}:{HC['chours']}{H_LAST})", HRS),
                 ("DAYS STILL TO CONFIRM", f'=COUNTIF({HC["status"]}{H_FIRST}:{HC["status"]}{H_LAST},"Not yet confirmed")', "#,##0"),
                 ("TIME % (CHECKED DAYS)", "TIME_PCT", PCT2),
                 ("PROJECTED TIME % (FULL YEAR)", "PROJ_PCT", PCT2)]
        self.hours_tiles = tiles
        for i, (lab, f, fmt) in enumerate(tiles):
            c1 = 2 + i * 3 + (1 if i >= 2 else 0)
            self.tile(ws, 4, [2, 5, 9, 12][i], [4, 7, 11, 15][i], lab, f, fmt)
        ws.row_dimensions[6].height = 8
        ws.merge_cells("B7:O7")
        ws["B7"].value = "YOU TYPE: children's times (or hours directly), other business hours, Closed, Confirmed   ·   CALCULATED: the shaded columns"
        ws["B7"].font = font(9, True, BRASS)
        heads = dict(date="Date", day="Day", start="Children arrive", end="Children leave", typed="Or children hours (typed)",
                     other="Other business hours", what="Other hours were for", notes="Notes", closed="Closed? (Y)",
                     conf="Confirmed?", child="Children hours", oth="Other hours", total="Total business hours", status="Status")
        calc_cols = {"date", "day", "child", "oth", "total", "status"}
        for k, t in heads.items():
            self.header(ws[f"{HC[k]}8"], t, GREEN2 if k in calc_cols else GREEN)
        ws[f"{HC['total']}8"].fill = fill(BRASS)
        ws[f"{HC['total']}8"].font = font(9, True, GREEN)
        ws.row_dimensions[8].height = 44
        Y = S("year")
        exp_child = lambda r: f"INDEX({SETQ}!$F${USUAL_FIRST}:$F${USUAL_FIRST + 6},WEEKDAY($B{r},2))"
        exp_other = lambda r: f"INDEX({SETQ}!$E${USUAL_FIRST}:$E${USUAL_FIRST + 6},WEEKDAY($B{r},2))"
        exp_total = lambda r: f"INDEX({SETQ}!$G${USUAL_FIRST}:$G${USUAL_FIRST + 6},WEEKDAY($B{r},2))"
        for i in range(366):
            r = H_FIRST + i
            b = f"$B{r}"
            x = lambda k: f"${HC[k]}{r}"
            f = {
                "date": f'=IF({i + 1}>{S("caldays")},"",DATE({Y},1,1)+{i})',
                "day": f'=IF({b}="","",CHOOSE(WEEKDAY({b},2),"Mon","Tue","Wed","Thu","Fri","Sat","Sun"))',
                "inbiz": f'=IF({b}="",0,IF(AND({b}>={S("first")},{b}<={S("last")}),1,0))',
                "edited": f'=IF(OR({x("start")}<>"",{x("end")}<>"",{x("typed")}<>"",{x("other")}<>""),1,0)',
                "child": (f'=IF({x("inbiz")}=0,"",IF({x("closed")}="Y",0,IF({x("typed")}<>"",N({x("typed")}),'
                          f'IF(AND({x("start")}<>"",{x("end")}<>""),MOD({x("end")}-{x("start")},1)*24,{exp_child(r)}))))'),
                "oth": f'=IF({x("inbiz")}=0,"",IF({x("closed")}="Y",0,IF({x("other")}<>"",N({x("other")}),{exp_other(r)})))',
                "total": f'=IF({x("inbiz")}=0,"",MIN(24,{x("child")}+{x("oth")}))',
                "status": (f'=IF({b}="","",IF({x("inbiz")}=0,"Not in business",IF({x("closed")}="Y","Closed",'
                           f'IF({x("edited")}=1,"Edited",IF({x("conf")}="Yes","Confirmed",IF({exp_total(r)}=0,"Usual day off","Not yet confirmed"))))))'),
                "counted": f'=IF(OR({x("status")}="",{x("status")}="Not in business",{x("status")}="Not yet confirmed"),0,1)',
                "chours": f'=IF({x("counted")}=1,N({x("total")}),0)',
                "proj": f'=IF({x("inbiz")}=1,N({x("total")}),0)',
                "month": f'=IF({b}="","",MONTH({b}))',
            }
            fmts = dict(date=DATE, day=None, child=HRS, oth=HRS, total=HRS, status=None)
            for k, formula in f.items():
                c = ws[f"{HC[k]}{r}"]
                c.value = formula
                if k in fmts:
                    self.calc(c, fmts[k], bold=(k == "total"), align="center" if k in ("day", "status") else None)
                else:
                    c.protection = Protection(locked=True)
            for k in H_INPUTS:
                fm = {"start": TIME, "end": TIME, "typed": HRS, "other": HRS}.get(k)
                self.inp(ws[f"{HC[k]}{r}"], fm, "center" if k in ("closed", "conf") else None)
        rng = lambda k: f"{HC[k]}{H_FIRST}:{HC[k]}{H_LAST}"
        self.dv(ws, "time", f"D{H_FIRST}:E{H_LAST}", operator="between", formula1="0", formula2="0.999988", errorTitle="Time", error="Enter a time, for example 7:00 AM.")
        self.dv(ws, "decimal", f"F{H_FIRST}:G{H_LAST}", operator="between", formula1="0", formula2="24", errorTitle="Hours", error="Enter hours between 0 and 24.")
        self.dv(ws, "list", rng("what"), formula1=f"={A_RNG}", errorTitle="Other hours", error="Pick from the list; add details in Notes.")
        self.yn(ws, rng("closed"), "Y", "Closed")
        self.yn(ws, rng("conf"), "Yes", "Confirmed")
        # prefilled look: grey italic hours until the day counts
        pre = f'AND(${HC["status"]}{H_FIRST}="Not yet confirmed")'
        ws.conditional_formatting.add(f"L{H_FIRST}:O{H_LAST}", FormulaRule(formula=[pre], font=Font(color=GREY, italic=True), fill=fill("F7F4EE")))
        ws.conditional_formatting.add(f"B{H_FIRST}:O{H_LAST}", FormulaRule(formula=[f'${HC["status"]}{H_FIRST}="Not in business"'], font=Font(color="B8B2A6")))
        ws.conditional_formatting.add(f"O{H_FIRST}:O{H_LAST}", FormulaRule(formula=[f'OR(${HC["status"]}{H_FIRST}="Confirmed",${HC["status"]}{H_FIRST}="Edited")'],
                                                                           font=Font(color=POS, bold=True)))
        ws.conditional_formatting.add(f"B{H_FIRST}:C{H_LAST}", FormulaRule(formula=[f'OR($C{H_FIRST}="Sat",$C{H_FIRST}="Sun")'], font=Font(color=INK2, italic=True)))
        # monthly table
        self.kicker(ws, "W7", "Month by month", rule_to=29)
        for col, t in zip(["W", "X", "Y", "Z", "AA", "AB", "AC"], ["Month", "Days in business", "Days counted", "Hours counted",
                                                                  "Days to confirm", "Projected hours", "Time % so far"]):
            self.header(ws[f"{col}8"], t, align="left" if col == "W" else "center")
        IB, CT, CH, PR, MO = (f"${HC[k]}${H_FIRST}:${HC[k]}${H_LAST}" for k in ("inbiz", "counted", "chours", "proj", "month"))
        for m in range(1, 13):
            r = 8 + m
            ws[f"W{r}"] = f"={SETQ}!$C${CAT_LAST + 5 + m}" if False else MONTHS[m - 1]
            ws[f"W{r}"].font = font(10, True, INK)
            self.calc(ws[f"X{r}"], "#,##0", align="center", value=f"=SUMIFS({IB},{MO},{m})")
            self.calc(ws[f"Y{r}"], "#,##0", align="center", value=f"=SUMIFS({CT},{MO},{m})")
            self.calc(ws[f"Z{r}"], HRS, bold=True, value=f"=SUMIFS({CH},{MO},{m})")
            self.calc(ws[f"AA{r}"], "#,##0", align="center", value=f'=COUNTIFS({MO},{m},${HC["status"]}${H_FIRST}:${HC["status"]}${H_LAST},"Not yet confirmed")')
            self.calc(ws[f"AB{r}"], HRS, value=f"=SUMIFS({PR},{MO},{m})")
            self.calc(ws[f"AC{r}"], PCT2, align="center", value=f'=IF(SUM($Y$9:$Y{r})=0,"",SUM($Z$9:$Z{r})/(24*SUM($Y$9:$Y{r})))')
        r = 21
        ws[f"W{r}"] = "Year"
        for col in ["X", "Y", "Z", "AA", "AB"]:
            ws[f"{col}{r}"] = f"=SUM({col}9:{col}20)"
        ws[f"AC{r}"] = f'=IF($Y$21=0,"",$Z$21/(24*$Y$21))'
        for col in ["W", "X", "Y", "Z", "AA", "AB", "AC"]:
            x = ws[f"{col}{r}"]
            x.fill, x.font = fill(GREEN), font(10, True, BRASS if col != "W" else PAPER)
            x.number_format = {"Z": HRS, "AB": HRS, "AC": PCT2}.get(col, "#,##0")
            x.alignment = Alignment(horizontal="center" if col not in ("W", "Z", "AB") else None, indent=1 if col == "W" else 0)
        self.note(ws, "W23:AC25", "Time % so far = hours counted ÷ (24 × days counted). Your final time % is on SUMMARY: hours "
                  "counted ÷ total hours available for the year.")
        self.note(ws, "W27:AC31", "What counts: hours children are in your care, plus time you use the home for the business "
                  "when they aren't there (preparing, cleaning, meal prep, paperwork, parent meetings). Time away from home, "
                  "such as shopping, doesn't count. Keep notes of what you did.")
        ws.freeze_panes = f"D{H_FIRST}"
        ws.auto_filter.ref = f"B8:O{H_LAST}"
        ws.print_area = f"A1:O{H_LAST}"
        ws.print_title_rows = "8:8"
        if self.sample:
            for i, row in enumerate(self.data.hours_rows()):
                r = H_FIRST + i
                for k, v in row.items():
                    ws[f"{HC[k]}{r}"].value = v
        self.protect(ws)

    # ============================================================ EXPENSES
    def build_expenses(self):
        ws = self.ws[S_EXP]
        widths = dict(B=13, C=22, D=36, E=12, F=26, G=30, H=10, I=40, J=22, K=11, L=13, M=50, O=6, P=6, Q=6)
        self.page(ws, widths, 13, E_LAST + 2, "Expenses",
                  "One row per receipt. The expense type decides the deductible share; the category decides where it goes.")
        for k in ("inyear", "colb", "form"):
            ws.column_dimensions[EC[k]].hidden = True
        ws.merge_cells("B5:I5")
        ws["B5"].value = ("Types: Direct (business only) 100%  ·  Direct home: exclusive area 100%  ·  Direct home: shared area × time %  "
                          "·  Indirect home × time-space %  ·  Shared household × time-space %  ·  Personal 0%")
        ws["B5"].font = font(9, True, GREEN)
        ws["B5"].alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        ws.row_dimensions[5].height = 30
        self.calc(ws["L5"], MONEY, bold=True, value=f"=SUM(L{E_FIRST}:L{E_LAST})")
        self.label(ws["J5"], "Total deductible", color=GREEN)
        ws["J5"].alignment = Alignment(horizontal="right", vertical="center")
        ws.merge_cells("J5:K5")
        heads = dict(date="Date", vendor="Vendor", desc="Description", amount="Amount", type="Expense type", cat="Category",
                     receipt="Receipt saved?", notes="Notes", goes="Goes on", share="Deductible share", ded="Deductible amount",
                     check="Check")
        for k, t in heads.items():
            self.header(ws[f"{EC[k]}7"], t, GREEN2 if k in ("goes", "share", "ded", "check") else GREEN)
        ws[f"{EC['ded']}7"].fill = fill(BRASS)
        ws[f"{EC['ded']}7"].font = font(9, True, GREEN)
        ws.row_dimensions[7].height = 32
        time_, ts = f"{SUMQ}!{SM['time']}", f"{SUMQ}!{SM['ts']}"
        for r in range(E_FIRST, E_LAST + 1):
            for k, fm in (("date", DATE), ("vendor", None), ("desc", None), ("amount", MONEY), ("type", None), ("cat", None),
                          ("receipt", None), ("notes", None)):
                self.inp(ws[f"{EC[k]}{r}"], fm, "center" if k == "receipt" else None)
            x = lambda k: f"${EC[k]}{r}"
            blank = f'AND({x("date")}="",{x("amount")}="",{x("cat")}="")'
            home_type = f'OR({x("type")}={TYPE(1)},{x("type")}={TYPE(2)},{x("type")}={TYPE(3)})'
            in_biz = f'AND({x("date")}>={S("first")},{x("date")}<={S("last")})'
            base = (f'IF({x("type")}={TYPE(0)},1,IF({x("type")}={TYPE(1)},1,IF({x("type")}={TYPE(2)},{time_},'
                    f'IF(OR({x("type")}={TYPE(3)},{x("type")}={TYPE(4)}),{ts},0))))')
            f = {
                "form": f'=IFERROR(INDEX({CAT_FORM},MATCH({x("cat")},{CAT_NAMES},0)),"")',
                "inyear": f'=IF(ISNUMBER({x("date")}),IF(YEAR({x("date")})={S("year")},1,0),0)',
                "goes": (f'=IF({blank},"",IF({x("form")}="","",IF({x("form")}="Personal","Not deductible",IF({x("form")}="Food",'
                         f'"Food: see SUMMARY",{x("form")}&" line "&INDEX({CAT_LINE},MATCH({x("cat")},{CAT_NAMES},0))))))'),
                "share": (f'=IF({blank},"",IF(OR({x("inyear")}=0,{x("type")}="",{x("form")}="",{x("form")}="Personal"),0,'
                          f'IF({x("form")}="Food",IF(AND({S("food")}={F_RNG.split(":")[0]},TRUE),0,IF({x("type")}={TYPE(0)},1,0)),'
                          f'IF(AND({home_type},NOT({in_biz})),0,{base}))))'),
                "ded": f'=IF({blank},"",N({x("amount")})*{x("share")})',
                "colb": f'=IF(AND({x("inyear")}=1,{x("type")}={TYPE(3)},{in_biz}),N({x("amount")}),0)',
                "check": (f'=IF({blank},"",IF(OR({x("date")}="",{x("amount")}="",{x("type")}="",{x("cat")}=""),"Add the date, amount, type and category",'
                          f'IF({x("inyear")}=0,"Not in this tax year",'
                          f'IF(AND({home_type},NOT({in_biz})),"Outside your business dates",'
                          f'IF(AND({x("form")}="Food",{S("food")}={F_RNG.split(":")[0]}),"Standard meal rates in use: not counted",'
                          f'IF(AND({x("form")}="Food",{x("type")}<>{TYPE(0)}),"Food: enter only the child care part, as Direct (business only)",'
                          f'IF(AND({x("form")}="Form 8829",OR({x("type")}={TYPE(0)},{x("type")}={TYPE(4)})),"Home cost: pick a home type",'
                          f'IF(AND({x("form")}="Schedule C",{home_type}),"Not a home cost: pick Direct or Shared household",'
                          f'IF(AND({x("type")}="Personal",{x("form")}<>"Personal"),"Personal: not counted","OK")))))))))'),
            }
            fmts = dict(goes=None, share=PCT2, ded=MONEY, check=None)
            for k, formula in f.items():
                c = ws[f"{EC[k]}{r}"]
                c.value = formula
                if k in fmts:
                    self.calc(c, fmts[k], bold=(k == "ded"), align="center" if k == "share" else None)
                else:
                    c.protection = Protection(locked=True)
        rng = lambda k: f"{EC[k]}{E_FIRST}:{EC[k]}{E_LAST}"
        self.dv(ws, "date", rng("date"), operator="between", formula1="36526", formula2="73051", errorTitle="Date", error="Enter the receipt date.")
        self.dv(ws, "decimal", rng("amount"), operator="greaterThanOrEqual", formula1="0", errorTitle="Amount", error="Enter an amount of 0 or more.")
        self.dv(ws, "list", rng("type"), formula1=f"={T_RNG}", errorTitle="Expense type", error="Pick an expense type from the list.")
        self.dv(ws, "list", rng("cat"), formula1=f"={CAT_NAMES}", errorTitle="Category", error="Pick a category from the list.")
        self.yn(ws, rng("receipt"))
        ws.conditional_formatting.add(rng("check"), FormulaRule(formula=[f'AND(${EC["check"]}{E_FIRST}<>"",${EC["check"]}{E_FIRST}<>"OK")'],
                                                                font=Font(color=NEG, bold=True)))
        ws.conditional_formatting.add(rng("check"), FormulaRule(formula=[f'${EC["check"]}{E_FIRST}="OK"'], font=Font(color=POS)))
        ws.freeze_panes = f"C{E_FIRST}"
        ws.auto_filter.ref = f"B7:M{E_LAST}"
        ws.print_area = f"A1:M{E_LAST}"
        ws.print_title_rows = "7:7"
        if self.sample:
            for i, e in enumerate(self.data.EXPENSES):
                r = E_FIRST + i
                for k, v in zip(("date", "vendor", "desc", "amount", "type", "cat", "receipt", "notes"), e):
                    if v not in (None, ""):
                        ws[f"{EC[k]}{r}"].value = v
        self.protect(ws)

    # ============================================================ MEALS
    def build_meals(self):
        ws = self.ws[S_MEALS]
        widths = dict(B=13, C=20, D=10, E=10, F=10, G=10, H=22, I=11, J=13, K=3, L=6, M=6, N=3,
                      O=20, P=13, Q=13, R=11, S=24)
        self.page(ws, widths, 19, M_LAST + 2, "Meals (optional)",
                  "Daily food log for the standard meal and snack rates. One row per child per day. List each child once on the right.")
        for c in ("L", "M"):
            ws.column_dimensions[c].hidden = True
        ws.merge_cells("B5:J5")
        ws["B5"].value = ("Up to 1 breakfast, 1 lunch, 1 dinner and 3 snacks per eligible child per day. Rates are on SETTINGS. "
                          "Only counted when SETTINGS › Food method is standard rates.")
        ws["B5"].font = font(9, True, GREEN)
        ws["B5"].alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        ws.row_dimensions[5].height = 30
        self.label(ws["H6"], "Total at standard rates", color=GREEN)
        ws["H6"].alignment = Alignment(horizontal="right", vertical="center")
        self.calc(ws["J6"], MONEY, bold=True, value=f"=SUM(J{M_FIRST}:J{M_LAST})")
        for k, t in dict(date="Date", child="Child", b="Breakfast", l="Lunch", d="Dinner", s="Snacks (0–3)", notes="Notes",
                         elig="Eligible child?", value="Value at standard rates").items():
            self.header(ws[f"{MC[k]}8"], t, GREEN2 if k in ("elig", "value") else GREEN)
        ws.row_dimensions[8].height = 32
        KN = f"$O${KID_FIRST}:$O${KID_LAST}"
        KE = f"$R${KID_FIRST}:$R${KID_LAST}"
        for r in range(M_FIRST, M_LAST + 1):
            for k, fm in (("date", DATE), ("child", None), ("b", "0"), ("l", "0"), ("d", "0"), ("s", "0"), ("notes", None)):
                self.inp(ws[f"{MC[k]}{r}"], fm, "center" if k in "blds" else None)
            blank = f'AND($B{r}="",$C{r}="")'
            ws[f"I{r}"] = f'=IF({blank},"",IFERROR(INDEX({KE},MATCH($C{r},{KN},0)),"Add to list"))'
            ws[f"L{r}"] = f'=IF({blank},0,COUNTIFS($B${M_FIRST}:$B{r},$B{r},$C${M_FIRST}:$C{r},$C{r}))'
            ws[f"M{r}"] = (f'=IF(OR({blank},$I{r}<>"Yes",$L{r}>1,NOT(ISNUMBER($B{r}))),0,'
                           f'IF(AND(YEAR($B{r})={S("year")},$B{r}>={S("first")},$B{r}<={S("last")}),1,0))')
            ws[f"J{r}"] = (f'=IF({blank},"",$M{r}*(MIN(1,N($D{r}))*{S("bfast")}+MIN(1,N($E{r}))*{S("lunch")}'
                           f'+MIN(1,N($F{r}))*{S("dinner")}+MIN(3,N($G{r}))*{S("snack")}))')
            self.calc(ws[f"I{r}"], None, align="center")
            self.calc(ws[f"J{r}"], MONEY)
            ws[f"L{r}"].protection = ws[f"M{r}"].protection = Protection(locked=True)
        self.dv(ws, "date", f"B{M_FIRST}:B{M_LAST}", operator="between", formula1="36526", formula2="73051", errorTitle="Date", error="Enter the date.")
        self.dv(ws, "list", f"C{M_FIRST}:C{M_LAST}", formula1=f"={KN}", errorTitle="Child", error="Pick a child from the list on the right (add them there first).")
        self.dv(ws, "whole", f"D{M_FIRST}:F{M_LAST}", operator="between", formula1="0", formula2="1", errorTitle="Meals", error="Enter 1 if served, otherwise leave blank or 0.")
        self.dv(ws, "whole", f"G{M_FIRST}:G{M_LAST}", operator="between", formula1="0", formula2="3", errorTitle="Snacks", error="Enter 0 to 3 snacks.")
        ws.conditional_formatting.add(f"I{M_FIRST}:I{M_LAST}", FormulaRule(formula=[f'AND($I{M_FIRST}<>"",$I{M_FIRST}<>"Yes")'], font=Font(color=NEG, bold=True)))
        ws.conditional_formatting.add(f"B{M_FIRST}:C{M_LAST}", FormulaRule(formula=[f'$L{M_FIRST}>1'], font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        # children list
        self.kicker(ws, "O7", "Children (list each once)", rule_to=19)
        for col, t in zip("OPQRS", ["Child", "Lives in your home?", "Care is a personal favour?", "Eligible?", "Notes"]):
            self.header(ws[f"{col}8"], t, GREEN2 if col == "R" else GREEN, align="left" if col in "OS" else "center")
        for r in range(KID_FIRST, KID_LAST + 1):
            self.inp(ws[f"O{r}"])
            self.inp(ws[f"P{r}"], align="center")
            self.inp(ws[f"Q{r}"], align="center")
            self.calc(ws[f"R{r}"], align="center", value=f'=IF($O{r}="","",IF(OR($P{r}="Y",$Q{r}="Y"),"No","Yes"))')
            self.inp(ws[f"S{r}"])
        self.yn(ws, f"P{KID_FIRST}:Q{KID_LAST}")
        ws.conditional_formatting.add(f"R{KID_FIRST}:R{KID_LAST}", FormulaRule(formula=[f'$R{KID_FIRST}="No"'], font=Font(color=NEG, bold=True)))
        self.note(ws, f"O{KID_LAST + 2}:S{KID_LAST + 4}", "Not eligible (Pub. 587): children who live in your home, including your "
                  "own, and children you care for as a personal favour, for example a relative's child as a favour.")
        self.note(ws, f"O{KID_LAST + 6}:S{KID_LAST + 7}", "A child listed twice for the same date is highlighted red and only the "
                  "first row counts.")
        ws.freeze_panes = f"C{M_FIRST}"
        ws.print_area = f"A1:S{M_LAST}"
        ws.print_title_rows = "8:8"
        if self.sample:
            for i, (name, lives, favour, note) in enumerate(self.data.CHILDREN):
                r = KID_FIRST + i
                ws[f"O{r}"].value, ws[f"P{r}"].value, ws[f"Q{r}"].value, ws[f"S{r}"].value = name, lives, favour, note
            for i, row in enumerate(self.data.meal_rows()):
                r = M_FIRST + i
                for k, v in zip(("date", "child", "b", "l", "d", "s", "notes"), row):
                    if v not in (None, "", 0):
                        ws[f"{MC[k]}{r}"].value = v
        self.protect(ws)

    # ============================================================ MILEAGE
    def build_mileage(self):
        ws = self.ws[S_MILES]
        widths = dict(B=13, C=34, D=20, E=20, F=10, G=11, H=13, I=6)
        self.page(ws, widths, 8, MI_LAST + 2, "Mileage (optional)",
                  "Business trips only. With the mileage rate, don't also enter car costs.",
                  landscape=False)
        ws.column_dimensions["I"].hidden = True
        self.label(ws["F5"], "Total", color=GREEN)
        self.calc(ws["G5"], "#,##0.0", bold=True, value=f"=SUM(I{MI_FIRST}:I{MI_LAST})")
        self.calc(ws["H5"], MONEY, bold=True, value=f"=SUM(H{MI_FIRST}:H{MI_LAST})")
        for col, t in zip("BCDEFGH", ["Date", "Purpose", "From", "To", "Miles", "Rate", "Deduction"]):
            self.header(ws[f"{col}7"], t, GREEN2 if col in "GH" else GREEN)
        ws.row_dimensions[7].height = 24
        for r in range(MI_FIRST, MI_LAST + 1):
            for col, fm in zip("BCDEF", [DATE, None, None, None, "#,##0.0"]):
                self.inp(ws[f"{col}{r}"], fm)
            blank = f'AND($B{r}="",$F{r}="")'
            inyear = f'AND(ISNUMBER($B{r}),YEAR($B{r})={S("year")})'
            ws[f"G{r}"] = f'=IF({blank},"",IF(AND(ISNUMBER({S("mchange")}),ISNUMBER($B{r}),$B{r}>={S("mchange")}),{S("mile2")},{S("mile1")}))'
            ws[f"H{r}"] = f'=IF({blank},"",IF({inyear},N($F{r})*$G{r},0))'
            ws[f"I{r}"] = f'=IF({inyear},N($F{r}),0)'
            self.calc(ws[f"G{r}"], '"$"0.000', align="center")
            self.calc(ws[f"H{r}"], MONEY, bold=True)
            ws[f"I{r}"].protection = Protection(locked=True)
        self.dv(ws, "date", f"B{MI_FIRST}:B{MI_LAST}", operator="between", formula1="36526", formula2="73051", errorTitle="Date", error="Enter the trip date.")
        self.dv(ws, "decimal", f"F{MI_FIRST}:F{MI_LAST}", operator="between", formula1="0", formula2="5000", errorTitle="Miles", error="Enter the miles driven.")
        ws.freeze_panes = f"A{MI_FIRST}"
        ws.print_area = f"A1:H{MI_LAST}"
        ws.print_title_rows = "7:7"
        if self.sample:
            for i, t in enumerate(self.data.TRIPS):
                r = MI_FIRST + i
                for col, v in zip("BCDEF", t):
                    ws[f"{col}{r}"].value = v
        self.protect(ws)

    # ============================================================ SUMMARY
    def build_summary(self):
        ws = self.ws[S_SUM]
        widths = dict(B=6, C=46, D=16, E=16, F=16, G=16)
        self.page(ws, widths, 7, 120, "Summary", "Step-by-step time-space percentage and totals. Print it for your tax preparer.", landscape=False)
        self.label(ws["C4"], "=" + S("name") + '&IF(' + S("name") + '="","","  ·  ")&"Tax year "&' + S("year"), color=GREEN, size=11)
        ws.merge_cells("C4:G4")
        r = 6
        self.kicker(ws, f"B{r}", "A  ·  Time percentage (Form 8829 lines 4 to 6)", rule_to=7)
        CH = f"SUM({HR('chours')})"
        steps = [
            ("1", "Hours children were in your care (checked days)", f"=SUMIFS({HR('child')},{HR('counted')},1)", HRS, "child"),
            ("2", "Other business hours in the home (checked days)", f"=SUMIFS({HR('oth')},{HR('counted')},1)", HRS, "other"),
            ("3", "Total business hours  (line 4)", f"={CH}", HRS, "bizhours"),
            ("4", "Days available for daycare", f"={S('days')}", "#,##0", "days"),
            ("5", "Total hours available: 24 × days  (line 5)", f"={S('hours')}", "#,##0", "avail"),
            ("6", "Time percentage: step 3 ÷ step 5  (line 6)", None, PCT2, "time"),
        ]
        r += 1
        for num, lab, f, fmt, key in steps:
            self.summary_row(ws, r, num, lab, f, fmt, key, bold=(key in ("bizhours", "time")))
            r += 1
        SM["_r_time"] = SM["time"]
        ws[SM["time"].replace("$", "")] = f'=IF(N({SM["avail"]})=0,0,{SM["bizhours"]}/{SM["avail"]})'
        ws.merge_cells(f"C{r}:F{r}")
        ws[f"C{r}"] = (f'=IF(COUNTIF({HR("status")},"Not yet confirmed")=0,"All days in the hours log are checked.",'
                       f'COUNTIF({HR("status")},"Not yet confirmed")&" days are not confirmed yet. If they match your usual hours, '
                       f'the full-year time percentage would be "&FIXED(100*IF(N({SM["avail"]})=0,0,SUM({HR("proj")})/{SM["avail"]}),2)&"%.")')
        ws[f"C{r}"].font = font(9, True, INK2)
        ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[r].height = 28
        SM["proj"] = f"$G${r}"
        ws[f"G{r}"] = f'=IF(N({SM["avail"]})=0,0,SUM({HR("proj")})/{SM["avail"]})'
        ws[f"G{r}"].number_format = PCT2
        ws[f"G{r}"].font = font(9, True, INK2)

        r += 2
        self.kicker(ws, f"B{r}", "B  ·  Space and the time-space percentage", rule_to=7)
        r += 1
        steps = [("7", "Total area of the home (sq ft)", f"={RMQ('home')}", SQFT, "home"),
                 ("8", "Area used exclusively for child care", f"={RMQ('excl')}", SQFT, "excl"),
                 ("9", "Area used regularly for child care (shared with family)", f"={RMQ('reg')}", SQFT, "reg"),
                 ("10", "Exclusive share: step 8 ÷ step 7", None, PCT2, "excl_pct"),
                 ("11", "Regular share: step 9 ÷ step 7", None, PCT2, "reg_pct"),
                 ("12", "Regular share adjusted for time: step 11 × step 6", None, PCT2, "reg_time"),
                 ("13", "TIME-SPACE PERCENTAGE: step 10 + step 12  (line 7)", None, PCT2, "ts")]
        for num, lab, f, fmt, key in steps:
            self.summary_row(ws, r, num, lab, f, fmt, key, bold=(key == "ts"))
            r += 1
        cell = lambda k: SM[k].replace("$", "")
        ws[cell("excl_pct")] = f'=IF(N({SM["home"]})=0,0,{SM["excl"]}/{SM["home"]})'
        ws[cell("reg_pct")] = f'=IF(N({SM["home"]})=0,0,{SM["reg"]}/{SM["home"]})'
        ws[cell("reg_time")] = f'={SM["reg_pct"]}*{SM["time"]}'
        ws[cell("ts")] = f'={SM["excl_pct"]}+{SM["reg_time"]}'
        tsr = int(SM["ts"].split("$")[-1])
        for col in "BCDEFG":
            ws[f"{col}{tsr}"].fill = fill(GREEN)
        ws[f"C{tsr}"].font = font(10, True, PAPER)
        ws[f"B{tsr}"].font = font(10, True, BRASS)
        ws[cell("ts")].font = font(13, True, BRASS)
        ws[cell("ts")].fill = fill(GREEN)
        ws.row_dimensions[tsr].height = 26
        ws.merge_cells(f"C{r}:G{r}")
        ws[f"C{r}"] = (f'=IF({SM["excl"]}>0,"You have exclusive-use space, so the IRS asks for this calculation as a statement: '
                       f'print the TIME-SPACE STATEMENT, attach it, and write \'See attached computation\' above Form 8829 line 7.",'
                       f'"No exclusive-use space: the time-space percentage is simply the space share (step 11) × the time percentage (step 6).")')
        ws[f"C{r}"].font = font(9, True, GREEN)
        ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="center")
        ws.row_dimensions[r].height = 30
        r += 2
        # ---- C. Schedule C
        self.kicker(ws, f"B{r}", "C  ·  Schedule C business expenses", rule_to=7)
        r += 1
        for col, t in zip("CDEF", ["Category", "Line (2026)", "Amount entered", "Deductible"]):
            self.header(ws[f"{col}{r}"], t, align="left" if col == "C" else "center")
        r += 1
        sc_first = r
        IY = ER("inyear")
        for cat, form, line, _n in CATS:
            if form != "Schedule C":
                continue
            ws[f"C{r}"] = cat
            ws[f"C{r}"].font = font(10, False, INK)
            ws[f"D{r}"] = line
            ws[f"D{r}"].alignment = Alignment(horizontal="center")
            ws[f"D{r}"].font = font(10, False, INK2)
            self.calc(ws[f"E{r}"], MONEY, value=f'=SUMIFS({ER("amount")},{ER("cat")},$C{r},{IY},1)')
            self.calc(ws[f"F{r}"], MONEY, bold=True, value=f'=SUMIFS({ER("ded")},{ER("cat")},$C{r})')
            SM.setdefault("cat_cells", []).append((cat, f"$F${r}"))
            r += 1
        SM["mile_row"] = r
        ws[f"C{r}"] = "Car: standard mileage (MILEAGE tab)"
        ws[f"D{r}"] = "9"
        r += 1
        SM["food_row"] = r
        ws[f"C{r}"] = "Food for children (section E)"
        ws[f"D{r}"] = "27b"
        for rr in (SM["mile_row"], SM["food_row"]):
            ws[f"C{rr}"].font = font(10, False, INK)
            ws[f"D{rr}"].alignment = Alignment(horizontal="center")
            ws[f"D{rr}"].font = font(10, False, INK2)
        sc_last = r
        r += 1
        ws[f"C{r}"] = "Total Schedule C expenses"
        ws[f"F{r}"] = f"=SUM(F{sc_first}:F{sc_last})"
        ws[f"E{r}"] = f"=SUM(E{sc_first}:E{sc_last})"
        for col in "CDEF":
            x = ws[f"{col}{r}"]
            x.fill, x.font = fill(GREEN), font(10, True, BRASS if col != "C" else PAPER)
            x.number_format = MONEY
        SM["sc_total"] = f"$F${r}"
        r += 2
        # ---- D. Form 8829
        self.kicker(ws, f"B{r}", "D  ·  Home expenses for Form 8829 (before limits)", rule_to=7)
        r += 1
        for col, t in zip("CDEFG", ["Category", "Line (2025)", "Direct (a), deductible part", "Indirect (b), total", "Deductible"]):
            self.header(ws[f"{col}{r}"], t, align="left" if col == "C" else "center")
        ws.row_dimensions[r].height = 30
        r += 1
        h_first = r
        TY = ER("type")
        for cat, form, line, _n in CATS:
            if form != "Form 8829":
                continue
            ws[f"C{r}"] = cat
            ws[f"C{r}"].font = font(10, False, INK)
            ws[f"D{r}"] = line
            ws[f"D{r}"].alignment = Alignment(horizontal="center")
            ws[f"D{r}"].font = font(10, False, INK2)
            self.calc(ws[f"E{r}"], MONEY, value=(f'=SUMIFS({ER("ded")},{ER("cat")},$C{r},{TY},{TYPE(1)})'
                                                 f'+SUMIFS({ER("ded")},{ER("cat")},$C{r},{TY},{TYPE(2)})'))
            self.calc(ws[f"F{r}"], MONEY, value=f'=SUMIFS({ER("colb")},{ER("cat")},$C{r})')
            self.calc(ws[f"G{r}"], MONEY, bold=True, value=f"=E{r}+F{r}*{SM['ts']}")
            SM.setdefault("cat_cells", []).append((cat, f"$G${r}"))
            r += 1
        h_last = r - 1
        ws[f"C{r}"] = "Total home expenses (before limits)"
        for col in "EFG":
            ws[f"{col}{r}"] = f"=SUM({col}{h_first}:{col}{h_last})"
        for col in "CDEFG":
            x = ws[f"{col}{r}"]
            x.fill, x.font = fill(GREEN), font(10, True, BRASS if col != "C" else PAPER)
            x.number_format = MONEY
        SM["home_total"] = f"$G${r}"
        r += 1
        self.note(ws, f"C{r}:G{r}", "Indirect home costs × time-space %; direct costs already include their share. Not included: "
                  "depreciation of your home (your preparer figures it from the FOR YOUR TAX PREPARER tab), carryovers, and the "
                  "limit based on your business income (Form 8829 Part II).", height=46)
        r += 2
        # ---- E. Food
        self.kicker(ws, f"B{r}", "E  ·  Food: standard meal rates vs actual receipts", rule_to=7)
        r += 1
        MV, MD = MR("valid"), MR("dup")
        food = [("Breakfasts counted (eligible children)", f"=SUMPRODUCT({MV}*MIN1({MR('b')}))", "#,##0", "n_b"),
                ("Lunches counted", f"=SUMPRODUCT({MV}*MIN1({MR('l')}))", "#,##0", "n_l"),
                ("Dinners counted", f"=SUMPRODUCT({MV}*MIN1({MR('d')}))", "#,##0", "n_d"),
                ("Snacks counted", f"=SUMPRODUCT({MV}*MIN3({MR('s')}))", "#,##0", "n_s"),
                ("Value at standard meal and snack rates (MEALS tab)", f"=SUM({MR('value')})", MONEY, "std"),
                ("Actual food receipts (EXPENSES, Food, Direct, this year)",
                 f'=SUMIFS({ER("amount")},{ER("cat")},"Food (actual receipts)",{ER("type")},{TYPE(0)},{IY},1)', MONEY, "actual"),
                ("Food method chosen (SETTINGS)", f'=IF({S("food")}={F_RNG.split(":")[0]},"Standard rates","Actual receipts")', None, "method"),
                ("Food cost under the chosen method", None, MONEY, "chosen"),
                ("Less: food program (CACFP) reimbursements", f"={S('reimb')}", MONEY, "reimb"),
                ("Food deduction (Schedule C Part V, line 27b)", None, MONEY, "food_net"),
                ("Reimbursements above food cost (report as income)", None, MONEY, "food_inc")]
        for lab, f, fmt, key in food:
            self.summary_row(ws, r, "", lab, f, fmt, key, bold=(key in ("food_net", "std", "actual")))
            r += 1
        for k in ("n_b", "n_l", "n_d"):
            col = {"n_b": "b", "n_l": "l", "n_d": "d"}[k]
            ws[cell(k)] = f"=SUMPRODUCT({MV}*(N(+{MR(col)})>0))" if False else f'=SUMPRODUCT(({MV}=1)*({MR(col)}>=1))'
        ws[cell("n_s")] = f"=SUMPRODUCT(({MV}=1)*({MR('s')}>=3)*3+({MV}=1)*({MR('s')}<3)*({MR('s')}>0)*{MR('s')})" if False else \
            f'=SUMPRODUCT(({MV}=1)*({MR("s")}>=1))+SUMPRODUCT(({MV}=1)*({MR("s")}>=2))+SUMPRODUCT(({MV}=1)*({MR("s")}>=3))'
        ws[cell("chosen")] = f'=IF({SM["method"]}="Standard rates",{SM["std"]},{SM["actual"]})'
        ws[cell("food_net")] = f'=MAX(0,{SM["chosen"]}-N({SM["reimb"]}))'
        ws[cell("food_inc")] = f'=MAX(0,N({SM["reimb"]})-{SM["chosen"]})'
        ws[cell("method")].alignment = Alignment(horizontal="right", shrink_to_fit=True)
        self.note(ws, f"C{r}:G{r}", "Use one method for the whole year. Only the chosen method is counted, never both. Pub. 587: CACFP "
                  "reimbursements are taxable only to the extent they exceed your food costs for eligible children.", height=34)
        r += 2
        # ---- F. Mileage
        self.kicker(ws, f"B{r}", "F  ·  Mileage", rule_to=7)
        r += 1
        self.summary_row(ws, r, "", "Business miles this tax year", f"=SUM({MIR('I')})", "#,##0.0", "miles")
        r += 1
        self.summary_row(ws, r, "", "Deduction at the standard mileage rate (Schedule C line 9)", f"=SUM({MIR('H')})", MONEY, "mile_ded", bold=True)
        r += 2
        # fill SC mileage and food rows now that anchors exist
        self.calc(ws[f"E{SM['mile_row']}"], MONEY, value=f"={SM['mile_ded']}")
        self.calc(ws[f"F{SM['mile_row']}"], MONEY, bold=True, value=f"={SM['mile_ded']}")
        self.calc(ws[f"E{SM['food_row']}"], MONEY, value=f"={SM['chosen']}")
        self.calc(ws[f"F{SM['food_row']}"], MONEY, bold=True, value=f"={SM['food_net']}")
        # ---- G. Simplified method
        self.kicker(ws, f"B{r}", "G  ·  Simplified method estimate (check current rate)", rule_to=7)
        r += 1
        simp = [("Area used for daycare (exclusive + regular)", lambda: f"={SM['excl']}+{SM['reg']}", SQFT, "s_area"),
                ("Allowed area (up to the maximum on SETTINGS)", lambda: f"=MIN({SM['s_area']},{S('smax')})", SQFT, "s_allowed"),
                ("  of which exclusive area at the full rate", lambda: f"=MIN({SM['excl']},{SM['s_allowed']})", SQFT, "s_excl"),
                ("  of which regular area at the time-reduced rate", lambda: f"={SM['s_allowed']}-{SM['s_excl']}", SQFT, "s_reg"),
                ("Rate per sq ft (SETTINGS)", lambda: f"={S('srate')}", MONEY, "s_rate"),
                ("Reduced rate: rate × time percentage, rounded to cents",
                 lambda: f"=IF({SM['excl']}>={S('smax')},{SM['s_rate']},ROUND({SM['s_rate']}*{SM['time']},2))", MONEY, "s_rrate"),
                ("Simplified method estimate", lambda: f"={SM['s_excl']}*{SM['s_rate']}+{SM['s_reg']}*{SM['s_rrate']}", MONEY, "simp")]
        for lab, f, fmt, key in simp:
            self.summary_row(ws, r, "", lab, f(), fmt, key, bold=(key == "simp"))
            r += 1
        r += 1
        # side by side
        self.tile(ws, r, 3, 4, "REGULAR METHOD: HOME EXPENSES (SECTION D)", f"={SM['home_total']}", MONEY, size=16)
        self.tile(ws, r, 5, 7, "SIMPLIFIED METHOD ESTIMATE (SECTION G)", f"={SM['simp']}", MONEY, size=16)
        SM["tile_row"] = r
        r += 2
        self.note(ws, f"C{r}:G{r}", "Estimate only. Your tax preparer will choose the right method. The regular method total "
                  "excludes depreciation and both are limited by your business income. If at least 300 sq ft is used "
                  "exclusively, no time reduction applies (Pub. 587).", height=46)
        r += 2
        self.note(ws, f"B{r}:G{r}", DISCLAIMER, height=46, size=9, color=INK, bold=True)
        ws.print_area = f"A1:H{r}"
        ws.page_setup.fitToHeight = 0
        # page breaks before sections C and E for a clean print
        from openpyxl.worksheet.pagebreak import Break
        ws.row_breaks.append(Break(id=sc_first - 3))
        self.sum_last = r
        self.protect(ws)

    def summary_row(self, ws, r, num, label, formula, fmt, key, bold=False):
        b = ws[f"B{r}"]
        b.value = num
        b.font = font(10, True, BRASS)
        b.alignment = Alignment(horizontal="center", vertical="center")
        ws.merge_cells(f"C{r}:F{r}")
        c = ws[f"C{r}"]
        c.value = label
        c.font = font(10, bold, INK)
        c.alignment = Alignment(vertical="center", indent=1)
        for col in "CDEF":
            ws[f"{col}{r}"].border = Border(bottom=Side(style="thin", color=BORDER))
        g = ws[f"G{r}"]
        self.calc(g, fmt, bold=bold, align="right")
        if formula is not None:
            g.value = formula
        SM[key] = f"$G${r}"
        ws.row_dimensions[r].height = 20

    # ============================================================ DASHBOARD
    def build_dashboard(self):
        ws = self.ws[S_DASH]
        widths = {L(c): 12.5 for c in range(2, 13)}
        widths["B"] = 15
        self.page(ws, widths, 13, 72, "Dashboard", "Where your year stands: percentages, hours, space and deductions.")
        SQ = lambda k: f"{SUMQ}!{SM[k]}"
        ws.merge_cells("B4:M4")
        self.label(ws["B4"], "=" + S("name") + '&IF(' + S("name") + '="","","  ·  ")&"Tax year "&' + S("year"), color=GREEN, size=11)
        tiles1 = [("TIME-SPACE PERCENTAGE", f"={SQ('ts')}", PCT2), ("TIME PERCENTAGE (CHECKED DAYS)", f"={SQ('time')}", PCT2),
                  ("BUSINESS HOURS COUNTED", f"={SQ('bizhours')}", HRS),
                  ("DAYS STILL TO CONFIRM", f'=COUNTIF({HR("status")},"Not yet confirmed")', "#,##0")]
        tiles2 = [("HOME EXPENSES (FORM 8829)", f"={SQ('home_total')}", MONEY), ("SIMPLIFIED METHOD ESTIMATE", f"={SQ('simp')}", MONEY),
                  ("SCHEDULE C EXPENSES", f"={SQ('sc_total')}", MONEY), ("FOOD DEDUCTION (NET)", f"={SQ('food_net')}", MONEY)]
        for r, tiles in ((5, tiles1), (8, tiles2)):
            for i, (lab, f, fmt) in enumerate(tiles):
                self.tile(ws, r, 2 + 3 * i, 4 + 3 * i, lab, f, fmt)
        ws.row_dimensions[7].height = 6
        ws.merge_cells("B11:M11")
        c = ws["B11"]
        c.value = (f'=IF(COUNTIF({HR("status")},"Not yet confirmed")=0,"All days in the hours log are checked.",'
                   f'COUNTIF({HR("status")},"Not yet confirmed")&" days in the HOURS LOG are not confirmed yet. If they match your '
                   f'usual hours, the full-year time percentage would be "&FIXED(100*{SQ("proj")},2)&"%.")')
        c.font, c.fill = font(9, True, GREEN), fill(BRASS_TINT)
        c.alignment = Alignment(vertical="center", indent=1, wrap_text=True)
        for col in range(2, 14):
            ws.cell(row=11, column=col).fill = fill(BRASS_TINT)
        ws.row_dimensions[11].height = 24

        def table_head(r, heads):
            for col, t in heads:
                self.header(ws[f"{col}{r}"], t, align="left" if col == "B" else "center")
            ws.row_dimensions[r].height = 24

        def total_row(r, cols):
            for col in cols:
                x = ws[f"{col}{r}"]
                x.fill, x.font = fill(GREEN), font(10, True, PAPER if col == "B" else BRASS)

        # ---- hours by month
        r = 13
        rows = {"hours": r}
        self.kicker(ws, f"B{r}", "Business hours by month", rule_to=13)
        hr = r + 1
        table_head(hr, [("B", "Month"), ("C", "Hours counted"), ("D", "Projected hours"), ("E", "Days to confirm")])
        HZ = f"{q(S_HOURS)}!"
        for m in range(1, 13):
            rr = hr + m
            ws[f"B{rr}"] = MONTHS[m - 1][:3]
            ws[f"B{rr}"].font = font(10, True, INK)
            self.calc(ws[f"C{rr}"], HRS, bold=True, value=f"={HZ}$Z${8 + m}")
            self.calc(ws[f"D{rr}"], HRS, value=f"={HZ}$AB${8 + m}")
            self.calc(ws[f"E{rr}"], "#,##0", align="center", value=f"={HZ}$AA${8 + m}")
        yr = hr + 13
        ws[f"B{yr}"] = "Year"
        for col in "CDE":
            ws[f"{col}{yr}"] = f"=SUM({col}{hr + 1}:{col}{hr + 12})"
            ws[f"{col}{yr}"].number_format = HRS if col != "E" else "#,##0"
            ws[f"{col}{yr}"].alignment = Alignment(horizontal="center" if col == "E" else None)
        total_row(yr, "BCDE")
        ch = BarChart()
        ch.type, ch.style = "col", 10
        ch.add_data(Reference(ws, min_col=3, max_col=4, min_row=hr, max_row=hr + 12), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=hr + 1, max_row=hr + 12))
        for s_, colr in zip(ch.series, (GREEN, "E3C68F")):
            s_.graphicalProperties.solidFill = colr
            s_.graphicalProperties.line.solidFill = colr
        BP.clean_chart(ch, legend=True)
        ch.gapWidth, ch.overlap = 50, -10
        ch.height, ch.width = 7.6, 17.2
        ch.anchor = f"G{hr}"
        ws.add_chart(ch)

        # ---- space
        r = yr + 2
        rows["space"] = r
        self.kicker(ws, f"B{r}", "How your home is used", rule_to=13)
        hr = r + 1
        table_head(hr, [("B", "Use"), ("C", "Square feet"), ("D", "Share of home")])
        ws.merge_cells(f"E{hr}:F{hr}")
        RQ = lambda k: f"{q(S_ROOMS)}!{RM[k]}"
        uses = [("Exclusive", "excl"), ("Regular", "reg"), ("Not used", "none")]
        for i, (lab, k) in enumerate(uses):
            rr = hr + 1 + i
            ws[f"B{rr}"] = lab
            ws[f"B{rr}"].font = font(10, True, INK)
            self.calc(ws[f"C{rr}"], SQFT, value=f"={RQ(k)}")
            self.calc(ws[f"D{rr}"], PCT2, value=f"=IF(N({RQ('home')})=0,0,C{rr}/{RQ('home')})")
        sp_first, sp_last = hr + 1, hr + 3
        BP.databar(ws, f"D{sp_first}:D{sp_last}", BRASS, max_value=1)
        tr = hr + 4
        ws[f"B{tr}"] = "Home"
        ws[f"C{tr}"] = f"={RQ('home')}"
        ws[f"D{tr}"] = f"=SUM(D{sp_first}:D{sp_last})"
        ws[f"C{tr}"].number_format, ws[f"D{tr}"].number_format = SQFT, PCT2
        total_row(tr, "BCD")
        nr = tr + 1
        ws.merge_cells(f"B{nr}:F{nr + 1}")
        ws[f"B{nr}"] = (f'="Exclusive space counts in full. Regular space counts for the share of the day it is used: "'
                        f'&FIXED(100*{SQ("reg_pct")},2)&"% × "&FIXED(100*{SQ("time")},2)&"% time = "&FIXED(100*{SQ("reg_time")},2)'
                        f'&"%. Time-space percentage: "&FIXED(100*{SQ("ts")},2)&"%."')
        ws[f"B{nr}"].font = font(9, False, INK2)
        ws[f"B{nr}"].alignment = Alignment(wrap_text=True, vertical="top")
        ch = DoughnutChart(holeSize=55)
        ch.add_data(Reference(ws, min_col=3, min_row=sp_first, max_row=sp_last), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=sp_first, max_row=sp_last))
        for i, colr in enumerate((GREEN, BRASS, "C9D3CF")):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.solidFill = "FFFFFF"
            ch.series[0].dPt.append(pt)
        BP.clean_chart(ch, legend=True, axes=False, legend_pos="r")
        ch.height, ch.width = 4.4, 12.5
        ch.anchor = f"G{hr}"
        ws.add_chart(ch)

        # ---- deductions
        ws.row_dimensions[nr].height = ws.row_dimensions[nr + 1].height = 18
        r = nr + 3
        rows["ded"] = r
        self.kicker(ws, f"B{r}", "Where your deductions come from", rule_to=13)
        hr = r + 1
        table_head(hr, [("B", "Part"), ("C", ""), ("D", "Amount"), ("E", "Share")])
        ws.merge_cells(f"B{hr}:C{hr}")
        parts = [("Home expenses (8829)", f"={SQ('home_total')}"),
                 ("Supplies and other (Sch. C)", f"={SQ('sc_total')}-{SQ('mile_ded')}-{SQ('food_net')}"),
                 ("Car: standard mileage", f"={SQ('mile_ded')}"),
                 ("Food for children (net)", f"={SQ('food_net')}")]
        d_first = hr + 1
        d_last = hr + len(parts)
        for i, (lab, f) in enumerate(parts):
            rr = d_first + i
            ws.merge_cells(f"B{rr}:C{rr}")
            ws[f"B{rr}"] = lab
            ws[f"B{rr}"].font = font(10, True, INK)
            self.calc(ws[f"D{rr}"], MONEY, value=f)
            self.calc(ws[f"E{rr}"], PCT2, value=f"=IF(SUM($D${d_first}:$D${d_last})=0,0,D{rr}/SUM($D${d_first}:$D${d_last}))")
        BP.databar(ws, f"E{d_first}:E{d_last}", GREEN, max_value=1)
        tr = d_last + 1
        ws.merge_cells(f"B{tr}:C{tr}")
        ws[f"B{tr}"] = "Total (before limits)"
        ws[f"D{tr}"] = f"=SUM(D{d_first}:D{d_last})"
        ws[f"E{tr}"] = f"=SUM(E{d_first}:E{d_last})"
        ws[f"D{tr}"].number_format, ws[f"E{tr}"].number_format = MONEY, PCT2
        total_row(tr, "BCDE")
        nr = tr + 1
        ws.merge_cells(f"B{nr}:F{nr + 1}")
        ws[f"B{nr}"] = ("Home expenses are before depreciation and the business-income limit. Your tax preparer applies "
                        "both and chooses between the regular and simplified methods.")
        ws[f"B{nr}"].font = font(9, False, INK2)
        ws[f"B{nr}"].alignment = Alignment(wrap_text=True, vertical="top")
        ch = DoughnutChart(holeSize=55)
        ch.add_data(Reference(ws, min_col=4, min_row=d_first, max_row=d_last), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=d_first, max_row=d_last))
        for i, colr in enumerate(DONUT[:4]):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.solidFill = "FFFFFF"
            ch.series[0].dPt.append(pt)
        BP.clean_chart(ch, legend=True, axes=False, legend_pos="r")
        ch.height, ch.width = 4.4, 12.5
        ch.anchor = f"G{hr}"
        ws.add_chart(ch)

        # ---- largest categories (helper list in hidden columns O:Q, sorted with LARGE + a row tie-break)
        r = nr + 3
        rows["cats"] = r
        self.kicker(ws, f"B{r}", "Largest deductible categories", rule_to=13)
        hr = r + 1
        table_head(hr, [("B", "Category"), ("C", ""), ("D", ""), ("E", "Deductible")])
        ws.merge_cells(f"B{hr}:D{hr}")
        cats = SM["cat_cells"]
        h1 = hr + 1
        h2 = h1 + len(cats) - 1
        for i, (cat, cell_) in enumerate(cats):
            rr = h1 + i
            ws[f"O{rr}"] = cat
            ws[f"P{rr}"] = f"=N({SUMQ}!{cell_})"
            ws[f"Q{rr}"] = f"=ROUND(P{rr},2)+({len(cats)}-{i})/1000000"
        for col in "OPQ":
            ws.column_dimensions[col].hidden = True
        TOP = 8
        t1 = hr + 1
        for k in range(TOP):
            rr = t1 + k
            m = f"MATCH(LARGE($Q${h1}:$Q${h2},{k + 1}),$Q${h1}:$Q${h2},0)"
            ws.merge_cells(f"B{rr}:D{rr}")
            ws[f"B{rr}"] = f'=IF(INDEX($P${h1}:$P${h2},{m})<=0,"",INDEX($O${h1}:$O${h2},{m}))'
            ws[f"B{rr}"].font = font(10, False, INK)
            self.calc(ws[f"E{rr}"], MONEY, bold=True, value=f"=MAX(0,INDEX($P${h1}:$P${h2},{m}))")
        BP.databar(ws, f"E{t1}:E{t1 + TOP - 1}", BRASS)
        ch = BarChart()
        ch.type, ch.style = "bar", 10
        ch.add_data(Reference(ws, min_col=5, min_row=t1, max_row=t1 + TOP - 1), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=t1, max_row=t1 + TOP - 1))
        s_ = ch.series[0]
        s_.graphicalProperties.solidFill = BRASS
        s_.graphicalProperties.line.solidFill = BRASS
        BP.clean_chart(ch, legend=False)
        ch.x_axis.scaling.orientation = "maxMin"
        ch.x_axis.tickLblSkip = 1
        ch.gapWidth = 40
        ch.height, ch.width = 8.4, 17.2
        ch.anchor = f"G{hr}"
        ws.add_chart(ch)
        r = t1 + TOP + 7
        self.note(ws, f"B{r}:M{r}", DISCLAIMER, height=34, size=9, color=INK, bold=True)
        ws.print_area = f"A1:M{r}"
        rows["end"] = r
        self.dash_rows = rows
        self.protect(ws)

    # ============================================================ TIME-SPACE STATEMENT
    def build_statement(self):
        ws = self.ws[S_STMT]
        widths = dict(B=6, C=50, D=18, E=18, F=18)
        self.page(ws, widths, 6, 44, "Time-space statement", "One printable page for your tax preparer.", landscape=False)
        g = lambda k: f"{SUMQ}!{SM[k]}"
        ws.merge_cells("B5:F5")
        ws["B5"] = "Statement: business-use percentage of the home for a daycare facility"
        ws["B5"].font = Font(name=TITLE, size=15, bold=True, color=GREEN)
        ws.row_dimensions[5].height = 28
        ws.merge_cells("B6:F6")
        ws["B6"] = f'="Provider: "&IF({S("name")}="","__________________",{S("name")})&"     Tax year: "&{S("year")}'
        ws["B6"].font = font(10, True, INK)
        ws.merge_cells("B7:F7")
        ws["B7"] = ('="Attachment to Form 8829, line 7. "&IF(' + g("excl") + '>0,"Part of the home is used exclusively for daycare and '
                    'part regularly but not exclusively, so the percentage is figured in two parts (Form 8829 instructions, Special '
                    'Computation for Certain Daycare Facilities).","No area is used exclusively; this page shows the time and space '
                    'figures behind lines 3 to 7.")')
        ws["B7"].font = font(9, False, INK2)
        ws["B7"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[7].height = 44
        r = 9
        sections = [
            ("Part 1  ·  Area used exclusively for daycare", [
                ("a", "Area used exclusively for daycare (sq ft)", g("excl"), SQFT),
                ("b", "Total area of the home (sq ft)", g("home"), SQFT),
                ("c", "Exclusive-use percentage (a ÷ b)", g("excl_pct"), PCT2)]),
            ("Part 2  ·  Area used regularly, not exclusively, for daycare", [
                ("d", "Area used regularly for daycare (sq ft)", g("reg"), SQFT),
                ("e", "Space percentage (d ÷ b)", g("reg_pct"), PCT2),
                ("f", "Hours the home was used for daycare during the year", g("bizhours"), HRS),
                ("g", "Total hours available: 24 × days available", g("avail"), "#,##0"),
                ("h", "Time percentage (f ÷ g)", g("time"), PCT2),
                ("i", "Business percentage for this area (e × h)", g("reg_time"), PCT2)]),
            ("Part 3  ·  Business percentage", [
                ("j", "Business percentage (c + i): enter on Form 8829 line 7", g("ts"), PCT2)])]
        for title, rows in sections:
            self.kicker(ws, f"B{r}", title, rule_to=6)
            r += 1
            for letter, lab, f, fmt in rows:
                ws[f"B{r}"] = letter
                ws[f"B{r}"].font = font(10, True, BRASS)
                ws[f"B{r}"].alignment = Alignment(horizontal="center", vertical="center")
                ws.merge_cells(f"C{r}:E{r}")
                ws[f"C{r}"] = lab
                ws[f"C{r}"].font = font(10, letter == "j", INK)
                ws[f"C{r}"].alignment = Alignment(indent=1, vertical="center")
                for col in "CDE":
                    ws[f"{col}{r}"].border = Border(bottom=Side(style="thin", color=BORDER))
                self.calc(ws[f"F{r}"], fmt, bold=(letter == "j"), align="right", value=f"={f}")
                ws.row_dimensions[r].height = 22
                if letter == "j":
                    for col in "BCDEF":
                        ws[f"{col}{r}"].fill = fill(GREEN)
                    ws[f"C{r}"].font = font(10, True, PAPER)
                    ws[f"F{r}"].font = font(13, True, BRASS)
                    ws.row_dimensions[r].height = 28
                r += 1
            r += 1
        ws.merge_cells(f"B{r}:F{r}")
        ws[f"B{r}"] = (f'="Business days: "&IF(ISNUMBER({S("first")}),MONTH({S("first")})&"/"&DAY({S("first")})&"/"&YEAR({S("first")}),"")'
                       f'&" to "&IF(ISNUMBER({S("last")}),MONTH({S("last")})&"/"&DAY({S("last")})&"/"&YEAR({S("last")}),"")'
                       f'&" ("&{S("days")}&" days). Hours include time children were in care and other business use of the home '
                       f'(preparation, cleaning, record keeping) recorded in the daily hours log."')
        ws[f"B{r}"].font = font(9, False, INK2)
        ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 40
        r += 2
        for lab in ("Prepared by", "Date"):
            ws[f"C{r}"] = lab + ":  ______________________________"
            ws[f"C{r}"].font = font(10, False, INK)
            r += 2
        self.note(ws, f"B{r}:F{r}", DISCLAIMER, height=46, size=8)
        ws.print_area = f"A1:G{r}"
        ws.page_setup.fitToHeight = 1
        self.protect(ws)

    # ============================================================ FOR YOUR TAX PREPARER
    def build_preparer(self):
        ws = self.ws[S_PREP]
        widths = dict(B=70, C=16, D=36, E=16, F=14)
        self.page(ws, widths, 6, 64, "For your tax preparer", "Home details, improvements, carryovers and a document checklist.", landscape=False)
        self.note(ws, "B4:F4", "Home depreciation is not calculated in this workbook. Give these details to your tax preparer, who "
                  "will figure depreciation on Form 8829 Part III.", height=34, size=10, color=INK, bold=True)
        self.kicker(ws, "B6", "Your home", rule_to=6)
        d = self.data if self.sample else None
        home = [(7, "Date you bought the home", DATE, "buy_date"), (8, "Purchase price (including closing costs)", MONEY, "price"),
                (9, "Value of the land included in the price", MONEY, "land"),
                (10, "Date you first used the home for daycare", DATE, "first_use"),
                (11, "Last year's time-space percentage (if any)", PCT2, "prior_ts"),
                (12, "Did you use the simplified method last year?", None, "prior_simple"),
                (13, "Carryover of operating expenses (last year's Form 8829 line 43)", MONEY, "co_ops"),
                (14, "Carryover of excess casualty losses and depreciation (line 44)", MONEY, "co_dep")]
        for r, lab, fmt, key in home:
            self.label(ws[f"B{r}"], lab, bold=False)
            self.inp(ws[f"C{r}"], fmt, "right")
            if d:
                ws[f"C{r}"].value = d.PREPARER.get(key)
        self.yn(ws, "C12", "Yes,No", "Simplified method")
        self.dv(ws, "date", "C7", operator="between", formula1="1", formula2="73051", errorTitle="Date", error="Enter a date.")
        self.dv(ws, "date", "C10", operator="between", formula1="1", formula2="73051", errorTitle="Date", error="Enter a date.")
        self.kicker(ws, "B17", "Improvements to the home (new roof, fence, remodel)", rule_to=6)
        for col, t in zip("BCDE", ["Description", "Date", "Area improved", "Cost"]):
            self.header(ws[f"{col}18"], t, align="left" if col in "BD" else "center")
        for r in range(19, 29):
            self.inp(ws[f"B{r}"])
            self.inp(ws[f"C{r}"], DATE, "center")
            self.inp(ws[f"D{r}"])
            self.inp(ws[f"E{r}"], MONEY)
        self.label(ws["D29"], "Total", color=GREEN)
        self.calc(ws["E29"], MONEY, bold=True, value="=SUM(E19:E28)")
        self.dv(ws, "date", "C19:C28", operator="between", formula1="1", formula2="73051", errorTitle="Date", error="Enter a date.")
        if d:
            for i, (desc, dt_, area, cost) in enumerate(d.IMPROVEMENTS):
                ws[f"B{19 + i}"].value, ws[f"C{19 + i}"].value, ws[f"D{19 + i}"].value, ws[f"E{19 + i}"].value = desc, dt_, area, cost
        self.kicker(ws, "B31", "Business income (optional)", rule_to=6)
        inc = [(32, "Parent fees received", "fees"), (33, "Food program (CACFP) reimbursements (from SETTINGS)", None),
               (34, "Grants and subsidies", "grants"), (35, "Other business income", "other_inc")]
        for r, lab, key in inc:
            self.label(ws[f"B{r}"], lab, bold=False)
            if key:
                self.inp(ws[f"C{r}"], MONEY, "right")
                if d:
                    ws[f"C{r}"].value = d.PREPARER.get(key)
            else:
                self.calc(ws[f"C{r}"], MONEY, align="right", value=f"=N({S('reimb')})")
        self.label(ws["B36"], "Total", color=GREEN)
        self.calc(ws["C36"], MONEY, bold=True, value="=SUM(C32:C35)")
        self.kicker(ws, "B39", "Documents to bring", rule_to=6)
        self.header(ws["B40"], "Document", align="left")
        self.header(ws["C40"], "Ready?")
        ws.merge_cells("D40:F40")
        self.header(ws["D40"], "Notes", align="left")
        docs = ["This workbook: SUMMARY and TIME-SPACE STATEMENT printed", "Daycare license or registration",
                "Form 1098 mortgage interest statement (or rent records)", "Property tax bills", "Homeowner's or renter's insurance declarations",
                "Utility bills for the year", "Receipts for business and household expenses", "Food program statements (CACFP reimbursements)",
                "Records of parent payments (income)", "Forms 1099-NEC, 1099-K or 1099-MISC received", "Hours log and meal log (this file)",
                "Mileage log (this file)", "Last year's tax return and Form 8829", "Home purchase documents and improvement receipts"]
        for i, doc in enumerate(docs):
            r = 41 + i
            self.label(ws[f"B{r}"], doc, bold=False)
            self.inp(ws[f"C{r}"], align="center")
            ws.merge_cells(f"D{r}:F{r}")
            self.inp(ws[f"D{r}"])
            for col in "EF":
                self.inp(ws[f"{col}{r}"])
            if d:
                ws[f"C{r}"].value = "Y" if i < 11 else None
        self.yn(ws, f"C41:C{40 + len(docs)}")
        r = 42 + len(docs)
        self.note(ws, f"B{r}:F{r}", DISCLAIMER, height=46, size=9, color=INK, bold=True)
        ws.print_area = f"A1:G{r}"
        self.protect(ws)

    # ============================================================ assemble
    def build(self):
        # SUMMARY anchors are needed by other tabs: build it first (formulas referencing other tabs are fine)
        self.build_summary()
        self.build_start()
        self.build_settings()
        self.build_rooms()
        self.build_hours()
        self.build_expenses()
        self.build_meals()
        self.build_mileage()
        self.build_statement()
        self.build_preparer()
        self.build_dashboard()
        # hours tiles that point at SUMMARY
        hs = self.ws[S_HOURS]
        hs["I5"].value = f"={SUMQ}!{SM['time']}"
        hs["L5"].value = f"={SUMQ}!{SM['proj']}"
        # MIN1/MIN3 placeholders are not used; nothing to replace
        self.wb.active = 0
        for ws in self.wb.worksheets:
            ws.sheet_view.tabSelected = ws.title == S_START
        self.wb.calculation.fullCalcOnLoad = True
        p = self.wb.properties
        p.title, p.creator, p.subject = PRODUCT, "Brass Ledger", "Simple tools for small business numbers."
        return self.wb


def add_sidebars(wb):
    """Icon sidebar on every tab (Excel shapes, with text links underneath for Google Sheets)."""
    return BP.add_sidebars(wb, NAV, {S_START: 70, S_DASH: 72, S_SET: 90, S_ROOMS: 60, S_HOURS: 120, S_EXP: 120,
                                     S_MEALS: 120, S_MILES: 120, S_SUM: 120, S_STMT: 60, S_PREP: 70})


def main(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for sample in (False, True):
        SM.clear()
        wb = Builder(sample).build()
        p = out_dir / (OUT_NAME + ("_SAMPLE" if sample else "") + ".xlsx")
        layers = add_sidebars(wb)
        wb.save(p)
        BP.finish(p, layers)
        paths.append(p)
        print("wrote", p)
    return paths


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "dist" / "home-daycare-tax-workbook")
