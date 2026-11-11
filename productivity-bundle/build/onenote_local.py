"""Build the OneNote planner WITHOUT a Microsoft account: OneNote page XML + a PowerShell script for OneNote desktop.

OneNote for Windows (the desktop app) has a built-in programming interface (COM) that works offline on notebooks saved
on the computer. This script converts the 225 planner pages (dist/.../OneNote_Import/pages/*.html) into OneNote's own
page XML (2013 schema) and writes a PowerShell script that, on the seller's Windows PC:
  1. creates a local notebook, its section groups and sections,
  2. creates every page and asks OneNote for each page's link,
  3. fills every page with its content, with links between pages resolved.
Then: File › Export › Notebook › OneNote Package (*.onepkg).

Usage: python onenote_local.py          -> dist/02_Ultimate_OneNote_Planner/OneNote_Local/
Run onenote_html.py first (it writes the HTML pages and manifest this reads).
"""
from __future__ import annotations

import html
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "dist" / "02_Ultimate_OneNote_Planner" / "OneNote_Import"
OUT = ROOT / "dist" / "02_Ultimate_OneNote_Planner" / "OneNote_Local"
NS = "http://schemas.microsoft.com/office/onenote/2013/onenote"
PX = 0.75                      # CSS px -> points
GREEN, BRASS_DARK = "#1F3D36", "#A87620"
VOID = {"br", "meta"}
BAD_NAME = re.compile(r'[\\/:*?"<>|#]')


# ------------------------------------------------------------------ tiny HTML tree
class Node:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.parent, self.kids = tag, dict(attrs or {}), parent, []

    def style(self):
        out = {}
        for part in self.attrs.get("style", "").split(";"):
            if ":" in part:
                k, v = part.split(":", 1)
                out[k.strip().lower()] = v.strip()
        return out


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.kids.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.kids.append(data)


def parse(text):
    t = Tree()
    t.feed(text)
    return t.root


def find(node, tag):
    for k in node.kids:
        if isinstance(k, Node):
            if k.tag == tag:
                return k
            r = find(k, tag)
            if r:
                return r
    return None


def text_of(node):
    return "".join(k if isinstance(k, str) else text_of(k) for k in node.kids)


# ------------------------------------------------------------------ inline content -> OneNote T (HTML inside CDATA)
def span_style(st):
    keep = []
    if st.get("font-weight") == "bold":
        keep.append("font-weight:bold")
    if "color" in st:
        keep.append(f"color:{st['color']}")
    if "font-size" in st:
        keep.append(f"font-size:{st['font-size']}")
    if "font-family" in st:
        keep.append(f"font-family:{st['font-family']}")
    return ";".join(keep)


def inline_lines(node, outer=""):
    """Inline HTML of a node, split into lines at <br>. Returns list of HTML strings."""
    lines, cur = [], []

    def walk(n, style):
        for k in n.kids:
            if isinstance(k, str):
                t = html.escape(k.replace("\xa0", " "), quote=False)
                cur.append(f"<span style='{style}'>{t}</span>" if style and t.strip() else t)
            elif k.tag == "br":
                lines.append("".join(cur))
                cur.clear()
            elif k.tag == "a":
                href = k.attrs.get("href", "")
                cur.append(f'<a href="{html.escape(href)}">{html.escape(text_of(k), quote=False)}</a>')
            elif k.tag == "b":
                walk(k, ";".join(x for x in (style, "font-weight:bold") if x))
            elif k.tag == "span":
                s2 = span_style(k.style())
                walk(k, ";".join(x for x in (style, s2) if x))
            else:
                walk(k, style)
    walk(node, outer)
    lines.append("".join(cur))
    return lines


def T(htmltext):
    return f"<one:T><![CDATA[{htmltext}]]></one:T>"


def oe(htmltext, align=None, tag=False):
    a = f' alignment="{align}"' if align in ("center", "right") else ""
    t = '<one:Tag index="0" completed="false" disabled="false"/>' if tag else ""
    return f"<one:OE{a}>{t}{T(htmltext)}</one:OE>"


# ------------------------------------------------------------------ blocks -> OE list
BLOCK = {"p", "h1", "h3", "table", "div"}


def blocks(node):
    """OneNote OE elements for the block children of node."""
    out = []
    for k in node.kids:
        if isinstance(k, str):
            if k.strip():
                out.append(oe(html.escape(k.strip(), quote=False)))
            continue
        if k.tag in ("div", "body", "html", "tbody"):
            out += blocks(k)
        elif k.tag == "h1":
            continue                                 # becomes the page title
        elif k.tag == "h3":
            col = k.style().get("color", BRASS_DARK)
            out.append(oe(f"<span style='font-weight:bold;font-size:13pt;color:{col}'>{html.escape(text_of(k).strip(), quote=False)}</span>"))
        elif k.tag == "p":
            todo = k.attrs.get("data-tag") == "to-do"
            st = span_style(k.style())
            for ln in inline_lines(k, st):
                out.append(oe(ln if ln.strip() else "", tag=todo))
        elif k.tag == "table":
            out.append(f"<one:OE>{table(k)}</one:OE>")
        elif k.tag in ("head", "title", "meta"):
            continue
        else:
            for ln in inline_lines(k):
                out.append(oe(ln))
    return out


def table(tnode):
    rows = [r for r in iter_rows(tnode)]
    ncol = max((len(r) for r in rows), default=1)
    widest = max(rows, key=len) if rows else []
    total = float(tnode.style().get("width", "940px").rstrip("px") or 940)
    widths = []
    for i in range(ncol):
        w = None
        if i < len(widest):
            ws = widest[i].style().get("width", "")
            if ws.endswith("px"):
                w = float(ws[:-2])
        widths.append(w or total / ncol)
    borders = "true" if "border" in tnode.attrs else "false"
    cols = "".join(f'<one:Column index="{i}" width="{max(20.0, w * PX):.1f}" isLocked="true"/>' for i, w in enumerate(widths))
    body = []
    for r in rows:
        cells = []
        for c in r + [None] * (ncol - len(r)):
            if c is None:
                cells.append(f"<one:Cell><one:OEChildren>{oe('')}</one:OEChildren></one:Cell>")
                continue
            st = c.style()
            shade = f' shadingColor="{st["background-color"]}"' if "background-color" in st else ""
            has_block = any(isinstance(k, Node) and k.tag in BLOCK for k in c.kids)
            if has_block:
                inner = blocks(c) or [oe("")]
            else:
                inner = [oe(ln, st.get("text-align")) for ln in inline_lines(c, span_style(st))]
            cells.append(f"<one:Cell{shade}><one:OEChildren>{''.join(inner)}</one:OEChildren></one:Cell>")
        body.append(f"<one:Row>{''.join(cells)}</one:Row>")
    return f'<one:Table bordersVisible="{borders}" hasHeaderRow="false"><one:Columns>{cols}</one:Columns>{"".join(body)}</one:Table>'


def iter_rows(tnode):
    for k in tnode.kids:
        if isinstance(k, Node):
            if k.tag == "tr":
                yield [c for c in k.kids if isinstance(c, Node) and c.tag == "td"]
            elif k.tag in ("tbody", "thead"):
                yield from iter_rows(k)


# ------------------------------------------------------------------ one page
def page_xml(src_html, fallback_title):
    root = parse(src_html)
    h1 = find(root, "h1")
    title = text_of(h1).strip() if h1 else fallback_title
    body = find(root, "body") or root
    content = "".join(blocks(body))
    return (f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<one:Page xmlns:one="{NS}" ID="__PAGEID__">'
            f'<one:TagDef index="0" type="0" symbol="3" fontColor="automatic" highlightColor="none" name="To Do"/>'
            f'<one:QuickStyleDef index="0" name="PageTitle" fontColor="{GREEN}" highlightColor="automatic" font="Georgia" fontSize="22.0" '
            f'spaceBefore="0.0" spaceAfter="0.0"/>'
            f'<one:Title><one:OE quickStyleIndex="0">{T(html.escape(title, quote=False))}</one:OE></one:Title>'
            f'<one:Outline><one:Position x="36.0" y="86.0" z="0"/><one:Size width="720.0" height="40.0" isSetByUser="true"/>'
            f'<one:OEChildren>{content}</one:OEChildren></one:Outline>'
            f'</one:Page>')


def safe(name):
    return BAD_NAME.sub("-", name).strip()


PS1 = r'''# Brass Ledger - builds the OneNote planner in OneNote for Windows, with no Microsoft account.
# Run:  powershell -ExecutionPolicy Bypass -File .\build_onenote_local.ps1          (full planner)
#       powershell -ExecutionPolicy Bypass -File .\build_onenote_local.ps1 -Test    (8 pages, to check first)
param([switch]$Test, [string]$Name = "__NAME__", [string]$Folder = "C:\Brass Ledger")
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$plan = Get-Content -Raw -Encoding UTF8 (Join-Path $here "plan.json") | ConvertFrom-Json
try { $on = New-Object -ComObject OneNote.Application }
catch { Write-Host "Could not start OneNote. Open OneNote (the desktop app) once, close it, and run this again." -ForegroundColor Red; exit 1 }

if ($Test) { $Name = "Planner Test" }
try { New-Item -ItemType Directory -Force -Path $Folder | Out-Null }
catch { $Folder = Join-Path $here "Notebooks"; New-Item -ItemType Directory -Force -Path $Folder | Out-Null }
$path = Join-Path $Folder $Name
$n = 2
while (Test-Path $path) { $path = Join-Path $Folder "$Name ($n)"; $n++ }

Write-Host "Keep OneNote on a normal page while this runs: no File menu, no dialog boxes open." -ForegroundColor Cyan
$nb = ""
$on.OpenHierarchy($path, "", [ref]$nb, 1)
Write-Host "Notebook created: $path"

# pass 1: sections and empty pages, collect each page's link
$ids = @{}; $links = @{}; $pages = @()
foreach ($g in $plan.groups) {
    if ($Test -and $g.name -ne "Start" -and $g.name -ne "Weekly") { continue }
    if ($g.single) { $parent = $nb }
    else { $gid = ""; $on.OpenHierarchy($g.name, $nb, [ref]$gid, 2); $parent = $gid }
    foreach ($s in $g.sections) {
        $sid = ""
        $on.OpenHierarchy("$($s.file).one", $parent, [ref]$sid, 3)
        $count = 0
        foreach ($p in $s.pages) {
            if ($Test -and $count -ge 4) { break }
            $pageId = ""
            $on.CreateNewPage($sid, [ref]$pageId, 0)
            $link = ""
            $on.GetHyperlinkToObject($pageId, "", [ref]$link)
            $ids[$p.key] = $pageId; $links[$p.key] = $link; $pages += $p
            $count++
        }
    }
    Write-Host "  created $($g.name)"
}

# pass 2: page content, links filled in
$eval = [System.Text.RegularExpressions.MatchEvaluator] {
    param($m)
    $k = $m.Groups[1].Value
    if ($links.ContainsKey($k)) { $links[$k].Replace("&", "&amp;").Replace('"', "&quot;") } elseif ($links.ContainsKey("index")) { $links["index"].Replace("&", "&amp;").Replace('"', "&quot;") } else { "#" }
}
$fail = @(); $done = 0
$logDir = Join-Path $here "failed_pages"
foreach ($p in $pages) {
    $xml = Get-Content -Raw -Encoding UTF8 (Join-Path $here ("pages\" + $p.file))
    $xml = $xml.Replace("__PAGEID__", $ids[$p.key])
    $xml = [regex]::Replace($xml, '\{\{LINK:([a-z0-9_]+)\}\}', $eval)
    $ok = $false
    for ($try = 1; $try -le 60 -and -not $ok; $try++) {
        try { $on.UpdatePageContent($xml); $ok = $true }
        catch {
            if ($_.Exception.Message -notmatch "80042030") { break }
            if ($try -eq 1) { Write-Host "  OneNote is busy with a menu or dialog box. Click back on a normal page in OneNote (close the File menu or any open window)..." -ForegroundColor Yellow }
            Start-Sleep -Seconds 2
        }
    }
    if (-not $ok) {
      try { $on.UpdatePageContent($xml) }
      catch {
        $fail += $p.key
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
        Set-Content -Encoding UTF8 -Path (Join-Path $logDir ($p.key + ".xml")) -Value $xml
        Add-Content -Encoding UTF8 -Path (Join-Path $logDir "errors.txt") -Value ("$($p.key): " + $_.Exception.Message)
    }
    }
    $done++
    if ($done % 25 -eq 0 -or $done -eq $pages.Count) { Write-Host "  pages $done / $($pages.Count)" }
}

$on.NavigateTo($ids["index"])
if ($fail.Count) { Write-Host "Finished with $($fail.Count) page(s) that OneNote did not accept: $($fail -join ', '). Details in failed_pages\errors.txt" -ForegroundColor Yellow }
else { Write-Host "Done. $($pages.Count) pages. Check the notebook, then File > Export > Notebook > OneNote Package (*.onepkg)." -ForegroundColor Green }
'''
DIAG = r"""# Brass Ledger - finds which page element OneNote rejects. Run:  powershell -ExecutionPolicy Bypass -File .\diagnose.ps1
$ErrorActionPreference = "Stop"
$on = New-Object -ComObject OneNote.Application
$folder = "C:\Brass Ledger"; New-Item -ItemType Directory -Force -Path $folder | Out-Null
$path = Join-Path $folder "Diagnose"; $n = 2
while (Test-Path $path) { $path = Join-Path $folder "Diagnose ($n)"; $n++ }
$nb = ""; $on.OpenHierarchy($path, "", [ref]$nb, 1)
$sid = ""; $on.OpenHierarchy("Tests.one", $nb, [ref]$sid, 3)
$ns = 'xmlns:one="http://schemas.microsoft.com/office/onenote/2013/onenote"'
$title = '<one:Title><one:OE><one:T><![CDATA[Test]]></one:T></one:OE></one:Title>'
function Body($inner) { return "<one:Outline><one:OEChildren>$inner</one:OEChildren></one:Outline>" }
$tests = [ordered]@{
  "01 title only"          = "$title"
  "02 xml declaration"     = "DECL$title"
  "03 paragraph"           = $title + (Body '<one:OE><one:T><![CDATA[Hello]]></one:T></one:OE>')
  "04 coloured text"       = $title + (Body "<one:OE><one:T><![CDATA[<span style='font-weight:bold;color:#A87620'>Hi</span>]]></one:T></one:OE>")
  "05 position and size"   = $title + '<one:Outline><one:Position x="36.0" y="86.0" z="0"/><one:Size width="720.0" height="40.0" isSetByUser="true"/><one:OEChildren><one:OE><one:T><![CDATA[x]]></one:T></one:OE></one:OEChildren></one:Outline>'
  "06 alignment"           = $title + (Body '<one:OE alignment="center"><one:T><![CDATA[x]]></one:T></one:OE>')
  "07 to-do tag"           = '<one:TagDef index="0" type="0" symbol="3" fontColor="automatic" highlightColor="none" name="To Do"/>' + $title + (Body '<one:OE><one:Tag index="0" completed="false" disabled="false"/><one:T><![CDATA[x]]></one:T></one:OE>')
  "08 title style"         = '<one:QuickStyleDef index="0" name="PageTitle" fontColor="#1F3D36" highlightColor="automatic" font="Georgia" fontSize="22.0" spaceBefore="0.0" spaceAfter="0.0"/><one:Title><one:OE quickStyleIndex="0"><one:T><![CDATA[Test]]></one:T></one:OE></one:Title>'
  "09 table"               = $title + (Body '<one:OE><one:Table bordersVisible="true"><one:Columns><one:Column index="0" width="200.0"/></one:Columns><one:Row><one:Cell><one:OEChildren><one:OE><one:T><![CDATA[x]]></one:T></one:OE></one:OEChildren></one:Cell></one:Row></one:Table></one:OE>')
  "10 table locked+header" = $title + (Body '<one:OE><one:Table bordersVisible="true" hasHeaderRow="false"><one:Columns><one:Column index="0" width="200.0" isLocked="true"/></one:Columns><one:Row><one:Cell><one:OEChildren><one:OE><one:T><![CDATA[x]]></one:T></one:OE></one:OEChildren></one:Cell></one:Row></one:Table></one:OE>')
  "11 shaded cell"         = $title + (Body '<one:OE><one:Table bordersVisible="true"><one:Columns><one:Column index="0" width="200.0"/></one:Columns><one:Row><one:Cell shadingColor="#F1ECE2"><one:OEChildren><one:OE><one:T><![CDATA[x]]></one:T></one:OE></one:OEChildren></one:Cell></one:Row></one:Table></one:OE>')
  "12 link"                = $title + (Body '<one:OE><one:T><![CDATA[<a href="https://example.com">link</a>]]></one:T></one:OE>')
  "13 empty text"          = $title + (Body '<one:OE><one:T><![CDATA[]]></one:T></one:OE>')
  "14 symbols"             = $title + (Body '<one:OE><one:T><![CDATA[⌂ Index · – 💡]]></one:T></one:OE>')
}
foreach ($k in $tests.Keys) {
  $pid2 = ""; $on.CreateNewPage($sid, [ref]$pid2, 0)
  $x = "<one:Page $ns ID=`"$pid2`">" + $tests[$k] + "</one:Page>"
  if ($x.Contains("DECL")) { $x = '<?xml version="1.0" encoding="utf-8"?>' + "`n" + $x.Replace("DECL", "") }
  try { $on.UpdatePageContent($x); Write-Host "OK    $k" -ForegroundColor Green }
  catch { Write-Host "FAIL  $k  ->  $($_.Exception.Message)" -ForegroundColor Red }
}
Write-Host "OneNote version: $((Get-Item (Get-Process onenote -ErrorAction SilentlyContinue | Select-Object -First 1).Path -ErrorAction SilentlyContinue).VersionInfo.ProductVersion)"
"""


README = """BRASS LEDGER - OneNote planner without a Microsoft account
=============================================================

Needs: Windows and the OneNote desktop app (the one with File > Export). No account, no internet.

1. Close OneNote.
2. Open PowerShell in this folder (Shift + right-click the folder > Open in Terminal / PowerShell).
3. Try a small test first (8 pages, about 20 seconds):
       powershell -ExecutionPolicy Bypass -File .\\build_onenote_local.ps1 -Test
   OneNote opens a notebook called "Planner Test". Check the General Index and that its links open pages.
   Then close that notebook (right-click it > Close This Notebook).
4. Build the full planner (225 pages, a few minutes):
       powershell -ExecutionPolicy Bypass -File .\\build_onenote_local.ps1
   The notebook is saved in C:\\Brass Ledger\\Ultimate Planner 2027.
5. In OneNote: File > Export > Notebook > OneNote Package (*.onepkg) > save as Ultimate_Planner_2027.onepkg
6. Test the file: double-click the .onepkg, save the copy under another name, open it and click several index links.

If a page fails, the script says which and writes the details to failed_pages\\errors.txt. Send that file back.
"""


def main():
    man = json.loads((SRC / "manifest.json").read_text(encoding="utf-8"))
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "pages").mkdir(parents=True)
    groups, n = [], 0
    for g in man["groups"]:
        single = len(g["sections"]) == 1 and g["sections"][0]["name"] in ("Start", "Weekly Tracker", "Notes")
        secs = []
        for s in g["sections"]:
            pages = sorted(s["pages"], key=lambda p: not p.get("contents"))          # contents page first
            for p in pages:
                xml = page_xml((SRC / "pages" / p["file"]).read_text(encoding="utf-8"), p["title"])
                ET.fromstring(xml.split("\n", 1)[1].replace("__PAGEID__", "x"))           # must be well-formed XML
                (OUT / "pages" / (p["key"] + ".xml")).write_text(xml, encoding="utf-8")
                n += 1
            secs.append({"name": s["name"], "file": safe(s["name"]), "pages": [{"key": p["key"], "title": p["title"], "file": p["key"] + ".xml"} for p in pages]})
        groups.append({"name": safe(g["name"]), "single": single, "sections": secs})
    (OUT / "plan.json").write_text(json.dumps({"notebook": man["notebook"], "groups": groups}, indent=1, ensure_ascii=False), encoding="utf-8")
    (OUT / "build_onenote_local.ps1").write_text(PS1.replace("__NAME__", man["notebook"]), encoding="utf-8-sig")
    (OUT / "README.txt").write_text(README, encoding="utf-8")
    (OUT / "diagnose.ps1").write_text(DIAG, encoding="utf-8-sig")
    print(f"wrote {n} OneNote pages to {OUT}")


if __name__ == "__main__":
    main()
