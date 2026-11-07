"""Render real screenshots of a workbook's tabs (for Etsy listing images and previews).

Recalculates a copy in LibreOffice, exports it to PDF (each tab's print area), finds the first page of every tab
by its title text, rasterises it and trims the page margins.

Usage: python render_screens.py WORKBOOK.xlsx OUT_DIR [--dpi 200]
Writes OUT_DIR/<Tab_Name>.png for every tab it can find. Requires LibreOffice (soffice), pdftoppm, ImageMagick.
"""
from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader

# text that appears near the top of each tab's first printed page
MARKERS = {
    "All-in-One Dashboard": "Budget vs actual by project",
    "Setup": "SETUP",
    "Monthly Calendar": "MONTHLY CALENDAR",
    "Weekly Calendar": "WEEKLY CALENDAR",
    "Project Overview": "PROJECT OVERVIEW",
    "Project Manager": "PROJECT MANAGER",
    "Project Budget": "PROJECT BUDGET",
    "Variable Tasks": "VARIABLE TASKS",
    "Recurring Tasks": "RECURRING TASKS",
    "Task Schedule": "TASK SCHEDULE",
    "Task Filter": "TASK FILTER",
    "Decision Matrix": "DECISION MATRIX",
    "Kanban Board": "KANBAN BOARD",
    "Gantt Chart": "GANTT CHART",
    "Instructions": "INSTRUCTIONS",
}


def render(xlsx: Path, out: Path, dpi: int = 200, markers=MARKERS):
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    work = tmp / "w.xlsx"
    shutil.copy(xlsx, work)
    rc = (glob.glob("/root/.claude/skills/synced/*/xlsx/scripts/recalc.py") or [None])[0]
    if rc:
        subprocess.run([sys.executable, rc, str(work), "600"], capture_output=True)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(work)], capture_output=True)
    pdf = tmp / "w.pdf"
    reader = PdfReader(str(pdf))
    found = {}
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        for tab, mk in markers.items():
            if tab in found:
                continue
            # upper-case markers are sheet titles: they must open the page (avoids matching body text)
            if text.lstrip().startswith(mk) if mk.isupper() else (mk in text):
                found[tab] = i + 1
    for tab, pg in found.items():
        stem = tmp / tab.replace(" ", "_")
        subprocess.run(["pdftoppm", "-f", str(pg), "-l", str(pg), "-r", str(dpi), "-png", str(pdf), str(stem)],
                       capture_output=True)
        png = sorted(tmp.glob(stem.name + "-*.png"))[0]
        dest = out / f"{tab.replace(' ', '_').replace('-', '')}.png"
        subprocess.run(["convert", str(png), "-trim", "+repage", str(dest)])
        w = int(subprocess.run(["identify", "-format", "%w", str(dest)], capture_output=True, text=True).stdout or 0)
        if w and w < 2200:   # portrait / fit-to-page tabs: re-render sharper
            hi = int(dpi * 2400 / w)
            subprocess.run(["pdftoppm", "-f", str(pg), "-l", str(pg), "-r", str(hi), "-png", str(pdf), str(stem) + "_hi"],
                           capture_output=True)
            png = sorted(tmp.glob(stem.name + "_hi-*.png"))[0]
            subprocess.run(["convert", str(png), "-trim", "+repage", str(dest)])
    return found


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    ap.add_argument("out")
    ap.add_argument("--dpi", type=int, default=200)
    a = ap.parse_args()
    f = render(Path(a.xlsx), Path(a.out), a.dpi)
    print(f"rendered {len(f)} tabs:", ", ".join(f))
