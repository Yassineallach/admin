"""PRODUCT 4 — Ultimate Budget Spreadsheet (28 tabs).

Usage:  python build_budget.py [--out DIR]
Builds four workbooks: Excel / Google-Sheets editions, each with DEMO data and BLANK.

Money model (one place for every number):
  * Variable Transactions  — what you log (income, spending, savings transfers, debt payments)
  * Recurring Transactions — repeating items; every occurrence up to today is posted automatically (Setup switch)
  * Payments               — one-off bills; counted once marked Paid (in the month they're due)
  All three feed the category x month matrix on Annual Totals; monthly tabs, dashboards, 50/30/20 and Expense
  Distribution read from it, so a number can never disagree between tabs.
  A transaction's Type (Income / Expense / Savings / Debt Payment) comes from its category: income categories and
  expense categories from Setup, savings categories = Sinking Fund names, debt categories = Debt Calculator names.

The budget year can start in any month (Setup): month tab "March" is the March inside the 12-month budget period.
Formula policy: INDEX/MATCH, SUMIFS/COUNTIFS, SUMPRODUCT, NPER, EDATE; no dynamic arrays/LET/XLOOKUP/macros;
conditional formatting only references its own sheet.
"""
from __future__ import annotations

import argparse
import calendar as _cal
import datetime as dt
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, DoughnutChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.series import DataPoint
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, Protection
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.table import Table, TableStyleInfo

from common import *  # noqa: F401,F403
from common import _cells
import common as _C
import sample_data_bg as SD

# ---------------------------------------------------------------- sheet names
S_SET, S_BA, S_RT, S_PAY, S_TR = "Easy Setup", "Bank Accounts", "Recurring Transactions", "Payments", "Variable Transactions"
S_DASH, S_AT, S_CAL, S_PC = "All-in-One Dashboard", "Annual Totals", "Automated Calendar", "Paycheck Dashboard"
MONTHS = list(_cal.month_name)[1:]
S_503, S_ED, S_SF, S_DC = "50-30-20 Dashboard", "Expense Distribution", "Sinking Funds", "Debt Calculator"
S_NW, S_IF, S_NS = "Net Worth", "Investment Forecast", "No-Spending Challenge"
ORDER = [S_SET, S_BA, S_RT, S_PAY, S_TR, S_DASH, S_AT, S_CAL, S_PC, *MONTHS, S_503, S_ED, S_SF, S_DC, S_NW, S_IF, S_NS]
NAV = [(S_SET, "gear", "Setup"), (S_BA, "bank", "Banks"), (S_RT, "repeat", "Recur"), (S_PAY, "receipt", "Bills"),
       (S_TR, "table", "Trans"), (S_DASH, "bar_chart", "Home"), (S_AT, "stack", "Annual"), (S_CAL, "calendar", "Cal"),
       (S_PC, "wallet", "Pay"), ("January", "week", "Months"), (S_503, "pie", "50/30"), (S_ED, "donut", "Spend"),
       (S_SF, "piggy", "Funds"), (S_DC, "card", "Debt"), (S_NW, "scale", "Worth"), (S_IF, "trend", "Invest"),
       (S_NS, "ban", "No-spend")]

# finance colours (spec): teal income, red expenses, blue savings, lavender goals
C_INC, C_EXP, C_SAV, C_GOAL, C_DEBT = "14958B", "CF3A43", "2F6FAA", "9B7BE0", "B26B00"
INC_BG, EXP_BG, SAV_BG, GOAL_BG = "E1F3F0", "FBE3E5", "E3EEF8", "EFEAFB"
FMT_M = '#,##0.00'
FMT_M0 = '#,##0'

# ---------------------------------------------------------------- geometry
INC1, INCN = 25, 36            # Setup income categories
EXP1, EXPN = 40, 69            # Setup expense categories
M1, MN = 5, 67                 # Setup master category rows (hidden AA..)
TR1, TRN = 9, 1008             # Variable Transactions
RT1, RTN = 9, 68               # Recurring
PY1, PYN = 9, 108              # Payments
BA1, BAN = 9, 18               # Bank accounts
SF1, SFN = 9, 18               # Sinking funds
DC1, DCN = 9, 18               # Debts
PC1, PCN = 9, 60               # Paychecks
MX1, MXN = 45, 107             # Annual Totals matrix
AT1 = 10                       # Annual Totals month rows 10..21, total 22
LD1, LDN = 5, 404              # Automated Calendar daily ledger (hidden)
RT_CNT = 18                    # recurring: first per-month count column (R)
RT_AMT = RT_CNT + 12           # first per-month amount column (AD)
TODAY, YEAR, AUTO, DUE, SYM, START, P0 = "BudToday", "BudYear", "AutoRecurring", "DueSoonDays", "CurSym", "StartMonthNum", "PeriodStart"


def q(s):
    return quote(s)


def R(sheet, c, r1, r2):
    return f"{q(sheet)}!${c}${r1}:${c}${r2}"


def TR(c): return R(S_TR, c, TR1, TRN)
def RT(c): return R(S_RT, c, RT1, RTN)
def PY(c): return R(S_PAY, c, PY1, PYN)
def BA(c): return R(S_BA, c, BA1, BAN)
def SF(c): return R(S_SF, c, SF1, SFN)
def DC(c): return R(S_DC, c, DC1, DCN)
def MX(c): return R(S_AT, c, MX1, MXN)
def ST(c, r1=M1, r2=MN): return R(S_SET, c, r1, r2)


MX_MONTHS = f"{q(S_AT)}!$F${MX1}:$Q${MXN}"


def cat_lists():
    """Compact helper lists on Setup (hidden): name -> (running-number column, compact column)."""
    return {"all": ("AF", "AG"), "fixed": ("AM", "AN"), "variable": ("AO", "AP"), "income": ("AQ", "AR"),
            "funds": ("AS", "AT"), "debts": ("AU", "AV"), "expense": ("AW", "AX"), "needs": ("AY", "AZ"), "wants": ("BA", "BB")}


def LIST(name):
    return ST(cat_lists()[name][1])


def cf_databar_amt(ws, rng, color):
    """Data bar scaled from 0 to the largest value in the range (for amounts, not percentages)."""
    from openpyxl.formatting.rule import DataBarRule
    ws.conditional_formatting.add(rng, DataBarRule(start_type="num", start_value=0, end_type="max", color=color,
                                                   showValue=True, minLength=0, maxLength=100))


class Builder:
    def __init__(self, edition: str, demo: bool):
        self.ed, self.demo = edition, demo
        self.T = Theme(edition)
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in ORDER}
        tabc = {S_SET: LAVENDER, S_BA: TEAL, S_RT: TEAL, S_PAY: TEAL, S_TR: TEAL, S_DASH: NAVY, S_AT: NAVY, S_CAL: NAVY,
                S_PC: NAVY, S_503: C_GOAL, S_ED: C_GOAL, S_SF: C_GOAL, S_DC: C_GOAL, S_NW: C_GOAL, S_IF: C_GOAL, S_NS: C_GOAL}
        for n in ORDER:
            self.ws[n].sheet_properties.tabColor = tabc.get(n, BLUE)
        self.unlocked = {n: [] for n in ORDER}
        _C.TAB_ORDER[:] = ORDER

    # ------------------------------------------------------------ helpers
    def inp(self, s, a, numfmt=None, align=None):
        style_input(self.ws[s], a, self.T, numfmt, align)
        self.unlocked[s].append(a)

    def opt(self, s, a, numfmt=None, align=None):
        paint(self.ws[s], a, f=FILL_OPT, font=self.T.font(10), border=_C.CELL_BOX, align=align or LEFT, numfmt=numfmt)
        self.unlocked[s].append(a)

    def calc(self, s, a, numfmt=None, align=None, color=DARK, bold=False):
        style_calc(self.ws[s], a, self.T, numfmt, align, color)
        if bold:
            for c in _cells(self.ws[s], a):
                c.font = self.T.font(10, True, color)

    def merge(self, ws, a, value=None):
        if ":" in a and a.split(":")[0] != a.split(":")[1]:
            ws.merge_cells(a)
        tl = a.split(":")[0]
        if value is not None:
            ws[tl] = value
        return ws[tl]

    def label(self, ws, a, text, size=10, bold=True, color=DARK, align=None, italic=False):
        c = self.merge(ws, a, text)
        c.font = self.T.font(size, bold, color, italic=italic)
        c.alignment = align or Alignment(vertical="center", indent=1)
        return c

    def head(self, ws, r, c1, heads, fill_="E2F2EF", color=MIDNIGHT, height=26):
        """heads: list of (text, span) or text."""
        c = c1
        for h in heads:
            t, span = (h, 1) if isinstance(h, str) else h
            a = f"{L(c)}{r}" if span == 1 else f"{L(c)}{r}:{L(c + span - 1)}{r}"
            cell = self.merge(ws, a, t)
            paint(ws, a, f=fill(fill_), border=Border(left=_C.CELL_EDGE, right=_C.CELL_EDGE, top=_C.CELL_EDGE,
                                                      bottom=Side(style="medium", color=BLUE)))
            cell.font = self.T.font(9, True, color)
            cell.alignment = CENTER
            c += span
        ws.row_dimensions[r].height = height

    def tile(self, ws, r, c1, c2, label, formula, numfmt=None, accent=BLUE, size=15, color=DARK):
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
        vc.font = self.T.font(size, True, color)
        vc.alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
        if numfmt:
            vc.number_format = numfmt
        ws.row_dimensions[r].height = 18
        ws.row_dimensions[r + 1].height = 30

    def tiles(self, ws, r, specs, c1=2, width=None, gap=0):
        """specs: list of (label, formula, numfmt, accent[, color]) laid out across equal spans."""
        c = c1
        for s in specs:
            label, f, nf, acc = s[:4]
            color = s[4] if len(s) > 4 else DARK
            self.tile(ws, r, c, c + width - 1, label, f, nf, acc, color=color)
            c += width + gap

    def table(self, ws, name, ref):
        if self.ed == "excel":
            t = Table(displayName=name, ref=ref)
            t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=False, showColumnStripes=False)
            ws.add_table(t)
        else:
            ws.auto_filter.ref = ref

    def title(self, ws, title, sub, last_col, home=S_DASH, label="⌂ Dashboard"):
        title_bar(ws, self.T, title, sub, last_col, home_link=home, home_label=label, demo=self.demo)

    def note(self, ws, a, text, size=9):
        c = self.merge(ws, a, text)
        c.font = self.T.font(size, False, SECONDARY, italic=True)
        c.alignment = Alignment(vertical="center", wrap_text=True, indent=1)
        return c

    def period_selector(self, ws, s, cell_lbl, cell_sel, helper):
        """Full year / month dropdown; `helper` cell gets the period index (0 = full year)."""
        self.label(ws, cell_lbl, "PERIOD", 9, True, SECONDARY, RIGHT)
        a = cell_sel
        self.merge(ws, a, "Full year")
        self.inp(s, a, align=CENTER)
        add_list_dv(ws, a.split(":")[0], f"{q(S_SET)}!$BD${M1}:$BD${M1 + 12}")
        ws[helper] = f'=IF({a.split(":")[0]}="Full year",0,IFERROR(MATCH({a.split(":")[0]},{q(S_AT)}!$B${AT1}:$B${AT1 + 11},0),0))'

    def chart_style(self, ch, title, colors=None, legend=True, h=7.5, w=13):
        ch.title = title
        ch.style = 10
        ch.visible_cells_only = False           # helper data lives in hidden columns
        ch.height, ch.width = h, w
        if not legend:
            ch.legend = None
        else:
            ch.legend.position = "b"
        for i, s in enumerate(ch.series):
            if colors and i < len(colors):
                s.graphicalProperties.solidFill = colors[i]
                s.graphicalProperties.line.solidFill = colors[i]
        return ch

    # ================================================================ 1 EASY SETUP
    def build_setup(self):
        ws, T, S = self.ws[S_SET], self.T, S_SET
        setup_sheet(ws, {"B": 34, "C": 20, "D": 15, "E": 15, "F": 15, "G": 3, "H": 24, "I": 16, "J": 22, "K": 14, "L": 3,
                         **{L(c): 13 for c in range(14, 26)}})
        title_bar(ws, T, "EASY SETUP  ·  Ultimate Budget", "Start here — currency, budget year, categories and budgets. "
                  "Every dropdown and total reads from this tab.", 12, home_link=S_DASH, demo=self.demo)
        c = self.merge(ws, "B5:K8", (
            "WELCOME TO THE ULTIMATE BUDGET SPREADSHEET.   1) Choose your currency, budget year and the month your budget "
            "starts.   2) Edit income and expense categories and set a monthly budget for each.   3) Add your accounts on Bank "
            "Accounts, savings goals on Sinking Funds and debts on Debt Calculator.   4) Log money on Variable Transactions, "
            "Recurring Transactions and Payments — every dashboard, month and chart updates by itself.   "
            "Light-mint cells are inputs; grey cells calculate. "
            + ("This copy contains DEMO DATA: use the BLANK file to start fresh." if self.demo else "")))
        paint(ws, "B5:K8", f=fill(SOFT_BLUE))
        c.font = T.font(10, False, MIDNIGHT)
        c.alignment = LEFT_WRAP
        for r in range(5, 9):
            ws.row_dimensions[r].height = 18
        ws.row_dimensions[4].height = 12
        legend(ws, T, 9, 2)
        ws.row_dimensions[9].height = 24

        section(ws, T, 10, 2, 6, "BUDGET PREFERENCES")
        prefs = [("Your name", SD.NAME if self.demo else None, "text", "Shown on the dashboard"),
                 ("Budget year", SD.YEAR if self.demo else "=YEAR(TODAY())", "year", "The year your budget period starts in"),
                 ("First month of your budget", SD.START_MONTH, "month", "Start in any month — 12 months follow"),
                 ("Currency", "USD", "cur", "Pick from the list"),
                 ("Currency symbol", f'=IFERROR(INDEX($Q$12:$Q$23,MATCH(C14,$P$12:$P$23,0)),"$")', "calc", "Automatic"),
                 ("Starting balance", f"=SUM({BA('E')})", "calcm", "Sum of account opening balances"),
                 ("Today's date override", SD.ANCHOR if self.demo else None, "date",
                  "DEMO date — clear it to use today" if self.demo else "Leave blank to use the real date"),
                 ("Effective today", '=IF(C17="",TODAY(),C17)', "calcd", "Drives every 'today' calculation"),
                 ("Auto-post recurring items", "Yes", "yn", "Yes = each occurrence up to today counts"),
                 ("Due-soon window (days)", 7, "int", "Payments due within N days are flagged"),
                 ("Budget period", f'=TEXT({P0},"mmm yyyy")&" – "&TEXT(EDATE({P0},11),"mmm yyyy")', "calc", "Your 12 budget months")]
        for i, (lab, val, kind, hint) in enumerate(prefs):
            r = 11 + i
            self.label(ws, f"B{r}", lab)
            ws[f"C{r}"] = val
            if kind.startswith("calc"):
                self.calc(S, f"C{r}", {"calcm": FMT_M, "calcd": FMT_DATE}.get(kind), CENTER)
            else:
                self.inp(S, f"C{r}", {"date": FMT_DATE, "int": "0", "year": "0"}.get(kind), CENTER)
            self.note(ws, f"D{r}:F{r}", hint)
            ws.row_dimensions[r].height = 21
        add_list_dv(ws, "C12", R(S, "O", 12, 23))
        add_list_dv(ws, "C13", R(S, "N", 12, 23))
        add_list_dv(ws, "C14", R(S, "P", 12, 23))
        add_dv(ws, "C17", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a valid date, or leave blank.")
        add_list_dv(ws, "C19", R(S, "R", 12, 13))
        add_dv(ws, "C20", "whole", "between", "0", "60")
        ws["Z1"] = "helpers"
        ws["Z2"] = "=IFERROR(MATCH(C13,$N$12:$N$23,0),1)"
        ws["Z3"] = "=DATE(C12,Z2,1)"
        ws["Z3"].number_format = FMT_DATE

        section(ws, T, 10, 8, 11, "HOW THE MONEY FLOWS", color=LAVENDER)
        flow = ["Variable Transactions — log income and spending as it happens.",
                "Recurring Transactions — salary, rent, subscriptions, savings transfers and loan payments repeat by themselves.",
                "Payments — one-off bills with due dates; they count once marked Paid.",
                "The Type of every entry comes from its category: income, expense, savings (a Sinking Fund) or debt (a debt on Debt Calculator).",
                "Annual Totals adds everything up by category and month; the 12 month tabs, dashboards and charts read from it.",
                "Expense categories: Fixed or Variable (month tabs), Needs or Wants (50/30/20).",
                "Savings transfers move money into the account a Sinking Fund is held in.",
                "Colours: teal = income, red = expenses, blue = savings, lavender = goals."]
        for i, t in enumerate(flow):
            r = 11 + i
            c = self.merge(ws, f"H{r}:K{r}", "•  " + t)
            c.font = T.font(9)
            c.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        ws.row_dimensions[22].height = 12

        # income categories
        section(ws, T, 23, 2, 6, "INCOME CATEGORIES", color=C_INC)
        self.head(ws, 24, 2, ["Category", "Expected / month", ("Notes", 3)])
        for i in range(INCN - INC1 + 1):
            r = INC1 + i
            if i < len(SD.INCOME):
                ws[f"B{r}"], ws[f"C{r}"] = SD.INCOME[i][0], (SD.INCOME[i][1] if self.demo else 0)
            self.inp(S, f"B{r}")
            self.inp(S, f"C{r}", FMT_M, RIGHT)
            self.merge(ws, f"D{r}:F{r}")
            self.opt(S, f"D{r}:F{r}")
        # payment methods & account types
        section(ws, T, 23, 8, 11, "PAYMENT METHODS & ACCOUNT TYPES")
        self.head(ws, 24, 8, ["Payment methods", "Account types", "Debt types", "Fund status"])
        for i in range(12):
            r = INC1 + i
            ws[f"H{r}"] = SD.PAY_METHODS[i] if i < len(SD.PAY_METHODS) else None
            ws[f"I{r}"] = ["Checking", "Savings", "Credit card", "Cash", "Investment", "Other"][i] if i < 6 else None
            ws[f"J{r}"] = ["Credit card", "Loan", "Mortgage", "Other"][i] if i < 4 else None
            self.inp(S, f"H{r}:J{r}")
        paint(ws, f"K{INC1}:K{INCN}", f=FILL_WHITE, border=_C.CELL_BOX)
        ws[f"K{INC1}"] = "(automatic)"
        ws[f"K{INC1}"].font = T.font(8, False, SECONDARY, italic=True)
        ws.row_dimensions[37].height = 12
        # expense categories
        section(ws, T, 38, 2, 6, "EXPENSE CATEGORIES  —  monthly budget", color=C_EXP)
        self.head(ws, 39, 2, ["Category", "Fixed / Variable", "Needs / Wants", "Monthly budget", "Yearly budget"])
        for i in range(EXPN - EXP1 + 1):
            r = EXP1 + i
            if i < len(SD.EXPENSE):
                cat, grp, bk, bud = SD.EXPENSE[i]
                ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"] = cat, grp, bk, bud
            self.inp(S, f"B{r}")
            self.inp(S, f"C{r}:D{r}", align=CENTER)
            self.inp(S, f"E{r}", FMT_M, RIGHT)
            ws[f"F{r}"] = f'=IF(B{r}="","",E{r}*12)'
            self.calc(S, f"F{r}", FMT_M, RIGHT)
        add_list_dv(ws, f"C{EXP1}:C{EXPN}", R(S, "U", 12, 13))
        add_list_dv(ws, f"D{EXP1}:D{EXPN}", R(S, "V", 12, 13))
        add_dv(ws, f"E{EXP1}:E{EXPN}", "decimal", "greaterThanOrEqual", "0", error="Enter an amount (0 or more).")
        add_dv(ws, f"C{INC1}:C{INCN}", "decimal", "greaterThanOrEqual", "0", error="Enter an amount (0 or more).")
        r = EXPN + 1
        self.label(ws, f"B{r}:D{r}", "Total monthly budget", 10, True, NAVY)
        ws[f"E{r}"] = f"=SUM(E{EXP1}:E{EXPN})"
        ws[f"F{r}"] = f"=SUM(F{EXP1}:F{EXPN})"
        self.calc(S, f"E{r}:F{r}", FMT_M, RIGHT, NAVY, True)
        # mirrors
        section(ws, T, 38, 8, 11, "ACCOUNTS & SAVINGS GOALS  (edit on their tabs)", color=C_GOAL)
        self.head(ws, 39, 8, ["Account", "Balance", "Savings goal", "Target"])
        for i in range(10):
            r = EXP1 + i
            ws[f"H{r}"] = f'=IF(INDEX({BA("B")},{i + 1})="","",INDEX({BA("B")},{i + 1}))'
            ws[f"I{r}"] = f'=IF(H{r}="","",INDEX({BA("I")},{i + 1}))'
            ws[f"J{r}"] = f'=IF(INDEX({SF("B")},{i + 1})="","",INDEX({SF("B")},{i + 1}))'
            ws[f"K{r}"] = f'=IF(J{r}="","",INDEX({SF("C")},{i + 1}))'
            self.calc(S, f"H{r}:K{r}")
            ws[f"I{r}"].number_format = ws[f"K{r}"].number_format = FMT_M
        ws[f"H{EXP1 + 11}"] = f'=HYPERLINK("#{q(S_BA)}!A1","Edit accounts ›")'
        ws[f"J{EXP1 + 11}"] = f'=HYPERLINK("#{q(S_SF)}!A1","Edit savings goals ›")'
        ws[f"H{EXP1 + 12}"] = f'=HYPERLINK("#{q(S_DC)}!A1","Edit debts ›")'
        for a in (f"H{EXP1 + 11}", f"J{EXP1 + 11}", f"H{EXP1 + 12}"):
            ws[a].font = T.font(10, True, BLUE)

        # system lists
        section(ws, T, 10, 14, 25, "SYSTEM LISTS  —  used by formulas; edit with care", color=LAVENDER)
        cur = [("USD", "$"), ("EUR", "€"), ("GBP", "£"), ("CAD", "C$"), ("AUD", "A$"), ("JPY", "¥"), ("CHF", "CHF"), ("INR", "₹"),
               ("MXN", "MX$"), ("BRL", "R$"), ("ZAR", "R"), ("SEK", "kr")]
        system = {"N": ("Months", MONTHS), "O": ("Years", list(range(2024, 2036))), "P": ("Currency", [a for a, _ in cur]),
                  "Q": ("Symbol", [b for _, b in cur]), "R": ("Yes / No", ["Yes", "No"]),
                  "S": ("Frequency", ["Weekly", "Biweekly", "Monthly", "Quarterly", "Annually"]),
                  "T": ("Payment status", ["Unpaid", "Scheduled", "Paid"]), "U": ("Group", ["Fixed", "Variable"]),
                  "V": ("Bucket", ["Needs", "Wants"]), "W": ("Recurring", ["Active", "Paused"]),
                  "X": ("No-spend day", ["✓ No spend", "✗ Spent", "★ Exception"]),
                  "Y": ("Asset types", ["Cash", "Bank accounts", "Investments", "Property", "Other assets"]),
                  "Z": ("Liability types", ["Credit cards", "Loans", "Other liabilities"])}
        system["Y"] = system["Y"]
        for c, (h, items) in system.items():
            if c == "Z":
                continue
            self.head(ws, 11, ord(c) - 64, [h], fill_="EFEAFB", color="4B3A8C", height=22)
            for i in range(12):
                ws[f"{c}{12 + i}"] = items[i] if i < len(items) else None
            paint(ws, f"{c}12:{c}23", f=FILL_OPT, font=T.font(10), border=_C.CELL_BOX, align=CENTER)
        # liability types under the asset types (column Y rows 18-20)
        self.label(ws, "Y18", "Liability types", 9, True, "4B3A8C", CENTER)
        ws["Y18"].fill = fill("EFEAFB")
        for i, t in enumerate(["Credit cards", "Loans", "Other liabilities"]):
            ws[f"Y{19 + i}"] = t
        for r in range(12, 24):
            ws.row_dimensions[r].height = ws.row_dimensions[r].height or 19

        self.build_master()
        ws.freeze_panes = "A4"
        skin(ws, 25, EXPN + 2, cards=[(2, 10, 6, 21), (8, 10, 11, 18), (2, 23, 6, INCN), (8, 23, 11, INCN),
                                       (2, 38, 6, EXPN + 1), (8, 38, 11, EXP1 + 12), (14, 10, 25, 23)], hide_headers=True)
        names = {TODAY: "$C$18", YEAR: "$C$12", AUTO: "$C$19", DUE: "$C$20", SYM: "$C$15", START: "$Z$2", P0: "$Z$3"}
        for n, a in names.items():
            self.wb.defined_names[n] = DefinedName(n, attr_text=f"{q(S_SET)}!{a}")

    def build_master(self):
        """Hidden category engine on Setup (AA..BD): raw stacked list -> compact lists used by dropdowns and tabs."""
        ws = self.ws[S_SET]
        heads = {"AA": "cat", "AB": "type", "AC": "bucket", "AD": "group", "AE": "plan / month", "AF": "#", "AG": "ALL (dropdown)",
                 "AH": "type", "AI": "bucket", "AJ": "group", "AK": "plan", "AL": "src row"}
        for c, h in heads.items():
            ws[f"{c}4"] = h
        blocks = [("Income", INC1, 12), ("Expense", EXP1, 30), ("Savings", SF1, 10), ("Debt Payment", DC1, 10), ("Transfer", 0, 1)]
        r = M1
        for typ, src1, n in blocks:
            for k in range(n):
                s = src1 + k
                if typ == "Income":
                    cat, bucket, group, plan = f"$B${s}", '"Income"', '"Income"', f"$C${s}"
                elif typ == "Expense":
                    cat, bucket, group, plan = f"$B${s}", f"$D${s}", f"$C${s}", f"$E${s}"
                elif typ == "Savings":
                    cat, bucket, group, plan = f"{q(S_SF)}!$B${s}", '"Savings & Debt"', '"Savings"', f"{q(S_SF)}!$E${s}"
                elif typ == "Transfer":
                    cat, bucket, group, plan = '"Transfer"', '"Transfer"', '"Transfer"', "0"
                else:
                    cat, bucket, group, plan = (f"{q(S_DC)}!$B${s}", '"Savings & Debt"', '"Debt"',
                                                f"{q(S_DC)}!$G${s}+{q(S_DC)}!$H${s}")
                ws[f"AA{r}"] = f'=IF({cat}="","",{cat}&"")'
                ws[f"AB{r}"] = typ
                ws[f"AC{r}"] = f"={bucket}"
                ws[f"AD{r}"] = f"={group}"
                ws[f"AE{r}"] = f'=IF(AA{r}="",0,N({plan}))' if typ not in ("Debt Payment", "Transfer") else "=0" if typ == "Transfer" else f'=IF(AA{r}="",0,N({q(S_DC)}!$G${s})+N({q(S_DC)}!$H${s}))'
                r += 1
        for r in range(M1, MN + 1):
            ws[f"AF{r}"] = f'=IF(AA{r}="","",COUNTIF(AA${M1}:AA{r},"?*"))'
            ws[f"AL{r}"] = f'=IFERROR(MATCH(ROW()-{M1 - 1},$AF${M1}:$AF${MN},0),"")'
            ws[f"AG{r}"] = f'=IF(AL{r}="","",INDEX($AA${M1}:$AA${MN},AL{r}))'
            for c, src in (("AH", "AB"), ("AI", "AC"), ("AJ", "AD"), ("AK", "AE")):
                ws[f"{c}{r}"] = f'=IF(AL{r}="","",INDEX(${src}${M1}:${src}${MN},AL{r}))'
        conds = {"fixed": '$AB{r}="Expense",$AD{r}="Fixed"', "variable": '$AB{r}="Expense",$AD{r}="Variable"',
                 "income": '$AB{r}="Income"', "funds": '$AB{r}="Savings"', "debts": '$AB{r}="Debt Payment"',
                 "expense": '$AB{r}="Expense"', "needs": '$AB{r}="Expense",$AC{r}="Needs"', "wants": '$AB{r}="Expense",$AC{r}="Wants"'}
        crit = {"fixed": '$AB${a}:$AB{r},"Expense",$AD${a}:$AD{r},"Fixed"', "variable": '$AB${a}:$AB{r},"Expense",$AD${a}:$AD{r},"Variable"',
                "income": '$AB${a}:$AB{r},"Income"', "funds": '$AB${a}:$AB{r},"Savings"', "debts": '$AB${a}:$AB{r},"Debt Payment"',
                "expense": '$AB${a}:$AB{r},"Expense"', "needs": '$AB${a}:$AB{r},"Expense",$AC${a}:$AC{r},"Needs"',
                "wants": '$AB${a}:$AB{r},"Expense",$AC${a}:$AC{r},"Wants"'}
        for name, (rn, cc) in cat_lists().items():
            if name == "all":
                continue
            ws[f"{rn}4"], ws[f"{cc}4"] = "#", name
            for r in range(M1, MN + 1):
                ws[f"{rn}{r}"] = (f'=IF(AND($AA{r}<>"",{conds[name].format(r=r)}),'
                                  f'COUNTIFS($AA${M1}:$AA{r},"?*",{crit[name].format(a=M1, r=r)}),"")')
                ws[f"{cc}{r}"] = f'=IFERROR(INDEX($AA${M1}:$AA${MN},MATCH(ROW()-{M1 - 1},${rn}${M1}:${rn}${MN},0)),"")'
        # period month labels for selectors (BD): "Full year" + 12 labels
        ws[f"BD{M1 - 1}"] = "period list"
        ws[f"BD{M1}"] = "Full year"
        for k in range(12):
            ws[f"BD{M1 + 1 + k}"] = f'=TEXT(EDATE($Z$3,{k}),"mmmm yyyy")'
        for c in range(27, 57):
            ws.column_dimensions[L(c)].hidden = True
        ws.column_dimensions["Z"].hidden = True

    # ================================================================ 2 BANK ACCOUNTS
    def build_ba(self):
        ws, T, S = self.ws[S_BA], self.T, S_BA
        widths = [26, 14, 24, 15, 15, 15, 15, 16, 11]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        self.title(ws, "BANK ACCOUNTS", "Opening balances in, everything else calculated from your transactions, recurring items and paid bills.", 10)
        self.tiles(ws, 5, [("TOTAL BALANCE", f"=SUM(I{BA1}:I{BAN})", FMT_M, NAVY),
                           ("CASH & BANK", f'=SUMIFS(I{BA1}:I{BAN},C{BA1}:C{BAN},"<>Credit card")', FMT_M, C_INC),
                           ("CREDIT CARDS", f'=SUMIFS(I{BA1}:I{BAN},C{BA1}:C{BAN},"Credit card")', FMT_M, C_EXP),
                           ("ACCOUNTS", f'=COUNTIF(B{BA1}:B{BAN},"?*")', "0", C_SAV)], c1=2, width=2)
        ws.row_dimensions[7].height = 10
        self.head(ws, 8, 2, ["Account name", "Type", "Institution", "Opening balance", "Money in", "Money out",
                             "Transfers in", "Current balance", "Share"])
        for i in range(BAN - BA1 + 1):
            r = BA1 + i
            if self.demo and i < len(SD.ACCOUNTS):
                for c, v in zip("BCDE", SD.ACCOUNTS[i]):
                    ws[f"{c}{r}"] = v
            self.inp(S, f"B{r}:D{r}")
            self.inp(S, f"E{r}", FMT_M, RIGHT)
            b = f"$B{r}"
            ws[f"F{r}"] = (f'=IF({b}="","",SUMIFS({TR("I")},{TR("G")},{b},{TR("F")},"Income")'
                           f'+SUMIFS({RT("L")},{RT("G")},{b},{RT("C")},"Income"))')
            ws[f"G{r}"] = (f'=IF({b}="","",SUMIFS({TR("I")},{TR("G")},{b},{TR("F")},"<>Income")'
                           f'+SUMIFS({RT("L")},{RT("G")},{b},{RT("C")},"<>Income")'
                           f'+SUMIFS({PY("C")},{PY("H")},{b},{PY("E")},"Paid"))')
            ws[f"H{r}"] = (f'=IF({b}="","",SUMIFS({TR("I")},{TR("P")},{b})+SUMIFS({RT("L")},{RT("O")},{b})'
                           f'+SUMIFS({PY("C")},{PY("M")},{b},{PY("E")},"Paid"))')
            ws[f"I{r}"] = f'=IF({b}="","",E{r}+F{r}-G{r}+H{r})'
            ws[f"J{r}"] = f'=IF(OR({b}="",I{r}<=0),"",I{r}/SUMIF($I${BA1}:$I${BAN},">0"))'
            self.calc(S, f"F{r}:H{r}", FMT_M, RIGHT)
            self.calc(S, f"I{r}", FMT_M, RIGHT, NAVY, True)
            self.calc(S, f"J{r}", FMT_PCT, CENTER)
            ws.row_dimensions[r].height = 20
        add_list_dv(ws, f"C{BA1}:C{BAN}", R(S_SET, "I", INC1, INCN))
        add_dv(ws, f"E{BA1}:E{BAN}", "decimal", "between", "-100000000", "100000000")
        r = BAN + 1
        self.label(ws, f"B{r}:D{r}", "Total", 10, True, NAVY)
        for c in "EFGHI":
            ws[f"{c}{r}"] = f"=SUM({c}{BA1}:{c}{BAN})"
        self.calc(S, f"E{r}:I{r}", FMT_M, RIGHT, NAVY, True)
        cf_formula(ws, f"I{BA1}:I{BAN}", f'AND(ISNUMBER(I{BA1}),I{BA1}<0)', EXP_BG, C_EXP, True)
        cf_databar(ws, f"J{BA1}:J{BAN}", TEAL)
        self.note(ws, f"B{r + 1}:J{r + 1}", "Money in = income booked to the account. Money out = expenses, savings transfers and "
                  "debt payments paid from it (incl. paid bills). Transfers in = transfers from your other accounts plus Sinking Fund savings held in this account. "
                  "Credit cards show a negative balance as you spend.")
        ws.row_dimensions[r + 1].height = 30
        section(ws, T, r + 3, 2, 10, "BALANCE BY ACCOUNT")
        for rr in range(r + 4, r + 18):
            ws.row_dimensions[rr].height = 18
        ch = BarChart()
        ch.type = "bar"
        ch.add_data(Reference(ws, min_col=9, min_row=BA1, max_row=BAN), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=BA1, max_row=BAN))
        self.chart_style(ch, "Current balance", [C_SAV], legend=False)
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = False
        ch.y_axis.delete = False
        place_chart(ws, ch, 2, r + 4, 10, r + 17)
        self.table(ws, "Accounts", f"B8:J{BAN}")
        ws.freeze_panes = "A9"
        skin(ws, 10, r + 18, cards=[(2, 8, 10, r + 1), (2, r + 3, 10, r + 17)], hide_headers=True)

    # ================================================================ 3 RECURRING
    def build_rt(self):
        ws, T, S = self.ws[S_RT], self.T, S_RT
        widths = [26, 13, 12, 12, 21, 23, 12, 12, 10, 13, 13, 13]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        self.title(ws, "RECURRING TRANSACTIONS", "Salary, bills, subscriptions, savings transfers and loan payments that repeat. "
                   "Each occurrence up to today posts to your budget automatically.", 13)
        T_ = TODAY
        self.tiles(ws, 5, [("ACTIVE ITEMS", f'=COUNTIFS(B{RT1}:B{RTN},"?*",J{RT1}:J{RTN},"<>Paused")', "0", NAVY),
                           ("MONTHLY INCOME", f'=SUMIFS(M{RT1}:M{RTN},C{RT1}:C{RTN},"Income",J{RT1}:J{RTN},"<>Paused")', FMT_M, C_INC),
                           ("MONTHLY BILLS & DEBT", f'=SUMIFS(M{RT1}:M{RTN},C{RT1}:C{RTN},"Expense",J{RT1}:J{RTN},"<>Paused")'
                                                    f'+SUMIFS(M{RT1}:M{RTN},C{RT1}:C{RTN},"Debt Payment",J{RT1}:J{RTN},"<>Paused")', FMT_M, C_EXP),
                           ("MONTHLY SAVINGS", f'=SUMIFS(M{RT1}:M{RTN},C{RT1}:C{RTN},"Savings",J{RT1}:J{RTN},"<>Paused")', FMT_M, C_SAV)],
                   c1=2, width=3)
        ws["B7"] = f'=IF({AUTO}="Yes","Posting is ON: occurrences up to "&TEXT({T_},"mmm d, yyyy")&" count in your budget.","Posting is OFF (Easy Setup): recurring items are shown here but not counted.")'
        ws["B7"].font = T.font(9, True, C_INC)
        ws.row_dimensions[7].height = 18
        self.head(ws, 8, 2, ["Name", "Type", "Amount", "Frequency", "Category", "Account", "Start date", "End date", "Status",
                             "Next payment", "Posted to date", "Per month"])
        # helper header rows 6/7 (window of each budget month)
        for k in range(12):
            cc = L(RT_CNT + k)
            ws[f"{cc}5"] = f"m{k + 1}"
            ws[f"{cc}6"] = f"=EDATE({P0},{k})"
            ws[f"{cc}7"] = f"=MIN(EOMONTH({cc}6,0),{T_})"
            ws[f"{cc}6"].number_format = ws[f"{cc}7"].number_format = FMT_SDATE
            ws[f"{L(RT_AMT + k)}5"] = f"amt m{k + 1}"
        for c, h in (("N", "bucket"), ("O", "to account"), ("P", "days"), ("Q", "months"), ("AP", "steps"), ("AQ", "cand"), ("AR", "next")):
            ws[f"{c}5"] = h
        for i in range(RTN - RT1 + 1):
            r = RT1 + i
            if self.demo and i < len(SD.RECURRING):
                nm, amt, fr, cat, acc, st, en, status = SD.RECURRING[i]
                ws[f"B{r}"], ws[f"D{r}"], ws[f"E{r}"], ws[f"F{r}"], ws[f"G{r}"] = nm, amt, fr, cat, acc
                ws[f"H{r}"], ws[f"I{r}"], ws[f"J{r}"] = st, en, status
            self.inp(S, f"B{r}")
            self.inp(S, f"D{r}", FMT_M, RIGHT)
            self.inp(S, f"E{r}:G{r}", align=CENTER)
            self.inp(S, f"H{r}:I{r}", FMT_SDATE, CENTER)
            self.inp(S, f"J{r}", align=CENTER)
            ws[f"C{r}"] = f'=IF(F{r}="","",IFERROR(INDEX({ST("AB")},MATCH(F{r},{ST("AA")},0)),"Unknown"))'
            ws[f"N{r}"] = f'=IF(F{r}="","",IFERROR(INDEX({ST("AC")},MATCH(F{r},{ST("AA")},0)),""))'
            ws[f"O{r}"] = f'=IF(C{r}="Savings",IFERROR(INDEX({SF("G")},MATCH(F{r},{SF("B")},0))&"",""),"")'
            ws[f"P{r}"] = f'=IF(E{r}="Weekly",7,IF(E{r}="Biweekly",14,0))'
            ws[f"Q{r}"] = f'=IF(E{r}="Monthly",1,IF(E{r}="Quarterly",3,IF(E{r}="Annually",12,0)))'
            ok = f'OR($B{r}="",$D{r}="",$H{r}="",$J{r}="Paused",{AUTO}<>"Yes")'
            for k in range(12):
                cc = L(RT_CNT + k)
                a, b = f"{cc}$6", f"{cc}$7"
                A = f"MAX({a},$H{r})"
                Bd = f'MIN({b},IF($I{r}="",{b},$I{r}))'
                mdiff = f"((YEAR({a})-YEAR($H{r}))*12+MONTH({a})-MONTH($H{r}))"
                d = f"DATE(YEAR({a}),MONTH({a}),MIN(DAY($H{r}),DAY(EOMONTH({a},0))))"
                ws[f"{cc}{r}"] = (f'=IF({ok},0,IF({Bd}<{A},0,IF($P{r}>0,MAX(0,INT(({Bd}-$H{r})/$P{r})+INT(-({A}-$H{r})/$P{r})+1),'
                                  f'IF($Q{r}>0,({mdiff}>=0)*(MOD({mdiff},$Q{r})=0)*({d}>={A})*({d}<={Bd}),0))))')
                ws[f"{L(RT_AMT + k)}{r}"] = f"={cc}{r}*N($D{r})"
            ws[f"AP{r}"] = f'=IF($Q{r}>0,MAX(0,-INT(-((YEAR({T_})-YEAR($H{r}))*12+MONTH({T_})-MONTH($H{r}))/$Q{r})),0)'
            ws[f"AQ{r}"] = f'=IF(OR($H{r}="",$Q{r}=0),"",EDATE($H{r},$Q{r}*AP{r}))'
            ws[f"AR{r}"] = (f'=IF($H{r}="","",IF($P{r}>0,$H{r}+$P{r}*MAX(0,-INT(-({T_}-$H{r})/$P{r})),'
                            f'IF($Q{r}>0,IF(AQ{r}<{T_},EDATE($H{r},$Q{r}*(AP{r}+1)),AQ{r}),"")))')
            ws[f"K{r}"] = f'=IF(OR($B{r}="",$H{r}=""),"",IF($J{r}="Paused","Paused",IF(AND($I{r}<>"",AR{r}>$I{r}),"Ended",AR{r})))'
            ws[f"L{r}"] = f'=IF($B{r}="","",SUM({L(RT_AMT)}{r}:{L(RT_AMT + 11)}{r}))'
            ws[f"M{r}"] = f'=IF(OR($B{r}="",$D{r}=""),"",$D{r}*IF($P{r}>0,365.25/12/$P{r},IF($Q{r}>0,1/$Q{r},0)))'
            self.calc(S, f"C{r}", align=CENTER)
            self.calc(S, f"K{r}", FMT_SDATE, CENTER)
            self.calc(S, f"L{r}:M{r}", FMT_M, RIGHT)
            ws.row_dimensions[r].height = 19
        add_list_dv(ws, f"E{RT1}:E{RTN}", R(S_SET, "S", 12, 16))
        add_list_dv(ws, f"F{RT1}:F{RTN}", ST("AG"))
        add_list_dv(ws, f"G{RT1}:G{RTN}", BA("B"))
        add_list_dv(ws, f"J{RT1}:J{RTN}", R(S_SET, "W", 12, 13))
        add_dv(ws, f"D{RT1}:D{RTN}", "decimal", "greaterThanOrEqual", "0", error="Enter a positive amount.")
        add_dv(ws, f"H{RT1}:I{RTN}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date.")
        for typ, col in (("Income", C_INC), ("Expense", C_EXP), ("Savings", C_SAV), ("Debt Payment", C_DEBT)):
            cf_formula(ws, f"C{RT1}:C{RTN}", f'C{RT1}="{typ}"', font_color=col, bold=True)
        cf_formula(ws, f"C{RT1}:C{RTN}", f'C{RT1}="Unknown"', EXP_BG, C_EXP, True)
        cf_formula(ws, f"K{RT1}:K{RTN}", f'AND(ISNUMBER(K{RT1}),K{RT1}-$AT$2<=7)', WARNING_BG, WARNING, True)
        ws["AT1"], ws["AT2"] = "today", f"={T_}"
        for c in range(14, 47):
            ws.column_dimensions[L(c)].hidden = True
        self.table(ws, "Recurring", f"B8:M{RTN}")
        ws.freeze_panes = "C9"
        skin(ws, 13, RTN + 1, cards=[(2, 8, 13, RTN)], hide_headers=True)

    # ================================================================ 4 PAYMENTS
    def build_pay(self):
        ws, T, S = self.ws[S_PAY], self.T, S_PAY
        widths = [26, 12, 12, 12, 15, 21, 23, 13, 16]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        self.title(ws, "PAYMENTS", "One-off bills with due dates. Mark them Paid and they count in that month's budget.", 10)
        t = TODAY
        self.tiles(ws, 5, [("UNPAID TOTAL", f'=SUMIFS(C{PY1}:C{PYN},E{PY1}:E{PYN},"<>Paid",B{PY1}:B{PYN},"?*")', FMT_M, C_EXP),
                           ("DUE SOON", f'=SUMIFS(C{PY1}:C{PYN},E{PY1}:E{PYN},"<>Paid",D{PY1}:D{PYN},">="&{t},D{PY1}:D{PYN},"<="&({t}+{DUE}))', FMT_M, WARNING),
                           ("OVERDUE", f'=COUNTIFS(E{PY1}:E{PYN},"<>Paid",D{PY1}:D{PYN},"<"&{t},B{PY1}:B{PYN},"?*")', "0", C_EXP),
                           ("PAID THIS PERIOD", f'=SUMIFS(C{PY1}:C{PYN},E{PY1}:E{PYN},"Paid",K{PY1}:K{PYN},">0")', FMT_M, C_INC)],
                   c1=2, width=2)
        ws.row_dimensions[7].height = 10
        self.head(ws, 8, 2, ["Payment name", "Amount", "Due date", "Status", "Payment method", "Category", "Account", "Type", "Due"])
        for c, h in (("K", "period month"), ("L", "bucket"), ("M", "to account"), ("N", "day key"), ("O", "unpaid sort")):
            ws[f"{c}7"] = h
        for i in range(PYN - PY1 + 1):
            r = PY1 + i
            if self.demo and i < len(SD.PAYMENTS):
                nm, amt, due, st, meth, cat, acc = SD.PAYMENTS[i]
                for c, v in zip("BCDEFGH", (nm, amt, due, st, meth, cat, acc)):
                    ws[f"{c}{r}"] = v
            self.inp(S, f"B{r}")
            self.inp(S, f"C{r}", FMT_M, RIGHT)
            self.inp(S, f"D{r}", FMT_SDATE, CENTER)
            self.inp(S, f"E{r}:F{r}", align=CENTER)
            self.inp(S, f"G{r}:H{r}")
            ws[f"I{r}"] = f'=IF(G{r}="","",IFERROR(INDEX({ST("AB")},MATCH(G{r},{ST("AA")},0)),"Unknown"))'
            ws[f"J{r}"] = (f'=IF(B{r}="","",IF(E{r}="Paid","✓ Paid",IF(D{r}="","No date",IF(D{r}<{t},"Overdue "&({t}-D{r})&"d",'
                           f'IF(D{r}={t},"Due today",IF(D{r}-{t}<={DUE},"Due in "&(D{r}-{t})&"d","Due "&TEXT(D{r},"mmm d")))))))')
            ws[f"K{r}"] = f'=IF(OR(D{r}="",C{r}=""),"",IF(AND(D{r}>={P0},D{r}<EDATE({P0},12)),(YEAR(D{r})-YEAR({P0}))*12+MONTH(D{r})-MONTH({P0})+1,""))'
            ws[f"L{r}"] = f'=IF(G{r}="","",IFERROR(INDEX({ST("AC")},MATCH(G{r},{ST("AA")},0)),""))'
            ws[f"M{r}"] = f'=IF(I{r}="Savings",IFERROR(INDEX({SF("G")},MATCH(G{r},{SF("B")},0))&"",""),"")'
            ws[f"N{r}"] = f'=IF(OR(B{r}="",D{r}=""),"",INT(D{r})&"|"&COUNTIF($D${PY1}:D{r},D{r}))'
            ws[f"O{r}"] = f'=IF(AND(B{r}<>"",D{r}<>"",E{r}<>"Paid"),D{r}+ROW()/100000,"")'
            self.calc(S, f"I{r}:J{r}", align=CENTER)
            ws.row_dimensions[r].height = 19
        add_list_dv(ws, f"E{PY1}:E{PYN}", R(S_SET, "T", 12, 14))
        add_list_dv(ws, f"F{PY1}:F{PYN}", R(S_SET, "H", INC1, INCN))
        add_list_dv(ws, f"G{PY1}:G{PYN}", ST("AG"))
        add_list_dv(ws, f"H{PY1}:H{PYN}", BA("B"))
        add_dv(ws, f"C{PY1}:C{PYN}", "decimal", "greaterThanOrEqual", "0", error="Enter a positive amount.")
        add_dv(ws, f"D{PY1}:D{PYN}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date.")
        cf_formula(ws, f"J{PY1}:J{PYN}", f'LEFT(J{PY1},7)="Overdue"', EXP_BG, C_EXP, True)
        cf_formula(ws, f"J{PY1}:J{PYN}", f'OR(J{PY1}="Due today",LEFT(J{PY1},6)="Due in")', WARNING_BG, WARNING, True)
        cf_formula(ws, f"J{PY1}:J{PYN}", f'J{PY1}="✓ Paid"', INC_BG, C_INC, True)
        cf_formula(ws, f"B{PY1}:H{PYN}", f'$E{PY1}="Paid"', font_color="8A9B99")
        for c in "KLMNO":
            ws.column_dimensions[c].hidden = True
        self.table(ws, "Payments", f"B8:J{PYN}")
        ws.freeze_panes = "C9"
        skin(ws, 10, PYN + 1, cards=[(2, 8, 10, PYN)], hide_headers=True)

    # ================================================================ 5 VARIABLE TRANSACTIONS
    def build_tr(self):
        ws, T, S = self.ws[S_TR], self.T, S_TR
        widths = [9, 12, 30, 21, 13, 23, 15, 13, 24, 23]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        self.title(ws, "VARIABLE TRANSACTIONS", "Log every income and expense as it happens. Type comes from the category. To move money between accounts, use the category 'Transfer' and pick 'Transfer to'.", 11)
        self.tiles(ws, 5, [("TRANSACTIONS", f'=COUNT(C{TR1}:C{TRN})', "0", NAVY),
                           ("INCOME LOGGED", f'=SUMIFS(I{TR1}:I{TRN},F{TR1}:F{TRN},"Income")', FMT_M, C_INC),
                           ("SPENDING LOGGED", f'=SUMIFS(I{TR1}:I{TRN},F{TR1}:F{TRN},"Expense")', FMT_M, C_EXP),
                           ("SAVINGS & DEBT", f'=SUMIFS(I{TR1}:I{TRN},F{TR1}:F{TRN},"Savings")+SUMIFS(I{TR1}:I{TRN},F{TR1}:F{TRN},"Debt Payment")', FMT_M, C_SAV)],
                   c1=2, width=2)
        ws.row_dimensions[7].height = 10
        self.head(ws, 8, 2, ["ID", "Date", "Description", "Category", "Type", "Account", "Payment method", "Amount", "Notes", "Transfer to"])
        for c, h in (("L", "bucket"), ("M", "group"), ("N", "period month"), ("O", "month key"), ("P", "to account")):
            ws[f"{c}7"] = h
        data = SD.transactions() if self.demo else []
        for i in range(TRN - TR1 + 1):
            r = TR1 + i
            if i < len(data):
                d, desc, cat, acc, meth, amt, note_ = data[i][:7]
                ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"], ws[f"G{r}"], ws[f"H{r}"], ws[f"I{r}"], ws[f"J{r}"] = d, desc, cat, acc, meth, amt, note_
                if len(data[i]) > 7:
                    ws[f"K{r}"] = data[i][7]
            ws[f"B{r}"] = f'=IF(AND(C{r}="",I{r}=""),"","T"&TEXT(ROW()-{TR1 - 1},"0000"))'
            ws[f"F{r}"] = f'=IF(E{r}="","",IFERROR(INDEX({ST("AB")},MATCH(E{r},{ST("AA")},0)),"Unknown"))'
            ws[f"L{r}"] = f'=IF(E{r}="","",IFERROR(INDEX({ST("AC")},MATCH(E{r},{ST("AA")},0)),""))'
            ws[f"M{r}"] = f'=IF(E{r}="","",IFERROR(INDEX({ST("AD")},MATCH(E{r},{ST("AA")},0)),""))'
            ws[f"N{r}"] = f'=IF(OR(C{r}="",I{r}=""),"",IF(AND(C{r}>={P0},C{r}<EDATE({P0},12)),(YEAR(C{r})-YEAR({P0}))*12+MONTH(C{r})-MONTH({P0})+1,""))'
            ws[f"O{r}"] = f'=IF(N{r}="","",N{r}&"|"&COUNTIF($N${TR1}:N{r},N{r}))'
            ws[f"P{r}"] = f'=IF(F{r}="Savings",IFERROR(INDEX({SF("G")},MATCH(E{r},{SF("B")},0))&"",""),IF(F{r}="Transfer",K{r}&"",""))'
        style_calc(ws, f"B{TR1}:B{TRN}", T, align=CENTER, color=SECONDARY)
        style_calc(ws, f"F{TR1}:F{TRN}", T, align=CENTER)
        style_input(ws, f"C{TR1}:C{TRN}", T, FMT_SDATE, CENTER)
        style_input(ws, f"D{TR1}:E{TRN}", T)
        style_input(ws, f"G{TR1}:H{TRN}", T)
        style_input(ws, f"I{TR1}:I{TRN}", T, FMT_M, RIGHT)
        style_input(ws, f"J{TR1}:J{TRN}", T)
        paint(ws, f"K{TR1}:K{TRN}", f=FILL_OPT, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
        self.unlocked[S] += [f"C{TR1}:E{TRN}", f"G{TR1}:K{TRN}"]
        add_list_dv(ws, f"K{TR1}:K{TRN}", BA("B"))
        cf_formula(ws, f"F{TR1}:F{TRN}", f'F{TR1}="Transfer"', font_color=SECONDARY, bold=True)
        add_dv(ws, f"C{TR1}:C{TRN}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date.")
        add_list_dv(ws, f"E{TR1}:E{TRN}", ST("AG"))
        add_list_dv(ws, f"G{TR1}:G{TRN}", BA("B"))
        add_list_dv(ws, f"H{TR1}:H{TRN}", R(S_SET, "H", INC1, INCN))
        add_dv(ws, f"I{TR1}:I{TRN}", "decimal", "greaterThanOrEqual", "0", error="Enter a positive amount — the category decides income or expense.")
        for typ, col in (("Income", C_INC), ("Expense", C_EXP), ("Savings", C_SAV), ("Debt Payment", C_DEBT)):
            cf_formula(ws, f"F{TR1}:F{TRN}", f'F{TR1}="{typ}"', font_color=col, bold=True)
        cf_formula(ws, f"F{TR1}:F{TRN}", f'F{TR1}="Unknown"', EXP_BG, C_EXP, True)
        cf_formula(ws, f"I{TR1}:I{TRN}", f'$F{TR1}="Income"', font_color=C_INC, bold=True)
        for c in "LMNOP":
            ws.column_dimensions[c].hidden = True
        self.table(ws, "Transactions", f"B8:K{TRN}")
        ws.freeze_panes = "C9"
        skin(ws, 11, TR1 + 40, hide_headers=True)

    # ================================================================ 7 ANNUAL TOTALS (engine)
    def build_at(self):
        ws, T, S = self.ws[S_AT], self.T, S_AT
        setup_sheet(ws, {"B": 25, "C": 14, "D": 15, "E": 14, **{L(c): 10.5 for c in range(6, 18)}, "R": 12, "S": 11,
                         "T": 12, "U": 12, "V": 10})
        self.title(ws, "ANNUAL TOTALS", "Month by month and category by category for your 12-month budget period. "
                   "Everything here is calculated.", 22)
        t = f"$C${AT1 + 12}"
        self.tiles(ws, 5, [("INCOME", f"=C{AT1 + 12}", FMT_M0, C_INC, C_INC), ("EXPENSES", f"=D{AT1 + 12}", FMT_M0, C_EXP, C_EXP),
                           ("SAVINGS", f"=E{AT1 + 12}", FMT_M0, C_SAV, C_SAV), ("DEBT PAYMENTS", f"=F{AT1 + 12}", FMT_M0, C_DEBT),
                           ("NET CASH FLOW", f"=H{AT1 + 12}", FMT_M0, NAVY), ("SAVINGS RATE", f"=J{AT1 + 12}", FMT_PCT, C_GOAL)],
                   c1=2, width=3, gap=0)
        ws.row_dimensions[7].height = 10
        self.head(ws, 9, 2, ["Month", "Income", "Expenses", "Savings", ("Debt payments", 2), ("Net cash flow", 2), ("Savings rate", 2),
                             ("Budget", 2), ("Remaining", 2), ("Budget used", 2)])
        ws["X8"] = "months elapsed"
        ws["X9"] = f"=MAX(1,MIN(12,(YEAR({TODAY})-YEAR({P0}))*12+MONTH({TODAY})-MONTH({P0})+1))"
        mcol = lambda k: L(6 + k)            # matrix month column for period month k (0-based)
        for k in range(12):
            r = AT1 + k
            ws[f"B{r}"] = f'=TEXT(EDATE({P0},{k}),"mmmm yyyy")'
            col = f"${mcol(k)}${MX1}:${mcol(k)}${MXN}"
            ws[f"C{r}"] = f'=SUMIFS({col},$C${MX1}:$C${MXN},"Income")'
            ws[f"D{r}"] = f'=SUMIFS({col},$C${MX1}:$C${MXN},"Expense")'
            ws[f"E{r}"] = f'=SUMIFS({col},$C${MX1}:$C${MXN},"Savings")'
            self.merge(ws, f"F{r}:G{r}", f'=SUMIFS({col},$C${MX1}:$C${MXN},"Debt Payment")')
            self.merge(ws, f"H{r}:I{r}", f"=C{r}-D{r}-E{r}-F{r}")
            self.merge(ws, f"J{r}:K{r}", f'=IF(C{r}=0,"",E{r}/C{r})')
            choose = ",".join(f"{q(m)}!$D$9" for m in MONTHS)
            self.merge(ws, f"L{r}:M{r}", f"=CHOOSE(MONTH(EDATE({P0},{k})),{choose})")
            self.merge(ws, f"N{r}:O{r}", f"=L{r}-D{r}")
            self.merge(ws, f"P{r}:Q{r}", f'=IF(L{r}=0,"",D{r}/L{r})')
            self.calc(S, f"B{r}", None, LEFT, DARK, True)
            self.calc(S, f"C{r}:Q{r}", FMT_M0, RIGHT)
            ws[f"J{r}"].number_format = FMT_PCT
            ws[f"P{r}"].number_format = FMT_PCT
            ws.row_dimensions[r].height = 19
        r = AT1 + 12
        self.label(ws, f"B{r}", "Total", 10, True, NAVY)
        for c in "CDE":
            ws[f"{c}{r}"] = f"=SUM({c}{AT1}:{c}{AT1 + 11})"
        self.merge(ws, f"F{r}:G{r}", f"=SUM(F{AT1}:F{AT1 + 11})")
        self.merge(ws, f"H{r}:I{r}", f"=SUM(H{AT1}:H{AT1 + 11})")
        self.merge(ws, f"J{r}:K{r}", f'=IF(C{r}=0,"",E{r}/C{r})')
        self.merge(ws, f"L{r}:M{r}", f"=SUM(L{AT1}:L{AT1 + 11})")
        self.merge(ws, f"N{r}:O{r}", f"=L{r}-D{r}")
        self.merge(ws, f"P{r}:Q{r}", f'=IF(L{r}=0,"",D{r}/L{r})')
        self.calc(S, f"C{r}:Q{r}", FMT_M0, RIGHT, NAVY, True)
        ws[f"J{r}"].number_format = ws[f"P{r}"].number_format = FMT_PCT
        r2 = r + 1
        self.label(ws, f"B{r2}", "Monthly average (to date)", 9, True, SECONDARY)
        for c in "CDE":
            ws[f"{c}{r2}"] = f"={c}{r}/$X$9"
        self.merge(ws, f"F{r2}:G{r2}", f"=F{r}/$X$9")
        self.merge(ws, f"H{r2}:I{r2}", f"=H{r}/$X$9")
        self.calc(S, f"C{r2}:I{r2}", FMT_M0, RIGHT, SECONDARY)
        for c, color in (("C", C_INC), ("D", C_EXP), ("E", C_SAV)):
            ws[f"{c}9"].font = T.font(9, True, color)
        cf_formula(ws, f"H{AT1}:I{AT1 + 12}", f"H{AT1}<0", EXP_BG, C_EXP, True)
        cf_formula(ws, f"N{AT1}:O{AT1 + 12}", f"N{AT1}<0", EXP_BG, C_EXP, True)
        cf_databar(ws, f"P{AT1}:P{AT1 + 11}", C_EXP)
        # charts
        cr = r2 + 2
        section(ws, T, cr, 2, 22, "TRENDS")
        for rr in range(cr + 1, cr + 16):
            ws.row_dimensions[rr].height = 18
        ch = BarChart()
        ch.type = "col"
        ch.add_data(Reference(ws, min_col=3, max_col=4, min_row=9, max_row=AT1 + 11), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=AT1, max_row=AT1 + 11))
        self.chart_style(ch, "Income vs expenses", [C_INC, C_EXP])
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = ch.y_axis.delete = False
        place_chart(ws, ch, 2, cr + 1, 10, cr + 15)
        ln = LineChart()
        ln.add_data(Reference(ws, min_col=8, min_row=9, max_row=AT1 + 11), titles_from_data=True)
        ln.add_data(Reference(ws, min_col=5, min_row=9, max_row=AT1 + 11), titles_from_data=True)
        ln.set_categories(Reference(ws, min_col=2, min_row=AT1, max_row=AT1 + 11))
        self.chart_style(ln, "Net cash flow and savings", [NAVY, C_SAV])
        for sr_ in ln.series:
            sr_.smooth = False
        ln.x_axis.delete = ln.y_axis.delete = False
        place_chart(ws, ln, 11, cr + 1, 22, cr + 15)
        # category matrix
        assert cr + 17 <= MX1 - 2, (cr, MX1)
        section(ws, T, MX1 - 2, 2, 22, "BY CATEGORY  —  annual comparison (actual vs budget)")
        self.head(ws, MX1 - 1, 2, ["Category", "Type", "Bucket", "Group"] + [f'=TEXT(EDATE({P0},{k}),"mmm")' for k in range(12)]
                  + ["Total", "Avg / month", "Annual budget", "Difference", "Used"])
        for i in range(MXN - MX1 + 1):
            r = MX1 + i
            s = M1 + i
            ws[f"B{r}"] = f"={q(S_SET)}!$AG${s}"
            ws[f"C{r}"] = f"={q(S_SET)}!$AH${s}"
            ws[f"D{r}"] = f"={q(S_SET)}!$AI${s}"
            ws[f"E{r}"] = f"={q(S_SET)}!$AJ${s}"
            for k in range(12):
                amt = L(RT_AMT + k)
                ws[f"{mcol(k)}{r}"] = (f'=IF($B{r}="","",SUMIFS({TR("I")},{TR("E")},$B{r},{TR("N")},{k + 1})'
                                       f'+SUMIFS({RT(amt)},{RT("F")},$B{r})'
                                       f'+SUMIFS({PY("C")},{PY("G")},$B{r},{PY("E")},"Paid",{PY("K")},{k + 1}))')
            ws[f"R{r}"] = f'=IF($B{r}="","",SUM(F{r}:Q{r}))'
            ws[f"S{r}"] = f'=IF($B{r}="","",R{r}/$X$9)'
            ws[f"T{r}"] = f'=IF($B{r}="","",{q(S_SET)}!$AK${s}*12)'
            ws[f"U{r}"] = f'=IF($B{r}="","",IF(C{r}="Income",R{r}-T{r},T{r}-R{r}))'
            ws[f"V{r}"] = f'=IF(OR($B{r}="",N(T{r})=0),"",R{r}/T{r})'
            ws.row_dimensions[r].height = 18
        self.calc(S, f"B{MX1}:E{MXN}", align=Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True))
        self.calc(S, f"F{MX1}:U{MXN}", FMT_M0, RIGHT)
        self.calc(S, f"V{MX1}:V{MXN}", FMT_PCT, CENTER)
        for typ, col in (("Income", C_INC), ("Expense", C_EXP), ("Savings", C_SAV), ("Debt Payment", C_DEBT)):
            cf_formula(ws, f"C{MX1}:C{MXN}", f'$C{MX1}="{typ}"', font_color=col, bold=True)
        cf_formula(ws, f"U{MX1}:U{MXN}", f'AND(ISNUMBER(U{MX1}),U{MX1}<0)', EXP_BG, C_EXP, True)
        ws.column_dimensions["X"].hidden = True
        ws.freeze_panes = "C4"
        skin(ws, 22, MXN + 1, cards=[(2, 9, 17, AT1 + 13), (2, cr, 22, cr + 15), (2, MX1 - 2, 22, MXN)], hide_headers=True)

    # ================================================================ 10-21 MONTHS
    def build_month(self, c_idx):
        name = MONTHS[c_idx - 1]
        ws, T, S = self.ws[name], self.T, name
        setup_sheet(ws, {L(c): 11.5 for c in range(2, 14)})
        title_bar(ws, T, f"{name.upper()}  ·  Monthly Budget", f'=TEXT($P$3,"mmmm yyyy")&"   ·   month "&$P$2&" of your budget period"',
                  13, home_link=S_DASH, home_label="⌂ Dashboard", demo=False)
        if self.demo:
            ws["B3"] = '="●  DEMO DATA   ·   "&' + ws["B3"].value[1:]
        # hidden helpers
        ws["P2"] = f"=MOD({c_idx}-{START},12)+1"
        ws["P3"] = f"=EDATE({P0},P2-1)"
        ws["P3"].number_format = FMT_DATE
        ws["P4"] = f"={TODAY}"
        ws["O2"], ws["O3"], ws["O4"] = "period month", "month start", "today"
        for c in "NOP":
            ws.column_dimensions[c].hidden = True
        # month strip
        for k, m in enumerate(MONTHS):
            cl = L(2 + k)
            ws[f"{cl}5"] = f'=HYPERLINK("#{q(m)}!A1","{m[:3]}")'
            ws[f"{cl}5"].fill = fill(TEAL if m == name else SOFT_BLUE)
            ws[f"{cl}5"].font = T.font(9, True, WHITE if m == name else MIDNIGHT)
            ws[f"{cl}5"].alignment = CENTER
            ws[f"{cl}5"].border = Border(left=Side(style="thin", color=WHITE), right=Side(style="thin", color=WHITE))
        ws.row_dimensions[5].height = 22
        ws.row_dimensions[6].height = 10
        # matrix lookup for a category cell
        act = lambda cell: f'IF({cell}="","",IFERROR(INDEX({MX_MONTHS},MATCH({cell},{MX("B")},0),$P$2),0))'
        # tiles
        inc, exp_f, exp_v, sav, debt = "$K$27", "$E$30", "$E$54", "$K$41", "$K$55"
        bud = "($D$30+$D$54)"
        self.tiles(ws, 7, [("INCOME", f"={inc}", FMT_M, C_INC, C_INC), ("EXPENSES", f"={exp_f}+{exp_v}", FMT_M, C_EXP, C_EXP),
                           ("SAVINGS", f"={sav}", FMT_M, C_SAV, C_SAV), ("DEBT PAYMENTS", f"={debt}", FMT_M, C_DEBT)], c1=2, width=3)
        ws.row_dimensions[9].height = 6
        self.tiles(ws, 10, [("MONTHLY BUDGET", f"={bud}", FMT_M, NAVY), ("ACTUAL SPENDING", f"={exp_f}+{exp_v}", FMT_M, C_EXP),
                            ("BUDGET REMAINING", f"={bud}-({exp_f}+{exp_v})", FMT_M, C_INC),
                            ("SAVINGS RATE", f'=IF({inc}=0,"—",{sav}/{inc})', FMT_PCT, C_GOAL)], c1=2, width=3)
        cf_formula(ws, "H11", "AND(ISNUMBER(H11),H11<0)", EXP_BG, C_EXP, True)
        ws["D9"] = f"={bud}"           # total budget (read by Annual Totals)
        ws["D9"].font = Font(color=BG, size=1)
        ws.row_dimensions[12].height = 10

        def block(r_sec, c1, title, color, heads, list_name, n, plan_f, cmp_better):
            c2 = c1 + 5
            section(ws, T, r_sec, c1, c2, title, color=color)
            self.head(ws, r_sec + 1, c1, [(heads[0], 2)] + heads[1:])
            cc = [L(c1 + i) for i in range(6)]
            for k in range(n):
                r = r_sec + 2 + k
                cat = f"{cc[0]}{r}"
                self.merge(ws, f"{cc[0]}{r}:{cc[1]}{r}", f'=IFERROR(INDEX({LIST(list_name)},{k + 1})&"","")')
                paint(ws, f"{cc[0]}{r}:{cc[1]}{r}", f=FILL_WHITE, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
                ws[f"{cc[2]}{r}"] = plan_f(cat)
                ws[f"{cc[3]}{r}"] = "=" + act(cat)
                ws[f"{cc[4]}{r}"] = (f'=IF({cat}="","",{cc[2]}{r}-{cc[3]}{r})' if cmp_better == "under"
                                     else f'=IF({cat}="","",{cc[3]}{r}-{cc[2]}{r})')
                ws[f"{cc[5]}{r}"] = f'=IF(OR({cat}="",N({cc[2]}{r})=0),"",{cc[3]}{r}/{cc[2]}{r})'
                if list_name in ("fixed", "variable", "income"):
                    self.inp(S, f"{cc[2]}{r}", FMT_M, RIGHT)
                else:
                    self.calc(S, f"{cc[2]}{r}", FMT_M, RIGHT)
                self.calc(S, f"{cc[3]}{r}:{cc[4]}{r}", FMT_M, RIGHT)
                self.calc(S, f"{cc[5]}{r}", FMT_PCT, CENTER)
                ws.row_dimensions[r].height = 18
            rt = r_sec + 2 + n
            self.label(ws, f"{cc[0]}{rt}:{cc[1]}{rt}", "Total", 10, True, NAVY)
            for k in (2, 3, 4):
                ws[f"{cc[k]}{rt}"] = f"=SUM({cc[k]}{r_sec + 2}:{cc[k]}{rt - 1})"
            ws[f"{cc[5]}{rt}"] = f'=IF({cc[2]}{rt}=0,"",{cc[3]}{rt}/{cc[2]}{rt})'
            self.calc(S, f"{cc[2]}{rt}:{cc[4]}{rt}", FMT_M, RIGHT, NAVY, True)
            self.calc(S, f"{cc[5]}{rt}", FMT_PCT, CENTER, NAVY, True)
            rng_ = f"{cc[4]}{r_sec + 2}:{cc[4]}{rt}"
            cf_formula(ws, rng_, f"AND(ISNUMBER({cc[4]}{r_sec + 2}),{cc[4]}{r_sec + 2}<0)", EXP_BG, C_EXP, True)
            cf_databar(ws, f"{cc[5]}{r_sec + 2}:{cc[5]}{rt - 1}", color)
            return (c1, r_sec, c2, rt)

        exp_plan = lambda cat: f'=IF({cat}="","",IFERROR(INDEX({R(S_SET, "E", EXP1, EXPN)},MATCH({cat},{R(S_SET, "B", EXP1, EXPN)},0)),0))'
        inc_plan = lambda cat: f'=IF({cat}="","",IFERROR(INDEX({R(S_SET, "C", INC1, INCN)},MATCH({cat},{R(S_SET, "B", INC1, INCN)},0)),0))'
        sf_plan = lambda cat: f'=IF({cat}="","",IFERROR(INDEX({SF("E")},MATCH({cat},{SF("B")},0)),0))'
        dc_plan = lambda cat: f'=IF({cat}="","",IFERROR(INDEX({DC("G")},MATCH({cat},{DC("B")},0))+INDEX({DC("H")},MATCH({cat},{DC("B")},0)),0))'
        cards = [(2, 7, 13, 11)]
        cards.append(block(13, 2, "FIXED EXPENSES", C_EXP, ["Category", "Budget", "Actual", "Remaining", "Used"], "fixed", 15, exp_plan, "under"))
        cards.append(block(32, 2, "VARIABLE EXPENSES", C_EXP, ["Category", "Budget", "Actual", "Remaining", "Used"], "variable", 20, exp_plan, "under"))
        cards.append(block(13, 8, "INCOME", C_INC, ["Category", "Expected", "Actual", "Difference", "Received"], "income", 12, inc_plan, "over"))
        cards.append(block(29, 8, "SAVINGS", C_SAV, ["Fund", "Planned", "Actual", "Difference", "Saved"], "funds", 10, sf_plan, "over"))
        cards.append(block(43, 8, "DEBT PAYMENTS", C_DEBT, ["Debt", "Planned", "Actual", "Difference", "Paid"], "debts", 10, dc_plan, "over"))
        ws.row_dimensions[56].height = 10
        # summary
        sr = 58
        section(ws, T, sr, 2, 7, "MONTHLY FINANCIAL SUMMARY", color=NAVY)
        summ = [("Income", f"={inc}", C_INC), ("Fixed expenses", f"={exp_f}", C_EXP), ("Variable expenses", f"={exp_v}", C_EXP),
                ("Total expenses", f"={exp_f}+{exp_v}", C_EXP), ("Savings", f"={sav}", C_SAV), ("Debt payments", f"={debt}", C_DEBT),
                ("Net cash flow", f"={inc}-{exp_f}-{exp_v}-{sav}-{debt}", NAVY), ("Monthly budget", f"={bud}", NAVY),
                ("Budget remaining", f"={bud}-{exp_f}-{exp_v}", C_INC), ("Savings rate", f'=IF({inc}=0,"—",{sav}/{inc})', C_GOAL)]
        for k, (lab, f, color) in enumerate(summ):
            r = sr + 1 + k
            self.label(ws, f"B{r}:D{r}", lab, 10, k in (3, 6, 9), DARK)
            paint(ws, f"B{r}:D{r}", f=FILL_WHITE, border=_C.CELL_BOX)
            self.merge(ws, f"E{r}:G{r}", f)
            self.calc(ws.title, f"E{r}:G{r}", FMT_PCT if lab == "Savings rate" else FMT_M, RIGHT, color, True)
            ws.row_dimensions[r].height = 19
        cf_formula(ws, f"E{sr + 7}:G{sr + 7}", f"AND(ISNUMBER(E{sr + 7}),E{sr + 7}<0)", EXP_BG, C_EXP, True)
        cf_formula(ws, f"E{sr + 9}:G{sr + 9}", f"AND(ISNUMBER(E{sr + 9}),E{sr + 9}<0)", EXP_BG, C_EXP, True)
        cards.append((2, sr, 7, sr + 10))
        section(ws, T, sr, 8, 13, "WHERE THE MONEY WENT")
        for k, (lab, f) in enumerate((("Fixed", f"={exp_f}"), ("Variable", f"={exp_v}"), ("Savings", f"={sav}"), ("Debt", f"={debt}"))):
            ws[f"N{sr + 1 + k}"] = lab
            ws[f"O{sr + 1 + k}"] = f
        dn = DoughnutChart()
        dn.add_data(Reference(ws, min_col=15, min_row=sr + 1, max_row=sr + 4), titles_from_data=False)
        dn.set_categories(Reference(ws, min_col=14, min_row=sr + 1, max_row=sr + 4))
        dn.holeSize = 55
        s = dn.series[0]
        for i, colr in enumerate((C_EXP, "F08A8F", C_SAV, C_DEBT)):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            s.dPt.append(pt)
        self.chart_style(dn, None, h=6, w=9)
        dn.legend.position = "r"
        place_chart(ws, dn, 8, sr + 1, 13, sr + 10)
        cards.append((8, sr, 13, sr + 10))
        # transactions this month
        tr0 = sr + 12
        section(ws, T, tr0, 2, 13, "TRANSACTIONS THIS MONTH  (from Variable Transactions)")
        self.head(ws, tr0 + 1, 2, ["Date", ("Description", 3), ("Category", 2), ("Account", 2), "Type", ("Amount", 2), "Method"])
        key = lambda k: f'$P$2&"|"&{k}'
        for k in range(50):
            r = tr0 + 2 + k
            m = f'MATCH({key(k + 1)},{TR("O")},0)'
            ws[f"B{r}"] = f'=IFERROR(INDEX({TR("C")},{m}),"")'
            self.merge(ws, f"C{r}:E{r}", f'=IFERROR(INDEX({TR("D")},{m})&"","")')
            self.merge(ws, f"F{r}:G{r}", f'=IFERROR(INDEX({TR("E")},{m})&"","")')
            self.merge(ws, f"H{r}:I{r}", f'=IFERROR(INDEX({TR("G")},{m})&"","")')
            ws[f"J{r}"] = f'=IFERROR(INDEX({TR("F")},{m})&"","")'
            self.merge(ws, f"K{r}:L{r}", f'=IFERROR(INDEX({TR("I")},{m}),"")')
            ws[f"M{r}"] = f'=IFERROR(INDEX({TR("H")},{m})&"","")'
            paint(ws, f"B{r}:M{r}", f=FILL_WHITE, font=T.font(9), border=_C.CELL_BOX,
                  align=Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True))
            ws[f"B{r}"].number_format = FMT_SDATE
            ws[f"K{r}"].number_format = FMT_M
            ws[f"K{r}"].alignment = RIGHT
            ws[f"J{r}"].alignment = CENTER
            ws.row_dimensions[r].height = 17
        rl = tr0 + 52
        cnt = f'COUNTIF({TR("N")},$P$2)'
        recs = f"SUM(INDEX({q(S_RT)}!${L(RT_CNT)}${RT1}:${L(RT_CNT + 11)}${RTN},0,$P$2))"
        paid = f'COUNTIFS({PY("K")},$P$2,{PY("E")},"Paid")'
        self.merge(ws, f"B{rl}:M{rl}", f'="Showing "&MIN(50,{cnt})&" of "&{cnt}&" logged transactions.   Also counted this month: "&{recs}&" recurring posts and "&{paid}&" paid bills."')
        ws[f"B{rl}"].font = T.font(9, False, SECONDARY, italic=True)
        typ = f"$J{tr0 + 2}"
        for t_, col in (("Income", C_INC), ("Expense", C_EXP), ("Savings", C_SAV), ("Debt Payment", C_DEBT)):
            cf_formula(ws, f"J{tr0 + 2}:L{tr0 + 51}", f'{typ}="{t_}"', font_color=col, bold=True)
        cards.append((2, tr0, 13, rl))
        ws.freeze_panes = "A6"
        skin(ws, 13, rl + 1, cards=cards, hide_headers=True)

    # ================================================================ 6 DASHBOARD
    def top_helper(self, ws, col, sel, typ="Expense", n=10):
        """Hidden helper (col..col+4, rows MX range): period amount per category with tiebreak, then top-n rows 5.. ."""
        c1, c2, c3, c4, c5 = (L(col + i) for i in range(5))
        ws[f"{c1}4"] = "period amt"
        for i in range(MXN - MX1 + 1):
            r = 5 + i
            m = MX1 + i
            amt = f"IF({sel}=0,N({q(S_AT)}!$R${m}),N(INDEX({q(S_AT)}!$F${m}:$Q${m},{sel})))"
            ws[f"{c1}{r}"] = f'=IF({q(S_AT)}!$C${m}="{typ}",{amt}+ROW()/10000000,-1)'
        last = 5 + MXN - MX1
        ws[f"{c2}4"], ws[f"{c3}4"], ws[f"{c4}4"], ws[f"{c5}4"] = "top name", "top amount", "budget", "rank value"
        for k in range(n):
            r = 5 + k
            ws[f"{c5}{r}"] = f"=LARGE(${c1}$5:${c1}${last},{k + 1})"
            ws[f"{c2}{r}"] = f'=IF({c5}{r}<0.001,"",INDEX({MX("B")},MATCH({c5}{r},${c1}$5:${c1}${last},0)))'
            ws[f"{c3}{r}"] = f'=IF({c2}{r}="",0,ROUND({c5}{r},2))'
            ws[f"{c4}{r}"] = f'=IF({c2}{r}="",0,INDEX({MX("T")},MATCH({c2}{r},{MX("B")},0))/IF({sel}=0,1,12))'
        return c2, c3, c4

    def build_dash(self):
        ws, T, S = self.ws[S_DASH], self.T, S_DASH
        setup_sheet(ws, {L(c): 11 for c in range(2, 14)})
        title_bar(ws, T, "ALL-IN-ONE DASHBOARD", f'=IF({q(S_SET)}!$C$11="","Your money at a glance",{q(S_SET)}!$C$11&"\'s money at a glance")&"   ·   Budget period: "&{q(S_SET)}!$C$21',
                  13, home_link=S_SET, home_label="⚙ Setup", demo=False)
        if self.demo:
            ws["B3"] = '="●  DEMO DATA   ·   "&' + ws["B3"].value[1:]
        ws.row_dimensions[4].height = 10
        self.period_selector(ws, S, "B5:C5", "D5:F5", "P5")
        self.label(ws, "H5:I5", "TODAY", 9, True, SECONDARY, RIGHT)
        self.merge(ws, "J5:K5", f"={TODAY}")
        self.calc(S, "J5:K5", FMT_DATE, CENTER)
        ws.row_dimensions[5].height = 24
        ws["O5"] = "period"
        sel = "$P$5"
        pick = lambda col: f"IF({sel}=0,{q(S_AT)}!${col}${AT1 + 12},INDEX({q(S_AT)}!${col}${AT1}:${col}${AT1 + 11},{sel}))"
        ws.row_dimensions[6].height = 10
        self.tiles(ws, 7, [("TOTAL INCOME", "=" + pick("C"), FMT_M0, C_INC, C_INC),
                           ("TOTAL EXPENSES", "=" + pick("D"), FMT_M0, C_EXP, C_EXP),
                           ("NET CASH FLOW", "=" + pick("H"), FMT_M0, NAVY),
                           ("TOTAL SAVINGS", "=" + pick("E"), FMT_M0, C_SAV, C_SAV)], c1=2, width=3)
        ws.row_dimensions[9].height = 6
        self.tiles(ws, 10, [("SAVINGS RATE", f'=IF({pick("C")}=0,"—",{pick("E")}/{pick("C")})', FMT_PCT, C_GOAL),
                            (f'=IF({sel}=0,"BUDGET (FULL YEAR)","MONTHLY BUDGET")', "=" + pick("L"), FMT_M0, NAVY),
                            ("BUDGET REMAINING", f"={pick('L')}-{pick('D')}", FMT_M0, C_INC),
                            ("TOTAL DEBT", f"=SUM({DC('E')})", FMT_M0, C_EXP, C_EXP)], c1=2, width=3)
        cf_formula(ws, "H11", "AND(ISNUMBER(H11),H11<0)", EXP_BG, C_EXP, True)
        cf_formula(ws, "E8", "AND(ISNUMBER(E8),E8<0)", EXP_BG, C_EXP, True)
        ws.row_dimensions[12].height = 10
        # helpers
        for k, (lab, f) in enumerate((("Fixed", f'SUMIFS(INDEX({MX_MONTHS},0,{sel}),{MX("C")},"Expense",{MX("E")},"Fixed")'),
                                      ("Variable", f'SUMIFS(INDEX({MX_MONTHS},0,{sel}),{MX("C")},"Expense",{MX("E")},"Variable")'),
                                      ("Savings", None), ("Debt payments", None))):
            r = 10 + k
            ws[f"O{r}"] = lab
        ws["P10"] = f'=IF({sel}=0,SUMIFS({MX("R")},{MX("C")},"Expense",{MX("E")},"Fixed"),SUMIFS(INDEX({MX_MONTHS},0,{sel}),{MX("C")},"Expense",{MX("E")},"Fixed"))'
        ws["P11"] = f'=IF({sel}=0,SUMIFS({MX("R")},{MX("C")},"Expense",{MX("E")},"Variable"),SUMIFS(INDEX({MX_MONTHS},0,{sel}),{MX("C")},"Expense",{MX("E")},"Variable"))'
        ws["P12"] = "=" + pick("E")
        ws["P13"] = "=" + pick("F")
        names, amts, buds = self.top_helper(ws, 18, sel)          # R..V
        for c in range(14, 24):
            ws.column_dimensions[L(c)].hidden = True
        cards = [(2, 7, 13, 11)]

        def chart_card(r, c1, c2, title, ch, h=15):
            section(ws, T, r, c1, c2, title)
            for rr in range(r + 1, r + h + 1):
                ws.row_dimensions[rr].height = 18
            place_chart(ws, ch, c1, r + 1, c2, r + h)
            cards.append((c1, r, c2, r + h))

        at = self.ws[S_AT]
        ch = BarChart()
        ch.type = "col"
        ch.add_data(Reference(at, min_col=3, max_col=4, min_row=9, max_row=AT1 + 11), titles_from_data=True)
        ch.set_categories(Reference(at, min_col=2, min_row=AT1, max_row=AT1 + 11))
        self.chart_style(ch, None, [C_INC, C_EXP])
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = ch.y_axis.delete = False
        chart_card(13, 2, 7, "Income vs expenses", ch)
        dn = DoughnutChart()
        dn.add_data(Reference(ws, min_col=16, min_row=10, max_row=13), titles_from_data=False)
        dn.set_categories(Reference(ws, min_col=15, min_row=10, max_row=13))
        dn.holeSize = 55
        for i, colr in enumerate((C_EXP, "F08A8F", C_SAV, C_DEBT)):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            dn.series[0].dPt.append(pt)
        self.chart_style(dn, None)
        dn.legend.position = "r"
        chart_card(13, 8, 13, "Expense distribution  (selected period)", dn)
        ln = BarChart()
        ln.type = "col"
        ln.add_data(Reference(at, min_col=8, min_row=9, max_row=AT1 + 11), titles_from_data=True)
        ln.set_categories(Reference(at, min_col=2, min_row=AT1, max_row=AT1 + 11))
        self.chart_style(ln, None, [NAVY], legend=False)
        ln.y_axis.majorGridlines = None
        ln.x_axis.delete = ln.y_axis.delete = False
        chart_card(30, 2, 7, "Monthly cash flow (net)", ln)
        sf = self.ws[S_SF]
        sp = BarChart()
        sp.type = "bar"
        sp.add_data(Reference(sf, min_col=11, min_row=SF1, max_row=SFN), titles_from_data=False)
        sp.set_categories(Reference(sf, min_col=2, min_row=SF1, max_row=SFN))
        self.chart_style(sp, None, [C_SAV], legend=False)
        sp.y_axis.scaling.min, sp.y_axis.scaling.max = 0, 1
        sp.y_axis.number_format = "0%"
        sp.y_axis.majorGridlines = None
        sp.x_axis.delete = sp.y_axis.delete = False
        chart_card(30, 8, 13, "Savings progress (sinking funds)", sp)
        bv = BarChart()
        bv.type = "bar"
        bv.add_data(Reference(ws, min_col=21, min_row=4, max_row=12), titles_from_data=True)
        bv.add_data(Reference(ws, min_col=20, min_row=4, max_row=12), titles_from_data=True)
        bv.set_categories(Reference(ws, min_col=19, min_row=5, max_row=12))
        self.chart_style(bv, None, [MED_GRAY, C_EXP])
        bv.y_axis.majorGridlines = None
        bv.x_axis.delete = bv.y_axis.delete = False
        bv.x_axis.scaling.orientation = "maxMin"
        chart_card(47, 2, 7, "Budget vs actual  (top 8 categories)", bv)
        cb = BarChart()
        cb.type = "bar"
        cb.add_data(Reference(ws, min_col=20, min_row=5, max_row=14), titles_from_data=False)
        cb.set_categories(Reference(ws, min_col=19, min_row=5, max_row=14))
        self.chart_style(cb, None, [C_EXP], legend=False)
        cb.y_axis.majorGridlines = None
        cb.x_axis.delete = cb.y_axis.delete = False
        cb.x_axis.scaling.orientation = "maxMin"
        chart_card(47, 8, 13, "Category breakdown  (top 10)", cb)
        ws["T4"], ws["U4"] = "Actual", "Budget"
        # lists
        lr = 64
        section(ws, T, lr, 2, 7, "UPCOMING & OVERDUE PAYMENTS")
        self.head(ws, lr + 1, 2, [("Payment", 2), "Due", ("Amount", 1), ("Status", 2)], height=22)
        for k in range(6):
            r = lr + 2 + k
            m = f"MATCH(SMALL({PY('O')},{k + 1}),{PY('O')},0)"
            self.merge(ws, f"B{r}:C{r}", f'=IFERROR(INDEX({PY("B")},{m}),"")')
            ws[f"D{r}"] = f'=IFERROR(INDEX({PY("D")},{m}),"")'
            ws[f"E{r}"] = f'=IFERROR(INDEX({PY("C")},{m}),"")'
            self.merge(ws, f"F{r}:G{r}", f'=IFERROR(INDEX({PY("J")},{m}),"")')
            paint(ws, f"B{r}:G{r}", f=FILL_WHITE, font=T.font(9), border=_C.CELL_BOX,
                  align=Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True))
            ws[f"D{r}"].number_format = FMT_SDATE
            ws[f"E{r}"].number_format = FMT_M
            ws.row_dimensions[r].height = 19
        ws[f"B{lr + 2}"].value = f'=IFERROR(INDEX({PY("B")},MATCH(SMALL({PY("O")},1),{PY("O")},0)),"No unpaid bills — nice!")'
        cf_formula(ws, f"F{lr + 2}:G{lr + 7}", f'LEFT($F{lr + 2},7)="Overdue"', EXP_BG, C_EXP, True)
        cards.append((2, lr, 7, lr + 7))
        section(ws, T, lr, 8, 13, "ACCOUNT BALANCES")
        self.head(ws, lr + 1, 8, [("Account", 3), ("Type", 1), ("Balance", 2)], height=22)
        for k in range(6):
            r = lr + 2 + k
            self.merge(ws, f"H{r}:J{r}", f'=IF(INDEX({BA("B")},{k + 1})="","",INDEX({BA("B")},{k + 1}))')
            ws[f"K{r}"] = f'=IF(H{r}="","",INDEX({BA("C")},{k + 1}))'
            self.merge(ws, f"L{r}:M{r}", f'=IF(H{r}="","",INDEX({BA("I")},{k + 1}))')
            paint(ws, f"H{r}:M{r}", f=FILL_WHITE, font=T.font(9), border=_C.CELL_BOX, align=LEFT)
            ws[f"L{r}"].number_format = FMT_M
            ws[f"L{r}"].alignment = RIGHT
            ws.row_dimensions[r].height = 19
        cf_formula(ws, f"L{lr + 2}:M{lr + 7}", f"AND(ISNUMBER($L{lr + 2}),$L{lr + 2}<0)", font_color=C_EXP, bold=True)
        cards.append((8, lr, 13, lr + 7))
        ws.freeze_panes = "A6"
        skin(ws, 13, lr + 8, cards=cards, hide_headers=True)

    # ================================================================ 8 AUTOMATED CALENDAR
    def build_cal(self):
        ws, T, S = self.ws[S_CAL], self.T, S_CAL
        setup_sheet(ws, {**{L(c): 15.5 for c in range(2, 9)}, "I": 3, "J": 25, "K": 13})
        self.title(ws, "AUTOMATED CALENDAR", "Income dates (↑), bills and loan payments (↓), savings transfers (◆) and payment deadlines (⚑) "
                   "for any month of your budget period — filled in from your recurring items and payments.", 11)
        ws.row_dimensions[4].height = 10
        self.label(ws, "B5", "MONTH", 9, True, SECONDARY, RIGHT)
        self.merge(ws, "C5:D5", f"={q(S_SET)}!$BD${M1 + 1}")
        self.inp(S, "C5:D5", align=CENTER)
        add_list_dv(ws, "C5", f"{q(S_SET)}!$BD${M1 + 1}:$BD${M1 + 12}")
        ws["C5"] = f'=INDEX({q(S_SET)}!$BD${M1 + 1}:$BD${M1 + 12},MAX(1,MIN(12,(YEAR({TODAY})-YEAR({P0}))*12+MONTH({TODAY})-MONTH({P0})+1)))'
        self.label(ws, "F5", "TODAY", 9, True, SECONDARY, RIGHT)
        ws["G5"] = "=$Y$4"
        self.calc(S, "G5", FMT_DATE, CENTER)
        ws.row_dimensions[5].height = 24
        ws.row_dimensions[6].height = 10
        # helpers
        hp = {1: (f'=IFERROR(MATCH(C5,{q(S_SET)}!$BD${M1 + 1}:$BD${M1 + 12},0),1)', None), 2: (f"=EDATE({P0},Y1-1)", FMT_DATE),
              3: ("=Y2-WEEKDAY(Y2,3)", FMT_DATE), 4: (f"={TODAY}", FMT_DATE)}
        for r, (f, nf) in hp.items():
            ws[f"Y{r}"] = f
            ws[f"X{r}"] = ["", "period month", "first of month", "grid start (Mon)", "today"][r]
            if nf:
                ws[f"Y{r}"].number_format = nf
        # daily ledger
        for c, h in (("AA", "date"), ("AB", "rec income"), ("AC", "rec bills"), ("AD", "rec savings"), ("AE", "payments due"),
                     ("AF", "unpaid due")):
            ws[f"{c}4"] = h
        rr = lambda c: f"{q(S_RT)}!${c}${RT1}:${c}${RTN}"
        for i in range(LDN - LD1 + 1):
            r = LD1 + i
            d = f"$AA{r}"
            ws[f"AA{r}"] = f"={P0}-7+{i}"
            eom = f"DAY(EOMONTH({d},0))"
            dayH = f"DAY({rr('H')})"
            occ = (f'({rr("B")}<>"")*({rr("J")}<>"Paused")*({rr("H")}<={d})*(({rr("I")}="")+({rr("I")}>={d})>0)*'
                   f'(({rr("P")}>0)*(MOD({d}-{rr("H")},{rr("P")}+({rr("P")}=0))=0)'
                   f'+({rr("Q")}>0)*(DAY({d})=({dayH}-({dayH}>{eom})*({dayH}-{eom})))'
                   f'*(MOD((YEAR({d})-YEAR({rr("H")}))*12+MONTH({d})-MONTH({rr("H")}),{rr("Q")}+({rr("Q")}=0))=0))')
            ws[f"AB{r}"] = f'=SUMPRODUCT({occ}*({rr("C")}="Income")*{rr("D")})'
            ws[f"AC{r}"] = f'=SUMPRODUCT({occ}*(({rr("C")}="Expense")+({rr("C")}="Debt Payment"))*{rr("D")})'
            ws[f"AD{r}"] = f'=SUMPRODUCT({occ}*({rr("C")}="Savings")*{rr("D")})'
            ws[f"AE{r}"] = f'=SUMIFS({PY("C")},{PY("D")},{d})'
            ws[f"AF{r}"] = f'=COUNTIFS({PY("D")},{d},{PY("E")},"<>Paid",{PY("B")},"?*")'
        for c in range(24, 33):
            ws.column_dimensions[L(c)].hidden = True
        led = lambda c: f"${c}${LD1}:${c}${LDN}"
        self.merge(ws, "B7:H7", "=Y2")
        ws["B7"].number_format = "mmmm yyyy"
        ws["B7"].font = T.font(16, True, NAVY)
        ws["B7"].alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[7].height = 30
        for d in range(7):
            c = L(2 + d)
            ws[f"{c}8"] = f"=$Y$3+{d}"
            ws[f"{c}8"].number_format = "dddd"
            paint(ws, f"{c}8", f=FILL_NAVY, font=T.font(10, True, WHITE), align=CENTER)
        ws.row_dimensions[8].height = 22
        G0 = 9
        for w in range(6):
            base = G0 + w * 5
            for d in range(7):
                c = L(2 + d)
                date = f"{c}{base}"
                ws[date] = f"=$Y$3+{w * 7 + d}"
                ws[date].number_format = "d"
                ws[date].font = T.font(11, True, DARK)
                ws[date].alignment = Alignment(horizontal="right", vertical="top", indent=1)
                inm = f"MONTH({date})=MONTH($Y$2)"
                sv = lambda col: f"SUMIFS({led(col)},{led('AA')},{date})"
                ws[f"{c}{base + 1}"] = f'=IF(AND({inm},{sv("AB")}>0),"↑ "&TEXT({sv("AB")},"#,##0"),"")'
                ws[f"{c}{base + 2}"] = f'=IF(AND({inm},{sv("AC")}+{sv("AE")}>0),"↓ "&TEXT({sv("AC")}+{sv("AE")},"#,##0"),"")'
                ws[f"{c}{base + 3}"] = f'=IF(AND({inm},{sv("AD")}>0),"◆ "&TEXT({sv("AD")},"#,##0")&" saved","")'
                nm = f'INDEX({PY("B")},MATCH(INT({date})&"|1",{PY("N")},0))'
                ws[f"{c}{base + 4}"] = f'=IF({inm},IFERROR("⚑ "&{nm},""),"")'
                fonts = {1: T.font(9, True, C_INC), 2: T.font(9, True, C_EXP), 3: T.font(9, False, C_SAV), 4: T.font(8, True, C_GOAL)}
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
                ws.row_dimensions[base + k].height = 15
            cf_formula(ws, f"B{base}:H{base}", f"B{base}=$Y$4", BLUE, WHITE, True, stop=True)
            cf_formula(ws, f"B{base}:H{base + 4}", f"MONTH(B${base})<>MONTH($Y$2)", BG, MED_GRAY, stop=True)
            cf_formula(ws, f"B{base + 4}:H{base + 4}",
                       f'AND(B{base + 4}<>"",B${base}<$Y$4,SUMIFS({led("AF")},{led("AA")},B${base})>0)', EXP_BG, C_EXP, True)
        # side panel
        first, nxt = "$Y$2", "EDATE($Y$2,1)"
        win = lambda col: f'SUMIFS({led(col)},{led("AA")},">="&{first},{led("AA")},"<"&{nxt})'
        section(ws, T, G0, 10, 11, "THIS MONTH")
        stats = [("Scheduled income", f"={win('AB')}", FMT_M, C_INC), ("Recurring bills & debt", f"={win('AC')}", FMT_M, C_EXP),
                 ("One-off payments due", f"={win('AE')}", FMT_M, C_EXP), ("Savings transfers", f"={win('AD')}", FMT_M, C_SAV),
                 ("Scheduled net", f"={win('AB')}-{win('AC')}-{win('AE')}-{win('AD')}", FMT_M, NAVY),
                 ("Unpaid bills (count)", f'=COUNTIFS({PY("D")},">="&{first},{PY("D")},"<"&{nxt},{PY("E")},"<>Paid",{PY("B")},"?*")', "0", C_EXP),
                 ("Logged spending", f'=SUMIFS({TR("I")},{TR("C")},">="&{first},{TR("C")},"<"&{nxt},{TR("F")},"Expense")', FMT_M, C_EXP)]
        for i, (lab, f, nf, color) in enumerate(stats):
            r = G0 + 1 + i
            self.label(ws, f"J{r}", lab, 10, False)
            ws[f"J{r}"].border = _C.CELL_BOX
            ws[f"K{r}"] = f
            self.calc(S, f"K{r}", nf, RIGHT, color, True)
            ws.row_dimensions[r].height = 18
        cf_formula(ws, f"K{G0 + 5}", f"K{G0 + 5}<0", EXP_BG, C_EXP, True)
        section(ws, T, G0 + 10, 10, 11, "LEGEND", color=LAVENDER)
        leg = [(BLUE, "Today", WHITE), (BG, "Other month", MED_GRAY), (WHITE, "↑ Income (recurring)", C_INC),
               (WHITE, "↓ Bills & loan payments", C_EXP), (WHITE, "◆ Savings transfers", C_SAV), (WHITE, "⚑ Payment due", C_GOAL),
               (EXP_BG, "⚑ Overdue payment", C_EXP)]
        for i, (colr, t, fc) in enumerate(leg):
            r = G0 + 11 + i
            self.merge(ws, f"J{r}:K{r}", t)
            ws[f"J{r}"].font = T.font(9, True, fc)
            paint(ws, f"J{r}:K{r}", f=fill(colr), border=_C.CELL_BOX)
            ws[f"J{r}"].alignment = Alignment(vertical="center", indent=1)
            ws.row_dimensions[r].height = 18
        self.note(ws, f"J{G0 + 19}:K{G0 + 22}", "Amounts are scheduled items (recurring + payments). Logged day-to-day spending "
                  "appears on the month tabs.")
        ws.freeze_panes = "A6"
        skin(ws, 11, G0 + 30, cards=[(2, 5, 8, 5), (2, 7, 8, G0 + 29), (10, G0, 11, G0 + 7), (10, G0 + 10, 11, G0 + 22)],
             hide_headers=True)

    # ================================================================ 9 PAYCHECK
    def build_pc(self):
        ws, T, S = self.ws[S_PC], self.T, S_PC
        widths = [12, 20, 13, 12, 13, 13, 15, 13, 13, 13]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        self.title(ws, "PAYCHECK DASHBOARD", "Plan each paycheck: what's left after the bills due before the next one and your savings.", 11)
        b, e = PC1, PCN
        self.tiles(ws, 5, [("PAYCHECKS", f'=COUNT(B{b}:B{e})', "0", NAVY),
                           ("GROSS INCOME", f"=SUM(D{b}:D{e})", FMT_M0, C_INC),
                           ("NET INCOME", f"=SUM(G{b}:G{e})", FMT_M0, C_INC, C_INC),
                           ("DEDUCTIONS", f"=SUM(E{b}:F{e})", FMT_M0, C_EXP),
                           ("SAVINGS ALLOCATED", f"=SUM(I{b}:I{e})", FMT_M0, C_SAV)], c1=2, width=2)
        ws.row_dimensions[7].height = 10
        self.head(ws, 8, 2, ["Pay date", "Employer / source", "Gross pay", "Taxes", "Other deductions", "Net pay",
                             "Bills before next pay", "Savings allocated", "Left to spend", "Covers until"])
        cal_led = lambda c: f"{q(S_CAL)}!${c}${LD1}:${c}${LDN}"
        data = SD.paychecks() if self.demo else []
        for i in range(PCN - PC1 + 1):
            r = PC1 + i
            if i < len(data):
                d, src, g, tx, oth, sav = data[i]
                ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"], ws[f"F{r}"], ws[f"I{r}"] = d, src, g, tx, oth, sav
            self.inp(S, f"B{r}", FMT_SDATE, CENTER)
            self.inp(S, f"C{r}")
            self.inp(S, f"D{r}:F{r}", FMT_M, RIGHT)
            self.inp(S, f"I{r}", FMT_M, RIGHT)
            ws[f"G{r}"] = f'=IF(B{r}="","",N(D{r})-N(E{r})-N(F{r}))'
            ws[f"K{r}"] = f'=IF(B{r}="","",IF(N(B{r + 1})>B{r},B{r + 1}-1,B{r}+13))'
            ws[f"H{r}"] = (f'=IF(B{r}="","",SUMIFS({cal_led("AC")},{cal_led("AA")},">="&B{r},{cal_led("AA")},"<="&K{r})'
                           f'+SUMIFS({PY("C")},{PY("D")},">="&B{r},{PY("D")},"<="&K{r}))')
            ws[f"J{r}"] = f'=IF(B{r}="","",G{r}-H{r}-N(I{r}))'
            self.calc(S, f"G{r}:H{r}", FMT_M, RIGHT)
            self.calc(S, f"J{r}", FMT_M, RIGHT, NAVY, True)
            self.calc(S, f"K{r}", FMT_SDATE, CENTER)
            ws.row_dimensions[r].height = 19
        add_dv(ws, f"B{b}:B{e}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date.")
        add_dv(ws, f"D{b}:F{e}", "decimal", "greaterThanOrEqual", "0")
        cf_formula(ws, f"J{b}:J{e}", f"AND(ISNUMBER(J{b}),J{b}<0)", EXP_BG, C_EXP, True)
        cf_formula(ws, f"B{b}:K{e}", f"AND(ISNUMBER($B{b}),$B{b}<=$M$2,$K{b}>=$M$2)", font_color=NAVY, bold=True)
        ws["M1"], ws["M2"] = "today", f"={TODAY}"
        ws.column_dimensions["M"].hidden = True
        note_r = PCN + 1
        self.note(ws, f"B{note_r}:K{note_r}", "Planning view: log the net pay as Income (Recurring or Variable Transactions) so your budget "
                  "counts it. Bills before next pay = recurring bills, loan payments and one-off payments due until the day before the next pay date.")
        ws.row_dimensions[note_r].height = 30
        cr = note_r + 2
        section(ws, T, cr, 2, 11, "WHERE EACH PAYCHECK GOES  (first 26)")
        for rr in range(cr + 1, cr + 16):
            ws.row_dimensions[rr].height = 18
        ch = BarChart()
        ch.type = "col"
        ch.grouping = "stacked"
        ch.overlap = 100
        for col in (8, 9, 10):
            ch.add_data(Reference(ws, min_col=col, min_row=8, max_row=PC1 + 25), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=PC1, max_row=PC1 + 25))
        self.chart_style(ch, None, [C_EXP, C_SAV, C_INC])
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.x_axis.number_format = "mmm d"
        place_chart(ws, ch, 2, cr + 1, 11, cr + 15)
        self.table(ws, "Paychecks", f"B8:K{PCN}")
        ws.freeze_panes = "C9"
        skin(ws, 11, cr + 16, cards=[(2, 8, 11, note_r), (2, cr, 11, cr + 15)], hide_headers=True)

    # ================================================================ 22 50/30/20
    def build_503(self):
        ws, T, S = self.ws[S_503], self.T, S_503
        setup_sheet(ws, {"B": 28, "C": 12, "D": 14, "E": 14, "F": 13, "G": 14, "H": 21, "I": 3, "J": 24, "K": 14})
        self.title(ws, "50/30/20 DASHBOARD", "Compare your real spending with the 50/30/20 rule: 50% needs, 30% wants, 20% savings & debt repayment.", 11)
        ws.row_dimensions[4].height = 10
        self.period_selector(ws, S, "B5", "C5:D5", "P5")
        sel = "$P$5"
        ws["O5"] = "period"
        ws.row_dimensions[5].height = 24
        inc = f"IF({sel}=0,{q(S_AT)}!$C${AT1 + 12},INDEX({q(S_AT)}!$C${AT1}:$C${AT1 + 11},{sel}))"
        by = lambda bucket: (f'IF({sel}=0,SUMIFS({MX("R")},{MX("D")},"{bucket}"),SUMIFS(INDEX({MX_MONTHS},0,{sel}),{MX("D")},"{bucket}"))')
        ws.row_dimensions[6].height = 10
        self.tile(ws, 7, 2, 3, "INCOME (PERIOD)", f"={inc}", FMT_M0, C_INC, color=C_INC)
        self.tile(ws, 7, 4, 5, "SPENT ON NEEDS + WANTS", f"=E12+E13", FMT_M0, C_EXP, color=C_EXP)
        self.tile(ws, 7, 6, 8, "SAVED + DEBT REPAID", "=E14", FMT_M0, C_SAV, color=C_SAV)
        ws.row_dimensions[9].height = 10
        section(ws, T, 10, 2, 8, "YOUR SPLIT VS THE RULE")
        self.head(ws, 11, 2, ["Bucket", "Target %", "Recommended", "Actual", "% of income", "Difference", "Status"])
        rows = [("Needs", 0.5, "Needs", C_EXP), ("Wants", 0.3, "Wants", "F08A8F"), ("Savings & debt repayment", 0.2, "Savings & Debt", C_SAV)]
        for k, (lab, pct, bucket, color) in enumerate(rows):
            r = 12 + k
            self.label(ws, f"B{r}", lab, 10, True, DARK)
            ws[f"B{r}"].border = _C.CELL_BOX
            ws[f"C{r}"] = pct
            self.inp(S, f"C{r}", FMT_PCT, CENTER)
            ws[f"D{r}"] = f"=C{r}*$B$8"
            ws[f"E{r}"] = f"={by(bucket)}"
            ws[f"F{r}"] = f'=IF($B$8=0,"",E{r}/$B$8)'
            ws[f"G{r}"] = f"=E{r}-D{r}" if k < 2 else f"=E{r}-D{r}"
            ws[f"H{r}"] = (f'=IF($B$8=0,"Add income",IF(E{r}<=D{r},"✓ Within target","Over by "&TEXT(E{r}-D{r},"#,##0")))' if k < 2 else
                           f'=IF($B$8=0,"Add income",IF(E{r}>=D{r},"✓ Target met","Short by "&TEXT(D{r}-E{r},"#,##0")))')
            self.calc(S, f"D{r}:E{r}", FMT_M, RIGHT)
            self.calc(S, f"F{r}", FMT_PCT, CENTER)
            self.calc(S, f"G{r}", FMT_M, RIGHT)
            self.calc(S, f"H{r}", None, CENTER)
            ws.row_dimensions[r].height = 22
        add_dv(ws, "C12:C14", "decimal", "between", "0", "1", error="Enter a percentage between 0% and 100%.")
        r = 15
        self.label(ws, f"B{r}", "Total", 10, True, NAVY)
        ws[f"C{r}"] = "=SUM(C12:C14)"
        ws[f"D{r}"] = "=SUM(D12:D14)"
        ws[f"E{r}"] = "=SUM(E12:E14)"
        ws[f"F{r}"] = '=IF($B$8=0,"",E15/$B$8)'
        ws[f"G{r}"] = "=$B$8-E15"
        ws[f"H{r}"] = '="Unallocated: "&TEXT(G15,"#,##0")'
        self.calc(S, f"C{r}:H{r}", FMT_M, RIGHT, NAVY, True)
        ws[f"C{r}"].number_format = ws[f"F{r}"].number_format = FMT_PCT
        cf_formula(ws, "H12:H14", 'LEFT(H12,1)="✓"', INC_BG, C_INC, True)
        cf_formula(ws, "H12:H14", 'OR(LEFT(H12,4)="Over",LEFT(H12,5)="Short")', EXP_BG, C_EXP, True)
        cf_formula(ws, "C15", "ROUND(C15,4)<>1", WARNING_BG, WARNING, True)
        self.note(ws, "B16:H16", "Needs and Wants come from each expense category's setting on Easy Setup. Savings & debt = transfers to "
                  "Sinking Funds + payments to debts. Targets are editable.")
        ws.row_dimensions[16].height = 28
        # charts
        section(ws, T, 18, 2, 8, "RECOMMENDED VS ACTUAL")
        for rr in range(19, 34):
            ws.row_dimensions[rr].height = 18
        ws["D11"].value, ws["E11"].value = "Recommended", "Actual"
        ch = BarChart()
        ch.type = "col"
        ch.add_data(Reference(ws, min_col=4, max_col=5, min_row=11, max_row=14), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=12, max_row=14))
        self.chart_style(ch, None, [MED_GRAY, C_GOAL])
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = ch.y_axis.delete = False
        place_chart(ws, ch, 2, 19, 5, 33)
        dn = DoughnutChart()
        dn.add_data(Reference(ws, min_col=5, min_row=12, max_row=14), titles_from_data=False)
        dn.set_categories(Reference(ws, min_col=2, min_row=12, max_row=14))
        dn.holeSize = 55
        for i, colr in enumerate((C_EXP, "F08A8F", C_SAV)):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = colr
            dn.series[0].dPt.append(pt)
        self.chart_style(dn, "Actual split", h=7, w=9)
        dn.legend.position = "b"
        place_chart(ws, dn, 6, 19, 8, 33)
        # category lists
        section(ws, T, 10, 10, 11, "NEEDS  (this period)", color=C_EXP)
        section(ws, T, 33 - 10, 10, 11, "WANTS  (this period)", color="F08A8F")
        amt = lambda cell: (f'IF({cell}="","",IF({sel}=0,SUMIFS({MX("R")},{MX("B")},{cell}),'
                            f'SUMIFS(INDEX({MX_MONTHS},0,{sel}),{MX("B")},{cell})))')
        for lst, r0, n in (("needs", 11, 11), ("wants", 24, 12)):
            for k in range(n):
                r = r0 + k
                ws[f"J{r}"] = f'=IFERROR(INDEX({LIST(lst)},{k + 1})&"","")'
                ws[f"K{r}"] = "=" + amt(f"J{r}")
                paint(ws, f"J{r}", f=FILL_WHITE, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
                self.calc(S, f"K{r}", FMT_M, RIGHT)
                ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 18, 18)
        cf_databar_amt(ws, "K11:K21", C_EXP)
        cf_databar_amt(ws, "K24:K35", "F08A8F")
        ws.column_dimensions["O"].hidden = ws.column_dimensions["P"].hidden = True
        ws.freeze_panes = "A6"
        skin(ws, 11, 36, cards=[(2, 7, 8, 8), (2, 10, 8, 16), (2, 18, 8, 33), (10, 10, 11, 21), (10, 23, 11, 35)], hide_headers=True)

    # ================================================================ 23 EXPENSE DISTRIBUTION
    def build_ed(self):
        ws, T, S = self.ws[S_ED], self.T, S_ED
        setup_sheet(ws, {"B": 22, "C": 10, "D": 10, "E": 13, "F": 10, "G": 13, "H": 13, "I": 12, "J": 3, "K": 12, "L": 12, "M": 12, "N": 12})
        self.title(ws, "EXPENSE DISTRIBUTION", "Where your money goes, category by category: amounts, shares, budgets and averages.", 14)
        ws.row_dimensions[4].height = 10
        self.period_selector(ws, S, "B5", "C5:E5", "P5")
        ws["O5"] = "period"
        sel = "$P$5"
        ws.row_dimensions[5].height = 24
        ws.row_dimensions[6].height = 10
        n = 30
        h0 = 8
        section(ws, T, h0 - 1, 2, 9, "ALL EXPENSE CATEGORIES", color=C_EXP)
        self.head(ws, h0, 2, ["Category", "Group", "Bucket", "Spent", "Share", "Budget", "Variance", "Avg / month"])
        tot = f"$E${h0 + 1 + n}"
        for k in range(n):
            r = h0 + 1 + k
            ws[f"B{r}"] = f'=IFERROR(INDEX({LIST("expense")},{k + 1})&"","")'
            m = f"MATCH($B{r},{MX('B')},0)"
            ws[f"C{r}"] = f'=IF(B{r}="","",INDEX({MX("E")},{m}))'
            ws[f"D{r}"] = f'=IF(B{r}="","",INDEX({MX("D")},{m}))'
            ws[f"E{r}"] = f'=IF(B{r}="","",IF({sel}=0,INDEX({MX("R")},{m}),INDEX({MX_MONTHS},{m},{sel})))'
            ws[f"F{r}"] = f'=IF(OR(B{r}="",N({tot})=0),"",E{r}/{tot})'
            ws[f"G{r}"] = f'=IF(B{r}="","",INDEX({MX("T")},{m})/IF({sel}=0,1,12))'
            ws[f"H{r}"] = f'=IF(B{r}="","",G{r}-E{r})'
            ws[f"I{r}"] = f'=IF(B{r}="","",INDEX({MX("S")},{m}))'
            paint(ws, f"B{r}", f=FILL_WHITE, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
            self.calc(S, f"C{r}:D{r}", None, CENTER)
            self.calc(S, f"E{r}", FMT_M, RIGHT)
            self.calc(S, f"F{r}", FMT_PCT, CENTER)
            self.calc(S, f"G{r}:I{r}", FMT_M, RIGHT)
            ws.row_dimensions[r].height = 18
        r = h0 + 1 + n
        self.label(ws, f"B{r}:D{r}", "Total", 10, True, NAVY)
        ws[f"E{r}"] = f"=SUM(E{h0 + 1}:E{r - 1})"
        ws[f"F{r}"] = f'=IF(E{r}=0,"",1)'
        ws[f"G{r}"] = f"=SUM(G{h0 + 1}:G{r - 1})"
        ws[f"H{r}"] = f"=G{r}-E{r}"
        ws[f"I{r}"] = f"=SUM(I{h0 + 1}:I{r - 1})"
        self.calc(S, f"E{r}:I{r}", FMT_M, RIGHT, NAVY, True)
        ws[f"F{r}"].number_format = FMT_PCT
        cf_databar(ws, f"F{h0 + 1}:F{r - 1}", C_EXP)
        cf_formula(ws, f"H{h0 + 1}:H{r}", f"AND(ISNUMBER(H{h0 + 1}),H{h0 + 1}<0)", EXP_BG, C_EXP, True)
        # summaries + charts (right)
        names, amts, _b = self.top_helper(ws, 18, sel, n=8)             # R..V
        ws["R2"] = "Other"
        last = 5 + MXN - MX1
        ws["W5"] = "=ROUND(SUMIF($R$5:$R$" + str(last) + ",\">0\")-SUM($T$5:$T$12),2)"
        for k in range(8):
            ws[f"X{5 + k}"] = f"=S{5 + k}"
            ws[f"Y{5 + k}"] = f"=T{5 + k}"
        ws["X13"], ws["Y13"] = '=IF(W5>0.005,"Other","")', "=MAX(0,W5)"
        for c in range(15, 26):
            ws.column_dimensions[L(c)].hidden = True
        section(ws, T, h0 - 1, 11, 14, "BY GROUP & BUCKET")
        self.head(ws, h0, 11, ["Split", "Spent", "Share", "Budget"])
        splits = [("Fixed", "C"), ("Variable", "C"), ("Needs", "D"), ("Wants", "D")]
        for k, (lab, col) in enumerate(splits):
            r = h0 + 1 + k
            ws[f"K{r}"] = lab
            ws[f"L{r}"] = f'=SUMIFS($E${h0 + 1}:$E${h0 + n},${col}${h0 + 1}:${col}${h0 + n},K{r})'
            ws[f"M{r}"] = f'=IF({tot}=0,"",L{r}/{tot})'
            ws[f"N{r}"] = f'=SUMIFS($G${h0 + 1}:$G${h0 + n},${col}${h0 + 1}:${col}${h0 + n},K{r})'
            paint(ws, f"K{r}", f=FILL_WHITE, font=T.font(10, True), border=_C.CELL_BOX, align=LEFT)
            self.calc(S, f"L{r}", FMT_M, RIGHT)
            self.calc(S, f"M{r}", FMT_PCT, CENTER)
            self.calc(S, f"N{r}", FMT_M, RIGHT)
            ws.row_dimensions[r].height = 18
        cf_databar(ws, f"M{h0 + 1}:M{h0 + 4}", C_EXP)
        section(ws, T, h0 + 6, 11, 14, "TOP CATEGORIES")
        dn = DoughnutChart()
        dn.add_data(Reference(ws, min_col=25, min_row=5, max_row=13), titles_from_data=False)
        dn.set_categories(Reference(ws, min_col=24, min_row=5, max_row=13))
        dn.holeSize = 50
        self.chart_style(dn, None)
        dn.legend.position = "r"
        place_chart(ws, dn, 11, h0 + 7, 14, h0 + 21)
        section(ws, T, h0 + 23, 11, 14, "TOP 8 BY AMOUNT")
        bc = BarChart()
        bc.type = "bar"
        bc.add_data(Reference(ws, min_col=20, min_row=5, max_row=12), titles_from_data=False)
        bc.set_categories(Reference(ws, min_col=19, min_row=5, max_row=12))
        self.chart_style(bc, None, [C_EXP], legend=False)
        bc.y_axis.majorGridlines = None
        bc.x_axis.delete = bc.y_axis.delete = False
        bc.x_axis.scaling.orientation = "maxMin"
        place_chart(ws, bc, 11, h0 + 24, 14, h0 + n + 1)
        ws.freeze_panes = "A6"
        skin(ws, 14, h0 + n + 2, cards=[(2, h0 - 1, 9, h0 + 1 + n), (11, h0 - 1, 14, h0 + 4), (11, h0 + 6, 14, h0 + 21),
                                        (11, h0 + 23, 14, h0 + n + 1)], hide_headers=True)

    # ================================================================ 24 SINKING FUNDS
    def build_sf(self):
        ws, T, S = self.ws[S_SF], self.T, S_SF
        widths = [22, 13, 13, 13, 12, 20, 13, 14, 13, 11, 10, 13, 28]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        self.title(ws, "SINKING FUNDS", "Savings goals. Contributions = transactions, recurring transfers and paid bills in the fund's category.", 14)
        t = TODAY
        self.tiles(ws, 5, [("TOTAL SAVED", f"=SUM(I{SF1}:I{SFN})", FMT_M0, C_SAV, C_SAV), ("TOTAL TARGET", f"=SUM(C{SF1}:C{SFN})", FMT_M0, C_GOAL),
                           ("OVERALL PROGRESS", f'=IF(SUM(C{SF1}:C{SFN})=0,"—",SUM(P{SF1}:P{SFN})/SUM(C{SF1}:C{SFN}))', FMT_PCT, C_GOAL),
                           ("MONTHLY PLAN", f"=SUM(E{SF1}:E{SFN})", FMT_M0, C_SAV),
                           ("GOALS REACHED", f'=COUNTIFS(K{SF1}:K{SFN},">=1")&" of "&COUNTIF(B{SF1}:B{SFN},"?*")', None, C_INC)], c1=2, width=2)
        ws.row_dimensions[7].height = 10
        self.head(ws, 8, 2, ["Fund name", "Target amount", "Starting balance", "Monthly contribution", "Target date", "Held in account",
                             "Saved this period", "Current balance", "Remaining", "Progress", "Months to go", "Projected finish", "Status"])
        for i in range(SFN - SF1 + 1):
            r = SF1 + i
            if self.demo and i < len(SD.FUNDS):
                for c, v in zip("BCDEFG", SD.FUNDS[i]):
                    ws[f"{c}{r}"] = v
            self.inp(S, f"B{r}")
            self.inp(S, f"C{r}:E{r}", FMT_M, RIGHT)
            self.inp(S, f"F{r}", FMT_SDATE, CENTER)
            self.inp(S, f"G{r}")
            ws[f"H{r}"] = f'=IF(B{r}="","",IFERROR(INDEX({MX("R")},MATCH(B{r},{MX("B")},0)),0))'
            ws[f"I{r}"] = f'=IF(B{r}="","",N(D{r})+H{r})'
            ws[f"J{r}"] = f'=IF(B{r}="","",MAX(0,N(C{r})-I{r}))'
            ws[f"K{r}"] = f'=IF(OR(B{r}="",N(C{r})=0),"",MIN(1,I{r}/C{r}))'
            ws[f"L{r}"] = f'=IF(B{r}="","",IF(J{r}=0,0,IF(N(E{r})<=0,"—",-INT(-J{r}/E{r}))))'
            ws[f"M{r}"] = f'=IF(OR(B{r}="",NOT(ISNUMBER(L{r}))),"",EDATE({t},L{r}))'
            need = f"J{r}/MAX(1,(YEAR(F{r})-YEAR({t}))*12+MONTH(F{r})-MONTH({t}))"
            ws[f"N{r}"] = (f'=IF(B{r}="","",IF(J{r}=0,"✓ Goal reached",IF(F{r}="","No target date",IF(F{r}<{t},"Past target date",'
                           f'IF(AND(ISNUMBER(M{r}),M{r}<=F{r}),"On track","Behind — needs "&TEXT({need},"#,##0")&"/mo")))))')
            self.calc(S, f"H{r}:J{r}", FMT_M, RIGHT)
            ws[f"I{r}"].font = T.font(10, True, C_SAV)
            ws[f"P{r}"] = f'=IF(B{r}="",0,MIN(I{r},N(C{r})))'
            self.calc(S, f"K{r}", FMT_PCT, CENTER)
            self.calc(S, f"L{r}", "0", CENTER)
            self.calc(S, f"M{r}", "mmm yyyy", CENTER)
            self.calc(S, f"N{r}", None, LEFT)
            ws.row_dimensions[r].height = 21
        ws["P8"] = "capped saved"
        ws.column_dimensions["P"].hidden = True
        add_list_dv(ws, f"G{SF1}:G{SFN}", BA("B"))
        add_dv(ws, f"C{SF1}:E{SFN}", "decimal", "greaterThanOrEqual", "0")
        add_dv(ws, f"F{SF1}:F{SFN}", "date", "greaterThan", "DATE(2000,1,1)")
        cf_databar(ws, f"K{SF1}:K{SFN}", C_SAV)
        cf_formula(ws, f"N{SF1}:N{SFN}", f'LEFT(N{SF1},1)="✓"', INC_BG, C_INC, True)
        cf_formula(ws, f"N{SF1}:N{SFN}", f'OR(LEFT(N{SF1},6)="Behind",LEFT(N{SF1},4)="Past")', EXP_BG, C_EXP, True)
        cf_formula(ws, f"N{SF1}:N{SFN}", f'N{SF1}="On track"', SAV_BG, C_SAV, True)
        r = SFN + 1
        self.label(ws, f"B{r}", "Total", 10, True, NAVY)
        for c in "CDEHIJ":
            ws[f"{c}{r}"] = f"=SUM({c}{SF1}:{c}{SFN})"
        self.calc(S, f"C{r}:J{r}", FMT_M, RIGHT, NAVY, True)
        for c in "FG":
            ws[f"{c}{r}"].value = None
        self.note(ws, f"B{r + 1}:N{r + 1}", "To save into a fund, use the fund's name as the category (a recurring transfer, a transaction or a "
                  "paid bill). The money moves into the 'Held in account' account on Bank Accounts.")
        ws.row_dimensions[r + 1].height = 28
        cr = r + 3
        section(ws, T, cr, 2, 14, "SAVINGS PROGRESS")
        for rr in range(cr + 1, cr + 15):
            ws.row_dimensions[rr].height = 18
        ch = BarChart()
        ch.type = "bar"
        ch.grouping = "stacked"
        ch.overlap = 100
        ch.add_data(Reference(ws, min_col=9, min_row=8, max_row=SFN), titles_from_data=True)
        ch.add_data(Reference(ws, min_col=10, min_row=8, max_row=SFN), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=SF1, max_row=SFN))
        self.chart_style(ch, None, [C_SAV, "D6E4F2"])
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.x_axis.scaling.orientation = "maxMin"
        place_chart(ws, ch, 2, cr + 1, 14, cr + 14)
        ws.freeze_panes = "C9"
        skin(ws, 14, cr + 15, cards=[(2, 8, 14, r), (2, cr, 14, cr + 14)], hide_headers=True)

    # ================================================================ 25 DEBT CALCULATOR
    def build_dc(self):
        ws, T, S = self.ws[S_DC], self.T, S_DC
        widths = [22, 12, 13, 13, 10, 12, 12, 11, 12, 13, 13, 13, 9, 13]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        self.title(ws, "DEBT CALCULATOR", "Your debts, payoff dates and a month-by-month snowball or avalanche plan.", 15)
        t = TODAY
        ws.row_dimensions[4].height = 10
        self.label(ws, "B5", "PAYOFF METHOD", 9, True, SECONDARY, RIGHT)
        self.merge(ws, "C5:D5", "Snowball")
        self.inp(S, "C5:D5", align=CENTER)
        add_list_dv(ws, "C5", '"Snowball,Avalanche"')
        self.label(ws, "E5:F5", "EXTRA PER MONTH", 9, True, SECONDARY, RIGHT)
        ws["G5"] = SD.EXTRA_DEBT if self.demo else 0
        self.inp(S, "G5", FMT_M, RIGHT)
        self.note(ws, "H5:O5", "Snowball = smallest balance first (quick wins). Avalanche = highest interest first (least interest). "
                  "Extra + all 'additional payments' go to the focus debt; paid-off minimums roll over.")
        ws.row_dimensions[5].height = 30
        ws.row_dimensions[6].height = 8
        # schedule geometry
        H20, H21, H22 = 21, 22, 23
        S0 = 28                       # month 0 row
        SN = S0 + 360
        ws.row_dimensions[7].height = 6
        self.head(ws, 8, 2, ["Debt", "Type", "Starting balance", "Current balance", "Interest (APR)", "Minimum payment",
                             "Additional payment", "Paid off", "Months to payoff", "Payoff date", "Total interest", "Paid this period",
                             "Order", "Payoff (plan)"])
        sched_col = lambda j: L(4 + j)            # debt j (0-based) -> schedule column D..M
        for i in range(DCN - DC1 + 1):
            r = DC1 + i
            if self.demo and i < len(SD.DEBTS):
                nm, start, cur, apr, mn, add, typ = SD.DEBTS[i]
                ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"], ws[f"E{r}"], ws[f"F{r}"], ws[f"G{r}"], ws[f"H{r}"] = nm, typ, start, cur, apr / 100, mn, add
            self.inp(S, f"B{r}:C{r}")
            self.inp(S, f"D{r}:E{r}", FMT_M, RIGHT)
            self.inp(S, f"F{r}", "0.0%", CENTER)
            self.inp(S, f"G{r}:H{r}", FMT_M, RIGHT)
            pay = f"(N(G{r})+N(H{r}))"
            ws[f"I{r}"] = f'=IF(OR(B{r}="",N(D{r})=0),"",MAX(0,(D{r}-E{r})/D{r}))'
            ws[f"J{r}"] = f'=IF(OR(B{r}="",N(E{r})<=0),IF(B{r}="","",0),IFERROR(NPER(N(F{r})/12,-{pay},E{r}),"Never"))'
            ws[f"K{r}"] = f'=IF(B{r}="","",IF(ISNUMBER(J{r}),EDATE({t},-INT(-J{r})),"Raise payment"))'
            ws[f"L{r}"] = f'=IF(B{r}="","",IF(ISNUMBER(J{r}),MAX(0,{pay}*J{r}-N(E{r})),""))'
            ws[f"M{r}"] = f'=IF(B{r}="","",IFERROR(INDEX({MX("R")},MATCH(B{r},{MX("B")},0)),0))'
            snow = (f'COUNTIFS($E${DC1}:$E${DCN},"<"&E{r},$B${DC1}:$B${DCN},"?*",$E${DC1}:$E${DCN},">0")'
                    f'+COUNTIFS($E${DC1}:E{r},E{r},$B${DC1}:B{r},"?*")')
            aval = (f'COUNTIFS($F${DC1}:$F${DCN},">"&N(F{r}),$B${DC1}:$B${DCN},"?*",$E${DC1}:$E${DCN},">0")'
                    f'+COUNTIFS($F${DC1}:F{r},N(F{r}),$B${DC1}:B{r},"?*",$E${DC1}:E{r},">0")')
            ws[f"N{r}"] = f'=IF(OR(B{r}="",N(E{r})<=0),99,IF($C$5="Avalanche",{aval},{snow}))'
            sc = sched_col(i)
            ws[f"O{r}"] = f'=IF(OR(B{r}="",N(E{r})<=0),"",IF(COUNTIF(${sc}${S0 + 1}:${sc}${SN},">0.005")>=360,"30+ years",EDATE({t},COUNTIF(${sc}${S0 + 1}:${sc}${SN},">0.005")+1)))'
            self.calc(S, f"I{r}", FMT_PCT, CENTER)
            self.calc(S, f"J{r}", "0.0", CENTER)
            self.calc(S, f"K{r}", "mmm yyyy", CENTER)
            self.calc(S, f"L{r}:M{r}", FMT_M, RIGHT)
            self.calc(S, f"N{r}", "0", CENTER)
            self.calc(S, f"O{r}", "mmm yyyy", CENTER, NAVY, True)
            ws.row_dimensions[r].height = 20
        add_list_dv(ws, f"C{DC1}:C{DCN}", R(S_SET, "J", INC1, INC1 + 3))
        add_dv(ws, f"D{DC1}:E{DCN}", "decimal", "greaterThanOrEqual", "0")
        add_dv(ws, f"F{DC1}:F{DCN}", "decimal", "between", "0", "1", error="Interest as a percentage, e.g. 19.9%.")
        add_dv(ws, f"G{DC1}:H{DCN}", "decimal", "greaterThanOrEqual", "0")
        cf_formula(ws, f"N{DC1}:N{DCN}", f"N{DC1}=99", font_color=WHITE)
        cf_databar(ws, f"I{DC1}:I{DCN}", C_INC)
        cf_formula(ws, f"K{DC1}:K{DCN}", f'K{DC1}="Raise payment"', EXP_BG, C_EXP, True)
        r = DCN + 1
        self.label(ws, f"B{r}:C{r}", "Total", 10, True, NAVY)
        for c in "DEGHLM":
            ws[f"{c}{r}"] = f"=SUM({c}{DC1}:{c}{DCN})"
        self.calc(S, f"D{r}:M{r}", FMT_M, RIGHT, NAVY, True)
        for c in "FIJK":
            ws[f"{c}{r}"].value = None
        # tiles (row 21..)? summary block to the right of helper rows
        pool = f"($G$5+SUM($H${DC1}:$H${DCN}))"
        months = f"IF(N{S0}<=0.005,0,COUNTIF($N${S0 + 1}:$N${SN},\">0.005\")+1)"
        ws.row_dimensions[DCN + 2].height = 10
        tr = DCN + 3     # 21
        # helper rows used by the schedule (min payment / monthly rate / priority) sit inside the schedule card header
        self.tiles(ws, tr, [("TOTAL DEBT", f"=E{DCN + 1}", FMT_M0, C_EXP, C_EXP),
                            ("MONTHLY PAYMENTS", f"=G{DCN + 1}+H{DCN + 1}+$G$5", FMT_M0, C_DEBT),
                            ("DEBT-FREE (PLAN)", f'=IF({months}>360,"30+ years",EDATE({t},{months}))', "mmm yyyy", C_INC, C_INC),
                            ("INTEREST (PLAN)", f"=SUM(O{S0 + 1}:O{SN})", FMT_M0, C_EXP),
                            ("SAVED VS NO PLAN", f'=MAX(0,L{DCN + 1}-SUM(O{S0 + 1}:O{SN}))', FMT_M0, C_INC)], c1=2, width=3, gap=0)
        ws.row_dimensions[tr + 2].height = 10
        # schedule
        sr = S0 - 3      # section row
        section(ws, T, sr, 2, 17, "PAYOFF SCHEDULE  —  month by month (plan method)")
        hr = S0 - 2
        self.head(ws, hr, 2, ["Month", "Date"] + [f'=IF($B${DC1 + j}="","Debt {j + 1}",LEFT($B${DC1 + j},14))' for j in range(10)]
                  + ["Total", "Interest", "Focus", "Pool"], height=30)
        # helper row (S0-1): min payments | rates | priority encoded in 3 hidden rows beyond the sheet (rows SN+2..SN+4)
        hm, hrate, hprio = SN + 2, SN + 3, SN + 4
        for j in range(10):
            c = sched_col(j)
            ws[f"{c}{hm}"] = f"=N($G${DC1 + j})"
            ws[f"{c}{hrate}"] = f"=N($F${DC1 + j})/12"
            ws[f"{c}{hprio}"] = f"=$N${DC1 + j}"
        ws[f"B{hm}"], ws[f"B{hrate}"], ws[f"B{hprio}"] = "min payment", "monthly rate", "priority"
        for rr in (hm, hrate, hprio):
            ws.row_dimensions[rr].hidden = True
        ws.row_dimensions[S0 - 1].height = 6
        rng = lambda r: f"$D${r}:$M${r}"
        for m in range(361):
            r = S0 + m
            ws[f"B{r}"] = m
            ws[f"C{r}"] = f"=EDATE({t},B{r})"
            if m == 0:
                for j in range(10):
                    ws[f"{sched_col(j)}{r}"] = f"=MAX(0,N($E${DC1 + j}))"
                ws[f"O{r}"] = 0
            else:
                p = r - 1
                ws[f"P{r}"] = f"=SUMPRODUCT(MIN({rng(hprio)}+({rng(p)}<=0.005)*1000))"
                ws[f"Q{r}"] = f"={pool}+SUMPRODUCT(({rng(p)}<=0.005)*{rng(hm)})"
                for j in range(10):
                    c = sched_col(j)
                    ws[f"{c}{r}"] = (f"=IF({c}{p}<=0.005,0,MAX(0,{c}{p}*(1+{c}${hrate})-({c}${hm}+IF({c}${hprio}=$P{r},$Q{r},0))))")
                ws[f"O{r}"] = f"=SUMPRODUCT({rng(p)},{rng(hrate)})"
            ws[f"N{r}"] = f"=SUM(D{r}:M{r})"
        paint(ws, f"B{S0}:Q{SN}", f=FILL_WHITE, font=T.font(9), border=_C.CELL_BOX, align=RIGHT, numfmt=FMT_M0)
        for r in range(S0, SN + 1):
            ws[f"B{r}"].number_format = "0"
            ws[f"C{r}"].number_format = "mmm yyyy"
            ws[f"P{r}"].number_format = "0"
        cf_formula(ws, f"N{S0}:N{SN}", f"N{S0}<=0.005", INC_BG, C_INC, True)
        # chart: total balance (10 years)
        chart_r = tr + 2
        ln = LineChart()
        ln.add_data(Reference(ws, min_col=14, min_row=S0, max_row=S0 + 120), titles_from_data=False)
        ln.set_categories(Reference(ws, min_col=3, min_row=S0, max_row=S0 + 120))
        self.chart_style(ln, "Total debt balance — next 10 years", [C_EXP], legend=False)
        ln.x_axis.number_format = "mmm yy"
        ln.x_axis.delete = ln.y_axis.delete = False
        ln.x_axis.tickLblSkip = 12
        ws.column_dimensions["R"].width = 3
        for c, w in (("S", 12), ("T", 12), ("U", 12), ("V", 12), ("W", 12), ("X", 12)):
            ws.column_dimensions[c].width = w
        section(ws, T, 8, 19, 24, "DEBT BALANCE OVER TIME")
        place_chart(ws, ln, 19, 9, 24, 24)
        ws.freeze_panes = "C9"
        skin(ws, 24, SN + 1, cards=[(2, 8, 15, DCN + 1), (2, sr, 17, SN), (19, 8, 24, 24)], hide_headers=True)

    # ================================================================ 26 NET WORTH
    def build_nw(self):
        ws, T, S = self.ws[S_NW], self.T, S_NW
        setup_sheet(ws, {"B": 18, "C": 41, "D": 15, "E": 3, "F": 18, "G": 43, "H": 15, "I": 3, "J": 20, "K": 15, "L": 15, "M": 15})
        self.title(ws, "NET WORTH", "What you own minus what you owe. Bank balances and debts come in automatically.", 13)
        self.tiles(ws, 5, [("TOTAL ASSETS", "=$K$19", FMT_M0, C_INC, C_INC), ("TOTAL LIABILITIES", "=$K$24", FMT_M0, C_EXP, C_EXP),
                           ("NET WORTH", "=$K$25", FMT_M0, NAVY), ("DEBT-TO-ASSET", '=IF($K$19=0,"—",$K$24/$K$19)', FMT_PCT, C_GOAL)],
                   c1=2, width=3)
        ws.row_dimensions[7].height = 10
        section(ws, T, 8, 2, 4, "ASSETS", color=C_INC)
        self.head(ws, 9, 2, ["Type", "Name", "Value"])
        ws["B10"], ws["C10"] = "Bank accounts", "All accounts except credit cards (auto)"
        ws["D10"] = f'=SUMIFS({BA("I")},{BA("C")},"<>Credit card",{BA("B")},"?*")'
        self.calc(S, "B10:C10")
        self.calc(S, "D10", FMT_M, RIGHT, C_INC, True)
        A1, AN = 11, 26
        for i in range(AN - A1 + 1):
            r = A1 + i
            if self.demo and i < len(SD.NET_WORTH_ITEMS):
                ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"] = SD.NET_WORTH_ITEMS[i]
            self.inp(S, f"B{r}:C{r}")
            self.inp(S, f"D{r}", FMT_M, RIGHT)
        add_list_dv(ws, f"B{A1}:B{AN}", R(S_SET, "Y", 12, 16))
        section(ws, T, 8, 6, 8, "LIABILITIES", color=C_EXP)
        self.head(ws, 9, 6, ["Type", "Name", "Balance"])
        ws["F10"], ws["G10"] = "Credit cards", "Credit-card debts (Debt Calculator, auto)"
        ws["H10"] = f'=SUMIFS({DC("E")},{DC("C")},"Credit card",{DC("B")},"?*")'
        ws["F11"], ws["G11"] = "Loans", "Other debts (Debt Calculator, auto)"
        ws["H11"] = f'=SUMIFS({DC("E")},{DC("C")},"<>Credit card",{DC("B")},"?*")'
        self.calc(S, "F10:G11")
        self.calc(S, "H10:H11", FMT_M, RIGHT, C_EXP, True)
        L1, LN = 12, 26
        for i in range(LN - L1 + 1):
            r = L1 + i
            if self.demo and i < len(SD.NET_WORTH_LIABS):
                ws[f"F{r}"], ws[f"G{r}"], ws[f"H{r}"] = SD.NET_WORTH_LIABS[i]
            self.inp(S, f"F{r}:G{r}")
            self.inp(S, f"H{r}", FMT_M, RIGHT)
        add_list_dv(ws, f"F{L1}:F{LN}", R(S_SET, "Y", 19, 21))
        for r in range(10, 27):
            ws.row_dimensions[r].height = 19
        # summary
        section(ws, T, 8, 10, 11, "SUMMARY", color=NAVY)
        items = ["Cash", "Bank accounts", "Investments", "Property", "Other assets"]
        for k, it in enumerate(items):
            r = 9 + k
            ws[f"J{r}"] = it
            ws[f"K{r}"] = f'=SUMIFS($D$10:$D${AN},$B$10:$B${AN},J{r})'
        for k, it in enumerate(["Credit cards", "Loans", "Other liabilities"]):
            r = 20 + k
            ws[f"J{r}"] = it
            ws[f"K{r}"] = f'=SUMIFS($H$10:$H${LN},$F$10:$F${LN},J{r})'
        ws["J19"], ws["K19"] = "Total assets", "=SUM(K9:K13)"
        ws["J24"], ws["K24"] = "Total liabilities", "=SUM(K20:K22)"
        ws["J25"], ws["K25"] = "NET WORTH", "=K19-K24"
        for r in list(range(9, 14)) + list(range(20, 23)):
            paint(ws, f"J{r}", f=FILL_WHITE, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
            self.calc(S, f"K{r}", FMT_M, RIGHT)
        for r, col in ((19, C_INC), (24, C_EXP), (25, NAVY)):
            paint(ws, f"J{r}", f=FILL_WHITE, font=T.font(10, True, col), border=_C.CELL_BOX, align=LEFT)
            self.calc(S, f"K{r}", FMT_M, RIGHT, col, True)
        for r in (14, 15, 16, 17, 18, 23):
            ws[f"J{r}"].fill = FILL_WHITE
        ws["J15"] = "Liabilities"
        ws["J15"].font = T.font(9, True, SECONDARY)
        cf_formula(ws, "K25", "K25<0", EXP_BG, C_EXP, True)
        # history
        hr = 29
        section(ws, T, hr, 2, 8, "NET WORTH HISTORY  —  copy the totals here at each month end", color=C_GOAL)
        self.head(ws, hr + 1, 2, ["Month", "Total assets", "Total liabilities"])
        self.head(ws, hr + 1, 6, [("Net worth", 2), "Change"])
        ws[f"E{hr + 1}"].fill = FILL_WHITE
        for k in range(12):
            r = hr + 2 + k
            ws[f"B{r}"] = f'=TEXT(EDATE({P0},{k}),"mmm yyyy")'
            paint(ws, f"B{r}", f=FILL_WHITE, font=T.font(10, True), border=_C.CELL_BOX, align=LEFT)
            self.inp(S, f"C{r}:D{r}", FMT_M, RIGHT)
            self.merge(ws, f"F{r}:G{r}", f'=IF(AND(C{r}="",D{r}=""),"",N(C{r})-N(D{r}))')
            self.calc(S, f"F{r}:G{r}", FMT_M, RIGHT, NAVY, True)
            ws[f"H{r}"] = '=""' if k == 0 else f'=IF(OR(F{r}="",F{r - 1}=""),"",F{r}-F{r - 1})'
            self.calc(S, f"H{r}", FMT_M, RIGHT)
            ws.row_dimensions[r].height = 19
        if self.demo:
            for m, a, l_ in SD.NET_WORTH_HISTORY:
                r = hr + 1 + m
                ws[f"C{r}"], ws[f"D{r}"] = a, l_
        cf_formula(ws, f"H{hr + 2}:H{hr + 13}", f"AND(ISNUMBER(H{hr + 2}),H{hr + 2}<0)", EXP_BG, C_EXP, True)
        cf_formula(ws, f"H{hr + 2}:H{hr + 13}", f"AND(ISNUMBER(H{hr + 2}),H{hr + 2}>0)", INC_BG, C_INC, True)
        section(ws, T, hr, 10, 13, "TREND")
        ln = BarChart()
        ln.type = "col"
        ln.add_data(Reference(ws, min_col=6, min_row=hr + 1, max_row=hr + 13), titles_from_data=True)
        ln.set_categories(Reference(ws, min_col=2, min_row=hr + 2, max_row=hr + 13))
        self.chart_style(ln, None, [NAVY], legend=False)
        ln.y_axis.majorGridlines = None
        ln.x_axis.delete = ln.y_axis.delete = False
        place_chart(ws, ln, 10, hr + 1, 13, hr + 13)
        ws.freeze_panes = "A8"
        skin(ws, 13, hr + 14, cards=[(2, 8, 4, AN), (6, 8, 8, LN), (10, 8, 11, 25), (2, hr, 8, hr + 13), (10, hr, 13, hr + 13)],
             hide_headers=True)

    # ================================================================ 27 INVESTMENT FORECAST
    def build_if(self):
        ws, T, S = self.ws[S_IF], self.T, S_IF
        setup_sheet(ws, {"B": 28, "C": 15, "D": 3, "E": 12, "F": 15, "G": 15, "H": 15, "I": 15, "J": 3, "K": 10, "L": 15, "M": 15, "N": 15})
        self.title(ws, "INVESTMENT FORECAST", "A configurable projection of how regular investing could grow. Hypothetical — not a guarantee.", 14)
        ws.row_dimensions[4].height = 10
        section(ws, T, 5, 2, 3, "YOUR ASSUMPTIONS", color=C_GOAL)
        p0, c, fr, rr, yrs, inf = SD.INVEST
        inputs = [("Initial investment", p0 if self.demo else 1000, FMT_M), ("Contribution amount", c if self.demo else 100, FMT_M),
                  ("Contribution frequency", fr, None), ("Annual return (assumed)", rr, "0.0%"),
                  ("Investment period (years)", yrs, "0"), ("Inflation (optional)", inf if self.demo else 0, "0.0%")]
        for k, (lab, v, nf) in enumerate(inputs):
            r = 6 + k
            self.label(ws, f"B{r}", lab)
            ws[f"B{r}"].border = _C.CELL_BOX
            ws[f"C{r}"] = v
            self.inp(S, f"C{r}", nf, CENTER)
            ws.row_dimensions[r].height = 21
        add_list_dv(ws, "C8", '"Monthly,Quarterly,Annually"')
        add_dv(ws, "C9", "decimal", "between", "-0.5", "0.5", error="Annual return between -50% and 50%.")
        add_dv(ws, "C10", "whole", "between", "1", "50", error="Investment period: 1 to 50 years.")
        add_dv(ws, "C11", "decimal", "between", "0", "0.2")
        add_dv(ws, "C6:C7", "decimal", "greaterThanOrEqual", "0")
        ws["P6"] = '=IF(C8="Monthly",12,IF(C8="Quarterly",4,1))'
        ws["P7"] = "=C9/P6"
        ws["O6"], ws["O7"] = "periods/yr", "rate/period"
        ws.column_dimensions["O"].hidden = ws.column_dimensions["P"].hidden = True
        fv = lambda n: (f"IF($P$7=0,$C$6+$C$7*$P$6*{n},$C$6*(1+$P$7)^($P$6*{n})+$C$7*((1+$P$7)^($P$6*{n})-1)/$P$7)")
        contrib = lambda n: f"($C$6+$C$7*$P$6*{n})"
        c_ = self.merge(ws, "B13:C16", "HYPOTHETICAL PROJECTION — NOT A GUARANTEE. Returns are assumed constant, contributions are made at the "
                                      "end of each period, and taxes and fees are ignored. Real markets go up and down; you could get back less "
                                      "than you invest. This is not financial advice.")
        paint(ws, "B13:C16", f=fill(GOAL_BG))
        c_.font = T.font(9, True, "4B3A8C")
        c_.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        self.tiles(ws, 5, [("ESTIMATED FUTURE VALUE", "=" + fv("$C$10"), FMT_M0, C_GOAL, C_GOAL),
                           ("TOTAL CONTRIBUTED", "=" + contrib("$C$10"), FMT_M0, C_SAV)], c1=5, width=2)
        self.tiles(ws, 8, [("ESTIMATED GROWTH", f"={fv('$C$10')}-{contrib('$C$10')}", FMT_M0, C_INC, C_INC),
                           ("IN TODAY'S MONEY", f"={fv('$C$10')}/(1+$C$11)^$C$10", FMT_M0, NAVY)], c1=5, width=2)
        ws["I5"] = None
        # checkpoint table (10 rows) for the chart
        section(ws, T, 11, 5, 9, "GROWTH CHECKPOINTS  (10 steps across your period)", color=C_GOAL)
        self.head(ws, 12, 5, ["Year", "Contributed", "Growth", "Balance", "Today's money"])
        for k in range(1, 11):
            r = 12 + k
            n = f"($C$10*{k}/10)"
            ws[f"E{r}"] = f'="Yr "&TEXT({n},"0.#")'
            ws[f"F{r}"] = f"={contrib(n)}"
            ws[f"H{r}"] = f"={fv(n)}"
            ws[f"G{r}"] = f"=H{r}-F{r}"
            ws[f"I{r}"] = f"=H{r}/(1+$C$11)^{n}"
            self.calc(S, f"E{r}", None, CENTER)
            self.calc(S, f"F{r}:I{r}", FMT_M0, RIGHT)
            ws.row_dimensions[r].height = 19
        section(ws, T, 24, 2, 9, "PROJECTED GROWTH")
        for rr_ in range(25, 41):
            ws.row_dimensions[rr_].height = 18
        ch = BarChart()
        ch.type = "col"
        ch.grouping = "stacked"
        ch.overlap = 100
        ch.add_data(Reference(ws, min_col=6, min_row=12, max_row=22), titles_from_data=True)
        ch.add_data(Reference(ws, min_col=7, min_row=12, max_row=22), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=5, min_row=13, max_row=22))
        self.chart_style(ch, None, [C_SAV, C_GOAL])
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = ch.y_axis.delete = False
        place_chart(ws, ch, 2, 25, 9, 40)
        # full table
        section(ws, T, 5, 11, 14, "YEAR BY YEAR", color=C_GOAL)
        self.head(ws, 6, 11, ["Year", "Contributed", "Balance", "Today's money"])
        for y in range(1, 51):
            r = 6 + y
            ws[f"K{r}"] = f'=IF({y}>$C$10,"",{y})'
            ws[f"L{r}"] = f'=IF(K{r}="","",{contrib(y)})'
            ws[f"M{r}"] = f'=IF(K{r}="","",{fv(y)})'
            ws[f"N{r}"] = f'=IF(K{r}="","",M{r}/(1+$C$11)^{y})'
            self.calc(S, f"K{r}", "0", CENTER)
            self.calc(S, f"L{r}:N{r}", FMT_M0, RIGHT)
        ws.freeze_panes = "A5"
        skin(ws, 14, 57, cards=[(2, 5, 3, 11), (2, 13, 3, 16), (5, 11, 9, 22), (2, 24, 9, 40), (11, 5, 14, 56)], hide_headers=True)

    # ================================================================ 28 NO-SPENDING CHALLENGE
    def build_ns(self):
        ws, T, S = self.ws[S_NS], self.T, S_NS
        setup_sheet(ws, {"B": 10, "C": 13, "D": 15, "E": 26, "F": 14, "G": 15, "H": 3, **{L(c): 6.2 for c in range(9, 19)}, "S": 8})
        self.title(ws, "NO-SPENDING CHALLENGE", "Pick a start date and length, then mark each day. Exceptions (like groceries) don't break your streak.", 18)
        nm, start, dur, daily, statuses = SD.CHALLENGE
        ws.row_dimensions[4].height = 10
        section(ws, T, 5, 2, 7, "YOUR CHALLENGE", color=C_GOAL)
        ins = [("Challenge name", nm if self.demo else "My no-spend challenge", None, "C6:E6"),
               ("Start date", start if self.demo else None, FMT_DATE, "C7:D7"),
               ("Duration (days)", dur, "0", "C8:D8"),
               ("Typical daily spending on wants", daily if self.demo else 20, FMT_M, "C9:D9")]
        for k, (lab, v, nf, a) in enumerate(ins):
            r = 6 + k
            self.merge(ws, a, v)
            self.inp(S, a, nf, CENTER if nf else LEFT)
            ws[f"F{r}"] = None
            ws.row_dimensions[r].height = 21
        for k, lab in enumerate(["Name", "Start", "Days", "Per day"]):
            self.label(ws, f"B{6 + k}", lab, 9, True, SECONDARY)
        self.label(ws, "E7", "End date", 9, True, SECONDARY, RIGHT)
        ws["F7"] = '=IF(C7="","",C7+C8-1)'
        self.calc(S, "F7", FMT_DATE, CENTER)
        add_dv(ws, "C7", "date", "greaterThan", "DATE(2000,1,1)")
        add_dv(ws, "C8", "whole", "between", "1", "60", error="Duration: 1 to 60 days.")
        add_dv(ws, "C9", "decimal", "greaterThanOrEqual", "0")
        section(ws, T, 5, 9, 19 - 1, "ALLOWED EXCEPTIONS", color=LAVENDER)
        for k in range(8):
            r = 6 + (k // 2)
            c1 = 9 + (k % 2) * 5
            a = f"{L(c1)}{r}:{L(c1 + 4)}{r}"
            self.merge(ws, a, SD.EXCEPTIONS[k] if k < len(SD.EXCEPTIONS) else None)
            self.opt(S, a)
        D1, DN = 18, 77
        lg = f"$D${D1}:$D${DN}"
        self.tile(ws, 11, 2, 3, "NO-SPEND DAYS", f'=COUNTIF({lg},"✓ No spend")', "0", C_INC, color=C_INC)
        self.tile(ws, 11, 4, 4, "SPENT DAYS", f'=COUNTIF({lg},"✗ Spent")', "0", C_EXP, color=C_EXP)
        self.tile(ws, 11, 5, 5, "EXCEPTIONS", f'=COUNTIF({lg},"★ Exception")', "0", C_GOAL)
        self.tile(ws, 11, 6, 7, "MONEY SAVED (EST.)", f'=COUNTIF({lg},"✓ No spend")*N($C$9)', FMT_M0, C_SAV, color=C_SAV)
        ws.row_dimensions[13].height = 6
        logged = f'COUNTIF({lg},"?*")'
        lastrow = f"SUMPRODUCT(MAX(({lg}<>\"\")*ROW({lg})))"
        self.tile(ws, 14, 2, 3, "DAYS LOGGED", f'={logged}&" of "&N($C$8)', None, NAVY)
        self.tile(ws, 14, 4, 4, "SUCCESS", f'=IF({logged}=0,"—",(COUNTIF({lg},"✓ No spend")+COUNTIF({lg},"★ Exception"))/{logged})', FMT_PCT, C_INC)
        self.tile(ws, 14, 5, 5, "CURRENT STREAK", f'=IF({logged}=0,0,INDEX($H${D1}:$H${DN},{lastrow}-{D1 - 1}))&" days"', None, C_GOAL)
        self.tile(ws, 14, 6, 7, "LONGEST STREAK", f'=MAX($H${D1}:$H${DN})&" days"', None, C_GOAL)
        # progress grid (right)
        section(ws, T, 11, 9, 18, "PROGRESS", color=C_GOAL)
        self.merge(ws, "I12:R12", f'=IF($C$8=0,0,{logged}/$C$8)')
        self.calc(S, "I12:R12", FMT_PCT, CENTER, NAVY, True)
        cf_databar(ws, "I12:R12", C_INC)
        for k in range(60):
            r = 13 + k // 10
            c = L(9 + k % 10)
            ws[f"{c}{r}"] = f'=IF({k + 1}>$C$8,"",{k + 1})'
            ws[f"{c}{r}"].alignment = CENTER
            ws[f"{c}{r}"].font = T.font(9, True, DARK)
            ws[f"{c}{r}"].fill = FILL_WHITE
            ws[f"{c}{r}"].border = Border(left=Side(style="thin", color=WHITE), right=Side(style="thin", color=WHITE),
                                          top=Side(style="thin", color=WHITE), bottom=Side(style="thin", color=WHITE))
        grid = "I13:R18"
        st = f'INDEX($D${D1}:$D${DN},I13)'
        cf_formula(ws, grid, f'AND(ISNUMBER(I13),{st}="✓ No spend")', C_INC, WHITE, True)
        cf_formula(ws, grid, f'AND(ISNUMBER(I13),{st}="✗ Spent")', C_EXP, WHITE, True)
        cf_formula(ws, grid, f'AND(ISNUMBER(I13),{st}="★ Exception")', C_GOAL, WHITE, True)
        cf_formula(ws, grid, "ISNUMBER(I13)", "E8EEED", SECONDARY)
        for r in range(13, 19):
            ws.row_dimensions[r].height = 20 if r > 13 else ws.row_dimensions[r].height
        ws.row_dimensions[16].height = ws.row_dimensions[16].height or 20
        # daily log
        section(ws, T, D1 - 2, 2, 7, "DAILY LOG")
        self.head(ws, D1 - 1, 2, ["Day", "Date", "Status", "What I bought (if anything)", "Amount", "Wants in transactions"])
        ws[f"H{D1 - 1}"] = "streak"
        for k in range(DN - D1 + 1):
            r = D1 + k
            ws[f"B{r}"] = f'=IF({k + 1}>$C$8,"",{k + 1})'
            ws[f"C{r}"] = f'=IF(OR(B{r}="",$C$7=""),"",$C$7+{k})'
            if self.demo and k < len(statuses):
                ws[f"D{r}"] = statuses[k]
                if k in SD.CHALLENGE_NOTES:
                    ws[f"E{r}"], ws[f"F{r}"] = SD.CHALLENGE_NOTES[k]
            ws[f"G{r}"] = f'=IF(C{r}="","",SUMIFS({TR("I")},{TR("C")},C{r},{TR("L")},"Wants"))'
            prev = "0" if k == 0 else f"N(H{r - 1})"
            ws[f"H{r}"] = f'=IF(D{r}="✓ No spend",{prev}+1,IF(D{r}="★ Exception",{prev},IF(D{r}="","",0)))'
            self.calc(S, f"B{r}", "0", CENTER, SECONDARY)
            self.calc(S, f"C{r}", "ddd mmm d", CENTER)
            self.inp(S, f"D{r}", align=CENTER)
            self.inp(S, f"E{r}")
            self.inp(S, f"F{r}", FMT_M, RIGHT)
            self.calc(S, f"G{r}", FMT_M, RIGHT)
            ws.row_dimensions[r].height = 18
        add_list_dv(ws, f"D{D1}:D{DN}", R(S_SET, "X", 12, 14))
        add_dv(ws, f"F{D1}:F{DN}", "decimal", "greaterThanOrEqual", "0")
        cf_formula(ws, f"D{D1}:D{DN}", f'D{D1}="✓ No spend"', INC_BG, C_INC, True)
        cf_formula(ws, f"D{D1}:D{DN}", f'D{D1}="✗ Spent"', EXP_BG, C_EXP, True)
        cf_formula(ws, f"D{D1}:D{DN}", f'D{D1}="★ Exception"', GOAL_BG, "4B3A8C", True)
        cf_formula(ws, f"G{D1}:G{DN}", f'AND(ISNUMBER(G{D1}),G{D1}>0)', WARNING_BG, WARNING, True)
        ws.column_dimensions["H"].hidden = True
        self.note(ws, f"I{20}:R{24}", "Wants in transactions = 'Wants' spending you logged on that date in Variable Transactions — a "
                  "quick check that a ✓ day really was spend-free. Money saved = no-spend days × your typical daily spending on wants.")
        ws.freeze_panes = "A5"
        skin(ws, 18, DN + 1, cards=[(2, 5, 7, 9), (9, 5, 18, 9), (2, 11, 7, 15), (9, 11, 18, 18), (2, D1 - 2, 7, DN)], hide_headers=True)

    # ================================================================ finalize
    def add_sidebars(self):
        import io
        import sidebar
        from drawing_inject import Layer, col_px_list, row_px_list
        from openpyxl.drawing.image import Image as XLImage
        from PIL import Image as PILImage
        navnames = {n for n, _, _ in NAV}
        self.side_layers = {}
        for name in ORDER:
            ws = self.ws[name]
            ws.column_dimensions["A"].width = 9.43
            last = max(ws.max_row if name not in (S_TR, S_DC) else 80, 75)
            last = min(last, 120)
            fp = ws.freeze_panes
            ws.freeze_panes = "B1" if fp is None else ("B" + fp[1:] if fp.startswith("A") else fp)
            current = name if name in navnames else "January"
            if self.ed == "excel":
                if not ws._charts and not ws._images:
                    buf = io.BytesIO()
                    PILImage.new("RGBA", (1, 1), (0, 0, 0, 0)).save(buf, "PNG")
                    img = XLImage(io.BytesIO(buf.getvalue()))
                    img.width = img.height = 1
                    ws.add_image(img, "A1")
                lay = Layer(col_px_list(ws, 2), row_px_list(ws, last + 1), font=self.T.font_name)
                sidebar.draw(lay, current, lay.y(last + 1), nav=NAV)
                self.side_layers[name] = lay
            else:
                sidebar.cells(ws, self.T, quote, current, last, nav=NAV)

    def protect(self):
        if self.ed != "excel":
            return
        display = [S_DASH, S_AT, S_CAL, S_503, S_ED, *MONTHS, S_IF, S_NW, S_SF, S_DC, S_NS, S_SET, S_BA, S_PC]
        for name in display:
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
        areas = {S_DASH: "A1:M72", S_CAL: "A1:K39", S_SET: "A1:K71", S_AT: f"A1:V{MXN}", S_503: "A1:K36", S_ED: "A1:N40",
                 S_SF: "A1:N34", S_DC: "A1:X48", S_NW: "A1:M43", S_IF: "A1:N56", S_NS: "A1:R77", S_BA: "A1:J37",
                 S_PC: "A1:K78", S_RT: f"A1:M{RTN}", S_PAY: f"A1:J{PYN}", S_TR: "A1:J120",
                 **{m: "A1:M123" for m in MONTHS}}
        for n, a in areas.items():
            self.ws[n].print_area = a

    def build(self):
        self.build_setup()
        self.build_ba()
        self.build_rt()
        self.build_pay()
        self.build_tr()
        self.build_at()
        for i in range(1, 13):
            self.build_month(i)
        self.build_sf()
        self.build_dc()
        self.build_dash()
        self.build_cal()
        self.build_pc()
        self.build_503()
        self.build_ed()
        self.build_nw()
        self.build_if()
        self.build_ns()
        self.add_sidebars()
        self.protect()
        self.page_setup()
        first = S_DASH if self.demo else S_SET
        self.wb.active = ORDER.index(first)
        for n in ORDER:
            self.ws[n].sheet_view.tabSelected = (n == first)
        return self.wb


def main():
    from common import solidify_databars
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "dist" / "04_Ultimate_Budget_Spreadsheet"))
    ap.add_argument("--only", choices=["excel-demo"], default=None)
    a = ap.parse_args()
    out = Path(a.out)
    files = []
    for ed, folder, suffix in (("excel", "Excel", "Excel"), ("gsheets", "Google_Sheets", "GoogleSheets")):
        for demo in (True, False):
            if a.only and (ed != "excel" or not demo):
                continue
            b = Builder(ed, demo)
            wb = b.build()
            p = out / folder / f"Ultimate_Budget_Spreadsheet_{suffix}_{'DEMO' if demo else 'BLANK'}.xlsx"
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
