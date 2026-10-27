"""Small 2D cut-out animation engine for the Red Rising video.

Every shot is a function ``draw(t, d) -> PIL.Image`` returning one 1920x1080
RGB frame for local time ``t`` (seconds) of a shot lasting ``d`` seconds.
The helpers here cover what the storyboard needs: slow camera moves on a
background, cut-out characters that slide in and breathe, lower thirds,
chapter cards, centred titles, dust, grain and fades.
"""
import math
import os
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
FPS = 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")

CREAM = (236, 230, 218)
GOLD = (212, 166, 58)
CRIMSON = (200, 16, 46)
INK = (8, 8, 10)


# ---------------------------------------------------------------- easing

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def lerp(a, b, x):
    return a + (b - a) * x


def ramp(t, start, length):
    """0 before ``start``, 1 after ``start + length``, eased in between."""
    return ease_out((t - start) / length) if length > 0 else float(t >= start)


# ---------------------------------------------------------------- assets

def _find(folder, asset_id):
    d = os.path.join(ASSETS, folder)
    for f in sorted(os.listdir(d)):
        if f.startswith(asset_id):
            return os.path.join(d, f)
    raise FileNotFoundError(f"{asset_id} not in {d}")


@lru_cache(maxsize=None)
def background(asset_id, blur=0, dim=0.0):
    """Background scaled to cover 1920x1080 at 1.35x so the camera has room."""
    im = Image.open(_find("backgrounds", asset_id)).convert("RGB")
    scale = max(W / im.width, H / im.height) * 1.35
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if dim:
        im = Image.blend(im, Image.new("RGB", im.size, INK), dim)
    return im


@lru_cache(maxsize=None)
def character(asset_id, height):
    im = Image.open(_find("characters/cutouts", asset_id)).convert("RGBA")
    scale = height / im.height
    return im.resize((round(im.width * scale), height), Image.LANCZOS)


@lru_cache(maxsize=None)
def cover(name, height):
    im = Image.open(_find("covers", name)).convert("RGBA")
    scale = height / im.height
    return im.resize((round(im.width * scale), height), Image.LANCZOS)


@lru_cache(maxsize=None)
def font(name, size):
    return ImageFont.truetype(os.path.join(ASSETS, "fonts", f"{name}.ttf"), size)


# ---------------------------------------------------------------- camera

def camera(src, zoom, cx, cy):
    """Crop ``src`` around (cx, cy) in 0..1 coordinates at ``zoom`` (1 = the
    full 1.35x-oversized image fits the frame) and return a 1920x1080 frame."""
    base = min(src.width / W, src.height / H)
    cw, ch = W * base / zoom, H * base / zoom
    x = clamp(cx * src.width - cw / 2, 0, src.width - cw)
    y = clamp(cy * src.height - ch / 2, 0, src.height - ch)
    return src.resize((W, H), Image.BILINEAR, box=(x, y, x + cw, y + ch))


def move(src, t, d, z0, z1, c0, c1, ease=ease_in_out):
    k = ease(t / d)
    return camera(src, lerp(z0, z1, k), lerp(c0[0], c1[0], k), lerp(c0[1], c1[1], k))


# ---------------------------------------------------------------- layers

def place(frame, sprite, x, y, alpha=1.0):
    """Composite an RGBA sprite with its bottom-centre at (x, y)."""
    if alpha <= 0:
        return frame
    if alpha < 1:
        sprite = sprite.copy()
        sprite.putalpha(sprite.getchannel("A").point(lambda a: int(a * alpha)))
    out = frame.convert("RGBA")
    out.alpha_composite(sprite, (round(x - sprite.width / 2), round(y - sprite.height)))
    return out.convert("RGB")


def actor(frame, asset_id, height, x, y, t, enter=None, alpha=1.0, breathe=True):
    """A cut-out character. ``enter`` = (from_x, start, length) slides it in."""
    if enter:
        fx, start, length = enter
        k = ramp(t, start, length)
        x = lerp(fx, x, k)
        alpha *= k
    h = height
    if breathe:
        h = round(height * (1 + 0.006 * math.sin(t * 1.9)))
    return place(frame, character(asset_id, h), x, y, alpha)


def shadowed(sprite, radius=18, offset=(14, 18), opacity=0.55):
    pad = radius * 3
    sh = Image.new("RGBA", (sprite.width + pad * 2, sprite.height + pad * 2), (0, 0, 0, 0))
    a = sprite.getchannel("A").point(lambda v: int(v * opacity))
    sh.paste(Image.new("RGBA", sprite.size, (0, 0, 0, 255)), (pad + offset[0], pad + offset[1]), a)
    sh = sh.filter(ImageFilter.GaussianBlur(radius))
    sh.alpha_composite(sprite, (pad, pad))
    return sh


def dim(frame, amount):
    return Image.blend(frame, Image.new("RGB", frame.size, INK), amount) if amount > 0 else frame


def fade(frame, t, d, fin=0.0, fout=0.0):
    a = 1.0
    if fin:
        a = min(a, clamp(t / fin))
    if fout:
        a = min(a, clamp((d - t) / fout))
    return dim(frame, 1 - a)


# ---------------------------------------------------------------- type

def _text(draw, xy, text, fnt, fill, spacing=0, anchor="la"):
    if not spacing:
        draw.text(xy, text, font=fnt, fill=fill, anchor=anchor)
        return
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x, y = xy
    if anchor[0] == "m":
        x -= total / 2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill, anchor="l" + anchor[1])
        x += w + spacing


def lower_third(frame, t, start, title, sub, out=None):
    """Name strip bottom-left: crimson bar, Cinzel title, Inter subtitle."""
    k = ramp(t, start, 0.6)
    if out is not None:
        k = min(k, 1 - ramp(t, out, 0.4))
    if k <= 0:
        return frame
    ft, fs = font("Cinzel-Bold", 58), font("Inter-Regular", 30)
    probe = ImageDraw.Draw(frame)
    w = max(probe.textlength(title, font=ft) + 6 * len(title), probe.textlength(sub, font=fs)) + 70
    x0, y1 = 90 - (1 - k) * 60, H - 90
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    dr.rectangle((x0, y1 - 138, x0 + w, y1), fill=(8, 8, 10, int(200 * k)))
    dr.rectangle((x0, y1 - 138, x0 + 8, y1), fill=CRIMSON + (int(255 * k),))
    _text(dr, (x0 + 34, y1 - 112), title, ft, CREAM + (int(255 * k),), spacing=6)
    _text(dr, (x0 + 34, y1 - 46), sub, fs, (201, 194, 180, int(255 * k)))
    out_im = frame.convert("RGBA")
    out_im.alpha_composite(layer)
    return out_im.convert("RGB")


def centred_title(frame, t, start, title, sub, size=150, track_from=60, track_to=14):
    k = ramp(t, start, 1.6)
    ks = ramp(t, start + 1.1, 0.9)
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    _text(dr, (W / 2, H / 2 - 30), title, font("Cinzel-Bold", size), CREAM + (int(255 * k),),
          spacing=lerp(track_from, track_to, k), anchor="ms")
    if ks > 0:
        _text(dr, (W / 2, H / 2 + 60), sub, font("Inter-SemiBold", 34), GOLD + (int(255 * ks),),
              spacing=10, anchor="mm")
        lw = 120 * ks
        dr.rectangle((W / 2 - lw, H / 2 + 8, W / 2 + lw, H / 2 + 12), fill=CRIMSON + (int(255 * ks),))
    out_im = frame.convert("RGBA")
    out_im.alpha_composite(layer)
    return out_im.convert("RGB")


# ---------------------------------------------------------------- texture

class Dust:
    """Slow drifting specks lit like dust in a lamp beam (foreground layer)."""

    def __init__(self, n=140, seed=7):
        rnd = random.Random(seed)
        self.p = [(rnd.random() * W, rnd.random() * H, rnd.uniform(1, 3.2),
                   rnd.uniform(-14, 14), rnd.uniform(-22, -6), rnd.uniform(0, 6.28)) for _ in range(n)]

    def draw(self, frame, t, alpha=1.0):
        layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(layer)
        for x, y, r, vx, vy, ph in self.p:
            px, py = (x + vx * t) % W, (y + vy * t) % H
            a = int(alpha * 120 * (0.6 + 0.4 * math.sin(t * 1.3 + ph)))
            dr.ellipse((px - r, py - r, px + r, py + r), fill=(240, 205, 150, a))
        out_im = frame.convert("RGBA")
        out_im.alpha_composite(layer)
        return out_im.convert("RGB")


# One fixed grain layer: the artwork already carries paper texture, and grain
# that changes every frame makes the video several times larger to encode.
_GRAIN = np.random.default_rng(3).normal(0, 3.0, (H, W, 1)).astype(np.int16)


def grain(frame, i):
    arr = np.asarray(frame, dtype=np.int16) + _GRAIN
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
