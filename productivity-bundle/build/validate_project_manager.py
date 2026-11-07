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
    # ---------------- dashboard KPIs
    D = wb[B.S_DASH]
    n_proj = len(SD.PROJECTS)
    check("KPI total projects", D["B8"].value, n_proj)
    check("KPI active projects", D["D8"].value, sum(p[7] in ("Planning", "In Progress") for p in SD.PROJECTS))
    check("KPI completed projects", D["F8"].value, sum(p[7] == "Completed" for p in SD.PROJECTS))
    check("KPI overdue projects", D["H8"].value, sum(p[7] not in ("Completed", "Cancelled") and p[5] < today for p in SD.PROJECTS))
    check("KPI total tasks", D["J8"].value, len(tasks))
    n_done = sum(t["status"] == done for t in tasks)
    check("KPI completed tasks", D["L8"].value, n_done)
    check("KPI pending", D["N8"].value, len(tasks) - n_done)
    check("KPI completion rate", D["B12"].value, n_done / len(tasks))
    plan = sum(b[2] for b in SD.BUDGET)
    act = sum(b[3] for b in SD.BUDGET)
    check("KPI budget", D["D12"].value, plan)
    check("KPI actual", D["F12"].value, act)
    check("KPI remaining", D["H12"].value, plan - act)
    ws_ = today - dt.timedelta(days=today.weekday())
    check("KPI due this week", D["L12"].value,
          sum(ws_ <= t["due"] <= ws_ + dt.timedelta(days=6) and t["status"] != done for t in tasks))
    overdue = [t for t in tasks if t["status"] != done and t["due"] < today]
    check("KPI overdue tasks", D["N12"].value, len(overdue))
    # upcoming list order
    up = sorted([(t["due"], i) for i, t in enumerate(tasks) if t["status"] != done and t["due"] >= today])[:8]
    for k, (due, i) in enumerate(up):
        check(f"Upcoming #{k + 1} name", D[f"B{48 + k}"].value, tasks[i]["name"])
        check(f"Upcoming #{k + 1} due", as_date(D[f"H{48 + k}"].value), due)
    od = sorted([(t["due"], i) for i, t in enumerate(tasks) if t["status"] != done and t["due"] < today])[:8]
    for k, (due, i) in enumerate(od):
        check(f"Overdue #{k + 1} name", D[f"I{48 + k}"].value, tasks[i]["name"])
        check(f"Overdue #{k + 1} days late", D[f"O{48 + k}"].value, (today - due).days)
    # monthly chart data for chart year
    yr = D["M3"].value
    for m in range(1, 13):
        due_m = [t for t in tasks if t["due"].year == yr and t["due"].month == m]
        check(f"Chart month {m} due", D[f"V{16 + m}"].value, len(due_m))
        check(f"Chart month {m} done", D[f"W{16 + m}"].value, sum(t["status"] == done for t in due_m))
    # status donut
    for i, st in enumerate(B.LISTS["F"][1]):
        check(f"Donut {st}", D[f"R{17 + i}"].value, sum(p[7] == st for p in SD.PROJECTS))

    # ---------------- project overview roll-ups
    P = wb[B.S_POV]
    for i, pr in enumerate(SD.PROJECTS):
        r = 7 + i
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
        r = 7 + i
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
    gs = as_date(M["K7"].value)
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
    check("Gantt tasks shown", G["J6"].value, sum(1 for t in tasks if t["start"] and t["due"]))
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
    for a in ("B8", "D8", "J8", "L8", "N8", "B12", "D12", "H12", "N12"):
        check(f"blank KPI {a}", D[a].value, 0)
    check("blank upcoming message", D["B48"].value, "No upcoming deadlines — nice!")
    check("blank TF message", wb[B.S_TF]["D19"].value, "No tasks match these filters.")
    check("blank gantt message", wb[B.S_GC]["C10"].value, "No tasks to show — add tasks with start and due dates.")


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
