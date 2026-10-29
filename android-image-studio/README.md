# Image Studio for Android

A native Android app (Kotlin + Jetpack Compose) for AI image generation, built on
[Open Generative AI](https://github.com/anil-matcha/open-generative-ai). Images are made in one of two places:

- **My GPU (free):** open models (SDXL Turbo, SDXL, Juggernaut XL) running in a notebook on a free
  Kaggle or Colab GPU. See [Free generation on Kaggle or Colab](#free-generation-on-kaggle-or-colab).
- **MuAPI (paid):** the same [MuAPI](https://muapi.ai) engine as Open Generative AI's web Image Studio,
  with its catalog of 150 models. Each generation is billed to your MuAPI account.

## Features

- **Text → Image** with 74 MuAPI models (Nano Banana Pro/2, Seedream, FLUX.2, GPT Image, Imagen 4,
  Midjourney, Ideogram, Qwen, Wan, Kling…)
- **Image → Image** with 76 MuAPI models: edits, multi-reference generation, upscalers,
  background removal, effects, face swap
- Controls are generated from each model's schema: aspect ratio, resolution, quality,
  number of images, sliders and toggles
- Reference images from the system photo picker, uploaded to MuAPI on generate
- History with resume: jobs still running when the app closes are picked up again on launch
- Full-screen pinch-zoom viewer, save to `Pictures/Image Studio`, share links

## Build

You need JDK 17+ and the Android SDK (or just Android Studio).

```bash
cd android-image-studio
./gradlew assembleDebug        # → app/build/outputs/apk/debug/app-debug.apk
./gradlew testDebugUnitTest    # JVM unit tests
```

Or open the folder in Android Studio and press Run. Every push that touches this folder also
builds the APK in GitHub Actions (see the **Android Image Studio** workflow's artifacts).

On first launch, open **Settings** and either connect your notebook server (free) or paste a MuAPI
key (paid). Keys and tokens stay in the app's private storage and are excluded from backups.

## Free generation on Kaggle or Colab

`server/image_studio_server.ipynb` turns a free notebook GPU into an Image Studio server.

1. Upload the notebook:
   - **Kaggle:** kaggle.com → *Create → New Notebook → File → Import Notebook*. In the right panel
     set *Accelerator* to **GPU T4 x2** and turn **Internet on** (Kaggle asks you to verify a phone
     number first). Kaggle gives about 30 GPU hours a week.
   - **Colab:** colab.research.google.com → *Upload*, then *Runtime → Change runtime type →* **T4 GPU**.
     Google restricts some image-generation use on the free tier, so sessions there may be cut off.
2. **Run all.** The first run downloads the model, about 7 GB, which takes a few minutes.
3. A QR code appears. In the app, go to **Settings → My GPU → Scan QR code**, or paste the
   `imagestudio://` link printed under it.

Keep the notebook tab open while you use the app. Each session gets a new address, so scan again
after a restart. The app copies every image it receives onto the phone, so your history outlives
the session.

To offer more models, edit `MODELS` in the notebook's second cell: `"sdxl"` and `"juggernaut-xl"`
are 1024 px models taking roughly 25 steps; `"sdxl-turbo"`, the default, is the fastest. Only one
model sits on the GPU at a time, so switching models in the app costs a reload.

**How it works:** the notebook runs a small FastAPI server that speaks the same protocol as MuAPI
(submit, poll, upload), so the app reuses its MuAPI client. A free Cloudflare quick tunnel gives it
a public `https://….trycloudflare.com` address, and a random access token, embedded in the QR code,
guards every API call. The server only accepts reference images uploaded to it and never fetches
other URLs.

The notebook is generated from `server/image_studio_server.py`; after editing the server, run
`python3 server/build_notebook.py`.

## How it works

| Piece | File |
|---|---|
| MuAPI client: `POST /api/v1/{endpoint}` with `x-api-key`, then poll `/api/v1/predictions/{id}/result`; `POST /api/v1/upload_file` for reference images. Also drives the notebook server. | `data/MuapiClient.kt` |
| Notebook connect links (`imagestudio://connect?url=…&token=…`) | `data/ServerLink.kt` |
| Notebook server | `server/image_studio_server.py` → `server/image_studio_server.ipynb` |
| Model catalog loaded from `assets/models.json` | `data/ModelCatalog.kt` |
| History (JSON file in app storage) | `data/HistoryStore.kt` |
| Gallery saving, local copies of server images, sharing | `data/ImageSaver.kt` |
| State and generation flow | `ui/StudioViewModel.kt` |
| Screens | `ui/CreateScreen.kt`, `HistoryScreen.kt`, `SettingsScreen.kt`, `ImageViewer.kt` |

## Updating the model list

`assets/models.json` is generated from the upstream catalog:

```bash
git clone --depth 1 https://github.com/anil-matcha/open-generative-ai /tmp/oga
python3 tools/extract_models.py /tmp/oga/packages/studio/src/models.js
```

The script parses the catalog's JSON literals as data. It skips models that need inputs this app
has no UI for, such as LoRA lists, masks and character sheets.

## License

The model catalog is derived from Open Generative AI (MIT).
