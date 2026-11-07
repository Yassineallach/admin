"""Independent QA for PRODUCT 1.

1. Recalculates each built workbook in LibreOffice (headless) and requires 0 formula errors.
2. Re-computes key results in plain Python from the DEMO data and compares them with the
   values the spreadsheet formulas produced (KPIs, project roll-ups, recurring next dates,
   Kanban, calendar, Gantt, Task Filter, Decision Matrix).

Usage: python validate_project_manager.py [--recalc PATH_TO_recalc.py]
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import glob
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sample_data_pm as SD  # noqa: E402
import build_project_manager as B  # noqa: E402
import dashboard_v2 as DP  # noqa: E402
B.Builder('excel', True).build()  # populates DP.DASH (cell map)

DIST = HERE.parent / "dist" / "01_Ultimate_Project_Manager"
fails: list[str] = []
passes = 0


def check(label, got, exp, tol=1e-6):
    global passes
    ok = (abs(float(got) - float(exp)) <= tol) if isinstance(exp, (int, float)) and not isinstance(exp, bool) and got not in (None, "") else got == exp
    if ok:
        passes += 1
    else:
        fails.append(f"{label}: got {got!r}, expected {exp!r}")


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    return v


def recalc(path: Path, script: str) -> Path:
    tmp = Path(tempfile.mkdtemp()) / path.name
    shutil.copy(path, tmp)
    out = subprocess.run([sys.executable, script, str(tmp), "300"], capture_output=True, text=True)
    res = json.loads(out.stdout)
    if res.get("status") != "success" or res.get("total_errors"):
        fails.append(f"{path.name}: recalc {res}")
    else:
        print(f"  {path.name}: {res['total_formulas']} formulas, 0 errors")
    return tmp


def validate_demo(p: Path):
    wb = load_workbook(p, data_only=True)
    today = as_date(wb[B.S_SETUP]["C20"].value)
    print("  effective today in workbook:", today)
    tasks = SD.build_tasks()
    done = "Completed"
    # ---------------- dashboard v2 (cell map published by dashboard_v2.DASH)
    Dm = wb[B.S_DASH]
    M_ = DP.DASH
    g = lambda k: Dm[M_[k]].value
    from openpyxl.utils import column_index_from_string as _ci, get_column_letter as _gl
    import re as _re

    def cr(a):
        m = _re.match(r"([A-Z]+)(\d+)", a)
        return _ci(m.group(1)), int(m.group(2))

    def at(a, dc=0, dr=0):
        c, r = cr(a)
        return Dm.cell(row=r + dr, column=c + dc).value
    # default period: first month of the current quarter .. current month, current year
    yr = g("year")
    mf, mt = g("from_"), g("to")
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    check("Period default year", yr, today.year)
    check("Period default from", mf, months[((today.month - 1) // 3) * 3])
    check("Period default to", mt, months[today.month - 1])
    lo, hi = sorted((months.index(mf) + 1, months.index(mt) + 1))
    p_start = dt.date(yr, lo, 1)
    p_end = dt.date(yr + (hi // 12), hi % 12 + 1, 1)
    check("Period start", as_date(g("start")), p_start)
    check("Period end", as_date(g("end")), p_end)
    in_p = [t for t in tasks if p_start <= t["due"] < p_end]
    done_p = sum(t["status"] == done for t in in_p)
    check("Tasks due in period", g("tasks_p"), len(in_p))
    check("Done in period", g("done_p"), done_p)
    check("Completion in period", g("compl_p"), done_p / len(in_p) if in_p else 0)
    check("Active projects", g("active_proj"), sum(p[7] in ("Planning", "In Progress") for p in SD.PROJECTS))
    spent = sum(b[3] for b in SD.BUDGET if p_start <= SD.d(b[4]) < p_end)
    check("Spent in period", g("spent_p"), spent)
    plan = sum(b[2] for b in SD.BUDGET)
    act = sum(b[3] for b in SD.BUDGET)
    check("Planned (all)", g("planned"), plan)
    check("Actual (all)", g("actual"), act)
    check("Budget used", g("used"), act / plan)
    overdue = [t for t in tasks if t["status"] != done and t["due"] < today]
    check("Overdue (all)", g("overdue"), len(overdue))
    check("Tile tasks", g("tile_tasks"), len(in_p))
    check("Tile spent text", g("tile_spent"), f"${spent:,.0f}")
    check("Tile completion", g("tile_completion"), done_p / len(in_p) if in_p else 0)
    check("Tile budget used", g("tile_budget"), act / plan)
    # monthly series for the selected year
    for m in range(1, 13):
        due_m = [t for t in tasks if t["due"].year == yr and t["due"].month == m]
        inr = lo <= m <= hi
        check(f"Month {m} in-period bar", at(M_["month_first"], 1, m - 1), len(due_m) if inr else 0)
        check(f"Month {m} other bar", at(M_["month_first"], 2, m - 1), 0 if inr else len(due_m))
        check(f"Month {m} completed line", at(M_["month_first"], 3, m - 1), sum(t["status"] == done for t in due_m))
        pm = sum(b[2] for b in SD.BUDGET if SD.d(b[4]).year == yr and SD.d(b[4]).month == m)
        am = sum(b[3] for b in SD.BUDGET if SD.d(b[4]).year == yr and SD.d(b[4]).month == m)
        check(f"Month {m} planned", at(M_["month_first"], 4, m - 1), pm)
        check(f"Month {m} actual", at(M_["month_first"], 5, m - 1), am)
    check("Donut done", at(M_["donut_first"]), done_p)
    check("Donut open", at(M_["donut_first"], 0, 1), (len(in_p) - done_p) if in_p else 1)
    # project progress bars (drawn top-down: project 1 at the top -> stored in reverse)
    for i in range(5):
        pr = SD.PROJECTS[4 - i]
        pt = [t for t in tasks if t["project"] == pr[0]]
        eff = [1.0 if t["status"] == done else (t["prog"] or 0) for t in pt]
        exp_prog = 1.0 if pr[7] == "Completed" else (sum(eff) / len(eff) if eff else 0)
        check(f"Progress bar {i} name", at(M_["proj_first"], 0, i), pr[0])
        check(f"Progress bar {i} value", at(M_["proj_first"], 2, i), exp_prog)
    for i, cat in enumerate(SD.TASK_CATS):
        check(f"Radar {cat} open", at(M_["radar_first"], 1, i), sum(t["cat"] == cat and t["status"] != done for t in tasks))
        check(f"Radar {cat} done", at(M_["radar_first"], 2, i), sum(t["cat"] == cat and t["status"] == done for t in tasks))
    for i, (nm, _, _) in enumerate(SD.TEAM):
        check(f"Team {nm} open", at(M_["team_first"], 1, i), sum(t["who"] == nm and t["status"] != done for t in tasks))
        check(f"Team {nm} overdue", at(M_["team_first"], 2, i), sum(t["who"] == nm and t in overdue for t in tasks))
    up = sorted([(t["due"], i) for i, t in enumerate(tasks) if t["status"] != done and t["due"] >= today])[:8]
    mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for k, (due, i) in enumerate(up):
        check(f"Upcoming #{k + 1} name", at(M_["up_first"], 0, k), tasks[i]["name"])
        check(f"Upcoming #{k + 1} due", at(M_["up_due_first"], 0, k), f"{mon[due.month - 1]} {due.day}")
    od = sorted([(t["due"], i) for i, t in enumerate(tasks) if t["status"] != done and t["due"] < today])[:8]
    for k, (due, i) in enumerate(od):
        check(f"Overdue #{k + 1} name", at(M_["od_first"], 0, k), tasks[i]["name"])
        check(f"Overdue #{k + 1} late", at(M_["od_late_first"], 0, k), f"{(today - due).days} d")

    # ---------------- project overview roll-ups
    P = wb[B.S_POV]
    for i, pr in enumerate(SD.PROJECTS):
        r = B.R1 + i
        pt = [t for t in tasks if t["project"] == pr[0]]
        eff = [1.0 if t["status"] == done else (t["prog"] or 0) for t in pt]
        exp_prog = 1.0 if pr[7] == "Completed" else (sum(eff) / len(eff) if eff else 0)
        check(f"{pr[0]} progress", P[f"K{r}"].value, exp_prog)
        check(f"{pr[0]} budget", P[f"L{r}"].value, sum(b[2] for b in SD.BUDGET if b[0] == i + 1))
        check(f"{pr[0]} actual", P[f"M{r}"].value, sum(b[3] for b in SD.BUDGET if b[0] == i + 1))
        check(f"{pr[0]} tasks", P[f"P{r}"].value, len(pt))
        check(f"{pr[0]} done", P[f"Q{r}"].value, sum(t["status"] == done for t in pt))
        if pr[7] not in ("Completed", "Cancelled"):
            check(f"{pr[0]} days remaining", P[f"O{r}"].value, (pr[5] - today).days)

    # ---------------- recurring next occurrence (independent implementation)
    R = wb[B.S_RT]
    steps = {f: (u, s) for f, u, s in B.FREQ}
    for i, (n, pr, cat, who, fq, cu, so, eo, pri, st, lc, cnt) in enumerate(SD.RECURRING):
        r = B.R1 + i
        start = SD.d(so)
        end = SD.d(eo) if eo is not None else None
        base = max(today, SD.d(lc) + dt.timedelta(days=1))
        unit, step = steps[fq]
        step = cu if fq == "Custom" else step
        if st == "Paused":
            exp = "Paused"
        else:
            k = 0
            while True:
                if unit == "D":
                    cand = start + dt.timedelta(days=step * k)
                else:
                    mm = start.month - 1 + step * k
                    y, m = start.year + mm // 12, mm % 12 + 1
                    cand = dt.date(y, m, min(start.day, calendar.monthrange(y, m)[1]))
                if cand >= base:
                    break
                k += 1
            exp = "Ended" if end and cand > end else cand
        check(f"Recurring '{n}' next", as_date(R[f"N{r}"].value), exp)
        # occurrences this month
        if st != "Paused":
            ms = today.replace(day=1)
            me = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            me2 = min(me, end) if end else me
            cnt_m = 0
            k = 0
            while True:
                if unit == "D":
                    cand = start + dt.timedelta(days=step * k)
                else:
                    mm = start.month - 1 + step * k
                    y, m = start.year + mm // 12, mm % 12 + 1
                    cand = dt.date(y, m, min(start.day, calendar.monthrange(y, m)[1]))
                if cand > me2:
                    break
                if cand >= ms:
                    cnt_m += 1
                k += 1
            check(f"Recurring '{n}' this month", R[f"P{r}"].value, cnt_m)

    # ---------------- kanban
    K = wb[B.S_KB]
    for j, st in enumerate(B.LISTS["E"][1][:5]):
        c = B.L(2 + j * 3)
        exp_n = sum(t["status"] == st for t in tasks)
        check(f"Kanban {st} count", K[f"{c}6"].value.split(" ")[0], str(exp_n))
        first = next((t for t in tasks if t["status"] == st), None)
        if first:
            got = K[f"{c}8"].value.lstrip("‼▲ ")
            check(f"Kanban {st} first card", got, first["name"])

    # ---------------- monthly calendar (current month)
    M = wb[B.S_MCAL]
    gs = as_date(M["Q7"].value)
    first_of = today.replace(day=1)
    exp_gs = first_of - dt.timedelta(days=first_of.weekday())  # Monday start
    check("Calendar grid start", gs, exp_gs)
    for w in range(6):
        for d in range(7):
            day = gs + dt.timedelta(days=w * 7 + d)
            c = B.L(2 + d)
            base = 9 + w * 5
            due_today = [t["name"] for t in tasks if t["due"] == day]
            exp1 = due_today[0] if (due_today and day.month == today.month) else ""
            got1 = M[f"{c}{base + 1}"].value or ""
            check(f"Calendar {day} item1", got1, exp1)
            dl = [p[0] for p in SD.PROJECTS if p[5] == day]
            exp3 = ("▲ " + dl[0]) if (dl and day.month == today.month) else ""
            check(f"Calendar {day} deadline", M[f"{c}{base + 3}"].value or "", exp3)
    check("Calendar month tasks due", M["K10"].value, sum(t["due"].year == today.year and t["due"].month == today.month for t in tasks))

    # ---------------- weekly calendar
    W = wb[B.S_WCAL]
    check("Weekly start", as_date(W["C6"].value), today - dt.timedelta(days=today.weekday()))
    monday = SD.ANCHOR - dt.timedelta(days=SD.ANCHOR.weekday())
    if monday == as_date(W["C6"].value):
        exp_hours = sum(x[3] for x in SD.SCHEDULE if x[0] < 7)
        check("Weekly scheduled hours", W["E6"].value, exp_hours)
        dd, h, m, dur, task = SD.SCHEDULE[1]
        cell = W[f"{B.L(3 + dd)}{11 + h - 7}"].value
        check("Weekly slot shows task", cell.split(" · ")[0], task)
        cont = W[f"{B.L(3 + dd)}{11 + h - 7 + 1}"].value
        check("Weekly continuation marker", cont, "⋮")

    # ---------------- gantt (all projects, show done)
    G = wb[B.S_GC]
    check("Gantt tasks shown", G["K6"].value, sum(1 for t in tasks if t["start"] and t["due"]))
    check("Gantt row1 task", G["C10"].value, tasks[0]["name"])

    # ---------------- task filter (demo default: Completion = Incomplete)
    TF = wb[B.S_TF]
    check("Filter incomplete count", TF["F6"].value, sum(t["status"] != done for t in tasks))

    # ---------------- decision matrix
    DM = wb[B.S_DM]
    tw = sum(c[1] for c in SD.DECISION["criteria"])
    tots = [sum(c[1] * c[2 + j] for c in SD.DECISION["criteria"]) / tw for j in range(3)]
    for j, col_ in enumerate("GHI"):
        check(f"Decision total {j}", DM[f"{col_}20"].value, tots[j])
    check("Decision winner", DM["C24"].value, SD.DECISION["options"][tots.index(max(tots))])

    # ---------------- project manager panel
    PM = wb[B.S_PM]
    check("PM selected id", PM["C8"].value, "P-001")
    check("PM objectives #1", PM["B32"].value, SD.DETAILS[0][2])


def validate_blank(p: Path):
    wb = load_workbook(p, data_only=True)
    D = wb[B.S_DASH]
    M_ = DP.DASH
    for k in ("tasks_p", "done_p", "compl_p", "active_proj", "spent_p", "planned", "actual", "used", "overdue"):
        check(f"blank {k}", D[M_[k]].value, 0)
    check("blank spent text", D[M_["tile_spent"]].value, "$0")
    check("blank upcoming message", D[M_["up_first"]].value, "No upcoming deadlines")
    check("blank overdue message", D[M_["od_first"]].value, "No overdue tasks")
    check("blank TF message", wb[B.S_TF]["D19"].value, "No tasks match these filters.")
    check("blank gantt message", wb[B.S_GC]["C10"].value, "No tasks to show yet")


def main():
    ap = argparse.ArgumentParser()
    default = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [""])[0]
    ap.add_argument("--recalc", default=default)
    a = ap.parse_args()
    for f in sorted(DIST.glob("*/*.xlsx")):
        print(f"\n== {f.relative_to(DIST)}")
        wb = load_workbook(f)
        check(f"{f.name} tab count", len(wb.sheetnames), 15)
        check(f"{f.name} tab names", wb.sheetnames, B.ORDER)
        t = recalc(f, a.recalc)
        (validate_demo if "DEMO" in f.name else validate_blank)(t)
    print(f"\nPASSED {passes} checks, FAILED {len(fails)}")
    for x in fails:
        print("  FAIL", x)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
