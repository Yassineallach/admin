"""Tests for the Home Daycare Tax Workbook.

1. LibreOffice recalculation: zero formula errors in both versions.
2. Known examples (built in the blank workbook): no exclusive space 1,000/2,000 sq ft at 23 % time = 11.5 %; exclusive
   300 + regular 900 of 2,000 sq ft at 40 % time = 33 %; Pub. 587 Rene examples (34.25 % time, 17.12 %; stop date
   June 24 -> 4,200 hours, 35.71 %); leap year 8,784 hours; mid-year start.
3. The sample provider's full year recomputed independently in Python: every SUMMARY figure, the hours log monthly
   table and tiles, expenses row by row, meals, mileage, simplified estimate, statement.
4. Scenarios: tax year changed, rates changed (simplified, mileage, meals, food method, reimbursements), a room's use
   type changed: everything recomputed and compared again.
5. Blank workbook: empty rows are blank, no errors, sensible empty-state messages.

Usage: python test_workbook.py   (exit code 1 on any failure; writes ../dist/test_results.json)
"""
from __future__ import annotations

import copy
import datetime as dt
import glob
import json
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from openpyxl import load_workbook

import build_workbook as B
import sample_data as SD

RECALC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
ERRS = ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "Err:")
RESULTS = []
OUT = Path(__file__).resolve().parent.parent / "dist" / "home-daycare-tax-workbook"


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    return ok


def close(a, b, tol=0.006):
    if a in (None, "") or b in (None, ""):
        return a in (None, "") and b in (None, "")
    if isinstance(a, str) or isinstance(b, str):
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
    out = subprocess.run([sys.executable, RECALC, str(tmp), "900"], capture_output=True, text=True).stdout
    return tmp, json.loads(out[out.index("{"):])


def scan_errors(path):
    wb = load_workbook(path, data_only=True)
    return [f"{ws.title}!{c.coordinate}={c.value}" for ws in wb.worksheets for row in ws.iter_rows() for c in row
            if isinstance(c.value, str) and c.value.startswith(ERRS)]


def as_date(v):
    return v.date() if isinstance(v, dt.datetime) else v


def round_half_up(x, n=2):
    return float(Decimal(str(round(x, 9))).quantize(Decimal(1).scaleb(-n), ROUND_HALF_UP))


# ================================================================== independent model
def to_h(t):
    return t.hour + t.minute / 60 + t.second / 3600


def model(inp):
    """inp: everything a user types. Returns every figure the workbook should show."""
    yr = inp["year"]
    first = max(dt.date(yr, 1, 1), inp["start"]) if inp["start"] and inp["start"] > dt.date(yr, 1, 1) else dt.date(yr, 1, 1)
    last = min(dt.date(yr, 12, 31), inp["stop"]) if inp["stop"] and inp["stop"] < dt.date(yr, 12, 31) else dt.date(yr, 12, 31)
    days = max(0, (last - first).days + 1)
    avail = 24 * days
    caldays = (dt.date(yr + 1, 1, 1) - dt.date(yr, 1, 1)).days
    usual = []
    for a, b, o in inp["usual"]:
        ch = 0 if (a is None or b is None) else ((to_h(b) - to_h(a)) % 24)
        usual.append((ch, o or 0, ch + (o or 0)))
    rows = []
    for i in range(366):
        if i >= caldays:
            rows.append(None)
            continue
        d = dt.date(yr, 1, 1) + dt.timedelta(days=i)
        x = inp["hours"][i] if i < len(inp["hours"]) else {}
        inbiz = first <= d <= last
        edited = any(x.get(k) not in (None, "") for k in ("start", "end", "typed", "other"))
        wd = d.weekday()
        if not inbiz:
            rows.append(dict(date=d, inbiz=0, status="Not in business", counted=0, child="", oth="", total="", month=d.month))
            continue
        closed = x.get("closed") == "Y"
        if closed:
            child = 0
        elif x.get("typed") not in (None, ""):
            child = x["typed"]
        elif x.get("start") and x.get("end"):
            child = (to_h(x["end"]) - to_h(x["start"])) % 24
        else:
            child = usual[wd][0]
        oth = 0 if closed else (x["other"] if x.get("other") not in (None, "") else usual[wd][1])
        total = min(24, child + oth)
        if closed:
            status = "Closed"
        elif edited:
            status = "Edited"
        elif x.get("conf") == "Yes":
            status = "Confirmed"
        elif usual[wd][2] == 0:
            status = "Usual day off"
        else:
            status = "Not yet confirmed"
        counted = 0 if status == "Not yet confirmed" else 1
        rows.append(dict(date=d, inbiz=1, status=status, counted=counted, child=child, oth=oth, total=total, month=d.month))
    live = [r for r in rows if r]
    child_h = sum(r["child"] for r in live if r["counted"])
    other_h = sum(r["oth"] for r in live if r["counted"])
    biz = sum(r["total"] for r in live if r["counted"])
    proj = sum(r["total"] for r in live if r["inbiz"])
    time = biz / avail if avail else 0
    # rooms
    by = defaultdict(float)
    for name, sq, use, _n in inp["rooms"]:
        if sq is not None:
            by[use] += sq
    listed = sum(sq for _n, sq, _u, _x in inp["rooms"] if sq is not None)
    home = inp["home_sqft"] if inp["home_sqft"] else listed
    excl, reg = by[B.USES[0]], by[B.USES[1]]
    excl_pct = excl / home if home else 0
    reg_pct = reg / home if home else 0
    ts = excl_pct + reg_pct * time
    # expenses
    cat = {c[0]: c for c in B.CATS}
    exp_rows, sc, h_direct, h_colb = [], defaultdict(lambda: [0.0, 0.0]), defaultdict(float), defaultdict(float)
    base = {B.TYPES[0]: 1, B.TYPES[1]: 1, B.TYPES[2]: time, B.TYPES[3]: ts, B.TYPES[4]: ts, B.TYPES[5]: 0}
    home_types = set(B.TYPES[1:4])
    std_method = inp["food"] == B.FOODS[0]
    for e in inp["expenses"]:
        d, _v, _ds, amt, typ, c, _r, _n = e
        inyear = 1 if (isinstance(d, dt.date) and d.year == yr) else 0
        form = cat[c][1] if c in cat else ""
        inb = isinstance(d, dt.date) and first <= d <= last
        if inyear == 0 or not typ or not form or form == "Personal":
            share = 0
        elif form == "Food":
            share = 0 if std_method else (1 if typ == B.TYPES[0] else 0)
        elif typ in home_types and not inb:
            share = 0
        else:
            share = base[typ]
        ded = (amt or 0) * share
        exp_rows.append((share, ded))
        if inyear:
            sc[c][0] += amt or 0
        sc[c][1] += ded
        if typ in (B.TYPES[1], B.TYPES[2]):
            h_direct[c] += ded
        if inyear and typ == B.TYPES[3] and inb:
            h_colb[c] += amt or 0
    # meals
    kids = {n: ("No" if (lives == "Y" or fav == "Y") else "Yes") for n, lives, fav, _x in inp["children"]}
    seen, mvals, counts = set(), [], dict(b=0, l=0, d=0, s=0)
    for d, child, b_, l_, d_, s_, _n in inp["meals"]:
        key = (d, child)
        dup = key in seen
        seen.add(key)
        elig = kids.get(child, "Add to list")
        valid = elig == "Yes" and not dup and isinstance(d, dt.date) and d.year == yr and first <= d <= last
        b_, l_, d_, s_ = (v or 0 for v in (b_, l_, d_, s_))
        val = (min(1, b_) * inp["rates"]["bfast"] + min(1, l_) * inp["rates"]["lunch"] + min(1, d_) * inp["rates"]["dinner"]
               + min(3, s_) * inp["rates"]["snack"]) if valid else 0
        mvals.append(val)
        if valid:
            counts["b"] += b_ >= 1
            counts["l"] += l_ >= 1
            counts["d"] += d_ >= 1
            counts["s"] += min(3, s_)
    std = sum(mvals)
    actual = sum(e[3] for e in inp["expenses"] if e[5] == "Food (actual receipts)" and e[4] == B.TYPES[0]
                 and isinstance(e[0], dt.date) and e[0].year == yr)
    chosen = std if std_method else actual
    reimb = inp["reimb"] or 0
    food_net, food_inc = max(0, chosen - reimb), max(0, reimb - chosen)
    # mileage
    miles = ded_m = 0
    for d, _p, _f, _t, mi in inp["trips"]:
        rate = inp["rates"]["mile2"] if (inp["rates"]["mchange"] and d >= inp["rates"]["mchange"]) else inp["rates"]["mile1"]
        if d.year == yr:
            miles += mi
            ded_m += mi * rate
    # simplified
    area = excl + reg
    allowed = min(area, inp["rates"]["smax"])
    s_excl = min(excl, allowed)
    s_reg = allowed - s_excl
    rrate = inp["rates"]["srate"] if excl >= inp["rates"]["smax"] else round_half_up(inp["rates"]["srate"] * time, 2)
    simp = s_excl * inp["rates"]["srate"] + s_reg * rrate
    sc_ded = sum(v[1] for k, v in sc.items() if k in cat and cat[k][1] == "Schedule C") + ded_m + food_net
    home_rows = {c[0]: (h_direct[c[0]], h_colb[c[0]], h_direct[c[0]] + h_colb[c[0]] * ts) for c in B.CATS if c[1] == "Form 8829"}
    months = []
    for m in range(1, 13):
        mr = [r for r in live if r["month"] == m]
        months.append((sum(r["inbiz"] for r in mr), sum(r["counted"] for r in mr if r["inbiz"]),
                       sum(r["total"] for r in mr if r["counted"] and r["inbiz"]),
                       sum(1 for r in mr if r["status"] == "Not yet confirmed"), sum(r["total"] for r in mr if r["inbiz"])))
    return dict(first=first, last=last, days=days, avail=avail, caldays=caldays, rows=rows, child=child_h, other=other_h,
                bizhours=biz, time=time, proj=proj / avail if avail else 0, home=home, excl=excl, reg=reg, excl_pct=excl_pct,
                reg_pct=reg_pct, reg_time=reg_pct * time, ts=ts, exp_rows=exp_rows, sc=sc, home_rows=home_rows,
                home_total=sum(v[2] for v in home_rows.values()), mvals=mvals, counts=counts, std=std, actual=actual,
                chosen=chosen, reimb=reimb, food_net=food_net, food_inc=food_inc, miles=miles, mile_ded=ded_m,
                s_area=area, s_allowed=allowed, s_excl=s_excl, s_reg=s_reg, s_rrate=rrate, simp=simp, sc_total=sc_ded,
                months=months, to_confirm=sum(1 for r in live if r["status"] == "Not yet confirmed"), listed=listed)


def sample_inputs():
    return dict(year=SD.YEAR, start=None, stop=None, usual=SD.USUAL, hours=SD.hours_rows(), rooms=SD.ROOMS, home_sqft=SD.HOME_SQFT,
                expenses=[e for e in SD.EXPENSES], children=SD.CHILDREN, meals=SD.meal_rows(), trips=SD.TRIPS,
                rates=dict(srate=5.0, smax=300, mile1=0.725, mchange=dt.date(2026, 7, 1), mile2=0.76, bfast=1.70, lunch=3.22,
                           dinner=3.22, snack=0.96), food=B.FOODS[0], reimb=SD.CACFP_REIMB)


# ================================================================== compare a recalculated workbook with the model
def compare(path, inp, label):
    m = model(inp)
    wb = load_workbook(path, data_only=True)
    st, sm, hl, ex, me, mi, rm, stt = (wb[n] for n in (B.S_SET, B.S_SUM, B.S_HOURS, B.S_EXP, B.S_MEALS, B.S_MILES, B.S_ROOMS, B.S_STMT))
    g = lambda k: sm[B.SM[k].replace("$", "")].value
    n = 0
    # settings
    for cell, exp in (("C10", m["first"]), ("C11", m["last"]), ("C12", m["days"]), ("C13", m["avail"]), ("C15", m["caldays"])):
        n += 1
        v = as_date(st[cell].value)
        check(f"{label}: SETTINGS {cell}", v == exp or close(v, exp), f"{v!r} vs {exp!r}")
    # hours log, row by row
    bad = 0
    for i, r in enumerate(m["rows"]):
        row = B.H_FIRST + i
        if r is None:
            bad += hl[f"B{row}"].value not in (None, "")
            continue
        got = (as_date(hl[f"B{row}"].value), hl[f"O{row}"].value, hl[f"L{row}"].value, hl[f"M{row}"].value, hl[f"N{row}"].value)
        exp = (r["date"], r["status"], r["child"], r["oth"], r["total"])
        if not (got[0] == exp[0] and got[1] == exp[1] and all(close(a, b) for a, b in zip(got[2:], exp[2:]))):
            bad += 1
            if bad < 4:
                check(f"{label}: HOURS row {row}", False, f"{got!r} vs {exp!r}")
    n += 366
    check(f"{label}: HOURS LOG all 366 rows (date, status, hours)", bad == 0, f"{bad} rows differ")
    for i, mm in enumerate(m["months"]):
        r = 9 + i
        got = [hl[f"{c}{r}"].value for c in ("X", "Y", "Z", "AA", "AB")]
        n += 1
        check(f"{label}: HOURS month {i + 1}", all(close(a, b) for a, b in zip(got, mm)), f"{got} vs {mm}")
    for cell, exp in (("B5", m["bizhours"]), ("E5", m["to_confirm"]), ("I5", m["time"]), ("L5", m["proj"])):
        n += 1
        check(f"{label}: HOURS tile {cell}", close(hl[cell].value, exp, 1e-6), f"{hl[cell].value!r} vs {exp!r}")
    # rooms
    for cell, exp in (("C7", m["excl"]), ("C8", m["reg"]), ("C10", m["listed"]), ("C11", m["home"]), ("C13", m["excl_pct"]), ("C14", m["reg_pct"])):
        n += 1
        check(f"{label}: ROOMS {cell}", close(rm[cell].value, exp, 1e-9), f"{rm[cell].value!r} vs {exp!r}")
    # summary A/B
    for k in ("child", "other", "bizhours", "days", "avail", "time", "proj", "home", "excl", "reg", "excl_pct", "reg_pct", "reg_time", "ts"):
        n += 1
        check(f"{label}: SUMMARY {k}", close(g(k), m[k], 1e-7 if isinstance(m[k], float) and m[k] < 2 else 0.006), f"{g(k)!r} vs {m[k]!r}")
    # expenses row by row
    bad = 0
    for i, (share, ded) in enumerate(m["exp_rows"]):
        r = B.E_FIRST + i
        if not (close(ex[f"K{r}"].value, share, 1e-9) and close(ex[f"L{r}"].value, ded)):
            bad += 1
            if bad < 4:
                check(f"{label}: EXPENSES row {r}", False, f"{ex[f'K{r}'].value!r},{ex[f'L{r}'].value!r} vs {share!r},{ded!r}")
    n += len(m["exp_rows"])
    check(f"{label}: EXPENSES all {len(m['exp_rows'])} rows (share and deductible)", bad == 0, f"{bad} differ")
    blank_rows = [ex[f"{c}{r}"].value for r in range(B.E_FIRST + len(m["exp_rows"]), B.E_LAST + 1) for c in "JKLM"]
    check(f"{label}: EXPENSES empty rows blank", all(v in (None, "") for v in blank_rows))
    # summary C (Schedule C) and D (Form 8829)
    rows_by_label = {sm[f"C{r}"].value: r for r in range(1, sm.max_row + 1) if isinstance(sm[f"C{r}"].value, str)}
    for c in B.CATS:
        if c[1] == "Schedule C":
            r = rows_by_label[c[0]]
            exp = m["sc"].get(c[0], [0.0, 0.0])
            n += 1
            check(f"{label}: SUMMARY Sch C {c[0]}", close(sm[f"E{r}"].value, exp[0]) and close(sm[f"F{r}"].value, exp[1]),
                  f"{sm[f'E{r}'].value},{sm[f'F{r}'].value} vs {exp}")
        elif c[1] == "Form 8829":
            r = rows_by_label[c[0]]
            exp = m["home_rows"][c[0]]
            got = (sm[f"E{r}"].value, sm[f"F{r}"].value, sm[f"G{r}"].value)
            n += 1
            check(f"{label}: SUMMARY 8829 {c[0]}", all(close(a, b) for a, b in zip(got, exp)), f"{got} vs {exp}")
    for k in ("home_total", "sc_total", "std", "actual", "chosen", "reimb", "food_net", "food_inc", "miles", "mile_ded",
              "s_area", "s_allowed", "s_excl", "s_reg", "s_rrate", "simp"):
        n += 1
        check(f"{label}: SUMMARY {k}", close(g(k), m[k]), f"{g(k)!r} vs {m[k]!r}")
    for k, key in (("n_b", "b"), ("n_l", "l"), ("n_d", "d"), ("n_s", "s")):
        n += 1
        check(f"{label}: SUMMARY meals {key}", close(g(k), m["counts"][key]), f"{g(k)!r} vs {m['counts'][key]!r}")
    # meals row by row
    bad = sum(1 for i, v in enumerate(m["mvals"]) if not close(me[f"J{B.M_FIRST + i}"].value, v))
    n += len(m["mvals"])
    check(f"{label}: MEALS all {len(m['mvals'])} rows valued", bad == 0, f"{bad} differ")
    # statement mirrors summary
    stmt_vals = [stt[f"F{r}"].value for r in range(1, stt.max_row + 1) if stt[f"F{r}"].value not in (None, "")]
    n += 1
    check(f"{label}: STATEMENT shows the summary figures", any(close(v, m["ts"], 1e-9) for v in stmt_vals)
          and any(close(v, m["time"], 1e-9) for v in stmt_vals) and any(close(v, m["bizhours"]) for v in stmt_vals))
    return n, m


# ================================================================== known examples on the blank workbook
def known_examples(blank: Path):
    out = {}

    def rooms(ws, items, total):
        for i, (nm, sq, use) in enumerate(items):
            ws[f"B{B.R_FIRST + i}"], ws[f"C{B.R_FIRST + i}"], ws[f"D{B.R_FIRST + i}"] = nm, sq, use
        ws["C6"] = total

    def typed(ws, values):
        for i, v in enumerate(values):
            ws[f"F{B.H_FIRST + i}"] = v

    cases = [
        ("No exclusive space: 1,000 of 2,000 sq ft, 23% time", 2026, None, None,
         [("Shared rooms", 1000, B.USES[1]), ("Bedrooms", 1000, B.USES[2])], 2000, [12] * 167 + [10.8], 0.23, 0.115),
        ("Exclusive 300 + regular 900 of 2,000 sq ft, 40% time", 2026, None, None,
         [("Playroom", 300, B.USES[0]), ("Shared rooms", 900, B.USES[1]), ("Bedrooms", 800, B.USES[2])], 2000, [12] * 292, 0.40, 0.33),
        ("Pub. 587 Example 1 (Rene): basement 1,600 of 3,200 sq ft, 3,000 hours", 2025, None, None,
         [("Basement", 1600, B.USES[1]), ("Rest of home", 1600, B.USES[2])], 3200, [12] * 250, 3000 / 8760, 0.5 * 3000 / 8760),
        ("Pub. 587 Example 3 (Rene stops June 24): 1,500 of 4,200 hours", 2025, None, dt.date(2025, 6, 24),
         [("Basement", 1600, B.USES[1]), ("Rest of home", 1600, B.USES[2])], 3200, [12] * 125, 1500 / 4200, 0.5 * 1500 / 4200),
    ]
    for name, yr, start, stop, rms, total, hrs, exp_time, exp_ts in cases:
        def edit(wb, yr=yr, start=start, stop=stop, rms=rms, total=total, hrs=hrs):
            st = wb[B.S_SET]
            st["C7"] = yr
            st["C8"], st["C9"] = start, stop
            rooms(wb[B.S_ROOMS], rms, total)
            typed(wb[B.S_HOURS], hrs)
        p, res = recalc(blank, edit)
        wb = load_workbook(p, data_only=True)
        sm = wb[B.S_SUM]
        t, ts = sm[B.SM["time"].replace("$", "")].value, sm[B.SM["ts"].replace("$", "")].value
        avail = sm[B.SM["avail"].replace("$", "")].value
        check(f"Known example: {name}: time %", close(t, exp_time, 1e-9), f"{t!r} vs {exp_time!r}")
        check(f"Known example: {name}: time-space %", close(ts, exp_ts, 1e-9), f"{ts!r} vs {exp_ts!r}")
        check(f"Known example: {name}: no formula errors", res.get("total_errors") == 0)
        out[name] = dict(time=t, ts=ts, hours_available=avail)
    # Pub. 587 Example 3: 4,200 hours available
    check("Pub. 587 Example 3: total hours available = 24 × 175 days = 4,200", close(out[cases[3][0]]["hours_available"], 4200),
          str(out[cases[3][0]]["hours_available"]))
    # leap year and mid-year start
    for name, yr, start, exp_days, exp_hours, exp_last_date in (("Leap year 2028", 2028, None, 366, 8784, dt.date(2028, 12, 31)),
                                                                ("Mid-year start Mar 15, 2026", 2026, dt.date(2026, 3, 15), 292, 7008, None),
                                                                ("Non-leap year 2026", 2026, None, 365, 8760, None)):
        def edit(wb, yr=yr, start=start):
            wb[B.S_SET]["C7"] = yr
            wb[B.S_SET]["C8"] = start
        p, _ = recalc(blank, edit)
        wb = load_workbook(p, data_only=True)
        st, hl = wb[B.S_SET], wb[B.S_HOURS]
        check(f"{name}: days available = {exp_days}", st["C12"].value == exp_days, str(st["C12"].value))
        check(f"{name}: total hours = {exp_hours:,}", st["C13"].value == exp_hours, str(st["C13"].value))
        if exp_last_date:
            check(f"{name}: hours log has Dec 31 in row 366", as_date(hl[f"B{B.H_LAST}"].value) == exp_last_date, str(hl[f"B{B.H_LAST}"].value))
            check(f"{name}: SETTINGS says leap year", st["C14"].value == "Yes")
        elif yr == 2026 and not start:
            check(f"{name}: row 366 of the hours log is blank", hl[f"B{B.H_LAST}"].value in (None, ""))
        if start:
            before = [hl[f"O{B.H_FIRST + i}"].value for i in range(73)]
            check(f"{name}: Jan 1 to Mar 14 show 'Not in business'", all(v == "Not in business" for v in before))
        out[name] = dict(days=st["C12"].value, hours=st["C13"].value)
    return out


def main():
    blank = OUT / (B.OUT_NAME + ".xlsx")
    sample = OUT / (B.OUT_NAME + "_SAMPLE.xlsx")
    B.SM.clear()
    B.Builder(True).build()                            # fills the SUMMARY anchors used to read results
    report = {}
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
    # known examples
    report["known_examples"] = known_examples(blank)
    # sample vs model
    inp = sample_inputs()
    n, m = compare(sample_rc, inp, "sample")
    report["sample_checks"] = n
    report["sample"] = {k: m[k] for k in ("bizhours", "avail", "time", "excl_pct", "reg_pct", "ts", "home_total", "sc_total", "std",
                                         "actual", "food_net", "miles", "mile_ded", "simp", "to_confirm")}
    # scenario 1: rates, food method, reimbursements and a room's use type
    alt = copy.deepcopy(inp)
    alt["rates"].update(srate=6.0, smax=250, mile1=0.70, mchange=None, bfast=1.80, lunch=3.40, dinner=3.40, snack=1.00)
    alt["food"], alt["reimb"] = B.FOODS[1], 5000.0
    alt["rooms"] = [r if r[0] != "Living room" else (r[0], r[1], B.USES[0], r[3]) for r in inp["rooms"]]

    def edit1(wb):
        st = wb[B.S_SET]
        st["C20"], st["C21"], st["C22"], st["C23"] = 6.0, 250, 0.70, None
        st["C25"], st["C26"], st["C27"], st["C28"] = 1.80, 3.40, 3.40, 1.00
        st["C29"], st["C30"] = B.FOODS[1], 5000.0
        rm = wb[B.S_ROOMS]
        for r in range(B.R_FIRST, B.R_LAST + 1):
            if rm[f"B{r}"].value == "Living room":
                rm[f"D{r}"] = B.USES[0]
    p1, res1 = recalc(sample, edit1)
    check("scenario rates/room: 0 formula errors", res1.get("total_errors") == 0)
    n1, m1 = compare(p1, alt, "rates and room changed")
    check("scenario: time-space % changed after the room change", abs(m1["ts"] - m["ts"]) > 0.01, f"{m['ts']} -> {m1['ts']}")
    report["scenario_rates_checks"] = n1
    # scenario 2: tax year changed to 2027 (dates, total hours, out-of-year receipts)
    alt2 = copy.deepcopy(inp)
    alt2["year"] = 2027

    def edit2(wb):
        wb[B.S_SET]["C7"] = 2027
    p2, res2 = recalc(sample, edit2)
    check("scenario tax year 2027: 0 formula errors", res2.get("total_errors") == 0)
    n2, m2 = compare(p2, alt2, "tax year 2027")
    report["scenario_year_checks"] = n2
    # scenario 3: business started mid-year
    alt3 = copy.deepcopy(inp)
    alt3["start"] = dt.date(2026, 3, 15)

    def edit3(wb):
        wb[B.S_SET]["C8"] = dt.date(2026, 3, 15)
    p3, res3 = recalc(sample, edit3)
    check("scenario mid-year start: 0 formula errors", res3.get("total_errors") == 0)
    n3, m3 = compare(p3, alt3, "start Mar 15")
    report["scenario_start_checks"] = n3
    # blank workbook
    wb = load_workbook(blank_rc, data_only=True)
    ex, me, mi = wb[B.S_EXP], wb[B.S_MEALS], wb[B.S_MILES]
    vals = [ex[f"{c}{r}"].value for r in range(B.E_FIRST, B.E_LAST + 1) for c in "JKLM"]
    check("blank: all 500 expense rows' calculated cells are blank", all(v in (None, "") for v in vals))
    vals = [me[f"{c}{r}"].value for r in range(B.M_FIRST, B.M_LAST + 1) for c in "IJ"]
    check("blank: all 2,500 meal rows' calculated cells are blank", all(v in (None, "") for v in vals))
    vals = [mi[f"{c}{r}"].value for r in range(B.MI_FIRST, B.MI_LAST + 1) for c in "GH"]
    check("blank: all 300 mileage rows' calculated cells are blank", all(v in (None, "") for v in vals))
    kids = [me[f"R{r}"].value for r in range(B.KID_FIRST, B.KID_LAST + 1)]
    check("blank: children list eligibility cells are blank", all(v in (None, "") for v in kids))
    sm = wb[B.S_SUM]
    check("blank: time % and time-space % are 0", sm[B.SM["time"].replace("$", "")].value == 0 and sm[B.SM["ts"].replace("$", "")].value == 0)
    check("blank: ROOMS asks for the home's square feet", str(wb[B.S_ROOMS]["D7"].value).startswith("Enter the home"))
    hl = wb[B.S_HOURS]
    st = [hl[f"O{r}"].value for r in range(B.H_FIRST, B.H_FIRST + 365)]
    check("blank: hours log days show 'Usual day off' until usual hours are set", all(v == "Usual day off" for v in st), str(set(st)))
    fails = [r for r in RESULTS if not r[1]]
    print(f"PASSED {len(RESULTS) - len(fails)} checks, FAILED {len(fails)}")
    for name, _, detail in fails[:40]:
        print("  FAIL", name, detail)
    report["passed"], report["failed"] = len(RESULTS) - len(fails), len(fails)
    report["recalculated"] = {"sample": str(sample_rc), "blank": str(blank_rc)}
    (OUT.parent / "test_results.json").write_text(json.dumps(report, indent=1, default=str))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
