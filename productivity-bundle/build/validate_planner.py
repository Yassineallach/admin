"""QA for PRODUCT 2 — Ultimate OneNote Planner. Exits non-zero on any failure.

Checks
  1. Content matches the spec: 12 months × (calendar, goals, reflection), 53 weekly pages, 111 templates with the
     exact per-category counts, 8 note templates, yearly goals + index + resources.
  2. Weekly pages carry the right ISO-week dates; monthly calendars have the right days.
  3. OneNote HTML: only tags Microsoft Graph accepts; every {{LINK:..}} target exists; every page links to the index.
  4. PDF: exactly one PDF page per planner page (+ cover/index/contents), every link resolves to a page,
     every page is reachable, page count reported.
  5. Importer end-to-end against the mock Graph server (test_onenote_import.py).
"""
from __future__ import annotations

import calendar as cal
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import onenote_html as OH  # noqa: E402
import planner_content as PC  # noqa: E402
import planner_pdf as PP  # noqa: E402

DIST = HERE.parent / "dist" / "02_Ultimate_OneNote_Planner"
fails, passes = [], 0


def check(label, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(f"{label} {detail}")


def main():
    secs = PC.build(PC.YEAR)
    by = {s.name: s for s in secs}
    # 1 — spec counts
    for name, n in PC.EXPECTED.items():
        check(f"template count {name}", len(by[name].pages) == n, f"{len(by[name].pages)} != {n}")
    check("111 templates", sum(PC.EXPECTED.values()) == 111)
    months = [s for s in secs if s.group == "Months"]
    check("12 monthly sections", len(months) == 12)
    for s in months:
        check(f"{s.name} has calendar/goals/reflection", [p.subtitle for p in s.pages] == ["Monthly calendar", "Monthly goals", "Monthly reflection"])
    check("53 weekly pages", len(by["Weekly Tracker"].pages) == 53)
    check("8 note templates", len(by["Notes"].pages) == 8)
    check("note names", [p.title for p in by["Notes"].pages] == ["General Notes", "Quick Notes", "Research Notes", "Meeting Notes",
                                                                 "Reading Notes", "Project Notes", "Ideas & Brainstorming", "Personal Reflection"])
    start_titles = [p.title for p in secs[0].pages]
    check("yearly goals page", any(t.startswith("Yearly Goals") for t in start_titles))
    check("resources page", "Resources" in start_titles)
    # every template has structured content (not just a heading)
    for s in secs:
        for p in s.pages:
            def flat(blocks):
                for b in blocks:
                    if b[0] == "cols":
                        yield from flat(b[1])
                        yield from flat(b[2])
                    else:
                        yield b
            fb = list(flat(p.blocks))
            kinds = {b[0] for b in fb}
            structured = bool(kinds & {"fields", "table", "check", "calendar", "habit", "yearcal"}) or \
                (sum(1 for b in fb if b[0] == "h") >= 2 and "lines" in kinds)          # labelled writing boxes (e.g. SWOT)
            check(f"{p.title} has fields/tables/checklists", structured)
    # 2 — dates
    for w, p in enumerate(by["Weekly Tracker"].pages, 1):
        last = dt.date(PC.YEAR, 12, 28).isocalendar()[1]
        if w <= last:
            mon = dt.date.fromisocalendar(PC.YEAR, w, 1)
            rows = next(b for b in p.blocks if b[0] == "table")[2]
            check(f"week {w} monday", rows[0][0] == f"Monday {mon.day}")
            check(f"week {w} sunday", rows[6][0] == f"Sunday {(mon + dt.timedelta(days=6)).day}")
        else:
            check(f"week {w} spare", "Spare" in p.subtitle)
    for m, s in enumerate(months, 1):
        b = s.pages[0].blocks[0]
        check(f"{s.name} calendar block", b == ("calendar", PC.YEAR, m))
    # 3 — OneNote HTML
    out = DIST / "OneNote_Import"
    man, files = OH.write(out)
    keys = {p["key"] for g in man["groups"] for s in g["sections"] for p in s["pages"]}
    for f in (out / "pages").glob("*.html"):
        txt = f.read_text(encoding="utf-8")
        check(f"{f.name} allowed tags", not OH.check_html(txt), str(OH.check_html(txt)))
        for k in re.findall(r"\{\{LINK:([a-z0-9_]+)\}\}", txt):
            check(f"{f.name} link {k}", k in keys)
        if f.stem != "index":
            check(f"{f.name} links to index", "{{LINK:index}}" in txt)
        for td in re.findall(r"data-tag=\"([^\"]+)\"", txt):
            check(f"{f.name} tag {td}", td == "to-do")
    total_pages = len(keys)
    check("OneNote page total", total_pages == 212 + 1 + 12, str(total_pages))
    # 4 — PDF
    pdf = Path(tempfile.mkdtemp()) / "p.pdf"
    PP.MARKS.clear()
    PP.build_pdf(pdf)
    r = PdfReader(str(pdf))
    n = len(r.pages)
    order = sorted(PP.MARKS.items(), key=lambda x: x[1])
    for i, (k, pg) in enumerate(order):
        nxt = order[i + 1][1] if i + 1 < len(order) else n + 1
        check(f"pdf {k} fits on one page", nxt - pg == 1, f"spans {nxt - pg}")
    check("pdf page count", n == 2 + 12 + 212, str(n))
    pages = {p.indirect_reference.idnum: i for i, p in enumerate(r.pages)}
    targets, links, broken = set(), 0, 0
    for p in r.pages:
        for an in p.get("/Annots") or []:
            a = an.get_object()
            if a.get("/Subtype") != "/Link":
                continue
            links += 1
            d = a.get("/Dest")
            if d is None or d[0].idnum not in pages:
                broken += 1
            else:
                targets.add(pages[d[0].idnum])
    check("pdf links resolve", broken == 0, f"{broken} broken")
    check("pdf pages reachable", len(targets) >= n - 1, f"{len(targets)} of {n}")
    compact = [k for k, (f, _) in PP.FIT_LOG.items() if f < 1]
    print(f"  PDF: {n} pages, {links} links, {len(compact)} pages compacted (min {min(f for f, _ in PP.FIT_LOG.values()):.2f})")
    # 5 — importer against mock Graph
    res = subprocess.run([sys.executable, str(HERE / "test_onenote_import.py")], capture_output=True, text=True)
    check("importer mock test", "RESULT: PASS" in res.stdout, res.stdout[-300:])
    print(f"  {[l for l in res.stdout.splitlines() if l.startswith('mock Graph')][0]}")
    print(f"PASSED {passes} checks, FAILED {len(fails)}")
    for f in fails[:40]:
        print("  FAIL", f)
    return not fails


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
