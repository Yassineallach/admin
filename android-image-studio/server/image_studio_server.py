"""Image Studio server: runs open image models on a free Kaggle or Colab GPU.

It speaks the part of the MuAPI protocol the Android app already uses, so the app only needs a
different base URL and key:

    POST /api/v1/{endpoint}                  submit a job        -> {"request_id": ...}
    GET  /api/v1/predictions/{id}/result     poll a job          -> {"status": ..., "outputs": [...]}
    POST /api/v1/upload_file                 upload a reference  -> {"url": "/uploads/..."}
    GET  /api/v1/models                      the models this server offers, in the app's catalog format

Every /api route needs the access token in an x-api-key header. Generated images are served
from /outputs/ under unguessable names so the app's image loader can fetch them directly.
"""
from __future__ import annotations

import io
import math
import os
import queue
import re
import secrets
import shutil
import subprocess
import threading
import time
import traceback
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote

import torch
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image

DATA = Path(os.environ.get("IMAGE_STUDIO_DATA", "/tmp/image-studio"))
OUTPUTS = DATA / "outputs"
UPLOADS = DATA / "uploads"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Output sizes per aspect ratio. SDXL Turbo is trained at 512 px, SDXL at 1024 px.
TURBO_SIZES = {"1:1": (512, 512), "3:4": (448, 576), "4:3": (576, 448), "9:16": (384, 640), "16:9": (640, 384)}
XL_SIZES = {"1:1": (1024, 1024), "3:4": (896, 1152), "4:3": (1152, 896), "9:16": (768, 1344), "16:9": (1344, 768)}

# Models the notebook can enable. Each SDXL-class model is a ~7 GB download on first use.
MODELS = {
    "sdxl-turbo": {"name": "SDXL Turbo", "repo": "stabilityai/sdxl-turbo", "family": "turbo"},
    "sdxl": {"name": "Stable Diffusion XL", "repo": "stabilityai/stable-diffusion-xl-base-1.0", "family": "xl"},
    "juggernaut-xl": {"name": "Juggernaut XL v9", "repo": "RunDiffusion/Juggernaut-XL-v9", "family": "xl"},
}


def _int(name, title, lo, hi, default=None):
    p = {"name": name, "title": title, "kind": "int", "min": lo, "max": hi, "step": 1}
    if default is not None:
        p["default"] = default
    return p


def _float(name, title, lo, hi, default, step):
    return {"name": name, "title": title, "kind": "float", "min": lo, "max": hi, "step": step, "default": default}


def catalog(model_ids) -> list[dict]:
    """The app's models.json format: one text-to-image and one image-to-image entry per model."""
    entries = []
    for model_id in model_ids:
        info = MODELS[model_id]
        turbo = info["family"] == "turbo"
        sizes = TURBO_SIZES if turbo else XL_SIZES
        ratio = {"name": "aspect_ratio", "title": "Aspect Ratio", "kind": "enum", "values": list(sizes), "default": "1:1"}
        seed = _int("seed", "Seed", 0, 2**31 - 1)
        if turbo:
            steps = _int("num_inference_steps", "Steps", 1, 4, 2)
            tuning = []
        else:
            steps = _int("num_inference_steps", "Steps", 10, 50, 25)
            tuning = [
                {"name": "negative_prompt", "title": "Negative prompt", "kind": "text"},
                _float("guidance_scale", "Guidance", 1.0, 12.0, 6.0, 0.5),
            ]
        common = {"provider": "Your GPU", "hasPrompt": True}
        entries.append({
            "id": model_id, "name": info["name"], "endpoint": model_id, "mode": "t2i", **common,
            "params": [ratio, steps, *tuning, _int("num_images", "Number of images", 1, 4 if turbo else 2, 1), seed],
        })
        entries.append({
            "id": f"{model_id}-edit", "name": f"{info['name']} (edit)", "endpoint": f"{model_id}-edit",
            "mode": "i2i", **common, "imageField": "image_url", "maxImages": 1,
            "params": [_float("strength", "Strength", 0.1, 1.0, 0.5 if turbo else 0.6, 0.05), steps, *tuning, seed],
        })
    return entries


class Engine:
    """Keeps one model on the GPU at a time and runs jobs one after another."""

    def __init__(self, model_ids, repo_overrides=None):
        unknown = [m for m in model_ids if m not in MODELS]
        if unknown:
            raise ValueError(f"Unknown model(s) {unknown}; choose from {list(MODELS)}")
        self.model_ids = list(model_ids)
        self.repos = {m: (repo_overrides or {}).get(m, MODELS[m]["repo"]) for m in model_ids}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.loaded_id = None
        self.t2i = self.i2i = None
        self.jobs: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.queue: queue.Queue = queue.Queue()
        threading.Thread(target=self._work, daemon=True).start()

    def load(self, model_id):
        if model_id == self.loaded_id:
            return
        from diffusers import AutoPipelineForImage2Image, AutoPipelineForText2Image

        self.t2i = self.i2i = None
        self.loaded_id = None
        if self.device == "cuda":
            torch.cuda.empty_cache()
        repo = self.repos[model_id]
        print(f"Loading {repo} …", flush=True)
        kwargs = {"torch_dtype": self.dtype, "token": os.environ.get("HF_TOKEN") or None}
        try:
            # The fp16 variant halves the download; not every repo publishes one.
            pipe = AutoPipelineForText2Image.from_pretrained(repo, variant="fp16", **kwargs) \
                if self.dtype == torch.float16 else AutoPipelineForText2Image.from_pretrained(repo, **kwargs)
        except (OSError, ValueError):
            pipe = AutoPipelineForText2Image.from_pretrained(repo, **kwargs)
        pipe = pipe.to(self.device)
        pipe.set_progress_bar_config(disable=True)
        self.t2i = pipe
        self.i2i = AutoPipelineForImage2Image.from_pipe(pipe)
        self.loaded_id = model_id
        print(f"{MODELS[model_id]['name']} ready on {self.device}.", flush=True)

    def submit(self, endpoint: str, payload: dict) -> str:
        model_id = endpoint.removesuffix("-edit")
        if model_id not in self.model_ids:
            raise HTTPException(404, f"This server does not offer '{endpoint}'. Enabled: {self.model_ids}")
        if not str(payload.get("prompt") or "").strip():
            raise HTTPException(400, "A prompt is required.")
        if endpoint.endswith("-edit") and not payload.get("image_url"):
            raise HTTPException(400, "image_url is required for image-to-image.")
        request_id = uuid.uuid4().hex
        with self.lock:
            self.jobs[request_id] = {"status": "queued", "created": time.time()}
        self.queue.put((request_id, model_id, endpoint.endswith("-edit"), payload))
        return request_id

    def result(self, request_id: str) -> dict:
        with self.lock:
            job = self.jobs.get(request_id)
        if job is None:
            raise HTTPException(404, "Unknown request id (the server may have restarted).")
        out = {"id": request_id, "status": job["status"]}
        if "outputs" in job:
            out["outputs"] = job["outputs"]
        if "error" in job:
            out["error"] = job["error"]
        return out

    def _set(self, request_id, **fields):
        with self.lock:
            self.jobs[request_id].update(fields)

    def _work(self):
        while True:
            request_id, model_id, edit, payload = self.queue.get()
            self._set(request_id, status="processing")
            try:
                self.load(model_id)
                images = self._generate(model_id, edit, payload)
                names = []
                for image in images:
                    name = f"{uuid.uuid4().hex}.png"
                    image.save(OUTPUTS / name)
                    names.append(f"/outputs/{name}")
                self._set(request_id, status="completed", outputs=names)
            except Exception as e:  # report every failure to the app instead of killing the worker
                traceback.print_exc()
                if self.device == "cuda":
                    torch.cuda.empty_cache()
                message = "The GPU ran out of memory; try fewer images or a smaller size." \
                    if isinstance(e, torch.cuda.OutOfMemoryError) else str(e)
                self._set(request_id, status="failed", error=message)

    def _generate(self, model_id, edit, p):
        turbo = MODELS[model_id]["family"] == "turbo"
        steps = int(p.get("num_inference_steps") or (2 if turbo else 25))
        args = {"prompt": str(p["prompt"]), "num_inference_steps": steps}
        if p.get("seed") is not None:
            args["generator"] = torch.Generator(self.device).manual_seed(int(p["seed"]))
        if turbo:
            args["guidance_scale"] = 0.0  # SDXL Turbo is distilled to run without guidance
        else:
            args["guidance_scale"] = float(p.get("guidance_scale") or 6.0)
            if p.get("negative_prompt"):
                args["negative_prompt"] = str(p["negative_prompt"])

        if not edit:
            sizes = TURBO_SIZES if turbo else XL_SIZES
            width, height = sizes.get(str(p.get("aspect_ratio")), sizes["1:1"])
            count = max(1, min(int(p.get("num_images") or 1), 4 if turbo else 2))
            return self.t2i(**args, width=width, height=height, num_images_per_prompt=count).images

        strength = min(max(float(p.get("strength") or 0.5), 0.05), 1.0)
        if turbo:
            # Image-to-image runs steps × strength denoising steps, which must be at least one.
            args["num_inference_steps"] = max(steps, math.ceil(1 / strength))
        image = fit(load_image(str(p["image_url"])), 512 if turbo else 1024)
        return self.i2i(**args, image=image, strength=strength).images


def load_image(url: str) -> Image.Image:
    """Only images uploaded to this server are accepted, so the server never fetches other URLs."""
    match = re.fullmatch(r"/uploads/([0-9a-f]{32}\.png)", url)
    if not match or not (UPLOADS / match.group(1)).exists():
        raise ValueError("Upload the reference image to this server first (via /api/v1/upload_file).")
    return Image.open(UPLOADS / match.group(1)).convert("RGB")


def fit(image: Image.Image, side: int) -> Image.Image:
    """Scales the image so its longer side is `side`, with both sides multiples of 8."""
    scale = side / max(image.size)
    width, height = (max(8, round(v * scale / 8) * 8) for v in image.size)
    return image.resize((width, height), Image.LANCZOS)


def create_app(engine: Engine, token: str) -> FastAPI:
    for folder in (OUTPUTS, UPLOADS):
        folder.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="Image Studio server", docs_url=None, redoc_url=None)

    def auth(x_api_key: str | None = Header(default=None)):
        if not secrets.compare_digest(x_api_key or "", token):
            raise HTTPException(401, "Wrong access token. Copy it again from the notebook.")

    secured = [Depends(auth)]

    @app.get("/api/v1/models", dependencies=secured)
    def models():
        return catalog(engine.model_ids)

    @app.post("/api/v1/upload_file", dependencies=secured)
    async def upload(file: UploadFile = File(...)):
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Images must be under 20 MB.")
        try:
            image = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            raise HTTPException(400, "That file is not an image.")
        name = f"{uuid.uuid4().hex}.png"
        image.save(UPLOADS / name)
        return {"url": f"/uploads/{name}"}

    @app.get("/api/v1/predictions/{request_id}/result", dependencies=secured)
    def result(request_id: str):
        return engine.result(request_id)

    @app.post("/api/v1/{endpoint}", dependencies=secured)
    async def submit(endpoint: str, request: Request):
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(400, "Send a JSON body.")
        if not isinstance(payload, dict):
            raise HTTPException(400, "Send a JSON object.")
        return {"request_id": engine.submit(endpoint, payload)}

    app.mount("/outputs", StaticFiles(directory=OUTPUTS), name="outputs")
    return app


def start_server(app: FastAPI, port: int = 8765):
    """Runs uvicorn on a background thread, so the notebook cell returns."""
    import uvicorn

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            return server
        time.sleep(0.1)
    raise RuntimeError("The server did not start.")


def start_tunnel(port: int = 8765) -> str:
    """Opens a free Cloudflare quick tunnel to the server and returns its public https URL."""
    binary = shutil.which("cloudflared") or str(DATA / "cloudflared")
    if not Path(binary).exists():
        DATA.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64", binary)
        os.chmod(binary, 0o755)
    process = subprocess.Popen(
        [binary, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    found: list[str] = []

    def read():
        for line in process.stdout:  # keep draining so cloudflared never blocks on a full pipe
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match and not found:
                found.append(match.group(0))

    threading.Thread(target=read, daemon=True).start()
    for _ in range(600):
        if found:
            return found[0]
        if process.poll() is not None:
            raise RuntimeError("cloudflared exited before the tunnel came up.")
        time.sleep(0.1)
    raise RuntimeError("Timed out waiting for the Cloudflare tunnel.")


def connect_link(url: str, token: str) -> str:
    """What the app's QR scanner and paste box understand."""
    return f"imagestudio://connect?url={quote(url, safe='')}&token={token}"
