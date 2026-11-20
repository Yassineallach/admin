"""Structure check for a Brass Ledger workbook: formula count, banned functions, Excel Tables, macros, external links,
sidebar icons, and protection / freeze panes / validations per tab.

Usage: python structure_check.py FILE.xlsx [FILE.xlsx ...]
"""
import re
import sys
import zipfile

from openpyxl import load_workbook

BANNED = re.compile(r"LAMBDA|LET\(|XLOOKUP|FILTER\(|UNIQUE\(|SORT\(|SEQUENCE\(|\[#|TEXT\(|INDIRECT|OFFSET\(|\[\d+\]")


def check(path):
    wb = load_workbook(path)
    forms = [c.value for ws in wb for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=")]
    bad = [f for f in forms if BANNED.search(f)]
    names = zipfile.ZipFile(path).namelist()
    out = [path.split("/")[-1],
           f"  formulas: {len(forms)} | banned functions / structured refs / external links: {len(bad)}",
           f"  Excel Tables: {sum(n.startswith('xl/tables/') for n in names)} | macros: {any('vba' in n.lower() for n in names)} | "
           f"external links: {any('externalLink' in n for n in names)}",
           f"  sidebar icon pictures: {sum(1 for n in names if n.startswith('xl/media/shape_icon'))} | charts: "
           f"{sum(1 for n in names if n.startswith('xl/charts/chart'))}",
           f"  tab order: {[ws.title for ws in wb]}"]
    for ws in wb:
        out.append(f"  {ws.title}: protected={ws.protection.sheet} password={'yes' if ws.protection.password else 'no'} "
                   f"freeze={ws.freeze_panes} validations={len(ws.data_validations.dataValidation)}")
    return "\n".join(out)


if __name__ == "__main__":
    print("\n".join(check(p) for p in sys.argv[1:]))
