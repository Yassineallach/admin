"""Brass Ledger Cake Pricing Calculator: ingredient library with unit conversion, recipe library, tiered cake builder,
batch pricing, customer quote, order tracker and dashboard.

Built on the shared pricing engine (engine.py, from the Lawn Care and Pressure Washing products): page styling, title
bars, tiles, validation helpers, total rows, currency text, icon sidebar, protection and the build/finish flow.

Units: every quantity is converted to grams (weight), millilitres (volume) or items (count) using the units table on
SETTINGS. Weight <-> volume uses each ingredient's grams per cup; count <-> weight uses grams per item.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, DoughnutChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, Protection, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.hyperlink import Hyperlink

import engine as base
from engine import BP, CUST, DATE, MONEY, MONEY0, PCT
from xlkit import (BRASS, BRASS_TINT, GREEN, GREEN2, INK, INK2, NEG, NEG_TINT, PAPER, POS, POS_TINT, TITLE, WHITE,
                   fill, font, q)

S_START, S_SET, S_ING, S_REC, S_CAKE, S_BATCH, S_CQ, S_ORD, S_DASH = (
    "START HERE", "SETTINGS", "INGREDIENTS", "RECIPES", "CAKE BUILDER", "BATCH PRICING", "CUSTOMER QUOTE",
    "ORDER TRACKER", "DASHBOARD")
ORDER = [S_START, S_SET, S_ING, S_REC, S_CAKE, S_BATCH, S_CQ, S_ORD, S_DASH]
NAV = [(S_DASH, "bar_chart", "Home"), (S_START, "question", "Start"), (S_SET, "gear", "Setup"),
       (S_ING, "box", "Ingred."), (S_REC, "book", "Recipes"), (S_CAKE, "calc", "Cakes"), (S_BATCH, "stack", "Batches"),
       (S_CQ, "receipt", "Quote"), (S_ORD, "calendar", "Orders")]
DISCLAIMER = "Prices are estimates based on the numbers you enter. Not financial, legal or tax advice."
ING_FIRST, ING_N = 8, 200
ING_LAST = ING_FIRST + ING_N - 1
REC_N, REC_LINES, REC_BLOCK = 40, 16, 22
IDX_FIRST = 8
BLK_FIRST = IDX_FIRST + REC_N + 4
SLOTS, SLOT_FIRST, SLOT_SIZE = 3, 7, 56
TIERS, EXTRA_N, SUPPLY_N = 5, 6, 8
ORD_FIRST, ORD_N = 8, 300
ORD_LAST = ORD_FIRST + ORD_N - 1
BATCH_N = 4
COST4 = "0.0000"
QTY = "#,##0.0"


class CakeEngine(base.Engine):
    def __init__(self, cfg, sample: bool):
        self.cfg = cfg
        self.product = cfg.PRODUCT
        self.sample = sample
        self.home_tab, self.start_tab = S_DASH, S_START
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.ws = {n: self.wb.create_sheet(n) for n in ORDER}
        self.S, self.rows = {}, {}

    def ref(self, key):
        return self.S[key].split("!")[1].replace("$", "")

    def hdr(self, ws, r, cols, height=30, calc=""):
        for col, t in cols:
            self.header(ws[f"{col}{r}"], t, GREEN2 if col in calc else GREEN, align="left" if col in self._left else "center")
        ws.row_dimensions[r].height = height

    _left = "B"

    # ============================================================ SETTINGS
    def build_settings(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_SET]
        SQ = q(S_SET)
        widths = {"B": 40, "C": 14, "D": 12, "E": 13, "F": 13, "G": 13, "H": 13, "I": 13, "J": 13, "K": 13, "L": 6}
        self.page(ws, widths, 11, 260, "Settings", "Your bakery, rates, units, supplies, decorations and pan sizes.")
        ws.column_dimensions["L"].hidden = True
        self.note(ws, "B4:K4", "EXAMPLE VALUES: check and adjust every white cell. Prices, pan amounts and servings "
                  "are typical values, not advice.", height=30, size=10, color=INK, bold=True)
        b = c.BUSINESS if self.sample else {}
        T = c.TARGETS

        def field(r, key, label, value, fmt=None, note="", wide=False, calc=None, align=None):
            self.label(ws[f"B{r}"], label, bold=False)
            cell = ws[f"C{r}"]
            if calc is not None:
                self.calc(cell, fmt, bold=True, align="right", value=calc)
            else:
                self.inp(cell, fmt, align or ("right" if fmt else None), value=value)
            if wide:
                ws.merge_cells(f"C{r}:G{r}")
                for col in "DEFG":
                    self.inp(ws[f"{col}{r}"])
                if note:
                    self.label(ws[f"H{r}"], note, bold=False, color=INK2, size=9, indent=1)
                    ws.merge_cells(f"H{r}:K{r}")
            elif note:
                self.label(ws[f"D{r}"], note, bold=False, color=INK2, size=9, indent=1)
                ws.merge_cells(f"D{r}:K{r}")
            ws.row_dimensions[r].height = 20
            S[key] = f"{SQ}!$C${r}"

        r = 6
        self.kicker(ws, f"B{r}", "Your bakery  ·  shown on the customer quote", rule_to=11)
        r += 1
        for key, label in [("name", "Bakery name"), ("contact", "Contact name"), ("phone", "Phone"), ("email", "Email"),
                           ("website", "Website or social"), ("street", "Street address"), ("city", "City, state, ZIP")]:
            field(r, key, label, b.get(key), wide=True)
            r += 1
        field(r, "currency", "Currency symbol", T["currency"], note="Shown before prices on tiles and the quote.", align="center")
        r += 1
        field(r, "units", "Unit system", T["units"], note="US shows batter and frosting in cups and fondant in oz; "
              "Metric in ml and g. Costs don't change.", align="center")
        r += 1
        field(r, "valid_days", "Quote valid for (days)", T["valid_days"], "0", "Sets the valid-until date on the quote.")
        r += 1
        self.label(ws[f"B{r}"], "Quote terms", bold=False)
        ws.merge_cells(f"C{r}:K{r}")
        self.inp(ws[f"C{r}"], value=c.TERMS)
        ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="top", indent=1)
        for col in "DEFGHIJK":
            self.inp(ws[f"{col}{r}"])
        ws.row_dimensions[r].height = 48
        S["terms"] = f"{SQ}!$C${r}"
        r += 2
        self.kicker(ws, f"B{r}", "Pricing", rule_to=11)
        r += 1
        for key, label, val, fmt, note in [
                ("rate", "Your hourly rate", T["rate"], MONEY, "What your time is worth. Labour is charged at this rate."),
                ("margin", "Target profit margin", T["margin"], PCT, "Share of the price kept as profit, after paying yourself."),
                ("min_serving", "Your minimum price per serving", T["min_serving"], MONEY, "Cakes below this show a red warning."),
                ("deposit", "Deposit to book", T["deposit"], PCT, "Share of the price taken as a deposit."),
                ("round_cake", "Round cake prices up to the nearest", T["round_cake"], MONEY0, "Example: 5 rounds 233.40 up to 235."),
                ("round_dozen", "Round dozen prices to the nearest", T["round_dozen"], MONEY, ""),
                ("round_item", "Round single-item prices to the nearest", T["round_item"], MONEY, "Example: 0.25 rounds 3.10 up to 3.25."),
                ("year", "Year for the dashboard", c.YEAR if self.sample else None, "0", "Monthly revenue chart.")]:
            field(r, key, label, val, fmt, note)
            r += 1
        if not self.sample:
            ws[self.ref("year")] = "=YEAR(TODAY())"
        r += 1
        self.kicker(ws, f"B{r}", "Overhead", rule_to=11)
        r += 1
        field(r, "oh_method", "Charge overhead", T["method"], note="Per hour of work, or a flat amount per order.", align="center")
        r += 1
        for col, t in zip("BC", ["Yearly cost", "Per year"]):
            self.header(ws[f"{col}{r}"], t, align="left" if col == "B" else "center")
        r += 1
        o1 = r
        for i in range(9):
            row = c.OVERHEAD[i] if i < len(c.OVERHEAD) else (None, None)
            self.inp(ws[f"B{r}"], value=row[0])
            self.inp(ws[f"C{r}"], MONEY, value=row[1])
            r += 1
        self.total_row(ws, r, "Overhead per year", "C", f"=SUM(C{o1}:C{r - 1})", MONEY, "BC")
        S["oh_year"] = f"{SQ}!$C${r}"
        self.dv_num(ws, f"C{o1}:C{r - 1}")
        r += 1
        field(r, "hours_year", "Baking hours per year", T["hours_year"], "#,##0", "All the hours you work on orders.")
        r += 1
        field(r, "orders_year", "Orders per year", T["orders_year"], "#,##0", "")
        r += 1
        field(r, "oh_hour", "Overhead per hour", None, MONEY, "Overhead per year ÷ hours.",
              calc=f'=IF(N({S["hours_year"]})=0,0,{S["oh_year"]}/{S["hours_year"]})')
        r += 1
        field(r, "oh_order", "Overhead per order", None, MONEY, "Overhead per year ÷ orders.",
              calc=f'=IF(N({S["orders_year"]})=0,0,{S["oh_year"]}/{S["orders_year"]})')
        r += 2
        self.kicker(ws, f"B{r}", "Delivery", rule_to=11)
        r += 1
        field(r, "mile_rate", "Delivery charge per mile (round trip)", T["mile_rate"], MONEY, "Fuel and wear.")
        r += 1
        field(r, "setup_fee", "Set-up fee (stacking on site)", T["setup_fee"], MONEY, "For 'Delivery + set-up'.")
        r += 2

        def table(r, title, heads, rows, fmts, key_names, note=""):
            self.kicker(ws, f"B{r}", title, rule_to=11)
            r += 1
            for i, t in enumerate(heads):
                col = L(2 + i)
                self.header(ws[f"{col}{r}"], t, align="left" if i == 0 else "center")
            if note:
                ncol = L(2 + len(heads))
                self.label(ws[f"{ncol}{r}"], note, bold=False, color=INK2, size=9, indent=1, wrap=True)
                ws.merge_cells(f"{ncol}{r}:K{r}")
            ws.row_dimensions[r].height = 30
            r += 1
            t1 = r
            for row in rows:
                for i, v in enumerate(row):
                    col = L(2 + i)
                    self.inp(ws[f"{col}{r}"], fmts[i], "center" if fmts[i] in (None, "0.00") and i > 0 else None, value=v)
                r += 1
            for i, k in enumerate(key_names):
                if k:
                    col = L(2 + i)
                    S[k] = f"{SQ}!${col}${t1}:${col}${r - 1}"
            return r + 1, t1

        r, cov1 = table(r, "Coverings", ["Covering", "Frosting factor", "Uses fondant?"], [list(x) for x in c.COVERINGS],
                        [None, "0.00", None], ["cover", "cover_factor", "cover_fondant"],
                        "Frosting factor × the pan table's frosting to cover. Fondant cakes need a thin buttercream coat.")
        self.dv_list(ws, f"D{cov1}:D{cov1 + len(c.COVERINGS) - 1}", f'"Yes,No"')
        r, lv1 = table(r, "Decoration levels", ["Level", "Decorating time multiplier"], [list(x) for x in c.LEVELS],
                       [None, "0.00"], ["levels", "level_mult"], "Multiplies the decorating hours you enter.")
        ex = [list(x) for x in c.EXTRAS] + [[None, None]] * (16 - len(c.EXTRAS))
        r, ex1 = table(r, "Decoration extras", ["Extra", "Cost each"], ex, [None, MONEY], ["extras", "extra_cost"],
                       "Your cost per item. Add your own in the empty rows.")
        sp = [list(x) for x in c.SUPPLIES] + [[None, None]] * (24 - len(c.SUPPLIES))
        r, sp1 = table(r, "Supplies", ["Supply", "Cost each"], sp, [None, MONEY], ["supplies", "supply_cost"],
                       "Boards, boxes, supports, liners, ribbon.")
        for k in ("extra_cost", "supply_cost", "cover_factor", "level_mult"):
            self.dv_num(ws, S[k].split("!")[1].replace("$", ""))

        # ---- units
        un = [list(x) for x in c.UNITS] + [[None, None, None]] * 4
        r, u1 = table(r, "Units", ["Unit", "Type", "Size in g, ml or items"], un, [None, None, "#,##0.0000"],
                      ["units_list", "unit_type", "unit_factor"],
                      "cup = US cup (236.6 ml); metric cup = 250 ml (Australia, Canada). Weight and volume convert through each "
                      "ingredient's grams per cup.")
        self.dv_list(ws, f"C{u1}:C{u1 + len(un) - 1}", f'"weight,volume,count"')
        cup_row = u1 + [x[0] for x in c.UNITS].index("cup")
        oz_row = u1 + [x[0] for x in c.UNITS].index("oz")
        S["cup_ml"] = f"{SQ}!$D${cup_row}"
        S["oz_g"] = f"{SQ}!$D${oz_row}"

        # ---- pans
        self.kicker(ws, f"B{r}", "Pans and servings", rule_to=11)
        r += 1
        self.note(ws, f"B{r}:K{r}", "TYPICAL VALUES, adjust to your recipes and cutting style. Amounts are per 2-inch layer "
                  "(batter, filling) or per 4-inch tier of two layers (frosting, fondant, servings). Party servings ≈ 1.5 × 2 "
                  "in slices; wedding ≈ 1 × 2 in. Add new pan sizes in the empty rows.", tint=PAPER, height=46)
        r += 1
        heads = ["Shape", "Size", "Metric size", "Batter per layer (cups)", "Filling per layer (cups)",
                 "Frosting to cover (cups)", "Fondant to cover (g)", "Party servings", "Wedding servings", "Batter per layer (ml)"]
        for i, t in enumerate(heads):
            self.header(ws[f"{L(2 + i)}{r}"], t, GREEN2 if i == 9 else GREEN, align="left" if i == 0 else "center")
        ws.row_dimensions[r].height = 44
        r += 1
        p1 = r
        rows = list(c.PANS) + [(None,) * 9] * 12
        for row in rows:
            for i, v in enumerate(row):
                col = L(2 + i)
                fmt = [None, None, None, "0.00", "0.00", "0.00", "#,##0", "0", "0"][i]
                self.inp(ws[f"{col}{r}"], fmt, "center" if i in (1, 2) else None, value=v)
            self.calc(ws[f"K{r}"], "#,##0", value=f'=IF(N(E{r})=0,"",E{r}*{S["cup_ml"]})')
            ws[f"L{r}"] = f'=IF(OR(B{r}="",C{r}=""),"",B{r}&"|"&C{r})'
            r += 1
        p2 = r - 1
        col = lambda k: f"{SQ}!${k}${p1}:${k}${p2}"
        S.update(pan_key=col("L"), pan_batter=col("E"), pan_fill=col("F"), pan_frost=col("G"), pan_fondant=col("H"),
                 pan_party=col("I"), pan_wedding=col("J"))
        self.dv_num(ws, f"E{p1}:J{p2}")
        r += 1
        self.kicker(ws, f"B{r}", "Dropdown lists", rule_to=11)
        r += 1
        lists = [("B", "Shapes", c.SHAPES, "shapes"), ("C", "Sizes", c.SIZES, "sizes"), ("D", "Unit systems", c.UNIT_SYSTEMS, "systems"),
                 ("E", "Recipe types", c.RECIPE_TYPES, "rtypes"), ("F", "Serving style", c.SERVING_STYLES, "styles"),
                 ("G", "Pickup or delivery", c.DELIVERY, "delivery"), ("H", "Overhead", c.OVERHEAD_METHODS, "methods"),
                 ("I", "Order type", c.ORDER_TYPES, "otypes"), ("J", "Status", c.STATUSES, "statuses"),
                 ("K", "Yes / No", ["Yes", "No"], "yesno")]
        n = max(len(x[2]) for x in lists)
        for colx, head, items, key in lists:
            self.header(ws[f"{colx}{r}"], head, align="left")
            for i, it in enumerate(items):
                self.sysval(ws[f"{colx}{r + 1 + i}"], it)
            S[key] = f"{SQ}!${colx}${r + 1}:${colx}${r + len(items)}"
        r += n + 1
        self.header(ws[f"B{r}"], "Cake to quote", align="left")
        for i in range(SLOTS):
            self.sysval(ws[f"B{r + 1 + i}"], i + 1)
        S["slots"] = f"{SQ}!$B${r + 1}:$B${r + SLOTS}"
        last = r + SLOTS + 1
        self.dv_list(ws, self.ref("units"), f"={S['systems']}")
        self.dv_list(ws, self.ref("oh_method"), f"={S['methods']}")
        self.dv_list(ws, f"B{p1}:B{p2}", f"={S['shapes']}")
        for k in ("rate", "min_serving", "round_cake", "round_dozen", "round_item", "valid_days", "hours_year", "orders_year",
                  "mile_rate", "setup_fee"):
            self.dv_num(ws, self.ref(k))
        self.dv_num(ws, self.ref("margin"), "decimal", 0, 0.9, "Margin", "Enter 0% to 90%.")
        self.dv_num(ws, self.ref("deposit"), "decimal", 0, 1, "Percent", "Enter 0% to 100%.")
        self.US = f'{S["units"]}="US"'
        ws.freeze_panes = "A4"
        ws.print_area = f"A1:K{last}"
        self.rows["set_last"] = last
        self.rows["pans"] = (p1, p2)
        self.protect(ws)

    # ============================================================ INGREDIENTS
    def build_ingredients(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_ING]
        widths = dict(B=32, C=12, D=10, E=10, F=10, G=10, H=18, I=13, J=12, K=12, L=12, M=40, N=6, O=6)
        self.page(ws, widths, 13, ING_LAST + 1, "Ingredients",
                  "Enter each ingredient once: what you pay and the package size. Costs per gram, ml and item follow.")
        for col in "NO":
            ws.column_dimensions[col].hidden = True
        cur = f'" ("&{S["currency"]}&")"'
        self.note(ws, "B4:M5", "Grams per cup lets a recipe use cups or spoons for an ingredient you buy by weight (and the "
                  "other way round). Grams per item does the same for eggs or lemons. Prices are EXAMPLE VALUES: replace "
                  "them with your own and note the date you checked.", tint=PAPER, height=20)
        heads = [("B", "Ingredient"), ("C", f'="Price"&{cur}'), ("D", "Package size"), ("E", "Package unit"),
                 ("F", "Grams per cup"), ("G", "Grams per item"), ("H", "Supplier"), ("I", "Price checked"),
                 ("J", f'="Cost per g"&{cur}'), ("K", f'="Cost per ml"&{cur}'), ("L", f'="Cost per item"&{cur}'), ("M", "Check")]
        for col, t in heads:
            self.header(ws[f"{col}7"], t, GREEN2 if col in "JKLM" else GREEN, align="left" if col in "BHM" else "center")
        ws.row_dimensions[7].height = 34
        CUP = S["cup_ml"]
        for i in range(ING_N):
            r = ING_FIRST + i
            row = c.INGREDIENTS[i] if i < len(c.INGREDIENTS) else (None,) * 6
            name, price, size, unit, gpc, gpi = row
            self.inp(ws[f"B{r}"], value=name)
            self.inp(ws[f"C{r}"], MONEY, value=price if self.sample else None)
            self.inp(ws[f"D{r}"], "#,##0.##", "right", value=size)
            self.inp(ws[f"E{r}"], align="center", value=unit)
            self.inp(ws[f"F{r}"], "#,##0", value=gpc)
            self.inp(ws[f"G{r}"], "#,##0", value=gpi)
            self.inp(ws[f"H{r}"], value=("Local store" if self.sample and name else None))
            self.inp(ws[f"I{r}"], DATE, "center", value=(c.PRICES_CHECKED if self.sample and name else None))
            ws[f"N{r}"] = f'=IF(E{r}="","",IFERROR(INDEX({S["unit_type"]},MATCH(E{r},{S["units_list"]},0)),"?"))'
            ws[f"O{r}"] = f'=IF(OR(N(D{r})=0,N{r}="",N{r}="?"),"",D{r}*INDEX({S["unit_factor"]},MATCH(E{r},{S["units_list"]},0)))'
            ok = f'OR(B{r}="",C{r}="",O{r}="")'
            self.calc(ws[f"J{r}"], COST4, value=(f'=IF({ok},"",IF(N{r}="weight",C{r}/O{r},IF(AND(N{r}="volume",N(F{r})>0),'
                                                f'C{r}/(O{r}/{CUP}*F{r}),IF(AND(N{r}="count",N(G{r})>0),C{r}/(O{r}*G{r}),""))))'))
            self.calc(ws[f"K{r}"], COST4, value=(f'=IF({ok},"",IF(N{r}="volume",C{r}/O{r},IF(AND(ISNUMBER(J{r}),N(F{r})>0),'
                                                f'J{r}*F{r}/{CUP},"")))'))
            self.calc(ws[f"L{r}"], COST4, value=(f'=IF({ok},"",IF(N{r}="count",C{r}/O{r},IF(AND(ISNUMBER(J{r}),N(G{r})>0),'
                                                f'J{r}*G{r},"")))'))
            self.calc(ws[f"M{r}"], value=(f'=IF(B{r}="","",IF(C{r}="","Add the price you pay",IF(OR(N(D{r})=0,E{r}=""),'
                                         f'"Add the package size and unit",IF(N{r}="?","Unit not in the SETTINGS units table",'
                                         f'IF(AND(N{r}="weight",N(F{r})=0),"OK, by weight only (no grams per cup)",'
                                         f'IF(AND(N{r}="volume",N(F{r})=0),"OK, by volume only (no grams per cup)","OK"))))))'))
            ws[f"M{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
        rr = lambda col: f"{col}{ING_FIRST}:{col}{ING_LAST}"
        self.dv_list(ws, rr("E"), f"={S['units_list']}")
        for col in "CDFG":
            self.dv_num(ws, rr(col))
        v = DataValidation(type="date", operator="between", formula1="36526", formula2="73051", allow_blank=True,
                           showErrorMessage=True, errorTitle="Date", error="Enter a date.")
        ws.add_data_validation(v)
        v.add(rr("I"))
        ws.conditional_formatting.add(rr("M"), FormulaRule(formula=[f'AND($M{ING_FIRST}<>"",LEFT($M{ING_FIRST},2)<>"OK")'],
                                                           font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add(rr("M"), FormulaRule(formula=[f'$M{ING_FIRST}="OK"'], font=Font(color=POS, bold=True)))
        col = lambda k: f"{q(S_ING)}!${k}${ING_FIRST}:${k}${ING_LAST}"
        S.update(ing=col("B"), ing_g=col("J"), ing_ml=col("K"), ing_item=col("L"))
        ws.freeze_panes = f"C{ING_FIRST}"
        ws.auto_filter.ref = f"B7:M{ING_LAST}"
        ws.print_area = f"A1:M{ING_LAST}"
        ws.page_setup.orientation = "landscape"
        self.protect(ws)

    # ============================================================ RECIPES
    def build_recipes(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_REC]
        widths = dict(B=32, C=13, D=12, E=13, F=13, G=14, H=34, I=14)
        self.page(ws, widths, 9, BLK_FIRST + REC_N * REC_BLOCK, "Recipes",
                  "Up to 40 recipes. Each block costs its ingredients; the index at the top sums them up.")
        for k in range(10, 16):
            ws.column_dimensions[L(k)].hidden = True
        ws.column_dimensions["I"].hidden = False
        self.note(ws, "B4:H5", "Fill one block per recipe below the index: name, type, what it yields (cups or ml of batter, "
                  "frosting or filling; grams of fondant; or number of cupcakes or cookies) and up to 16 ingredients in any "
                  "unit. Cakes use batters, fillings and frostings by volume and fondant by weight.", tint=PAPER, height=22)
        cur = f'" ("&{S["currency"]}&")"'
        self.kicker(ws, f"B{IDX_FIRST - 2}", "Recipe index  ·  calculated", rule_to=9)
        heads = [("B", "Recipe"), ("C", "Type"), ("D", f'="Recipe cost"&{cur}'), ("E", "Yield"), ("F", "Yield unit"),
                 ("G", f'="Cost per yield unit"&{cur}'), ("H", "Check"), ("I", "Go to")]
        for col, t in heads:
            self.header(ws[f"{col}{IDX_FIRST - 1}"], t, GREEN2, align="left" if col in "BH" else "center")
        ws.row_dimensions[IDX_FIRST - 1].height = 32
        for k in range(REC_N):
            r0 = BLK_FIRST + k * REC_BLOCK
            self.recipe_block(ws, k, r0)
            i = IDX_FIRST + k
            l1, l2 = r0 + 4, r0 + 4 + REC_LINES - 1
            ws[f"B{i}"] = f'=IF(C{r0 + 1}="","",C{r0 + 1})'
            ws[f"B{i}"].font = font(10, True, INK)
            ws[f"B{i}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            self.link(ws[f"I{i}"], f"Recipe {k + 1}  ›", S_REC, f"B{r0}")
            ws[f"I{i}"].font = font(9, True, GREEN2)
            self.calc(ws[f"C{i}"], align="center", value=f'=IF(B{i}="","",IF(G{r0 + 1}="","",G{r0 + 1}))')
            ws[f"M{i}"] = f'=IF(B{i}="",0,COUNTIFS(B{l1}:B{l2},"<>",C{l1}:C{l2},">0")-COUNT(E{l1}:E{l2}))'
            self.calc(ws[f"D{i}"], MONEY, bold=True,
                      value=f'=IF(OR(B{i}="",M{i}>0,COUNT(E{l1}:E{l2})=0),"",SUM(E{l1}:E{l2}))')
            self.calc(ws[f"E{i}"], "#,##0.##", value=f'=IF(OR(B{i}="",N(C{r0 + 2})=0),"",C{r0 + 2})')
            self.calc(ws[f"F{i}"], align="center", value=f'=IF(OR(B{i}="",D{r0 + 2}=""),"",D{r0 + 2})')
            ws[f"J{i}"] = f'=IF(F{i}="","",IFERROR(INDEX({S["unit_type"]},MATCH(F{i},{S["units_list"]},0)),""))'
            ws[f"K{i}"] = f'=IF(OR(J{i}="",E{i}=""),"",E{i}*INDEX({S["unit_factor"]},MATCH(F{i},{S["units_list"]},0)))'
            ws[f"L{i}"] = f'=IF(OR(D{i}="",K{i}=""),"",D{i}/K{i})'
            self.calc(ws[f"G{i}"], MONEY, value=f'=IF(OR(D{i}="",N(E{i})=0),"",D{i}/E{i})')
            self.calc(ws[f"H{i}"], value=(f'=IF(B{i}="","",IF(M{i}>0,M{i}&" ingredient line(s) to fix",IF(D{i}="","Add ingredients",'
                                         f'IF(OR(E{i}="",F{i}=""),"Add the yield and its unit","OK"))))'))
        ix = lambda col: f"{q(S_REC)}!${col}${IDX_FIRST}:${col}${IDX_FIRST + REC_N - 1}"
        S.update(rec=ix("B"), rec_cost=ix("D"), rec_yield=ix("E"), rec_ytype=ix("J"), rec_ybase=ix("K"), rec_cpb=ix("L"))
        hr = f"H{IDX_FIRST}:H{IDX_FIRST + REC_N - 1}"
        ws.conditional_formatting.add(hr, FormulaRule(formula=[f'AND($H{IDX_FIRST}<>"",$H{IDX_FIRST}<>"OK")'],
                                                      font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add(hr, FormulaRule(formula=[f'$H{IDX_FIRST}="OK"'], font=Font(color=POS, bold=True)))
        ws.freeze_panes = "A4"
        ws.print_area = f"A1:H{BLK_FIRST + REC_N * REC_BLOCK}"
        self.protect(ws)
        self.rows["rec_blocks"] = BLK_FIRST

    def recipe_block(self, ws, k, r0):
        c, S = self.cfg, self.S
        self.kicker(ws, f"B{r0}", f"Recipe {k + 1}", rule_to=8)
        self.label(ws[f"B{r0 + 1}"], "Name", bold=False)
        ws.merge_cells(f"C{r0 + 1}:E{r0 + 1}")
        for col in "CDE":
            self.inp(ws[f"{col}{r0 + 1}"])
        self.label(ws[f"F{r0 + 1}"], "Type", bold=False, indent=1)
        self.inp(ws[f"G{r0 + 1}"], align="center")
        self.dv_list(ws, f"G{r0 + 1}", f"={S['rtypes']}")
        self.label(ws[f"B{r0 + 2}"], "Yield (what one batch makes)", bold=False)
        self.inp(ws[f"C{r0 + 2}"], "#,##0.##", "right")
        self.inp(ws[f"D{r0 + 2}"], align="center")
        self.dv_list(ws, f"D{r0 + 2}", f"={S['units_list']}")
        self.dv_num(ws, f"C{r0 + 2}")
        self.label(ws[f"F{r0 + 2}"], "Notes", bold=False, indent=1)
        ws.merge_cells(f"G{r0 + 2}:H{r0 + 2}")
        self.inp(ws[f"G{r0 + 2}"])
        self.inp(ws[f"H{r0 + 2}"])
        cur = f'" ("&{S["currency"]}&")"'
        for col, t in (("B", "Ingredient"), ("C", "Quantity"), ("D", "Unit"), ("E", f'="Cost"&{cur}'), ("F", "Check")):
            self.header(ws[f"{col}{r0 + 3}"], t, GREEN2 if col in "EF" else GREEN, align="left" if col in "BF" else "center")
        ws.merge_cells(f"F{r0 + 3}:H{r0 + 3}")
        l1 = r0 + 4
        for j in range(REC_LINES):
            r = l1 + j
            self.inp(ws[f"B{r}"])
            self.inp(ws[f"C{r}"], "#,##0.###", "right")
            self.inp(ws[f"D{r}"], align="center")
            on = f'AND(B{r}<>"",N(C{r})>0)'
            ws[f"J{r}"] = f'=IF(NOT({on}),"",IFERROR(INDEX({S["unit_type"]},MATCH(D{r},{S["units_list"]},0)),"?"))'
            ws[f"K{r}"] = f'=IF(OR(J{r}="",J{r}="?"),"",C{r}*INDEX({S["unit_factor"]},MATCH(D{r},{S["units_list"]},0)))'
            ws[f"L{r}"] = f'=IF(NOT({on}),"",IFERROR(MATCH(B{r},{S["ing"]},0),"none"))'
            ws[f"M{r}"] = (f'=IF(OR(K{r}="",NOT(ISNUMBER(L{r}))),"",IF(J{r}="weight",INDEX({S["ing_g"]},L{r}),'
                           f'IF(J{r}="volume",INDEX({S["ing_ml"]},L{r}),INDEX({S["ing_item"]},L{r}))))')
            self.calc(ws[f"E{r}"], MONEY, align="right",
                      value=f'=IF(NOT({on}),"",IF(ISNUMBER(M{r}),K{r}*M{r},"–"))')
            ws.merge_cells(f"F{r}:H{r}")
            self.calc(ws[f"F{r}"], value=(f'=IF(NOT({on}),"",IF(L{r}="none","Not in INGREDIENTS",IF(D{r}="","Pick a unit",'
                                         f'IF(J{r}="?","Unknown unit",IF(ISNUMBER(M{r}),"","No price, or add grams per "'
                                         f'&IF(J{r}="count","item","cup")&" on INGREDIENTS to convert "&D{r})))))'))
            ws[f"F{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
            self.calc(ws[f"G{r}"])
            self.calc(ws[f"H{r}"])
        l2 = l1 + REC_LINES - 1
        self.dv_list(ws, f"B{l1}:B{l2}", f"={S['ing']}")
        self.dv_list(ws, f"D{l1}:D{l2}", f"={S['units_list']}")
        self.dv_num(ws, f"C{l1}:C{l2}")
        ws.conditional_formatting.add(f"F{l1}:F{l2}", FormulaRule(formula=[f'$F{l1}<>""'], font=Font(color=NEG, bold=True),
                                                                fill=fill(NEG_TINT)))
        tr = l2 + 1
        ws[f"B{tr}"] = "Recipe cost"
        ws[f"E{tr}"] = f"={q(S_REC)}!D{IDX_FIRST + k}"
        ws[f"F{tr}"] = (f'=IF({q(S_REC)}!G{IDX_FIRST + k}="","",'
                        f'{self.cur(f"{q(S_REC)}!G{IDX_FIRST + k}")}&" per "&{q(S_REC)}!F{IDX_FIRST + k})')
        for col in "BCDEFGH":
            x = ws[f"{col}{tr}"]
            x.fill, x.font = fill(GREEN), font(10, True, PAPER if col == "B" else BRASS)
            x.number_format = MONEY
            x.alignment = Alignment(horizontal="left" if col in "BF" else None, vertical="center", indent=1 if col in "BF" else 0)
        ws.merge_cells(f"F{tr}:H{tr}")
        ws.row_dimensions[tr].height = 22
        if self.sample and k < len(c.RECIPES):
            name, rtype, yq, yu, lines = c.RECIPES[k]
            ws[f"C{r0 + 1}"], ws[f"G{r0 + 1}"], ws[f"C{r0 + 2}"], ws[f"D{r0 + 2}"] = name, rtype, yq, yu
            for j, (ing, qty, unit) in enumerate(lines):
                ws[f"B{l1 + j}"], ws[f"C{l1 + j}"], ws[f"D{l1 + j}"] = ing, qty, unit

    # ============================================================ CAKE BUILDER
    def rec_cost(self, ml_expr, recipe_cell, want="volume"):
        """cost of `ml_expr` ml (or g) of a recipe; 'x' when the recipe is missing, unpriced or the wrong kind."""
        S = self.S
        m = f"MATCH({recipe_cell},{S['rec']},0)"
        return (f'IF({recipe_cell}="","x",IFERROR(IF(INDEX({S["rec_ytype"]},{m})="{want}",'
                f'{ml_expr}*INDEX({S["rec_cpb"]},{m}),"x"),"x"))')

    def build_cake(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_CAKE]
        widths = dict(B=10, C=11, D=10, E=8, F=22, G=22, H=22, I=13, J=11, K=11, L=11, M=11, N=12, O=11)
        last = SLOT_FIRST + SLOTS * SLOT_SIZE
        self.page(ws, widths, 15, last, "Cake builder", "Price up to three cakes. Each tier knows its pan, batter, servings and cost.")
        for k in range(17, 33):
            ws.column_dimensions[L(k)].hidden = True
        ws.merge_cells("B4:O5")
        ws["B4"] = ("Tier 1 is the bottom tier. Pick a shape, size and layers (2-inch layers), then the recipes. CUSTOMER QUOTE "
                    "shows the cake you choose there (1, 2 or 3).")
        ws["B4"].font = font(9, False, INK2)
        ws["B4"].alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        self.slot_rows = []
        for i in range(SLOTS):
            R = SLOT_FIRST + i * SLOT_SIZE
            self.slot_rows.append(R)
            self.cake_slot(ws, i, R)
        # jump links in the note row
        ws.row_dimensions[4].height = 18
        ws.row_dimensions[5].height = 18
        ws.freeze_panes = "A4"
        ws.print_area = f"A1:O{last}"
        ws.page_setup.orientation = "landscape"
        self.protect(ws)

    def cake_slot(self, ws, i, R):
        c, S = self.cfg, self.S
        d = c.CAKES[i] if self.sample and i < len(c.CAKES) else None
        US = self.US
        disp = f"IF({US},{S['cup_ml']},1)"
        self.kicker(ws, f"B{R}", f"Cake {i + 1}", rule_to=15)
        A = {}

        def left(r, key, label, fmt=None, align=None):
            ws.merge_cells(f"B{r}:C{r}")
            self.label(ws[f"B{r}"], label, bold=False)
            ws.merge_cells(f"D{r}:G{r}")
            for col in "DEFG":
                self.inp(ws[f"{col}{r}"], fmt, align)
            A[key] = f"$D${r}"
            ws.row_dimensions[r].height = 20

        def right(r, key, label, fmt=None, wide=True, note=""):
            self.label(ws[f"H{r}"], label, bold=False, indent=1)
            if wide:
                ws.merge_cells(f"I{r}:O{r}")
                for col in "IJKLMNO":
                    self.inp(ws[f"{col}{r}"], fmt)
            else:
                self.inp(ws[f"I{r}"], fmt, "right" if fmt else None)
                if note:
                    ws.merge_cells(f"J{r}:O{r}")
                    self.label(ws[f"J{r}"], note, bold=False, color=INK2, size=9, indent=1)
            A[key] = f"$I${r}"

        left(R + 1, "customer", "Customer")
        left(R + 2, "event", "Event date", DATE, "left")
        ws[f"D{R + 2}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        left(R + 3, "occasion", "Occasion")
        left(R + 4, "style", "Serving style")
        left(R + 5, "delivery", "Pickup or delivery")
        right(R + 1, "miles", "Delivery miles", "0", wide=False, note="Round trip, at the SETTINGS rate per mile.")
        right(R + 2, "fondant", "Fondant recipe")
        right(R + 3, "design", "Design notes")
        right(R + 4, "allergens", "Allergen notes")
        right(R + 5, "own", "Your own price", MONEY, wide=False, note="Optional. Blank = suggested price.")
        self.dv_list(ws, A["style"].replace("$", ""), f"={S['styles']}")
        self.dv_list(ws, A["delivery"].replace("$", ""), f"={S['delivery']}")
        self.dv_list(ws, A["fondant"].replace("$", ""), f"={S['rec']}")
        self.dv_num(ws, A["miles"].replace("$", ""))
        self.dv_num(ws, A["own"].replace("$", ""))
        v = DataValidation(type="date", operator="between", formula1="36526", formula2="73051", allow_blank=True,
                           showErrorMessage=True, errorTitle="Date", error="Enter a date.")
        ws.add_data_validation(v)
        v.add(A["event"].replace("$", ""))

        # ---- tiers
        tk = R + 7
        self.kicker(ws, f"B{tk}", "Tiers  ·  tier 1 is the bottom", rule_to=15)
        th = tk + 1
        heads = [("B", "Tier"), ("C", "Shape"), ("D", "Size"), ("E", "Layers"), ("F", "Batter recipe"),
                 ("G", "Filling recipe"), ("H", "Frosting recipe"), ("I", "Covering"),
                 ("J", f'="Batter ("&IF({US},"cups","ml")&")"'), ("K", f'="Filling ("&IF({US},"cups","ml")&")"'),
                 ("L", f'="Frosting ("&IF({US},"cups","ml")&")"'), ("M", f'="Fondant ("&IF({US},"oz","g")&")"'),
                 ("N", f'="Ingredients ("&{S["currency"]}&")"'), ("O", "Servings")]
        for col, t in heads:
            self.header(ws[f"{col}{th}"], t, GREEN2 if col in "JKLMNO" else GREEN, align="left" if col in "BFGH" else "center")
        ws.row_dimensions[th].height = 30
        t1 = th + 1
        style = A["style"]
        for k in range(TIERS):
            r = t1 + k
            ws[f"B{r}"] = f"{k + 1}" + (" (base)" if k == 0 else "")
            ws[f"B{r}"].font = font(10, True, INK)
            ws[f"B{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            for col in "CDEFGHI":
                self.inp(ws[f"{col}{r}"], "0" if col == "E" else None, "center" if col in "CDEI" else None)
            # helpers Q..AE
            ws[f"Q{r}"] = f'=IF(OR(C{r}="",D{r}=""),"",C{r}&"|"&D{r})'
            ws[f"R{r}"] = f'=IF(Q{r}="","",IFERROR(MATCH(Q{r},{S["pan_key"]},0),"none"))'
            ws[f"S{r}"] = f'=IF(OR(NOT(ISNUMBER(R{r})),N(E{r})=0),0,1)'
            cov = f'IF(I{r}="","{c.COVERINGS[0][0]}",I{r})'
            ws[f"T{r}"] = f'=IF(S{r}=0,0,IFERROR(INDEX({S["cover_factor"]},MATCH({cov},{S["cover"]},0)),1))'
            ws[f"U{r}"] = f'=IF(S{r}=0,0,IF(IFERROR(INDEX({S["cover_fondant"]},MATCH({cov},{S["cover"]},0)),"No")="Yes",1,0))'
            ws[f"V{r}"] = f'=IF(S{r}=0,0,E{r}*N(INDEX({S["pan_batter"]},R{r}))*{S["cup_ml"]})'
            ws[f"W{r}"] = f'=IF(OR(S{r}=0,G{r}=""),0,(E{r}-1)*N(INDEX({S["pan_fill"]},R{r}))*{S["cup_ml"]})'
            ws[f"X{r}"] = f'=IF(OR(S{r}=0,H{r}=""),0,N(INDEX({S["pan_frost"]},R{r}))*T{r}*E{r}/2*{S["cup_ml"]})'
            ws[f"Y{r}"] = f'=IF(S{r}=0,0,U{r}*N(INDEX({S["pan_fondant"]},R{r}))*E{r}/2)'
            ws[f"Z{r}"] = (f'=IF(S{r}=0,0,ROUNDDOWN(IF({style}="Wedding",N(INDEX({S["pan_wedding"]},R{r})),'
                           f'N(INDEX({S["pan_party"]},R{r})))*E{r}/2,0))')
            ws[f"AA{r}"] = f'=IF(V{r}=0,0,{self.rec_cost(f"V{r}", f"F{r}")})'
            ws[f"AB{r}"] = f'=IF(W{r}=0,0,{self.rec_cost(f"W{r}", f"G{r}")})'
            ws[f"AC{r}"] = f'=IF(X{r}=0,0,{self.rec_cost(f"X{r}", f"H{r}")})'
            ws[f"AD{r}"] = f'=IF(Y{r}=0,0,{self.rec_cost(f"Y{r}", A["fondant"], "weight")})'
            ws[f"AE{r}"] = f'=IF(R{r}="none",1,0)+IF(S{r}=0,0,COUNTIF(AA{r}:AD{r},"x"))'
            self.calc(ws[f"J{r}"], QTY, value=f'=IF(S{r}=0,"",V{r}/{disp})')
            self.calc(ws[f"K{r}"], QTY, value=f'=IF(OR(S{r}=0,W{r}=0),"",W{r}/{disp})')
            self.calc(ws[f"L{r}"], QTY, value=f'=IF(OR(S{r}=0,X{r}=0),"",X{r}/{disp})')
            self.calc(ws[f"M{r}"], "#,##0", value=f'=IF(OR(S{r}=0,Y{r}=0),"",Y{r}/IF({US},{S["oz_g"]},1))')
            self.calc(ws[f"N{r}"], MONEY, bold=True, align="right",
                      value=f'=IF(R{r}="none","no such pan",IF(S{r}=0,"",IF(AE{r}>0,"check",SUM(AA{r}:AD{r}))))')
            self.calc(ws[f"O{r}"], "0", align="center", value=f'=IF(S{r}=0,"",Z{r})')
        t2 = t1 + TIERS - 1
        self.dv_list(ws, f"C{t1}:C{t2}", f"={S['shapes']}")
        self.dv_list(ws, f"D{t1}:D{t2}", f"={S['sizes']}")
        self.dv_num(ws, f"E{t1}:E{t2}", "whole", 1, 8, "Layers", "Enter 1 to 8 layers (2 inches each).")
        for col in "FGH":
            self.dv_list(ws, f"{col}{t1}:{col}{t2}", f"={S['rec']}")
        self.dv_list(ws, f"I{t1}:I{t2}", f"={S['cover']}")
        ws.conditional_formatting.add(f"N{t1}:N{t2}", FormulaRule(formula=[f'AND(ISTEXT($N{t1}),$N{t1}<>"")'], font=Font(color=NEG, bold=True),
                                                                 fill=fill(NEG_TINT)))
        tr = t2 + 1
        ws.merge_cells(f"B{tr}:I{tr}")
        ws[f"B{tr}"] = "Whole cake"
        for col, f, fmt in (("J", f'=IF(SUM(J{t1}:J{t2})=0,"",SUM(J{t1}:J{t2}))', QTY), ("K", f'=IF(SUM(K{t1}:K{t2})=0,"",SUM(K{t1}:K{t2}))', QTY),
                            ("L", f'=IF(SUM(L{t1}:L{t2})=0,"",SUM(L{t1}:L{t2}))', QTY), ("M", f'=IF(SUM(M{t1}:M{t2})=0,"",SUM(M{t1}:M{t2}))', "#,##0"),
                            ("N", f"=SUM(N{t1}:N{t2})", MONEY), ("O", f"=SUM(O{t1}:O{t2})", "0")):
            ws[f"{col}{tr}"] = f
            ws[f"{col}{tr}"].number_format = fmt
        for col in "BCDEFGHIJKLMNO":
            x = ws[f"{col}{tr}"]
            x.fill, x.font = fill(GREEN), font(10, True, PAPER if col == "B" else BRASS)
            x.alignment = Alignment(horizontal="left" if col == "B" else ("center" if col == "O" else None), vertical="center",
                                    indent=1 if col == "B" else 0)
        ws.row_dimensions[tr].height = 22
        ws[f"Q{R + 1}"] = f"=SUM(S{t1}:S{t2})"
        ws[f"Q{R + 2}"] = f"=SUM(AE{t1}:AE{t2})"
        n_t, probs = f"$Q${R + 1}", f"$Q${R + 2}"

        # ---- decorations, supplies, labour
        dk = tr + 2
        self.kicker(ws, f"B{dk}", "Decoration and extras", rule_to=7)
        self.kicker(ws, f"H{dk}", "Labour", rule_to=15)
        ws.merge_cells(f"B{dk + 1}:C{dk + 1}")
        self.label(ws[f"B{dk + 1}"], "Decoration level", bold=False)
        ws.merge_cells(f"D{dk + 1}:E{dk + 1}")
        self.inp(ws[f"D{dk + 1}"], align="center")
        self.inp(ws[f"E{dk + 1}"])
        A["level"] = f"$D${dk + 1}"
        self.dv_list(ws, f"D{dk + 1}", f"={S['levels']}")
        mult = f'IFERROR(INDEX({S["level_mult"]},MATCH({A["level"]},{S["levels"]},0)),1)'
        ws.merge_cells(f"F{dk + 1}:G{dk + 1}")
        ws[f"F{dk + 1}"] = f'="× "&FIXED({mult},2)&" on decorating hours"'
        ws[f"F{dk + 1}"].font = font(9, False, INK2)
        ws[f"F{dk + 1}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)

        def item_table(r, title, names, costs, n):
            ws.merge_cells(f"B{r}:E{r}")
            self.header(ws[f"B{r}"], title, align="left")
            self.header(ws[f"F{r}"], "Quantity")
            self.header(ws[f"G{r}"], f'="Cost ("&{S["currency"]}&")"', GREEN2)
            for col in "CDE":
                ws[f"{col}{r}"].fill = fill(GREEN)
            ws.row_dimensions[r].height = 24
            x1 = r + 1
            for j in range(n):
                rr = x1 + j
                ws.merge_cells(f"B{rr}:E{rr}")
                for col in "BCDE":
                    self.inp(ws[f"{col}{rr}"])
                self.inp(ws[f"F{rr}"], "#,##0.##", "center")
                self.calc(ws[f"G{rr}"], MONEY, align="right",
                          value=f'=IF(OR(B{rr}="",N(F{rr})=0),"",IFERROR(F{rr}*INDEX({costs},MATCH(B{rr},{names},0)),"not in list"))')
            self.dv_list(ws, f"B{x1}:B{x1 + n - 1}", f"={names}")
            self.dv_num(ws, f"F{x1}:F{x1 + n - 1}")
            return x1, x1 + n - 1

        e1, e2 = item_table(dk + 2, "Extra", S["extras"], S["extra_cost"], EXTRA_N)
        s1, s2 = item_table(e2 + 2, "Supply", S["supplies"], S["supply_cost"], SUPPLY_N)
        # labour on the right
        lh = dk + 1
        self.header(ws[f"H{lh}"], "Task", align="left")
        self.header(ws[f"I{lh}"], "Hours")
        self.header(ws[f"J{lh}"], "Counted", GREEN2)
        for j, task in enumerate(c.TASKS):
            rr = lh + 1 + j
            self.label(ws[f"H{rr}"], task, bold=False, indent=1)
            self.inp(ws[f"I{rr}"], "0.00", "center")
            m = mult if task == c.DECOR_TASK else "1"
            self.calc(ws[f"J{rr}"], "0.00", align="center", value=f'=IF(I{rr}="","",I{rr}*{m})')
            if task == c.DECOR_TASK:
                ws.merge_cells(f"K{rr}:O{rr}")
                ws[f"K{rr}"] = "× the decoration level multiplier"
                ws[f"K{rr}"].font = font(9, False, INK2)
                ws[f"K{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            ws.row_dimensions[rr].height = 20
        h1, h2 = lh + 1, lh + len(c.TASKS)
        self.dv_num(ws, f"I{h1}:I{h2}", "decimal", 0, 200)
        ht = h2 + 1
        ws[f"H{ht}"] = "Total hours"
        ws[f"J{ht}"] = f"=SUM(J{h1}:J{h2})"
        for col in "HIJ":
            x = ws[f"{col}{ht}"]
            x.fill, x.font = fill(GREEN), font(10, True, PAPER if col == "H" else BRASS)
            x.number_format = "0.00"
            x.alignment = Alignment(horizontal="left" if col == "H" else "center", vertical="center", indent=1 if col == "H" else 0)
        hours = f"$J${ht}"

        # ---- price
        pk = s2 + 2
        self.kicker(ws, f"B{pk}", "Price", rule_to=15)
        rate, m = S["rate"], f"N({S['margin']})"
        cost_rows = [("ing", "Ingredients (batter, filling, frosting, fondant)", f"=IF({n_t}=0,0,SUMIF(N{t1}:N{t2},\">0\"))"),
                     ("dec", "Decoration extras", f"=SUM(G{e1}:G{e2})"),
                     ("sup", "Supplies", f"=SUM(G{s1}:G{s2})"),
                     ("lab", "Labour (hours × your rate)", f"={hours}*N({rate})"),
                     ("oh", "Overhead", f'=IF({n_t}=0,0,IF({S["oh_method"]}="Per order",{S["oh_order"]},{hours}*{S["oh_hour"]}))'),
                     ("deliv", "Delivery", (f'=IF(LEFT({A["delivery"]},8)="Delivery",N({A["miles"]})*N({S["mile_rate"]})'
                                            f'+IF({A["delivery"]}="Delivery + set-up",N({S["setup_fee"]}),0),0)'))]
        br = pk + 7
        for j, (key, lab, f) in enumerate(cost_rows):
            rr = br + j
            ws.merge_cells(f"B{rr}:F{rr}")
            self.label(ws[f"B{rr}"], lab, bold=False)
            self.calc(ws[f"G{rr}"], MONEY, align="right", value=f)
            A[key] = f"$G${rr}"
            ws.row_dimensions[rr].height = 20
        ct = br + len(cost_rows)
        ws.merge_cells(f"B{ct}:F{ct}")
        ws[f"B{ct}"] = "Total cost"
        ws[f"G{ct}"] = f"=IF({n_t}=0,0,SUM(G{br}:G{ct - 1}))"
        for col in "BCDEFG":
            x = ws[f"{col}{ct}"]
            x.fill, x.font = fill(GREEN), font(10, True, PAPER if col == "B" else BRASS)
            x.number_format = MONEY
            x.alignment = Alignment(horizontal="left" if col == "B" else None, vertical="center", indent=1 if col == "B" else 0)
        A["cost"] = f"$G${ct}"
        cost = A["cost"]
        inc = f"N({S['round_cake']})"
        raw = f"{cost}/(1-{m})"
        prow = [("suggested", "Suggested price (target margin, rounded up)",
                 f'=IF({n_t}=0,"",IF({inc}>0,ROUNDUP(ROUND({raw},6)/{inc},0)*{inc},ROUND({raw},2)))', MONEY, ""),
                ("price", "Price used", f'=IF({n_t}=0,"",IF(N({A["own"]})>0,{A["own"]},$L${br}))', MONEY, ""),
                ("servings", "Servings", f'=IF({n_t}=0,"",O{tr})', "0", ""),
                ("per_serving", "Price per serving", "=0", MONEY, ""),
                ("profit", "Profit (after paying yourself)", "=0", MONEY, ""),
                ("hourly", "Your hourly earnings (labour + profit ÷ hours)", "=0", MONEY, ""),
                ("deposit", "Deposit to book", "=0", MONEY, ""),
                ("balance", "Balance due", "=0", MONEY, "")]
        for j, (key, lab, f, fmt, note) in enumerate(prow):
            rr = br + j
            ws.merge_cells(f"H{rr}:K{rr}")
            self.label(ws[f"H{rr}"], lab, bold=key in ("price", "per_serving"), indent=1)
            self.calc(ws[f"L{rr}"], fmt, bold=key in ("price", "per_serving"), align="right", value=f)
            A[key] = f"$L${rr}"
        P = A["price"]
        ws[A["price"].replace("$", "")] = f'=IF({n_t}=0,"",IF(N({A["own"]})>0,{A["own"]},{A["suggested"]}))'
        ws[A["per_serving"].replace("$", "")] = f'=IF(OR({P}="",N({A["servings"]})=0),"",{P}/{A["servings"]})'
        ws[A["profit"].replace("$", "")] = f'=IF({P}="","",{P}-{cost})'
        ws[A["hourly"].replace("$", "")] = f'=IF(OR({P}="",N({hours})=0),"",({P}-({cost}-{A["lab"]}))/{hours})'
        ws[A["deposit"].replace("$", "")] = f'=IF({P}="","",ROUND({P}*N({S["deposit"]}),2))'
        ws[A["balance"].replace("$", "")] = f'=IF({P}="","",{P}-{A["deposit"]})'
        notes = {"price": f'=IF({P}="","",IF(N({A["own"]})>0,"Your own price","Suggested"))',
                 "per_serving": f'=IF({A["per_serving"]}="","","Minimum "&{self.cur(S["min_serving"])})',
                 "hourly": f'=IF({A["hourly"]}="","","Your rate "&{self.cur(rate)})',
                 "deposit": f'=IF({P}="","",FIXED(100*N({S["deposit"]}),0)&"% of the price")'}
        for key, f in notes.items():
            rr = int(A[key].split("$")[-1])
            ws.merge_cells(f"M{rr}:O{rr}")
            ws[f"M{rr}"] = f
            ws[f"M{rr}"].font = font(9, False, INK2)
            ws[f"M{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
        # tiles and warning
        PS, HR = A["per_serving"], A["hourly"]
        self.tile(ws, pk + 1, 2, 5, "PRICE", f'=IF({P}="","–",{self.cur(P)})', "General", size=20)
        self.tile(ws, pk + 1, 6, 7, "PRICE PER SERVING", f'=IF({PS}="","–",{self.cur(PS)})', "General", size=20)
        self.tile(ws, pk + 1, 8, 11, "YOUR HOURLY EARNINGS", f'=IF({HR}="","–",{self.cur(HR)})', "General", size=20)
        self.tile(ws, pk + 1, 12, 15, "SERVINGS", f'=IF({A["servings"]}="","–",{A["servings"]})', "General", size=20)
        wr = pk + 4
        ws.merge_cells(f"B{wr}:O{wr + 1}")
        w = ws[f"B{wr}"]
        w.value = (f'=IF({n_t}=0,"Add at least one tier (shape, size and layers) to price this cake.",'
                   f'IF({probs}>0,"CHECK THE TIERS: a pan size isn\'t in the SETTINGS pan table, or a recipe is missing, has no cost, '
                   f'or has the wrong yield unit (batter, filling and frosting need a volume yield; fondant a weight).",'
                   f'IF(N({PS})<N({S["min_serving"]}),"BELOW YOUR MINIMUM: "&{self.cur(PS)}&" per serving, under your minimum of "&{self.cur(S["min_serving"])}&".",'
                   f'IF(N({HR})<N({rate}),"LOW HOURLY EARNINGS: "&{self.cur(HR)}&" an hour, below your rate of "&{self.cur(rate)}&".",'
                   f'"Priced for profit: "&{self.cur(PS)}&" per serving and "&{self.cur(HR)}&" an hour for your time."))))')
        w.font = font(10, True, POS)
        w.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        for rr in (wr, wr + 1):
            for col in "BCDEFGHIJKLMNO":
                ws[f"{col}{rr}"].fill = fill(POS_TINT)
            ws.row_dimensions[rr].height = 20
        rng = f"B{wr}:O{wr + 1}"
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'OR(LEFT($B${wr},5)="BELOW",LEFT($B${wr},3)="LOW",LEFT($B${wr},5)="CHECK")'],
                                                       font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'LEFT($B${wr},3)="Add"'], font=Font(color=INK2, bold=True),
                                                       fill=fill(BRASS_TINT)))
        A.update(n=n_t, probs=probs, t1=t1, e1=e1, s1=s1, h1=h1, hours=hours, warning=f"$B${wr}", tier_total=tr, pk=pk)
        self.A = getattr(self, "A", [])
        self.A.append(A)
        # sample inputs
        if d:
            put = lambda k, v: ws.__setitem__(A[k].replace("$", ""), v)
            for k in ("customer", "event", "occasion", "style", "delivery", "miles", "fondant", "design", "allergens", "own"):
                put(k, d[k])
            for k, tier in enumerate(d["tiers"]):
                for col, val in zip("CDEFGHI", tier):
                    ws[f"{col}{t1 + k}"] = val
            put("level", d["level"])
            for j, (n_, qn) in enumerate(d["extras"]):
                ws[f"B{e1 + j}"], ws[f"F{e1 + j}"] = n_, qn
            for j, (n_, qn) in enumerate(d["supplies"]):
                ws[f"B{s1 + j}"], ws[f"F{s1 + j}"] = n_, qn
            for j, hrs in enumerate(d["hours"]):
                ws[f"I{h1 + j}"] = hrs
        else:
            ws[A["style"].replace("$", "")] = "Party"
            ws[A["delivery"].replace("$", "")] = "Pickup"
            ws[A["level"].replace("$", "")] = "Simple"

    # ============================================================ BATCH PRICING
    def build_batch(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_BATCH]
        widths = dict(B=46, C=22, D=22, E=22, F=22, G=30)
        self.page(ws, widths, 7, 60, "Batch pricing", "Cupcakes, cookies, cake pops, brownies: cost and price per item, half dozen and dozen.")
        for k in range(9, 13):
            ws.column_dimensions[L(k)].hidden = True
        cols = [L(3 + i) for i in range(BATCH_N)]
        self.kicker(ws, "B4", "What you're making", rule_to=7)
        self.header(ws["B5"], "", align="left")
        for i, col in enumerate(cols):
            self.header(ws[f"{col}5"], f"Product {i + 1}")
        ws.row_dimensions[5].height = 24
        rows = [("name", "Product", None, "text"), ("recipe", "Recipe (batter or dough)", None, "rec"),
                ("per_batch_rec", "Items per batch (from the recipe yield)", "0", "calc"),
                ("per_batch_own", "Items per batch (if the recipe yield isn't in items)", "0", "num"),
                ("batches", "Number of batches", "0.##", "num"),
                ("frost", "Frosting or icing recipe", None, "rec"),
                ("frost_qty", "Frosting per item (amount)", "0.##", "num"),
                ("frost_unit", "Frosting unit", None, "unit"),
                ("level", "Decoration level", None, "level"),
                ("extra_item", "Decoration extras per item (cost)", MONEY, "num"),
                ("pack_dozen", "Packaging per dozen (boxes, liners, bags)", MONEY, "num"),
                ("hours", "Baking and other hours (whole order)", "0.00", "num"),
                ("dec_hours", "Decorating hours (whole order)", "0.00", "num")]
        B = {}
        r = 6
        for key, lab, fmt, kind in rows:
            self.label(ws[f"B{r}"], lab, bold=False)
            for col in cols:
                cell = ws[f"{col}{r}"]
                if kind == "calc":
                    rec = f"{col}{B['recipe']}"
                    m = f"MATCH({rec},{S['rec']},0)"
                    self.calc(cell, fmt, align="center",
                              value=f'=IF({rec}="","",IFERROR(IF(INDEX({S["rec_ytype"]},{m})="count",INDEX({S["rec_ybase"]},{m}),"–"),"–"))')
                else:
                    self.inp(cell, fmt, "center" if kind != "text" else None)
            B[key] = r
            ws.row_dimensions[r].height = 20
            r += 1
        rr = lambda k: f"{cols[0]}{B[k]}:{cols[-1]}{B[k]}"
        self.dv_list(ws, rr("recipe"), f"={S['rec']}")
        self.dv_list(ws, rr("frost"), f"={S['rec']}")
        self.dv_list(ws, rr("frost_unit"), f"={S['units_list']}")
        self.dv_list(ws, rr("level"), f"={S['levels']}")
        for k in ("per_batch_own", "batches", "frost_qty", "extra_item", "pack_dozen", "hours", "dec_hours"):
            self.dv_num(ws, rr(k))
        r += 1
        self.kicker(ws, f"B{r}", "Cost", rule_to=7)
        r += 1
        m_ = f"N({S['margin']})"
        out = [("items", "Items made", "0"), ("c_rec", "Recipe cost", MONEY), ("c_frost", "Frosting or icing", MONEY),
               ("c_dec", "Decoration extras", MONEY), ("c_pack", "Packaging", MONEY), ("hrs", "Hours (decorating × level)", "0.00"),
               ("c_lab", "Labour", MONEY), ("c_oh", "Overhead", MONEY), ("cost", "Total cost", MONEY),
               ("cost_item", "Cost per item", MONEY)]
        for key, lab, fmt in out:
            self.label(ws[f"B{r}"], lab, bold=key in ("cost", "cost_item"))
            B[key] = r
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Price", rule_to=7)
        r += 1
        for key, lab, fmt in [("p_item", "Price per item", MONEY), ("p_half", "Price per half dozen", MONEY),
                              ("p_dozen", "Price per dozen", MONEY), ("profit_dozen", "Profit per dozen", MONEY),
                              ("hourly", "Your hourly earnings", MONEY), ("check", "Check", None)]:
            self.label(ws[f"B{r}"], lab, bold=key in ("p_item", "p_dozen"))
            B[key] = r
            r += 1
        out += [("p_item", "", MONEY), ("p_half", "", MONEY), ("p_dozen", "", MONEY), ("profit_dozen", "", MONEY),
                ("hourly", "", MONEY), ("check", "", None)]
        for col in cols:
            g = lambda k: f"{col}{B[k]}"
            on = f'AND({g("recipe")}<>"",N({g("batches")})>0)'
            rec_m = f"MATCH({g('recipe')},{S['rec']},0)"
            fr_m = f"MATCH({g('frost')},{S['rec']},0)"
            per = f'IF(N({g("per_batch_own")})>0,{g("per_batch_own")},N({g("per_batch_rec")}))'
            utype = f'IFERROR(INDEX({S["unit_type"]},MATCH({g("frost_unit")},{S["units_list"]},0)),"")'
            ufac = f'INDEX({S["unit_factor"]},MATCH({g("frost_unit")},{S["units_list"]},0))'
            lvl = f'IFERROR(INDEX({S["level_mult"]},MATCH({g("level")},{S["levels"]},0)),1)'
            f = {
                "items": f'=IF(NOT({on}),"",{g("batches")}*{per})',
                "c_rec": f'=IF(NOT({on}),"",IFERROR({g("batches")}*INDEX({S["rec_cost"]},{rec_m}),"–"))',
                "c_frost": (f'=IF(OR(NOT({on}),{g("frost")}="",N({g("frost_qty")})=0),IF({on},0,""),IFERROR(IF(INDEX({S["rec_ytype"]},{fr_m})={utype},'
                            f'{g("items")}*{g("frost_qty")}*{ufac}*INDEX({S["rec_cpb"]},{fr_m}),"–"),"–"))'),
                "c_dec": f'=IF(NOT({on}),"",N({g("items")})*N({g("extra_item")}))',
                "c_pack": f'=IF(NOT({on}),"",N({g("items")})/12*N({g("pack_dozen")}))',
                "hrs": f'=IF(NOT({on}),"",N({g("hours")})+N({g("dec_hours")})*{lvl})',
                "c_lab": f'=IF(NOT({on}),"",{g("hrs")}*N({S["rate"]}))',
                "c_oh": f'=IF(NOT({on}),"",IF({S["oh_method"]}="Per order",{S["oh_order"]},{g("hrs")}*{S["oh_hour"]}))',
                "cost": (f'=IF(NOT({on}),"",IF(OR(ISTEXT({g("c_rec")}),ISTEXT({g("c_frost")})),"–",'
                         f'{g("c_rec")}+{g("c_frost")}+{g("c_dec")}+{g("c_pack")}+{g("c_lab")}+{g("c_oh")}))'),
                "cost_item": f'=IF(OR(NOT({on}),ISTEXT({g("cost")}),N({g("items")})=0),"",{g("cost")}/{g("items")})',
            }
            ci = g("cost_item")
            rnd = lambda mult, inc: (f'=IF({ci}="","",IF(N({inc})>0,ROUNDUP(ROUND({ci}*{mult}/(1-{m_}),6)/N({inc}),0)*N({inc}),'
                                     f'ROUND({ci}*{mult}/(1-{m_}),2)))')
            f["p_item"] = rnd(1, S["round_item"])
            f["p_half"] = rnd(6, S["round_dozen"])
            f["p_dozen"] = rnd(12, S["round_dozen"])
            f["profit_dozen"] = f'=IF({g("p_dozen")}="","",{g("p_dozen")}-12*{ci})'
            f["hourly"] = (f'=IF(OR({g("p_dozen")}="",N({g("hrs")})=0),"",({g("items")}*{g("p_dozen")}/12-({g("cost")}-{g("c_lab")}))'
                           f'/{g("hrs")})')
            f["check"] = (f'=IF(NOT({on}),"",IF(ISTEXT({g("c_rec")}),"Recipe has no cost: check RECIPES",IF(ISTEXT({g("c_frost")}),IF(IFERROR(INDEX({S["rec_cost"]},{fr_m}),"")="",'
                          f'"Frosting recipe has no cost: check RECIPES","Frosting unit doesn\'t match the frosting recipe yield"),'
                          f'IF(N({g("items")})=0,"Add items per batch",'
                          f'IF(N({g("hourly")})<N({S["rate"]}),"Low hourly earnings","OK")))))')
            for key, lab, fmt in out:
                cell = ws[f"{col}{B[key]}"]
                self.calc(cell, fmt, bold=key in ("cost", "cost_item", "p_item", "p_dozen"), align="center", value=f[key])
            ws.conditional_formatting.add(g("check"), FormulaRule(formula=[f'AND({g("check")}<>"",{g("check")}<>"OK")'],
                                                                  font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
            ws.conditional_formatting.add(g("check"), FormulaRule(formula=[f'{g("check")}="OK"'], font=Font(color=POS, bold=True)))
        for key in ("cost", "p_dozen"):
            for col in ["B"] + cols:
                x = ws[f"{col}{B[key]}"]
                x.fill, x.font = fill(GREEN), font(10, True, PAPER if col == "B" else BRASS)
        self.note(ws, f"G6:G{B['dec_hours']}", "Items per batch comes from the recipe when its yield is in items (24 each). "
                  "For a recipe measured in cups, type how many items one batch makes.\n\nFrosting per item: for example 2 tbsp "
                  "of buttercream per cupcake. The unit must match the frosting recipe's yield (volume with volume, weight with "
                  "weight).\n\nPrices are rounded up with the SETTINGS rounding.", tint=PAPER)
        ws[f"G6"].alignment = Alignment(wrap_text=True, vertical="top", indent=1)
        self.B = B
        ws.freeze_panes = "C6"
        ws.print_area = f"A1:G{r}"
        ws.page_setup.orientation = "landscape"
        self.protect(ws)
        if self.sample:
            for i, row in enumerate(c.BATCHES):
                col = cols[i]
                for key, v in zip(("name", "recipe", "per_batch_own", "batches", "frost", "frost_qty", "frost_unit", "level",
                                   "extra_item", "pack_dozen", "hours", "dec_hours"), row):
                    ws[f"{col}{B[key]}"] = v
        self.rows["batch_last"] = r

    # ============================================================ CUSTOMER QUOTE
    def build_customer(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_CQ]
        CB = q(S_CAKE)
        for col, w in {"A": 2, "B": 24, "C": 14, "D": 14, "E": 14, "F": 14, "G": 16, "H": 3, "I": 44}.items():
            ws.column_dimensions[col].width = w
        ws.sheet_view.showGridLines = False
        for r in range(1, 50):
            for col in range(1, 9):
                x = ws.cell(row=r, column=col)
                x.fill = fill(WHITE)
                x.font = Font(name=CUST, size=10, color="222222")
        f = lambda size=10, bold=False, color="222222", italic=False, name=CUST: Font(name=name, size=size, bold=bold,
                                                                                     color=color, italic=italic)
        SERIF = "Georgia"
        # selector and quote date (outside the printed columns)
        ws["I2"] = "Printing this quote"
        ws["I2"].font = Font(name="Inter", size=10, bold=True, color=GREEN)
        ws["I3"] = "Cake to quote (1, 2 or 3 from CAKE BUILDER)"
        ws["I3"].font = Font(name="Inter", size=9, color=INK2)
        self.inp(ws["I4"], align="center", value=1)
        ws["I4"].font = Font(name="Inter", size=11, bold=True, color=INK)
        self.dv_list(ws, "I4", f"={S['slots']}")
        ws["I5"] = "Quote date"
        ws["I5"].font = Font(name="Inter", size=9, color=INK2)
        self.inp(ws["I6"], DATE, "center", value=(c.QUOTE_DATE if self.sample else "=TODAY()"))
        ws.merge_cells("I8:I12")
        ws["I8"] = ("Everything on the quote comes from CAKE BUILDER and SETTINGS. File > Print (or Save as PDF): it fits one "
                    "page on letter or A4. This column doesn't print. Logo: Insert > Picture over the dashed box "
                    "(Review > Unprotect Sheet if Excel blocks it; no password).")
        ws["I8"].alignment = Alignment(wrap_text=True, vertical="top")
        ws["I8"].font = Font(name="Inter", size=9, color=INK2)
        SEL, QD = "$I$4", "$I$6"
        Aa = self.A

        def pick(fn):
            return f"CHOOSE({SEL},{','.join(f'{CB}!' + fn(Aa[k]) for k in range(SLOTS))})"

        def pick_rel(dr, col):
            """cell at row offset dr from a slot anchor key, column col."""
            return pick(lambda a: f"${col}${dr(a)}")

        line, dark = Side(style="thin", color="D9D2C5"), Side(style="medium", color="3A3A3A")
        dash = Side(style="dashed", color="BFBFBF")
        ws.merge_cells("B2:B5")
        ws["B2"] = "Your logo here"
        ws["B2"].font = f(9, False, "9A9A9A", True)
        ws["B2"].alignment = Alignment(horizontal="center", vertical="center")
        for r in range(2, 6):
            ws[f"B{r}"].border = Border(left=dash, right=dash, top=dash if r == 2 else None, bottom=dash if r == 5 else None)
        right = Alignment(horizontal="right", vertical="center")
        for r, formula, ft in [(2, f'=IF({S["name"]}="","Your bakery name",{S["name"]})', f(18, True, "222222", name=SERIF)),
                               (3, f'=IF({S["contact"]}="","",{S["contact"]})', f(10)),
                               (4, f'={S["phone"]}&IF(AND({S["phone"]}<>"",{S["email"]}<>""),"  ·  ","")&{S["email"]}', f(10)),
                               (5, f'={S["street"]}&IF(AND({S["street"]}<>"",{S["city"]}<>""),", ","")&{S["city"]}', f(10)),
                               (6, f'=IF({S["website"]}="","",{S["website"]})', f(10, False, "666666"))]:
            ws.merge_cells(f"C{r}:G{r}")
            ws[f"C{r}"] = formula
            ws[f"C{r}"].font = ft
            ws[f"C{r}"].alignment = right
        ws.row_dimensions[2].height = 28
        ws["B8"] = "Cake quote"
        ws["B8"].font = f(22, False, "222222", name=SERIF)
        for col in "BCDEFG":
            ws[f"{col}8"].border = Border(bottom=dark)
        ws.row_dimensions[8].height = 36
        cust = pick(lambda a: a["customer"])
        ev = pick(lambda a: a["event"])
        for col, lab in (("B", "Prepared for"), ("D", "Event date"), ("E", "Quote date"), ("F", "Valid until"), ("G", "Servings")):
            ws[f"{col}10"] = lab
            ws[f"{col}10"].font = f(8, True, "777777")
        ws["B11"] = f'=IF({cust}="","",{cust})'
        ws["B11"].font = f(12, True)
        ws.merge_cells("B12:C12")
        occ = pick(lambda a: a["occasion"])
        ws["B12"] = f'=IF({occ}="","",{occ})'
        ws["B12"].font = f(10, False, "555555", True)
        ws["D11"] = f'=IF(N({ev})=0,"",{ev})'
        ws["E11"] = f'=IF({QD}="","",{QD})'
        ws["F11"] = f'=IF({QD}="","",{QD}+N({S["valid_days"]}))'
        serv = pick(lambda a: a["servings"])
        ws["G11"] = f'=IF({serv}="","",{serv}&" "&LOWER({pick(lambda a: a["style"])}))'
        for col in "DEF":
            ws[f"{col}11"].number_format = DATE
            ws[f"{col}11"].alignment = Alignment(horizontal="left")
        ws["G11"].alignment = Alignment(horizontal="left")
        # cake description
        ws["B14"] = "Your cake"
        ws["B14"].font = f(9, True, "777777")
        for col in "BCDEFG":
            ws[f"{col}14"].border = Border(bottom=line)
        for k in range(TIERS):
            r = 15 + k
            g = lambda col: pick(lambda a, col=col: f"${col}${a['t1'] + k}")
            act = pick(lambda a: f"$S${a['t1'] + k}")
            txt = (f'=IF({act}<>1,"",IF({k}=0,"Bottom tier","Tier {k + 1}")&": "&{g("D")}&" "&LOWER({g("C")})&", "&{g("E")}&" layers  ·  "'
                   f'&{g("F")}&IF({g("G")}="","","  ·  "&{g("G")})&IF({g("H")}="","","  ·  "&{g("H")})'
                   f'&"  ·  "&LOWER(IF({g("I")}="","{c.COVERINGS[0][0]}",{g("I")})))')
            ws.merge_cells(f"B{r}:G{r}")
            ws[f"B{r}"] = txt
            ws[f"B{r}"].alignment = Alignment(vertical="center", shrink_to_fit=True)
            ws.row_dimensions[r].height = 18
        r = 15 + TIERS
        ws.merge_cells(f"B{r}:G{r + 1}")
        des = pick(lambda a: a["design"])
        lvl = pick(lambda a: a["level"])
        parts = []
        for j in range(EXTRA_N):
            e = pick(lambda a, j=j: f'$B${a["e1"] + j}')
            qn = pick(lambda a, j=j: f'$F${a["e1"] + j}')
            parts.append(f'IF(OR({e}="",N({qn})=0),"",", "&{qn}&" × "&TRIM(LEFT({e},FIND(" (",{e}&" (")-1)))')
        extras = "&".join(parts)
        ws[f"B{r}"] = (f'=IF({des}="","",{des})&IF({lvl}="",""," Decoration: "&LOWER({lvl}))'
                       f'&IF(LEN({extras})>2,", with "&LOWER(MID({extras},3,300)),"")&IF({lvl}="","",".")')
        ws[f"B{r}"].font = f(10, False, "333333")
        ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 22
        ws.row_dimensions[r + 1].height = 22
        r += 3
        dl = pick(lambda a: a["delivery"])
        ws[f"B{r}"] = "Pickup or delivery"
        ws[f"B{r}"].font = f(9, True, "777777")
        ws[f"B{r}"].alignment = Alignment(vertical="top")
        ws[f"C{r}"].alignment = Alignment(vertical="top")
        ws.merge_cells(f"C{r}:G{r}")
        ws[f"C{r}"] = f'=IF({dl}="","",{dl})'
        r += 1
        al = pick(lambda a: a["allergens"])
        ws[f"B{r}"] = "Allergen notes"
        ws[f"B{r}"].font = f(9, True, "777777")
        ws[f"B{r}"].alignment = Alignment(vertical="top")
        ws.merge_cells(f"C{r}:G{r}")
        ws[f"C{r}"] = f'=IF({al}="","Please tell us about any allergies.",{al})'
        ws[f"C{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 30
        self.rows["cq_allergen"] = r
        r += 2
        cur = lambda e: f'{S["currency"]}&FIXED({e},2)'
        price, dep, bal = (pick(lambda a, k=k: a[k]) for k in ("price", "deposit", "balance"))
        for lab, v, bold in (("Total", price, True), (f'="Deposit to book ("&FIXED(100*N({S["deposit"]}),0)&"%)"', dep, False),
                             ("Balance due", bal, False)):
            ws.merge_cells(f"B{r}:F{r}")
            ws[f"B{r}"] = lab if lab.startswith("=") else lab
            ws[f"G{r}"] = f'=IF({price}="","",{cur(v)})'
            for col in "BG":
                ws[f"{col}{r}"].alignment = Alignment(horizontal="right", vertical="center")
                ws[f"{col}{r}"].font = f(12 if bold else 10, bold)
            if bold:
                for col in "BCDEFG":
                    ws[f"{col}{r}"].border = Border(top=dark)
            ws.row_dimensions[r].height = 24 if bold else 20
            r += 1
        self.rows["cq_total"] = r - 3
        ws.merge_cells(f"B{r}:G{r}")
        ws[f"B{r}"] = f'=IF({price}="","",IF(N({serv})=0,"","That is "&{cur(f"{price}/{serv}")}&" per serving."))'
        ws[f"B{r}"].font = f(9, False, "777777", True)
        ws[f"B{r}"].alignment = Alignment(horizontal="right")
        r += 2
        ws[f"B{r}"] = "Terms"
        ws[f"B{r}"].font = f(9, True)
        r += 1
        ws.merge_cells(f"B{r}:G{r + 2}")
        ws[f"B{r}"] = f'=IF({S["terms"]}="","",{S["terms"]})'
        ws[f"B{r}"].font = f(9, False, "444444")
        ws[f"B{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        r += 4
        ws[f"B{r}"] = "Accepted by"
        ws[f"B{r}"].font = f(9, True)
        r += 2
        for col in "BCD":
            ws[f"{col}{r}"].border = Border(bottom=Side(style="thin", color="222222"))
        for col in "FG":
            ws[f"{col}{r}"].border = Border(bottom=Side(style="thin", color="222222"))
        ws.row_dimensions[r].height = 26
        r += 1
        ws[f"B{r}"], ws[f"F{r}"] = "Customer signature", "Date"
        for col in "BF":
            ws[f"{col}{r}"].font = f(8, False, "777777")
        r += 2
        ws.merge_cells(f"B{r}:G{r}")
        ws[f"B{r}"] = (f'="Thank you for choosing "&IF({S["name"]}="","us",{S["name"]})&IF(RIGHT({S["name"]},1)=".","",".")'
                       f'&" Questions? "&IF({S["phone"]}="",{S["email"]},{S["phone"]})')
        ws[f"B{r}"].font = f(9, False, "555555", True, SERIF)
        ws[f"B{r}"].alignment = Alignment(horizontal="center")
        last = r
        ws.print_area = f"A1:H{last + 1}"
        ws.page_setup.orientation = "portrait"
        ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
        ws.page_margins.left = ws.page_margins.right = 0.5
        ws.page_margins.top = ws.page_margins.bottom = 0.6
        ws.sheet_properties.tabColor = "BFBFBF"
        self.protect(ws)
        ws.protection.objects = False
        self.rows["cq_last"] = last

    # ============================================================ ORDER TRACKER
    def build_orders(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_ORD]
        widths = dict(B=14, C=24, D=27, E=14, F=17, G=13, H=42, I=9, J=11, K=11, L=14, M=9, N=11, O=24, P=11, Q=20,
                      R=6, S=6, T=6, U=6, V=3, W=15, X=22, Y=32, Z=10, AA=12)
        self.page(ws, widths, 27, ORD_LAST + 1, "Order tracker",
                  "One row per order. Orders due in the next 7 days and unpaid balances are highlighted.")
        for col in "RSTU":
            ws.column_dimensions[col].hidden = True
        R = lambda col: f"${col}${ORD_FIRST}:${col}${ORD_LAST}"
        due7 = f'COUNTIFS({R("E")},">="&TODAY(),{R("E")},"<="&TODAY()+7,{R("N")},"<>Cancelled",{R("N")},"<>Completed",{R("C")},"<>")'
        tiles = [(2, 3, "OPEN ORDERS", f'=SUMPRODUCT(COUNTIFS({R("N")},{{"Enquiry","Quoted","Booked","Baking"}}))', "0"),
                 (4, 6, "DUE IN THE NEXT 7 DAYS", f"={due7}", "0"),
                 (7, 9, "BALANCES TO COLLECT", f'={self.cur(f"SUM({R(chr(80))})")}', "General"),
                 (10, 14, "DEPOSITS NOT YET PAID", f'={self.cur(f"SUM({R(chr(82))})")}', "General")]
        for c1, c2, lab, f, fmt in tiles:
            self.tile(ws, 4, c1, c2, lab, f, fmt)
        cur = f'" ("&{S["currency"]}&")"'
        heads = [("B", "Order date"), ("C", "Customer"), ("D", "Phone or email"), ("E", "Event date"), ("F", "Pickup or delivery"),
                 ("G", "Type"), ("H", "Description"), ("I", "Servings"), ("J", f'="Price"&{cur}'), ("K", f'="Deposit paid"&{cur}'),
                 ("L", "Deposit date"), ("M", "Paid in full?"), ("N", "Status"), ("O", "Allergen notes"),
                 ("P", f'="Balance due"&{cur}'), ("Q", "When")]
        for col, t in heads:
            self.header(ws[f"{col}7"], t, GREEN2 if col in "PQ" else GREEN, align="left" if col in "CDHO" else "center")
        ws.row_dimensions[7].height = 34
        dep = S["deposit"]
        for r in range(ORD_FIRST, ORD_LAST + 1):
            for col, fmt in (("B", DATE), ("C", None), ("D", None), ("E", DATE), ("F", None), ("G", None), ("H", None),
                             ("I", "0"), ("J", MONEY), ("K", MONEY), ("L", DATE), ("M", None), ("N", None), ("O", None)):
                self.inp(ws[f"{col}{r}"], fmt, "center" if col in "BEFGILMN" else None)
            self.calc(ws[f"P{r}"], MONEY, value=f'=IF(J{r}="","",IF(OR(M{r}="Yes",N{r}="Cancelled"),0,MAX(0,J{r}-N(K{r}))))')
            self.calc(ws[f"Q{r}"], align="center",
                      value=(f'=IF(OR(E{r}="",N{r}="Cancelled",N{r}="Completed"),"",IF(E{r}<TODAY(),"Past",IF(E{r}=TODAY(),"Today",'
                             f'IF(E{r}-TODAY()<=7,"In "&(E{r}-TODAY())&IF(E{r}-TODAY()=1," day"," days"),"In "&(E{r}-TODAY())&" days"))))'))
            ws[f"R{r}"] = (f'=IF(OR(J{r}="",AND(N{r}<>"Quoted",N{r}<>"Booked",N{r}<>"Baking")),"",'
                           f'MAX(0,ROUND(J{r}*N({dep}),2)-N(K{r})))')
            ws[f"S{r}"] = (f'=IF(OR(E{r}="",C{r}="",N{r}="Completed",N{r}="Cancelled",N{r}=""),"",IF(E{r}<TODAY(),"",'
                           f'E{r}+ROW()/100000))')
            ws[f"T{r}"] = f'=IF(OR(E{r}="",C{r}=""),"",MONTH(E{r}))'
            ws[f"U{r}"] = f'=IF(OR(E{r}="",C{r}=""),"",YEAR(E{r}))'
        rr = lambda col: f"{col}{ORD_FIRST}:{col}{ORD_LAST}"
        self.dv_list(ws, rr("F"), f"={S['delivery']}")
        self.dv_list(ws, rr("G"), f"={S['otypes']}")
        self.dv_list(ws, rr("M"), f"={S['yesno']}")
        self.dv_list(ws, rr("N"), f"={S['statuses']}")
        for col in "IJK":
            self.dv_num(ws, rr(col))
        v = DataValidation(type="date", operator="between", formula1="36526", formula2="73051", allow_blank=True,
                           showErrorMessage=True, errorTitle="Date", error="Enter a date.")
        ws.add_data_validation(v)
        for col in "BEL":
            v.add(rr(col))
        soon = f'AND($E{ORD_FIRST}<>"",$E{ORD_FIRST}>=TODAY(),$E{ORD_FIRST}-TODAY()<=7,$N{ORD_FIRST}<>"Cancelled",$N{ORD_FIRST}<>"Completed")'
        ws.conditional_formatting.add(f"B{ORD_FIRST}:O{ORD_LAST}", FormulaRule(formula=[soon], fill=fill(BRASS_TINT)))
        ws.conditional_formatting.add(rr("Q"), FormulaRule(formula=[soon], font=Font(color=GREEN, bold=True), fill=fill(BRASS_TINT)))
        unpaid = f'AND(ISNUMBER($P{ORD_FIRST}),$P{ORD_FIRST}>0,OR($N{ORD_FIRST}="Completed",AND($E{ORD_FIRST}<>"",$E{ORD_FIRST}<TODAY())))'
        ws.conditional_formatting.add(rr("P"), FormulaRule(formula=[unpaid], font=Font(color=NEG, bold=True), fill=fill(NEG_TINT)))
        ws.conditional_formatting.add(rr("N"), FormulaRule(formula=[f'$N{ORD_FIRST}="Cancelled"'], font=Font(color="9A958C")))
        ws.conditional_formatting.add(rr("N"), FormulaRule(formula=[f'$N{ORD_FIRST}="Completed"'], font=Font(color=POS, bold=True)))
        # upcoming list
        self.kicker(ws, "W6", "Coming up  ·  sorted by event date", rule_to=27)
        for col, t in (("W", "Event date"), ("X", "Customer"), ("Y", "Description"), ("Z", "Status"), ("AA", f'="Balance"&{cur}')):
            self.header(ws[f"{col}7"], t, align="left" if col in "XY" else "center")
        Sk = R("S")
        for k in range(20):
            r = ORD_FIRST + k
            m = f"MATCH(SMALL({Sk},{k + 1}),{Sk},0)"
            for col, src, fmt in (("W", "E", DATE), ("X", "C", None), ("Y", "H", None), ("Z", "N", None), ("AA", "P", MONEY)):
                self.calc(ws[f"{col}{r}"], fmt, align="center" if col in "WZ" else None,
                          value=f'=IFERROR(INDEX({R(src)},{m}),"")')
            ws[f"Y{r}"].alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
        ws.conditional_formatting.add(f"W{ORD_FIRST}:AA{ORD_FIRST + 19}",
                                      FormulaRule(formula=[f'AND(ISNUMBER($W{ORD_FIRST}),$W{ORD_FIRST}-TODAY()<=7)'], fill=fill(BRASS_TINT)))
        ws.freeze_panes = f"D{ORD_FIRST}"
        ws.auto_filter.ref = f"B7:Q{ORD_LAST}"
        ws.print_area = f"A1:Q{ORD_LAST}"
        ws.page_setup.orientation = "landscape"
        ws.print_title_rows = "7:7"
        self.protect(ws)
        self.S["ord"] = lambda col: f"{q(S_ORD)}!${col}${ORD_FIRST}:${col}${ORD_LAST}"
        if self.sample:
            for i, row in enumerate(c.ORDERS):
                r = ORD_FIRST + i
                for col, val in zip("BCDEFGHIJKLMNO", row):
                    ws[f"{col}{r}"] = None if val in ("", None) else val

    # ============================================================ DASHBOARD
    def build_dashboard(self):
        c, S = self.cfg, self.S
        ws = self.ws[S_DASH]
        widths = {L(k): 12.5 for k in range(2, 14)}
        widths["B"] = 15
        self.page(ws, widths, 13, 70, "Dashboard", "This month, the year, deposits and what's due this week.")
        O = S["ord"]
        ws.merge_cells("B4:M4")
        self.label(ws["B4"], f'=IF({S["name"]}="","Your bakery",{S["name"]})&"  ·  "&{S["year"]}', color=GREEN, size=11)
        live = f'{O("N")},"<>Cancelled",{O("C")},"<>"'
        mon = f'{O("T")},MONTH(TODAY()),{O("U")},YEAR(TODAY())'
        tiles1 = [("ORDERS THIS MONTH", f"=COUNTIFS({mon},{live})"),
                  ("REVENUE THIS MONTH", f'={self.cur(f"SUMIFS({O(chr(74))},{mon},{live})")}'),
                  ("REVENUE YEAR TO DATE", "=" + self.cur(f'SUMIFS({O("J")},{O("U")},N({S["year"]}),{O("E")},"<="&TODAY(),{live})')),
                  ("AVERAGE ORDER", f'=IFERROR({self.cur(f"AVERAGEIFS({O(chr(74))},{O(chr(74))},CHAR(62)&0,{live})")},"–")')]
        tiles2 = [("AVERAGE PRICE PER SERVING", f'=IFERROR({self.cur(f"SUMIFS({O(chr(74))},{O(chr(73))},CHAR(62)&0,{O(chr(74))},CHAR(62)&0,{live})/SUMIFS({O(chr(73))},{O(chr(73))},CHAR(62)&0,{O(chr(74))},CHAR(62)&0,{live})")},"–")'),
                  ("DEPOSITS NOT YET PAID", f'={self.cur(f"SUM({O(chr(82))})")}'),
                  ("ORDERS DUE THIS WEEK", f'=COUNTIFS({O("E")},">="&TODAY(),{O("E")},"<="&TODAY()+7,{O("N")},"<>Cancelled",{O("N")},"<>Completed",{O("C")},"<>")')]
        for i, (lab, f) in enumerate(tiles1):
            self.tile(ws, 6, 2 + 3 * i, 4 + 3 * i, lab, f, "0" if i == 0 else "General")
        for i, (lab, f) in enumerate(tiles2):
            self.tile(ws, 9, 2 + 4 * i, 5 + 4 * i, lab, f, "0" if i == 2 else "General")
        ws.row_dimensions[8].height = 6

        def head(r, cols):
            for col, t in cols:
                self.header(ws[f"{col}{r}"], t, align="left" if col == "B" else "center")
            ws.row_dimensions[r].height = 24

        rows = {}
        r = 12
        rows["months"] = r
        self.kicker(ws, f"B{r}", "Monthly revenue  ·  by event date", rule_to=13)
        hr = r + 1
        head(hr, [("B", "Month"), ("C", "Orders"), ("D", "Revenue")])
        yr = f"{O('U')},N({S['year']})"
        for k in range(12):
            rr = hr + 1 + k
            ws[f"B{rr}"] = c.MONTHS[k][:3]
            ws[f"B{rr}"].font = font(10, True, INK)
            ws[f"B{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            self.calc(ws[f"C{rr}"], "0", align="center", value=f"=COUNTIFS({O('T')},{k + 1},{yr},{live})")
            self.calc(ws[f"D{rr}"], MONEY0, value=f"=SUMIFS({O('J')},{O('T')},{k + 1},{yr},{live})")
        ch = BarChart()
        ch.type, ch.style = "col", 10
        ch.add_data(Reference(ws, min_col=4, min_row=hr, max_row=hr + 12), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=2, min_row=hr + 1, max_row=hr + 12))
        ch.series[0].graphicalProperties.solidFill = GREEN
        ch.series[0].graphicalProperties.line.solidFill = GREEN
        BP.clean_chart(ch, legend=False)
        ch.gapWidth = 50
        ch.height, ch.width = 7.0, 19.0
        ch.anchor = f"F{hr}"
        ws.add_chart(ch)
        r = hr + 15
        rows["types"] = r
        self.kicker(ws, f"B{r}", "Orders by type", rule_to=13)
        hr = r + 1
        head(hr, [("B", "Type"), ("C", "Orders"), ("D", "Revenue")])
        d1 = hr + 1
        n = len(c.ORDER_TYPES)
        for k in range(n):
            rr = d1 + k
            ws[f"B{rr}"] = f"=INDEX({S['otypes']},{k + 1})"
            ws[f"B{rr}"].font = font(10, True, INK)
            ws[f"B{rr}"].alignment = Alignment(horizontal="left", vertical="center", indent=1)
            self.calc(ws[f"C{rr}"], "0", align="center", value=f"=COUNTIFS({O('G')},B{rr},{live})")
            self.calc(ws[f"D{rr}"], MONEY0, value=f"=SUMIFS({O('J')},{O('G')},B{rr},{live})")
        ch = DoughnutChart(holeSize=55)
        ch.add_data(Reference(ws, min_col=3, min_row=d1, max_row=d1 + n - 1), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=d1, max_row=d1 + n - 1))
        for k, colr in enumerate([GREEN, BRASS, "6B7F79", "2E7D4F", "C9D3CF"]):
            pt = DataPoint(idx=k)
            pt.graphicalProperties.solidFill = colr
            pt.graphicalProperties.line.solidFill = "FFFFFF"
            ch.series[0].dPt.append(pt)
        BP.clean_chart(ch, legend=True, axes=False, legend_pos="r")
        ch.height, ch.width = 5.0, 13.0
        ch.anchor = f"F{hr}"
        ws.add_chart(ch)
        r = d1 + n + 4
        self.note(ws, f"B{r}:M{r}", DISCLAIMER, height=30, size=9, color=INK, bold=True)
        rows["end"] = r
        self.rows["dash"] = rows
        ws.print_area = f"A1:M{r}"
        self.protect(ws)

    # ============================================================ START HERE
    def build_start(self):
        c = self.cfg
        ws = self.ws[S_START]
        self.page(ws, {"B": 5, "C": 30, "D": 30, "E": 30, "F": 24}, 6, 80, "Start here",
                  "Read this first. Setting up takes about 20 minutes.", landscape=False)
        self.note(ws, "B4:F4", "Know what every cake really costs, and what to charge for it.", tint=PAPER, height=32,
                  size=15, color=GREEN, bold=True)
        ws["B4"].font = Font(name=TITLE, size=15, bold=True, color=GREEN)
        self.note(ws, "B5:F5", "Pricing by ingredients alone leaves out your hours, boards and boxes, decorations, electricity "
                  "and delivery. This workbook costs every ingredient, recipe and tier, adds your time at your own hourly rate, "
                  "and shows a price per serving you can explain to customers.", tint=PAPER, height=48, size=10, color=INK)
        r = 7
        self.kicker(ws, f"B{r}", "Quick start in 4 steps", rule_to=6)
        r = 8
        for num, head, body, sheet in [
                ("1", "Settings", "Your bakery details, hourly rate, margin, minimum price per serving, deposit, overhead, "
                 "delivery, supplies and decorations. The pan and serving table is ready to use.", S_SET),
                ("2", "Ingredients", "Type what you pay and the package size for each ingredient. Names and grams per cup "
                 "are already filled in for 48 common ones.", S_ING),
                ("3", "Recipes", "One block per recipe: pick ingredients from the list, type quantities in any unit, and "
                 "say what the recipe yields (cups of batter, grams of fondant, 24 cupcakes).", S_REC),
                ("4", "Price a cake", "On CAKE BUILDER, choose the tiers, recipes, decoration and hours. The price, price "
                 "per serving and deposit appear. Print the CUSTOMER QUOTE, then log the order.", S_CAKE)]:
            x = ws[f"B{r}"]
            x.value = num
            x.font = Font(name=TITLE, size=18, bold=True, color=BRASS)
            x.alignment = Alignment(horizontal="center", vertical="top")
            self.link(ws[f"C{r}"], f"{head}  ›", sheet)
            ws[f"C{r}"].alignment = Alignment(vertical="top")
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"] = body
            ws[f"D{r}"].font = font(10, color=INK)
            ws[f"D{r}"].alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 48
            r += 1
        self.link(ws[f"C{r}"], "Cupcakes and cookies  ›", S_BATCH)
        ws[f"C{r}"].alignment = Alignment(vertical="top")
        ws.merge_cells(f"D{r}:F{r}")
        ws[f"D{r}"] = "BATCH PRICING prices per item, half dozen and dozen. ORDER TRACKER keeps deposits and due dates."
        ws[f"D{r}"].font = font(10, color=INK2)
        ws[f"D{r}"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 34
        r += 2
        self.kicker(ws, f"B{r}", "How the recipes tab is laid out", rule_to=6)
        r += 1
        self.note(ws, f"B{r}:F{r}", "RECIPES has an index at the top (one line per recipe with its cost and cost per cup, gram "
                  "or item) and 40 recipe blocks below it, each with room for 16 ingredients. Use the Go to links in the index to jump "
                  "to its block. Fixed blocks keep every formula simple, so it works the same in Excel and Google Sheets.",
                  tint=PAPER, height=48, size=10, color=INK)
        r += 2
        self.kicker(ws, f"B{r}", "Colour key", rule_to=6)
        r += 1
        for kind, head, body in [("inp", "Type here", "White cell with a border: your numbers, or pick from the dropdown."),
                                 ("calc", "Calculated", "Shaded cell: a formula, locked so it can't be overwritten by accident."),
                                 ("tile", "Result", "Green block with a brass figure: a key number."),
                                 ("warn", "Check this", "Red: a missing price or conversion, or a price below your minimum.")]:
            x = ws[f"C{r}"]
            if kind == "inp":
                self.inp(x)
            elif kind == "calc":
                self.calc(x)
            elif kind == "tile":
                x.fill, x.font = fill(GREEN), font(10, True, BRASS)
            else:
                x.fill, x.font = fill(NEG_TINT), font(10, True, NEG)
            x.value = head
            x.protection = Protection(locked=True)
            x.alignment = Alignment(indent=1, vertical="center")
            ws.merge_cells(f"D{r}:F{r}")
            ws[f"D{r}"] = body
            ws[f"D{r}"].font = font(10, color=INK2)
            ws[f"D{r}"].alignment = Alignment(vertical="center", indent=1)
            ws.row_dimensions[r].height = 22
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Reminders  ·  not legal advice", rule_to=6, color=NEG)
        r += 1
        for t in c.COMPLIANCE:
            self.note(ws, f"B{r}:F{r}", t, tint=NEG_TINT, height=34, size=9.5, color=NEG, bold=True)
            r += 1
        r += 1
        self.kicker(ws, f"B{r}", "Guide and Google Sheets", rule_to=6)
        r += 1
        self.note(ws, f"B{r}:F{r}", f"Quick-start guide: {c.GUIDE_NAME} (in your download).   "
                  "Google Sheets copy: [GOOGLE SHEETS COPY LINK]", tint=PAPER, height=30, size=10, color=INK)
        r += 2
        self.note(ws, f"B{r}:F{r}", DISCLAIMER, tint=BRASS_TINT, height=30, size=10, color=INK, bold=True)
        if self.sample:
            r += 2
            self.note(ws, f"B{r}:F{r}", "SAMPLE FILE: a fictional bakery, Willow & Whisk, with 48 priced ingredients, 9 recipes, "
                      "a 3-tier wedding cake, a birthday cake, two batches and 15 orders. Use the blank file for your own bakery.",
                      tint=POS_TINT, height=34, size=10, color=POS, bold=True)
        ws.print_area = f"A1:G{r + 1}"
        self.protect(ws)

    # ============================================================ build
    def build(self):
        self.build_settings()
        self.build_ingredients()
        self.build_recipes()
        self.build_cake()
        self.build_batch()
        self.build_customer()
        self.build_orders()
        self.build_dashboard()
        self.build_start()
        self.wb.active = 0
        for ws in self.wb.worksheets:
            ws.sheet_view.tabSelected = ws.title == S_START
        self.wb.calculation.fullCalcOnLoad = True
        p = self.wb.properties
        p.title, p.creator, p.subject = self.cfg.PRODUCT, "Brass Ledger", "Simple tools for small business numbers."
        return self.wb

    def add_sidebars(self):
        return BP.add_sidebars(self.wb, NAV, {S_START: 70, S_SET: self.rows["set_last"] + 2, S_ING: 120, S_REC: 200,
                                              S_CAKE: SLOT_FIRST + SLOTS * SLOT_SIZE, S_BATCH: 60, S_ORD: 120, S_DASH: 70},
                               skip=(S_CQ,), max_last=260)


def main(cfg, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for sample in (False, True):
        e = CakeEngine(cfg, sample)
        wb = e.build()
        layers = e.add_sidebars()
        p = out_dir / (cfg.OUT_NAME + ("_SAMPLE" if sample else "") + ".xlsx")
        wb.save(p)
        BP.finish(p, layers)
        paths.append(p)
        print("wrote", p)
    return paths
