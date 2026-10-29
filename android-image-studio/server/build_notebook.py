#!/usr/bin/env python3
"""Regenerates image_studio_server.ipynb, embedding image_studio_server.py in it.

Run after editing the server:  python3 server/build_notebook.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = (HERE / "image_studio_server.py").read_text(encoding="utf-8")

INTRO = """# Image Studio — free GPU server

Runs open image models on this notebook's free GPU and connects them to the **Image Studio** Android app.

**Before you run**
- **Kaggle:** in the right panel set *Accelerator* to **GPU T4 x2** (or P100) and turn **Internet on**
  (Kaggle asks for a verified phone number the first time).
- **Colab:** *Runtime → Change runtime type →* **T4 GPU**.

Then **Run all**. The last-but-one cell prints a QR code: in the app, open **Settings → My server → Scan QR**.
Keep this tab open while you use the app; images stop when the session ends, but the app keeps copies of what you made.

The first run downloads the model (about 7 GB for SDXL-class models), which takes a few minutes."""

CONFIG = """# Models to offer. Each is about a 7 GB download, and only one sits on the GPU at a time.
#   "sdxl-turbo"    – fastest (1–4 steps, 512 px); good for quick ideas
#   "sdxl"          – Stable Diffusion XL base (1024 px, ~25 steps)
#   "juggernaut-xl" – photorealistic SDXL fine-tune (1024 px, ~25 steps)
MODELS = ["sdxl-turbo"]

# Optional: a Hugging Face token, only needed for gated models or to avoid download rate limits.
HF_TOKEN = \"\""""

# diffusers and transformers are pinned as a pair: newer transformers releases break older diffusers.
INSTALL = """%pip install -q diffusers==0.41.0 transformers==5.20.2 accelerate fastapi uvicorn python-multipart "qrcode[pil]"
"""

START = """import os, secrets
os.environ["HF_TOKEN"] = HF_TOKEN
import image_studio_server as studio

engine = studio.Engine(MODELS)
engine.load(MODELS[0])  # download and warm up the first model before going public

TOKEN = secrets.token_urlsafe(24)
studio.start_server(studio.create_app(engine, TOKEN))
URL = studio.start_tunnel()
LINK = studio.connect_link(URL, TOKEN)

import qrcode
from IPython.display import display
print("Scan this in Image Studio → Settings → My server → Scan QR\\n")
display(qrcode.make(LINK).resize((360, 360)))
print("\\nOr paste this into the app's server box:\\n" + LINK)"""

KEEP_ALIVE = """# Keeps the session busy so it is not stopped as idle. Stop this cell to shut the server down.
import time
while True:
    with engine.lock:
        jobs = list(engine.jobs.values())
    done = sum(j["status"] == "completed" for j in jobs)
    waiting = sum(j["status"] in ("queued", "processing") for j in jobs)
    print(f"{time.strftime('%H:%M')}  {done} images made, {waiting} in progress — {URL}", flush=True)
    time.sleep(300)"""


def cell(kind, source):
    lines = source.splitlines(keepends=True)
    c = {"cell_type": kind, "metadata": {}, "source": lines}
    if kind == "code":
        c.update(execution_count=None, outputs=[])
    return c


notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "language_info": {"name": "python"},
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "T4"},
        "kaggle": {"accelerator": "gpu", "isInternetEnabled": True},
    },
    "cells": [
        cell("markdown", INTRO),
        cell("code", CONFIG),
        cell("code", INSTALL),
        cell("code", "%%writefile image_studio_server.py\n" + SERVER),
        cell("code", START),
        cell("code", KEEP_ALIVE),
    ],
}
for i, c in enumerate(notebook["cells"]):
    c["id"] = f"cell-{i}"

out = HERE / "image_studio_server.ipynb"
out.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {out}")
