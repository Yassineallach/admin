"""Logo helper: the supplied Brass Ledger logo PNG with its white background made transparent."""
from pathlib import Path

from PIL import Image

LOGO_PNG = Path("/home/user/admin/productivity-bundle/brand/logo_light.png")


def logo_rgba(width):
    im = Image.open(LOGO_PNG).convert("RGBA")
    im = im.crop(im.convert("L").point(lambda v: 255 if v < 245 else 0).getbbox())
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            lum = min(r, g, b)
            if lum > 235:
                px[x, y] = (r, g, b, int(255 * max(0, 255 - lum) / 20))
    return im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
