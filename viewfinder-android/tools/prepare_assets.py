#!/usr/bin/env python3
"""Copies the CC0 art used by Lensfold into res://assets/, trimmed for mobile.

Sources (all CC0 1.0):
  * Quaternius "Stylized Nature MegaKit" (free/standard edition)
  * Quaternius "Medieval Village MegaKit" (free/standard edition)
  * ambientCG Grass005, Rock023 (1K JPG)

Usage: tools/prepare_assets.py <nature_dir> <village_dir> <ambientcg_dir>
  nature_dir/village_dir = unzipped packs (folders containing glTF/ and Textures/)
  ambientcg_dir          = folder containing the unzipped Grass005 / Rock023 zips

What it does: copies the chosen glTF models + .bin, strips normal / ORM /
roughness maps (the game's shaders only use base colour), drops unused images,
and resizes textures (1024 px max, 512 px for small atlases).
"""
import json, os, shutil, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets")

NATURE = [
    "CommonTree_1", "CommonTree_2", "CommonTree_3", "CommonTree_4", "CommonTree_5",
    "Pine_1", "Pine_2", "Pine_3", "TwistedTree_1",
    "Bush_Common", "Bush_Common_Flowers", "Flower_3_Group", "Flower_4_Group", "Flower_3_Single",
    "Clover_1", "Grass_Common_Short", "Grass_Common_Tall", "Grass_Wispy_Short", "Fern_1",
    "Plant_1", "Plant_7", "Mushroom_Common", "Rock_Medium_1", "Rock_Medium_2", "Rock_Medium_3",
    "Pebble_Round_1", "Pebble_Round_2", "Pebble_Round_3", "RockPath_Round_Small_1", "RockPath_Round_Wide",
]
VILLAGE = [
    "Wall_Plaster_Straight", "Wall_Plaster_Window_Wide_Round", "Wall_Plaster_Window_Thin_Round",
    "Wall_Plaster_Door_Round", "Wall_Plaster_WoodGrid", "Wall_UnevenBrick_Straight",
    "Wall_UnevenBrick_Window_Wide_Round", "Wall_UnevenBrick_Door_Round", "Corner_Exterior_Wood",
    "Corner_Exterior_Brick", "Roof_RoundTiles_4x4", "Roof_RoundTiles_4x6", "Roof_RoundTiles_6x6",
    "Prop_Chimney", "Door_1_Round", "Window_Wide_Round1", "Window_Thin_Round1",
    "WindowShutters_Wide_Round_Open", "WindowShutters_Thin_Round_Open", "Prop_WoodenFence_Single",
    "Prop_WoodenFence_Extension1", "Prop_Crate", "Prop_Wagon", "Prop_Vine1", "Prop_Vine5", "Prop_Vine6",
    "Balcony_Simple_Straight", "Stairs_Exterior_Straight", "Prop_ExteriorBorder_Straight1",
    "Prop_Support", "Prop_MetalFence_Simple",
]
WORLD_TEXTURES = {
    # out name: (pack, relative path)
    "plaster.png": ("village", "Textures/T_Plaster_BaseColor.png"),
    "stone_brick.png": ("village", "Textures/T_Brick_BaseColor.png"),
    "red_brick.png": ("village", "Textures/T_RedBrick_BaseColor.png"),
    "cobble.png": ("village", "Textures/T_UnevenBrick_BaseColor.png"),
    "roof_tiles.png": ("village", "Textures/T_RoundTiles_BaseColor.png"),
    "wood.png": ("village", "Textures/T_WoodTrim_BaseColor.png"),
    "rock_trim.png": ("village", "Textures/T_RockTrim_BaseColor.png"),
    "grass.jpg": ("acg", "Grass005/Grass005_1K-JPG_Color.jpg"),
    "cliff.jpg": ("acg", "Rock023/Rock023_1K-JPG_Color.jpg"),
}
SMALL = ("Flowers", "Grass", "Mushrooms", "Leaves.", "Vine", "WindowGradient", "Metal")


def resize(src, dst, max_px):
    im = Image.open(src)
    if max(im.size) > max_px:
        im = im.resize((max_px, max_px * im.size[1] // im.size[0]), Image.LANCZOS)
    if dst.endswith(".jpg"):
        im.convert("RGB").save(dst, quality=88)
    else:
        im.save(dst, optimize=True)


def copy_model(pack_dir, name, out_dir):
    gltf_dir = os.path.join(pack_dir, "glTF")
    d = json.load(open(os.path.join(gltf_dir, name + ".gltf")))
    used_tex = set()
    for m in d.get("materials", []):
        for k in ("normalTexture", "occlusionTexture", "emissiveTexture"):
            m.pop(k, None)
        pbr = m.setdefault("pbrMetallicRoughness", {})
        pbr.pop("metallicRoughnessTexture", None)
        pbr["metallicFactor"] = 0.0
        if "baseColorTexture" in pbr:
            used_tex.add(pbr["baseColorTexture"]["index"])
    # Re-index textures/images to only the base-colour ones.
    tex_map, new_tex, img_map, new_img = {}, [], {}, []
    for ti in sorted(used_tex):
        t = d["textures"][ti]
        si = t["source"]
        if si not in img_map:
            img_map[si] = len(new_img)
            new_img.append(d["images"][si])
        t = dict(t, source=img_map[si])
        tex_map[ti] = len(new_tex)
        new_tex.append(t)
    for m in d.get("materials", []):
        pbr = m["pbrMetallicRoughness"]
        if "baseColorTexture" in pbr:
            pbr["baseColorTexture"]["index"] = tex_map[pbr["baseColorTexture"]["index"]]
    d["textures"], d["images"] = new_tex, new_img
    if not new_tex:
        d.pop("textures"); d.pop("images")
        d.pop("samplers", None)
    json.dump(d, open(os.path.join(out_dir, name + ".gltf"), "w"))
    for b in d.get("buffers", []):
        shutil.copy(os.path.join(gltf_dir, b["uri"]), out_dir)
    for img in new_img:
        uri = img["uri"]
        dst = os.path.join(out_dir, uri)
        if not os.path.exists(dst):
            src = os.path.join(gltf_dir, uri)
            if not os.path.exists(src):
                src = os.path.join(pack_dir, "Textures", uri)
            resize(src, dst, 512 if uri.startswith(SMALL) else 1024)


def main():
    nature, village, acg = sys.argv[1:4]
    packs = {"nature": nature, "village": village, "acg": acg}
    for sub, names, pack in (("nature", NATURE, nature), ("village", VILLAGE, village)):
        out = os.path.join(OUT, sub)
        os.makedirs(out, exist_ok=True)
        for n in names:
            copy_model(pack, n, out)
    tex_out = os.path.join(OUT, "textures")
    os.makedirs(tex_out, exist_ok=True)
    for name, (pack, rel) in WORLD_TEXTURES.items():
        resize(os.path.join(packs[pack], rel), os.path.join(tex_out, name), 1024)
    open(os.path.join(OUT, "LICENSES.txt"), "w").write(
        "Art in this folder is CC0 1.0 (public domain):\n"
        "  nature/, village/  - Quaternius (https://quaternius.com): Stylized Nature MegaKit,\n"
        "                       Medieval Village MegaKit (standard editions)\n"
        "  textures/grass.jpg, textures/cliff.jpg - ambientCG (https://ambientcg.com): Grass005, Rock023\n"
        "  other textures/    - Quaternius Medieval Village MegaKit\n")
    print("assets ready in", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
