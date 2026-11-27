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
import dashboard_v3 as DP  # noqa: E402
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
    # ---------------- shared expectations
    Dm = wb[B.S_DASH]
    M_ = DP.DASH
    g = lambda k: Dm[M_[k]].value
    from openpyxl.utils import column_index_from_string as _ci
    import re as _re

    def cr(a):
        m = _re.match(r"([A-Z]+)(\d+)", a)
        return _ci(m.group(1)), int(m.group(2))

    def at(a, dc=0, dr=0):
        c, r = cr(a)
        return Dm.cell(row=r + dr, column=c + dc).value
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    mon3 = [m[:3] for m in months]
    money = lambda x: f"${x:,.0f}"
    overdue = [t for t in tasks if t["status"] != done and t["due"] < today]
    n_done = sum(t["status"] == done for t in tasks)
    plan = sum(b[2] for b in SD.BUDGET)
    act = sum(b[3] for b in SD.BUDGET)
    proj_actual = {i + 1: sum(b[3] for b in SD.BUDGET if b[0] == i + 1) for i in range(len(SD.PROJECTS))}
    proj_budget = {i + 1: sum(b[2] for b in SD.BUDGET if b[0] == i + 1) for i in range(len(SD.PROJECTS))}

    def health(i, pr):
        if pr[7] == "Completed":
            return "Completed"
        if pr[7] == "Cancelled":
            return "Cancelled"
        if pr[5] < today:
            return "Overdue"
        if proj_budget[i + 1] > 0 and proj_actual[i + 1] > proj_budget[i + 1]:
            return "Over budget"
        if any(t["project"] == pr[0] for t in overdue):
            return "At risk"
        return "On track"

    def proj_progress(pr):
        pt = [t for t in tasks if t["project"] == pr[0]]
        eff = [1.0 if t["status"] == done else (t["prog"] or 0) for t in pt]
        return 1.0 if pr[7] == "Completed" else (sum(eff) / len(eff) if eff else 0)

    # recurring occurrences (independent implementation)
    steps = {f: (u, st_) for f, u, st_ in B.FREQ}

    def add_months(d0, n):
        mm = d0.month - 1 + n
        y, m = d0.year + mm // 12, mm % 12 + 1
        return dt.date(y, m, min(d0.day, calendar.monthrange(y, m)[1]))

    def occurs(rec, day):
        n, pr, cat, who, fq, cu, so, eo, pri, st, lc, cnt = rec
        if st == "Paused":
            return False
        start, end = SD.d(so), (SD.d(eo) if eo is not None else None)
        unit, step = steps[fq]
        step = cu if fq == "Custom" else step
        if day < start or (end and day > end):
            return False
        if unit == "D":
            return (day - start).days % step == 0
        md = (day.year - start.year) * 12 + day.month - start.month
        return md % step == 0 and add_months(start, md) == day

    def next_occ(rec):
        n, pr, cat, who, fq, cu, so, eo, pri, st, lc, cnt = rec
        if st == "Paused":
            return None
        start, end = SD.d(so), (SD.d(eo) if eo is not None else None)
        base = max(today, SD.d(lc) + dt.timedelta(days=1))
        unit, step = steps[fq]
        step = cu if fq == "Custom" else step
        k = 0
        while True:
            cand = start + dt.timedelta(days=step * k) if unit == "D" else add_months(start, step * k)
            if cand >= base:
                break
            k += 1
        return None if (end and cand > end) else cand

    # ---------------- dashboard v3 tiles / strip
    check("Setup dashboard title", g("header_title"), "Project Command Center")
    check("Demo date frozen", wb[B.S_SETUP]["C19"].value is not None, True)
    yr, mf, mt = g("year"), g("from_"), g("to")
    check("Period default year", yr, today.year)
    check("Period default from", mf, months[((today.month - 1) // 3) * 3])
    check("Period default to", mt, months[today.month - 1])
    lo, hi = sorted((months.index(mf) + 1, months.index(mt) + 1))
    p_start, p_end = dt.date(yr, lo, 1), dt.date(yr + (hi // 12), hi % 12 + 1, 1)
    in_p = [t for t in tasks if p_start <= t["due"] < p_end]
    spent_p = sum(b[3] for b in SD.BUDGET if p_start <= SD.d(b[4]) < p_end)
    active = sum(p[7] in ("Planning", "In Progress") for p in SD.PROJECTS)
    comp_p = sum(p[7] == "Completed" for p in SD.PROJECTS)
    od_p = sum(p[7] not in ("Completed", "Cancelled") and p[5] < today for p in SD.PROJECTS)
    check("Tile projects value", g("tile_projects"), active)
    check("Tile projects sub", g("tile_projects_sub"), f"{len(SD.PROJECTS)} total · {comp_p} done · {od_p} overdue")
    check("Tile completion value", g("tile_completion"), n_done / len(tasks))
    check("Tile completion sub", g("tile_completion_sub"), f"{len(tasks)} tasks · {n_done} done · {len(tasks) - n_done} pending")
    check("Tile budget value", g("tile_budget"), money(plan - act))
    check("Tile budget sub", g("tile_budget_sub"), f"of {money(plan)} · {money(act)} spent")
    check("Tile period value", g("tile_period"), len(in_p))
    plabel = mon3[lo - 1] + ("" if lo == hi else "–" + mon3[hi - 1]) + f" {yr}"
    check("Tile period sub", g("tile_period_sub"), f"{money(spent_p)} spent · {plabel}")
    due_today = [t for t in tasks if t["due"] == today]
    ws_ = today - dt.timedelta(days=today.weekday())
    week_open = sum(ws_ <= t["due"] <= ws_ + dt.timedelta(days=6) and t["status"] != done for t in tasks)
    rec_today = [r_[0] for r_ in SD.RECURRING if occurs(r_, today)]
    check("Pill due today", g("pill_today"), f"●  {len(due_today)} due today")
    check("Pill week", g("pill_week"), f"●  {week_open} open, due this week")
    check("Pill overdue", g("pill_overdue"), f"●  {len(overdue)} overdue tasks")
    check("Pill recurring", g("pill_recurring"), f"↻  {len(rec_today)} recurring today")
    check("Budget used", g("used"), act / plan)
    check("Revenue total", g("revenue"), sum(x or 0 for x in SD.REVENUE))
    # ---------------- charts data
    for m in range(1, 13):
        due_m = [t for t in tasks if t["due"].year == yr and t["due"].month == m]
        inr = lo <= m <= hi
        check(f"Month {m} in-period", at(M_["month_first"], 1, m - 1), len(due_m) if inr else 0)
        check(f"Month {m} other", at(M_["month_first"], 2, m - 1), 0 if inr else len(due_m))
        comp_m = sum(1 for t in tasks if t["status"] == done and (t["completed_on"] or t["due"]).year == yr
                     and (t["completed_on"] or t["due"]).month == m)
        check(f"Month {m} completed (by completion date)", at(M_["month_first"], 3, m - 1), comp_m)
    for i, st_ in enumerate(B.LISTS["F"][1]):
        check(f"Status donut {st_}", at(M_["status_first"], 0, i), sum(p[7] == st_ for p in SD.PROJECTS))
    for i in range(5):
        pr = SD.PROJECTS[4 - i]
        check(f"Progress bar {i} name", at(M_["proj_first"], 0, i), pr[0])
        check(f"Progress bar {i} value", at(M_["proj_first"], 2, i), proj_progress(pr))
    for i in range(8):
        pi_ = 8 - i
        check(f"Budget chart {i} name", at(M_["budget_first"], 0, i), SD.PROJECTS[pi_ - 1][0])
        check(f"Budget chart {i} budget", at(M_["budget_first"], 1, i), proj_budget[pi_])
        check(f"Budget chart {i} actual", at(M_["budget_first"], 2, i), proj_actual[pi_])
    for k, pname in enumerate(B.LISTS["D"][1]):
        check(f"Priority {pname}", at(M_["priority_first"], 0, k), sum(t["pri"] == pname and t["status"] != done for t in tasks))
    for i, (nm, _, _) in enumerate(SD.TEAM):
        check(f"Team {nm} open", at(M_["team_first"], 1, i), sum(t["who"] == nm and t["status"] != done for t in tasks))
        check(f"Team {nm} overdue", at(M_["team_first"], 2, i), sum(t["who"] == nm and t in overdue for t in tasks))
    # ---------------- lists
    exp_today = [t["name"] for t in due_today] + ["↻ " + n for n in rec_today]
    for k in range(8):
        exp = exp_today[k] if k < len(exp_today) else ("Nothing due today" if k == 0 else "")
        check(f"Due today #{k + 1}", at(M_["today_first"], 0, k) or "", exp)
    up = sorted([(t["due"], i) for i, t in enumerate(tasks) if t["status"] != done and t["due"] >= today])[:8]
    for k, (due, i) in enumerate(up):
        check(f"Upcoming #{k + 1}", at(M_["up_first"], 0, k), tasks[i]["name"])
        check(f"Upcoming #{k + 1} due", at(M_["up_due_first"], 0, k), f"{mon3[due.month - 1]} {due.day}")
    od = sorted([(t["due"], i) for i, t in enumerate(tasks) if t["status"] != done and t["due"] < today])[:8]
    for k, (due, i) in enumerate(od):
        check(f"Overdue #{k + 1}", at(M_["od_first"], 0, k), tasks[i]["name"])
        check(f"Overdue #{k + 1} late", at(M_["od_late_first"], 0, k), f"{(today - due).days} d")
    for i, pr in enumerate(SD.PROJECTS):
        check(f"Perf {i + 1} name", at(M_["perf_first"], 0, i), pr[0])
        check(f"Perf {i + 1} health", at(M_["perf_health_first"], 0, i), health(i, pr))
        rev = SD.REVENUE[i]
        check(f"Perf {i + 1} margin", at(M_["perf_margin_first"], 0, i),
              "—" if not rev else f"{round((rev - proj_actual[i + 1]) / rev * 100):.0f}%")
    dls = sorted([(p[5], i) for i, p in enumerate(SD.PROJECTS) if p_start <= p[5] < p_end])[:8]
    for k, (dd, i) in enumerate(dls):
        check(f"Deadline in period #{k + 1}", at(M_["deadline_first"], 0, k), SD.PROJECTS[i][0])
    nexts = sorted([(no, i) for i, r_ in enumerate(SD.RECURRING) if (no := next_occ(r_)) and (no - today).days <= 6])[:8]
    for k, (no, i) in enumerate(nexts):
        check(f"Recurring this week #{k + 1}", at(M_["recurring_first"], 0, k), "↻ " + SD.RECURRING[i][0])
    # ---------------- recurring on the calendars
    MC = wb[B.S_MCAL]
    gs = as_date(MC["Q7"].value)
    for w in range(6):
        for d in range(7):
            day = gs + dt.timedelta(days=w * 7 + d)
            if day.month != as_date(MC["Q6"].value).month:
                continue
            items = [t["name"] for t in tasks if t["due"] == day] + ["↻ " + r_[0] for r_ in SD.RECURRING if occurs(r_, day)]
            for k in (1, 2):
                exp = items[k - 1] if len(items) >= k else ""
                check(f"Calendar {day} slot {k}", MC.cell(row=9 + w * 5 + k, column=2 + d).value or "", exp)
    WC = wb[B.S_WCAL]
    wstart = as_date(WC["C6"].value)
    for d in range(7):
        day = wstart + dt.timedelta(days=d)
        items = [t["name"] for t in tasks if t["due"] == day] + ["↻ " + r_[0] for r_ in SD.RECURRING if occurs(r_, day)]
        for k in (1, 2, 3):
            exp = items[k - 1] if len(items) >= k else ""
            check(f"Weekly {day} slot {k}", WC.cell(row=26 + k, column=3 + d).value or "", exp)
    # ---------------- Eisenhower matrix
    DMx = wb[B.S_DM]
    quad = lambda t: (None if t["status"] == done or (t["urgent"] is None and t["important"] is None) else
                      ("Do first" if t["urgent"] == "Yes" and t["important"] == "Yes" else "Delegate" if t["urgent"] == "Yes"
                       else "Schedule" if t["important"] == "Yes" else "Eliminate"))
    for name, c1, r0 in (("Do first", 2, 34), ("Schedule", 6, 34), ("Delegate", 2, 45), ("Eliminate", 6, 45)):
        names = [t["name"] for t in tasks if quad(t) == name]
        check(f"Eisenhower {name} header", DMx.cell(row=r0, column=c1).value.endswith(f"({len(names)})"), True)
        for k in range(min(8, len(names))):
            check(f"Eisenhower {name} #{k + 1}", DMx.cell(row=r0 + 1 + k, column=c1).value, names[k])
    # ---------------- revenue / margin on Project Overview & Project Manager
    P_ = wb[B.S_POV]
    for i, pr in enumerate(SD.PROJECTS):
        r = B.R1 + i
        rev = SD.REVENUE[i]
        if rev:
            check(f"{pr[0]} profit", P_[f"X{r}"].value, rev - proj_actual[i + 1])
            check(f"{pr[0]} margin", P_[f"Y{r}"].value, (rev - proj_actual[i + 1]) / rev)
    PMx = wb[B.S_PM]
    check("PM revenue", PMx["G12"].value, SD.REVENUE[0])
    check("PM margin", PMx["G13"].value, (SD.REVENUE[0] - proj_actual[1]) / SD.REVENUE[0])

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
            if due_today and day.month == today.month:   # one-time tasks always come before recurring items
                check(f"Calendar {day} item1", M[f"{c}{base + 1}"].value or "", due_today[0])
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
    for k in ("total_projects", "active_projects", "total_tasks", "done_tasks", "completion", "planned", "actual", "remaining",
              "tasks_p", "spent_p", "overdue_tasks", "due_today", "recurring_today"):
        check(f"blank {k}", D[M_[k]].value, 0)
    check("blank budget tile", D[M_["tile_budget"]].value, "$0")
    check("blank due today", D[M_["today_first"]].value, "Nothing due today")
    check("blank upcoming", D[M_["up_first"]].value, "No upcoming deadlines")
    check("blank overdue", D[M_["od_first"]].value, "No overdue tasks")
    check("blank perf", D[M_["perf_first"]].value, "No projects yet")
    check("blank recurring", D[M_["recurring_first"]].value, "Nothing recurring this week")
    check("blank demo date not frozen", wb[B.S_SETUP]["C19"].value, None)
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
