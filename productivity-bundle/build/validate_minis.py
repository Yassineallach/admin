"""QA for the six mini-products. Exits non-zero on any failure.

Every workbook (6 products x Excel/Sheets x DEMO/BLANK = 24 files) is recalculated in LibreOffice: 0 errors required.
DEMO values are compared with an independent Python model of the demo data:
  debt (NPER, snowball schedule, debt-free date), sinking funds (balances, progress, monthly deposits),
  net worth (totals, history changes), no-spend (counts, streaks, saved-so-far), investment (FV, 3 scenarios),
  habits (per-habit done counts and rates, month and year overview).
"""
from __future__ import annotations

import calendar as cal
import datetime as dt
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_budget as BB  # noqa: E402
import build_minis as M  # noqa: E402
import validate_budget as VB  # noqa: E402

fails, passes = [], 0
T = M.ANCHOR


def check(label, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(f"{label}  {detail}")


near = VB.near
as_date = VB.as_date


def v_debt(wb):
    ws = wb[BB.S_DC]
    debts = [(d[2], d[3] / 100, d[4], d[5]) for d in M.DEBTS] + [(0, 0, 0, 0)] * (10 - len(M.DEBTS))
    rank, hist, interest = VB.simulate(debts, M.EXTRA, "Snowball")
    for i, d in enumerate(M.DEBTS):
        r = BB.DC1 + i
        bal, apr, mn, add = debts[i]
        rr = apr / 12
        nper = -math.log(1 - rr * bal / (mn + add)) / math.log(1 + rr)
        check(f"debt NPER {d[0]}", near(ws[f"J{r}"].value, nper, 1e-6))
        check(f"debt rank {d[0]}", ws[f"N{r}"].value == rank[i], f"{ws[f'N{r}'].value} {rank[i]}")
        months = sum(1 for t in range(1, 361) if hist[t][i] > 0.005) + 1
        check(f"debt plan payoff {d[0]}", as_date(ws[f"O{r}"].value) == VB.edate(T, months))
        check(f"debt interest/month {d[0]}", near(ws[f"M{r}"].value, bal * apr / 12))
    total_months = sum(1 for t in range(1, 361) if sum(hist[t]) > 0.005) + 1
    check("debt-free date", as_date(ws["H22"].value) == VB.edate(T, total_months), ws["H22"].value)
    check("plan interest", near(ws["K22"].value, interest, 0.05))


def v_funds(wb):
    ws = wb["Sinking Funds"]
    log = M.fund_log()
    for i, (name, target, start, monthly, tdate, where) in enumerate(M.FUNDS):
        r = 9 + i
        dep = sum(a for d, f, t, a, n in log if f == name and t == "Deposit")
        wd = sum(a for d, f, t, a, n in log if f == name and t == "Withdrawal")
        bal = start + dep - wd
        check(f"fund {name} balance", near(ws[f"J{r}"].value, bal), f"{ws[f'J{r}'].value} != {bal}")
        check(f"fund {name} progress", near(ws[f"L{r}"].value, max(0, min(1, bal / target)), 1e-6))
        rem = max(0, target - bal)
        mtg = 0 if rem == 0 else math.ceil(rem / monthly)
        check(f"fund {name} months to go", ws[f"M{r}"].value == mtg)
        proj = VB.edate(T, mtg)
        exp = "✓ Goal reached" if rem == 0 else ("Past target date" if tdate < T else ("On track" if proj <= tdate else None))
        got = ws[f"O{r}"].value
        check(f"fund {name} status", got == exp if exp else got.startswith("Behind"), got)
    mr = 26
    for m in range(12):
        dep = sum(a for d, f, t, a, n in log if t == "Deposit" and d.month == m + 1 and d.year == 2026)
        check(f"deposits {cal.month_abbr[m + 1]}", near(ws[f"C{mr + 2 + m}"].value, dep))


def v_networth(wb):
    ws = wb[BB.S_NW]
    a = sum(v for *_x, v in M.NW_ASSETS)
    l_ = sum(v for *_x, v in M.NW_LIABS)
    check("NW assets", near(ws["K19"].value, a))
    check("NW liabilities", near(ws["K24"].value, l_))
    check("NW net worth", near(ws["K25"].value, a - l_))
    for k, t in enumerate(["Cash", "Bank accounts", "Investments", "Property", "Other assets"]):
        check(f"NW {t}", near(ws[f"K{9 + k}"].value, sum(v for tt, _n, v in M.NW_ASSETS if tt == t)))
    hs = wb["Net Worth History"]
    hist = M.nw_history()
    for k, (d, aa, ll) in enumerate(hist):
        r = 9 + k
        check(f"history date {k}", as_date(hs[f"B{r}"].value) == d)
        check(f"history NW {k}", near(hs[f"E{r}"].value, aa - ll))
        if k:
            check(f"history change {k}", near(hs[f"F{r}"].value, (aa - ll) - (hist[k - 1][1] - hist[k - 1][2])))
    last = hist[-1][1] - hist[-1][2]
    check("latest NW tile", near(hs["B6"].value, last))
    check("12-month change tile", near(hs["D6"].value, last - (hist[-13][1] - hist[-13][2])))


def v_nospend(wb):
    ws = wb[BB.S_NS]
    sts = M.CHALLENGE[4]
    check("NS no-spend", ws["B12"].value == sts.count("✓ No spend"))
    check("NS spent", ws["D12"].value == sts.count("✗ Spent"))
    check("NS saved", near(ws["F12"].value, sts.count("✓ No spend") * M.CHALLENGE[3]))
    streak = best = 0
    for s_ in sts:
        streak = streak + 1 if s_ == "✓ No spend" else (streak if s_ == "★ Exception" else 0)
        best = max(best, streak)
    check("NS current streak", ws["E15"].value == f"{streak} days", ws["E15"].value)
    check("NS longest streak", ws["F15"].value == f"{best} days")
    for k in range(len(sts)):
        check(f"NS saved so far day {k + 1}", near(ws[f"G{18 + k}"].value, sts[:k + 1].count("✓ No spend") * M.CHALLENGE[3]))
    check("NS dates", as_date(ws["C18"].value) == M.CHALLENGE[1])


def v_invest(wb):
    ws = wb[BB.S_IF]
    p0, c, fr, rate, yrs, inf = BB.SD.INVEST
    fv = lambda r, n: p0 * (1 + r / 12) ** (12 * n) + c * ((1 + r / 12) ** (12 * n) - 1) / (r / 12)
    check("IF FV", near(ws["E6"].value, fv(rate, yrs), 0.01))
    sc = wb["Compare Scenarios"]
    for col, r in zip("CDE", (0.04, 0.06, 0.08)):
        check(f"scenario {r}", near(sc[f"{col}13"].value, fv(r, yrs), 0.01), f"{sc[f'{col}13'].value} {fv(r, yrs)}")
    check("scenario contributed", near(sc["C14"].value, p0 + c * 12 * yrs))
    check("checkpoint 5", near(sc["I11"].value, fv(0.06, yrs * 5 / 10), 0.01))


def v_habits(wb):
    total = 0
    yo = wb["Year Overview"]
    rates = {h: [] for h in range(len(M.HABITS))}
    for m in range(1, 13):
        ws = wb[BB.MONTHS[m - 1]]
        days = cal.monthrange(2026, m)[1]
        elapsed = 0 if dt.date(2026, m, 1) > T else (days if dt.date(2026, m, days) <= T else T.day)
        marks = M.habit_marks(m) if m <= T.month else [[None] * days for _ in M.HABITS]
        check(f"{ws.title} day columns", ws[f"{BB.L(4 + days - 1)}7"].value == days and (days == 31 or ws[f"{BB.L(4 + days)}7"].value in ("", None)))
        for h, row in enumerate(marks):
            done = row.count("✓")
            total += done
            r = 9 + h
            check(f"{ws.title} habit {h} done", ws[f"AJ{r}"].value == done, f"{ws[f'AJ{r}'].value} {done}")
            if elapsed:
                rate = done / elapsed
                rates[h].append(rate)
                check(f"{ws.title} habit {h} rate", near(ws[f"AK{r}"].value, rate, 1e-6))
                check(f"{ws.title} habit {h} goal", ws[f"AL{r}"].value == ("✓ On goal" if rate >= 0.8 else "Below goal"))
                check(f"year overview {m} {h}", near(yo.cell(row=9 + h, column=2 + m).value, rate, 1e-6))
    check("year total ✓", yo["H6"].value == total, f"{yo['H6'].value} {total}")
    avgs = [sum(v) / len(v) for v in rates.values()]
    best = M.HABITS[avgs.index(max(avgs))]
    check("best habit", yo["C6"].value == best, yo["C6"].value)


CHECKS = {"debt": v_debt, "funds": v_funds, "networth": v_networth, "nospend": v_nospend, "invest": v_invest, "habits": v_habits}


def main(keys):
    for key in keys:
        for ed in ("excel", "gsheets"):
            for demo in (True, False):
                res, wb = VB.recalc(M.out_path(key, ed, demo))
                check(f"{key} {ed} {'demo' if demo else 'blank'} no errors", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
                if demo and ed == "gsheets":
                    CHECKS[key](wb)
    print(f"PASSED {passes} checks, FAILED {len(fails)}")
    for f in fails[:50]:
        print("  FAIL", f)
    return not fails


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:] or list(M.PRODUCTS)) else 1)
