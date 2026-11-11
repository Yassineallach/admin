#!/usr/bin/env python3
"""Create the Ultimate OneNote Planner as a NATIVE OneNote notebook in your Microsoft account (Microsoft Graph).

Run once (seller), then in OneNote for Windows: File › Export › Notebook › OneNote Package (*.onepkg) to get the file
you sell. Buyers can also simply receive a copy of this notebook.

Usage
  python3 onenote_import.py                      # sign in with a device code, build the notebook
  python3 onenote_import.py --dry-run            # show what would be created, no network
  python3 onenote_import.py --token <ACCESS_TOKEN>   # use a token you already have (scope Notes.ReadWrite)

Options
  --folder PATH       folder that holds manifest.json and pages/ (default: next to this script's ../dist output)
  --client-id ID      Azure app (public client) to sign in with. Default: Microsoft Graph Command Line Tools
                      (14d82eec-204b-4c2f-b7e8-296a70dab67e). If your account blocks it, register your own free app
                      (portal.azure.com › App registrations › "Allow public client flows" › API permission Notes.ReadWrite).
  --name NAME         notebook name (default from manifest)
  --links web|client  link style inside the notebook (default: client = onenote: links, best for OneNote desktop)
  --graph URL         Graph base URL (default https://graph.microsoft.com/v1.0; used by the test suite's mock server)

Needs: Python 3.9+. Sign-in needs the `msal` package (pip install msal); --token / --dry-run need nothing extra.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_CLIENT = "14d82eec-204b-4c2f-b7e8-296a70dab67e"


class Graph:
    def __init__(self, base, token, dry=False, pause=0.4):
        self.base, self.token, self.dry, self.pause = base.rstrip("/"), token, dry, pause
        self.calls = 0
        self._n = 0

    def req(self, method, path, body=None, ctype="application/json"):
        self.calls += 1
        if self.dry:
            self._n += 1
            fake = f"dry-{self._n}"
            return {"id": fake, "links": {"oneNoteClientUrl": {"href": f"onenote:#{fake}"}, "oneNoteWebUrl": {"href": f"https://example/{fake}"}}}
        data = body.encode("utf-8") if isinstance(body, str) else (json.dumps(body).encode() if body is not None else None)
        for attempt in range(8):
            r = urllib.request.Request(self.base + path, data=data, method=method,
                                       headers={"Authorization": f"Bearer {self.token}", "Content-Type": ctype})
            try:
                with urllib.request.urlopen(r, timeout=60) as resp:
                    txt = resp.read().decode() or "{}"
                    time.sleep(self.pause)
                    return json.loads(txt) if txt.strip().startswith("{") else {}
            except urllib.error.HTTPError as e:
                if e.code in (429, 502, 503, 504):
                    wait = int(e.headers.get("Retry-After", "0") or 0) or min(60, 2 ** attempt)
                    print(f"  … service busy ({e.code}), waiting {wait}s")
                    time.sleep(wait)
                    continue
                raise SystemExit(f"Graph error {e.code} on {method} {path}: {e.read().decode()[:400]}")
        raise SystemExit(f"Gave up after repeated throttling on {method} {path}")


def sign_in(client_id):
    try:
        import msal
    except ImportError:
        raise SystemExit("Sign-in needs the msal package:  pip install msal   (or pass --token)")
    app = msal.PublicClientApplication(client_id, authority="https://login.microsoftonline.com/common")
    flow = app.initiate_device_flow(scopes=["Notes.ReadWrite"])
    if "user_code" not in flow:
        raise SystemExit(f"Could not start sign-in: {flow}")
    print(flow["message"])
    res = app.acquire_token_by_device_flow(flow)
    if "access_token" not in res:
        raise SystemExit(f"Sign-in failed: {res.get('error_description', res)}")
    return res["access_token"]


def build_notebook(folder: Path, g: Graph, name=None, link_style="client", log=print):
    man = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    nb = g.req("POST", "/me/onenote/notebooks", {"displayName": name or man["notebook"]})
    log(f"notebook: {name or man['notebook']}")
    urls, ids, contents = {}, {}, []
    sections = []
    for grp in man["groups"]:
        single = len(grp["sections"]) == 1 and grp["sections"][0]["name"] in ("Start", "Weekly Tracker", "Notes")
        if single:
            parent = f"/me/onenote/notebooks/{nb['id']}/sections"
        else:
            sg = g.req("POST", f"/me/onenote/notebooks/{nb['id']}/sectionGroups", {"displayName": grp["name"]})
            parent = f"/me/onenote/sectionGroups/{sg['id']}/sections"
        for s in grp["sections"]:
            sec = g.req("POST", parent, {"displayName": s["name"]})
            sections.append((sec["id"], s))
    pick = (lambda r: r["links"]["oneNoteClientUrl"]["href"]) if link_style == "client" else (lambda r: r["links"]["oneNoteWebUrl"]["href"])

    def create(sec_id, p, html_text):
        r = g.req("POST", f"/me/onenote/sections/{sec_id}/pages", html_text, "text/html")
        urls[p["key"]], ids[p["key"]] = pick(r), r["id"]

    # pass 1: index / contents pages first (so they sit at the top of their section) with a placeholder body
    for sec_id, s in sections:
        for p in s["pages"]:
            if p.get("contents"):
                create(sec_id, p, f'<!DOCTYPE html><html><head><title>{p["title"]}</title></head><body>'
                                  f'<div data-id="links"><p>Building links…</p></div></body></html>')
                contents.append(p)
    # pass 2: every other page, links already resolvable for index/contents
    total = sum(1 for _, s in sections for p in s["pages"] if not p.get("contents"))
    done = 0

    def fill(text):
        return re.sub(r"\{\{LINK:([a-z0-9_]+)\}\}", lambda m: urls.get(m.group(1), "#"), text)
    for sec_id, s in sections:
        for p in s["pages"]:
            if p.get("contents"):
                continue
            create(sec_id, p, fill((folder / "pages" / p["file"]).read_text(encoding="utf-8")))
            done += 1
            if done % 25 == 0 or done == total:
                log(f"  pages {done}/{total}")
    # pass 3: write the real links into the index / contents pages
    for p in contents:
        src = (folder / "pages" / p["file"]).read_text(encoding="utf-8")
        m = re.search(r'<div data-id="links">(.*)</div>', src, re.S)
        g.req("PATCH", f"/me/onenote/pages/{ids[p['key']]}/content",
              [{"target": "#links", "action": "replace", "content": f'<div data-id="links">{fill(m.group(1))}</div>'}])
    log(f"done: {len(urls)} pages, {g.calls} API calls")
    return urls


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    here = Path(__file__).resolve().parent
    default_folder = here if (here / "manifest.json").exists() else here.parent / "dist" / "02_Ultimate_OneNote_Planner" / "OneNote_Import"
    ap.add_argument("--folder", default=str(default_folder))
    ap.add_argument("--client-id", default=DEFAULT_CLIENT)
    ap.add_argument("--token")
    ap.add_argument("--name")
    ap.add_argument("--links", choices=("client", "web"), default="client")
    ap.add_argument("--graph", default="https://graph.microsoft.com/v1.0")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pause", type=float, default=0.4)
    a = ap.parse_args(argv)
    token = "dry" if a.dry_run else (a.token or sign_in(a.client_id))
    g = Graph(a.graph, token, dry=a.dry_run, pause=0 if a.dry_run else a.pause)
    build_notebook(Path(a.folder), g, a.name, a.links)


if __name__ == "__main__":
    main()
