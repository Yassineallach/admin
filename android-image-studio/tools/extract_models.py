#!/usr/bin/env python3
"""Builds app/src/main/assets/models.json from Open Generative AI's model catalog.

Usage:
    python3 tools/extract_models.py path/to/open-generative-ai/packages/studio/src/models.js

The catalog in models.js is a set of JSON array literals (`export const t2iModels = [...]`),
so it is parsed here as data; nothing from that file is executed.
"""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app/src/main/assets/models.json"

# Inputs the app fills itself, or that need UI it does not have (LoRA lists, masks, raw keys).
SKIP_INPUTS = {
    "prompt", "image_url", "images_list", "model_image_url", "person_image_url",
    "request_id", "mask_url", "mask_indexs", "api_key", "model_url", "audio_ids",
    "loras", "lora_list", "lora_url", "lora_weight", "make_input",
}
TEXT_INPUTS = {"negative_prompt", "scene_description", "character_name", "descriptions"}

# Models that cannot be driven from a plain prompt + reference-image form.
SKIP_MODELS = {
    "Api Node", "image-passthrough", "grok-imagine-image-2-edit",
    "seedance-2-character", "gemini-omni-character",
}
# These two need a reference image; the image-to-image catalog already carries them.
SKIP_T2I = {"flux-pulid", "flux-redux"}

NUMERIC_TYPES = {"int", "integer", "number", "float"}
IMAGE_INPUTS = {"image_url", "images_list", "model_image_url", "person_image_url"}


def read_array(source: str, name: str) -> list:
    marker = f"export const {name} = ["
    start = source.index(marker) + len(marker) - 1
    end = source.index("\n];", start) + 2
    return json.loads(source[start:end])


def convert_param(key: str, spec: dict):
    if key in SKIP_INPUTS or not isinstance(spec, dict):
        return None
    title = spec.get("title") or key.replace("_", " ").title()
    param = {"name": key, "title": title}
    if "default" in spec:
        param["default"] = spec["default"]
    if "enum" in spec:
        param["kind"] = "enum"
        param["values"] = spec["enum"]
        return param
    kind = spec.get("type")
    if kind in NUMERIC_TYPES:
        step = spec.get("step", 1)
        is_float = kind in ("number", "float") or float(step) != int(step) \
            or isinstance(spec.get("default"), float)
        param["kind"] = "float" if is_float else "int"
        for src, dst in (("minValue", "min"), ("maxValue", "max")):
            if src in spec:
                param[dst] = spec[src]
        param["step"] = step
        return param
    if kind == "boolean":
        param["kind"] = "bool"
        return param
    if kind == "string" and key in TEXT_INPUTS:
        param["kind"] = "text"
        return param
    return None


def convert_model(model: dict, mode: str):
    if model["id"] in SKIP_MODELS:
        return None
    if "lora" in model["id"]:
        return None
    inputs = model.get("inputs", {})
    # A few text-to-image models are also listed under image-to-image; they take no image.
    if mode == "i2i" and not model.get("imageField") and not IMAGE_INPUTS & inputs.keys():
        return None
    params = [p for p in (convert_param(k, v) for k, v in inputs.items()) if p]
    out = {
        "id": model["id"],
        "name": model["name"],
        "endpoint": model.get("endpoint") or model["id"],
        "provider": model.get("provider_name") or model.get("provider") or "",
        "mode": mode,
        "hasPrompt": model.get("hasPrompt", "prompt" in inputs),
        "params": params,
    }
    if mode == "i2i":
        field = model.get("imageField") or "image_url"
        out["imageField"] = field
        out["maxImages"] = model.get("maxImages") or (4 if field == "images_list" else 1)
    return out


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    models = []
    for name, mode in (("t2iModels", "t2i"), ("i2iModels", "i2i")):
        for model in read_array(source, name):
            if mode == "t2i" and model["id"] in SKIP_T2I:
                continue
            converted = convert_model(model, mode)
            if converted:
                models.append(converted)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(models, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    counts = {m: sum(1 for x in models if x["mode"] == m) for m in ("t2i", "i2i")}
    print(f"Wrote {len(models)} models to {OUT} ({counts})")


if __name__ == "__main__":
    main()
