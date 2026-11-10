"""QA for PRODUCT 4 — Ultimate Budget Spreadsheet. Exits non-zero on any failure.

Recalculates every edition in LibreOffice and compares the results with an independent Python model of the demo
data. It rebuilds every posting (transactions, each recurring occurrence up to today, paid bills) and recomputes:
  category x month matrix, annual totals, every month tab, bank balances, recurring next dates, payment status,
  dashboard KPIs, calendar days, paycheck bills, 50/30/20, expense distribution, sinking funds, debt NPER + a full
  snowball simulation, net worth, investment forecast, no-spend challenge.
Scenarios on modified copies: budget starting in April, recurring posting switched off, avalanche method.
BLANK files: zero errors and blank-state messages.
"""
from __future__ import annotations

import calendar as cal
import datetime as dt
import glob
import json
import math
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_budget as B  # noqa: E402
import sample_data_bg as SD  # noqa: E402

DIST = HERE.parent / "dist" / "04_Ultimate_Budget_Spreadsheet"
RC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
fails, passes = [], 0
TODAY = SD.ANCHOR


def check(label, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(f"{label}  {detail}")


def near(a, b, tol=0.011):
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, (int, float)):
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(v))
    return v


def recalc(src, edit=None):
    tmp = Path(tempfile.mkdtemp()) / "w.xlsx"
    if edit:
        wb = load_workbook(src)
        edit(wb)
        wb.save(tmp)
    else:
        shutil.copy(src, tmp)
    out = json.loads(subprocess.run([sys.executable, RC, str(tmp), "900"], capture_output=True, text=True).stdout)
    return out, load_workbook(tmp, data_only=True)


def edate(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    return dt.date(y, m, min(d.day, cal.monthrange(y, m)[1]))


# ---------------------------------------------------------------- independent model
class Model:
    def __init__(self, start_month=1, year=2026, auto=True, method="Snowball"):
        self.p0 = dt.date(year, start_month, 1)
        self.auto, self.method = auto, method
        self.ctype = {c: "Income" for c, _ in SD.INCOME}
        self.ctype.update({c: "Expense" for c, *_ in SD.EXPENSE})
        self.ctype.update({f[0]: "Savings" for f in SD.FUNDS})
        self.ctype.update({d[0]: "Debt Payment" for d in SD.DEBTS})
        self.ctype["Transfer"] = "Transfer"
        self.bucket = {c: b for c, _g, b, _ in SD.EXPENSE}
        self.group = {c: g for c, g, _b, _ in SD.EXPENSE}
        self.fund_acc = {f[0]: f[5] for f in SD.FUNDS}
        self.txns = SD.transactions()
        self.post = []   # (date, cat, amount, account, to_account, source)
        for t in self.txns:
            d, desc, cat, acc, meth, amt, note = t[:7]
            to = self.fund_acc.get(cat, "") if self.ctype[cat] == "Savings" else (t[7] if cat == "Transfer" else "")
            self.post.append((d, cat, amt, acc, to, "T"))
        self.rec_posted = []
        for i, (nm, amt, fr, cat, acc, st, en, status) in enumerate(SD.RECURRING):
            for d in self.occurrences(st, fr, en, until=TODAY):
                if status == "Paused" or not self.auto or not (self.p0 <= d < edate(self.p0, 12)):
                    continue
                to = self.fund_acc.get(cat, "") if self.ctype[cat] == "Savings" else ""
                self.post.append((d, cat, amt, acc, to, "R"))
                self.rec_posted.append((i, d))
        for nm, amt, due, st, meth, cat, acc in SD.PAYMENTS:
            if st == "Paid":
                self.post.append((due, cat, amt, acc, "", "P"))

    @staticmethod
    def occurrences(st, fr, en, until):
        out = []
        if fr in ("Weekly", "Biweekly"):
            step = 7 if fr == "Weekly" else 14
            d = st
            while d <= until:
                if en is None or d <= en:
                    out.append(d)
                d += dt.timedelta(days=step)
        else:
            q = {"Monthly": 1, "Quarterly": 3, "Annually": 12}[fr]
            k = 0
            while True:
                d = edate(st, k * q)
                if d > until:
                    break
                if en is None or d <= en:
                    out.append(d)
                k += 1
        return out

    def mi(self, d):
        k = (d.year - self.p0.year) * 12 + d.month - self.p0.month + 1
        return k if 1 <= k <= 12 else None

    def matrix(self, cat, k, src=None):
        return round(sum(a for d, c, a, *_ in self.post if c == cat and self.mi(d) == k
                         and (d <= TODAY or _[-1] in ("T", "P"))), 2)

    def by_type(self, typ, k):
        return sum(self.matrix(c, k) for c, t in self.ctype.items() if t == typ)


def check_demo(path, ed):
    res, wb = recalc(path)
    check(f"{ed} demo: no formula errors", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
    check(f"{ed} 28 tabs in order", wb.sheetnames == B.ORDER and len(B.ORDER) == 28, str(wb.sheetnames))
    M = Model()
    su = wb[B.S_SET]
    check("effective today", as_date(su["C18"].value) == TODAY)
    check("starting balance", near(su["C16"].value, sum(a[3] for a in SD.ACCOUNTS)))
    # ---- recurring
    rt = wb[B.S_RT]
    for i, (nm, amt, fr, cat, acc, st, en, status) in enumerate(SD.RECURRING):
        r = B.RT1 + i
        posted = sum(amt for j, d in M.rec_posted if j == i)
        check(f"recurring posted {nm}", near(rt[f"L{r}"].value, posted), f"{rt[f'L{r}'].value} != {posted}")
        if status == "Paused":
            check(f"recurring next {nm}", rt[f"K{r}"].value == "Paused", rt[f"K{r}"].value)
        else:
            nxt = next((d for d in M.occurrences(st, fr, None, TODAY + dt.timedelta(days=400)) if d >= TODAY), None)
            exp = "Ended" if en and nxt > en else nxt
            got = rt[f"K{r}"].value
            check(f"recurring next {nm}", (got == exp) if exp == "Ended" else as_date(got) == exp, f"{got} != {exp}")
        check(f"recurring type {nm}", rt[f"C{r}"].value == M.ctype[cat])
    # ---- matrix
    at = wb[B.S_AT]
    cats = {}
    for r in range(B.MX1, B.MXN + 1):
        c = at[f"B{r}"].value
        if c:
            cats[c] = r
    check("matrix has every category", set(cats) == set(M.ctype), str(set(M.ctype) ^ set(cats)))
    for c, r in cats.items():
        for k in range(12):
            got = at.cell(row=r, column=6 + k).value
            check(f"matrix {c} m{k + 1}", near(got, M.matrix(c, k + 1)), f"{got} != {M.matrix(c, k + 1)}")
    budget_m = sum(b for *_x, b in SD.EXPENSE)
    for k in range(12):
        r = B.AT1 + k
        inc, exp_, sav, debt = (M.by_type(t, k + 1) for t in ("Income", "Expense", "Savings", "Debt Payment"))
        check(f"annual income m{k + 1}", near(at[f"C{r}"].value, inc))
        check(f"annual expenses m{k + 1}", near(at[f"D{r}"].value, exp_))
        check(f"annual savings m{k + 1}", near(at[f"E{r}"].value, sav))
        check(f"annual debt m{k + 1}", near(at[f"F{r}"].value, debt))
        check(f"annual net m{k + 1}", near(at[f"H{r}"].value, inc - exp_ - sav - debt))
        check(f"annual budget m{k + 1}", near(at[f"L{r}"].value, budget_m))
        check(f"annual label m{k + 1}", at[f"B{r}"].value == f"{cal.month_name[k + 1]} 2026")
    tot_inc = sum(M.by_type("Income", k) for k in range(1, 13))
    tot_exp = sum(M.by_type("Expense", k) for k in range(1, 13))
    tot_sav = sum(M.by_type("Savings", k) for k in range(1, 13))
    tot_debt = sum(M.by_type("Debt Payment", k) for k in range(1, 13))
    check("annual total income", near(at[f"C{B.AT1 + 12}"].value, tot_inc))
    check("annual savings rate", near(at[f"J{B.AT1 + 12}"].value, tot_sav / tot_inc, 1e-6))
    # ---- month tabs
    for k in range(12):
        ws = wb[cal.month_name[k + 1]]
        inc, exp_, sav, debt = (M.by_type(t, k + 1) for t in ("Income", "Expense", "Savings", "Debt Payment"))
        check(f"{ws.title} income tile", near(ws["B8"].value, inc), f"{ws['B8'].value} {inc}")
        check(f"{ws.title} expenses tile", near(ws["E8"].value, exp_))
        check(f"{ws.title} savings tile", near(ws["H8"].value, sav))
        check(f"{ws.title} debt tile", near(ws["K8"].value, debt))
        check(f"{ws.title} budget tile", near(ws["B11"].value, budget_m))
        check(f"{ws.title} remaining tile", near(ws["H11"].value, budget_m - exp_))
        fixed = sum(M.matrix(c, k + 1) for c, g, *_ in SD.EXPENSE if g == "Fixed")
        check(f"{ws.title} fixed total", near(ws["E30"].value, fixed))
        for i in range(15):
            c = ws[f"B{15 + i}"].value
            if c:
                check(f"{ws.title} fixed row {c}", near(ws[f"E{15 + i}"].value, M.matrix(c, k + 1)))
        n_tx = sum(1 for t in M.txns if t[0].month == k + 1)
        shown = [ws[f"C{72 + j}"].value for j in range(50) if ws[f"C{72 + j}"].value]
        check(f"{ws.title} transaction list", len(shown) == min(50, n_tx), f"{len(shown)} vs {n_tx}")
    # ---- bank accounts
    ba = wb[B.S_BA]
    for i, (name, typ, inst, opening) in enumerate(SD.ACCOUNTS):
        inc = sum(a for d, c, a, acc, to, s in M.post if acc == name and M.ctype[c] == "Income")
        out = sum(a for d, c, a, acc, to, s in M.post if acc == name and M.ctype[c] != "Income")
        tin = sum(a for d, c, a, acc, to, s in M.post if to == name)
        check(f"balance {name}", near(ba[f"I{B.BA1 + i}"].value, opening + inc - out + tin), f"{ba[f'I{B.BA1 + i}'].value} != {opening + inc - out + tin}")
    # ---- payments
    py = wb[B.S_PAY]
    for i, (nm, amt, due, st, *_x) in enumerate(SD.PAYMENTS):
        got = py[f"J{B.PY1 + i}"].value
        if st == "Paid":
            exp = "✓ Paid"
        elif due < TODAY:
            exp = f"Overdue {(TODAY - due).days}d"
        elif due == TODAY:
            exp = "Due today"
        elif (due - TODAY).days <= 7:
            exp = f"Due in {(due - TODAY).days}d"
        else:
            exp = f"Due {due:%b} {due.day}"
        check(f"payment status {nm}", got == exp, f"{got} != {exp}")
    # ---- dashboard
    da = wb[B.S_DASH]
    check("dash income", near(da["B8"].value, tot_inc))
    check("dash expenses", near(da["E8"].value, tot_exp))
    check("dash net", near(da["H8"].value, tot_inc - tot_exp - tot_sav - tot_debt))
    check("dash savings", near(da["K8"].value, tot_sav))
    check("dash rate", near(da["B11"].value, tot_sav / tot_inc, 1e-6))
    check("dash budget", near(da["E11"].value, budget_m * 12))
    check("dash total debt", near(da["K11"].value, sum(d[2] for d in SD.DEBTS)))
    unpaid = sorted((p for p in SD.PAYMENTS if p[3] != "Paid"), key=lambda p: p[2])
    check("dash next payment", da["B66"].value == unpaid[0][0], da["B66"].value)
    exp_by_cat = {c: sum(M.matrix(c, k) for k in range(1, 13)) for c, *_x in SD.EXPENSE}
    top = sorted(exp_by_cat.items(), key=lambda x: -x[1])
    check("dash top category", da["S5"].value == top[0][0] and near(da["T5"].value, top[0][1]), f"{da['S5'].value}")
    # ---- calendar (November 2026)
    ca = wb[B.S_CAL]
    check("calendar month", as_date(ca["Y2"].value) == dt.date(2026, 11, 1))
    occ = {}
    for nm, amt, fr, cat, acc, st, en, status in SD.RECURRING:
        if status == "Paused":
            continue
        for d in M.occurrences(st, fr, en, dt.date(2026, 12, 31)):
            occ.setdefault(d, []).append((M.ctype[cat], amt))
    grid0 = as_date(ca["Y3"].value)
    check("calendar grid starts Monday", grid0 == dt.date(2026, 10, 26), grid0)
    for w in range(6):
        for d in range(7):
            date = grid0 + dt.timedelta(days=w * 7 + d)
            base = 9 + w * 5
            col = "BCDEFGH"[d]
            items = occ.get(date, []) if date.month == 11 else []
            inc = sum(a for t, a in items if t == "Income")
            bills = sum(a for t, a in items if t in ("Expense", "Debt Payment")) + \
                (sum(p[1] for p in SD.PAYMENTS if p[2] == date) if date.month == 11 else 0)
            sav = sum(a for t, a in items if t == "Savings")
            e1 = f"↑ {inc:,.0f}" if inc > 0 else ""
            e2 = f"↓ {bills:,.0f}" if bills > 0 else ""
            e3 = f"◆ {sav:,.0f} saved" if sav > 0 else ""
            pays = [p[0] for p in SD.PAYMENTS if p[2] == date]
            e4 = f"⚑ {pays[0]}" if pays and date.month == 11 else ""
            for kk, e in ((1, e1), (2, e2), (3, e3), (4, e4)):
                got = ca[f"{col}{base + kk}"].value or ""
                check(f"calendar {date} row {kk}", got == e, f"{got!r} != {e!r}")
    # ---- paychecks
    pc = wb[B.S_PC]
    pays = SD.paychecks()
    for i, (d, src, g, tx, oth, sv) in enumerate(pays):
        r = B.PC1 + i
        end = pays[i + 1][0] - dt.timedelta(days=1) if i + 1 < len(pays) else d + dt.timedelta(days=13)
        bills = sum(a for dd, items in occ.items() if d <= dd <= end for t, a in items if t in ("Expense", "Debt Payment"))
        bills += sum(p[1] for p in SD.PAYMENTS if d <= p[2] <= end)
        check(f"paycheck {d} net", near(pc[f"G{r}"].value, g - tx - oth))
        check(f"paycheck {d} bills", near(pc[f"H{r}"].value, bills), f"{pc[f'H{r}'].value} != {bills}")
        check(f"paycheck {d} left", near(pc[f"J{r}"].value, g - tx - oth - bills - sv))
    # ---- 50/30/20
    ws = wb[B.S_503]
    needs = sum(v for c, v in exp_by_cat.items() if M.bucket[c] == "Needs")
    wants = sum(v for c, v in exp_by_cat.items() if M.bucket[c] == "Wants")
    check("503 income", near(ws["B8"].value, tot_inc))
    check("503 needs", near(ws["E12"].value, needs))
    check("503 wants", near(ws["E13"].value, wants))
    check("503 savings+debt", near(ws["E14"].value, tot_sav + tot_debt))
    check("503 needs status", ws["H12"].value == ("✓ Within target" if needs <= 0.5 * tot_inc else f"Over by {needs - 0.5 * tot_inc:,.0f}"), ws["H12"].value)
    # ---- expense distribution
    ws = wb[B.S_ED]
    tot = sum(exp_by_cat.values())
    for i, (c, *_x) in enumerate(SD.EXPENSE):
        r = 9 + i
        check(f"ED {c}", ws[f"B{r}"].value == c and near(ws[f"E{r}"].value, exp_by_cat[c]) and near(ws[f"F{r}"].value, exp_by_cat[c] / tot, 1e-6))
    check("ED fixed split", near(ws["L9"].value, sum(v for c, v in exp_by_cat.items() if M.group[c] == "Fixed")))
    # ---- sinking funds
    ws = wb[B.S_SF]
    for i, (fund, target, start, monthly, tdate, acc) in enumerate(SD.FUNDS):
        r = B.SF1 + i
        saved = sum(M.matrix(fund, k) for k in range(1, 13))
        check(f"fund {fund} saved", near(ws[f"H{r}"].value, saved))
        check(f"fund {fund} balance", near(ws[f"I{r}"].value, start + saved))
        check(f"fund {fund} progress", near(ws[f"K{r}"].value, min(1, (start + saved) / target), 1e-6))
    # ---- debts
    debt_checks(wb[B.S_DC], "Snowball")
    # ---- net worth
    ws = wb[B.S_NW]
    bank = sum(ba[f"I{B.BA1 + i}"].value for i, a in enumerate(SD.ACCOUNTS) if a[1] != "Credit card")
    assets = bank + sum(v for *_x, v in SD.NET_WORTH_ITEMS)
    liabs = sum(d[2] for d in SD.DEBTS) + sum(v for *_x, v in SD.NET_WORTH_LIABS)
    check("NW assets", near(ws["K19"].value, assets))
    check("NW liabilities", near(ws["K24"].value, liabs))
    check("NW net worth", near(ws["K25"].value, assets - liabs))
    # ---- investment
    ws = wb[B.S_IF]
    p0, c, fr, rate, yrs, inf = SD.INVEST
    i_ = rate / 12
    fv = p0 * (1 + i_) ** (12 * yrs) + c * ((1 + i_) ** (12 * yrs) - 1) / i_
    check("IF future value", near(ws["E6"].value, fv, 0.01), f"{ws['E6'].value} != {fv}")
    check("IF contributed", near(ws["G6"].value, p0 + c * 12 * yrs))
    check("IF real value", near(ws["G9"].value, fv / (1 + inf) ** yrs, 0.01))
    check("IF year 10 row", near(ws["M16"].value, p0 * (1 + i_) ** 120 + c * ((1 + i_) ** 120 - 1) / i_, 0.01))
    check("IF rows stop at period", ws["K27"].value in ("", None) and ws["K26"].value == 20)
    # ---- no-spend
    ws = wb[B.S_NS]
    sts = SD.CHALLENGE[4]
    check("NS no-spend days", ws["B12"].value == sts.count("✓ No spend"))
    check("NS spent days", ws["D12"].value == sts.count("✗ Spent"))
    check("NS money saved", near(ws["F12"].value, sts.count("✓ No spend") * SD.CHALLENGE[3]))
    streak, best = 0, 0
    for s_ in sts:
        streak = streak + 1 if s_ == "✓ No spend" else (streak if s_ == "★ Exception" else 0)
        best = max(best, streak)
    check("NS current streak", ws["E15"].value == f"{streak} days", ws["E15"].value)
    check("NS longest streak", ws["F15"].value == f"{best} days", ws["F15"].value)
    check("NS end date", as_date(ws["F7"].value) == SD.CHALLENGE[1] + dt.timedelta(days=SD.CHALLENGE[2] - 1))
    return wb


def simulate(debts, extra, method):
    """debts: list of (balance, apr, min, add). Mirrors the spreadsheet's month-by-month plan."""
    n = len(debts)
    act = [i for i, d in enumerate(debts) if d[0] > 0]
    if method == "Snowball":
        order = sorted(act, key=lambda i: (debts[i][0], i))
    else:
        order = sorted(act, key=lambda i: (-debts[i][1], i))
    rank = [99] * n
    for k, i in enumerate(order):
        rank[i] = k + 1
    pool0 = extra + sum(d[3] for d in debts)
    bal = [max(0, d[0]) for d in debts]
    hist, interest = [bal[:]], 0.0
    for _ in range(360):
        prev = bal[:]
        focus = min(rank[i] + (1000 if prev[i] <= 0.005 else 0) for i in range(n))
        pool = pool0 + sum(debts[i][2] for i in range(n) if prev[i] <= 0.005)
        interest += sum(prev[i] * debts[i][1] / 12 for i in range(n))
        bal = [0 if prev[i] <= 0.005 else max(0, prev[i] * (1 + debts[i][1] / 12) - (debts[i][2] + (pool if rank[i] == focus else 0)))
               for i in range(n)]
        hist.append(bal[:])
    return rank, hist, interest


def debt_checks(ws, method):
    debts = [(d[2], d[3] / 100, d[4], d[5]) for d in SD.DEBTS] + [(0, 0, 0, 0)] * 7
    rank, hist, interest = simulate(debts, SD.EXTRA_DEBT, method)
    for i, d in enumerate(SD.DEBTS):
        r = B.DC1 + i
        check(f"debt rank {d[0]} ({method})", ws[f"N{r}"].value == rank[i], f"{ws[f'N{r}'].value} != {rank[i]}")
        bal, apr, mn, add = debts[i]
        rr = apr / 12
        nper = -math.log(1 - rr * bal / (mn + add)) / math.log(1 + rr)
        check(f"debt NPER {d[0]}", near(ws[f"J{r}"].value, nper, 1e-6), f"{ws[f'J{r}'].value} {nper}")
        check(f"debt own payoff {d[0]}", as_date(ws[f"K{r}"].value) == edate(TODAY, math.ceil(nper)))
        months = sum(1 for t in range(1, 361) if hist[t][i] > 0.005) + 1
        check(f"debt plan payoff {d[0]}", as_date(ws[f"O{r}"].value) == edate(TODAY, months), f"{ws[f'O{r}'].value}")
    total_months = sum(1 for t in range(1, 361) if sum(hist[t]) > 0.005) + 1
    check(f"debt-free date ({method})", as_date(ws["H22"].value) == edate(TODAY, total_months), f"{ws['H22'].value}")
    check(f"plan interest ({method})", near(ws["K22"].value, interest, 0.05), f"{ws['K22'].value} != {interest}")
    for t in (1, 12, 30):
        got = ws[f"N{28 + t}"].value
        check(f"schedule month {t}", near(got, sum(hist[t]), 0.02), f"{got} != {sum(hist[t])}")


def check_structure(path, ed):
    wb = load_workbook(path)
    tr = wb[B.S_TR]
    srcs = {str(dv.formula1) for dv in tr.data_validations.dataValidation}
    check(f"{ed} category dropdown", B.ST("AG") in srcs)
    check(f"{ed} account dropdown", B.BA("B") in srcs)
    z = zipfile.ZipFile(path)
    shapes = any(b"<xdr:sp" in z.read(f) for f in z.namelist() if f.startswith("xl/drawings/drawing"))
    check(f"{ed} shapes {'present' if ed == 'excel' else 'absent'}", shapes == (ed == "excel"))
    if ed == "excel":
        check("dashboard protected", wb[B.S_DASH].protection.sheet)
        check("transactions editable", not wb[B.S_TR].protection.sheet)
        check("transactions table", "Transactions" in wb[B.S_TR].tables)
        ws = wb["January"]
        check("month budget cell unlocked", not ws["D15"].protection.locked and ws["E15"].protection.locked)


def scenarios(path):
    # 1) budget starts in April; 2) recurring posting off; 3) avalanche
    def edit(wb):
        wb[B.S_SET]["C13"] = "April"
        wb[B.S_SET]["C19"] = "No"
        wb[B.S_DC]["C5"] = "Avalanche"
    res, wb = recalc(path, edit)
    check("scenario: no errors", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
    M = Model(start_month=4, auto=False, method="Avalanche")
    at = wb[B.S_AT]
    check("April start: first month label", at[f"B{B.AT1}"].value == "April 2026", at[f"B{B.AT1}"].value)
    check("April start: last month label", at[f"B{B.AT1 + 11}"].value == "March 2027")
    for k in range(12):
        r = B.AT1 + k
        for col, t in (("C", "Income"), ("D", "Expense"), ("E", "Savings"), ("F", "Debt Payment")):
            check(f"April start m{k + 1} {t}", near(at[f"{col}{r}"].value, M.by_type(t, k + 1)),
                  f"{at[f'{col}{r}'].value} != {M.by_type(t, k + 1)}")
    jan = wb["January"]
    check("January tab = Jan 2027 (month 10)", jan["P2"].value == 10 and as_date(jan["P3"].value) == dt.date(2027, 1, 1))
    check("January 2027 has no income yet", near(jan["B8"].value, 0))
    check("recurring off: nothing posted", near(sum(wb[B.S_RT][f"L{B.RT1 + i}"].value or 0 for i in range(len(SD.RECURRING))), 0))
    debt_checks(wb[B.S_DC], "Avalanche")


def check_blank(path, ed):
    res, wb = recalc(path)
    check(f"{ed} blank: no errors", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
    da = wb[B.S_DASH]
    check(f"{ed} blank: no unpaid bills message", da["B66"].value == "No unpaid bills", da["B66"].value)
    check(f"{ed} blank: savings rate dash", da["B11"].value == "—", da["B11"].value)
    check(f"{ed} blank: budget year = this year", wb[B.S_SET]["C12"].value == dt.date.today().year)
    check(f"{ed} blank: dropdown categories", wb[B.S_SET][f"AG{B.M1}"].value == "Salary")
    check(f"{ed} blank: investment disclaimer", "NOT A GUARANTEE" in (wb[B.S_IF]["B13"].value or ""))


def main():
    for ed, folder, suf in (("excel", "Excel", "Excel"), ("gsheets", "Google_Sheets", "GoogleSheets")):
        demo = DIST / folder / f"Ultimate_Budget_Spreadsheet_{suf}_DEMO.xlsx"
        check_structure(demo, ed)
        check_demo(demo, ed)
        check_blank(DIST / folder / f"Ultimate_Budget_Spreadsheet_{suf}_BLANK.xlsx", ed)
    scenarios(DIST / "Google_Sheets" / "Ultimate_Budget_Spreadsheet_GoogleSheets_DEMO.xlsx")
    print(f"PASSED {passes} checks, FAILED {len(fails)}")
    for f in fails[:60]:
        print("  FAIL", f)
    return not fails


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
