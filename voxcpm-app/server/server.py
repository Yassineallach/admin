"""HTTP server that exposes text-to-speech models to the VoxCPM Studio Android app.

Two engines, one per server process (they need different Python environments):

    voxcpm    VoxCPM2 (openbmb/VoxCPM2): default voice, voice design and cloning, 30 languages.
    indextts  IndexTTS-2.5 (IndexTeam/IndexTTS-2.5): cloning with emotion control,
              EN / ZH / JA / ES / AR. Run it from an index-tts checkout (see the notebooks).

Run:
    pip install -r requirements.txt
    python server.py --host 0.0.0.0 --port 8000                     # VoxCPM2
    python server.py --engine indextts --model-dir checkpoints      # IndexTTS-2.5

Endpoints:
    GET    /health           -> engine, model info and what the engine supports
    POST   /tts              -> multipart form, returns audio/wav in one request
    POST   /jobs             -> same form, queues the generation and returns {"id", "status", ...}
    GET    /jobs/{id}        -> {"status": queued|running|done|error|cancelled, "position", "error"}
    GET    /jobs/{id}/audio  -> audio/wav once done
    DELETE /jobs/{id}        -> cancel
"""

import argparse
import inspect
import io
import os
import queue
import random
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from typing import Optional

import numpy as np
import soundfile as sf
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

ENGINE = os.environ.get("TTS_ENGINE", "voxcpm")
MODEL_ID = os.environ.get("VOXCPM_MODEL", "openbmb/VoxCPM2")
INDEXTTS_MODEL_DIR = os.environ.get("INDEXTTS_MODEL_DIR", "checkpoints")
API_KEY = os.environ.get("VOXCPM_API_KEY", "")
MAX_TEXT_CHARS = int(os.environ.get("VOXCPM_MAX_CHARS", "2000"))

app = FastAPI(title="VoxCPM Studio Server")

_engine = None
_engine_lock = threading.Lock()  # one generation at a time on the GPU


class GenerationError(Exception):
    pass


def seed_everything(seed: int):
    """Neither model takes a seed argument, so seed the global RNGs they sample from."""
    random.seed(seed)
    np.random.seed(seed % 2**32)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


class VoxCPMEngine:
    name = "VoxCPM2"

    def __init__(self):
        import torch
        from voxcpm import VoxCPM

        on_gpu = torch.cuda.is_available()
        self.device = "cuda" if on_gpu else "cpu"
        print(f"Loading {MODEL_ID} on {self.device} ...", flush=True)
        if on_gpu:
            self.model = VoxCPM.from_pretrained(MODEL_ID, load_denoiser=False)
        else:
            # voxcpm builds the model in float32 and only then converts it to bfloat16, which
            # needs more RAM than a free Colab CPU machine has. Building it directly in bfloat16
            # keeps the peak around 10.6 GB.
            torch.set_num_threads(os.cpu_count() or 2)
            torch.set_default_dtype(torch.bfloat16)
            try:
                # optimize=False: torch.compile is CUDA-only here and its warm-up run is slow on CPU.
                self.model = VoxCPM.from_pretrained(MODEL_ID, load_denoiser=False, optimize=False)
            finally:
                torch.set_default_dtype(torch.float32)
            print("No GPU found: running on CPU. Expect roughly 10-25x slower than real time; "
                  "fewer inference steps (e.g. 4) help most.", flush=True)
        # generate() is often a *args/**kwargs wrapper around _generate(), so inspect the real one.
        target = getattr(self.model, "_generate", self.model.generate)
        params = inspect.signature(target).parameters
        self.params = None  # None = accepts **kwargs, don't filter
        if not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            self.params = set(params)
        self.sample_rate = int(getattr(self.model.tts_model, "sample_rate", 48000))

    def info(self):
        return {
            "modes": ["default", "design", "clone"],
            "languages": [],
            "cfg": True,
            "steps": True,
            "transcript": True,
            "emotion_vector": False,
            "emotion_text": True,  # style control prefix, e.g. "(slightly faster, cheerful tone)"
            "duration": False,
        }

    def generate(self, p: dict) -> np.ndarray:
        # VoxCPM2 takes voice design / style instructions as a parenthesised prefix.
        control = p["control"].strip().strip("()")
        kwargs = {
            "text": f"({control}){p['text']}" if control else p["text"],
            "cfg_value": max(0.5, min(p["cfg_value"], 5.0)),
            "inference_timesteps": max(1, min(p["inference_timesteps"], 50)),
        }
        if p["ref_path"]:
            kwargs["reference_wav_path"] = p["ref_path"]
            if p["prompt_text"]:
                # "Ultimate cloning": continue from the reference clip and its transcript.
                kwargs["prompt_wav_path"] = p["ref_path"]
                kwargs["prompt_text"] = p["prompt_text"]
        if self.params is not None:
            if "seed" in self.params:
                kwargs["seed"] = p["seed"]
            kwargs = {k: v for k, v in kwargs.items() if k in self.params}
        return np.asarray(self.model.generate(**kwargs), dtype=np.float32).squeeze()


INDEXTTS_LANGUAGES = ["auto", "en", "zh", "ja", "es", "ar"]
# Order IndexTTS-2.5 expects for emo_vector.
INDEXTTS_EMOTIONS = ["happy", "angry", "sad", "afraid", "disgusted", "melancholic", "surprised", "calm"]


def detect_language(text: str) -> str:
    """Picks an IndexTTS language code from the script the text is written in."""
    if re.search(r"[؀-ۿݐ-ݿ]", text):
        return "ar"
    if re.search(r"[぀-ヿ]", text):  # hiragana / katakana
        return "ja"
    if re.search(r"[一-鿿]", text):
        return "zh"
    if re.search(r"[ñÑ¿¡]|\b(el|la|los|las|que|de|y|es|por|para|con|una?)\b", text, re.IGNORECASE):
        return "es"
    return "en"


class IndexTTSEngine:
    name = "IndexTTS-2.5"

    def __init__(self):
        import torch
        from indextts.infer_v2_5 import IndexTTS2

        on_gpu = torch.cuda.is_available()
        self.device = "cuda" if on_gpu else "cpu"
        # The 0.6B emotion-from-text model costs ~1.2 GB more; skip it on CPU machines with little RAM.
        use_qwen = os.environ.get("INDEXTTS_QWEN_EMO", "1" if on_gpu else "0") == "1"
        print(f"Loading IndexTTS-2.5 from {INDEXTTS_MODEL_DIR} on {self.device} ...", flush=True)
        self.model = IndexTTS2(
            cfg_path=os.path.join(INDEXTTS_MODEL_DIR, "config.yaml"),
            model_dir=INDEXTTS_MODEL_DIR,
            use_bf16=on_gpu,
            use_qwen_emo=use_qwen,
        )
        self.emotion_text = use_qwen
        self.sample_rate = 22050

    def info(self):
        return {
            "modes": ["clone"],
            "languages": INDEXTTS_LANGUAGES,
            "cfg": False,
            "steps": False,
            "transcript": False,
            "emotion_vector": True,
            "emotion_text": self.emotion_text,
            "emotions": INDEXTTS_EMOTIONS,
            "duration": True,
        }

    def generate(self, p: dict) -> np.ndarray:
        if not p["ref_path"]:
            raise GenerationError("IndexTTS-2.5 needs a reference voice: use Voice clone with a clip or saved voice")
        lang = p["language"].lower() or "auto"
        if lang == "auto":
            lang = detect_language(p["text"])
        kwargs = {
            "spk_audio_prompt": p["ref_path"],
            "text": p["text"],
            "output_path": None,  # return the audio instead of writing a file
            "lang": lang.upper(),
            "duration_factor": max(0.5, min(p["duration_factor"], 2.0)),
        }
        control = p["control"].strip().strip("()")
        if control and self.emotion_text:
            kwargs.update(use_emo_text=True, emo_text=control, emo_alpha=min(p["emo_alpha"], 0.6))
        elif p["emo_vector"]:
            kwargs.update(emo_vector=p["emo_vector"], emo_alpha=p["emo_alpha"])
        elif control:
            raise GenerationError("This server can't read emotion descriptions (needs a GPU); pick an emotion instead")
        result = self.model.infer(**kwargs)
        if not result:
            raise GenerationError("IndexTTS-2.5 returned no audio")
        sr, wav = result  # int16 samples shaped (n, 1)
        self.sample_rate = int(sr)
        return np.asarray(wav, dtype=np.float32).squeeze() / 32768.0


def get_model():
    """Loads the selected engine once and returns it."""
    global _engine
    if _engine is None:
        _engine = IndexTTSEngine() if ENGINE == "indextts" else VoxCPMEngine()
        print(f"{_engine.name} ready.", flush=True)
    return _engine


def check_key(authorization: Optional[str] = Header(None), x_api_key: Optional[str] = Header(None)):
    if not API_KEY:
        return
    token = x_api_key or ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def save_upload_as_wav(upload: UploadFile, workdir: str, name: str) -> str:
    """Decode any common audio format (wav/flac/ogg/mp3/m4a) to a wav file."""
    raw_path = os.path.join(workdir, f"{name}_raw")
    with open(raw_path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    wav_path = os.path.join(workdir, f"{name}.wav")

    try:
        data, sr = sf.read(raw_path, always_2d=False)
        sf.write(wav_path, data, sr)
        return wav_path
    except Exception:
        pass
    if shutil.which("ffmpeg"):
        result = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", raw_path, "-ac", "1", wav_path],
            capture_output=True,
        )
        if result.returncode == 0:
            return wav_path
    try:
        import librosa

        data, sr = librosa.load(raw_path, sr=None, mono=True)
        sf.write(wav_path, data, sr)
        return wav_path
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not decode {name} audio: {e}")


@app.get("/health")
def health(_: None = Depends(check_key)):
    engine = get_model()
    return {
        "status": "ok",
        "engine": ENGINE,
        "model": engine.name if ENGINE == "indextts" else MODEL_ID,
        "sample_rate": engine.sample_rate,
        "device": engine.device,
        "jobs": True,
        "capabilities": engine.info(),
    }


def parse_emo_vector(raw: str) -> Optional[list]:
    """"0,0,0.8,0,0,0,0,0" -> 8 floats in IndexTTS order; empty -> None."""
    if not raw.strip():
        return None
    try:
        values = [max(0.0, min(float(v), 1.0)) for v in raw.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="emo_vector must be 8 comma-separated numbers")
    if len(values) != len(INDEXTTS_EMOTIONS):
        raise HTTPException(status_code=400, detail="emo_vector must have 8 values")
    return values if any(values) else None


def prepare(form: dict, reference_audio, workdir) -> dict:
    """Validates a request and turns it into engine parameters. Files go into [workdir]."""
    text = form["text"].strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(status_code=400, detail=f"Text longer than {MAX_TEXT_CHARS} characters")
    ref_path = None
    if reference_audio is not None and reference_audio.filename:
        ref_path = save_upload_as_wav(reference_audio, workdir, "reference")
    elif "default" not in get_model().info()["modes"]:
        raise HTTPException(
            status_code=400,
            detail=f"{get_model().name} needs a reference voice: use Voice clone with a clip or saved voice",
        )
    return {
        "text": text,
        "control": form["control"],
        "prompt_text": form["prompt_text"].strip(),
        "cfg_value": form["cfg_value"],
        "inference_timesteps": form["inference_timesteps"],
        "seed": form["seed"] if form["seed"] is not None else random.randint(0, 2**31 - 1),
        "language": form["language"].strip(),
        "emo_vector": parse_emo_vector(form["emo_vector"]),
        "emo_alpha": max(0.0, min(form["emo_alpha"], 1.0)),
        "duration_factor": form["duration_factor"],
        "ref_path": ref_path,
    }


def synthesize(params: dict):
    """Runs the model. Returns (wav bytes, response headers)."""
    engine = get_model()
    started = time.time()
    with _engine_lock:
        try:
            seed_everything(params["seed"])
            wav = engine.generate(params)
        except GenerationError:
            raise
        except Exception as e:
            raise GenerationError(f"Generation failed: {e}")
    elapsed = time.time() - started

    sr = engine.sample_rate
    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV", subtype="PCM_16")
    headers = {
        "X-Seed": str(params["seed"]),
        "X-Sample-Rate": str(sr),
        "X-Duration": f"{len(wav) / sr:.2f}",
        "X-Generation-Seconds": f"{elapsed:.2f}",
        "X-Engine": engine.name,
    }
    return buf.getvalue(), headers


def form_fields(
    text: str = Form(...),
    control: str = Form(""),
    prompt_text: str = Form(""),
    cfg_value: float = Form(2.0),
    inference_timesteps: int = Form(10),
    seed: Optional[int] = Form(None),
    language: str = Form(""),
    emo_vector: str = Form(""),
    emo_alpha: float = Form(1.0),
    duration_factor: float = Form(1.0),
) -> dict:
    return dict(
        text=text, control=control, prompt_text=prompt_text, cfg_value=cfg_value,
        inference_timesteps=inference_timesteps, seed=seed, language=language,
        emo_vector=emo_vector, emo_alpha=emo_alpha, duration_factor=duration_factor,
    )


@app.post("/tts")
def tts(
    form: dict = Depends(form_fields),
    reference_audio: Optional[UploadFile] = File(None),
    _: None = Depends(check_key),
):
    """Generates in one request. Tunnels such as Cloudflare cut requests after ~100 s; use /jobs then."""
    with tempfile.TemporaryDirectory() as workdir:
        params = prepare(form, reference_audio, workdir)
        try:
            audio, headers = synthesize(params)
        except GenerationError as e:
            raise HTTPException(status_code=500, detail=str(e))
    return Response(content=audio, media_type="audio/wav", headers=headers)


# --- Background jobs: every request returns quickly, so tunnel timeouts can't cut a long generation.

JOB_TTL_SECONDS = 1800  # finished jobs are kept this long for the client to fetch

_jobs: dict = {}  # id -> job dict, in submission order
_jobs_lock = threading.Lock()
_job_queue: "queue.Queue[str]" = queue.Queue()
_worker: Optional[threading.Thread] = None


def _prune_jobs():
    now = time.time()
    for job_id in [i for i, j in _jobs.items() if j.get("finished") and now - j["finished"] > JOB_TTL_SECONDS]:
        _jobs.pop(job_id, None)


def _run_jobs():
    while True:
        job_id = _job_queue.get()
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is None or job["status"] != "queued":
                if job is not None:
                    shutil.rmtree(job["workdir"], ignore_errors=True)
                continue
            job["status"] = "running"
            job["started"] = time.time()
        try:
            audio, headers = synthesize(job["params"])
            result = {"status": "done", "audio": audio, "headers": headers}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        finally:
            shutil.rmtree(job["workdir"], ignore_errors=True)
        with _jobs_lock:
            if job["status"] == "running":  # not cancelled meanwhile
                job.update(result)
            job["finished"] = time.time()


def _ensure_worker():
    global _worker
    if _worker is None or not _worker.is_alive():
        _worker = threading.Thread(target=_run_jobs, name="tts-jobs", daemon=True)
        _worker.start()


def _job_status(job_id: str, job: dict) -> dict:
    ahead = 0
    for other_id, other in _jobs.items():
        if other_id == job_id:
            break
        if other["status"] in ("queued", "running"):
            ahead += 1
    started = job.get("started")
    return {
        "id": job_id,
        "status": job["status"],
        "position": ahead if job["status"] == "queued" else 0,
        "elapsed": round(time.time() - started, 1) if started and job["status"] == "running" else None,
        "error": job.get("error"),
    }


@app.post("/jobs")
def create_job(
    form: dict = Depends(form_fields),
    reference_audio: Optional[UploadFile] = File(None),
    _: None = Depends(check_key),
):
    workdir = tempfile.mkdtemp(prefix="tts_job_")
    try:
        params = prepare(form, reference_audio, workdir)
    except Exception:
        shutil.rmtree(workdir, ignore_errors=True)
        raise
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _prune_jobs()
        _jobs[job_id] = {"status": "queued", "params": params, "workdir": workdir}
        status = _job_status(job_id, _jobs[job_id])
    _ensure_worker()
    _job_queue.put(job_id)
    return status


def _get_job(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job (it may have expired or the server restarted)")
    return job


@app.get("/jobs/{job_id}")
def job_status(job_id: str, _: None = Depends(check_key)):
    with _jobs_lock:
        return _job_status(job_id, _get_job(job_id))


@app.get("/jobs/{job_id}/audio")
def job_audio(job_id: str, _: None = Depends(check_key)):
    with _jobs_lock:
        job = _get_job(job_id)
        if job["status"] != "done":
            raise HTTPException(status_code=409, detail=f"Job is {job['status']}")
        return Response(content=job["audio"], media_type="audio/wav", headers=job["headers"])


@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str, _: None = Depends(check_key)):
    """Drops a job. A running generation still finishes on the GPU, but its result is discarded."""
    with _jobs_lock:
        job = _get_job(job_id)
        if job["status"] in ("queued", "running"):
            job["status"] = "cancelled"
            job.pop("audio", None)
        else:
            _jobs.pop(job_id, None)
    return {"id": job_id, "status": "cancelled"}


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--engine", choices=["voxcpm", "indextts"], default=ENGINE)
    parser.add_argument("--model-dir", default=INDEXTTS_MODEL_DIR, help="IndexTTS-2.5 checkpoints folder")
    args = parser.parse_args()
    ENGINE = args.engine
    INDEXTTS_MODEL_DIR = args.model_dir
    get_model()  # load before accepting requests
    uvicorn.run(app, host=args.host, port=args.port)
