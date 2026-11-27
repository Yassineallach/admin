"""Tests for the Lawn Care Pricing Calculator.

1. Both files: LibreOffice headless recalculation, 0 formula errors, no error values in any cell.
2. Independent Python model (no formulas) of cost per hour and the full quote; compared with the workbook for the
   sample quote and several lawns (small push-mower lawn, medium zero-turn lawn with obstacles and a crew of 2,
   large lawn entered in acres with bagging and add-ons).
3. Edge cases: lawn area blank, margin 0 %, price below the minimum charge, own price below cost, no rounding,
   one-time frequency.
4. Settings changes (fuel price, margin, mower speed, owner pay): every dependent figure, the customer quote and the
   dashboard update.
5. Quote log, route planner, season tracker and dashboard against the model; blank file shows blanks.
6. Customer quote: one letter page, no Brass Ledger branding; no "###" anywhere in the printed sample.

Usage: python test_workbook.py
"""
from __future__ import annotations

import copy
import datetime as dt
import glob
import json
import math
import subprocess
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from openpyxl import load_workbook

import engine as E
import lawn_config as CFG

RECALC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
OUT = Path(__file__).resolve().parent.parent / "dist" / "lawn-care-pricing-calculator"
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


# ================================================================== model
def settings(over=None):
    T, F = copy.deepcopy(CFG.TARGETS), copy.deepcopy(CFG.FUEL)
    s = dict(T, **F)
    s["methods"] = {n: (r, f) for n, r, f in CFG.METHODS}
    s["mults"] = [dict(opts) for _g, opts in CFG.MULTIPLIERS]
    s["tasks"] = [(per, mn) for _n, per, mn, _d in CFG.DETAIL_TASKS]
    s["extra_mult"], s["extra_cost"] = CFG.EXTRA["mult"], CFG.EXTRA["cost"]
    s["addons"] = {n: (u, p) for n, u, p, _x in CFG.ADDONS}
    s["equipment"], s["overhead"] = list(CFG.EQUIPMENT), list(CFG.OVERHEAD)
    if over:
        for k, v in over.items():
            if k == "method_rate":
                name, rate = v
                s["methods"][name] = (rate, s["methods"][name][1])
            else:
                s[k] = v
    eq = sum((p / life if life else p) + m for _n, p, life, m in s["equipment"])
    ov = sum(v for _n, v in s["overhead"])
    s["equip_year"], s["over_year"] = eq, ov
    s["equip_hr"] = eq / s["hours"] if s["hours"] else 0
    s["over_hr"] = ov / s["hours"] if s["hours"] else 0
    s["breakeven_hr"] = s["equip_hr"] + s["over_hr"] + s["owner_pay"]
    s["target_hr"] = s["breakeven_hr"] / (1 - s["margin"])
    s["vehicle_mile"] = (s["fuel_price"] / s["mpg"] if s["mpg"] else 0) + s["wear_mile"]
    w = s["season_weeks"]
    s["fpm"] = {"Weekly": 52 / 12, "Bi-weekly": 26 / 12, "Monthly": 1, "One-time": 0}
    s["fps"] = {"Weekly": w, "Bi-weekly": math.ceil(w / 2), "Monthly": rnd(w * 12 / 52, 0), "One-time": 1}
    return s


def quote(inp, s):
    sq, ac = inp.get("sqft"), inp.get("acres")
    area = sq if (sq or 0) > 0 else (rnd(ac * 43560, 0) if (ac or 0) > 0 else 0)
    rate, fuel_use = s["methods"].get(inp["method"], (0, 0))
    mults = [s["mults"][i].get(v, 1) for i, v in enumerate(inp["mults"])]
    extra = inp["extra"] == "Yes"
    o = dict(area=area)
    o["mow"] = 0 if (area == 0 or not rate) else area / rate * 60 * math.prod(mults) * (s["extra_mult"] if extra else 1)
    det = sum(max(mn, per * area / 1000) for (per, mn), t in zip(s["tasks"], inp["tasks"]) if t == "Yes")
    o["detail"] = 0 if area == 0 else det * (mults[0] if CFG.FIRST_MULT_ON_DETAIL else 1)
    o["work"] = o["mow"] + o["detail"]
    crew = max(1, inp.get("crew") or 0)
    o["onsite"] = o["work"] * (1 + s["crew_loss"] * (crew - 1)) / crew
    o["drive_min"] = inp.get("drive") or 0
    o["job_hours"] = (o["onsite"] + o["drive_min"]) / 60
    lab_rate = s["owner_pay"] + (crew - 1) * s["helper_wage"] * (1 + s["payroll"])
    o["c_lab"] = o["onsite"] / 60 * lab_rate
    o["c_eq"] = o["job_hours"] * s["equip_hr"]
    o["c_ov"] = o["job_hours"] * s["over_hr"]
    o["c_fuel"] = o["mow"] / 60 * fuel_use * s["fuel_price"]
    o["c_trav"] = o["drive_min"] / 60 * lab_rate + (inp.get("miles") or 0) * s["vehicle_mile"]
    o["c_disp"] = s["extra_cost"] if extra else 0
    o["cost"] = 0 if area == 0 else sum(o[k] for k in ("c_lab", "c_eq", "c_ov", "c_fuel", "c_trav", "c_disp"))
    if area == 0:
        for k in ("calc_price", "price", "profit", "profit_hr", "per1000", "monthly", "season", "prepaid"):
            o[k] = ""
    else:
        raw = o["cost"] / (1 - s["margin"])
        inc = s["rounding"] or 0
        rounded = math.ceil(round(raw, 6) / inc) * inc if inc > 0 else rnd(raw, 2)
        o["calc_price"] = max(s["min_charge"], rounded)
        ov = inp.get("override") or 0
        o["price"] = ov if ov > 0 else o["calc_price"]
        o["profit"] = o["price"] - o["cost"]
        o["profit_hr"] = o["profit"] / o["job_hours"] if o["job_hours"] else ""
        o["per1000"] = o["price"] / area * 1000
        f = inp.get("freq") or ""
        vpm = s["fpm"].get(f, 0)
        o["monthly"] = rnd(o["price"] * vpm, 2) if vpm else ""
        o["season"] = "" if f in ("", "One-time") else o["price"] * s["fps"][f]
        o["prepaid"] = "" if o["season"] == "" else rnd(o["season"] * (1 - s["prepay"]), 2)
    tot, lines = 0.0, []
    for name, qty in inp.get("addons", []):
        unit, price = s["addons"][name]
        qu = qty if (qty or 0) > 0 else (rnd(area / 1000, 1) if unit == "per 1,000 sq ft" else (1 if unit == "flat" else None))
        t = rnd(qu * price, 2) if qu is not None else "enter qty"
        lines.append((name, unit, qu, price, t))
        tot += t if isinstance(t, float) else 0
    o["addons"], o["lines"] = tot, lines
    if area == 0:
        o["warning"] = "Enter the lawn area"
    elif o["price"] < o["cost"]:
        o["warning"] = "BELOW BREAK-EVEN"
    elif o["profit_hr"] != "" and o["profit_hr"] < s["target_profit_hr"]:
        o["warning"] = "LOW PROFIT"
    else:
        o["warning"] = "Priced for profit"
    return o


# ================================================================== workbook helpers
def build(sample=True, inp=None, over=None, edit=None):
    """Build the sample (or blank) workbook, apply quote inputs and settings overrides, save, recalc. Returns (wb, e)."""
    e = E.Engine(CFG, sample)
    wb = e.build()
    qq, st = wb[E.S_QQ], wb[E.S_SET]
    cell = lambda ref: ref.split("!")[-1].replace("$", "")
    if inp:
        Q = e.Q
        put = lambda k, v: qq.__setitem__(cell(Q[k]), v)
        for k in ("sqft", "acres", "method", "extra", "crew", "drive", "miles", "freq", "going", "override"):
            if k in inp:
                put(k, inp[k])
        for ref, v in zip(Q["mults"], inp["mults"]):
            qq[cell(ref)] = v
        for ref, v in zip(Q["tasks"], inp["tasks"]):
            qq[cell(ref)] = v
        for i in range(E.ADD_N):
            qq[f"B{Q['ad1'] + i}"], qq[f"C{Q['ad1'] + i}"] = None, None
        for i, (n, qty) in enumerate(inp.get("addons", [])):
            qq[f"B{Q['ad1'] + i}"], qq[f"C{Q['ad1'] + i}"] = n, qty
    if over:
        for k, v in over.items():
            if k == "method_rate":
                name, rate = v
                for r in range(1, 300):
                    if st[f"B{r}"].value == name and isinstance(st[f"C{r}"].value, (int, float)):
                        st[f"C{r}"] = rate
                        break
            else:
                st[cell(e.S[k])] = v
    if edit:
        edit(wb, e)
    tmp = Path(tempfile.mkdtemp()) / "t.xlsx"
    wb.save(tmp)
    res = json.loads(subprocess.run([sys.executable, RECALC, str(tmp), "240"], capture_output=True, text=True).stdout or "{}")
    return load_workbook(tmp, data_only=True), e, res, tmp


def scan_errors(wb):
    bad = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("#") and c.value.rstrip("!?0/").upper() in (
                        "#REF", "#VALUE", "#DIV", "#NAME", "#N/A", "#NUM", "#NULL") or (
                        isinstance(c.value, str) and c.value in ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!")):
                    bad.append(f"{ws.title}!{c.coordinate}={c.value}")
    return bad


def compare_quote(label, wb, e, inp, s):
    m = quote(inp, s)
    qq = wb[E.S_QQ]
    g = lambda k: qq[e.Q[k].replace("$", "")].value
    keys = ["mow", "detail", "work", "onsite", "drive_min", "job_hours", "c_lab", "c_eq", "c_ov", "c_fuel", "c_trav",
            "c_disp", "cost", "calc_price", "price", "profit", "profit_hr", "per1000", "monthly", "season", "prepaid", "addons"]
    for k in keys:
        tol = 0.006 if k not in ("job_hours",) else 1e-6
        check(f"{label}: {k}", close(g(k), m[k], tol), f"{g(k)!r} vs {m[k]!r}")
    check(f"{label}: area used", close(qq[e.Q["area"].replace("$", "")].value, m["area"]))
    w = qq[e.Q["warning"].replace("$", "")].value or ""
    check(f"{label}: warning '{m['warning']}'", w.startswith(m["warning"]), w)
    for i, (name, unit, qu, price, t) in enumerate(m["lines"]):
        r = e.Q["ad1"] + i
        check(f"{label}: add-on {name}", qq[f"D{r}"].value == unit and close(qq[f"E{r}"].value, t),
              f"{qq[f'D{r}'].value!r} {qq[f'E{r}'].value!r} vs {unit!r} {t!r}")
    # save row mirrors the result
    sr = e.rows["save"]
    exp = [m["area"] or "", inp.get("freq") or "", m["price"], m["monthly"], m["addons"] or ""]
    got = [qq[f"{c}{sr}"].value for c in "EFGHI"]
    check(f"{label}: save-this-quote row", all(close(a, b) for a, b in zip(got, exp)), f"{got} vs {exp}")
    return m


def compare_customer(label, wb, m, s, inp):
    cq = wb[E.S_CQ]
    cur = s["currency"]
    money = lambda v: "" if v in ("", None) else f"{cur}{v:,.2f}"
    check(f"{label}: customer quote price per visit", cq["G15"].value == money(m["price"]), f"{cq['G15'].value!r} vs {money(m['price'])!r}")
    check(f"{label}: customer quote monthly", (cq["G16"].value or "") == money(m["monthly"]), f"{cq['G16'].value!r}")
    check(f"{label}: customer quote season", (cq["G17"].value or "") == money(m["season"]), f"{cq['G17'].value!r}")
    check(f"{label}: customer quote prepaid", (cq["G18"].value or "") == (money(m["prepaid"]) if s["prepay"] else ""),
          f"{cq['G18'].value!r}")
    for i, (name, unit, qu, price, t) in enumerate(m["lines"]):
        r = 21 + i
        if isinstance(t, float):
            check(f"{label}: customer quote add-on {name}", cq[f"B{r}"].value == name and cq[f"G{r}"].value == money(t),
                  f"{cq[f'B{r}'].value!r} {cq[f'G{r}'].value!r}")


# ================================================================== scenarios
SAMPLE = dict(sqft=CFG.QUOTE["sqft"], acres=None, method=CFG.QUOTE["method"], mults=CFG.QUOTE["mults"],
              tasks=CFG.QUOTE["tasks"], extra=CFG.QUOTE["extra"], crew=1, drive=12, miles=6, freq="Weekly", going=55,
              override=None, addons=CFG.QUOTE["addons"])
SMALL = dict(sqft=3000, acres=None, method='21" push mower', mults=["Low", "Flat", "Normal"], tasks=["Yes", "Yes", "Yes"],
             extra="No", crew=1, drive=8, miles=3, freq="Weekly", going=None, override=None, addons=[])
MEDIUM = dict(sqft=12000, acres=None, method='52" zero-turn', mults=["High", "Moderate", "Normal"], tasks=["Yes", "Yes", "Yes"],
              extra="No", crew=2, drive=15, miles=7, freq="Bi-weekly", going=60, override=None,
              addons=[("Hedge and shrub trimming", 1.5)])
LARGE = dict(sqft=None, acres=0.9, method='61" zero-turn', mults=["Medium", "Moderate", "Overgrown"], tasks=["Yes", "Yes", "Yes"],
             extra="Yes", crew=2, drive=20, miles=11, freq="Weekly", going=None, override=None,
             addons=[("Fall cleanup", None), ("Aeration", None), ("Leaf removal", 3), ("Mulching", 4), ("Overseeding", 20),
                     ("Gutter cleaning", None)])


def main():
    report = {}
    # ---- 1. both files
    for p in (OUT / (CFG.OUT_NAME + ".xlsx"), OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx")):
        tmp = Path(tempfile.mkdtemp()) / p.name
        tmp.write_bytes(p.read_bytes())
        res = json.loads(subprocess.run([sys.executable, RECALC, str(tmp), "240"], capture_output=True, text=True).stdout)
        wb = load_workbook(tmp, data_only=True)
        bad = scan_errors(wb)
        check(f"{p.name}: LibreOffice reports 0 formula errors", res.get("total_errors") == 0, json.dumps(res.get("error_summary")))
        check(f"{p.name}: no error values in any cell", not bad, ", ".join(bad[:5]))
        report[p.name] = res.get("total_formulas")

    s = settings()
    # ---- 2. cost per hour from the sample settings
    wb, e, res, _ = build(True)
    st = wb[E.S_SET]
    g = lambda k: st[e.S[k].split("!")[1].replace("$", "")].value
    for k in ("equip_year", "over_year", "equip_hr", "over_hr", "breakeven_hr", "target_hr", "vehicle_mile"):
        check(f"Settings: {k}", close(g(k), s[k], 1e-6), f"{g(k)!r} vs {s[k]!r}")
    report["cost_per_hour"] = {k: round(s[k], 4) for k in ("equip_year", "over_year", "equip_hr", "over_hr", "breakeven_hr", "target_hr")}
    m = compare_quote("Sample quote (9,500 sq ft)", wb, e, SAMPLE, s)
    compare_customer("Sample quote", wb, m, s, SAMPLE)
    report["sample_quote"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != "lines"}
    cq = wb[E.S_CQ]
    vals = [str(c.value) for row in cq.iter_rows() for c in row if c.value is not None]
    check("Customer quote: no Brass Ledger branding in any cell", not any("brass" in v.lower() for v in vals))
    check("Customer quote: shows the user's business name", cq["C2"].value == CFG.BUSINESS["name"], str(cq["C2"].value))
    check("Customer quote: valid-until = quote date + valid days",
          cq["F11"].value.date() == CFG.QUOTE["date"] + dt.timedelta(days=CFG.TARGETS["valid_days"]), str(cq["F11"].value))
    check("Customer quote: service line lists the chosen tasks",
          cq["B15"].value == "Lawn mowing, trimming, edging, blowing off hard surfaces", repr(cq["B15"].value))
    # quote log
    lg = wb[E.S_LOG]
    acc = [r for r in CFG.LOG if r[8] == "Accepted"]
    dec = [r for r in CFG.LOG if r[8] == "Declined"]
    decided = [r for r in CFG.LOG if r[8] in ("Accepted", "Declined", "No reply")]
    check("Quote log: win rate = accepted ÷ (accepted + declined + no reply)", close(lg["D5"].value, len(acc) / len(decided), 1e-9),
          f"{lg['D5'].value!r}")
    avg = lambda rows: sum(r[5] / r[3] * 1000 for r in rows) / len(rows)
    check("Quote log: per 1,000 sq ft accepted", lg["H5"].value == f"${avg(acc):,.2f}", f"{lg['H5'].value!r} vs {avg(acc):.2f}")
    check("Quote log: per 1,000 sq ft declined", lg["J5"].value == f"${avg(dec):,.2f}", f"{lg['J5'].value!r} vs {avg(dec):.2f}")
    check("Quote log: average price per visit", lg["F5"].value == f"${sum(r[5] for r in CFG.LOG) / len(CFG.LOG):,.2f}", lg["F5"].value)
    for i, r in enumerate(CFG.LOG):
        check(f"Quote log row {i + 1}: per 1,000 sq ft", close(lg[f"M{E.LOG_FIRST + i}"].value, r[5] / r[3] * 1000))
    check("Quote log: empty rows blank", all(lg[f"M{r}"].value in (None, "") for r in range(E.LOG_FIRST + len(CFG.LOG), E.LOG_LAST + 1)))
    # route planner
    rt = wb[E.S_ROUTE]
    fpw = {k: v * 12 / 52 for k, v in s["fpm"].items()}
    days = {}
    for day, _stop, _c, _a, price, ons, drv, freq in CFG.ROUTE:
        d = days.setdefault(day, dict(n=0, rev=0, on=0, dr=0))
        w = fpw[freq]
        d["n"] += 1; d["rev"] += price * w; d["on"] += ons * w; d["dr"] += drv * w
    best, best_v = None, -1
    for i, day in enumerate(CFG.WEEKDAYS):
        r = 8 + i
        d = days.get(day)
        if not d:
            check(f"Route {day}: blank", rt[f"Q{r}"].value == 0 and rt[f"R{r}"].value in (None, ""), f"{rt[f'R{r}'].value!r}")
            continue
        hrs = (d["on"] + d["dr"]) / 60
        rph, share = d["rev"] / hrs, d["dr"] / 60 / hrs
        warn = share > s["drive_warn"]
        ok = (rt[f"Q{r}"].value == d["n"] and close(rt[f"R{r}"].value, d["rev"]) and close(rt[f"U{r}"].value, hrs, 1e-6)
              and close(rt[f"V{r}"].value, rph) and close(rt[f"W{r}"].value, share, 1e-9)
              and (rt[f"X{r}"].value or "").startswith("Driving" if warn else "OK"))
        check(f"Route {day}: stops, revenue, hours, revenue per hour, driving share, warning", ok,
              f"{[rt[f'{c}{r}'].value for c in 'QRUVWX']} vs {d['n'], d['rev'], hrs, rph, share, warn}")
        if rph > best_v:
            best, best_v = day, rph
    # season tracker
    se = wb[E.S_SEASON]
    cut = 12 if CFG.SEASON_YEAR < TODAY.year else (0 if CFG.SEASON_YEAR > TODAY.year else TODAY.month)
    tot = {mo: v[1] + v[2] for mo, v in CFG.SEASON.items()}
    ytd = sum(tot[mo] for i, mo in enumerate(CFG.MONTHS) if i + 1 <= cut and (CFG.SEASON[mo][1] or CFG.SEASON[mo][2]))
    for i, mo in enumerate(CFG.MONTHS):
        r = 8 + i
        a, mw, ad, goal = CFG.SEASON[mo]
        exp_total = (mw + ad) if (a or mw or ad) else ""
        check(f"Season {mo}: total and % of goal", close(se[f"F{r}"].value, exp_total)
              and close(se[f"I{r}"].value, (exp_total / goal) if (exp_total != "" and goal) else "", 1e-9),
              f"{se[f'F{r}'].value!r} {se[f'I{r}'].value!r}")
    check("Season: revenue year to date", se["B5"].value == f"${ytd:,.2f}", f"{se['B5'].value!r} vs {ytd}")
    # dashboard
    db = wb[E.S_DASH]
    clients = len(CFG.ROUTE)
    avg_route = sum(r[4] for r in CFG.ROUTE) / clients
    exp_tiles = {"B7": f"${s['breakeven_hr']:,.2f}", "F7": f"${avg_route:,.2f}",
                 "J7": f"{rnd(100 * len(acc) / len(decided), 0):.0f}%", "B10": clients, "F10": f"${ytd:,.2f}", "J10": best}
    for cell_, v in exp_tiles.items():
        check(f"Dashboard tile {cell_}", db[cell_].value == v, f"{db[cell_].value!r} vs {v!r}")
    report["dashboard"] = exp_tiles
    check("Dashboard: 3 charts", len(load_workbook(OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx"))[E.S_DASH]._charts) == 3)

    # ---- 2b. three more lawns
    for label, inp in (("Small push-mower lawn (3,000 sq ft)", SMALL), ("Medium zero-turn lawn, high obstacles, crew 2", MEDIUM),
                       ("Large lawn in acres, overgrown, bagging, add-ons", LARGE)):
        wb, e, res, _ = build(True, inp)
        check(f"{label}: 0 formula errors", res.get("total_errors") == 0, json.dumps(res.get("error_summary")))
        m = compare_quote(label, wb, e, inp, s)
        compare_customer(label, wb, m, s, inp)
        report[label] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k not in ("lines",)}
    check("Small lawn hits the minimum job charge", report["Small push-mower lawn (3,000 sq ft)"]["price"] == CFG.TARGETS["min_charge"]
          and report["Small push-mower lawn (3,000 sq ft)"]["calc_price"] == CFG.TARGETS["min_charge"])

    # ---- 3. edge cases
    blank_area = dict(SAMPLE, sqft=None, acres=None)
    wb, e, res, _ = build(True, blank_area)
    qq = wb[E.S_QQ]
    gq = lambda k: qq[e.Q[k].replace("$", "")].value
    check("Edge: area blank -> 0 errors", res.get("total_errors") == 0)
    check("Edge: area blank -> price, profit, monthly, season blank",
          all(gq(k) in (None, "") for k in ("price", "profit", "profit_hr", "per1000", "monthly", "season", "prepaid")))
    check("Edge: area blank -> tiles show a dash", qq["F6"].value == "–" and qq["G6"].value == "–", f"{qq['F6'].value!r}")
    check("Edge: area blank -> message asks for the lawn area", (gq("warning") or "").startswith("Enter the lawn area"))
    check("Edge: area blank -> customer quote price empty", wb[E.S_CQ]["G15"].value in (None, ""))
    for label, inp, over in (("Edge: margin 0 %", SAMPLE, dict(margin=0)),
                             ("Edge: crew of 2 on the sample lawn", dict(SAMPLE, crew=2), None),
                             ("Edge: own price below cost", dict(SAMPLE, override=25), None),
                             ("Edge: no rounding (increment 0)", SAMPLE, dict(rounding=0)),
                             ("Edge: one-time job", dict(SAMPLE, freq="One-time"), None),
                             ("Edge: monthly visits", dict(SAMPLE, freq="Monthly"), None)):
        wb, e, res, _ = build(True, inp, over)
        check(f"{label}: 0 errors", res.get("total_errors") == 0)
        m = compare_quote(label, wb, e, inp, settings(over))
    check("Edge: own price below cost shows BELOW BREAK-EVEN", quote(dict(SAMPLE, override=25), s)["warning"] == "BELOW BREAK-EVEN")

    # ---- 4. settings changes ripple through
    over = {"fuel_price": 5.00, "margin": 0.30, "method_rate": ('52" zero-turn', 50000), "owner_pay": 28.00}
    s2 = settings(over)
    wb, e, res, _ = build(True, SAMPLE, over)
    check("Settings change: 0 errors", res.get("total_errors") == 0)
    m2 = compare_quote("Settings change (fuel 5.00, margin 30 %, 52in speed 50,000, pay 28)", wb, e, SAMPLE, s2)
    compare_customer("Settings change", wb, m2, s2, SAMPLE)
    check("Settings change: the price moved", m2["price"] != quote(SAMPLE, s)["price"], f"{m2['price']} vs {quote(SAMPLE, s)['price']}")
    check("Settings change: dashboard break-even updates", wb[E.S_DASH]["B7"].value == f"${s2['breakeven_hr']:,.2f}",
          f"{wb[E.S_DASH]['B7'].value!r} vs {s2['breakeven_hr']:.2f}")
    check("Settings change: QUICK QUOTE tile updates", wb[E.S_QQ]["F6"].value == f"${m2['price']:,.2f}", f"{wb[E.S_QQ]['F6'].value!r}")
    report["settings_change"] = {"before": quote(SAMPLE, s)["price"], "after": m2["price"]}

    # ---- 5. blank file
    wb, e, res, tmp_blank = build(False)
    check("Blank: 0 formula errors", res.get("total_errors") == 0)
    lg, rt, se, db, qq = wb[E.S_LOG], wb[E.S_ROUTE], wb[E.S_SEASON], wb[E.S_DASH], wb[E.S_QQ]
    check("Blank: quote log calculated column blank (300 rows)", all(lg[f"M{r}"].value in (None, "") for r in range(E.LOG_FIRST, E.LOG_LAST + 1)))
    check("Blank: route visits-per-week blank (100 rows)", all(rt[f"J{r}"].value in (None, "") for r in range(E.RT_FIRST, E.RT_LAST + 1)))
    check("Blank: route weekday summary blank", all(rt[f"{c}{r}"].value in (None, "") for r in range(8, 15) for c in "RSTUVWX"))
    check("Blank: season totals blank", all(se[f"{c}{r}"].value in (None, "") for r in range(8, 20) for c in "FHI"))
    check("Blank: quick quote shows no price until an area is entered",
          qq[e.Q["price"].replace("$", "")].value in (None, "") and (qq[e.Q["warning"].replace("$", "")].value or "").startswith("Enter"))
    check("Blank: log tiles show dashes", lg["D5"].value == "–" and lg["F5"].value == "–", f"{lg['D5'].value!r} {lg['F5'].value!r}")
    check("Blank: dashboard win rate and best day show dashes", db["J7"].value == "–" and db["J10"].value == "–")
    check("Blank: dashboard break-even uses the default settings", db["B7"].value == f"${s['breakeven_hr']:,.2f}", db["B7"].value)
    check("Blank: business name empty, quote shows a placeholder", wb[E.S_CQ]["C2"].value == "Your business name")

    # ---- 6. printing: customer quote on one page, no ### in the sample
    pages, cq_text = print_sheet(OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx"), E.S_CQ)
    check("Customer quote prints on exactly one page", pages == 1, str(pages))
    check("Customer quote printout has no Brass Ledger branding", "brass" not in cq_text.lower())
    check("Customer quote printout shows the business name and price", "Greenline Lawn Co." in cq_text and "$50.00" in cq_text)
    for name in (E.S_QQ, E.S_SET, E.S_LOG, E.S_ROUTE, E.S_SEASON, E.S_DASH, E.S_START):
        _p, text = print_sheet(OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx"), name, first_rows=60)
        check(f"{name}: no '###' (column too narrow) in the printed sample", "###" not in text)

    fails = [r for r in RESULTS if not r[1]]
    print(f"PASSED {len(RESULTS) - len(fails)} checks, FAILED {len(fails)}")
    for name, _ok, detail in fails[:40]:
        print("  FAIL", name, detail)
    report["passed"], report["failed"] = len(RESULTS) - len(fails), len(fails)
    report["checks"] = [r[0] for r in RESULTS]
    (OUT.parent / "test_results.json").write_text(json.dumps(report, indent=1, default=str))
    return 1 if fails else 0


def print_sheet(path, sheet, first_rows=None):
    """Print one tab to PDF with LibreOffice. Returns (pages, text)."""
    wb = load_workbook(path)
    for ws in wb.worksheets:
        if ws.title != sheet:
            ws.print_area = "ZZ900:ZZ900"
        elif first_rows:
            import re
            col = re.findall(r":\$?([A-Z]+)\$?\d+", str(ws.print_area))[0]
            ws.print_area = f"A1:{col}{first_rows}"
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "p.xlsx"
    wb.save(p)
    subprocess.run([sys.executable, RECALC, str(p), "240"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(p)], capture_output=True)
    pdf = tmp / "p.pdf"
    n = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    pages = 0
    text = ""
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), str(pdf), "-"], capture_output=True, text=True).stdout
        if t.strip():
            pages += 1
            text += t
    return pages, text


if __name__ == "__main__":
    sys.exit(main())
