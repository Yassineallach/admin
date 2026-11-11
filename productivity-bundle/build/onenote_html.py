"""Render the planner to OneNote-ready HTML (Microsoft Graph "create page" format) + a browsable preview.

Output (dist/02_Ultimate_OneNote_Planner/OneNote_Import/):
  pages/*.html     one file per page; only HTML Microsoft Graph's OneNote API accepts
                   (p, h1–h3, table/tr/td/th, span, a, br; inline styles; data-tag="to-do" checkboxes)
  manifest.json    notebook → section groups → sections → pages, used by onenote_import.py
Links between pages are written as {{LINK:<page key>}}; the importer swaps them for real OneNote page links once
the pages exist. The preview copy (Preview/ folder) swaps them for relative file links so the planner can be browsed.
"""
from __future__ import annotations

import calendar as cal
import html
import json
import re
from pathlib import Path

import planner_content as PC

WIDTH = 940
TEAL_LIGHT, GREY_FILL, LABEL_FILL = "F6EBD3", "FAF7F2", "F1ECE2"   # Brass Ledger: brass tint, paper, calculated
TXT, SUB = "222222", "444444"


def esc(s):
    return html.escape(str(s), quote=False)


def cell(content="&nbsp;", w=None, bg=None, bold=False, color=None, align=None, size=None):
    st = []
    if w:
        st.append(f"width:{w}px")
    if bg:
        st.append(f"background-color:#{bg}")
    if bold:
        st.append("font-weight:bold")
    if color:
        st.append(f"color:#{color}")
    if align:
        st.append(f"text-align:{align}")
    if size:
        st.append(f"font-size:{size}pt")
    return f'<td style="{";".join(st)}">{content}</td>'


def table(rows_html, width=WIDTH):
    return f'<table border="1" style="border-collapse:collapse;width:{width}px">{"".join(rows_html)}</table>'


def render_block(b, width=WIDTH, color="0F6E68"):
    kind = b[0]
    if kind == "h":
        return f'<h3 style="color:#{color};margin-top:12px">{esc(b[1])}</h3>'
    if kind == "note":
        return table([f"<tr>{cell('💡 ' + esc(b[1]), width, 'FEF0E3', color=TXT)}</tr>"], width)
    if kind == "fields":
        labels, cols = b[1], b[2]
        lw = int(width / cols * 0.36)
        aw = int(width / cols - lw)
        rows = []
        for i in range(0, len(labels), cols):
            chunk = labels[i:i + cols]
            tds = "".join(cell(esc(l), lw, LABEL_FILL, True, TXT) + cell("&nbsp;", aw) for l in chunk)
            tds += "".join(cell("", lw) + cell("", aw) for _ in range(cols - len(chunk)))
            rows.append(f"<tr>{tds}</tr>")
        return table(rows, width)
    if kind == "check":
        items = b[1] if isinstance(b[1], list) else [""] * b[1]
        return "".join(f'<p data-tag="to-do">{esc(t) if t else "&nbsp;"}</p>' for t in items)
    if kind == "table":
        headers, rows = b[1], b[2]
        n = len(headers)
        w = int(width / n)
        out = ["<tr>" + "".join(cell(esc(h), w, TEAL_LIGHT, True, TXT) for h in headers) + "</tr>"]
        data = rows if isinstance(rows, list) else [[""] * n for _ in range(rows)]
        for r in data:
            out.append("<tr>" + "".join(cell(esc(v) if v else "&nbsp;", w, bold=(j == 0 and bool(v))) for j, v in enumerate(r)) + "</tr>")
        return table(out, width)
    if kind == "lines":
        return table([f"<tr>{cell('&nbsp;', width)}</tr>" for _ in range(b[1])], width)
    if kind == "scale":
        label, n = b[1], b[2]
        lw = int(width * 0.4)
        w = int((width - lw) / n)
        return table(["<tr>" + cell(esc(label), lw, LABEL_FILL, True, TXT) + "".join(cell(str(i), w, align="center", color=SUB) for i in range(1, n + 1)) + "</tr>"], width)
    if kind == "habit":
        habits, days = b[1], b[2]
        names = habits if isinstance(habits, list) else [""] * habits
        hw = 200 if days <= 7 else 140
        dw = int((width - hw) / days)
        head = [d[:3] for d in PC.DAYS] if days == 7 else [str(i) for i in range(1, days + 1)]
        out = ["<tr>" + cell("Habit", hw, TEAL_LIGHT, True, TXT) + "".join(cell(h, dw, TEAL_LIGHT, True, TXT, "center", 8 if days > 7 else None) for h in head) + "</tr>"]
        for nm in names:
            out.append("<tr>" + cell(esc(nm) or "&nbsp;", hw) + "".join(cell("☐", dw, align="center", color=SUB, size=8 if days > 7 else None) for _ in range(days)) + "</tr>")
        return table(out, width)
    if kind == "calendar":
        y, m = b[1], b[2]
        w = int(width / 7)
        out = ["<tr>" + "".join(cell(d[:3], w, color, True, "FFFFFF", "center") for d in PC.DAYS) + "</tr>"]
        for week in cal.Calendar(firstweekday=0).monthdatescalendar(y, m):
            tds = []
            for d in week:
                inm = d.month == m
                tds.append(cell(f'<span style="font-weight:bold;color:#{TXT if inm else "B8B2A6"}">{d.day}</span><br/>&nbsp;<br/>&nbsp;',
                                w, None if inm else GREY_FILL))
            out.append("<tr>" + "".join(tds) + "</tr>")
        return table(out, width)
    if kind == "yearcal":
        y = b[1]
        mw = int(width / 3)
        rows = []
        for q in range(4):
            tds = []
            for k in range(3):
                m = q * 3 + k + 1
                inner = [f"<tr>{cell('<b>' + PC.MONTHS[m - 1] + '</b>', None, TEAL_LIGHT, color=TXT)}</tr>"]
                txt = "Mo Tu We Th Fr Sa Su<br/>"
                for week in cal.Calendar(0).monthdayscalendar(y, m):
                    txt += " ".join(f"{d:2d}" if d else "  " for d in week).replace(" ", "&nbsp;") + "<br/>"
                inner.append(f"<tr>{cell('<span style=\"font-family:Consolas;font-size:9pt\">' + txt + '</span>')}</tr>")
                tds.append(cell(table(inner, mw - 12), mw))
            rows.append("<tr>" + "".join(tds) + "</tr>")
        return f'<table style="border-collapse:collapse;width:{width}px">{"".join(rows)}</table>'
    if kind == "cols":
        half = int(width / 2) - 10
        left = "".join(render_block(x, half, color) for x in b[1])
        right = "".join(render_block(x, half, color) for x in b[2])
        return (f'<table style="border-collapse:collapse;width:{width}px"><tr><td style="width:{half + 10}px">{left}</td>'
                f'<td style="width:{half + 10}px">{right}</td></tr></table>')
    raise ValueError(kind)


def page_html(p, sec, extra_top=""):
    title = esc(p.title)
    label = (f'<table style="border-collapse:collapse"><tr>{cell(esc(sec.name.upper()), None, sec.color, True, "FFFFFF", size=9)}</tr></table>')
    nav = (f'<p style="font-size:9pt;color:#{SUB}"><a href="{{{{LINK:index}}}}">⌂ Index</a>'
           + (f' &nbsp;·&nbsp; <a href="{{{{LINK:contents_{sec.key}}}}}">{esc(sec.name)} contents</a>' if sec.group in ("Templates", "Weekly", "Notes") else "")
           + "</p>")
    sub = f'<p style="color:#{SUB}">{esc(p.subtitle)}</p>' if p.subtitle else ""
    body = "".join(render_block(b, WIDTH, sec.color) for b in p.blocks)
    return (f'<!DOCTYPE html><html><head><title>{title}</title><meta charset="utf-8"/></head><body>'
            f'{nav}{label}<h1 style="color:#1F3D36;font-family:Georgia">{title}</h1>{sub}{extra_top}{body}</body></html>')


# ---------------------------------------------------------------- index + contents pages
def link(key, text, color=None):
    st = f' style="color:#{color}"' if color else ""
    return f'<a href="{{{{LINK:{key}}}}}"{st}>{esc(text)}</a>'


def index_html(secs, year):
    start = secs[0]
    months = [s for s in secs if s.group == "Months"]
    weekly = next(s for s in secs if s.key == "weekly")
    tpls = [s for s in secs if s.group == "Templates"]
    notes = next(s for s in secs if s.key == "notes")
    rows = []

    def row(label, links_html, color):
        return f"<tr>{cell(esc(label), 220, color, True, 'FFFFFF')}{cell(links_html, 720)}</tr>"
    rows.append(row("Start here", " · ".join(link(p.key, p.title) for p in start.pages), "1F3D36"))
    rows.append(row("Yearly goals", link("year_goals", f"Yearly Goals {year}") + " · " + link("year_glance", "Year at a Glance"), "0F6E68"))
    rows.append(row("Monthly calendars", " · ".join(link(f"m{m}_cal", PC.MONTHS[m - 1][:3]) for m in range(1, 13)), "2E7D4F"))
    rows.append(row("Monthly goals", " · ".join(link(f"m{m}_goals", PC.MONTHS[m - 1][:3]) for m in range(1, 13)), "2E7D4F"))
    rows.append(row("Monthly reflections", " · ".join(link(f"m{m}_refl", PC.MONTHS[m - 1][:3]) for m in range(1, 13)), "2E7D4F"))
    rows.append(row("Weekly trackers", " ".join(link(f"w{w}", f"{w:02d}") for w in range(1, 54)), "2F6FAA"))
    for s in tpls:
        rows.append(row(f"{s.name} ({len(s.pages)})", link(f"contents_{s.key}", "Open contents") + " · " +
                        " · ".join(link(p.key, p.title) for p in s.pages[:4]) + (" …" if len(s.pages) > 4 else ""), s.color))
    rows.append(row("Notes", " · ".join(link(p.key, p.title) for p in notes.pages), notes.color))
    rows.append(row("Resources", link("resources", "Links, contacts & references"), "1F3D36"))
    body = (f'<table style="border-collapse:collapse"><tr>{cell("GENERAL INDEX", None, "1F3D36", True, "FFFFFF", size=9)}</tr></table>'
            f'<h1 style="color:#1F3D36;font-family:Georgia">Ultimate Planner {year}</h1>'
            f'<p style="color:#{SUB}">Click any link to jump straight to that page. Every page has a ⌂ Index link back here.</p>'
            f'<div data-id="links">{table(rows)}</div>')
    return f'<!DOCTYPE html><html><head><title>General Index</title><meta charset="utf-8"/></head><body>{body}</body></html>'


def contents_html(sec):
    rows = ["<tr>" + cell("#", 60, TEAL_LIGHT, True, TXT) + cell("Page", 520, TEAL_LIGHT, True, TXT) + cell("Use it for", 360, TEAL_LIGHT, True, TXT) + "</tr>"]
    for i, p in enumerate(sec.pages, 1):
        first = next((b for b in p.blocks if b[0] in ("h", "note", "fields", "table")), None)
        hint = ""
        if first and first[0] == "note":
            hint = first[1]
        elif first and first[0] == "fields":
            hint = ", ".join(first[1][:3])
        elif first and first[0] == "table":
            hint = ", ".join(first[1][:4])
        elif first and first[0] == "h":
            hint = first[1]
        rows.append("<tr>" + cell(str(i), 60, align="center") + cell(link(p.key, p.title), 520) + cell(esc(hint[:60]), 360, color=SUB) + "</tr>")
    nav = f'<p style="font-size:9pt;color:#{SUB}"><a href="{{{{LINK:index}}}}">⌂ Index</a></p>'
    label = f'<table style="border-collapse:collapse"><tr>{cell(esc(sec.name.upper()), None, sec.color, True, "FFFFFF", size=9)}</tr></table>'
    body = (f'{nav}{label}<h1 style="color:#1F3D36;font-family:Georgia">{esc(sec.name)} — contents</h1>'
            f'<p style="color:#{SUB}">{len(sec.pages)} pages. Click a title to open it.</p><div data-id="links">{table(rows)}</div>')
    return f'<!DOCTYPE html><html><head><title>{esc(sec.name)} — Contents</title><meta charset="utf-8"/></head><body>{body}</body></html>'


# ---------------------------------------------------------------- write
ALLOWED = {"html", "head", "title", "meta", "body", "p", "h1", "h2", "h3", "table", "tr", "td", "th", "span", "a", "br", "b", "div"}


def check_html(s):
    tags = set(t.lower() for t in re.findall(r"<\s*([a-zA-Z0-9]+)", s))
    bad = tags - ALLOWED
    return bad


def write(out_dir: Path, year=PC.YEAR):
    secs = PC.build(year)
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"notebook": f"Ultimate Planner {year}", "year": year, "groups": []}
    files = {}

    def add(key, name, content):
        f = f"{key}.html"
        (pages_dir / f).write_text(content, encoding="utf-8")
        files[key] = f
        bad = check_html(content)
        assert not bad, (key, bad)
        return f

    groups = {}
    for s in secs:
        g = groups.setdefault(s.group, {"name": s.group, "sections": []})
        sec_entry = {"name": s.name, "key": s.key, "color": s.color, "pages": []}
        if s.key == "start":
            sec_entry["pages"].append({"key": "index", "title": "General Index", "file": add("index", "General Index", index_html(secs, year)),
                                       "contents": True})
        if s.group in ("Templates", "Weekly", "Notes"):
            sec_entry["pages"].append({"key": f"contents_{s.key}", "title": f"{s.name} — Contents",
                                       "file": add(f"contents_{s.key}", s.name, contents_html(s)), "contents": True})
        for p in s.pages:
            sec_entry["pages"].append({"key": p.key, "title": p.title, "file": add(p.key, p.title, page_html(p, s)), "contents": False})
        g["sections"].append(sec_entry)
    manifest["groups"] = list(groups.values())
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest, files


def write_preview(import_dir: Path, preview_dir: Path, manifest):
    """Browsable copy: {{LINK:key}} -> key.html, plus a light frame that mimics a OneNote page canvas."""
    preview_dir.mkdir(parents=True, exist_ok=True)
    frame = ('<style>body{font-family:Segoe UI,Arial,sans-serif;font-size:11pt;color:#222222;background:#FAF7F2;margin:0}'
             '.pg{background:#fff;max-width:980px;margin:24px auto;padding:28px 36px;box-shadow:0 6px 24px rgba(11,79,76,.12);border-radius:10px}'
             'td{padding:4px 6px;border:1px solid #E6E1D8;vertical-align:top}table{margin:6px 0}p[data-tag="to-do"]::before{content:"☐ ";color:#A87620}'
             'p[data-tag="to-do"]{margin:3px 0}a{color:#A87620}h1{margin:6px 0}h3{margin:14px 0 4px}</style>')
    for g in manifest["groups"]:
        for s in g["sections"]:
            for p in s["pages"]:
                src = (import_dir / "pages" / p["file"]).read_text(encoding="utf-8")
                src = re.sub(r"\{\{LINK:([a-z0-9_]+)\}\}", r"\1.html", src)
                src = src.replace("<body>", f"<body>{frame}<div class=\"pg\">").replace("</body>", "</div></body>")
                (preview_dir / p["file"]).write_text(src, encoding="utf-8")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent / "dist" / "02_Ultimate_OneNote_Planner"
    man, files = write(root / "OneNote_Import")
    write_preview(root / "OneNote_Import", root / "Preview_HTML", man)
    n = sum(len(s["pages"]) for g in man["groups"] for s in g["sections"])
    print(f"wrote {n} OneNote pages ({len(man['groups'])} groups)")
