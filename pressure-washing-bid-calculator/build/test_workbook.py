"""Tests for the Pressure Washing Bid Calculator.

1. Both files: LibreOffice headless recalculation, 0 formula errors, no error values in any cell.
2. Independent Python model (no formulas) of cost per hour and the full multi-line quote, compared line by line with the
   workbook for: the sample quote, a small driveway below the minimum charge, a 2-storey house wash + driveway + gutters
   with bundle discount and a maintenance plan, and heavy commercial flatwork with oil stains, a crew of 2, no water on
   site and a travel surcharge.
3. Edge cases: empty quote lines, quantity 0, margin 0 %, no water on site, rounding 0, a service missing from SETTINGS.
4. Settings changes (chemical cost, production rate, margin): every dependent figure, the customer quote and the dashboard.
5. Quote log, job log (per row and estimate-vs-actual notes per service), maintenance plans, dashboard tiles.
6. Blank file shows blanks; customer quote prints on one page with no Brass Ledger branding; no '###' in printouts.

Usage: python test_workbook.py
"""
from __future__ import annotations

import copy
import datetime as dt
import glob
import json
import math
import re
import subprocess
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from openpyxl import load_workbook

import pw_config as CFG
import pw_engine as E

RECALC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
OUT = Path(__file__).resolve().parent.parent / "dist" / "pressure-washing-bid-calculator"
RESULTS = []
TODAY = dt.date.today()


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))


def close(a, b, tol=0.006):
    if a in (None, "") and b in (None, ""):
        return True
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


def rnd(x, n=2):
    return float(Decimal(str(x)).quantize(Decimal(1).scaleb(-n), rounding=ROUND_HALF_UP))


def money(x, cur="$"):
    return f"–{cur}{-x:,.2f}" if x < 0 else f"{cur}{x:,.2f}"


# ================================================================== model
def settings(over=None):
    s = dict(copy.deepcopy(CFG.TARGETS), **CFG.FUEL)
    s["svc"] = {n: dict(cat=c, unit=u, rate=r, chem=ch, going=g, flat=f) for n, c, u, r, ch, g, f in CFG.SERVICES}
    s["cond"] = {n: (t, c) for n, t, c in CFG.CONDITIONS}
    s["acc"] = dict(CFG.ACCESS)
    s["stain"] = {n: (m, c) for n, _u, m, c in CFG.STAINS}
    s["equipment"], s["overhead"] = list(CFG.EQUIPMENT), list(CFG.OVERHEAD)
    for k, v in (over or {}).items():
        if k in ("svc_rate", "svc_chem"):
            name, val = v
            s["svc"][name][k[4:]] = val
        else:
            s[k] = v
    s["equip_year"] = sum((p / life if life else p) + m for _n, p, life, m in s["equipment"])
    s["over_year"] = sum(v for _n, v in s["overhead"])
    s["equip_hr"] = s["equip_year"] / s["hours"]
    s["over_hr"] = s["over_year"] / s["hours"]
    s["breakeven_hr"] = s["equip_hr"] + s["over_hr"] + s["owner_pay"]
    s["target_hr"] = s["breakeven_hr"] / (1 - s["margin"])
    s["vehicle_mile"] = s["fuel_price"] / s["mpg"] + s["wear_mile"]
    return s


def quote(inp, s):
    lines = []
    for ln in inp["lines"]:
        svc, qty, cond, acc, stain, sq, pv = ln
        ok = bool(svc) and (qty or 0) > 0 and svc in s["svc"]
        d = dict(svc=svc, qty=qty, ok=ok, visits=pv or 0)
        if ok:
            sv = s["svc"][svc]
            tm, cm = s["cond"].get(cond or CFG.DEFAULT_CONDITION, (1, 1))
            hm = s["acc"].get(acc, 1) if acc else 1
            smin, scost = (0, 0) if not stain or not sq else (sq * s["stain"][stain][0], sq * s["stain"][stain][1])
            d["min"] = (qty / sv["rate"] * 60 * tm * hm if sv["rate"] else 0) + smin
            d["chem"] = qty / 1000 * sv["chem"] * cm + scost
            d["going"], d["flat"], d["unit"] = sv["going"], sv["flat"] == "Yes", sv["unit"]
        lines.append(d)
    ok = [d for d in lines if d["ok"]]
    n = len(ok)
    o = dict(n=n, lines=lines)
    W = sum(d["min"] for d in ok)
    crew = max(1, inp.get("crew") or 0)
    cf = (1 + s["crew_loss"] * (crew - 1)) / crew
    o["work"] = W
    o["extra"] = 0 if n == 0 else s["setup_min"] + (s["water_min"] if inp.get("water") == "No" else 0)
    o["onsite"] = (W + o["extra"]) * cf
    o["drive_min"] = inp.get("drive") or 0
    o["job_hours"] = 0 if n == 0 else (o["onsite"] + o["drive_min"]) / 60
    lab = s["owner_pay"] + (crew - 1) * s["helper_wage"] * (1 + s["payroll"])
    o["c_lab"] = o["onsite"] / 60 * lab
    o["c_eq"] = o["job_hours"] * s["equip_hr"]
    o["c_ov"] = o["job_hours"] * s["over_hr"]
    o["c_fuel"] = W * cf / 60 * s["machine_gph"] * s["fuel_price"]
    o["c_chem"] = sum(d["chem"] for d in ok)
    o["c_trav"] = 0 if n == 0 else o["drive_min"] / 60 * lab + (inp.get("miles") or 0) * s["vehicle_mile"]
    o["c_fees"] = 0 if n == 0 else (inp.get("other") or 0)
    o["cost"] = 0 if n == 0 else sum(o[k] for k in ("c_lab", "c_eq", "c_ov", "c_fuel", "c_chem", "c_trav", "c_fees"))
    shared = o["cost"] - o["c_chem"]
    inc = s["rounding"]
    for d in ok:
        d["cost"] = d["chem"] + (shared / n if W == 0 else shared * d["min"] / W)
        raw = d["cost"] / (1 - s["margin"])
        d["price"] = math.ceil(round(raw, 6) / inc) * inc if inc > 0 else rnd(raw, 2)
        d["per_unit"] = d["price"] / d["qty"]
    if n == 0:
        for k in ("subtotal", "bundle", "water_fee", "travel_fee", "min_adj", "total", "profit", "profit_hr"):
            o[k] = ""
        o["plan"] = ""
        o["plan_full"] = 0
        o["flat_sqft"] = 0
        o["warning"] = "Add a service"
        return o
    o["subtotal"] = sum(d["price"] for d in ok)
    o["bundle"] = -rnd(o["subtotal"] * s["bundle_disc"], 2) if n >= 2 else 0
    o["water_fee"] = s["water_fee"] if inp.get("water") == "No" else 0
    o["travel_fee"] = rnd(max(0, (inp.get("miles") or 0) - s["free_miles"]) * s["surcharge_mile"], 2)
    before = o["subtotal"] + o["bundle"] + o["water_fee"] + o["travel_fee"]
    o["min_adj"] = max(0, s["min_charge"] - before)
    o["total"] = before + o["min_adj"]
    o["profit"] = o["total"] - o["cost"]
    o["profit_hr"] = o["profit"] / o["job_hours"] if o["job_hours"] else ""
    o["flat_sqft"] = sum(d["qty"] for d in ok if d["flat"])
    o["flat_price"] = sum(d["price"] for d in ok if d["flat"])
    o["plan_full"] = sum(d["price"] * d["visits"] for d in ok)
    o["plan"] = rnd(o["plan_full"] * (1 - s["plan_disc"]), 2) if o["plan_full"] else ""
    o["warning"] = ("BELOW BREAK-EVEN" if o["total"] < o["cost"] else
                    "LOW PROFIT" if o["profit_hr"] != "" and o["profit_hr"] < s["target_profit_hr"] else "Priced for profit")
    return o


# ================================================================== workbook helpers
def build(sample=True, inp=None, over=None):
    e = E.PWEngine(CFG, sample)
    wb = e.build()
    qq, st = wb[E.S_QQ], wb[E.S_SET]
    cell = lambda ref: ref.split("!")[-1].replace("$", "")
    if inp:
        for k in ("crew", "drive", "miles", "water", "other", "property"):
            if k in inp:
                qq[cell(e.Q[k])] = inp[k]
        for i in range(E.LINES):
            for col in "BCEFGHI":
                qq[f"{col}{e.Q['l1'] + i}"] = None
        for i, (svc, qty, cond, acc, stain, sq, pv) in enumerate(inp["lines"]):
            rr = e.Q["l1"] + i
            for col, v in zip("BCEFGHI", (svc, qty, cond, acc, stain, sq, pv)):
                qq[f"{col}{rr}"] = v
    for k, v in (over or {}).items():
        if k in ("svc_rate", "svc_chem"):
            name, val = v
            s1, s2 = e.rows["svc"]
            r = next(r for r in range(s1, s2 + 1) if st[f"B{r}"].value == name)
            st[f"{'E' if k == 'svc_rate' else 'F'}{r}"] = val
        else:
            st[cell(e.S[k])] = v
    tmp = Path(tempfile.mkdtemp()) / "t.xlsx"
    wb.save(tmp)
    res = json.loads(subprocess.run([sys.executable, RECALC, str(tmp), "240"], capture_output=True, text=True).stdout or "{}")
    return load_workbook(tmp, data_only=True), e, res


ERRS = ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!")


def scan_errors(wb):
    return [f"{ws.title}!{c.coordinate}={c.value}" for ws in wb.worksheets for row in ws.iter_rows() for c in row
            if isinstance(c.value, str) and c.value in ERRS]


def compare(label, wb, e, inp, s):
    m = quote(inp, s)
    qq = wb[E.S_QQ]
    g = lambda k: qq[e.Q[k].replace("$", "")].value
    for k in ("n", "work", "extra", "onsite", "drive_min", "job_hours", "c_lab", "c_eq", "c_ov", "c_fuel", "c_chem", "c_trav",
              "c_fees", "cost", "subtotal", "bundle", "water_fee", "travel_fee", "min_adj", "total", "profit", "profit_hr",
              "plan_full", "plan"):
        check(f"{label}: {k}", close(g(k), m[k], 1e-6 if k == "job_hours" else 0.006), f"{g(k)!r} vs {m[k]!r}")
    if m["n"]:
        check(f"{label}: flatwork sq ft", close(g("flat_sqft"), m["flat_sqft"]))
        if m["flat_sqft"]:
            check(f"{label}: flatwork price per sq ft", close(g("flat_price"), m["flat_price"] / m["flat_sqft"], 1e-6))
    for i, d in enumerate(m["lines"]):
        r = e.Q["l1"] + i
        got = [qq[f"{c}{r}"].value for c in "JKLMN"]
        if d["ok"]:
            exp = [d["min"], d["chem"], d["cost"], d["price"], d["per_unit"]]
            check(f"{label}: line {i + 1} {d['svc']} minutes, chemicals, cost, price, per unit",
                  all(close(a, b, 1e-6 if j == 4 else 0.006) for j, (a, b) in enumerate(zip(got, exp))), f"{got} vs {exp}")
            going = d["going"] * d["qty"]
            want = "" if not going else (f"{rnd(100 * (d['price'] / going - 1), 0):.0f}% above" if d["price"] > going else
                                         f"{rnd(100 * (1 - d['price'] / going), 0):.0f}% below" if d["price"] < going else "Same")
            check(f"{label}: line {i + 1} vs going rate", (qq[f"O{r}"].value or "") == want, f"{qq[f'O{r}'].value!r} vs {want!r}")
        else:
            check(f"{label}: line {i + 1} blank", all(v in (None, "") for v in got), str(got))
    w = qq["H8"].value or ""
    check(f"{label}: warning '{m['warning']}'", w.startswith(m["warning"]), w)
    return m


def compare_customer(label, wb, m):
    cq = wb[E.S_CQ]
    k = 0
    for i, d in enumerate(m["lines"]):
        if d["ok"]:
            r = 15 + i
            check(f"{label}: customer quote line {i + 1}", cq[f"G{r}"].value == money(d["price"]) and
                  str(cq[f"B{r}"].value).startswith(d["svc"]), f"{cq[f'B{r}'].value!r} {cq[f'G{r}'].value!r}")
    want = [("Subtotal", m["subtotal"])] + [(lab, m[key]) for lab, key in (("Bundle discount", "bundle"), ("Water hauling", "water_fee"),
                                                                             ("Travel surcharge", "travel_fee"), ("Minimum job charge", "min_adj")) if m[key]] + [("Total", m["total"])]
    got = []
    for r in range(15 + E.LINES, 15 + E.LINES + 6):
        if cq[f"B{r}"].value:
            got.append((cq[f"B{r}"].value, cq[f"G{r}"].value))
    exp = [(lab, money(v)) for lab, v in want]
    check(f"{label}: customer quote totals (no gaps)", got == exp, f"{got} vs {exp}")
    pr = None
    for r in range(25, 45):
        if str(cq[f"B{r}"].value or "").startswith("Maintenance plan option"):
            pr = cq[f"B{r}"].value
    if m["plan"]:
        check(f"{label}: customer quote plan offer", pr is not None and money(m["plan"]) in pr, str(pr))
    else:
        check(f"{label}: customer quote has no plan offer", pr is None, str(pr))


def qinp(lines, **kw):
    d = dict(crew=1, drive=15, miles=9, water="Yes", other=0, property="Residential")
    d.update(kw)
    d["lines"] = lines
    return d


Q = CFG.QUOTE
SAMPLE = qinp(Q["lines"], crew=Q["crew"], drive=Q["drive"], miles=Q["miles"], water=Q["water"], other=Q["other"])
SMALL = qinp([("Concrete driveway", 400, "Normal", None, None, None, 0)], drive=10, miles=4)
HOUSE = qinp([("House wash (soft wash)", 2200, None, "2 storeys", None, None, 1),
              ("Concrete driveway", 800, None, None, None, None, 1),
              ("Gutter brightening", 140, None, "2 storeys", None, None, 0)], drive=18, miles=11)
COMMERCIAL = qinp([("Commercial flatwork", 8000, "Heavy", None, "Oil", 12, 0),
                   ("Dumpster pad", 300, "Heavy", None, "Organic (leaves, berries)", 40, 4)],
                  crew=2, drive=30, miles=24, water="No", other=25, property="Commercial")


def main():
    report = {}
    for p in (OUT / (CFG.OUT_NAME + ".xlsx"), OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx")):
        tmp = Path(tempfile.mkdtemp()) / p.name
        tmp.write_bytes(p.read_bytes())
        res = json.loads(subprocess.run([sys.executable, RECALC, str(tmp), "240"], capture_output=True, text=True).stdout)
        bad = scan_errors(load_workbook(tmp, data_only=True))
        check(f"{p.name}: LibreOffice reports 0 formula errors", res.get("total_errors") == 0, json.dumps(res.get("error_summary")))
        check(f"{p.name}: no error values in any cell", not bad, ", ".join(bad[:5]))
        report[p.name] = res.get("total_formulas")
    s = settings()
    wb, e, res = build(True)
    st = wb[E.S_SET]
    for k in ("equip_year", "over_year", "equip_hr", "over_hr", "breakeven_hr", "target_hr", "vehicle_mile"):
        v = st[e.ref(k)].value
        check(f"Settings: {k}", close(v, s[k], 1e-6), f"{v!r} vs {s[k]!r}")
    report["cost_per_hour"] = {k: round(s[k], 4) for k in ("equip_year", "over_year", "equip_hr", "over_hr", "breakeven_hr", "target_hr", "vehicle_mile")}
    m = compare("Sample quote", wb, e, SAMPLE, s)
    compare_customer("Sample quote", wb, m)
    report["sample_quote"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != "lines"}
    report["sample_lines"] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()} for d in m["lines"]]
    cq = wb[E.S_CQ]
    vals = [str(c.value) for row in cq.iter_rows(max_col=8) for c in row if c.value is not None]
    check("Customer quote: no Brass Ledger branding in the printed columns", not any("brass" in v.lower() for v in vals))
    check("Customer quote: user's business name", cq["C2"].value == CFG.BUSINESS["name"], str(cq["C2"].value))
    check("Customer quote: valid until = date + valid days", cq["F11"].value.date() == Q["date"] + dt.timedelta(days=CFG.TARGETS["valid_days"]))
    sr = e.rows["save"]
    qq = wb[E.S_QQ]
    got = [qq.cell(sr, c).value for c in range(2, 11)]
    exp = [None, Q["client"], Q["address"], Q["property"], None, m["total"], m["flat_sqft"], m["flat_price"], rnd(m["job_hours"], 1)]
    check("Save-this-quote row", all(b is None or close(a, b) for a, b in zip(got, exp)) and got[4].startswith("House wash"),
          f"{got} vs {exp}")

    # ---- quote log
    lg = wb[E.S_LOG]
    L_ = CFG.LOG
    acc = [x for x in L_ if x[9] == "Accepted"]
    decided = [x for x in L_ if x[9] in ("Accepted", "Declined", "No reply")]
    check("Quote log: win rate", close(lg["D5"].value, len(acc) / len(decided), 1e-9), f"{lg['D5'].value!r}")
    totals = [x[5] for x in L_ if x[5] > 0]
    check("Quote log: average quote", lg["F5"].value == money(sum(totals) / len(totals)), f"{lg['F5'].value!r}")
    for stt, cell in (("Accepted", "G5"), ("Declined", "K5")):
        rows = [x for x in L_ if x[9] == stt]
        v = sum(x[7] for x in rows) / sum(x[6] for x in rows)
        check(f"Quote log: flatwork per sq ft {stt}", lg[cell].value == f"${v:,.3f}", f"{lg[cell].value!r} vs {v:.3f}")
    check("Quote log: empty rows blank", all(lg[f"N{r}"].value in (None, "") for r in range(E.LOG_FIRST + len(L_), E.LOG_LAST + 1)))

    # ---- job log
    jb = wb[E.S_JOB]
    per = {}
    tot_profit = tot_hours = 0
    for i, (d_, client, svc, price, est, act, crew, chem, extra, paid) in enumerate(CFG.JOBS):
        r = E.JOB_FIRST + i
        rate = s["owner_pay"] + (crew - 1) * s["helper_wage"] * (1 + s["payroll"]) + s["equip_hr"] + s["over_hr"]
        cost = act * rate + chem + extra
        profit = price - cost
        got = [jb[f"{c}{r}"].value for c in "MNOP"]
        exp = [cost, profit, profit / act, act / est - 1]
        check(f"Job log row {i + 1}: cost, profit, per hour, time vs estimate", all(close(a, b, 1e-6) for a, b in zip(got, exp)), f"{got} vs {exp}")
        p = per.setdefault(svc, [0, 0, 0])
        p[0] += 1; p[1] += est; p[2] += act
        tot_profit += profit; tot_hours += act
    notes = {}
    for i in range(E.SVC_ROWS):
        r = E.JOB_FIRST + i
        name = jb[f"R{r}"].value
        if name in per:
            n, est, act = per[name]
            diff = act / est - 1
            rate = s["svc"][name]["rate"]
            want = ("Slower than estimated" if diff > 0.15 else "Faster than estimated" if diff < -0.15 else "On target.")
            w = jb[f"W{r}"].value or ""
            ok = jb[f"S{r}"].value == n and close(jb[f"V{r}"].value, diff, 1e-9) and w.startswith(want)
            if want != "On target.":
                ok = ok and f"{rnd(rate * est / act, 0):,.0f}" in w
            check(f"Job log by service: {name} ({diff:+.0%}) -> {want}", ok, f"{jb[f'S{r}'].value} {jb[f'V{r}'].value} {w!r}")
            notes[name] = w
        elif name:
            check(f"Job log by service: {name} blank", jb[f"S{r}"].value in (None, "") and jb[f"W{r}"].value in (None, ""))
    report["job_notes"] = notes
    check("Job log: at least one 'slower' and one 'faster' note on the sample", any(v.startswith("Slower") for v in notes.values())
          and any(v.startswith("Faster") for v in notes.values()))
    check("Job log: actual profit per hour tile", jb["F5"].value == money(tot_profit / tot_hours), f"{jb['F5'].value!r} vs {tot_profit / tot_hours:.2f}")

    # ---- plans
    pl = wb[E.S_PLAN]
    freq = dict(CFG.PLAN_FREQ)
    annual = due30 = overdue = due_month = 0
    eom = (dt.date(TODAY.year + (TODAY.month == 12), TODAY.month % 12 + 1, 1) - dt.timedelta(days=1))
    for i, (cl, _a, _s, fr, price, last, status, _n) in enumerate(CFG.PLANS):
        r = E.PLAN_FIRST + i
        v = freq[fr]
        if status != "Active":
            check(f"Plan {cl}: paused/cancelled shows status, no due date", pl[f"M{r}"].value == status and pl[f"L{r}"].value in (None, ""))
            continue
        import calendar
        mo = last.month - 1 + 12 // v
        y_, m_ = last.year + mo // 12, mo % 12 + 1
        nxt = dt.date(y_, m_, min(last.day, calendar.monthrange(y_, m_)[1]))      # EDATE: same day, clamped to month end
        annual += price * v
        days = (nxt - TODAY).days
        want = "Overdue" if days < 0 else (f"Due in {days} days" if days <= 30 else "Scheduled")
        due30 += 0 <= days <= 30
        overdue += days < 0
        due_month += nxt <= eom
        got = pl[f"L{r}"].value.date() if pl[f"L{r}"].value else None
        check(f"Plan {cl}: next due {nxt}, '{want}', annual value", got == nxt and pl[f"M{r}"].value == want and
              close(pl[f"K{r}"].value, price * v), f"{got} {pl[f'M{r}'].value!r} {pl[f'K{r}'].value}")
    check("Plans: annual plan revenue tile", pl["D5"].value == money(annual), f"{pl['D5'].value!r} vs {annual}")
    check("Plans: due in next 30 days tile", pl["F5"].value == due30, f"{pl['F5'].value!r} vs {due30}")
    check("Plans: overdue tile", pl["I5"].value == overdue, f"{pl['I5'].value!r} vs {overdue}")

    # ---- dashboard
    db = wb[E.S_DASH]
    ytd = sum(j[3] for j in CFG.JOBS if j[0].year == CFG.YEAR)
    exp = {"B7": money(s["breakeven_hr"]), "E7": money(sum(j[3] for j in CFG.JOBS) / len(CFG.JOBS)),
           "H7": f"{rnd(100 * len(acc) / len(decided), 0):.0f}%", "K7": money(ytd), "B10": money(tot_profit / tot_hours),
           "F10": money(annual), "J10": due_month}
    for cell, v in exp.items():
        check(f"Dashboard tile {cell}", db[cell].value == v, f"{db[cell].value!r} vs {v!r}")
    report["dashboard"] = exp
    cats = {}
    for j in CFG.JOBS:
        cats[s["svc"][j[2]]["cat"]] = cats.get(s["svc"][j[2]]["cat"], 0) + j[3]
    r0 = e.rows["dash"]["cats"] + 2
    for i, cat in enumerate(CFG.CATEGORIES):
        check(f"Dashboard revenue by type: {cat}", close(db[f"D{r0 + i}"].value, cats.get(cat, 0)), f"{db[f'D{r0 + i}'].value}")
    check("Dashboard: 3 charts", len(load_workbook(OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx"))[E.S_DASH]._charts) == 3)

    # ---- three jobs
    for label, inp in (("Driveway only, below the minimum", SMALL), ("2-storey house wash + driveway + gutters, bundle and plan", HOUSE),
                       ("Commercial flatwork, heavy, oil stains, crew 2, no water, travel surcharge", COMMERCIAL)):
        wb, e, res = build(True, inp)
        check(f"{label}: 0 formula errors", res.get("total_errors") == 0, json.dumps(res.get("error_summary")))
        m = compare(label, wb, e, inp, s)
        compare_customer(label, wb, m)
        report[label] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != "lines"}
    check("Small driveway is lifted to the minimum charge", report["Driveway only, below the minimum"]["min_adj"] > 0
          and report["Driveway only, below the minimum"]["total"] == CFG.TARGETS["min_charge"])
    check("House job gets the bundle discount", report["2-storey house wash + driveway + gutters, bundle and plan"]["bundle"] < 0)
    check("Commercial job: water hauling and travel surcharge charged",
          report["Commercial flatwork, heavy, oil stains, crew 2, no water, travel surcharge"]["water_fee"] > 0
          and report["Commercial flatwork, heavy, oil stains, crew 2, no water, travel surcharge"]["travel_fee"] > 0)

    # ---- edge cases
    empty = qinp([])
    wb, e, res = build(True, empty)
    qq = wb[E.S_QQ]
    check("Edge: empty quote -> 0 errors", res.get("total_errors") == 0)
    check("Edge: empty quote -> totals blank", all(qq[e.Q[k].replace("$", "")].value in (None, "") for k in ("subtotal", "total", "profit", "profit_hr", "plan")))
    check("Edge: empty quote -> tiles show a dash", qq["H6"].value == "–" and qq["K6"].value == "–" and qq["N6"].value == "–")
    check("Edge: empty quote -> message", (qq["H8"].value or "").startswith("Add a service"))
    check("Edge: empty quote -> customer quote total empty", not any(wb[E.S_CQ][f"B{r}"].value for r in range(25, 31)))
    for label, inp, over in (("Edge: quantity 0 on a line", qinp([("Patio", 0, None, None, None, None, 0), ("Patio", 500, None, None, None, None, 0)]), None),
                             ("Edge: margin 0 %", SAMPLE, dict(margin=0)),
                             ("Edge: no water on site", dict(SAMPLE, water="No"), None),
                             ("Edge: rounding 0", SAMPLE, dict(rounding=0)),
                             ("Edge: service not in SETTINGS", qinp([("Boat wash", 100, None, None, None, None, 0), ("Patio", 400, None, None, None, None, 0)]), None)):
        wb, e, res = build(True, inp, over)
        check(f"{label}: 0 errors", res.get("total_errors") == 0, json.dumps(res.get("error_summary")))
        compare(label, wb, e, inp, settings(over))
    wb, e, _ = build(True, qinp([("Boat wash", 100, None, None, None, None, 0)]))
    check("Edge: unknown service shows 'not in SETTINGS'", wb[E.S_QQ][f"D{e.Q['l1']}"].value == "not in SETTINGS")

    # ---- settings change
    over = {"svc_chem": ("Concrete driveway", 12.0), "svc_rate": ("House wash (soft wash)", 900), "margin": 0.40}
    s2 = settings(over)
    wb, e, res = build(True, SAMPLE, over)
    check("Settings change: 0 errors", res.get("total_errors") == 0)
    m2 = compare("Settings change (driveway chemicals 12, house wash 900/h, margin 40 %)", wb, e, SAMPLE, s2)
    compare_customer("Settings change", wb, m2)
    before = quote(SAMPLE, s)["total"]
    check("Settings change: total moved", m2["total"] != before, f"{before} -> {m2['total']}")
    check("Settings change: quote tile updates", wb[E.S_QQ]["H6"].value == money(m2["total"]))
    wb3, _e, _ = build(True, None, {"owner_pay": 40.0})
    check("Settings change: dashboard break-even updates", wb3[E.S_DASH]["B7"].value == money(settings({"owner_pay": 40.0})["breakeven_hr"]))
    report["settings_change"] = {"before": before, "after": m2["total"]}

    # ---- blank file
    wb, e, res = build(False)
    check("Blank: 0 errors", res.get("total_errors") == 0)
    lg, jb, pl, db, qq = (wb[n] for n in (E.S_LOG, E.S_JOB, E.S_PLAN, E.S_DASH, E.S_QQ))
    check("Blank: quote log calculated column blank (300 rows)", all(lg[f"N{r}"].value in (None, "") for r in range(E.LOG_FIRST, E.LOG_LAST + 1)))
    check("Blank: job log calculated columns blank (300 rows)", all(jb[f"{c}{r}"].value in (None, "") for r in range(E.JOB_FIRST, E.JOB_LAST + 1) for c in "MNOP"))
    check("Blank: job log service summary blank", all(jb[f"{c}{r}"].value in (None, "") for r in range(E.JOB_FIRST, E.JOB_FIRST + E.SVC_ROWS) for c in "STUVW"))
    check("Blank: plans calculated columns blank (150 rows)", all(pl[f"{c}{r}"].value in (None, "") for r in range(E.PLAN_FIRST, E.PLAN_LAST + 1) for c in "JKLM"))
    check("Blank: quote lines blank", all(qq[f"{c}{r}"].value in (None, "") for r in range(e.Q["l1"], e.Q["l2"] + 1) for c in "DJKLMNO"))
    check("Blank: quote asks for a service", (qq["H8"].value or "").startswith("Add a service"))
    check("Blank: dashboard dashes and zeros", db["E7"].value == "–" and db["H7"].value == "–" and db["B10"].value == "–")
    check("Blank: dashboard break-even uses default settings", db["B7"].value == money(s["breakeven_hr"]))
    check("Blank: customer quote placeholder name", wb[E.S_CQ]["C2"].value == "Your business name")

    # ---- printing
    pages, text = print_sheet(OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx"), E.S_CQ)
    check("Customer quote prints on exactly one page", pages == 1, str(pages))
    check("Customer quote printout has no Brass Ledger branding", "brass" not in text.lower())
    check("Customer quote printout shows business name and total", CFG.BUSINESS["name"] in text and "$531.00" in text, text[:200])
    for name in (E.S_QQ, E.S_SET, E.S_LOG, E.S_JOB, E.S_PLAN, E.S_DASH, E.S_START):
        _p, t = print_sheet(OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx"), name, first_rows=70)
        check(f"{name}: no '###' in the printed sample", "###" not in t)

    fails = [r for r in RESULTS if not r[1]]
    print(f"PASSED {len(RESULTS) - len(fails)} checks, FAILED {len(fails)}")
    for name, _ok, detail in fails[:40]:
        print("  FAIL", name, detail)
    report["passed"], report["failed"] = len(RESULTS) - len(fails), len(fails)
    (OUT.parent / "test_results.json").write_text(json.dumps(report, indent=1, default=str))
    return 1 if fails else 0


def print_sheet(path, sheet, first_rows=None):
    wb = load_workbook(path)
    for ws in wb.worksheets:
        if ws.title != sheet:
            ws.print_area = "ZZ900:ZZ900"
        elif first_rows:
            col = re.findall(r":\$?([A-Z]+)\$?\d+", str(ws.print_area))[0]
            ws.print_area = f"A1:{col}{first_rows}"
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "p.xlsx"
    wb.save(p)
    subprocess.run([sys.executable, RECALC, str(p), "240"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(p)], capture_output=True)
    n = int(subprocess.run(["pdfinfo", str(tmp / "p.pdf")], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    pages, text = 0, ""
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), str(tmp / "p.pdf"), "-"], capture_output=True, text=True).stdout
        if t.strip():
            pages += 1
            text += t
    return pages, text


if __name__ == "__main__":
    sys.exit(main())
