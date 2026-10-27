"""Remove the flat cream background from character art.

Pass 1 flood-fills from the image border, so background connected to the edge
goes. Pass 2 removes enclosed pockets (gaps between an arm and the body, inside
curls) whose colour is very close to the background, as long as the pocket is
big enough to be a real gap rather than a highlight. Edges get a soft feather.
"""
import os
import re
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SENTINEL = (255, 0, 255)


def border_fill_mask(im, thresh):
    w, h = im.size
    work = im.copy()
    step = 24
    seeds = [(x, 0) for x in range(0, w, step)] + [(x, h - 1) for x in range(0, w, step)]
    seeds += [(0, y) for y in range(0, h, step)] + [(w - 1, y) for y in range(0, h, step)]
    for s in seeds:
        if work.getpixel(s) != SENTINEL:
            ImageDraw.floodfill(work, s, SENTINEL, thresh=thresh)
    arr = np.asarray(work)
    return np.all(arr == SENTINEL, axis=-1)


def enclosed_pockets(rgb, removed, bg, tol, min_area):
    dist = np.abs(rgb.astype(int) - bg).max(axis=-1)
    cand = (dist <= tol) & ~removed
    h, w = cand.shape
    seen = np.zeros_like(cand)
    out = np.zeros_like(cand)
    for y0, x0 in zip(*np.nonzero(cand)):
        if seen[y0, x0]:
            continue
        comp = []
        q = deque([(y0, x0)])
        seen[y0, x0] = True
        while q:
            y, x = q.popleft()
            comp.append((y, x))
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and cand[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        if len(comp) >= min_area:
            ys, xs = zip(*comp)
            out[list(ys), list(xs)] = True
    return out


def cutout(path, out_path, thresh=34, tol=16, min_area=60):
    im = Image.open(path).convert("RGB")
    rgb = np.asarray(im)
    removed = border_fill_mask(im, thresh)
    bg = np.median(rgb[removed], axis=0) if removed.any() else rgb[0, 0]
    removed |= enclosed_pockets(rgb, removed, bg, tol, min_area)
    mask = Image.fromarray(np.where(removed, 0, 255).astype(np.uint8), "L")
    mask = mask.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    rgba = im.convert("RGBA")
    rgba.putalpha(mask)
    rgba = rgba.crop(rgba.getbbox())
    rgba.save(out_path)
    return rgba.size


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    for f in sorted(os.listdir(src)):
        m = re.match(r"(A\d\d)\s*\W+\s*(.+)\.png$", f)
        if not m:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
        size = cutout(os.path.join(src, f), os.path.join(dst, f"{m.group(1)}_{slug}.png"))
        print(f"{m.group(1)}_{slug}.png", size)
