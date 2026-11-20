"""Shared design system + openpyxl helpers for every spreadsheet product in the bundle."""
from __future__ import annotations

import json
import re
from pathlib import Path

from openpyxl.formatting.rule import FormulaRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

TOKENS = json.loads((Path(__file__).resolve().parent.parent / "design-system" / "design-tokens.json").read_text())
_c = TOKENS["color"]


def _h(x: str) -> str:
    return x.lstrip("#").upper()


NAVY = _h(_c["primary"]["deep_navy"])
MIDNIGHT = _h(_c["primary"]["midnight_blue"])
BLUE = _h(_c["primary"]["professional_blue"])
SOFT_BLUE = _h(_c["primary"]["soft_blue"])
TEAL = _h(_c["accent"]["teal"])
SOFT_TEAL = _h(_c["accent"]["soft_teal"])
LAVENDER = _h(_c["accent"]["lavender"])
SOFT_LAV = _h(_c["accent"]["soft_lavender"])
BG = _h(_c["neutral"]["background"])
WHITE = "FFFFFF"
LIGHT_GRAY = _h(_c["neutral"]["light_gray"])
MED_GRAY = _h(_c["neutral"]["medium_gray"])
DARK = _h(_c["neutral"]["dark_text"])
SECONDARY = _h(_c["neutral"]["secondary_text"])
BORDER = _h(_c["neutral"]["border"])
SUCCESS = _h(_c["status"]["success"])
SUCCESS_BG = _h(_c["status"]["success_bg"])
WARNING = _h(_c["status"]["warning"])
WARNING_BG = _h(_c["status"]["warning_bg"])
DANGER = _h(_c["status"]["danger"])
DANGER_BG = _h(_c["status"]["danger_bg"])
INFO = _h(_c["status"]["info"])
INFO_BG = _h(_c["status"]["info_bg"])

FMT_DATE = "mmm d, yyyy"
FMT_SDATE = "mmm d"
FMT_CUR = "#,##0.00"
FMT_CUR0 = "#,##0"
FMT_PCT = "0%"
FMT_HRS = "0.0"
FMT_TIME = "h:mm AM/PM"


class Theme:
    """Edition-aware style factory (both editions use Arial so the layout is identical everywhere)."""

    def __init__(self, edition: str):
        self.edition = edition
        self.font_name = "Inter"          # brand body font (Google Sheets has it; Excel substitutes if not installed)
        # Fraunces is the brand heading font; inside Excel it isn't available, so titles use Georgia there
        self.title_name = "Georgia" if edition == "excel" else "Fraunces"

    def font(self, size=10, bold=False, color=DARK, italic=False, underline=None):
        return Font(name=self.font_name, size=size, bold=bold, color=color, italic=italic, underline=underline)

    def title_font(self, size=18, color="FAF7F2"):
        return Font(name=self.title_name, size=size, bold=True, color=color)


def fill(color: str) -> PatternFill:
    return PatternFill("solid", start_color=color, end_color=color)


THIN = Side(style="thin", color=BORDER)
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BOTTOM = Border(bottom=THIN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=False, indent=1)
LEFT_WRAP = Alignment(horizontal="left", vertical="top", wrap_text=True, indent=1)
RIGHT = Alignment(horizontal="right", vertical="center", indent=1)

FILL_INPUT = fill(WHITE)            # Brass Ledger: inputs are white with a border
PAPER, BRASS = "FAF7F2", "D29A3A"
FILL_CALC = fill(LIGHT_GRAY)
FILL_POS = fill(SOFT_TEAL)
FILL_NEG = fill(DANGER_BG)
FILL_OPT = fill(SOFT_LAV)
FILL_WHITE = fill(WHITE)
FILL_BG = fill(BG)
FILL_NAVY = fill(NAVY)
FILL_MID = fill(MIDNIGHT)


def col(c) -> str:
    return c if isinstance(c, str) else get_column_letter(c)


def quote(sheet: str) -> str:
    return f"'{sheet}'"


def ref(sheet: str, rng: str) -> str:
    return f"{quote(sheet)}!{rng}"


def setup_sheet(ws, widths: dict, tab_color: str | None = None, zoom=100, bg=True, max_row=120, max_col=30):
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = zoom
    if tab_color:
        ws.sheet_properties.tabColor = tab_color
    ws.column_dimensions["A"].width = 2.5
    for k, v in widths.items():
        ws.column_dimensions[col(k)].width = v


def _cells(ws, rng: str):
    if ":" not in rng:
        return [ws[rng]]
    return [c for row in ws[rng] for c in row]


def paint(ws, rng: str, f=None, font=None, border=None, align=None, numfmt=None):
    for c in _cells(ws, rng):
        if True:
            if f is not None:
                c.fill = f
            if font is not None:
                c.font = font
            if border is not None:
                c.border = border
            if align is not None:
                c.alignment = align
            if numfmt is not None:
                c.number_format = numfmt


TAB_ORDER: list[str] = []          # set by each product builder (used for "Next tab" links)
HERO_SUB = "C9D3CF"
CELL_EDGE = Side(style="thin", color="E6E1D8")
CELL_BOX = Border(left=CELL_EDGE, right=CELL_EDGE, top=CELL_EDGE, bottom=CELL_EDGE)


def col_px(ws, c: int) -> int:
    w = ws.column_dimensions[get_column_letter(c)].width
    return int((w or 8.43) * 7 + 5)


def title_bar(ws, T: Theme, title: str, subtitle: str, last_col: int, home_link: str | None = "All-in-One Dashboard",
              demo: bool = False, hero_to: int | None = None, home_label: str = "⌂ Dashboard"):
    """Brass Ledger title bar on rows 2-3: green fill, paper title in the heading font, subtitle beneath.

    Right block (wide enough for the text): "BRASS LEDGER" small in brass (row 2) and one link (row 3) — the home tab,
    or "Next tab" on the home tab itself. The band runs to `hero_to` (default last_col).
    """
    hero_to = hero_to or last_col
    ws.row_dimensions[1].height = 8
    ws.row_dimensions[2].height = 34
    ws.row_dimensions[3].height = 20
    for r in (2, 3):
        for c in range(2, hero_to + 1):
            ws.cell(row=r, column=c).fill = FILL_NAVY
    # right block: grow leftwards until >= 110 px
    rb, width = last_col, col_px(ws, last_col)
    while width < 110 and rb > 3:
        rb -= 1
        width += col_px(ws, rb)
    left_end = rb - 1
    for r in (2, 3):
        if left_end > 2:
            ws.merge_cells(f"B{r}:{get_column_letter(left_end)}{r}")
        if last_col > rb:
            ws.merge_cells(f"{get_column_letter(rb)}{r}:{get_column_letter(last_col)}{r}")
    ws["B2"] = title
    ws["B2"].font = T.title_font(18, PAPER)
    ws["B2"].alignment = Alignment(vertical="center", indent=1)
    ws["B3"] = ("●  DEMO DATA   ·   " if demo else "") + subtitle
    ws["B3"].font = T.font(9, False, HERO_SUB)
    ws["B3"].alignment = Alignment(vertical="center", indent=1, shrink_to_fit=True)
    right = Alignment(horizontal="right", vertical="center", indent=1)
    c = ws.cell(row=2, column=rb)                      # brand mark, small, in brass
    c.value = "BRASS LEDGER"
    c.font = T.font(8, True, BRASS)
    c.alignment = right
    c = ws.cell(row=3, column=rb)                      # one navigation link: home, or next tab on the home tab itself
    if home_link:
        c.value = f'=HYPERLINK("#{quote(home_link)}!A1","{home_label}")'
    elif TAB_ORDER and ws.title in TAB_ORDER:
        nxt = TAB_ORDER[(TAB_ORDER.index(ws.title) + 1) % len(TAB_ORDER)]
        c.value = f'=HYPERLINK("#{quote(nxt)}!A1","Next tab ▸")'
    c.font = T.font(9, True, PAPER)
    c.alignment = right

def kicker_text(text):
    """Section labels are uppercase kickers; any explanation after a dash keeps its case."""
    if not isinstance(text, str) or text.startswith("="):
        return text
    for sep in ("  —  ", " — "):
        if sep in text:
            head, rest = text.split(sep, 1)
            return head.upper() + "  —  " + rest
    return text.upper()


def section(ws, T: Theme, r: int, c1: int, c2: int, text: str, color=BLUE, height=24, size=9):
    """Card title row: white, green uppercase kicker, brass rule on top."""
    accent = Side(style="medium", color=BRASS)
    for c in range(c1, c2 + 1):
        cell = ws.cell(row=r, column=c)
        cell.fill = FILL_WHITE
        cell.border = Border(top=accent, bottom=Side(style="thin", color="E6E1D8"),
                             left=THIN if c == c1 else None, right=THIN if c == c2 else None)
    if c2 > c1:
        ws.merge_cells(f"{get_column_letter(c1)}{r}:{get_column_letter(c2)}{r}")
    cell = ws.cell(row=r, column=c1, value=kicker_text(text))
    cell.font = T.font(size, True, NAVY)
    cell.alignment = Alignment(vertical="center", indent=1, shrink_to_fit=True)
    ws.row_dimensions[r].height = height


def header_row(ws, T: Theme, r: int, c1: int, headers: list[str], color=NAVY, height=30):
    """Modern table header: light fill, dark bold text, accent underline."""
    accent = Side(style="medium", color=BLUE if color in (NAVY, MIDNIGHT) else color)
    helper = color == MED_GRAY
    for i, h in enumerate(headers):
        cell = ws.cell(row=r, column=c1 + i, value=h)
        cell.fill = fill("F3EFE7" if helper else "EFEAE0")
        cell.font = T.font(9, True, SECONDARY if helper else MIDNIGHT)
        cell.alignment = CENTER
        cell.border = Border(left=CELL_EDGE, right=CELL_EDGE, top=CELL_EDGE,
                             bottom=Side(style="medium", color=MED_GRAY if helper else accent.color))
    ws.row_dimensions[r].height = height


def mark_helper_headers(ws, r: int, c1: int, c2: int):
    """Restyle header cells of calculated helper columns (grey, secondary text)."""
    for c in range(c1, c2 + 1):
        cell = ws.cell(row=r, column=c)
        cell.fill = fill("F3EFE7")
        cell.font = Font(name=cell.font.name, size=9, bold=True, color=SECONDARY)
        cell.border = Border(left=CELL_EDGE, right=CELL_EDGE, top=CELL_EDGE, bottom=Side(style="medium", color=MED_GRAY))


def legend(ws, T: Theme, r: int, c: int, compact=False):
    """Cell-convention legend laid out horizontally from (r, c): swatch + label pairs."""
    items = [
        (FILL_INPUT, "Input"), (FILL_WHITE, "Info"), (FILL_CALC, "Calculated"),
        (FILL_POS, "Positive"), (FILL_NEG, "Warning"), (FILL_OPT, "Optional"),
    ]
    if compact:
        items = [items[0], items[2], items[5]]
    lab = ws.cell(row=r, column=c, value="LEGEND")
    lab.font = T.font(8, True, SECONDARY)
    lab.alignment = Alignment(vertical="center", indent=1)
    for i, (f, t) in enumerate(items):
        sw = ws.cell(row=r, column=c + 1 + i * 2)
        sw.fill = f
        sw.border = BOX
        tx = ws.cell(row=r, column=c + 2 + i * 2, value=t)
        tx.font = T.font(8, False, SECONDARY)
        tx.alignment = Alignment(vertical="center", indent=1)


def green_tile(ws, T: Theme, r: int, c1: int, c2: int, label, formula, numfmt=None, size=15):
    """Result block: green fill, small paper label (row r), main figure in brass (row r + 1)."""
    gap = Side(style="medium", color=PAPER)
    for rr in (r, r + 1):
        if c2 > c1:
            ws.merge_cells(f"{get_column_letter(c1)}{rr}:{get_column_letter(c2)}{rr}")
        for cc in range(c1, c2 + 1):
            cell = ws.cell(row=rr, column=cc)
            cell.fill = FILL_NAVY
            cell.border = Border(left=gap if cc == c1 else None, right=gap if cc == c2 else None)
    lc = ws.cell(row=r, column=c1, value=label)
    lc.font = T.font(8, True, "C9D3CF")
    lc.alignment = Alignment(vertical="bottom", indent=1, shrink_to_fit=True)
    vc = ws.cell(row=r + 1, column=c1, value=formula)
    vc.font = T.font(size, True, BRASS)
    vc.alignment = Alignment(horizontal="left", vertical="center", indent=1, shrink_to_fit=True)
    if numfmt:
        vc.number_format = numfmt
    return vc


def stat_strip(ws, T: Theme, r: int, items, start_col: int = 2, min_px: int = 130, end_col: int | None = None):
    """Row of KPI tiles (label row r, value row r+1). items: (label, formula, numfmt, accent).

    Each tile takes as many consecutive columns as needed to reach `min_px`. Returns the next free column.
    """
    ws.row_dimensions[r].height = 20
    ws.row_dimensions[r + 1].height = 30
    c = start_col
    for label, formula, numfmt, accent in items:
        c1, width = c, col_px(ws, c)
        while width < min_px:
            c += 1
            width += col_px(ws, c)
        c2 = c
        if end_col and c2 > end_col:
            break
        green_tile(ws, T, r, c1, c2, label, formula, numfmt, size=16)
        c += 2  # one gutter column between tiles
    return c


def card_box(ws, c1: int, r1: int, c2: int, r2: int):
    """White card: fill unfilled cells white and draw the outer edge (keeps existing inner borders / accents)."""
    for r in range(r1, r2 + 1):
        for c in range(c1, c2 + 1):
            cell = ws.cell(row=r, column=c)
            if cell.fill is None or cell.fill.fill_type is None:
                cell.fill = FILL_WHITE
            b = cell.border
            cell.border = Border(left=(b.left if b.left and b.left.style else THIN) if c == c1 else b.left,
                                 right=(b.right if b.right and b.right.style else THIN) if c == c2 else b.right,
                                 top=(b.top if b.top and b.top.style else THIN) if r == r1 else b.top,
                                 bottom=(b.bottom if b.bottom and b.bottom.style else THIN) if r == r2 else b.bottom)


def skin(ws, last_col: int, last_row: int, cards=(), hide_headers=False):
    """Apply the app look: white cards on a light canvas. Any unfilled cell outside a card becomes canvas."""
    for (c1, r1, c2, r2) in cards:
        card_box(ws, c1, r1, c2, r2)
    for r in range(1, last_row + 2):
        for c in range(1, last_col + 2):
            cell = ws.cell(row=r, column=c)
            if cell.fill is None or cell.fill.fill_type is None:
                cell.fill = FILL_BG
    if hide_headers:
        ws.sheet_view.showRowColHeaders = False


def place_chart(ws, chart, c1: int, r1: int, c2: int, r2: int, pad: int = 6):
    """Pin a chart inside the cell box (c1,r1)-(c2,r2) with `pad` px padding (two-cell anchor)."""
    from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, TwoCellAnchor
    emu = 9525
    a = TwoCellAnchor()
    a._from = AnchorMarker(col=c1 - 1, colOff=pad * emu, row=r1 - 1, rowOff=pad * emu)
    hpx = int((ws.row_dimensions[r2].height or 15) * 96 / 72)
    a.to = AnchorMarker(col=c2 - 1, colOff=max(0, col_px(ws, c2) - pad) * emu, row=r2 - 1, rowOff=max(0, hpx - pad) * emu)
    chart.anchor = a
    ws.add_chart(chart)


def add_list_dv(ws, rng: str, source: str, prompt: str | None = None, allow_blank=True, strict=True):
    dv = DataValidation(type="list", formula1=source, allow_blank=allow_blank, showErrorMessage=strict)
    dv.error = "Please choose a value from the dropdown list (edit lists on the Setup tab)."
    dv.errorTitle = "Invalid entry"
    if prompt:
        dv.prompt = prompt
        dv.showInputMessage = True
    ws.add_data_validation(dv)
    dv.add(rng)
    return dv


def add_dv(ws, rng: str, type_: str, op: str | None = None, f1=None, f2=None, error=None):
    dv = DataValidation(type=type_, operator=op, formula1=f1, formula2=f2, allow_blank=True, showErrorMessage=True)
    dv.error = error or "Invalid value."
    ws.add_data_validation(dv)
    dv.add(rng)
    return dv


def cf_formula(ws, rng: str, formula: str, fill_color=None, font_color=None, bold=None, stop=False, T: Theme | None = None):
    kw = {}
    if fill_color:
        kw["fill"] = fill(fill_color)
    if font_color or bold:
        kw["font"] = Font(color=font_color, bold=bold)
    ws.conditional_formatting.add(rng, FormulaRule(formula=[formula], stopIfTrue=stop, **kw))


def cf_databar(ws, rng: str, color=BLUE):
    ws.conditional_formatting.add(
        rng, DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color=color, showValue=True,
                          minLength=0, maxLength=100)
    )


def style_input(ws, rng, T: Theme, numfmt=None, align=None):
    paint(ws, rng, f=FILL_INPUT, font=T.font(10), border=CELL_BOX, numfmt=numfmt, align=align or LEFT)


def style_calc(ws, rng, T: Theme, numfmt=None, align=None, color=DARK):
    paint(ws, rng, f=FILL_CALC, font=T.font(10, color=color), border=CELL_BOX, numfmt=numfmt, align=align or LEFT)


def note(ws, T: Theme, cellref: str, text: str, size=9, color=SECONDARY, italic=True):
    ws[cellref] = text
    ws[cellref].font = T.font(size, False, color, italic=italic)
    ws[cellref].alignment = Alignment(vertical="center", wrap_text=False)


# ---------------------------------------------------------------- solid data bars (Excel 2010+ x14 extension)
X14_CF_URI = "{78C0D931-6437-407d-A8EE-F0AAD7539E65}"
X14_ID_URI = "{B025F937-C7B1-47D3-B67F-A62EFF666E3E}"
NS_X14 = "http://schemas.microsoft.com/office/spreadsheetml/2009/9/main"
NS_XM = "http://schemas.microsoft.com/office/excel/2006/main"


def solidify_databars(path):
    """Make every data bar solid in Excel 2010+ (no gradient, no border, full 0-100% length).

    openpyxl writes only the 2007 <dataBar>, which Excel renders as a faded gradient. This adds the standard
    x14 extension (the same XML Excel itself writes). LibreOffice and Google Sheets read the file as before.
    """
    import re
    import shutil
    import tempfile
    import uuid
    import zipfile

    fd, tmp = tempfile.mkstemp(suffix=".xlsx")
    import os
    os.close(fd)
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("xl/worksheets/sheet") and b"dataBar" in data:
                xml = data.decode("utf-8")
                ext_rules = []

                def fix_block(m):
                    sqref, body = m.group(1), m.group(2)

                    def fix_rule(rm):
                        rule = rm.group(0)
                        if 'type="dataBar"' not in rule:
                            return rule
                        gid = "{" + str(uuid.uuid4()).upper() + "}"
                        vals = re.findall(r'<cfvo type="(\w+)"(?: val="([^"]*)")?\s*/>', rule)
                        ext_rules.append((gid, sqref, vals))
                        ext = f'<extLst><ext uri="{X14_ID_URI}" xmlns:x14="{NS_X14}"><x14:id>{gid}</x14:id></ext></extLst>'
                        return rule.replace("</cfRule>", ext + "</cfRule>")

                    body = re.sub(r"<cfRule\b.*?</cfRule>", fix_rule, body, flags=re.S)
                    return f'<conditionalFormatting sqref="{sqref}">{body}</conditionalFormatting>'

                xml = re.sub(r'<conditionalFormatting sqref="([^"]+)">(.*?)</conditionalFormatting>', fix_block, xml, flags=re.S)
                if ext_rules:
                    parts = []
                    for gid, sqref, vals in ext_rules:
                        cfvos = ""
                        for t, v in vals:
                            if t in ("num", "percent", "formula", "percentile"):
                                cfvos += f'<x14:cfvo type="{t}"><xm:f>{v}</xm:f></x14:cfvo>'
                            else:
                                cfvos += f'<x14:cfvo type="{"autoMin" if t == "min" else "autoMax"}"/>'
                        parts.append(
                            f'<x14:conditionalFormatting xmlns:xm="{NS_XM}"><x14:cfRule type="dataBar" id="{gid}">'
                            f'<x14:dataBar minLength="0" maxLength="100" gradient="0">{cfvos}'
                            f'<x14:negativeFillColor rgb="FFDC5B64"/><x14:axisColor rgb="FF9AA5B1"/></x14:dataBar>'
                            f"</x14:cfRule><xm:sqref>{sqref}</xm:sqref></x14:conditionalFormatting>")
                    ext = (f'<extLst><ext uri="{X14_CF_URI}" xmlns:x14="{NS_X14}"><x14:conditionalFormattings>'
                           + "".join(parts) + "</x14:conditionalFormattings></ext></extLst>")
                    xml = xml.replace("</worksheet>", ext + "</worksheet>")
                data = xml.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp, path)


# ---------------------------------------------------------------- Google Sheets: native in-workbook links
def nativize_links(wb):
    """Replace =HYPERLINK("#'Tab'!A1", label) formulas with native cell hyperlinks (text + link to a place in the
    workbook). Excel follows either form; Google Sheets converts native links on import but does not reliably follow
    the "#Tab!A1" formula form, so the Google Sheets editions use native links. Returns the number converted."""
    import re
    from openpyxl.worksheet.hyperlink import Hyperlink
    pat = re.compile(r'^=HYPERLINK\("#([^"]+)",(.*)\)$', re.S)
    n = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if not (isinstance(v, str) and v.startswith("=HYPERLINK(")):
                    continue
                m = pat.match(v)
                if not m:
                    continue
                target, label = m.group(1), m.group(2).strip()
                if re.fullmatch(r'"[^"]*"', label):
                    c.value = label[1:-1]
                else:
                    c.value = "=" + label
                c.hyperlink = Hyperlink(ref=c.coordinate, location=target)
                n += 1
    return n


# ---------------------------------------------------------------- dates as text, the same in every language of Excel
_DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
_DATE_TOKENS = re.compile(r"dddd|ddd|d|mmmm|mmm|yyyy|yy")


def date_text(x: str, fmt: str) -> str:
    """Formula fragment that writes date `x` in `fmt` without TEXT().

    TEXT(date,"mmm d, yyyy") depends on the language of the buyer's Excel: French Excel expects "jj/aaaa", German "TT/JJJJ",
    and prints the letters d and y as they are. DAY, MONTH, YEAR and WEEKDAY are the same everywhere."""
    lst = lambda names, n=None: ",".join(f'"{s[:n] if n else s}"' for s in names)
    piece = {"dddd": f"CHOOSE(WEEKDAY({x}),{lst(_DAYS)})", "ddd": f'MID("{"".join(d[:3] for d in _DAYS)}",WEEKDAY({x})*3-2,3)', "d": f"DAY({x})",
             "mmmm": f"CHOOSE(MONTH({x}),{lst(_MONTHS)})", "mmm": f'MID("{"".join(m[:3] for m in _MONTHS)}",MONTH({x})*3-2,3)',
             "yyyy": f"YEAR({x})", "yy": f"RIGHT(YEAR({x}),2)"}
    parts, pos = [], 0
    for m in _DATE_TOKENS.finditer(fmt):
        if m.start() > pos:
            parts.append(f'"{fmt[pos:m.start()]}"')
        parts.append(piece[m.group()])
        pos = m.end()
    if pos < len(fmt):
        parts.append(f'"{fmt[pos:]}"')
    return "(" + "&".join(parts) + ")"


def _split_text_call(f: str, start: int):
    """f[start:] begins with 'TEXT('. Returns (end index after the closing bracket, [arguments]) or None."""
    i, depth, quote, args, a0 = start + 5, 1, False, [], start + 5
    while i < len(f):
        ch = f[i]
        if ch == '"':
            quote = not quote
        elif not quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    args.append(f[a0:i])
                    return i + 1, args
            elif ch == "," and depth == 1:
                args.append(f[a0:i])
                a0 = i + 1
        i += 1
    return None


def localeproof_dates(wb) -> int:
    """Rewrite every TEXT(date,"<day/month/year format>") in the workbook with date_text(). Returns the number rewritten."""
    n = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                f = cell.value
                if not (isinstance(f, str) and f.startswith("=") and "TEXT(" in f):
                    continue
                pos = 0
                while True:
                    i = f.find("TEXT(", pos)
                    if i < 0:
                        break
                    if i and (f[i - 1].isalnum() or f[i - 1] == "_"):
                        pos = i + 5
                        continue
                    got = _split_text_call(f, i)
                    fmt = got[1][1].strip() if got and len(got[1]) == 2 else ""
                    body = fmt[1:-1]
                    if (fmt[:1] == '"' and fmt[-1:] == '"' and _DATE_TOKENS.search(body)
                            and not re.search(r"[h0#@sA-Z]", _DATE_TOKENS.sub("", body))):
                        f = f[:i] + date_text(got[1][0].strip(), body) + f[got[0]:]
                        n += 1
                        pos = i                      # look again from here: the argument may hold another TEXT()
                    else:
                        pos = i + 5
                cell.value = f
    return n
