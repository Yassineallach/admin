"""End-to-end test of onenote_import.py against a local mock of the Microsoft Graph OneNote API.

The mock implements the endpoints the importer uses (notebooks, sectionGroups, sections, pages, page content PATCH
with data-id targets), checks auth headers and content types, and throttles one request with HTTP 429.
After the run it verifies: structure, page count, no unresolved {{LINK:..}}, every link points at a created page,
index/contents pages received their link tables, and the throttled request was retried.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import onenote_import as OI  # noqa: E402

STATE = {"notebooks": {}, "groups": {}, "sections": {}, "pages": {}, "throttled": 0, "requests": 0, "errors": []}


class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj=None, headers=None):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        body = json.dumps(obj or {}).encode()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n).decode()

    def _new(self, kind, **kw):
        i = str(uuid.uuid4())
        STATE[kind][i] = kw
        return i

    def do_POST(self):
        STATE["requests"] += 1
        if self.headers.get("Authorization") != "Bearer test-token":
            return self._send(401, {"error": "auth"})
        body = self._body()
        p = self.path.replace("/v1.0", "")
        if STATE["requests"] == 40 and STATE["throttled"] == 0:     # throttle once
            STATE["throttled"] += 1
            return self._send(429, {"error": "throttled"}, {"Retry-After": "0"})
        if p == "/me/onenote/notebooks":
            i = self._new("notebooks", name=json.loads(body)["displayName"])
            return self._send(201, {"id": i})
        m = re.match(r"/me/onenote/notebooks/([^/]+)/sectionGroups$", p)
        if m:
            return self._send(201, {"id": self._new("groups", nb=m.group(1), name=json.loads(body)["displayName"])})
        m = re.match(r"/me/onenote/(notebooks|sectionGroups)/([^/]+)/sections$", p)
        if m:
            return self._send(201, {"id": self._new("sections", parent=m.group(2), name=json.loads(body)["displayName"])})
        m = re.match(r"/me/onenote/sections/([^/]+)/pages$", p)
        if m:
            if self.headers.get("Content-Type") != "text/html":
                STATE["errors"].append("page content-type")
            title = re.search(r"<title>(.*?)</title>", body).group(1)
            i = self._new("pages", section=m.group(1), title=title, html=body, order=len(STATE["pages"]))
            return self._send(201, {"id": i, "links": {"oneNoteClientUrl": {"href": f"onenote:#page-{i}"},
                                                       "oneNoteWebUrl": {"href": f"https://onenote.example/{i}"}}})
        self._send(404, {"error": p})

    def do_PATCH(self):
        STATE["requests"] += 1
        m = re.match(r"/v1.0/me/onenote/pages/([^/]+)/content$", self.path)
        if not m or m.group(1) not in STATE["pages"]:
            return self._send(404, {"error": self.path})
        for op in json.loads(self._body()):
            pg = STATE["pages"][m.group(1)]
            assert op["target"] == "#links" and op["action"] == "replace"
            new, n = re.subn(r'<div data-id="links">.*?</div>', op["content"], pg["html"], flags=re.S)
            if n != 1:
                STATE["errors"].append("patch target missing")
            pg["html"] = new
        self.send_response(204)
        self.end_headers()


def run():
    folder = Path(__file__).resolve().parent.parent / "dist" / "02_Ultimate_OneNote_Planner" / "OneNote_Import"
    man = json.loads((folder / "manifest.json").read_text())
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/v1.0"
    OI.main(["--token", "test-token", "--graph", base, "--folder", str(folder), "--pause", "0"])
    srv.shutdown()
    fails = []
    exp_pages = sum(len(s["pages"]) for g in man["groups"] for s in g["sections"])
    exp_sections = sum(len(g["sections"]) for g in man["groups"])
    if len(STATE["notebooks"]) != 1:
        fails.append("notebook count")
    if len(STATE["groups"]) != 2:                       # Months + Templates; Start/Weekly/Notes sit at notebook root
        fails.append(f"section groups {len(STATE['groups'])}")
    if len(STATE["sections"]) != exp_sections:
        fails.append(f"sections {len(STATE['sections'])} != {exp_sections}")
    if len(STATE["pages"]) != exp_pages:
        fails.append(f"pages {len(STATE['pages'])} != {exp_pages}")
    valid = {f"onenote:#page-{i}" for i in STATE["pages"]}
    bad_links = 0
    for i, pg in STATE["pages"].items():
        if "{{LINK" in pg["html"]:
            fails.append(f"unresolved link on {pg['title']}")
        for href in re.findall(r'href="([^"]+)"', pg["html"]):
            if href not in valid:
                bad_links += 1
    if bad_links:
        fails.append(f"{bad_links} links point to pages that don't exist")
    idx = next(p for p in STATE["pages"].values() if p["title"] == "General Index")
    n_idx_links = len(re.findall(r'href="onenote:', idx["html"]))
    if n_idx_links < 100:
        fails.append(f"index has only {n_idx_links} links")
    by_section = {}
    for p in STATE["pages"].values():
        by_section.setdefault(p["section"], []).append(p)
    for sec, pages in by_section.items():
        first = min(pages, key=lambda p: p["order"])
        sname = STATE["sections"][sec]["name"]
        if sname in ("Start",) and first["title"] != "General Index":
            fails.append("index not first in Start")
        if any(p["title"].endswith("— Contents") for p in pages) and not first["title"].endswith("— Contents"):
            fails.append(f"contents not first in {sname}")
    if STATE["throttled"] != 1:
        fails.append("throttle path not exercised")
    fails += STATE["errors"]
    total_links = sum(len(re.findall(r'href="onenote:', p["html"])) for p in STATE["pages"].values())
    print(f"mock Graph: {len(STATE['notebooks'])} notebook, {len(STATE['groups'])} section groups, "
          f"{len(STATE['sections'])} sections, {len(STATE['pages'])} pages, {total_links} links, 1 throttled request retried")
    print("RESULT:", "PASS" if not fails else "FAIL")
    for f in fails:
        print("  FAIL", f)
    return not fails


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
