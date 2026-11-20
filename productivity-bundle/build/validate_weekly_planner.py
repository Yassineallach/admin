"""QA for PRODUCT 3 — Weekly Planner Pro. Exits non-zero on any failure.

Recalculates every edition in LibreOffice and checks:
  1. structure: 8 tabs in order, no formula errors, dropdowns wired to Setup lists, Excel protection + reset names,
     Google Sheets edition carries no Excel-only shapes
  2. DEMO values against the sample data computed independently in Python: week dates, ISO week numbers, schedule
     slots, task/day/week progress, habits, water, exercise, productivity, six-week table, calendar grid, calendar
     items, monthly stats, week goals, monthly priorities
  3. scenarios on a modified copy: week-tab date override, Sunday week start, slot length, status 'done' rename
  4. BLANK: blank-state messages instead of errors, Week 1 = current week
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_weekly_planner as B  # noqa: E402
import sample_data_wp as SD  # noqa: E402

DIST = HERE.parent / "dist" / "03_Weekly_Planner_Pro"
RC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
fails, passes = [], 0


def check(label, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(f"{label}  {detail}")


def recalc(src, edit=None):
    tmp = Path(tempfile.mkdtemp()) / "w.xlsx"
    if edit:
        wb = load_workbook(src)
        edit(wb)
        wb.save(tmp)
    else:
        shutil.copy(src, tmp)
    out = json.loads(subprocess.run([sys.executable, RC, str(tmp), "300"], capture_output=True, text=True).stdout)
    return out, load_workbook(tmp, data_only=True)


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, (int, float)):
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(v))
    return v


def frac(v):
    if isinstance(v, dt.time):
        return (v.hour * 3600 + v.minute * 60 + v.second) / 86400
    if isinstance(v, dt.datetime):
        return (v.hour * 3600 + v.minute * 60 + v.second) / 86400
    return v


def iso_label(start):
    y, w, _ = (start + dt.timedelta(days=3)).isocalendar()
    return f"Week {w}  ·  {y}"


def check_demo(path, ed):
    res, wb = recalc(path)
    check(f"{ed} demo recalc no errors", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
    check(f"{ed} tab order", wb.sheetnames == B.ORDER, str(wb.sheetnames))
    su = wb[B.S_SETUP]
    check("effective today", as_date(su["C20"].value) == SD.ANCHOR, su["C20"].value)
    check("week 1 start", as_date(su["C21"].value) == SD.FIRST_WEEK)
    for n in range(1, 7):
        ws = wb[f"Week {n}"]
        w = SD.week(n)
        start = SD.FIRST_WEEK + dt.timedelta(days=7 * (n - 1))
        check(f"W{n} start", as_date(ws["N3"].value) == start, ws["N3"].value)
        check(f"W{n} iso", ws["B7"].value == iso_label(start), ws["B7"].value)
        check(f"W{n} end", as_date(ws["K12"].value) == start + dt.timedelta(days=6))
        tot = sum(len(d["tasks"][:B.BODY]) for d in w["days"])
        done = sum(1 for d in w["days"] for t in d["tasks"][:B.BODY] if t[3] == SD.DONE)
        check(f"W{n} tasks done tile", ws["J7"].value == f"{done} of {tot}", ws["J7"].value)
        prog = ws["N4"].value
        check(f"W{n} progress", abs((prog or 0) - (done / tot if tot else 0)) < 1e-9, prog)
        check(f"W{n} setup table progress", abs((su[f"L{17 + n}"].value or 0) - (done / tot)) < 1e-9)
        check(f"W{n} setup table goal", su[f"J{17 + n}"].value == w["goal"])
        for d, day in enumerate(w["days"]):
            r0 = B.DAY_ROW[d]
            check(f"W{n} d{d} date", as_date(ws[f"B{r0}"].value) == day["date"])
            k = len(day["tasks"][:B.BODY])
            kd = sum(1 for t in day["tasks"][:B.BODY] if t[3] == SD.DONE)
            exp = "No tasks yet" if k == 0 else f"{kd} of {k} done  ·  {round(100 * kd / k):.0f}%"
            got = ws[f"J{r0}"].value
            check(f"W{n} d{d} day progress", got == exp, f"{got!r} != {exp!r}")
            pct = ws[f"{B.DAYCOLS[d]}{B.R_TASKPCT}"].value
            check(f"W{n} d{d} tracker pct", (pct in ("", None) and k == 0) or abs(pct - kd / k) < 1e-9, pct)
            for i in range(B.BODY):
                t = frac(ws[f"J{r0 + 2 + i}"].value)
                if i < 10:
                    exp_t = (8 + i) / 24
                    check(f"W{n} slot {i}", t is not None and abs(t - exp_t) < 1e-6 if 8 + i < 18 else t in ("", None), t)
                tv = ws[f"E{r0 + 2 + i}"].value
                nd = ws[f"N{r0 + 2 + i}"].value
                check(f"W{n} d{d} r{i} task date helper", (as_date(nd) == day["date"]) if tv else nd in ("", None))
        for i, row in enumerate(w["habits"]):
            got = ws[f"L{B.HT + 2 + i}"].value
            check(f"W{n} habit {i}", got == sum(1 for v in row if v == "✓"), got)
        hab_done = sum(1 for row in w["habits"] for v in row if v == "✓")
        check(f"W{n} habits tile", ws["B10"].value == f"{hab_done} of {7 * len(SD.HABITS)}", ws["B10"].value)
        met = sum(1 for v in w["water"] if v is not None and v >= 8)
        check(f"W{n} water met", ws[f"L{B.R_WMET}"].value == met and ws["E10"].value == f"{met} of 7 days", ws["E10"].value)
        exm = sum(v for v in w["ex_min"] if v)
        check(f"W{n} exercise", ws[f"L{B.R_EXM}"].value == exm and ws["H10"].value == f"{exm} / 150 min", ws["H10"].value)
        sc = [v for v in w["score"] if v is not None]
        exp_sc = "—" if not sc else f"{sum(sc) / len(sc):.1f} / 10"
        check(f"W{n} avg productivity", ws["J10"].value == exp_sc, f"{ws['J10'].value} {exp_sc}")
        check(f"W{n} habit names", ws[f"B{B.HT + 2}"].value == SD.HABITS[0])
        if w["reflection"]:
            got = ws[f"F{B.RF + 5}"].value
            check(f"W{n} rating stars", got == "★" * w["reflection"][4] + "☆" * (10 - w["reflection"][4]), got)
    # calendar
    ws = wb[B.S_CAL]
    check("cal month", ws["E5"].value == "November" and ws["C5"].value == 2026)
    check("cal grid start", as_date(ws["Q7"].value) == dt.date(2026, 10, 26), ws["Q7"].value)
    tasks_by_date, done_by_date = {}, {}
    for n in range(1, 7):
        for day in SD.week(n)["days"]:
            tasks_by_date[day["date"]] = tasks_by_date.get(day["date"], 0) + len(day["tasks"][:B.BODY])
            done_by_date[day["date"]] = done_by_date.get(day["date"], 0) + sum(1 for t in day["tasks"][:B.BODY] if t[3] == SD.DONE)
    imp = {}
    for d, ev, _c in SD.IMPORTANT:
        imp.setdefault(d, []).append(ev)
    dls = {}
    for t, d, _p, _s in SD.DEADLINES:
        dls.setdefault(d, []).append(t)
    for wrow in range(6):
        base = B.G0 + wrow * 5
        for d in range(7):
            c = "BCDEFGH"[d]
            date = dt.date(2026, 10, 26) + dt.timedelta(days=wrow * 7 + d)
            check(f"cal {date} date", as_date(ws[f"{c}{base}"].value) == date)
            inm = date.month == 11
            e1 = f"★ {imp[date][0]}" if inm and date in imp else ""
            e2 = f"⚑ {dls[date][0]}" if inm and date in dls else ""
            k = tasks_by_date.get(date, 0)
            e3 = f"☑ {done_by_date.get(date, 0)}/{k} tasks done" if inm and k else ""
            more = (max(0, len(imp.get(date, [])) - 1) + max(0, len(dls.get(date, [])) - 1)) if inm else 0
            e4 = f"+{more} more" if more else ""
            for kk, e in ((1, e1), (2, e2), (3, e3), (4, e4)):
                got = ws[f"{c}{base + kk}"].value or ""
                check(f"cal {date} row{kk}", got == e, f"{got!r} != {e!r}")
        first = dt.date(2026, 10, 26) + dt.timedelta(days=wrow * 7)
        widx = [n for n in range(1, 7) if first == SD.FIRST_WEEK + dt.timedelta(days=7 * (n - 1))]
        got = ws[f"I{base}"].value or ""
        check(f"cal week goal row {wrow}", (got.startswith(SD.WEEKS[widx[0] - 1][0]) and f"Week {widx[0]}" in got) if widx else got == "", got)
    nov = lambda d: d.month == 11 and d.year == 2026
    exp_stats = [sum(1 for d, *_ in SD.IMPORTANT if nov(d)),
                 sum(1 for _t, d, *_ in SD.DEADLINES if nov(d)),
                 sum(1 for _t, d, _p, s in SD.DEADLINES if nov(d) and s == SD.DONE),
                 sum(1 for _t, d, _p, s in SD.DEADLINES if nov(d) and s != SD.DONE and d < SD.ANCHOR),
                 sum(v for d, v in tasks_by_date.items() if nov(d)),
                 sum(v for d, v in done_by_date.items() if nov(d))]
    for i, e in enumerate(exp_stats):
        got = ws[f"L{B.G0 + 6 + i}"].value
        check(f"cal stat {i}", got == e, f"{got} != {e}")
    check("cal completion", abs(ws[f"L{B.G0 + 12}"].value - exp_stats[5] / exp_stats[4]) < 1e-9)
    check("cal monthly priority", ws[f"K{B.G0 + 1}"].value == "1.  " + SD.MONTH_PRIORITIES[11][0], ws[f"K{B.G0 + 1}"].value)
    for i, (t, d, _p, s) in enumerate(SD.DEADLINES):
        got = ws[f"L{B.IMP1 + i}"].value
        exp = "✓ Done" if s == SD.DONE else (f"Late {(SD.ANCHOR - d).days}d" if d < SD.ANCHOR else
                                            ("Today" if d == SD.ANCHOR else f"In {(d - SD.ANCHOR).days}d"))
        check(f"deadline due {t}", got == exp, f"{got} != {exp}")
    return wb


def check_structure(path, ed):
    wb = load_workbook(path)
    for n in B.WEEKS:
        ws = wb[n]
        srcs = {str(dv.formula1) for dv in ws.data_validations.dataValidation}
        for need in (B.SL("B"), B.SL("C"), B.SL("E"), B.SL("G"), B.SL("K", B.LR1 + 1)):
            check(f"{ed} {n} dropdown {need}", need in srcs)
        if ed == "excel":
            check(f"{ed} {n} protected", ws.protection.sheet)
            check(f"{ed} {n} input unlocked", not ws["E23"].protection.locked and ws["J23"].protection.locked)
    if ed == "excel":
        from openpyxl.utils import range_boundaries
        for i in range(1, 7):
            nm = f"Week{i}_Inputs"
            check(f"reset name {nm}", nm in wb.defined_names)
            ws = wb[f"Week {i}"]
            merged = [range_boundaries(str(m)) for m in ws.merged_cells.ranges]
            for a in wb.defined_names[nm].attr_text.split(","):
                r = a.split("!")[1].replace("$", "")
                c1, r1, c2, r2 = range_boundaries(r if ":" in r else f"{r}:{r}")
                partial = [m for m in merged if not (m[2] < c1 or m[0] > c2 or m[3] < r1 or m[1] > r2)
                           and not (m[0] >= c1 and m[2] <= c2 and m[1] >= r1 and m[3] <= r2)]
                formulas = [c.coordinate for row in ws.iter_rows(min_row=r1, max_row=r2, min_col=c1, max_col=c2)
                            for c in row if isinstance(c.value, str) and c.value.startswith("=")]
                check(f"{nm} {r} clears cleanly", not partial and not formulas, f"{partial} {formulas}")
    z = zipfile.ZipFile(path)
    shapes = any(b"<xdr:sp>" in z.read(f) or b"<xdr:sp " in z.read(f) for f in z.namelist() if f.startswith("xl/drawings/drawing"))
    check(f"{ed} shapes {'present' if ed == 'excel' else 'absent'}", shapes == (ed == "excel"))


def scenarios(path):
    def edit(wb):
        su = wb[B.S_SETUP]
        su["C17"] = "Sunday"
        su["I13"] = 30
        su["E30"] = "Finished"          # rename the 'done' status in the list ...
        su["C24"] = "Finished"          # ... and in the preference
        w3 = wb["Week 3"]
        w3["D12"] = dt.datetime(2027, 3, 10)
        w3["I23"] = "Finished"
        w3["I24"] = "Finished"
        cal = wb[B.S_CAL]
        cal["E5"] = "March"
        cal["C5"] = 2027
    res, wb = recalc(path, edit)
    check("scenario recalc", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
    su = wb[B.S_SETUP]
    check("sunday week1 start", as_date(su["C21"].value) == dt.date(2026, 11, 1), su["C21"].value)
    w3 = wb["Week 3"]
    check("override aligned to sunday", as_date(w3["N3"].value) == dt.date(2027, 3, 7), w3["N3"].value)
    check("week 2 follows week 1", as_date(wb["Week 2"]["N3"].value) == dt.date(2026, 11, 8))
    check("30-min slots", abs(frac(w3[f"J{B.D0 + 3}"].value) - (8.5 / 24)) < 1e-6)
    check("10th 30-min slot", abs(frac(w3[f"J{B.D0 + 11}"].value) - (12.5 / 24)) < 1e-6)
    r0 = B.D0
    got = w3[f"J{r0}"].value
    check("renamed done status counts", got.startswith("2 of "), got)
    cal = wb[B.S_CAL]
    check("cal sunday grid", as_date(cal["Q7"].value) == dt.date(2027, 2, 28), cal["Q7"].value)
    check("cal sunday header", cal["B8"].value is not None)
    found = [cal[f"I{B.G0 + w * 5}"].value for w in range(6)]
    check("cal shows overridden week 3 goal", any(f and "Week 3" in f for f in found), str(found))


def check_blank(path, ed):
    res, wb = recalc(path)
    check(f"{ed} blank recalc no errors", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
    today = dt.date.today()
    monday = today - dt.timedelta(days=today.weekday())
    check(f"{ed} blank week1 = this week", as_date(wb[B.S_SETUP]["C21"].value) == monday, wb[B.S_SETUP]["C21"].value)
    ws = wb["Week 1"]
    check(f"{ed} blank progress message", ws["H7"].value == "No tasks yet", ws["H7"].value)
    check(f"{ed} blank day message", ws[f"J{B.D0}"].value == "No tasks yet")
    check(f"{ed} blank productivity", ws["J10"].value == "—")
    cal = wb[B.S_CAL]
    check(f"{ed} blank priorities message", cal[f"K{B.G0 + 1}"].value == "Add priorities in the table below ↓")
    check(f"{ed} blank completion", cal[f"L{B.G0 + 12}"].value == "—")


def main():
    for ed, folder, suf in (("excel", "Excel", "Excel"), ("gsheets", "Google_Sheets", "GoogleSheets")):
        demo = DIST / folder / f"Weekly_Planner_Pro_{suf}_DEMO.xlsx"
        blank = DIST / folder / f"Weekly_Planner_Pro_{suf}_BLANK.xlsx"
        check_structure(demo, ed)
        check_demo(demo, ed)
        check_blank(blank, ed)
    scenarios(DIST / "Google_Sheets" / "Weekly_Planner_Pro_GoogleSheets_DEMO.xlsx")
    print(f"PASSED {passes} checks, FAILED {len(fails)}")
    for f in fails[:40]:
        print("  FAIL", f)
    return not fails


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
