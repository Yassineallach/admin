# Image Studio for Android

A native Android app (Kotlin + Jetpack Compose) for AI image generation, built on
[Open Generative AI](https://github.com/anil-matcha/open-generative-ai). It talks to the
same [MuAPI](https://muapi.ai) engine as that project's web Image Studio and ships its model catalog.

## Features

- **Text → Image** with 74 models (Nano Banana Pro/2, Seedream, FLUX.2, GPT Image, Imagen 4,
  Midjourney, Ideogram, Qwen, Wan, Kling…)
- **Image → Image** with 76 models: edits, multi-reference generation, upscalers,
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

On first launch, paste your MuAPI key under **Settings**. It stays in the app's private storage
and is excluded from backups. Generations are billed to your MuAPI account.

## How it works

| Piece | File |
|---|---|
| MuAPI client: `POST /api/v1/{endpoint}` with `x-api-key`, then poll `/api/v1/predictions/{id}/result`; `POST /api/v1/upload_file` for reference images | `data/MuapiClient.kt` |
| Model catalog loaded from `assets/models.json` | `data/ModelCatalog.kt` |
| History (JSON file in app storage) | `data/HistoryStore.kt` |
| Gallery saving via MediaStore | `data/ImageSaver.kt` |
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
