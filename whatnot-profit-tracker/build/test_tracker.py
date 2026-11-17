"""Tests for the Whatnot Live Show Profit Tracker.

1. Recalculate both workbooks in LibreOffice (headless) and count formula errors.
2. Recompute the sample shows independently in Python and compare every calculated SHOW LOG cell, every
   DASHBOARD tile, table, top/bottom list and insight line, the YEAR SUMMARY and the ITEM SALES summary.
3. Scenarios: other fee rates + commission on shipping + another giveaway cost; another dashboard month.
4. Blank workbook: calculated cells are blank, no errors, empty-state messages shown.

Usage: python test_tracker.py [OUT_DIR]   -> prints a report; exit code 1 on any failure.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

import build_tracker as B
from sample_data import ITEMS, SHOWS

RECALC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
ERRORS = ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "Err:")
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))


def close(a, b, tol=0.006):
    if a in (None, "") or b in (None, ""):
        return (a in (None, "")) and (b in (None, ""))
    if isinstance(b, str) or isinstance(a, str):
        return str(a) == str(b)
    return abs(float(a) - float(b)) <= tol


def recalc(src: Path, edit=None) -> tuple[Path, dict]:
    tmp = Path(tempfile.mkdtemp()) / src.name
    if edit:
        wb = load_workbook(src)
        edit(wb)
        wb.save(tmp)
    else:
        shutil.copy(src, tmp)
    out = subprocess.run([sys.executable, RECALC, str(tmp), "300"], capture_output=True, text=True).stdout
    return tmp, json.loads(out[out.index("{"):])


def scan_errors(path: Path):
    wb = load_workbook(path, data_only=True)
    bad = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith(ERRORS):
                    bad.append(f"{ws.title}!{c.coordinate}={c.value}")
    return bad


# ------------------------------------------------------------------ independent model
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
CATS = ["Sports Cards", "Pokemon/TCG", "Sneakers", "Clothing", "Vintage", "Beauty", "Toys", "Collectibles", "Mystery Packs", "Other"]
SLOTS = ["Morning", "Afternoon", "Evening", "Late night"]


def model_show(s, cfg):
    gross, ship = s["gross"] or 0, s["ship"] or 0
    to_h = lambda t: t.hour + t.minute / 60
    hours = (to_h(s["end"]) - to_h(s["start"])) % 24
    gcost = s["gover"] if s["gover"] is not None else (s["gives"] or 0) * cfg["give"]
    comm = cfg["comm"] * (gross + (ship if cfg["on_ship"] else 0))
    proc = cfg["proc"] * (gross + ship) + cfg["fixed"] * (s["orders"] or 0)
    fees = comm + proc
    profit = gross - fees - (s["cogs"] or 0) - gcost - (s["supplies"] or 0) - (s["other"] or 0)
    return dict(wday=WEEKDAYS[s["date"].weekday()][:3], hours=hours, gcost=gcost, comm=comm, proc=proc, fees=fees, profit=profit,
                margin=profit / gross if gross else "", perhour=profit / hours if hours else "",
                aov=gross / s["orders"] if s["orders"] else "", gpct=gcost / gross if gross else "")


def money_text(x, cur="$"):
    return ("-" if x < 0 else "") + cur + f"{abs(x):,.0f}"


def model_dashboard(rows, year, month, goal):
    """rows: list of (show, calc). Returns the expected DASHBOARD values."""
    yr = [(s, m) for s, m in rows if s["date"].year == year]
    mon = [(s, m) for s, m in yr if s["date"].month == month]
    ytd = [(s, m) for s, m in yr if s["date"].month <= month]
    mp = sum(m["profit"] for _, m in mon)
    hrs = sum(m["hours"] for _, m in mon if m["hours"])
    exp = dict(month_profit=mp, ytd_profit=sum(m["profit"] for _, m in ytd), shows=len(mon),
               avg_show=mp / len(mon) if mon else "–",
               avg_hour=sum(m["profit"] for _, m in mon if m["hours"]) / hrs if hrs else "–",
               fees_ytd=sum(m["fees"] for _, m in ytd), give_ytd=sum(m["gcost"] for _, m in ytd),
               goal=mp / goal if goal else "–")

    def table(keyf, names):
        out = []
        for n in names:
            sel = [(s, m) for s, m in yr if keyf(s) == n]
            p = sum(m["profit"] for _, m in sel)
            h = sum(m["hours"] for _, m in sel if m["hours"])
            out.append((n, len(sel), p, p / len(sel) if sel else "", sum(m["profit"] for _, m in sel if m["hours"]) / h if h else ""))
        return out
    exp["slot"] = table(lambda s: s["slot"], SLOTS)
    exp["wday"] = table(lambda s: WEEKDAYS[s["date"].weekday()], WEEKDAYS)
    exp["cat"] = table(lambda s: s["cat"], CATS)
    exp["trend"] = [(MONTHS[i], len([1 for s, _ in yr if s["date"].month == i + 1]),
                     sum(s["gross"] for s, _ in yr if s["date"].month == i + 1),
                     sum(m["fees"] for s, m in yr if s["date"].month == i + 1),
                     sum(m["profit"] for s, m in yr if s["date"].month == i + 1)) for i in range(12)]
    ranked = sorted(yr, key=lambda sm: sm[1]["profit"], reverse=True)
    exp["top"] = [(s["date"], s["title"], s["cat"], m["profit"]) for s, m in ranked[:5]]
    exp["bottom"] = [(s["date"], s["title"], s["cat"], m["profit"]) for s, m in sorted(yr, key=lambda sm: sm[1]["profit"])[:5]]

    def insight(tab, noun):
        if sum(t[1] for t in tab) == 0:
            return f"Log a few shows to see which {noun} earns the most."
        best = max(tab, key=lambda t: t[2])
        if best[2] <= 0:
            return f"No {noun} is in profit yet this year."
        return f"Your most profitable {noun} is {best[0]} ({money_text(best[2])} net profit this year)."
    exp["ins_slot"], exp["ins_day"], exp["ins_cat"] = insight(exp["slot"], "time slot"), insight(exp["wday"], "day"), insight(exp["cat"], "category")
    if not yr:
        exp["ins_trend"] = "Log a few shows to see your monthly trend."
        exp["ins_tb"] = "Your best and weakest shows of the year will appear here."
    else:
        bm = max(exp["trend"], key=lambda t: t[4])
        exp["ins_trend"] = f"Your best month this year is {bm[0]} ({money_text(bm[4])} net profit)."
        exp["ins_tb"] = (f"Your best show this year made {money_text(ranked[0][1]['profit'])} and your weakest made "
                         f"{money_text(ranked[-1][1]['profit'])}. Compare their time slots, giveaways and costs.")
    return exp


# ------------------------------------------------------------------ reading the workbook
def cell_rows(ws, first, n, cols):
    return [[ws[f"{c}{first + i}"].value for c in cols] for i in range(n)]


def find_rows(ws, title_prefix):
    """Row of the kicker whose text starts with title_prefix (DASHBOARD sections)."""
    for r in range(1, ws.max_row + 1):
        v = ws[f"B{r}"].value
        if isinstance(v, str) and v.startswith(title_prefix.upper()):
            return r
    raise KeyError(title_prefix)


def compare_all(path: Path, cfg, label, year, month):
    wb = load_workbook(path, data_only=True)
    log, dash, ys, items = wb[B.S_LOG], wb[B.S_DASH], wb[B.S_YEAR], wb[B.S_ITEM]
    rows = [(s, model_show(s, cfg)) for s in SHOWS]
    n_cmp = 0
    # SHOW LOG
    for i, (s, m) in enumerate(rows):
        r = B.LOG_FIRST + i
        for k in B.CALC_COLS:
            got = log[f"{B.C[k]}{r}"].value
            n_cmp += 1
            check(f"{label}: SHOW LOG row {r} {k}", close(got, m[k]), f"workbook {got!r} vs model {m[k]!r}")
    # DASHBOARD tiles
    exp = model_dashboard(rows, year, month, cfg["goal"])
    tiles = dict(month_profit="B9", ytd_profit="E9", shows="H9", avg_show="K9", avg_hour="B12", fees_ytd="E12", give_ytd="H12", goal="K12")
    for k, ref in tiles.items():
        n_cmp += 1
        check(f"{label}: DASHBOARD tile {k}", close(dash[ref].value, exp[k]), f"{dash[ref].value!r} vs {exp[k]!r}")
    # tables
    for prefix, key, ins in (("Profit by time slot", "slot", "ins_slot"), ("Profit by weekday", "wday", "ins_day"),
                             ("Profit by category", "cat", "ins_cat")):
        r0 = find_rows(dash, prefix) + 2
        for i, t in enumerate(exp[key]):
            got = [dash[f"{c}{r0 + i}"].value for c in "BCDEF"]
            for g, e, what in zip(got, t, ("name", "shows", "profit", "avg", "per hour")):
                n_cmp += 1
                check(f"{label}: {prefix} {t[0]} {what}", close(g, e), f"{g!r} vs {e!r}")
        g = dash[f"B{r0 + len(exp[key])}"].value
        n_cmp += 1
        check(f"{label}: insight {prefix}", g == exp[ins], f"{g!r} vs {exp[ins]!r}")
    r0 = find_rows(dash, "Monthly profit trend") + 2
    for i, t in enumerate(exp["trend"]):
        for c, e in zip("BCDEF", t):
            n_cmp += 1
            check(f"{label}: trend {t[0]} {c}", close(dash[f"{c}{r0 + i}"].value, e), f"{dash[f'{c}{r0 + i}'].value!r} vs {e!r}")
    g = dash[f"B{r0 + 12}"].value
    n_cmp += 1
    check(f"{label}: insight monthly trend", g == exp["ins_trend"], f"{g!r} vs {exp['ins_trend']!r}")
    r0 = find_rows(dash, "Top 5 shows") + 2
    for side, c0 in (("top", 0), ("bottom", 6)):
        cols = [chr(ord("B") + c0 + i) for i in range(6)]
        for k in range(5):
            r = r0 + k
            got = (dash[f"{cols[1]}{r}"].value, dash[f"{cols[2]}{r}"].value, dash[f"{cols[4]}{r}"].value, dash[f"{cols[5]}{r}"].value)
            e = exp[side][k] if k < len(exp[side]) else ("", "", "", "")
            gd = got[0].date() if isinstance(got[0], dt.datetime) else got[0]
            ok = (gd == e[0] or (gd in (None, "") and e[0] == "")) and close(got[1], e[1]) and close(got[2], e[2]) and close(got[3], e[3])
            n_cmp += 1
            check(f"{label}: {side} 5 #{k + 1}", ok, f"{got!r} vs {e!r}")
    g = dash[f"B{r0 + 5}"].value
    n_cmp += 1
    check(f"{label}: insight top/bottom", g == exp["ins_tb"], f"{g!r} vs {exp['ins_tb']!r}")
    # goal line
    gl = dash["B13"].value
    mp = exp["month_profit"]
    eg = (f"Goal for {MONTHS[month - 1]}: {money_text(cfg['goal'])}.  Profit so far: {money_text(mp)}"
          + (".  Goal reached." if mp >= cfg["goal"] else f" ({money_text(cfg['goal'] - mp)} to go)."))
    n_cmp += 1
    check(f"{label}: goal line", gl == eg, f"{gl!r} vs {eg!r}")
    # YEAR SUMMARY
    keys = dict(D="gross", E="fees", F="cogs", G="gcost", H="supplies", I="other", J="profit")
    for mth in range(1, 13):
        r = 8 + mth
        sel = [(s, m) for s, m in rows if s["date"].year == year and s["date"].month == mth]
        vals = dict(gross=sum(s["gross"] for s, _ in sel), cogs=sum(s["cogs"] for s, _ in sel), supplies=sum(s["supplies"] or 0 for s, _ in sel),
                    other=sum(s["other"] or 0 for s, _ in sel), fees=sum(m["fees"] for _, m in sel), gcost=sum(m["gcost"] for _, m in sel),
                    profit=sum(m["profit"] for _, m in sel))
        n_cmp += 1
        check(f"{label}: YEAR {MONTHS[mth - 1]} shows", close(ys[f"C{r}"].value, len(sel)))
        for c, k in keys.items():
            n_cmp += 1
            check(f"{label}: YEAR {MONTHS[mth - 1]} {k}", close(ys[f"{c}{r}"].value, vals[k]), f"{ys[f'{c}{r}'].value!r} vs {vals[k]!r}")
    tot = sum(m["profit"] for s, m in rows if s["date"].year == year)
    n_cmp += 1
    check(f"{label}: YEAR total net profit", close(ys["J21"].value, tot), f"{ys['J21'].value!r} vs {tot!r}")
    # check: year total = gross - all costs
    t = {c: ys[f"{c}21"].value for c in "DEFGHIJ"}
    n_cmp += 1
    check(f"{label}: YEAR totals add up", close(t["D"] - t["E"] - t["F"] - t["G"] - t["H"] - t["I"], t["J"]))
    # ITEM SALES summary
    groups = defaultdict(lambda: [0, 0.0, 0.0, 0])
    order = []
    for d, title, _n, _c, cost, price, _b, shipped in ITEMS:
        k = (d, title)
        if k not in groups:
            order.append(k)
        g = groups[k]
        g[0] += 1
        g[1] += price
        g[2] += cost
        g[3] += shipped != "Y"
    logged = {(s["date"], s["title"]) for s in SHOWS}
    for i, k in enumerate(order):
        r = B.ITEM_FIRST + i
        got = [items[f"{c}{r}"].value for c in "OPQRSTU"]
        gd = got[0].date() if isinstance(got[0], dt.datetime) else got[0]
        e = [k[0], k[1], *groups[k], "Yes" if k in logged else "Not yet"]
        ok = gd == e[0] and got[1] == e[1] and all(close(a, b) for a, b in zip(got[2:], e[2:]))
        n_cmp += 1
        check(f"{label}: ITEM summary {k[1]}", ok, f"{got!r} vs {e!r}")
    r = B.ITEM_FIRST + len(order)
    n_cmp += 1
    check(f"{label}: ITEM summary ends after last show", items[f"O{r}"].value in (None, ""))
    # blank rows in SHOW LOG
    blanks = [log[f"{B.C[k]}{r}"].value for r in range(B.LOG_FIRST + len(SHOWS), B.LOG_LAST + 1) for k in B.CALC_COLS]
    n_cmp += 1
    check(f"{label}: SHOW LOG unused rows are blank", all(v in (None, "") for v in blanks),
          f"{sum(v not in (None, '') for v in blanks)} non-blank")
    return n_cmp, exp


def main(out_dir: Path):
    blank = out_dir / (B.OUT_NAME + ".xlsx")
    sample = out_dir / (B.OUT_NAME + "_SAMPLE.xlsx")
    report = {}
    base = dict(comm=0.08, proc=0.029, fixed=0.30, on_ship=False, give=3.00, goal=1500)

    # 1. zero errors, both versions
    for p in (blank, sample):
        rp, res = recalc(p)
        bad = scan_errors(rp)
        check(f"{p.name}: LibreOffice reports 0 formula errors", res.get("total_errors") == 0, json.dumps(res.get("error_summary")))
        check(f"{p.name}: no error values in any cell", not bad, ", ".join(bad[:5]))
        report[p.name] = res.get("total_formulas")
        if p == sample:
            sample_rc = rp
        else:
            blank_rc = rp
    # 2. sample vs independent model (October 2026)
    n1, exp = compare_all(sample_rc, base, "sample", 2026, 10)
    report["sample_checks"] = n1
    report["expected"] = {k: exp[k] for k in ("month_profit", "ytd_profit", "shows", "avg_show", "avg_hour", "fees_ytd", "give_ytd", "goal")}

    # 3a. other fee rates, commission on shipping, other giveaway cost and goal
    alt = dict(comm=0.10, proc=0.0349, fixed=0.49, on_ship=True, give=4.50, goal=1000)

    def edit(wb):
        st = wb[B.S_SET]
        st["C7"], st["C8"], st["C9"], st["C10"], st["C16"], st["C17"] = alt["comm"], alt["proc"], alt["fixed"], "Sale price + shipping", alt["give"], alt["goal"]
        wb[B.S_DASH]["C6"] = "September"
    rp, res = recalc(sample, edit)
    check("fee change: 0 formula errors", res.get("total_errors") == 0)
    n2, exp2 = compare_all(rp, alt, "fees changed", 2026, 9)
    report["fee_change_checks"] = n2
    # confirm dependent figures really moved
    wb0, wb1 = load_workbook(sample_rc, data_only=True), load_workbook(rp, data_only=True)
    moved = [c for c in ("V", "W", "X", "Y", "U") if wb0[B.S_LOG][f"{c}6"].value != wb1[B.S_LOG][f"{c}6"].value]
    check("fee change: commission, processing, fees, giveaway cost and profit all changed", len(moved) == 5, str(moved))
    check("fee change: YEAR SUMMARY profit changed", wb0[B.S_YEAR]["J21"].value != wb1[B.S_YEAR]["J21"].value)

    # 3b. currency symbol
    rp3, _ = recalc(sample, lambda wb: wb[B.S_SET].__setitem__("C6", "£"))
    w3 = load_workbook(rp3, data_only=True)
    check("currency change: SHOW LOG heading uses £", "(£)" in str(w3[B.S_LOG]["Y5"].value), str(w3[B.S_LOG]["Y5"].value))
    check("currency change: dashboard insight uses £", "£" in str(w3[B.S_DASH]["B13"].value), str(w3[B.S_DASH]["B13"].value))

    # 4. blank workbook
    wb = load_workbook(blank_rc, data_only=True)
    log = wb[B.S_LOG]
    vals = [log[f"{B.C[k]}{r}"].value for r in range(B.LOG_FIRST, B.LOG_LAST + 1) for k in B.CALC_COLS]
    check("blank: every calculated SHOW LOG cell is blank", all(v in (None, "") for v in vals), f"{sum(v not in (None, '') for v in vals)} non-blank")
    d = wb[B.S_DASH]
    check("blank: profit tiles are 0", d["B9"].value == 0 and d["E9"].value == 0)
    check("blank: average tiles show a dash", d["K9"].value == "–" and d["B12"].value == "–", f"{d['K9'].value!r} {d['B12'].value!r}")
    ins = [d[f"B{find_rows(d, p) + off}"].value for p, off in (("Profit by time slot", 6), ("Profit by weekday", 9), ("Profit by category", 12))]
    check("blank: insight lines show the 'log a few shows' message", all(str(v).startswith("Log a few shows") for v in ins), str(ins))
    items = wb[B.S_ITEM]
    check("blank: ITEM SALES summary is empty", all(items[f"{c}{B.ITEM_FIRST}"].value in (None, "") for c in "OPQRSTU"))
    today = dt.date.today()
    check("blank: dashboard defaults to the current month and year",
          d["C6"].value == MONTHS[today.month - 1] and d["F6"].value == today.year, f"{d['C6'].value} {d['F6'].value}")

    fails = [r for r in RESULTS if not r[1]]
    print(f"PASSED {len(RESULTS) - len(fails)} checks, FAILED {len(fails)}")
    for name, _, detail in fails[:40]:
        print("  FAIL", name, detail)
    report["passed"], report["failed"] = len(RESULTS) - len(fails), len(fails)
    report["recalculated"] = {"sample": str(sample_rc), "blank": str(blank_rc)}
    Path(out_dir.parent / "test_results.json").write_text(json.dumps(report, indent=1, default=str))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "dist" / "whatnot-profit-tracker"))
