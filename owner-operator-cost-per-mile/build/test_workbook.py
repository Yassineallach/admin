"""Tests for the Owner-Operator Cost Per Mile & Load Profit Calculator.

1. Both files recalculated in LibreOffice headless: 0 formula errors.
2. Independent Python model (no formulas) of SETTINGS: fixed, variable, operating, all-in cost per mile, target and
   break-even rates, and the miles-per-month table.
3. Load checker: 4 loads (clear TAKE; NEGOTIATE; good per loaded mile but PASS with deadhead; reefer load with reefer
   fuel), every output and the counter-offer, on LOAD CHECK (PHONE) and LOAD COMPARE.
4. TRIP LOG, FUEL LOG (MPG), MONTHLY P&L and DASHBOARD against Python totals for the 3 sample months.
5. Edge cases: zero deadhead, zero miles, factoring 0 %, lumper reimbursed, empty rows, switching the equipment preset.
6. Blank file: blank rows show blanks, not zeros or errors.
7. Phone tab width at 390 px, structure (no banned functions, Tables, macros, external links), validations, protection.

Usage: python test_workbook.py          -> prints results, writes ../dist/test_results.json
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

import truck_config as C
import truck_engine as E

RECALC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
OUT = Path(__file__).resolve().parent.parent / "dist" / "owner-operator-cost-per-mile"
RESULTS = []
ERRS = ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!")
TMP = Path(tempfile.mkdtemp())


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), str(detail)))


def close(a, b, tol=0.006):
    if a in (None, "") and b in (None, ""):
        return True
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return a == b


def recalc(path):
    r = subprocess.run([sys.executable, RECALC, str(path), "300"], capture_output=True, text=True)
    return json.loads(r.stdout[r.stdout.index("{"):])


def build(sample=True, edit=None, name="t.xlsx"):
    e = E.TruckEngine(C, sample)
    wb = e.build()
    if edit:
        edit(e, wb)
    p = TMP / name
    wb.save(p)
    info = recalc(p)
    return e, load_workbook(p, data_only=True), info


# ================================================================== model
def settings_model(equip="Dry van", over=None):
    D = dict(C.SET)
    D.update(over or {})
    pr = {p[0]: p for p in C.PRESETS}[equip]
    mpg, maint, tset, tlife, defc, gph = pr[1:]
    fuel = D["fuel_price"]
    m = {}
    m["fixed_month"] = sum(a / 12 if per == "Year" else a for _, a, per, _ in C.FIXED)
    m["month_miles"] = D["weekly_miles"] * D["weeks_year"] / 12
    m["parts"] = dict(fuel=fuel / mpg, defc=defc, maint=maint, tire=tset / tlife,
                      reefer=gph * D["reefer_hours_day"] * D["load_days_week"] * fuel / D["weekly_miles"], other=D["other_var"])
    m["var"] = sum(m["parts"].values())
    m["fixed_cpm"] = m["fixed_month"] / m["month_miles"]
    m["op"] = m["var"] + m["fixed_cpm"]
    m["paypm"] = D["weekly_pay"] * 52 / (D["weekly_miles"] * D["weeks_year"])
    m["allin"] = m["op"] + m["paypm"]
    fees = D["factoring"] + D["dispatch"]
    m["fees"] = fees
    m["be_rate"] = m["op"] / (1 - fees)
    m["target"] = m["allin"] / (1 - D["margin"] - fees)
    m["sens"] = []
    for mi in D["sens"]:
        allin = m["var"] + m["fixed_month"] / mi + D["weekly_pay"] * 52 / 12 / mi
        m["sens"].append((m["fixed_month"] / mi, allin, allin / (1 - D["margin"] - fees)))
    m.update(mpg=mpg, gph=gph, fuel=fuel, D=D, permile=defc + maint + tset / tlife + D["other_var"])
    return m


def load_model(m, rate, loaded, dh, days, fuel=None, tolls=0, lumper=0, lr="", stopcost=0, stoppay=0, det=0, rhrs=None,
               fact=None, disp=None):
    D = m["D"]
    if not (rate and loaded):
        return None
    fp = fuel or m["fuel"]
    tot = loaded + dh
    rev = rate + det + stoppay
    feep = (D["factoring"] if fact is None else fact) + (D["dispatch"] if disp is None else disp)
    o = dict(tot=tot, rev=rev)
    o["fuelc"] = tot / m["mpg"] * fp
    o["reefer"] = (rhrs if rhrs else days * D["reefer_hours_day"]) * m["gph"] * fp
    o["permile"] = tot * m["permile"]
    o["trip"] = tolls + (0 if lr == "Y" else lumper) + stopcost
    o["fixed"] = tot * m["fixed_cpm"]
    o["fees"] = rev * feep
    o["opcost"] = o["fuelc"] + o["reefer"] + o["permile"] + o["trip"] + o["fixed"] + o["fees"]
    o["pay"] = tot * m["paypm"]
    o["allin"] = o["opcost"] + o["pay"]
    o["profit"] = rev - o["allin"]
    o["ppd"] = o["profit"] / days if days else None
    o["rpl"] = rate / loaded
    o["rpt"] = rev / tot
    o["cpm"] = o["allin"] / tot
    nonfee = o["opcost"] - o["fees"]
    be_rev = (nonfee + (o["pay"] if D["pass_basis"] != C.PASS_BASIS[0] else 0)) / (1 - feep)
    t_rev = (nonfee + o["pay"]) / (1 - feep - D["margin"])
    o["counter"] = -(-round(t_rev - det - stoppay, 9) // 1)
    o["be_rate"] = -(-round(be_rev - det - stoppay, 9) // 1)
    o["verdict"] = "PASS" if rev < be_rev else ("TAKE" if rev >= t_rev else "NEGOTIATE")
    return o


# ================================================================== tests
def t_recalc():
    for f in sorted(OUT.glob("*.xlsx")):
        p = TMP / f.name
        shutil.copy(f, p)
        info = recalc(p)
        check(f"LibreOffice recalc, 0 formula errors: {f.name}", info.get("total_errors") == 0,
              f'{info.get("total_formulas")} formulas, errors {info.get("error_summary")}')
        wb = load_workbook(p, data_only=True)
        bad = [(ws.title, c.coordinate, c.value) for ws in wb for row in ws.iter_rows() for c in row if c.value in ERRS]
        check(f"No error values in any cell: {f.name}", not bad, bad[:5])


def t_settings():
    e, wb, _ = build(True)
    ws = wb[E.S_SET]
    m = settings_model()
    cell = lambda k: ws[e.S[k].split("!")[1].replace("$", "")].value   # noqa: E731
    for k, v in (("fixed_month", m["fixed_month"]), ("month_miles", m["month_miles"]), ("fuel_pm", m["parts"]["fuel"]),
                 ("tire_pm", m["parts"]["tire"]), ("reefer_pm", m["parts"]["reefer"]), ("var_cpm", m["var"]),
                 ("fixed_cpm", m["fixed_cpm"]), ("op_cpm", m["op"]), ("paypm", m["paypm"]), ("allin_cpm", m["allin"]),
                 ("be_rate", m["be_rate"]), ("target_rate", m["target"])):
        check(f"SETTINGS {k} = {v:.4f}", close(cell(k), v, 1e-6), cell(k))
    s0, _ = e.rows["set"]["sens"]
    for i, (fx, allin, tgt) in enumerate(m["sens"]):
        r = s0 + i
        ok = close(ws[f"F{r}"].value, fx, 1e-6) and close(ws[f"G{r}"].value, allin, 1e-6) and close(ws[f"H{r}"].value, tgt, 1e-6)
        check(f"Miles-per-month table, {C.SET['sens'][i]:,} miles: fixed {fx:.3f}, all-in {allin:.3f}, target {tgt:.3f}", ok,
              (ws[f"F{r}"].value, ws[f"G{r}"].value, ws[f"H{r}"].value))
    return m


LOADS = {   # name: kwargs for the model; all four checked on LOAD COMPARE, the deadhead case on the phone tab as well
    "Clear TAKE": dict(rate=2600, loaded=820, dh=20, days=2),
    "NEGOTIATE": dict(rate=1350, loaded=550, dh=20, days=2, tolls=28),
    "Good per loaded mile, PASS with deadhead": dict(rate=1150, loaded=380, dh=300, days=2),
    "Detention, extra stop, lumper, own fees": dict(rate=1700, loaded=600, dh=45, days=2, fuel=6.20, lumper=80, lr="N",
                                                    stopcost=25, stoppay=75, det=100, fact=0.0, disp=0.08),
}


def compare_edit(loads):
    def edit(e, wb):
        ws = wb[E.S_CMP]
        R = e.rows["cmp"]["inputs"]
        for k in range(E.CMP_N):
            for rr in R.values():
                ws[f"{E.L(3 + k)}{rr}"] = None
        for k, kw in enumerate(loads.values()):
            col = E.L(3 + k)
            for key, v in kw.items():
                ws[f"{col}{R[{'lr': 'lumper_r'}.get(key, key)]}"] = v
    return edit


def read_compare(e, wb, k):
    ws = wb[E.S_CMP]
    O = e.rows["cmp"]["outs"]
    col = E.L(3 + k)
    return {key: ws[f"{col}{r}"].value for key, r in O.items()}


def t_loads(m):
    e, wb, _ = build(True, compare_edit(LOADS), "cmp.xlsx")
    names = list(LOADS)
    verdicts = {}
    for k, name in enumerate(names):
        o = load_model(m, **LOADS[name])
        got = read_compare(e, wb, k)
        diffs = [key for key in ("tot", "rev", "fuelc", "reefer", "permile", "trip", "fixed", "fees", "opcost", "pay", "allin",
                                 "profit", "ppd", "rpl", "rpt", "counter", "be_rate", "verdict")
                 if not close(got[key], o[key], 0.01)]
        verdicts[name] = got["verdict"]
        check(f"LOAD COMPARE '{name}': {o['verdict']}, profit ${o['profit']:,.2f}, profit/day ${o['ppd']:,.2f}, "
              f"counter-offer ${o['counter']:,.0f}", not diffs, f"mismatch: {diffs}" if diffs else "")
    check("The four loads give TAKE, NEGOTIATE, PASS as designed",
          (verdicts[names[0]], verdicts[names[1]], verdicts[names[2]]) == ("TAKE", "NEGOTIATE", "PASS"), verdicts)
    o = load_model(m, **LOADS[names[2]])
    check("Deadhead case: the loaded-mile rate beats the target rate, yet the verdict is PASS",
          o["rpl"] > m["target"] and o["verdict"] == "PASS", f"${o['rpl']:.3f}/loaded mi vs target ${m['target']:.3f}")
    # best-per-day marker
    ws = wb[E.S_CMP]
    br = e.rows["cmp"]["best"]
    ppd = [load_model(m, **kw)["ppd"] for kw in LOADS.values()]
    best = ppd.index(max(ppd))
    marks = [ws[f"{E.L(3 + k)}{br}"].value for k in range(E.CMP_N)]
    check("LOAD COMPARE marks only the best profit per day", marks[best] == "BEST PER DAY" and marks.count("BEST PER DAY") == 1, marks)
    # phone tab (sample = the deadhead case)
    e, wb, _ = build(True, name="phone.xlsx")
    ws = wb[E.S_CHECK]
    o = load_model(m, **C.LOAD_CHECK)
    got = {k: ws[e.cells[k]].value for k in ("rpl", "rpt", "cpm", "allin", "profit", "ppd", "counter", "be_rate", "fuelc",
                                             "fees", "fixed", "opcost", "pay")}
    diffs = [k for k, v in got.items() if not close(v, o[k], 0.01)]
    check(f"LOAD CHECK (PHONE) sample load: {o['verdict']}, every output matches", not diffs and ws[e.cells["verdict"]].value == o["verdict"],
          diffs or ws[e.cells["verdict"]].value)


def t_reefer():
    def edit(e, wb):
        wb[E.S_SET][e.S["equip"].split("!")[1].replace("$", "")] = "Reefer"
        compare_edit({"Reefer": dict(rate=2400, loaded=780, dh=40, days=2),
                      "Reefer, own hours": dict(rate=2400, loaded=780, dh=40, days=2, rhrs=30)})(e, wb)
    e, wb, _ = build(True, edit, "reefer.xlsx")
    m = settings_model("Reefer")
    ws = wb[E.S_SET]
    got = ws[e.S["var_cpm"].split("!")[1].replace("$", "")].value
    check(f"Reefer preset: variable cost per mile {m['var']:.4f} includes reefer fuel {m['parts']['reefer']:.4f}/mile",
          close(got, m["var"], 1e-6), got)
    for k, kw in enumerate(({"rate": 2400, "loaded": 780, "dh": 40, "days": 2},
                            {"rate": 2400, "loaded": 780, "dh": 40, "days": 2, "rhrs": 30})):
        o = load_model(m, **kw)
        g = read_compare(e, wb, k)
        diffs = [x for x in ("reefer", "fuelc", "allin", "profit", "counter", "verdict") if not close(g[x], o[x], 0.01)]
        check(f"Reefer load {k + 1}: reefer fuel ${o['reefer']:.2f}, verdict {o['verdict']}, counter ${o['counter']:,.0f}",
              not diffs, diffs)


def t_presets():
    for equip in ("Hotshot (CDL)", "Box truck", "Flatbed"):
        def edit(e, wb, equip=equip):
            wb[E.S_SET][e.S["equip"].split("!")[1].replace("$", "")] = equip
        e, wb, _ = build(True, edit, "preset.xlsx")
        m = settings_model(equip)
        ws = wb[E.S_SET]
        g = lambda k: ws[e.S[k].split("!")[1].replace("$", "")].value   # noqa: E731
        check(f"Switching preset to {equip}: MPG {m['mpg']}, variable {m['var']:.4f}, all-in {m['allin']:.4f}",
              close(g("mpg"), m["mpg"]) and close(g("var_cpm"), m["var"], 1e-6) and close(g("allin_cpm"), m["allin"], 1e-6),
              (g("mpg"), g("var_cpm"), g("allin_cpm")))

    def edit(e, wb):
        ws = wb[E.S_SET]
        ws[e.S["equip"].split("!")[1].replace("$", "")] = "Hotshot (CDL)"
        r = int(e.S["mpg"].split("$")[-1])
        ws[f"D{r}"] = 12.5
    e, wb, _ = build(True, edit, "override.xlsx")
    ws = wb[E.S_SET]
    r = int(e.S["mpg"].split("$")[-1])
    check("Your own value overrides the preset (hotshot MPG 12.5 typed over 10.0)",
          ws[f"C{r}"].value == 10.0 and ws[f"E{r}"].value == 12.5, (ws[f"C{r}"].value, ws[f"E{r}"].value))


def t_edges(m):
    loads = {"Zero deadhead": dict(rate=1500, loaded=600, dh=0, days=2),
             "Zero miles": dict(rate=1500, loaded=0, dh=0, days=1),
             "Factoring 0 %": dict(rate=1500, loaded=600, dh=50, days=2, fact=0.0),
             "Lumper reimbursed": dict(rate=1500, loaded=600, dh=50, days=2, lumper=150, lr="Y"),
             "Days blank": dict(rate=1500, loaded=600, dh=50, days=0)}
    e, wb, _ = build(True, compare_edit(loads), "edges.xlsx")
    g = [read_compare(e, wb, k) for k in range(5)]
    o0 = load_model(m, **loads["Zero deadhead"])
    check("Zero deadhead: rate per loaded mile = all-in rate per total mile", close(g[0]["rpl"], g[0]["rpt"]) and close(g[0]["profit"], o0["profit"], 0.01),
          (g[0]["rpl"], g[0]["rpt"]))
    check("Zero miles: every output blank, no error, no verdict", all(v in (None, "", 0) for v in g[1].values()), g[1])
    o2 = load_model(m, **loads["Factoring 0 %"])
    check("Factoring 0 % on the load: fees $0 and profit matches", close(g[2]["fees"], 0) and close(g[2]["profit"], o2["profit"], 0.01),
          (g[2]["fees"], g[2]["profit"]))
    o3 = load_model(m, **loads["Lumper reimbursed"])
    check("Lumper marked reimbursed is not counted as a cost", close(g[3]["trip"], 0) and close(g[3]["profit"], o3["profit"], 0.01), g[3]["trip"])
    check("Days left blank: profit shows, profit per day stays blank", g[4]["profit"] not in (None, "") and g[4]["ppd"] in (None, ""),
          (g[4]["profit"], g[4]["ppd"]))

    def zero_fact(e, wb):
        wb[E.S_SET][e.S["fact"].split("!")[1].replace("$", "")] = 0
    e, wb, _ = build(True, zero_fact, "fact0.xlsx")
    m0 = settings_model(over={"factoring": 0.0})
    ws = wb[E.S_SET]
    v = ws[e.S["target_rate"].split("!")[1].replace("$", "")].value
    check(f"Factoring 0 % in SETTINGS: target rate = all-in / (1 - margin) = {m0['target']:.4f}", close(v, m0["target"], 1e-6), v)
    t = wb[E.S_TRIP]
    check("Factoring 0 % in SETTINGS: trip log factoring fees all $0", all(close(t[f"Q{r}"].value, 0) for r in range(E.TRIP_FIRST, E.TRIP_FIRST + 40)))


def t_tracking(m):
    e, wb, _ = build(True, name="track.xlsx")
    trips = C.sample_trips()
    t = wb[E.S_TRIP]
    p = wb[E.S_PNL]
    D = C.SET
    for i, tr in enumerate(trips):
        r = E.TRIP_FIRST + i
        tot = tr["loaded"] + tr["dh"]
        rev = tr["lh"] + tr["fsc"] + tr["det"] + tr["oth"]
        fact = 0 if tr["factored"] == "N" else rev * D["factoring"]
        reserve = tot * m["permile"]
        profit = rev - tr["fuel"] - tr["tolls"] - tr["ocost"] - fact - rev * D["dispatch"] - reserve - tot * m["fixed_cpm"]
        days = (tr["de"] - tr["pu"]).days + 1
        tr.update(tot=tot, rev=rev, fact=fact, reserve=reserve, profit=profit, days=days)
        ok = (close(t[f"V{r}"].value, tot) and close(t[f"W{r}"].value, rev) and close(t[f"Q{r}"].value, fact)
              and close(t[f"AB{r}"].value, profit, 0.01) and close(t[f"AD{r}"].value, profit / days, 0.01)
              and close(t[f"Y{r}"].value, rev / tot))
        if not ok:
            check(f"Trip row {r}", False, [t[f"{c}{r}"].value for c in ("V", "W", "Q", "AB", "AD")])
    check(f"TRIP LOG: all {len(trips)} sample trips match (miles, revenue, fees, profit, profit per day)", True)
    blank_row = E.TRIP_FIRST + len(trips) + 3
    check("TRIP LOG: empty rows show blanks", all(t[f"{c}{blank_row}"].value in (None, "") for c in
                                                   ("Q", "R", "V", "W", "X", "Y", "Z", "AA", "AB", "AC", "AD")))
    # fuel
    fl = C.sample_fuel()
    f = wb[E.S_FUEL]
    bad = []
    for i in range(1, len(fl)):
        r = E.FUEL_FIRST + i
        mpg = (fl[i]["odo"] - fl[i - 1]["odo"]) / fl[i]["gal"]
        if not close(f[f"K{r}"].value, mpg, 1e-6):
            bad.append(r)
    check(f"FUEL LOG: MPG between fill-ups for {len(fl) - 1} fills", not bad, bad)
    avg = (fl[-1]["odo"] - fl[0]["odo"]) / (sum(x["gal"] for x in fl) - fl[0]["gal"])
    check(f"FUEL LOG: average MPG {avg:.2f}", close(f["I5"].value, avg, 1e-6), f["I5"].value)
    sm = {}
    for d, _, st, mi in C.sample_state_miles():
        sm[st] = sm.get(st, 0) + mi
    tr_ = e.rows["fuel_states_total"]
    got = {f[f"R{r}"].value: f[f"S{r}"].value for r in range(E.FUEL_FIRST, tr_) if f[f"S{r}"].value}
    check(f"FUEL LOG: miles by state for the year ({len(sm)} states, {sum(sm.values()):,} miles)", got == sm,
          {k: (got.get(k), v) for k, v in sm.items() if got.get(k) != v})
    # P&L by month
    m1 = e.rows["pnl"]["m1"]
    months = sorted({x["pu"].month for x in trips})
    fixed_m = m["fixed_month"]
    tot_net = 0
    for mo in range(1, 13):
        r = m1 + mo - 1
        mt = [x for x in trips if x["pu"].month == mo]
        miles = sum(x["tot"] for x in mt)
        rev = sum(x["rev"] for x in mt)
        fuel = sum(x["fuel"] for x in mt)
        other = sum(x["tolls"] + x["ocost"] + x["reserve"] for x in mt)
        fixed = fixed_m if months[0] <= mo <= months[-1] else 0
        fees = sum(x["fact"] + x["rev"] * D["dispatch"] for x in mt)
        net = rev - fuel - other - fixed - fees - C.PAY_DRAWN.get(mo, 0)
        tot_net += net
        ok = (close(p[f"D{r}"].value, miles) and close(p[f"F{r}"].value, rev, 0.01) and close(p[f"G{r}"].value, fuel, 0.01)
              and close(p[f"H{r}"].value, other, 0.01) and close(p[f"I{r}"].value, fixed, 0.01) and close(p[f"M{r}"].value, net, 0.01))
        if miles:
            cpm = (fuel + other + fixed) / miles
            ok = ok and close(p[f"O{r}"].value, cpm, 1e-6)
            flag = cpm > m["op"] * 1.1
            ok = ok and (str(p[f"Q{r}"].value).startswith("Above") == flag)
            check(f"MONTHLY P&L {C.MONTHS[mo - 1]}: {mo and len(mt)} loads, {miles:,} mi, revenue ${rev:,.2f}, net ${net:,.2f}, "
                  f"actual CPM ${cpm:.3f}{' (flagged >10 % above estimate)' if flag else ''}", ok,
                  [p[f"{c}{r}"].value for c in "DFGHIMOQ"])
        elif not ok:
            check(f"MONTHLY P&L {C.MONTHS[mo - 1]} (no loads)", False)
    # days away
    away = {}
    for a, b in C.AWAY:
        d = dt.date.fromisoformat(a)
        while d <= dt.date.fromisoformat(b):
            away[d.month] = away.get(d.month, 0) + 1
            d += dt.timedelta(days=1)
    got = {mo: p[f"R{m1 + mo - 1}"].value for mo in range(1, 13) if p[f"R{m1 + mo - 1}"].value}
    check(f"Days away from home split by month {away}", got == away, got)
    # dashboard
    d = wb[E.S_DASH]
    miles = sum(x["tot"] for x in trips)
    unpaid = sum(x["rev"] for x in trips if x["paid"] != "Y")
    ppd = sum(x["profit"] for x in trips) / sum(x["days"] for x in trips)
    exp = {"B7": m["op"], "E7": m["allin"], "H7": sum(x["rev"] for x in trips) / miles,
           "K7": sum(x["dh"] for x in trips) / miles, "B10": tot_net, "F10": ppd, "J10": unpaid}
    bad = {k: (d[k].value, v) for k, v in exp.items() if not close(d[k].value, v, 0.01)}
    check(f"DASHBOARD tiles: net profit YTD ${tot_net:,.2f}, profit/day ${ppd:,.2f}, unpaid ${unpaid:,.2f}", not bad, bad)
    check("DASHBOARD has 3 charts", len(load_workbook(TMP / "track.xlsx")[E.S_DASH]._charts) == 3)


def t_blank():
    p = TMP / "blank.xlsx"
    shutil.copy(OUT / f"{C.OUT_NAME}.xlsx", p)
    recalc(p)
    wb = load_workbook(p, data_only=True)
    e = E.TruckEngine(C, False)
    e.build()
    bad = []
    for ws, cols, first, last in ((wb[E.S_TRIP], "QRVWXYZ", E.TRIP_FIRST, E.TRIP_FIRST + 20),
                                  (wb[E.S_FUEL], "GJK", E.FUEL_FIRST, E.FUEL_FIRST + 20)):
        for r in range(first, last):
            for c in cols:
                if ws[f"{c}{r}"].value not in (None, ""):
                    bad.append((ws.title, f"{c}{r}", ws[f"{c}{r}"].value))
        for c in ("AA", "AB", "AC", "AD") if ws.title == E.S_TRIP else ():
            for r in range(first, last):
                if ws[f"{c}{r}"].value not in (None, ""):
                    bad.append((ws.title, f"{c}{r}", ws[f"{c}{r}"].value))
    ch = wb[E.S_CHECK]
    for k in ("rpl", "profit", "ppd", "counter", "verdict"):
        v = ch[e.cells[k]].value
        if v not in (None, ""):
            bad.append(("check", k, v))
    check("Blank file: empty log rows and the empty load check show blanks, not zeros or errors", not bad, bad[:6])
    s = wb[E.S_SET]
    check("Blank file: SETTINGS keeps the presets and the labelled example values",
          s[e.S["equip"].split("!")[1].replace("$", "")].value == "Dry van" and "EXAMPLE VALUES" in s["B4"].value)
    check("Blank file: no sample trips, fuel or name", wb[E.S_TRIP][f"B{E.TRIP_FIRST}"].value is None
          and wb[E.S_FUEL][f"B{E.FUEL_FIRST}"].value is None and s["C7"].value is None)


def t_structure():
    sys.path.insert(0, "/home/user/admin/productivity-bundle/build")
    import re
    import zipfile
    banned = re.compile(r"LAMBDA|LET\(|XLOOKUP|FILTER\(|UNIQUE\(|SORT\(|SEQUENCE\(|\[#|TEXT\(|INDIRECT|OFFSET\(|MAXIFS|MINIFS|(?<![A-Z])IFS\(|SWITCH\(|CONCAT\(|TEXTJOIN|\[\d+\]")
    for f in sorted(OUT.glob("*.xlsx")):
        wb = load_workbook(f)
        forms = [c.value for ws in wb for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")]
        bad = [x for x in forms if banned.search(x)]
        names = zipfile.ZipFile(f).namelist()
        check(f"{f.name}: {len(forms):,} formulas, none use functions missing from Excel 2016 / Google Sheets", not bad, bad[:3])
        check(f"{f.name}: no Excel Tables, macros or external links",
              not any(n.startswith("xl/tables/") or "vba" in n.lower() or "externalLink" in n for n in names))
        check(f"{f.name}: tab order", wb.sheetnames == E.ORDER, wb.sheetnames)
        unprot = [ws.title for ws in wb if not ws.protection.sheet or ws.protection.password]
        check(f"{f.name}: every tab protected, no password", not unprot, unprot)
        dv = {ws.title: len(ws.data_validations.dataValidation) for ws in wb}
        check(f"{f.name}: dropdowns / validation on every input tab {dv}", all(dv[t] > 0 for t in E.ORDER if t not in (E.S_START, E.S_DASH)))
        frozen = {ws.title: ws.freeze_panes for ws in wb}
        check(f"{f.name}: header rows frozen on SETTINGS, COMPARE, TRIP LOG, FUEL LOG, P&L",
              all(frozen[t] and frozen[t] != "B1" for t in (E.S_SET, E.S_CMP, E.S_TRIP, E.S_FUEL, E.S_PNL)), frozen)
        cf_cross = [r for ws in wb for rng in ws.conditional_formatting for r in rng.rules for fm in (r.formula or []) if "!" in fm]
        check(f"{f.name}: conditional formatting uses same-sheet formulas only (Google Sheets)", not cf_cross)
        # unlocked inputs / locked calcs
        ws = wb[E.S_TRIP]
        check(f"{f.name}: trip log inputs unlocked, calculated cells locked",
              not ws[f"G{E.TRIP_FIRST}"].protection.locked and ws[f"AB{E.TRIP_FIRST}"].protection.locked)
    # phone width
    wb = load_workbook(OUT / f"{C.OUT_NAME}_SAMPLE.xlsx")
    ws = wb[E.S_CHECK]
    px = sum(int(ws.column_dimensions[c].width * 7 + 5) for c in "ABCD")
    cd = ws.column_dimensions["E"]
    visible = [] if (cd.hidden and cd.min == 5 and cd.max >= 26) else ["E:Z"]
    check(f"LOAD CHECK (PHONE): visible columns A-D are {px} px wide (+46 px row numbers = {px + 46} px), fits a 390 px phone, "
          f"columns E-Z hidden", px + 46 <= 390 and not visible, visible)
    merged = all(any(str(m).startswith(f"B{r}:C{r}") for m in ws.merged_cells.ranges)
                 for r in range(4, 12, 2))
    check("LOAD CHECK (PHONE): one column of inputs, each label above its input", merged)


if __name__ == "__main__":
    t_recalc()
    m = t_settings()
    t_loads(m)
    t_reefer()
    t_presets()
    t_edges(m)
    t_tracking(m)
    t_blank()
    t_structure()
    ok = sum(1 for _, o, _ in RESULTS if o)
    for name, o, detail in RESULTS:
        print(("PASS " if o else "FAIL ") + name + (f"   [{detail}]" if detail and not o else ""))
    print(f"\n{ok}/{len(RESULTS)} passed")
    (OUT.parent / "test_results.json").write_text(json.dumps(RESULTS, indent=1, default=str))
    shutil.rmtree(TMP, ignore_errors=True)
