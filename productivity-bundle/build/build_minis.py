"""Six focused mini-products (separate Etsy listings), built from the same tested engine as the budget workbook.

  debt      Debt Payoff Calculator        Start · Debt Calculator (snowball / avalanche, 30-year schedule)
  funds     Sinking Funds Tracker         Start · Sinking Funds · Contributions
  networth  Net Worth Tracker             Start · Net Worth · Net Worth History (24 months)
  nospend   No-Spend Challenge Tracker    Start · No-Spending Challenge
  invest    Investment Growth Calculator  Start · Investment Forecast · Compare Scenarios
  habits    Habit Tracker                 Start · Year Overview · January … December

Usage: python build_minis.py [--only debt funds ...]
Writes dist/05_Mini_Products/<Product>/{Excel,Google_Sheets}/<Product>_{Excel,GoogleSheets}_{DEMO,BLANK}.xlsx
Each workbook is standalone: the budget engine's names (BudToday, PeriodStart) point at its own Start tab.
"""
from __future__ import annotations

import argparse
import calendar as cal
import datetime as dt
import random
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, Protection
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName

import build_budget as BB
from build_budget import (q, C_DEBT, C_EXP, C_GOAL, C_INC, C_SAV, EXP_BG, FMT_M, FMT_M0, GOAL_BG, INC_BG, SAV_BG, cf_databar_amt)
from common import *  # noqa: F401,F403
from common import _cells
import common as _C
import icons
import sample_data_bg as SD

ANCHOR = SD.ANCHOR
S_START = "Start"

PRODUCTS = {
    "debt": ("Debt Payoff Calculator", "Debt_Payoff_Calculator", [S_START, BB.S_DC]),
    "funds": ("Sinking Funds Tracker", "Sinking_Funds_Tracker", [S_START, "Sinking Funds", "Contributions"]),
    "networth": ("Net Worth Tracker", "Net_Worth_Tracker", [S_START, BB.S_NW, "Net Worth History"]),
    "nospend": ("No-Spend Challenge Tracker", "No_Spend_Challenge_Tracker", [S_START, BB.S_NS]),
    "invest": ("Investment Growth Calculator", "Investment_Growth_Calculator", [S_START, BB.S_IF, "Compare Scenarios"]),
    "habits": ("Habit Tracker", "Habit_Tracker", [S_START, "Year Overview", *BB.MONTHS]),
}
ICON = {S_START: "gear", BB.S_DC: "card", "Sinking Funds": "piggy", "Contributions": "table", BB.S_NW: "scale",
        "Net Worth History": "trend", BB.S_NS: "ban", BB.S_IF: "trend", "Compare Scenarios": "bar_chart", "Year Overview": "bar_chart"}
SHORT = {S_START: "Start", BB.S_DC: "Debts", "Sinking Funds": "Funds", "Contributions": "Log", BB.S_NW: "Worth",
         "Net Worth History": "History", BB.S_NS: "Days", BB.S_IF: "Forecast", "Compare Scenarios": "Compare", "Year Overview": "Year"}

# ---------------------------------------------------------------- demo data for the minis
DEBTS = [("Visa card", 4200, 3650, 22.9, 95, 50, "Credit card"), ("Store card", 900, 640, 26.9, 35, 0, "Credit card"),
         ("Car loan", 16000, 11200, 6.9, 330, 0, "Loan"), ("Student loan", 21000, 17800, 4.9, 210, 0, "Loan"),
         ("Personal loan", 5000, 2900, 11.5, 150, 0, "Loan")]
EXTRA = 150
FUNDS = [("Emergency fund", 10000, 3000, 300, dt.date(2027, 12, 31), "High-yield savings"),
         ("Vacation 2027", 3000, 400, 200, dt.date(2027, 6, 30), "Savings account"),
         ("Car repairs", 1500, 300, 75, dt.date(2027, 3, 31), "Savings account"),
         ("Holiday gifts", 800, 0, 70, dt.date(2026, 12, 1), "Checking"),
         ("New laptop", 1600, 200, 100, dt.date(2027, 4, 30), "Savings account"),
         ("Annual insurance", 900, 150, 75, dt.date(2027, 1, 15), "Savings account")]


def fund_log():
    out = []
    for m in range(1, 11):
        for name, _t, _s, monthly, _d, _w in FUNDS:
            out.append((dt.date(2026, m, 1 if name != "Holiday gifts" else 15), name, "Deposit", float(monthly), "Monthly transfer"))
    out.append((dt.date(2026, 11, 1), "Emergency fund", "Deposit", 300.0, "Monthly transfer"))
    out.append((dt.date(2026, 4, 18), "Car repairs", "Withdrawal", 420.0, "New tyres"))
    out.append((dt.date(2026, 8, 9), "Vacation 2027", "Deposit", 250.0, "Birthday money"))
    out.append((dt.date(2026, 9, 2), "Annual insurance", "Withdrawal", 640.0, "Home insurance renewal"))
    out.append((dt.date(2026, 6, 30), "Emergency fund", "Deposit", 500.0, "Tax refund"))
    out.sort(key=lambda t: t[0])
    return out


NW_ASSETS = [("Cash", "Wallet & emergency cash", 300), ("Bank accounts", "Checking", 3850), ("Bank accounts", "High-yield savings", 12600),
             ("Investments", "401(k)", 41200), ("Investments", "Roth IRA", 13900), ("Investments", "Brokerage", 6300),
             ("Property", "Home (estimated value)", 365000), ("Other assets", "Car (estimated value)", 14500)]
NW_LIABS = [("Loans", "Mortgage", 286400), ("Loans", "Car loan", 9800), ("Credit cards", "Visa card (statement)", 1240),
            ("Loans", "Student loan", 15200)]


def nw_history():
    out, a, l_ = [], 430000.0, 330000.0
    r = random.Random(77)
    for k in range(22):
        d = dt.date(2025 + (k // 12), k % 12 + 1, 1)
        a += r.uniform(600, 2600)
        l_ -= r.uniform(900, 1400)
        out.append((d, round(a, -1), round(l_, -1)))
    return out


CHALLENGE = ("30-day no-spend challenge", dt.date(2026, 10, 20), 30, 22.0,
             ["✓ No spend", "✓ No spend", "★ Exception", "✓ No spend", "✓ No spend", "✗ Spent", "✓ No spend", "✓ No spend",
              "✓ No spend", "★ Exception", "✓ No spend", "✓ No spend", "✓ No spend", "✓ No spend", "✗ Spent", "✓ No spend",
              "✓ No spend", "★ Exception", "✓ No spend"])
CH_NOTES = {2: ("Groceries (allowed)", 71.40), 5: ("Coffee & pastry", 8.75), 9: ("Fuel (allowed)", 48.00), 14: ("Concert ticket", 45.00),
            17: ("Pharmacy (allowed)", 12.30)}
HABITS = ["Drink 8 glasses of water", "Exercise 30 minutes", "Read 20 pages", "Meditate 10 minutes", "No sugar", "Sleep by 11 pm",
          "Journal", "Practise Spanish"]
HABIT_P = [0.85, 0.6, 0.7, 0.55, 0.45, 0.65, 0.5, 0.6]


def habit_marks(month):
    """Demo ✓/✗ marks for a month of 2026 up to ANCHOR: list[habit][day] -> '✓' | '✗' | None."""
    r = random.Random(500 + month)
    days = cal.monthrange(2026, month)[1]
    out = []
    for h, p in enumerate(HABIT_P):
        trend = 0.08 * (month - 5) / 5
        row = []
        for d in range(1, days + 1):
            if dt.date(2026, month, d) > ANCHOR:
                row.append(None)
            else:
                row.append("✓" if r.random() < min(0.97, p + trend) else ("✗" if r.random() < 0.6 else None))
        out.append(row)
    return out


class Mini(BB.Builder):
    def __init__(self, key, edition, demo):
        self.key, self.ed, self.demo = key, edition, demo
        self.name, self.slug, self.order = PRODUCTS[key]
        self.T = Theme(edition)
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in self.order}
        for n in self.order:
            self.ws[n].sheet_properties.tabColor = LAVENDER if n == S_START else (BLUE if n in BB.MONTHS else NAVY)
        self.unlocked = {n: [] for n in self.order}
        _C.TAB_ORDER[:] = self.order
        self.nav = []
        for i, n in enumerate(self.order):
            if n in BB.MONTHS:
                self.nav.append((n, icons.week_num(BB.MONTHS.index(n) + 1), n[:3]))
            else:
                self.nav.append((n, ICON[n], SHORT[n]))

    def title(self, ws, title, sub, last_col, home=S_START, label="⌂ Start"):
        title_bar(ws, self.T, title, sub, last_col, home_link=home, home_label=label, demo=self.demo)

    # ------------------------------------------------------------ Start tab (every mini)
    def build_start(self, welcome, settings, tips, extra=None):
        """settings: list of (label, value, kind, hint, name) — kind: text/date/int/pct/money/year/calc; name = defined name or None."""
        ws, T, S = self.ws[S_START], self.T, S_START
        setup_sheet(ws, {"B": 32, "C": 20, "D": 16, "E": 16, "F": 9, "G": 9, "H": 24, "I": 18, "J": 18, "K": 18})
        title_bar(ws, T, f"{self.name.upper()}  ·  Start here", "Settings, instructions and help. Everything else updates from your entries.",
                  11, home_link=None, demo=self.demo)
        c = self.merge(ws, "B5:K7", welcome + ("   This copy contains DEMO DATA — use the BLANK file to start fresh." if self.demo else ""))
        paint(ws, "B5:K7", f=fill(SOFT_BLUE))
        c.font = T.font(10, False, MIDNIGHT)
        c.alignment = LEFT_WRAP
        for r in (5, 6, 7):
            ws.row_dimensions[r].height = 20
        ws.row_dimensions[4].height = 12
        legend(ws, T, 8, 2)
        ws.row_dimensions[8].height = 24
        section(ws, T, 9, 2, 5, "SETTINGS")
        base = [("Today's date override", ANCHOR if self.demo else None, "date",
                 "DEMO date — clear it to use today" if self.demo else "Leave blank to use the real date", None),
                ("Effective today", '=IF(C10="",TODAY(),C10)', "calcd", "Drives every 'today' calculation", BB.TODAY)]
        rows = base + settings
        for i, (lab, val, kind, hint, name) in enumerate(rows):
            r = 10 + i
            self.label(ws, f"B{r}", lab)
            ws[f"C{r}"] = val
            if kind.startswith("calc"):
                self.calc(S, f"C{r}", {"calcd": FMT_DATE, "calcp": FMT_PCT}.get(kind), CENTER)
            else:
                self.inp(S, f"C{r}", {"date": FMT_DATE, "int": "0", "pct": FMT_PCT, "money": FMT_M, "year": "0"}.get(kind), CENTER)
            if kind == "date":
                add_dv(ws, f"C{r}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a valid date, or leave blank.")
            self.note(ws, f"D{r}:E{r}", hint)
            ws.row_dimensions[r].height = 21
            if name:
                self.wb.defined_names[name] = DefinedName(name, attr_text=f"{q(S)}!$C${r}")
        last = 10 + len(rows) - 1
        section(ws, T, 9, 8, 11, "HOW TO USE", color=LAVENDER)
        for i, t in enumerate(tips):
            r = 10 + i
            c = self.merge(ws, f"H{r}:K{r}", f"{i + 1}.  {t}")
            c.font = T.font(10)
            c.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
            ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 15, 30)
        tip_end = 10 + len(tips) - 1
        end = max(last, tip_end)
        cards = [(2, 9, 5, last), (8, 9, 11, tip_end)]
        r0 = end + 2
        if extra:
            r0, card = extra(ws, r0)
            cards.append(card)
            r0 += 2
        section(ws, T, r0, 2, 11, "GO TO", color=NAVY)
        slots = ["B{r}", "C{r}:E{r}", "H{r}:I{r}", "J{r}:K{r}"]
        for i, n in enumerate(self.order[1:]):
            rr = r0 + 1 + i // 4
            a = slots[i % 4].format(r=rr)
            self.merge(ws, a, f'=HYPERLINK("#{quote(n)}!A1","{n}  ›")')
            paint(ws, a, f=fill(SOFT_BLUE), font=T.font(10, True, MIDNIGHT), align=CENTER,
                  border=Border(left=Side(style="thin", color=WHITE), right=Side(style="thin", color=WHITE)))
            ws.row_dimensions[rr].height = 24
        gend = r0 + 1 + (len(self.order) - 2) // 4
        cards.append((2, r0, 11, gend))
        r1 = gend + 2
        section(ws, T, r1, 2, 11, "WANT THE COMPLETE SYSTEM?", color=C_GOAL)
        c = self.merge(ws, f"B{r1 + 1}:K{r1 + 2}",
                       "This tracker is also part of the Ultimate Budget Spreadsheet (28 tabs): budgets, dashboards, recurring bills, "
                       "a financial calendar, debt payoff, sinking funds, net worth and more — all connected. Look for it in the same shop.")
        c.font = T.font(10, False, DARK)
        c.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        ws.row_dimensions[r1 + 1].height = ws.row_dimensions[r1 + 2].height = 20
        ws.freeze_panes = "A4"
        skin(ws, 11, r1 + 3, cards=cards + [(2, r1, 11, r1 + 2)], hide_headers=True)
        return last

    def fix_dv(self, ws, contains, literal):
        for dv in ws.data_validations.dataValidation:
            if contains in str(dv.formula1):
                dv.formula1 = literal

    # ------------------------------------------------------------ products
    def make_debt(self):
        self.build_start("DEBT PAYOFF CALCULATOR.   1) Go to Debt Calculator and list each debt: current balance, interest rate (APR), "
                         "minimum payment and any extra you already pay.   2) Choose Snowball or Avalanche and how much extra you can add "
                         "each month.   3) See your debt-free date, each debt's payoff month, the interest you'll pay and the full "
                         "month-by-month schedule.",
                         [], ["List every debt with its current balance from your latest statement.",
                              "Snowball pays the smallest balance first (quick wins); Avalanche pays the highest interest first (least interest).",
                              "Add an 'extra per month' amount — even small amounts move your debt-free date.",
                              "Update the current balances every month or two to keep the plan accurate."])
        saved = (SD.DEBTS, SD.EXTRA_DEBT)
        SD.DEBTS, SD.EXTRA_DEBT = DEBTS, EXTRA
        try:
            self.build_dc()
        finally:
            SD.DEBTS, SD.EXTRA_DEBT = saved
        ws = self.ws[BB.S_DC]
        ws["M8"] = "Interest / month"
        for r in range(BB.DC1, BB.DCN + 1):
            ws[f"M{r}"] = f'=IF(B{r}="","",N(E{r})*N(F{r})/12)'
        self.fix_dv(ws, "Easy Setup", '"Credit card,Loan,Mortgage,Other"')

    def make_nospend(self):
        self.build_start("NO-SPEND CHALLENGE TRACKER.   1) Name your challenge, pick a start date and length (up to 60 days) and how much "
                         "you'd normally spend on 'wants' each day.   2) List the exceptions you allow (groceries, bills…).   3) Mark each "
                         "day: ✓ No spend, ✗ Spent or ★ Exception. Your streak, success rate and money saved update automatically.",
                         [], ["Exceptions don't break your streak — they're the essentials you decided to allow.",
                              "Be honest with ✗ days: the tracker is for you.",
                              "Money saved = no-spend days × your typical daily spending on wants.",
                              "When a challenge ends, change the start date to begin the next one (clear the log first)."])
        saved = (SD.CHALLENGE, SD.CHALLENGE_NOTES)
        SD.CHALLENGE, SD.CHALLENGE_NOTES = CHALLENGE, CH_NOTES
        try:
            self.build_ns()
        finally:
            SD.CHALLENGE, SD.CHALLENGE_NOTES = saved
        ws = self.ws[BB.S_NS]
        ws["G17"] = "Saved so far"
        for r in range(18, 78):
            ws[f"G{r}"] = f'=IF(C{r}="","",COUNTIF($D$18:D{r},"✓ No spend")*N($C$9))'
        self.fix_dv(ws, "Easy Setup", '"✓ No spend,✗ Spent,★ Exception"')
        del ws.conditional_formatting["G18:G77"]
        cf_databar_amt(ws, "G18:G77", C_SAV)
        ws["I20"].value = ("Saved so far = no-spend days up to that day × your typical daily spending on wants. "
                           "Tip: start a new challenge by changing the start date and clearing the Status column.")

    def make_invest(self):
        self.build_start("INVESTMENT GROWTH CALCULATOR.   1) On Investment Forecast, enter your starting amount, regular contribution, "
                         "how often you contribute, an assumed yearly return and how many years.   2) See the estimated future value, "
                         "what you put in and the growth.   3) Compare Scenarios shows three return assumptions side by side. "
                         "All results are hypothetical projections, not guarantees.",
                         [], ["Use a conservative return assumption — markets go up and down.",
                              "Inflation turns future money into today's money so the numbers feel real.",
                              "Contributions are assumed at the end of each period; taxes and fees are ignored.",
                              "This is an educational planning tool, not financial advice."])
        self.build_if()
        ws, T, S = self.ws["Compare Scenarios"], self.T, "Compare Scenarios"
        setup_sheet(ws, {"B": 26, "C": 15, "D": 15, "E": 15, "F": 3, "G": 10, "H": 15, "I": 15, "J": 15})
        self.title(ws, "COMPARE SCENARIOS", "Same contributions, three return assumptions. Hypothetical projections — not guarantees.", 10)
        fs = q(BB.S_IF)
        section(ws, T, 5, 2, 5, "SCENARIOS", color=C_GOAL)
        self.head(ws, 6, 2, ["", "Conservative", "Moderate", "Optimistic"])
        for k, (lab, vals, nf) in enumerate((("Annual return (assumed)", (0.04, 0.06, 0.08), "0.0%"),)):
            r = 7
            self.label(ws, f"B{r}", lab)
            for j, v in enumerate(vals):
                ws[f"{'CDE'[j]}{r}"] = v
            self.inp(S, f"C{r}:E{r}", nf, CENTER)
        add_dv(ws, "C7:E7", "decimal", "between", "-0.5", "0.5")
        shared = [("Initial investment", f"={fs}!$C$6", FMT_M), ("Contribution", f"={fs}!$C$7", FMT_M),
                  ("Frequency", f"={fs}!$C$8", None), ("Years", f"={fs}!$C$10", "0")]
        for k, (lab, f, nf) in enumerate(shared):
            r = 8 + k
            self.label(ws, f"B{r}", lab)
            self.merge(ws, f"C{r}:E{r}", f)
            self.calc(S, f"C{r}:E{r}", nf, CENTER)
        self.note(ws, "B12:E12", "Initial amount, contribution, frequency and years come from Investment Forecast.")
        ws["L6"] = f'=IF({fs}!$C$8="Monthly",12,IF({fs}!$C$8="Quarterly",4,1))'
        ws.column_dimensions["L"].hidden = True
        fv = lambda col, n: (f"IF({col}$7=0,$C$8+$C$9*$L$6*{n},$C$8*(1+{col}$7/$L$6)^($L$6*{n})+$C$9*((1+{col}$7/$L$6)^($L$6*{n})-1)/({col}$7/$L$6))")
        r = 13
        self.label(ws, f"B{r}", "Estimated future value", 10, True, NAVY)
        for col in "CDE":
            ws[f"{col}{r}"] = "=" + fv(col, "$C$11")
        self.calc(S, f"C{r}:E{r}", FMT_M0, CENTER, C_GOAL, True)
        self.label(ws, "B14", "Total contributed")
        ws["C14"] = "=$C$8+$C$9*$L$6*$C$11"
        self.merge(ws, "C14:E14")
        self.calc(S, "C14:E14", FMT_M0, CENTER)
        self.label(ws, "B15", "Estimated growth")
        for col in "CDE":
            ws[f"{col}15"] = f"={col}13-$C$14"
        self.calc(S, "C15:E15", FMT_M0, CENTER, C_INC, True)
        for rr in range(7, 16):
            ws.row_dimensions[rr].height = 21
        c_ = self.merge(ws, "B17:E19", "HYPOTHETICAL PROJECTIONS — NOT A GUARANTEE. Constant returns are assumed; real returns vary and can be "
                                      "negative. Taxes and fees are ignored. Not financial advice.")
        paint(ws, "B17:E19", f=fill(GOAL_BG))
        c_.font = T.font(9, True, "4B3A8C")
        c_.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        section(ws, T, 5, 7, 10, "CHECKPOINTS", color=C_GOAL)
        self.head(ws, 6, 7, ["Year", "Conservative", "Moderate", "Optimistic"])
        for k in range(1, 11):
            r = 6 + k
            n = f"($C$11*{k}/10)"
            ws[f"G{r}"] = f'="Yr "&TEXT({n},"0.#")'
            for j, col in enumerate("CDE"):
                ws[f"{'HIJ'[j]}{r}"] = "=" + fv(col, n)
            self.calc(S, f"G{r}", None, CENTER)
            self.calc(S, f"H{r}:J{r}", FMT_M0, RIGHT)
        section(ws, T, 21, 2, 10, "GROWTH UNDER EACH SCENARIO")
        for rr in range(22, 38):
            ws.row_dimensions[rr].height = 18
        ln = LineChart()
        for col in (8, 9, 10):
            ln.add_data(Reference(ws, min_col=col, min_row=6, max_row=16), titles_from_data=True)
        ln.set_categories(Reference(ws, min_col=7, min_row=7, max_row=16))
        self.chart_style(ln, None, [C_SAV, C_GOAL, C_INC])
        for s_ in ln.series:
            s_.smooth = False
        ln.x_axis.delete = ln.y_axis.delete = False
        place_chart(ws, ln, 2, 22, 10, 37)
        ws.freeze_panes = "A5"
        skin(ws, 10, 38, cards=[(2, 5, 5, 15), (2, 17, 5, 19), (7, 5, 10, 16), (2, 21, 10, 37)], hide_headers=True)

    def make_networth(self):
        self.build_start("NET WORTH TRACKER.   1) On Net Worth, list what you own (cash, bank accounts, investments, property, other) and "
                         "what you owe (credit cards, loans, other).   2) Your totals, net worth and debt-to-asset ratio calculate "
                         "automatically.   3) Once a month, copy the totals into Net Worth History to watch your progress over 24 months.",
                         [], ["Use current values: statement balances and realistic estimates for property and vehicles.",
                              "Update once a month — the same day each month works best.",
                              "Net worth history: type the first month, the rest of the dates fill in.",
                              "A rising line matters more than the number itself."])
        ws, T, S = self.ws[BB.S_NW], self.T, BB.S_NW
        setup_sheet(ws, {"B": 18, "C": 34, "D": 15, "E": 3, "F": 18, "G": 34, "H": 15, "I": 3, "J": 20, "K": 15})
        self.title(ws, "NET WORTH", "What you own minus what you owe — updated whenever you change a value.", 11)
        self.tiles(ws, 5, [("TOTAL ASSETS", "=$K$19", FMT_M0, C_INC, C_INC), ("TOTAL LIABILITIES", "=$K$24", FMT_M0, C_EXP, C_EXP),
                           ("NET WORTH", "=$K$25", FMT_M0, NAVY), ("DEBT-TO-ASSET", '=IF($K$19=0,"—",$K$24/$K$19)', FMT_PCT, C_GOAL)],
                   c1=2, width=2)
        cf_formula(ws, "F6", "AND(ISNUMBER(F6),F6<0)", EXP_BG, C_EXP, True)
        ws.row_dimensions[7].height = 10
        A1, AN, L1, LN = 10, 29, 10, 29
        section(ws, T, 8, 2, 4, "ASSETS", color=C_INC)
        self.head(ws, 9, 2, ["Type", "Name", "Value"])
        section(ws, T, 8, 6, 8, "LIABILITIES", color=C_EXP)
        self.head(ws, 9, 6, ["Type", "Name", "Balance"])
        for i in range(AN - A1 + 1):
            r = A1 + i
            if self.demo and i < len(NW_ASSETS):
                ws[f"B{r}"], ws[f"C{r}"], ws[f"D{r}"] = NW_ASSETS[i]
            if self.demo and i < len(NW_LIABS):
                ws[f"F{r}"], ws[f"G{r}"], ws[f"H{r}"] = NW_LIABS[i]
            self.inp(S, f"B{r}:C{r}")
            self.inp(S, f"D{r}", FMT_M, RIGHT)
            self.inp(S, f"F{r}:G{r}")
            self.inp(S, f"H{r}", FMT_M, RIGHT)
            ws.row_dimensions[r].height = 19
        add_list_dv(ws, f"B{A1}:B{AN}", '"Cash,Bank accounts,Investments,Property,Other assets"')
        add_list_dv(ws, f"F{L1}:F{LN}", '"Credit cards,Loans,Other liabilities"')
        add_dv(ws, f"D{A1}:D{AN}", "decimal", "greaterThanOrEqual", "0")
        add_dv(ws, f"H{L1}:H{LN}", "decimal", "greaterThanOrEqual", "0")
        section(ws, T, 8, 10, 11, "SUMMARY", color=NAVY)
        for k, it in enumerate(["Cash", "Bank accounts", "Investments", "Property", "Other assets"]):
            r = 9 + k
            ws[f"J{r}"], ws[f"K{r}"] = it, f'=SUMIFS($D${A1}:$D${AN},$B${A1}:$B${AN},J{r})'
        for k, it in enumerate(["Credit cards", "Loans", "Other liabilities"]):
            r = 20 + k
            ws[f"J{r}"], ws[f"K{r}"] = it, f'=SUMIFS($H${L1}:$H${LN},$F${L1}:$F${LN},J{r})'
        ws["J19"], ws["K19"] = "Total assets", "=SUM(K9:K13)"
        ws["J24"], ws["K24"] = "Total liabilities", "=SUM(K20:K22)"
        ws["J25"], ws["K25"] = "NET WORTH", "=K19-K24"
        for r in list(range(9, 14)) + list(range(20, 23)):
            paint(ws, f"J{r}", f=FILL_WHITE, font=T.font(10), border=_C.CELL_BOX, align=LEFT)
            self.calc(S, f"K{r}", FMT_M, RIGHT)
        for r, col in ((19, C_INC), (24, C_EXP), (25, NAVY)):
            paint(ws, f"J{r}", f=FILL_WHITE, font=T.font(10, True, col), border=_C.CELL_BOX, align=LEFT)
            self.calc(S, f"K{r}", FMT_M, RIGHT, col, True)
        cf_formula(ws, "K25", "K25<0", EXP_BG, C_EXP, True)
        section(ws, T, AN + 2, 2, 11, "WHERE YOUR WEALTH IS")
        for rr in range(AN + 3, AN + 17):
            ws.row_dimensions[rr].height = 18
        ch = BarChart()
        ch.type = "bar"
        ch.add_data(Reference(ws, min_col=11, min_row=9, max_row=13), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=10, min_row=9, max_row=13))
        self.chart_style(ch, "Assets by type", [C_INC], legend=False)
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.x_axis.scaling.orientation = "maxMin"
        place_chart(ws, ch, 2, AN + 3, 6, AN + 16)
        ch2 = BarChart()
        ch2.type = "bar"
        ch2.add_data(Reference(ws, min_col=11, min_row=20, max_row=22), titles_from_data=False)
        ch2.set_categories(Reference(ws, min_col=10, min_row=20, max_row=22))
        self.chart_style(ch2, "Liabilities by type", [C_EXP], legend=False)
        ch2.y_axis.majorGridlines = None
        ch2.x_axis.delete = ch2.y_axis.delete = False
        ch2.x_axis.scaling.orientation = "maxMin"
        place_chart(ws, ch2, 7, AN + 3, 11, AN + 16)
        ws.freeze_panes = "A8"
        skin(ws, 11, AN + 17, cards=[(2, 8, 4, AN), (6, 8, 8, LN), (10, 8, 11, 25), (2, AN + 2, 11, AN + 16)], hide_headers=True)
        # history
        ws, S = self.ws["Net Worth History"], "Net Worth History"
        setup_sheet(ws, {"B": 14, "C": 16, "D": 16, "E": 16, "F": 14, "G": 11, "H": 3, **{L(c): 12 for c in range(9, 15)}})
        self.title(ws, "NET WORTH HISTORY", "One row per month — type the totals from the Net Worth tab at each month end.", 14)
        nwq = q(BB.S_NW)
        H1, HN = 9, 32
        filled = f'COUNT($E${H1}:$E${HN})'
        last_nw = f"INDEX($E${H1}:$E${HN},SUMPRODUCT(MAX(ISNUMBER($E${H1}:$E${HN})*(ROW($E${H1}:$E${HN})-{H1 - 1}))))"
        self.tiles(ws, 5, [("LATEST NET WORTH", f'=IF({filled}=0,"—",{last_nw})', FMT_M0, NAVY),
                           ("CHANGE (12 MONTHS)", f'=IF({filled}<13,"—",{last_nw}-INDEX($E${H1}:$E${HN},SUMPRODUCT(MAX(ISNUMBER($E${H1}:$E${HN})*(ROW($E${H1}:$E${HN})-{H1 - 1})))-12))', FMT_M0, C_INC),
                           ("BEST MONTH", f'=IF(COUNT($F${H1}:$F${HN})=0,"—",MAX($F${H1}:$F${HN}))', FMT_M0, C_INC),
                           ("NET WORTH TAB NOW", f"={nwq}!$K$25", FMT_M0, C_GOAL)], c1=2, width=2, gap=0)
        ws.row_dimensions[7].height = 10
        self.head(ws, 8, 2, ["Month", "Total assets", "Total liabilities", "Net worth", "Change", "% change"])
        hist = nw_history() if self.demo else []
        for k in range(HN - H1 + 1):
            r = H1 + k
            if k == 0:
                ws[f"B{r}"] = hist[0][0] if hist else f"=DATE(YEAR({BB.TODAY}),MONTH({BB.TODAY}),1)"
                self.inp(S, f"B{r}", "mmm yyyy", CENTER)
            else:
                ws[f"B{r}"] = f"=EDATE(B{r - 1},1)"
                self.calc(S, f"B{r}", "mmm yyyy", CENTER, DARK, True)
            if k < len(hist):
                ws[f"C{r}"], ws[f"D{r}"] = hist[k][1], hist[k][2]
            self.inp(S, f"C{r}:D{r}", FMT_M, RIGHT)
            ws[f"E{r}"] = f'=IF(AND(C{r}="",D{r}=""),"",N(C{r})-N(D{r}))'
            ws[f"F{r}"] = '=""' if k == 0 else f'=IF(OR(E{r}="",E{r - 1}=""),"",E{r}-E{r - 1})'
            ws[f"G{r}"] = '=""' if k == 0 else f'=IF(OR(F{r}="",N(E{r - 1})=0),"",F{r}/ABS(E{r - 1}))'
            self.calc(S, f"E{r}", FMT_M, RIGHT, NAVY, True)
            self.calc(S, f"F{r}", FMT_M, RIGHT)
            self.calc(S, f"G{r}", "0.0%", CENTER)
            ws.row_dimensions[r].height = 19
        add_dv(ws, f"B{H1}", "date", "greaterThan", "DATE(2000,1,1)")
        cf_formula(ws, f"F{H1}:G{HN}", f"AND(ISNUMBER(F{H1}),F{H1}<0)", EXP_BG, C_EXP, True)
        cf_formula(ws, f"F{H1}:G{HN}", f"AND(ISNUMBER(F{H1}),F{H1}>0)", INC_BG, C_INC, True)
        ws["P8"] = "label"
        for k in range(HN - H1 + 1):
            ws[f"P{H1 + k}"] = f'=TEXT(B{H1 + k},"mmm yy")'
        ws.column_dimensions["P"].hidden = True
        section(ws, T, 8, 9, 14, "NET WORTH OVER TIME")
        ln = BarChart()
        ln.type = "col"
        ln.add_data(Reference(ws, min_col=5, min_row=8, max_row=HN), titles_from_data=True)
        ln.set_categories(Reference(ws, min_col=16, min_row=H1, max_row=HN))
        self.chart_style(ln, None, [NAVY], legend=False)
        ln.y_axis.majorGridlines = None
        ln.x_axis.delete = ln.y_axis.delete = False
        place_chart(ws, ln, 9, 9, 14, HN)
        ws.freeze_panes = "A9"
        skin(ws, 14, HN + 1, cards=[(2, 8, 7, HN), (9, 8, 14, HN)], hide_headers=True)

    def make_funds(self):
        self.build_start("SINKING FUNDS TRACKER.   1) On Sinking Funds, add each savings goal: target amount, what's already saved, "
                         "how much you plan to add each month and the target date.   2) Log every deposit or withdrawal on Contributions.   "
                         "3) Balances, progress bars, months to go and on-track status update automatically.",
                         [("Year for the monthly summary", 2026 if self.demo else "=YEAR(TODAY())", "year", "Deposits by month on Sinking Funds", "FundYear")],
                         ["A sinking fund is money set aside for a known future cost — gifts, car repairs, insurance, travel.",
                          "Log deposits when you move money in; log withdrawals when you spend from a fund.",
                          "Status turns 'Behind' when your plan won't reach the target by the target date — it shows what's needed per month.",
                          "Keep each fund in the account you note under 'Where it's kept'."])
        ws, T, S = self.ws["Sinking Funds"], self.T, "Sinking Funds"
        widths = [22, 13, 13, 13, 12, 21, 12, 12, 13, 12, 10, 10, 12, 28]
        setup_sheet(ws, {i + 2: w for i, w in enumerate(widths)})
        self.title(ws, "SINKING FUNDS", "Savings goals with progress, months to go and on-track status. Contributions come from the log.", 15)
        F1, FN = 9, 23
        G1, GN = 9, 508
        lg = lambda c: f"{q('Contributions')}!${c}${G1}:${c}${GN}"
        t = BB.TODAY
        self.tiles(ws, 5, [("TOTAL SAVED", f"=SUM(J{F1}:J{FN})", FMT_M0, C_SAV, C_SAV), ("TOTAL TARGET", f"=SUM(C{F1}:C{FN})", FMT_M0, C_GOAL),
                           ("OVERALL PROGRESS", f'=IF(SUM(C{F1}:C{FN})=0,"—",SUM(Q{F1}:Q{FN})/SUM(C{F1}:C{FN}))', FMT_PCT, C_GOAL),
                           ("MONTHLY PLAN", f"=SUM(E{F1}:E{FN})", FMT_M0, C_SAV),
                           ("GOALS REACHED", f'=COUNTIFS(L{F1}:L{FN},">=1")&" of "&COUNTIF(B{F1}:B{FN},"?*")', None, C_INC)], c1=2, width=2)
        ws.row_dimensions[7].height = 10
        self.head(ws, 8, 2, ["Fund name", "Target", "Starting balance", "Monthly plan", "Target date", "Where it's kept", "Deposits",
                             "Withdrawals", "Balance", "Remaining", "Progress", "Months to go", "Projected", "Status"])
        for i in range(FN - F1 + 1):
            r = F1 + i
            if self.demo and i < len(FUNDS):
                for c, v in zip("BCDEFG", FUNDS[i]):
                    ws[f"{c}{r}"] = v
            self.inp(S, f"B{r}")
            self.inp(S, f"C{r}:E{r}", FMT_M, RIGHT)
            self.inp(S, f"F{r}", FMT_SDATE, CENTER)
            self.opt(S, f"G{r}")
            ws[f"H{r}"] = f'=IF(B{r}="","",SUMIFS({lg("E")},{lg("C")},B{r},{lg("D")},"Deposit"))'
            ws[f"I{r}"] = f'=IF(B{r}="","",SUMIFS({lg("E")},{lg("C")},B{r},{lg("D")},"Withdrawal"))'
            ws[f"J{r}"] = f'=IF(B{r}="","",N(D{r})+H{r}-I{r})'
            ws[f"K{r}"] = f'=IF(B{r}="","",MAX(0,N(C{r})-J{r}))'
            ws[f"L{r}"] = f'=IF(OR(B{r}="",N(C{r})=0),"",MAX(0,MIN(1,J{r}/C{r})))'
            ws[f"M{r}"] = f'=IF(B{r}="","",IF(K{r}=0,0,IF(N(E{r})<=0,"—",-INT(-K{r}/E{r}))))'
            ws[f"N{r}"] = f'=IF(OR(B{r}="",NOT(ISNUMBER(M{r}))),"",EDATE({t},M{r}))'
            need = f"K{r}/MAX(1,(YEAR(F{r})-YEAR({t}))*12+MONTH(F{r})-MONTH({t}))"
            ws[f"O{r}"] = (f'=IF(B{r}="","",IF(K{r}=0,"✓ Goal reached",IF(F{r}="","No target date",IF(F{r}<{t},"Past target date",'
                           f'IF(AND(ISNUMBER(N{r}),N{r}<=F{r}),"On track","Behind — needs "&TEXT({need},"#,##0")&"/mo")))))')
            ws[f"Q{r}"] = f'=IF(B{r}="",0,MAX(0,MIN(J{r},N(C{r}))))'
            self.calc(S, f"H{r}:K{r}", FMT_M, RIGHT)
            ws[f"J{r}"].font = T.font(10, True, C_SAV)
            self.calc(S, f"L{r}", FMT_PCT, CENTER)
            self.calc(S, f"M{r}", "0", CENTER)
            self.calc(S, f"N{r}", "mmm yyyy", CENTER)
            self.calc(S, f"O{r}", None, LEFT)
            ws.row_dimensions[r].height = 20
        ws.column_dimensions["Q"].hidden = True
        add_dv(ws, f"C{F1}:E{FN}", "decimal", "greaterThanOrEqual", "0")
        add_dv(ws, f"F{F1}:F{FN}", "date", "greaterThan", "DATE(2000,1,1)")
        cf_databar(ws, f"L{F1}:L{FN}", C_SAV)
        cf_formula(ws, f"O{F1}:O{FN}", f'LEFT(O{F1},1)="✓"', INC_BG, C_INC, True)
        cf_formula(ws, f"O{F1}:O{FN}", f'OR(LEFT(O{F1},6)="Behind",LEFT(O{F1},4)="Past")', EXP_BG, C_EXP, True)
        cf_formula(ws, f"O{F1}:O{FN}", f'O{F1}="On track"', SAV_BG, C_SAV, True)
        r = FN + 1
        self.label(ws, f"B{r}", "Total", 10, True, NAVY)
        for c in "CDEHIJK":
            ws[f"{c}{r}"] = f"=SUM({c}{F1}:{c}{FN})"
        self.calc(S, f"C{r}:K{r}", FMT_M, RIGHT, NAVY, True)
        for c in "FG":
            ws[f"{c}{r}"].value = None
        # monthly deposits + charts
        mr = r + 2
        section(ws, T, mr, 2, 5, "DEPOSITS BY MONTH", color=C_SAV)
        self.head(ws, mr + 1, 2, ["Month", "Deposits", "Withdrawals", "Net"])
        for k in range(12):
            rr = mr + 2 + k
            a = f"DATE(FundYear,{k + 1},1)"
            ws[f"B{rr}"] = f'=TEXT({a},"mmm yyyy")'
            ws[f"C{rr}"] = f'=SUMIFS({lg("E")},{lg("D")},"Deposit",{lg("B")},">="&{a},{lg("B")},"<"&EDATE({a},1))'
            ws[f"D{rr}"] = f'=SUMIFS({lg("E")},{lg("D")},"Withdrawal",{lg("B")},">="&{a},{lg("B")},"<"&EDATE({a},1))'
            ws[f"E{rr}"] = f"=C{rr}-D{rr}"
            paint(ws, f"B{rr}", f=FILL_WHITE, font=T.font(10, True), border=_C.CELL_BOX, align=LEFT)
            self.calc(S, f"C{rr}:E{rr}", FMT_M, RIGHT)
            ws.row_dimensions[rr].height = 18
        section(ws, T, mr, 7, 15, "SAVINGS PROGRESS")
        ch = BarChart()
        ch.type = "bar"
        ch.grouping = "stacked"
        ch.overlap = 100
        ch.add_data(Reference(ws, min_col=10, min_row=8, max_row=FN), titles_from_data=True)
        ch.add_data(Reference(ws, min_col=11, min_row=8, max_row=FN), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=F1, max_row=FN))
        self.chart_style(ch, None, [C_SAV, "D6E4F2"])
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = ch.y_axis.delete = False
        ch.x_axis.scaling.orientation = "maxMin"
        place_chart(ws, ch, 7, mr + 1, 15, mr + 13)
        ws.freeze_panes = "C9"
        skin(ws, 15, mr + 14, cards=[(2, 8, 15, r), (2, mr, 5, mr + 13), (7, mr, 15, mr + 13)], hide_headers=True)
        # contributions log
        ws, S = self.ws["Contributions"], "Contributions"
        setup_sheet(ws, {"B": 13, "C": 24, "D": 14, "E": 14, "F": 34})
        self.title(ws, "CONTRIBUTIONS", "Log every deposit into a fund and every withdrawal from one. Up to 500 entries.", 7)
        self.tiles(ws, 5, [("ENTRIES", f"=COUNT(B{G1}:B{GN})", "0", NAVY),
                           ("DEPOSITED", f'=SUMIFS(E{G1}:E{GN},D{G1}:D{GN},"Deposit")', FMT_M0, C_SAV, C_SAV),
                           ("WITHDRAWN", f'=SUMIFS(E{G1}:E{GN},D{G1}:D{GN},"Withdrawal")', FMT_M0, C_EXP, C_EXP)], c1=2, width=1)
        ws.row_dimensions[7].height = 10
        self.head(ws, 8, 2, ["Date", "Fund", "Type", "Amount", "Note"])
        data = fund_log() if self.demo else []
        for i in range(GN - G1 + 1):
            r = G1 + i
            if i < len(data):
                for c, v in zip("BCDEF", data[i]):
                    ws[f"{c}{r}"] = v
        style_input(ws, f"B{G1}:B{GN}", T, FMT_SDATE, CENTER)
        style_input(ws, f"C{G1}:D{GN}", T)
        style_input(ws, f"E{G1}:E{GN}", T, FMT_M, RIGHT)
        style_input(ws, f"F{G1}:F{GN}", T)
        self.unlocked[S].append(f"B{G1}:F{GN}")
        add_dv(ws, f"B{G1}:B{GN}", "date", "greaterThan", "DATE(2000,1,1)", error="Enter a date.")
        add_list_dv(ws, f"C{G1}:C{GN}", f"{q('Sinking Funds')}!$B${F1}:$B${FN}")
        add_list_dv(ws, f"D{G1}:D{GN}", '"Deposit,Withdrawal"')
        add_dv(ws, f"E{G1}:E{GN}", "decimal", "greaterThanOrEqual", "0", error="Enter a positive amount; choose Deposit or Withdrawal.")
        cf_formula(ws, f"D{G1}:E{GN}", f'$D{G1}="Withdrawal"', font_color=C_EXP, bold=True)
        cf_formula(ws, f"D{G1}:E{GN}", f'$D{G1}="Deposit"', font_color=C_SAV, bold=True)
        self.table(ws, "Contributions", f"B8:F{GN}")
        ws.freeze_panes = "A9"
        skin(ws, 7, G1 + 30, hide_headers=True)

    def make_habits(self):
        def habit_block(ws, hr):
            T, S = self.T, S_START
            section(ws, T, hr, 2, 5, "YOUR HABITS (up to 12)", color=C_INC)
            for k in range(12):
                r = hr + 1 + k
                self.label(ws, f"B{r}", f"Habit {k + 1}", 9, True, SECONDARY)
                ws[f"C{r}"] = HABITS[k] if (self.demo and k < len(HABITS)) else (["Drink water", "Exercise", "Read", "Sleep 8 hours"][k] if k < 4 and not self.demo else None)
                self.merge(ws, f"C{r}:E{r}")
                self.inp(S, f"C{r}:E{r}")
                ws.row_dimensions[r].height = 20
            self.wb.defined_names["HabitList"] = DefinedName("HabitList", attr_text=f"{q(S)}!$C${hr + 1}:$C${hr + 12}")
            return hr + 12, (2, hr, 5, hr + 12)

        self.build_start("HABIT TRACKER.   1) Type up to 12 habits below and the year you're tracking.   2) Each month tab has one "
                                "row per habit and one column per day: pick ✓ when you did it (✗ if you want to mark a miss).   3) Monthly "
                                "and yearly success rates, streak-friendly charts and your best habit update automatically.",
                                [("Year", 2026 if self.demo else "=YEAR(TODAY())", "year", "The year the month tabs show", "HabitYear"),
                                 ("Monthly goal", 0.8, "pct", "A habit 'meets the goal' at this success rate", "HabitGoal")],
                                ["Start small: 3–5 habits are easier to keep than 12.",
                                 "Tick ✓ the same time each day (e.g. before bed).",
                                 "Rename or replace a habit any time — the month tabs follow the list.",
                                 "Year Overview shows each habit's success rate by month and your best habit."], extra=habit_block)
        T = self.T
        # month tabs
        D1 = 4                      # day 1 -> column D
        H1, HN = 9, 20              # habit rows
        for mi, mname in enumerate(BB.MONTHS, start=1):
            ws, S = self.ws[mname], mname
            setup_sheet(ws, {"B": 26, "C": 3, **{L(D1 + d): 3.6 for d in range(31)}, L(D1 + 31): 3, L(D1 + 32): 9, L(D1 + 33): 9,
                             L(D1 + 34): 11})
            cD, cP, cG = L(D1 + 32), L(D1 + 33), L(D1 + 34)
            title_bar(ws, T, f"{mname.upper()}  ·  Habit Tracker", f'=TEXT(DATE(HabitYear,{mi},1),"mmmm yyyy")&"   ·   pick ✓ for each day you did the habit"',
                      D1 + 34, home_link=S_START, home_label="⌂ Start", demo=False)
            if self.demo:
                ws["B3"] = '="●  DEMO DATA   ·   "&' + ws["B3"].value[1:]
            ws["AU2"], ws["AU3"], ws["AU4"] = f"=DATE(HabitYear,{mi},1)", f"=DAY(EOMONTH(AU2,0))", f"={BB.TODAY}"
            ws["AT2"], ws["AT3"], ws["AT4"] = "first day", "days in month", "today"
            ws.column_dimensions["AT"].hidden = ws.column_dimensions["AU"].hidden = True
            habits = f"COUNTIF($B${H1}:$B${HN},\"?*\")"
            ticks = f'COUNTIF(${L(D1)}${H1}:${L(D1 + 30)}${HN},"✓")'
            elapsed = f"MAX(0,MIN($AU$3,IF($AU$4<$AU$2,0,IF($AU$4>EOMONTH($AU$2,0),$AU$3,DAY($AU$4)))))"
            spans = [(2, 2), (4, 11), (12, 21), (22, 34)]
            specs = [("HABITS", f"={habits}", "0", NAVY, DARK), ("✓ THIS MONTH", f"={ticks}", "0", C_INC, C_INC),
                     ("SUCCESS SO FAR", f'=IF({habits}*{elapsed}=0,"—",{ticks}/({habits}*{elapsed}))', FMT_PCT, C_GOAL, DARK),
                     ("HABITS ON GOAL", f'=COUNTIF(${cG}${H1}:${cG}${HN},"✓ On goal")&" of "&{habits}', None, C_INC, DARK)]
            for (c1, c2), (lab, f, nf, acc, colr) in zip(spans, specs):
                self.tile(ws, 5, c1, c2, lab, f, nf, acc, color=colr)
            ws.row_dimensions[7].height = 10
            # header rows: day number (7) and weekday letter (8)
            self.label(ws, "B8", "Habit", 9, True, MIDNIGHT)
            ws["B8"].fill = fill("E2F2EF")
            for d in range(31):
                c = L(D1 + d)
                ws[f"{c}7"] = f'=IF({d + 1}>$AU$3,"",{d + 1})'
                ws[f"{c}8"] = f'=IF({c}7="","",MID("SMTWTFS",WEEKDAY(DATE(HabitYear,{mi},{d + 1})),1))'
                for rr in (7, 8):
                    ws[f"{c}{rr}"].alignment = CENTER
                    ws[f"{c}{rr}"].font = T.font(8, True, MIDNIGHT if rr == 7 else SECONDARY)
                    ws[f"{c}{rr}"].fill = fill("E2F2EF")
            for c, h in ((cD, "Done"), (cP, "Rate"), (cG, "Goal")):
                ws[f"{c}8"] = h
                ws[f"{c}8"].font = T.font(9, True, MIDNIGHT)
                ws[f"{c}8"].alignment = CENTER
                ws[f"{c}8"].fill = fill("E2F2EF")
            ws.row_dimensions[7].height = 16
            ws.row_dimensions[8].height = 16
            marks = habit_marks(mi) if self.demo and mi <= ANCHOR.month else None
            for k in range(HN - H1 + 1):
                r = H1 + k
                ws[f"B{r}"] = f'=IF(INDEX(HabitList,{k + 1})="","",INDEX(HabitList,{k + 1}))'
                paint(ws, f"B{r}", f=FILL_WHITE, font=T.font(10), border=_C.CELL_BOX,
                      align=Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True))
                if marks and k < len(marks):
                    for d, v in enumerate(marks[k]):
                        ws[f"{L(D1 + d)}{r}"] = v
                style_input(ws, f"{L(D1)}{r}:{L(D1 + 30)}{r}", T, None, CENTER)
                ws[f"{cD}{r}"] = f'=IF(B{r}="","",COUNTIF({L(D1)}{r}:{L(D1 + 30)}{r},"✓"))'
                ws[f"{cP}{r}"] = f'=IF(OR(B{r}="",{elapsed}=0),"",{cD}{r}/{elapsed})'
                ws[f"{cG}{r}"] = f'=IF({cP}{r}="","",IF({cP}{r}>=HabitGoal,"✓ On goal","Below goal"))'
                self.calc(S, f"{cD}{r}", "0", CENTER)
                self.calc(S, f"{cP}{r}", FMT_PCT, CENTER)
                self.calc(S, f"{cG}{r}", None, CENTER)
                ws.row_dimensions[r].height = 20
            self.unlocked[S].append(f"{L(D1)}{H1}:{L(D1 + 30)}{HN}")
            add_list_dv(ws, f"{L(D1)}{H1}:{L(D1 + 30)}{HN}", '"✓,✗"')
            grid = f"{L(D1)}{H1}:{L(D1 + 30)}{HN}"
            cf_formula(ws, grid, f'{L(D1)}${7}=""', "EEF2F1", stop=True)
            cf_formula(ws, grid, f'{L(D1)}{H1}="✓"', C_INC, WHITE, True)
            cf_formula(ws, grid, f'{L(D1)}{H1}="✗"', EXP_BG, C_EXP)
            cf_formula(ws, f"{L(D1)}7:{L(D1 + 30)}8", f'AND({L(D1)}$7<>"",$AU$2+N({L(D1)}$7)-1=$AU$4)', TEAL, WHITE, True)
            cf_databar(ws, f"{cP}{H1}:{cP}{HN}", C_INC)
            cf_formula(ws, f"{cG}{H1}:{cG}{HN}", f'{cG}{H1}="✓ On goal"', INC_BG, C_INC, True)
            # daily completion row + chart
            rd = HN + 1
            self.label(ws, f"B{rd}", "Daily completion", 9, True, NAVY)
            for d in range(31):
                c = L(D1 + d)
                ws[f"{c}{rd}"] = f'=IF(OR({c}$7="",{habits}=0),"",COUNTIF({c}{H1}:{c}{HN},"✓")/{habits})'
                ws[f"{c}{rd}"].number_format = "0%"
                ws[f"{c}{rd}"].font = T.font(7, False, SECONDARY)
                ws[f"{c}{rd}"].alignment = CENTER
            ws.conditional_formatting.add(f"{L(D1)}{rd}:{L(D1 + 30)}{rd}",
                                          ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF",
                                                         end_type="num", end_value=1, end_color="7FD3C6"))
            ws.row_dimensions[rd].height = 20
            cr = rd + 2
            section(ws, T, cr, 2, D1 + 34, "DAILY COMPLETION")
            for rr in range(cr + 1, cr + 13):
                ws.row_dimensions[rr].height = 18
            ch = BarChart()
            ch.type = "col"
            ch.add_data(Reference(ws, min_col=D1, max_col=D1 + 30, min_row=rd, max_row=rd), from_rows=True, titles_from_data=False)
            ch.set_categories(Reference(ws, min_col=D1, max_col=D1 + 30, min_row=7, max_row=7))
            self.chart_style(ch, None, [C_INC], legend=False, h=6)
            ch.y_axis.scaling.min, ch.y_axis.scaling.max = 0, 1
            ch.y_axis.number_format = "0%"
            ch.y_axis.majorGridlines = None
            ch.x_axis.delete = ch.y_axis.delete = False
            ch.gapWidth = 40
            place_chart(ws, ch, 2, cr + 1, D1 + 34, cr + 12)
            ws.freeze_panes = "C9"
            skin(ws, D1 + 34, cr + 13, cards=[(2, 7, D1 + 34, rd), (2, cr, D1 + 34, cr + 12)], hide_headers=True)
        # year overview
        ws, S = self.ws["Year Overview"], "Year Overview"
        setup_sheet(ws, {"B": 26, **{L(3 + m): 8 for m in range(12)}, "O": 10, "P": 3, "Q": 12})
        title_bar(ws, T, "YEAR OVERVIEW", '=HabitYear&"   ·   success rate of every habit, month by month"', 15,
                  home_link=S_START, home_label="⌂ Start", demo=False)
        if self.demo:
            ws["B3"] = '="●  DEMO DATA   ·   "&' + ws["B3"].value[1:]
        Y1, YN = 9, 20
        avg = f"$O${Y1}:$O${YN}"
        self.tile(ws, 5, 2, 2, "OVERALL SUCCESS", f'=IF(COUNT({avg})=0,"—",AVERAGE({avg}))', FMT_PCT, C_INC, color=C_INC)
        self.tile(ws, 5, 3, 7, "BEST HABIT", f'=IF(COUNT({avg})=0,"—",INDEX($B${Y1}:$B${YN},MATCH(MAX({avg}),{avg},0)))', None, C_GOAL)
        self.tile(ws, 5, 8, 11, "TOTAL ✓ THIS YEAR", "=" + "+".join(f"COUNTIF({q(m)}!$D${H1}:$AH${HN},\"✓\")" for m in BB.MONTHS), "0", C_INC)
        self.tile(ws, 5, 12, 15, "BEST MONTH", f'=IF(COUNT($C${YN + 1}:$N${YN + 1})=0,"—",INDEX($C$8:$N$8,MATCH(MAX($C${YN + 1}:$N${YN + 1}),$C${YN + 1}:$N${YN + 1},0)))', None, C_GOAL)
        ws.row_dimensions[7].height = 10
        self.head(ws, 8, 2, ["Habit"] + [m[:3] for m in BB.MONTHS] + ["Average"])
        for k in range(YN - Y1 + 1):
            r = Y1 + k
            ws[f"B{r}"] = f'=IF(INDEX(HabitList,{k + 1})="","",INDEX(HabitList,{k + 1}))'
            paint(ws, f"B{r}", f=FILL_WHITE, font=T.font(10), border=_C.CELL_BOX,
                  align=Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True))
            for m in range(12):
                c = L(3 + m)
                ws[f"{c}{r}"] = f"=IF($B{r}=\"\",\"\",{q(BB.MONTHS[m])}!$AK${H1 + k})"
            ws[f"O{r}"] = f'=IF(COUNT(C{r}:N{r})=0,"",AVERAGE(C{r}:N{r}))'
            self.calc(S, f"C{r}:O{r}", FMT_PCT, CENTER)
            ws.row_dimensions[r].height = 20
        r = YN + 1
        self.label(ws, f"B{r}", "Month average", 10, True, NAVY)
        for m in range(13):
            c = L(3 + m)
            ws[f"{c}{r}"] = f'=IF(COUNT({c}{Y1}:{c}{YN})=0,"",AVERAGE({c}{Y1}:{c}{YN}))'
        self.calc(S, f"C{r}:O{r}", FMT_PCT, CENTER, NAVY, True)
        ws.conditional_formatting.add(f"C{Y1}:N{YN}", ColorScaleRule(start_type="num", start_value=0, start_color="FBE3E5",
                                                                    mid_type="num", mid_value=0.5, mid_color="FFF6DD",
                                                                    end_type="num", end_value=1, end_color="7FD3C6"))
        cf_databar(ws, f"O{Y1}:O{YN}", C_INC)
        cr = r + 2
        section(ws, T, cr, 2, 15, "MONTHLY AVERAGE")
        for rr in range(cr + 1, cr + 14):
            ws.row_dimensions[rr].height = 18
        ch = BarChart()
        ch.type = "col"
        ch.add_data(Reference(ws, min_col=3, max_col=14, min_row=r, max_row=r), from_rows=True, titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=3, max_col=14, min_row=8, max_row=8))
        self.chart_style(ch, None, [C_INC], legend=False)
        ch.y_axis.scaling.min, ch.y_axis.scaling.max = 0, 1
        ch.y_axis.number_format = "0%"
        ch.y_axis.majorGridlines = None
        ch.x_axis.delete = ch.y_axis.delete = False
        place_chart(ws, ch, 2, cr + 1, 15, cr + 13)
        ws.freeze_panes = "C9"
        skin(ws, 15, cr + 14, cards=[(2, 8, 15, r), (2, cr, 15, cr + 13)], hide_headers=True)

    # ------------------------------------------------------------ finalize
    def add_sidebars(self):
        import io
        import sidebar
        from drawing_inject import Layer, col_px_list, row_px_list
        from openpyxl.drawing.image import Image as XLImage
        from PIL import Image as PILImage
        self.side_layers = {}
        for name in self.order:
            ws = self.ws[name]
            ws.column_dimensions["A"].width = 9.43
            last = min(max(ws.max_row, 60), 70)
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
                sidebar.draw(lay, name, lay.y(last + 1), nav=self.nav)
                self.side_layers[name] = lay
            else:
                sidebar.cells(ws, self.T, quote, name, last, nav=self.nav)

    def protect(self):
        if self.ed != "excel":
            return
        for name in self.order:
            if name == "Contributions":
                continue
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
        for n in self.order:
            ws = self.ws[n]
            ws.page_setup.orientation = "landscape"
            ws.page_setup.paperSize = ws.PAPERSIZE_A4
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            ws.print_options.horizontalCentered = True
            ws.page_margins.left = ws.page_margins.right = 0.4
            ws.page_margins.top = ws.page_margins.bottom = 0.5
        if BB.S_DC in self.ws:
            self.ws[BB.S_DC].print_area = "A1:X60"

    def build(self):
        getattr(self, f"make_{self.key}")()
        self.add_sidebars()
        self.protect()
        self.page_setup()
        first = self.order[1]
        if self.key == "habits":
            first = BB.MONTHS[ANCHOR.month - 1] if self.demo else "January"
        if not self.demo:
            first = S_START
        self.wb.active = self.order.index(first)
        for n in self.order:
            self.ws[n].sheet_view.tabSelected = (n == first)
        return self.wb


def out_path(key, ed, demo):
    name, slug, _ = PRODUCTS[key]
    folder = "Excel" if ed == "excel" else "Google_Sheets"
    suffix = "Excel" if ed == "excel" else "GoogleSheets"
    return (Path(__file__).resolve().parent.parent / "dist" / "05_Mini_Products" / slug / folder /
            f"{slug}_{suffix}_{'DEMO' if demo else 'BLANK'}.xlsx")


def main():
    from common import solidify_databars
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=list(PRODUCTS))
    ap.add_argument("--excel-demo", action="store_true")
    a = ap.parse_args()
    files = []
    for key in a.only:
        for ed in ("excel", "gsheets"):
            for demo in (True, False):
                if a.excel_demo and (ed != "excel" or not demo):
                    continue
                b = Mini(key, ed, demo)
                wb = b.build()
                p = out_path(key, ed, demo)
                p.parent.mkdir(parents=True, exist_ok=True)
                wb.save(p)
                solidify_databars(p)
                for name, lay in b.side_layers.items():
                    lay.inject(p, name)
                files.append(p)
                print("wrote", p.relative_to(p.parents[3]))
    return files


if __name__ == "__main__":
    main()
