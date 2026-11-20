"""Tests for the Cake Pricing Calculator.

1. Both files recalculated in LibreOffice headless: 0 formula errors, no error values.
2. Unit conversions: 12 hand-worked conversions placed in a test recipe and compared with the workbook.
3. Independent Python model (no formulas): ingredient costs, all sample recipes, both builder cakes (quantities, costs,
   servings, price, price per serving, deposit, hourly earnings), both batches (cost and prices).
4. Metric switch: costs and prices identical; displayed quantities change to ml / g.
5. Edge cases: unused tiers, an ingredient without grams per cup used in cups, margin 0 %, a missing pan size.
6. Ingredient price change ripples through recipes, cake builder, batch pricing and the customer quote.
7. Order tracker and dashboard; blank file shows blanks; customer quote one page on letter and A4, no Brass Ledger.

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

import cake_config as CFG
import cake_engine as E

RECALC = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
OUT = Path(__file__).resolve().parent.parent / "dist" / "cake-pricing-calculator"
RESULTS = []
TODAY = dt.date.today()
ERRS = ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!")


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


def money(x):
    return f"${x:,.2f}"


def roundup(x, inc):
    return math.ceil(round(x, 6) / inc) * inc if inc > 0 else rnd(x, 2)


# ================================================================== model
UNIT = {u: (t, f) for u, t, f in CFG.UNITS}
CUP = UNIT["cup"][1]


def ingredients(over=None):
    ing = {}
    for name, price, size, unit, gpc, gpi in CFG.INGREDIENTS:
        if over and name in over:
            price = over[name]
        t, f = UNIT[unit]
        base = size * f
        g = ml = item = None
        if t == "weight":
            g = price / base
        elif t == "volume" and gpc:
            g = price / (base / CUP * gpc)
        elif t == "count" and gpi:
            g = price / (base * gpi)
        if t == "volume":
            ml = price / base
        elif g is not None and gpc:
            ml = g * gpc / CUP
        if t == "count":
            item = price / base
        elif g is not None and gpi:
            item = g * gpi
        ing[name] = dict(g=g, ml=ml, item=item)
    return ing


def line_cost(ing, name, qty, unit):
    t, f = UNIT[unit]
    c = ing[name][{"weight": "g", "volume": "ml", "count": "item"}[t]]
    return None if c is None else qty * f * c


def recipes(ing):
    out = {}
    for name, rtype, yq, yu, lines in CFG.RECIPES:
        costs = [line_cost(ing, *ln) for ln in lines]
        total = None if any(x is None for x in costs) else sum(costs)
        yt, yf = UNIT[yu]
        out[name] = dict(total=total, ytype=yt, ybase=yq * yf, cpb=None if total is None else total / (yq * yf),
                         per_yield=None if total is None else total / yq, lines=costs)
    return out


PANS = {f"{p[0]}|{p[1]}": p for p in CFG.PANS}
COVER = {c[0]: c for c in CFG.COVERINGS}
LEVEL = dict(CFG.LEVELS)
EXTRA = dict(CFG.EXTRAS)
SUPPLY = dict(CFG.SUPPLIES)


def settings(over=None):
    s = dict(CFG.TARGETS)
    s.update(over or {})
    s["oh_year"] = sum(v for _n, v in CFG.OVERHEAD)
    s["oh_hour"] = s["oh_year"] / s["hours_year"]
    s["oh_order"] = s["oh_year"] / s["orders_year"]
    return s


def cake(d, rec, s):
    tiers = []
    for shape, size, layers, bat, fil, fro, cov in d["tiers"]:
        p = PANS[f"{shape}|{size}"]
        _sh, _sz, _cm, batter, fill_, frost, fondant, party, wedding = p
        cv = COVER[cov or CFG.COVERINGS[0][0]]
        v = layers * batter * CUP
        w = (layers - 1) * fill_ * CUP if fil else 0
        x = frost * cv[1] * layers / 2 * CUP if fro else 0
        y = (fondant * layers / 2) if cv[2] == "Yes" else 0
        serv = math.floor((wedding if d["style"] == "Wedding" else party) * layers / 2)
        cost = v * rec[bat]["cpb"] + (w * rec[fil]["cpb"] if w else 0) + (x * rec[fro]["cpb"] if x else 0) + \
            (y * rec[d["fondant"]]["cpb"] if y else 0)
        tiers.append(dict(v=v, w=w, x=x, y=y, serv=serv, cost=cost))
    m = LEVEL[d["level"]]
    hours = sum(h * (m if t == CFG.DECOR_TASK else 1) for t, h in zip(CFG.TASKS, d["hours"]))
    o = dict(tiers=tiers, hours=hours)
    o["ing"] = sum(t["cost"] for t in tiers)
    o["dec"] = sum(EXTRA[n] * q_ for n, q_ in d["extras"])
    o["sup"] = sum(SUPPLY[n] * q_ for n, q_ in d["supplies"])
    o["lab"] = hours * s["rate"]
    o["oh"] = s["oh_order"] if s["method"] == "Per order" else hours * s["oh_hour"]
    o["deliv"] = (d["miles"] * s["mile_rate"] + (s["setup_fee"] if d["delivery"] == "Delivery + set-up" else 0)) \
        if d["delivery"].startswith("Delivery") else 0
    o["cost"] = o["ing"] + o["dec"] + o["sup"] + o["lab"] + o["oh"] + o["deliv"]
    o["suggested"] = roundup(o["cost"] / (1 - s["margin"]), s["round_cake"])
    o["price"] = d["own"] if d.get("own") else o["suggested"]
    o["servings"] = sum(t["serv"] for t in tiers)
    o["per_serving"] = o["price"] / o["servings"]
    o["profit"] = o["price"] - o["cost"]
    o["hourly"] = (o["price"] - (o["cost"] - o["lab"])) / hours
    o["deposit"] = rnd(o["price"] * s["deposit"], 2)
    o["balance"] = o["price"] - o["deposit"]
    return o


def batch(b, rec, s):
    name, r_, own, batches, fr, fq, fu, lvl, extra, pack, hrs, dhrs = b
    per = own or (rec[r_]["ybase"] if rec[r_]["ytype"] == "count" else 0)
    o = dict(items=batches * per)
    o["c_rec"] = batches * rec[r_]["total"]
    t, f = UNIT[fu]
    o["c_frost"] = o["items"] * fq * f * rec[fr]["cpb"] if fr else 0
    o["c_dec"] = o["items"] * extra
    o["c_pack"] = o["items"] / 12 * pack
    o["hrs"] = hrs + dhrs * LEVEL[lvl]
    o["c_lab"] = o["hrs"] * s["rate"]
    o["c_oh"] = s["oh_order"] if s["method"] == "Per order" else o["hrs"] * s["oh_hour"]
    o["cost"] = sum(o[k] for k in ("c_rec", "c_frost", "c_dec", "c_pack", "c_lab", "c_oh"))
    ci = o["cost"] / o["items"]
    o["cost_item"] = ci
    m = s["margin"]
    o["p_item"] = roundup(ci / (1 - m), s["round_item"])
    o["p_half"] = roundup(ci * 6 / (1 - m), s["round_dozen"])
    o["p_dozen"] = roundup(ci * 12 / (1 - m), s["round_dozen"])
    o["hourly"] = (o["items"] * o["p_dozen"] / 12 - (o["cost"] - o["c_lab"])) / o["hrs"]
    return o


# ================================================================== workbook helpers
def build(sample=True, edit=None):
    e = E.CakeEngine(CFG, sample)
    wb = e.build()
    if edit:
        edit(wb, e)
    tmp = Path(tempfile.mkdtemp()) / "t.xlsx"
    wb.save(tmp)
    res = json.loads(subprocess.run([sys.executable, RECALC, str(tmp), "300"], capture_output=True, text=True).stdout or "{}")
    return load_workbook(tmp, data_only=True), e, res


def scan(wb):
    return [f"{ws.title}!{c.coordinate}={c.value}" for ws in wb.worksheets for row in ws.iter_rows() for c in row
            if isinstance(c.value, str) and c.value in ERRS]


def setting(wb, e, key, value):
    wb[E.S_SET][e.ref(key)] = value


def cell(ref):
    return ref.replace("$", "")


def compare_cake(label, wb, e, slot, m, metric=False):
    cb = wb[E.S_CAKE]
    A = e.A[slot]
    g = lambda k: cb[cell(A[k])].value
    for k in ("ing", "dec", "sup", "lab", "oh", "deliv", "cost"):
        check(f"{label}: {k}", close(g(k), m[k]), f"{g(k)!r} vs {m[k]!r}")
    for k in ("suggested", "price", "servings", "per_serving", "profit", "hourly", "deposit", "balance"):
        check(f"{label}: {k}", close(g(k), m[k], 1e-6 if k in ("per_serving", "hourly") else 0.006), f"{g(k)!r} vs {m[k]!r}")
    check(f"{label}: total hours", close(cb[cell(A["hours"])].value, m["hours"], 1e-9))
    disp = 1 if metric else CUP
    fon = 1 if metric else UNIT["oz"][1]
    for k, t in enumerate(m["tiers"]):
        r = A["t1"] + k
        got = [cb[f"{c}{r}"].value for c in "JKLMNO"]
        exp = [t["v"] / disp, t["w"] / disp if t["w"] else None, t["x"] / disp if t["x"] else None,
               t["y"] / fon if t["y"] else None, t["cost"], t["serv"]]
        check(f"{label}: tier {k + 1} batter, filling, frosting, fondant, cost, servings",
              all(close(a, b, 1e-6) for a, b in zip(got, exp)), f"{got} vs {exp}")
    for k in range(len(m["tiers"]), E.TIERS):
        r = A["t1"] + k
        check(f"{label}: unused tier {k + 1} blank", all(cb[f"{c}{r}"].value in (None, "") for c in "JKLMNO"))


def main():
    report = {}
    for p in (OUT / (CFG.OUT_NAME + ".xlsx"), OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx")):
        tmp = Path(tempfile.mkdtemp()) / p.name
        tmp.write_bytes(p.read_bytes())
        res = json.loads(subprocess.run([sys.executable, RECALC, str(tmp), "300"], capture_output=True, text=True).stdout)
        bad = scan(load_workbook(tmp, data_only=True))
        check(f"{p.name}: LibreOffice reports 0 formula errors", res.get("total_errors") == 0, json.dumps(res.get("error_summary")))
        check(f"{p.name}: no error values in any cell", not bad, ", ".join(bad[:5]))
        report[p.name] = res.get("total_formulas")

    s = settings()
    ing = ingredients()
    rec = recipes(ing)

    # ---- 1. conversions placed in recipe block 10, with hand-worked expected costs
    lb, oz, tbsp, tsp, floz = 453.592, 28.3495, 14.7868, 4.92892, 29.5735
    hand = [  # (ingredient, qty, unit, expected cost, how)
        ("All-purpose flour", 2, "cup", 2 * 120 * 4.50 / (5 * lb), "2 cups × 120 g = 240 g of a $4.50 / 5 lb bag"),
        ("Granulated sugar", 8, "oz", 8 * oz * 4.00 / (4 * lb), "8 oz = 226.8 g of a $4 / 4 lb bag"),
        ("Unsalted butter", 1, "tbsp", tbsp / CUP * 227 * 5.00 / lb, "1 tbsp = 1/16 cup = 14.19 g of a $5 / 1 lb block"),
        ("Eggs, large", 3, "each", 3 * 4.20 / 12, "3 of a $4.20 dozen"),
        ("Eggs, large", 100, "g", 100 / 50 * 4.20 / 12, "100 g ÷ 50 g per egg = 2 eggs"),
        ("Whole milk", 250, "ml", 250 * 4.00 / 3785.41, "250 ml of a $4 gallon (3,785 ml)"),
        ("Heavy cream", 1, "metric cup", 250 * 5.50 / 473.176, "1 metric cup = 250 ml of a $5.50 pint"),
        ("Vanilla extract", 1, "tsp", tsp * 12.00 / (4 * floz), "1 tsp = 4.93 ml of a $12 / 4 fl oz bottle"),
        ("Cake flour", 1, "kg", 1000 * 5.50 / (2 * lb), "1 kg of a $5.50 / 2 lb box"),
        ("Eggs, large", 1, "dozen", 4.20, "a dozen eggs = the carton price"),
        ("Lemon juice", 2, "tbsp", 2 * tbsp * 3.00 / (15 * floz), "2 tbsp = 29.6 ml of a $3 / 15 fl oz bottle"),
        ("Dark chocolate", 1, "cup", 170 * 10.00 / lb, "1 cup chopped = 170 g of a $10 / 1 lb bar"),
        ("Sprinkles", 0.5, "cup", None, "no grams per cup: must show a message, not a number"),
    ]

    def put_conv(wb, e):
        ws = wb[E.S_REC]
        r0 = E.BLK_FIRST + 9 * E.REC_BLOCK
        ws[f"C{r0 + 1}"], ws[f"G{r0 + 1}"], ws[f"C{r0 + 2}"], ws[f"D{r0 + 2}"] = "Conversion test", "Other", 1, "cup"
        for j, (n, qn, u, _x, _h) in enumerate(hand):
            ws[f"B{r0 + 4 + j}"], ws[f"C{r0 + 4 + j}"], ws[f"D{r0 + 4 + j}"] = n, qn, u
    wb, e, res = build(True, put_conv)
    ws = wb[E.S_REC]
    r0 = E.BLK_FIRST + 9 * E.REC_BLOCK
    conv = []
    for j, (n, qn, u, exp, how) in enumerate(hand):
        got, msg = ws[f"E{r0 + 4 + j}"].value, ws[f"F{r0 + 4 + j}"].value
        if exp is None:
            ok = got == "–" and str(msg).startswith("No price, or add grams per cup")
        else:
            ok = close(got, exp, 1e-6) and close(line_cost(ing, n, qn, u), exp, 1e-9)
        check(f"Conversion: {qn} {u} {n} ({how})", ok, f"{got!r} {msg!r} vs {exp!r}")
        conv.append((f"{qn} {u} {n}", how, None if exp is None else round(exp, 4)))
    report["conversions"] = conv
    idx = E.IDX_FIRST + 9
    check("Conversion test recipe: total blank and index says lines to fix",
          ws[f"D{idx}"].value in (None, "") and str(ws[f"H{idx}"].value).startswith("1 ingredient line"), str(ws[f"H{idx}"].value))

    # ---- 2. ingredients and recipes
    wb, e, res = build(True)
    ig = wb[E.S_ING]
    for i, (name, *_r) in enumerate(CFG.INGREDIENTS):
        r = E.ING_FIRST + i
        got = [ig[f"{c}{r}"].value for c in "JKL"]
        exp = [ing[name]["g"], ing[name]["ml"], ing[name]["item"]]
        check(f"Ingredient {name}: cost per g, ml, item", all(close(a, b, 1e-9) for a, b in zip(got, exp)), f"{got} vs {exp}")
    rx = wb[E.S_REC]
    for k, (name, *_r) in enumerate(CFG.RECIPES):
        i = E.IDX_FIRST + k
        m = rec[name]
        check(f"Recipe {name}: total cost", close(rx[f"D{i}"].value, m["total"], 1e-6), f"{rx[f'D{i}'].value} vs {m['total']}")
        check(f"Recipe {name}: cost per yield unit", close(rx[f"G{i}"].value, m["per_yield"], 1e-6))
        r0 = E.BLK_FIRST + k * E.REC_BLOCK
        check(f"Recipe {name}: every line", all(close(rx[f"E{r0 + 4 + j}"].value, c, 1e-6) for j, c in enumerate(m["lines"])))
    report["recipes"] = {n: round(m["total"], 4) for n, m in rec.items()}

    # ---- 3. cakes and batches
    cakes = [cake(d, rec, s) for d in CFG.CAKES]
    for i, m in enumerate(cakes):
        compare_cake(f"Cake {i + 1} ({CFG.CAKES[i]['occasion']})", wb, e, i, m)
    report["cakes"] = [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != "tiers"} for m in cakes]
    report["tiers"] = [[{k: round(v, 3) for k, v in t.items()} for t in m["tiers"]] for m in cakes]
    bt = wb[E.S_BATCH]
    batches = [batch(b, rec, s) for b in CFG.BATCHES]
    for i, m in enumerate(batches):
        col = "CDEF"[i]
        for k in ("items", "c_rec", "c_frost", "c_dec", "c_pack", "hrs", "c_lab", "c_oh", "cost", "cost_item", "p_item",
                  "p_half", "p_dozen", "hourly"):
            v = bt[f"{col}{e.B[k]}"].value
            check(f"Batch {CFG.BATCHES[i][0]}: {k}", close(v, m[k], 1e-6), f"{v!r} vs {m[k]!r}")
    report["batches"] = [{k: round(v, 4) for k, v in m.items()} for m in batches]

    # ---- customer quote
    cq = wb[E.S_CQ]
    m = cakes[0]
    check("Customer quote: total, deposit, balance", cq[f"G{e.rows['cq_total']}"].value == money(m["price"])
          and cq[f"G{e.rows['cq_total'] + 1}"].value == money(m["deposit"]) and cq[f"G{e.rows['cq_total'] + 2}"].value == money(m["balance"]))
    check("Customer quote: bakery name", cq["C2"].value == CFG.BUSINESS["name"])
    check("Customer quote: servings", cq["G11"].value == f"{m['servings']} wedding", str(cq["G11"].value))
    check("Customer quote: tier lines", str(cq["B15"].value).startswith('Bottom tier: 10" round, 2 layers') and
          str(cq["B17"].value).startswith('Tier 3: 6" round') and cq["B18"].value in (None, ""), str(cq["B15"].value))
    check("Customer quote: extras with quantities", "8 × sugar flowers" in str(cq["B20"].value), str(cq["B20"].value))
    vals = [str(c.value) for row in cq.iter_rows(max_col=8) for c in row if c.value is not None]
    check("Customer quote: no Brass Ledger branding in printed columns", not any("brass" in v.lower() for v in vals))

    def pick2(wb, e):
        wb[E.S_CQ]["I4"] = 2
    wb2, e2, _ = build(True, pick2)
    check("Customer quote: switching to cake 2 shows its price and customer",
          wb2[E.S_CQ][f"G{e2.rows['cq_total']}"].value == money(cakes[1]["price"]) and wb2[E.S_CQ]["B11"].value == CFG.CAKES[1]["customer"])

    # ---- 4. metric switch
    wbm, em, res = build(True, lambda wb, e: setting(wb, e, "units", "Metric"))
    check("Metric: 0 errors", res.get("total_errors") == 0)
    for i, m in enumerate(cakes):
        compare_cake(f"Metric cake {i + 1}", wbm, em, i, m, metric=True)
    check("Metric: header shows ml", str(wbm[E.S_CAKE][f"J{em.A[0]['t1'] - 1}"].value) == "Batter (ml)")
    check("Metric: batch prices unchanged", all(close(wbm[E.S_BATCH][f"C{em.B[k]}"].value, batches[0][k], 1e-6) for k in ("cost", "p_dozen")))

    # ---- 5. edge cases
    def sprinkles_in_cups(wb, e):
        ws = wb[E.S_REC]
        r0 = E.BLK_FIRST + 3 * E.REC_BLOCK       # vanilla buttercream
        ws[f"B{r0 + 4 + 5}"], ws[f"C{r0 + 4 + 5}"], ws[f"D{r0 + 4 + 5}"] = "Sprinkles", 0.25, "cup"
    wbx, ex, res = build(True, sprinkles_in_cups)
    rx = wbx[E.S_REC]
    r0 = E.BLK_FIRST + 3 * E.REC_BLOCK
    check("Edge: sprinkles (no grams per cup) used in cups shows a message, not a number",
          rx[f"E{r0 + 9}"].value == "–" and "grams per cup" in str(rx[f"F{r0 + 9}"].value), f"{rx[f'E{r0 + 9}'].value!r} {rx[f'F{r0 + 9}'].value!r}")
    check("Edge: that recipe's total is blank, not understated", rx[f"D{E.IDX_FIRST + 3}"].value in (None, ""))
    w = wbx[E.S_CAKE][cell(ex.A[0]["warning"])].value
    check("Edge: the cake using it shows CHECK THE TIERS", str(w).startswith("CHECK THE TIERS"), str(w))
    check("Edge: the batch using it shows a check message", str(wbx[E.S_BATCH][f"C{ex.B['check']}"].value).startswith("Frosting recipe has no cost"))
    s0 = settings({"margin": 0})
    wb0, e0, res = build(True, lambda wb, e: setting(wb, e, "margin", 0))
    check("Edge: margin 0 %: 0 errors", res.get("total_errors") == 0)
    compare_cake("Edge: margin 0 %", wb0, e0, 0, cake(CFG.CAKES[0], rec, s0))

    def bad_pan(wb, e):
        wb[E.S_CAKE][f"D{e.A[0]['t1'] + 2}"] = '5"'
        wb[E.S_CAKE][f"C{e.A[0]['t1'] + 2}"] = "Square"
    wbp, ep, _ = build(True, bad_pan)
    check("Edge: square 5\" (not in the pan table) shows 'no such pan' and a warning",
          wbp[E.S_CAKE][f"N{ep.A[0]['t1'] + 2}"].value == "no such pan" and str(wbp[E.S_CAKE][cell(ep.A[0]["warning"])].value).startswith("CHECK"))
    cb = wb[E.S_CAKE]
    check("Edge: empty cake slot 3 shows blanks and asks for a tier",
          cb[cell(e.A[2]["price"])].value in (None, "") and str(cb[cell(e.A[2]["warning"])].value).startswith("Add at least one tier"))
    d_own = dict(CFG.CAKES[1], own=150)
    wbo, eo, _ = build(True, lambda wb, e: wb[E.S_CAKE].__setitem__(cell(e.A[1]["own"]), 150))
    mo = cake(d_own, rec, s)
    compare_cake("Edge: own price below cost", wbo, eo, 1, mo)
    check("Edge: own price triggers a red warning", str(wbo[E.S_CAKE][cell(eo.A[1]["warning"])].value).startswith(("BELOW", "LOW")))

    # ---- 6. ingredient price change
    ing2 = ingredients({"Unsalted butter": 7.00})
    rec2 = recipes(ing2)

    def butter(wb, e):
        wb[E.S_ING][f"C{E.ING_FIRST + [x[0] for x in CFG.INGREDIENTS].index('Unsalted butter')}"] = 7.00
    wbb, eb, res = build(True, butter)
    check("Price change: 0 errors", res.get("total_errors") == 0)
    for k, (name, *_r) in enumerate(CFG.RECIPES):
        check(f"Price change: recipe {name}", close(wbb[E.S_REC][f"D{E.IDX_FIRST + k}"].value, rec2[name]["total"], 1e-6))
    c2 = [cake(d, rec2, s) for d in CFG.CAKES]
    for i, m in enumerate(c2):
        compare_cake(f"Price change: cake {i + 1}", wbb, eb, i, m)
    b2 = batch(CFG.BATCHES[0], rec2, s)
    check("Price change: cupcake cost per item", close(wbb[E.S_BATCH][f"C{eb.B['cost_item']}"].value, b2["cost_item"], 1e-6))
    check("Price change: customer quote total", wbb[E.S_CQ][f"G{eb.rows['cq_total']}"].value == money(c2[0]["price"]),
          str(c2[0]['price']))
    report["price_change"] = {"butter": "5.00 -> 7.00", "cake1": [cakes[0]["price"], c2[0]["price"]],
                              "cupcake_item": [round(batches[0]["cost_item"], 4), round(b2["cost_item"], 4)]}

    # ---- 7. orders and dashboard
    od = wb[E.S_ORD]
    bal_total = dep_total = 0
    up = []
    for i, o in enumerate(CFG.ORDERS):
        r = E.ORD_FIRST + i
        od_, cust, _ct, ev, _pd, typ, desc, serv, price, dep, _dd, paid, st, _al = o
        bal = 0 if paid == "Yes" or st == "Cancelled" else max(0, price - dep)
        bal_total += bal
        depo = max(0, rnd(price * s["deposit"], 2) - dep) if st in ("Quoted", "Booked", "Baking") else None
        dep_total += depo or 0
        check(f"Order {cust}: balance", close(od[f"P{r}"].value, bal), f"{od[f'P{r}'].value} vs {bal}")
        if st not in ("Completed", "Cancelled") and ev >= TODAY:
            up.append((ev, r, cust))
    up.sort()
    got = [od[f"X{E.ORD_FIRST + k}"].value for k in range(len(up))]
    check("Order tracker: upcoming list sorted by event date", got == [u[2] for u in up], f"{got} vs {[u[2] for u in up]}")
    check("Order tracker: rest of the upcoming list blank", od[f"X{E.ORD_FIRST + len(up)}"].value in (None, ""))
    check("Order tracker: balances to collect tile", od["G5"].value == money(bal_total), f"{od['G5'].value} vs {bal_total}")
    check("Order tracker: deposits not yet paid tile", od["J5"].value == money(dep_total), f"{od['J5'].value} vs {dep_total}")
    live = [o for o in CFG.ORDERS if o[12] != "Cancelled"]
    month = [o for o in live if o[3].month == TODAY.month and o[3].year == TODAY.year]
    ytd = sum(o[8] for o in live if o[3].year == CFG.YEAR and o[3] <= TODAY)
    priced = [o for o in live if o[8] > 0]
    pps = sum(o[8] for o in priced if o[7] > 0) / sum(o[7] for o in priced if o[7] > 0)
    week = [o for o in CFG.ORDERS if TODAY <= o[3] <= TODAY + dt.timedelta(days=7) and o[12] not in ("Cancelled", "Completed")]
    db = wb[E.S_DASH]
    exp = {"B7": len(month), "E7": money(sum(o[8] for o in month)), "H7": money(ytd),
           "K7": money(sum(o[8] for o in priced) / len(priced)), "B10": money(pps), "F10": money(dep_total), "J10": len(week)}
    for c_, v in exp.items():
        check(f"Dashboard tile {c_}", db[c_].value == v, f"{db[c_].value!r} vs {v!r}")
    report["dashboard"] = exp
    r0 = e.rows["dash"]["types"] + 2
    for k, t in enumerate(CFG.ORDER_TYPES):
        check(f"Dashboard orders by type: {t}", db[f"C{r0 + k}"].value == sum(1 for o in live if o[5] == t))
    check("Dashboard: 2 charts", len(load_workbook(OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx"))[E.S_DASH]._charts) == 2)

    # ---- blank file
    wbk, ek, res = build(False)
    check("Blank: 0 errors", res.get("total_errors") == 0)
    ig, rx, cb, bt, od = (wbk[n] for n in (E.S_ING, E.S_REC, E.S_CAKE, E.S_BATCH, E.S_ORD))
    check("Blank: ingredient names and grams per cup prefilled, prices empty",
          ig[f"B{E.ING_FIRST}"].value == CFG.INGREDIENTS[0][0] and ig[f"F{E.ING_FIRST}"].value == CFG.INGREDIENTS[0][4]
          and ig[f"C{E.ING_FIRST}"].value is None)
    check("Blank: ingredient costs blank (no prices yet)", all(ig[f"{c}{r}"].value in (None, "") for r in range(E.ING_FIRST, E.ING_LAST + 1) for c in "JKL"))
    check("Blank: ingredient check asks for prices", ig[f"M{E.ING_FIRST}"].value == "Add the price you pay")
    check("Blank: recipe index blank (40 rows)", all(rx[f"{c}{E.IDX_FIRST + k}"].value in (None, "") for k in range(E.REC_N) for c in "BCDEFGH"))
    check("Blank: recipe lines blank", all(rx[f"{c}{E.BLK_FIRST + 4 + j}"].value in (None, "") for j in range(E.REC_LINES) for c in "EF"))
    for i in range(E.SLOTS):
        A = ek.A[i]
        check(f"Blank: cake {i + 1} blank and asks for a tier", all(cb[f"{c}{A['t1'] + k}"].value in (None, "") for k in range(E.TIERS) for c in "JKLMNO")
              and cb[cell(A["price"])].value in (None, "") and str(cb[cell(A["warning"])].value).startswith("Add at least one tier"))
    check("Blank: batch outputs blank", all(bt[f"{c}{ek.B[k]}"].value in (None, "") for c in "CDEF" for k in ("items", "cost", "p_dozen", "check")))
    check("Blank: order calculated columns blank (300 rows)", all(od[f"{c}{r}"].value in (None, "") for r in range(E.ORD_FIRST, E.ORD_LAST + 1) for c in "PQ"))
    check("Blank: upcoming list blank", all(od[f"X{E.ORD_FIRST + k}"].value in (None, "") for k in range(20)))
    check("Blank: customer quote placeholder", wbk[E.S_CQ]["C2"].value == "Your bakery name" and wbk[E.S_CQ][f"G{ek.rows['cq_total']}"].value in (None, ""))
    check("Blank: pan table and settings defaults present", wbk[E.S_SET][ek.ref("rate")].value == CFG.TARGETS["rate"])

    # ---- printing
    for paper, size in (("letter", 1), ("A4", 9)):
        pages, text = print_sheet(OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx"), E.S_CQ, paper=size)
        check(f"Customer quote prints on one {paper} page", pages == 1, str(pages))
        check(f"Customer quote on {paper}: no Brass Ledger, shows bakery and total", "brass" not in text.lower()
              and CFG.BUSINESS["name"] in text and money(cakes[0]["price"]) in text)
    for name in (E.S_START, E.S_SET, E.S_ING, E.S_REC, E.S_CAKE, E.S_BATCH, E.S_ORD, E.S_DASH):
        _p, t = print_sheet(OUT / (CFG.OUT_NAME + "_SAMPLE.xlsx"), name, first_rows=70)
        check(f"{name}: no '###' in the printed sample", "###" not in t)

    fails = [r for r in RESULTS if not r[1]]
    print(f"PASSED {len(RESULTS) - len(fails)} checks, FAILED {len(fails)}")
    for name, _ok, detail in fails[:40]:
        print("  FAIL", name, detail)
    report["passed"], report["failed"] = len(RESULTS) - len(fails), len(fails)
    (OUT.parent / "test_results.json").write_text(json.dumps(report, indent=1, default=str))
    return 1 if fails else 0


def print_sheet(path, sheet, first_rows=None, paper=None):
    wb = load_workbook(path)
    for ws in wb.worksheets:
        if ws.title != sheet:
            ws.print_area = "ZZ900:ZZ900"
        else:
            if first_rows:
                col = re.findall(r":\$?([A-Z]+)\$?\d+", str(ws.print_area))[0]
                ws.print_area = f"A1:{col}{first_rows}"
            if paper:
                ws.page_setup.paperSize = paper
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "p.xlsx"
    wb.save(p)
    subprocess.run([sys.executable, RECALC, str(p), "300"], capture_output=True)
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
