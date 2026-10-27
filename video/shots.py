"""Shot list: each entry is (shot id, duration in seconds, draw function).

Durations come from the retimed storyboard. Narration for each shot starts
VO_OFFSET seconds after the shot begins.
"""
from functools import lru_cache

from PIL import Image

from engine import (CREAM, H, W, Dust, actor, background, camera, centred_title, character, cover,
                    dim, fade, lerp, lower_third, move, place, ramp, shadowed)

VO_OFFSET = {"default": 0.3, "S06": 0.6}

_dust = Dust()


@lru_cache(maxsize=None)
def world(bg_id, *actors):
    """Background with characters painted into it, so they move with the camera.
    ``actors`` are (asset_id, height, x, y) in background-pixel coordinates."""
    im = background(bg_id).copy()
    for asset_id, height, x, y in actors:
        im = place(im, character(asset_id, height), x, y)
    return im


# ------------------------------------------------------------------- shots

def s01(t, d):
    # Mine tunnel; a small Darrow stands in the lamp light. Slow push-in.
    bg = background("A01")
    src = world("A01", ("A02", round(bg.height * 0.30), round(bg.width * 0.40), round(bg.height * 0.80)))
    f = move(src, t, d, 1.05, 1.14, (0.52, 0.55), (0.50, 0.60))
    f = _dust.draw(f, t, 0.8)
    return fade(f, t, d, fin=1.2)


def s02(t, d):
    # Darrow enters close; tunnel blurred behind him.
    f = move(background("A01", blur=6, dim=0.35), t, d, 1.25, 1.32, (0.30, 0.55), (0.34, 0.55))
    f = _dust.draw(f, t, 0.5)
    f = actor(f, "A02", 960, 1240 - t * 4, H + 40, t, enter=(2300, 0.0, 0.9))
    return lower_third(f, t, 1.0, "DARROW", "Helldiver · Lykos, Mars")


def s03(t, d):
    # Pan up and across the tunnel; helium-3 capsules rise out of frame.
    f = move(background("A01"), t, d, 1.35, 1.2, (0.25, 0.75), (0.65, 0.45))
    f = _capsules(f, t)
    f = _dust.draw(f, t, 0.7)
    return lower_third(f, t, 1.0, "HELIUM-3", "fuel for terraforming — or so he’s told")


def _capsules(frame, t):
    from PIL import ImageDraw
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    for i in range(5):
        y = H + 100 - ((t * 120 + i * 250) % (H + 300))
        x = 230 + (i % 2) * 46
        dr.rounded_rectangle((x - 17, y - 40, x + 17, y + 40), radius=17,
                             fill=(212, 166, 58, 225), outline=(23, 35, 59, 255), width=4)
        dr.rectangle((x - 17, y - 5, x + 17, y + 5), fill=(23, 35, 59, 255))
    out = frame.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def s04(t, d):
    # Hard cut to the city. Hold one beat, then crane up and out.
    k = ramp(t, 1.0, d - 1.0)
    return camera(background("A03"), lerp(1.3, 1.02, k), 0.5, lerp(0.72, 0.48, k))


def s05(t, d):
    # The Gold who live there; slow push toward him.
    f = camera(background("A03", blur=7, dim=0.45), 1.1, 0.5, 0.5)
    h = round(lerp(980, 1060, t / d))
    return actor(f, "A04", h, 1250, H + 60 + (h - 980) * 0.6, t, enter=(1350, 0.0, 0.7), breathe=False)


@lru_cache(maxsize=None)
def _s06_plate():
    # Darrow alone in the dark mine, tunnel sunk into red-black behind him.
    bg = background("A01", blur=5, dim=0.62)
    return place(bg, character("A02", round(bg.height * 0.92)), bg.width * 0.5, bg.height * 1.04)


def s06(t, d):
    # "Welcome to Red Rising." Slow push toward Darrow's face, lamp glowing.
    f = move(_s06_plate(), t, d, 1.0, 2.1, (0.5, 0.55), (0.5, 0.27))
    f = _vignette(f, 0.75)
    f = _dust.draw(f, t, 0.6)
    return fade(f, t, d, fin=0.4, fout=0.5)


@lru_cache(maxsize=None)
def _vignette_mask():
    from PIL import ImageDraw, ImageFilter
    m = Image.new("L", (W, H), 255)
    ImageDraw.Draw(m).ellipse((-W * 0.15, -H * 0.2, W * 1.15, H * 1.2), fill=0)
    return m.filter(ImageFilter.GaussianBlur(160))


def _vignette(frame, strength):
    dark = Image.new("RGB", (W, H), (20, 4, 6))
    mask = _vignette_mask().point(lambda v: int(v * strength))
    return Image.composite(dark, frame, mask)


def s07(t, d):
    f = move(background("A05"), t, d, 1.0, 1.06, (0.55, 0.5), (0.53, 0.5))
    f = centred_title(dim(f, 0.25), t, 0.4, "RED RISING", "THE TRILOGY · EXPLAINED & REVIEWED")
    return fade(f, t, d, fin=0.6)


def s08(t, d):
    f = move(background("A05", blur=8, dim=0.55), t, d, 1.15, 1.2, (0.5, 0.5), (0.52, 0.5))
    names = ["A07_red-rising", "A07_golden-son", "A07_morning-star"]
    xs = [W / 2 - 400, W / 2, W / 2 + 400]
    for i, (n, x) in enumerate(zip(names, xs)):
        k = ramp(t, 0.2 + i * 0.15, 0.8)
        if k > 0:
            sp = _shadowed_cover(n)
            f = place(f, sp, lerp(x + 900, x, k), 150 + sp.height, k)
    f = lower_third(f, t, 1.0, "PIERCE BROWN", "Red Rising 2014 · Golden Son 2015 · Morning Star 2016")
    return fade(f, t, d, fout=0.5)


@lru_cache(maxsize=None)
def _shadowed_cover(name):
    return shadowed(cover(name, 560))


SHOTS = [
    ("S01", 8.5, s01),
    ("S02", 8.0, s02),
    ("S03", 9.0, s03),
    ("S04", 10.5, s04),
    ("S05", 5.0, s05),
    ("S06", 5.0, s06),
    ("S07", 6.0, s07),
    ("S08", 12.5, s08),
]
