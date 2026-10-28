"""HTTP server that exposes VoxCPM2 text-to-speech to the Android app.

Run:
    pip install -r requirements.txt
    python server.py --host 0.0.0.0 --port 8000

Endpoints:
    GET  /health  -> model info
    POST /tts     -> multipart form, returns audio/wav
"""

import argparse
import inspect
import io
import os
import random
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Optional

import numpy as np
import soundfile as sf
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response

MODEL_ID = os.environ.get("VOXCPM_MODEL", "openbmb/VoxCPM2")
API_KEY = os.environ.get("VOXCPM_API_KEY", "")
MAX_TEXT_CHARS = int(os.environ.get("VOXCPM_MAX_CHARS", "2000"))

app = FastAPI(title="VoxCPM Studio Server")

_model = None
_device = "unknown"
_model_lock = threading.Lock()
_generate_params: Optional[set] = None  # None = accepts **kwargs, don't filter


def get_model():
    global _model, _generate_params, _device
    if _model is None:
        import torch
        from voxcpm import VoxCPM

        on_gpu = torch.cuda.is_available()
        _device = "cuda" if on_gpu else "cpu"
        print(f"Loading {MODEL_ID} on {_device} ...", flush=True)
        if on_gpu:
            _model = VoxCPM.from_pretrained(MODEL_ID, load_denoiser=False)
        else:
            # voxcpm builds the model in float32 and only then converts it to bfloat16, which
            # needs more RAM than a free Colab CPU machine has. Building it directly in bfloat16
            # keeps the peak around 10.6 GB.
            torch.set_num_threads(os.cpu_count() or 2)
            torch.set_default_dtype(torch.bfloat16)
            try:
                # optimize=False: torch.compile is CUDA-only here and its warm-up run is slow on CPU.
                _model = VoxCPM.from_pretrained(MODEL_ID, load_denoiser=False, optimize=False)
            finally:
                torch.set_default_dtype(torch.float32)
            print("No GPU found: running on CPU. Expect roughly 10-25x slower than real time; "
                  "fewer inference steps (e.g. 4) help most.", flush=True)
        # generate() is often a *args/**kwargs wrapper around _generate(), so inspect the real one.
        target = getattr(_model, "_generate", _model.generate)
        params = inspect.signature(target).parameters
        if not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            _generate_params = set(params)
        print("Model ready.", flush=True)
    return _model


def sample_rate() -> int:
    model = get_model()
    return int(getattr(model.tts_model, "sample_rate", 48000))


def seed_everything(seed: int):
    """voxcpm has no seed argument, so seed the global RNGs it samples from."""
    random.seed(seed)
    np.random.seed(seed % 2**32)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


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
    return {"status": "ok", "model": MODEL_ID, "sample_rate": sample_rate(), "device": _device}


@app.post("/tts")
def tts(
    text: str = Form(...),
    control: str = Form(""),
    prompt_text: str = Form(""),
    cfg_value: float = Form(2.0),
    inference_timesteps: int = Form(10),
    seed: Optional[int] = Form(None),
    reference_audio: Optional[UploadFile] = File(None),
    _: None = Depends(check_key),
):
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")
    if len(text) > MAX_TEXT_CHARS:
        raise HTTPException(status_code=400, detail=f"Text longer than {MAX_TEXT_CHARS} characters")

    # VoxCPM2 takes voice design / style instructions as a parenthesised prefix.
    control = control.strip().strip("()")
    full_text = f"({control}){text}" if control else text

    kwargs = {
        "text": full_text,
        "cfg_value": max(0.5, min(cfg_value, 5.0)),
        "inference_timesteps": max(1, min(inference_timesteps, 50)),
    }
    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    with tempfile.TemporaryDirectory() as workdir:
        if reference_audio is not None and reference_audio.filename:
            ref_path = save_upload_as_wav(reference_audio, workdir, "reference")
            kwargs["reference_wav_path"] = ref_path
            if prompt_text.strip():
                # "Ultimate cloning": continue from the reference clip and its transcript.
                kwargs["prompt_wav_path"] = ref_path
                kwargs["prompt_text"] = prompt_text.strip()

        model = get_model()
        if _generate_params is not None:
            if "seed" in _generate_params:
                kwargs["seed"] = seed
            kwargs = {k: v for k, v in kwargs.items() if k in _generate_params}

        started = time.time()
        with _model_lock:
            try:
                seed_everything(seed)
                wav = model.generate(**kwargs)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Generation failed: {e}")
        elapsed = time.time() - started

    wav = np.asarray(wav, dtype=np.float32).squeeze()
    sr = sample_rate()
    buf = io.BytesIO()
    sf.write(buf, wav, sr, format="WAV", subtype="PCM_16")
    return Response(
        content=buf.getvalue(),
        media_type="audio/wav",
        headers={
            "X-Seed": str(seed),
            "X-Sample-Rate": str(sr),
            "X-Duration": f"{len(wav) / sr:.2f}",
            "X-Generation-Seconds": f"{elapsed:.2f}",
        },
    )


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    get_model()  # load before accepting requests
    uvicorn.run(app, host=args.host, port=args.port)
