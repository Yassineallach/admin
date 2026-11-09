"""Future-date stress test: the templates must keep working when the date changes (the top complaint in this niche).

Weekly Planner Pro: today = 29 Feb 2028 (leap day), Week 1 left blank, Sunday start.
Budget:            budget year 2027 starting in July (crosses New Year), today = 29 Feb 2028.
Project Manager:   today = 29 Feb 2028 and 1 Jan 2030.
Each case: zero formula errors + spot checks of date-driven results.
"""
import datetime as dt
import sys

import build_budget as B
import build_weekly_planner as W
import sample_data_bg as SD
import validate_budget as VB

fails, passes = [], 0


def check(label, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(f"{label}  {detail}")


D = dt.datetime(2028, 2, 29)
root = VB.DIST.parent

# ---- Weekly Planner Pro
def edit_wp(wb):
    s = wb["Setup"]
    s["C19"], s["C18"], s["C17"] = D, None, "Sunday"
    wb["Monthly Calendar"]["C5"], wb["Monthly Calendar"]["E5"] = 2028, "February"
for ed in ("Excel", "GoogleSheets"):
    res, wb = VB.recalc(root / "03_Weekly_Planner_Pro" / ("Excel" if ed == "Excel" else "Google_Sheets") / f"Weekly_Planner_Pro_{ed}_DEMO.xlsx", edit_wp)
    check(f"WP {ed} leap day: no errors", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
    check(f"WP {ed} week 1 = Sunday 27 Feb 2028", VB.as_date(wb["Setup"]["C21"].value) == dt.date(2028, 2, 27), wb["Setup"]["C21"].value)
    check(f"WP {ed} week 6 follows", VB.as_date(wb["Week 6"]["N3"].value) == dt.date(2028, 4, 2))
    cal = wb["Monthly Calendar"]
    days = [VB.as_date(cal[f"{c}{9 + w * 5}"].value) for w in range(6) for c in "BCDEFGH"]
    check(f"WP {ed} calendar has 29 Feb", dt.date(2028, 2, 29) in days and days[0] == dt.date(2028, 1, 30), str(days[0]))

# ---- Budget
def edit_bg(wb):
    s = wb[B.S_SET]
    s["C12"], s["C13"], s["C17"] = 2027, "July", D
for ed in ("Excel", "GoogleSheets"):
    res, wb = VB.recalc(root / "04_Ultimate_Budget_Spreadsheet" / ("Excel" if ed == "Excel" else "Google_Sheets") / f"Ultimate_Budget_Spreadsheet_{ed}_DEMO.xlsx", edit_bg)
    check(f"BG {ed} July-2027 budget: no errors", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
    at = wb[B.S_AT]
    check(f"BG {ed} labels", at[f"B{B.AT1}"].value == "July 2027" and at[f"B{B.AT1 + 11}"].value == "June 2028")
    feb = wb["February"]
    check(f"BG {ed} February tab = Feb 2028, month 8", feb["P2"].value == 8 and VB.as_date(feb["P3"].value) == dt.date(2028, 2, 1))
    # recurring items still post: rent once a month Jul 2027..Feb 2028; salary every 14 days from 9 Jan 2026
    rows = {at[f"B{r}"].value: r for r in range(B.MX1, B.MXN + 1) if at[f"B{r}"].value}
    rent = [at.cell(row=rows["Rent"], column=6 + k).value for k in range(12)]
    check(f"BG {ed} rent posts Jul–Feb, not after today", rent == [1450] * 8 + [0] * 4, str(rent))
    d, cnt = dt.date(2026, 1, 9), 0
    while d <= D.date():
        cnt += (d.year, d.month) == (2028, 2)
        d += dt.timedelta(days=14)
    check(f"BG {ed} biweekly salary in Feb 2028", abs(at.cell(row=rows["Salary"], column=6 + 7).value - 2400 * cnt) < 0.01,
          f"{at.cell(row=rows['Salary'], column=13).value} vs {2400 * cnt}")
    nxt = wb[B.S_RT][f"K{B.RT1 + 1}"].value          # rent: next payment on/after 29 Feb 2028 -> 1 Mar 2028
    check(f"BG {ed} next rent date", VB.as_date(nxt) == dt.date(2028, 3, 1), nxt)
    cal = wb[B.S_CAL]
    check(f"BG {ed} calendar month", VB.as_date(cal["Y2"].value) == dt.date(2028, 2, 1), cal["Y2"].value)
    check(f"BG {ed} language app ended", wb[B.S_RT][f"K{B.RT1 + 11}"].value == "Ended")

# ---- Project Manager
import sample_data_pm  # noqa
for day in (D, dt.datetime(2030, 1, 1)):
    def edit_pm(wb, day=day):
        wb["Setup"]["C19"] = day
    res, wb = VB.recalc(root / "01_Ultimate_Project_Manager" / "Google_Sheets" / "Ultimate_Project_Manager_GoogleSheets_DEMO.xlsx", edit_pm)
    check(f"PM today={day.date()}: no errors", res.get("total_errors", 1) == 0, str(res.get("error_summary")))
    check(f"PM today={day.date()}: effective today", VB.as_date(wb["Setup"]["C20"].value) == day.date())

print(f"PASSED {passes} checks, FAILED {len(fails)}")
for f in fails:
    print("  FAIL", f)
sys.exit(1 if fails else 0)
