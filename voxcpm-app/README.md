# VoxCPM Studio — Android voice generator for VoxCPM2

An Android app (Kotlin + Jetpack Compose) for generating speech with
[VoxCPM2](https://github.com/OpenBMB/VoxCPM) (`openbmb/VoxCPM2`, 48 kHz, 30 languages).

VoxCPM2 is a 2B-parameter model that needs a GPU with ~8 GB VRAM, so it can't run
inside a phone. The app is a client: it sends requests to a small server
(`server/server.py`) that runs the model on a PC or in Google Colab.

```
Android app  ──HTTP (multipart)──▶  server.py (FastAPI + voxcpm)  ──▶  GPU
             ◀──────── WAV ────────
```

## Features

- **Default** — VoxCPM2 picks a voice that fits the text.
- **Voice design** — describe a voice ("A young woman, gentle and sweet voice") with presets.
- **Voice clone** — pick an audio file or record from the mic. Add the clip's transcript for
  the closest match (VoxCPM2 "ultimate cloning"), plus optional style control
  ("slightly faster, cheerful tone").
- **Multiple texts** — turn it on and every line of the text box becomes its own clip, made
  one after another with the same voice settings. Stop any time; play all clips in a row.
- Advanced: CFG guidance, inference steps, seed (shown after each run so you can reproduce it).
- History with play, save to device, share, reuse settings, delete.
- Share text from any app into VoxCPM Studio to speak it.
- Optional API key to protect your server.

## 1. Start a server

**Free, no GPU needed: Google Colab**

1. Open `server/VoxCPM_Server_Colab.ipynb` in [Colab](https://colab.research.google.com)
   (File → Upload notebook, or open it from GitHub).
2. Runtime → Change runtime type → **T4 GPU**.
3. Run all cells. The last cell prints a URL like `https://xxxx.trycloudflare.com`.

**Your own PC (NVIDIA GPU, Python 3.10–3.12, CUDA 12+)**

```bash
cd voxcpm-app/server
pip install -r requirements.txt
python server.py --host 0.0.0.0 --port 8000
# optional: VOXCPM_API_KEY=secret python server.py
```

The phone must be on the same Wi-Fi; use `http://<your-PC-IP>:8000` in the app.
The first start downloads the model (~5 GB) from Hugging Face.

## 2. Install the app

- Download the APK from the **Actions** tab (workflow "VoxCPM Studio APK" → artifact), or
- build it: open `voxcpm-app/android` in Android Studio and press Run, or
  `cd voxcpm-app/android && ./gradlew assembleDebug`
  (APK at `app/build/outputs/apk/debug/app-debug.apk`).

Open the app → **Settings** → paste the server URL (and API key if you set one) →
**Test connection** → go to **Generate**.

## Server API

| Method | Path      | Description |
|--------|-----------|-------------|
| GET    | `/health` | `{"status","model","sample_rate"}` |
| POST   | `/tts`    | multipart form → `audio/wav` |

`/tts` fields: `text` (required), `control` (voice description / style, sent to VoxCPM2 as a
`(…)` prefix), `reference_audio` (file, enables cloning), `prompt_text` (transcript of the
reference), `cfg_value` (default 2.0), `inference_timesteps` (default 10), `seed`.
Response headers: `X-Seed`, `X-Duration`, `X-Sample-Rate`, `X-Generation-Seconds`.

Auth (when `VOXCPM_API_KEY` is set): `Authorization: Bearer <key>` or `X-API-Key: <key>`.

Environment variables: `VOXCPM_MODEL` (default `openbmb/VoxCPM2`), `VOXCPM_API_KEY`,
`VOXCPM_MAX_CHARS` (default 2000).

Please use voice cloning only with voices you have permission to use.
