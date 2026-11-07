"""Toolkit for Etsy listing images (shared by every product in the bundle).

Canvas 2400 x 1800 (4:3, Etsy's recommended ratio; thumbnails stay sharp). Brand: teal palette + Inter.
Everything is drawn with Pillow from real product screenshots (render_screens.py), so images never show
features the product doesn't have.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 2400, 1800
FONT_DIR = "/usr/share/fonts/opentype/inter/"
NAVY = (11, 79, 76)
TEAL = (20, 149, 139)
TEAL2 = (31, 169, 156)
MINT = (225, 243, 240)
MINT2 = (237, 245, 244)
DARK = (31, 53, 51)
GREY = (95, 116, 114)
WHITE = (255, 255, 255)
CORAL = (207, 58, 67)
ORANGE = (238, 138, 58)
LAV = (155, 123, 224)


def font(size, weight="Regular"):
    return ImageFont.truetype(f"{FONT_DIR}Inter-{weight}.otf", size)


def canvas(top=MINT2, bottom=WHITE, blobs=True):
    img = Image.new("RGB", (W, H), bottom)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3)))
    if blobs:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ld.ellipse((-300, -350, 700, 650), fill=(31, 169, 156, 38))
        ld.ellipse((1900, 1250, 2800, 2150), fill=(155, 123, 224, 30))
        layer = layer.filter(ImageFilter.GaussianBlur(60))
        img = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    return img


def shadow(img, box, radius=36, blur=40, offset=(0, 22), color=(11, 79, 76, 70)):
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).rounded_rectangle((x0 + offset[0], y0 + offset[1], x1 + offset[0], y1 + offset[1]), radius, fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def card(img, box, radius=36, fill=WHITE, shade=True):
    if shade:
        img = shadow(img, box, radius)
    ImageDraw.Draw(img).rounded_rectangle(box, radius, fill=fill)
    return img


def rounded_paste(img, shot, box, radius=24):
    """Paste `shot` resized to cover box (cropping overflow), with rounded corners."""
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    sw, sh = shot.size
    scale = max(bw / sw, bh / sh)
    shot = shot.resize((int(sw * scale), int(sh * scale)), Image.LANCZOS)
    shot = shot.crop((0, 0, bw, bh))
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw - 1, bh - 1), radius, fill=255)
    img.paste(shot, (x0, y0), mask)
    return img


def fit(shot, max_w, max_h):
    sw, sh = shot.size
    s = min(max_w / sw, max_h / sh)
    return shot.resize((int(sw * s), int(sh * s)), Image.LANCZOS)


def framed(img, shot, x, y, max_w, max_h, radius=22, border=10):
    """Screenshot in a white rounded frame with a soft shadow; returns (img, box)."""
    s = fit(shot, max_w - 2 * border, max_h - 2 * border)
    box = (x, y, x + s.width + 2 * border, y + s.height + 2 * border)
    img = card(img, box, radius)
    img = rounded_paste(img, s, (x + border, y + border, x + border + s.width, y + border + s.height), radius - 6)
    return img, box


def laptop(img, shot, cx, top, screen_w):
    """Laptop mockup: dark bezel, screen showing `shot` (cover-cropped from the top), aluminium base."""
    screen_h = int(screen_w * 10 / 16)
    bez = int(screen_w * 0.028)
    x0 = cx - screen_w // 2 - bez
    x1 = cx + screen_w // 2 + bez
    y0, y1 = top, top + screen_h + 2 * bez
    img = shadow(img, (x0, y0, x1, y1 + 40), radius=40, blur=50, offset=(0, 40), color=(11, 79, 76, 80))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0, y0, x1, y1), 34, fill=(28, 36, 38))
    s = shot
    scale = screen_w / s.width
    s = s.resize((screen_w, int(s.height * scale)), Image.LANCZOS)
    s = s.crop((0, 0, screen_w, min(screen_h, s.height)))
    img.paste(s, (x0 + bez, y0 + bez))
    d = ImageDraw.Draw(img)
    d.ellipse((cx - 6, y0 + bez // 2 - 6, cx + 6, y0 + bez // 2 + 6), fill=(60, 70, 72))
    bw = int(screen_w * 1.16)
    d.rounded_rectangle((cx - bw // 2, y1 - 4, cx + bw // 2, y1 + 30), 14, fill=(200, 208, 210))
    d.rounded_rectangle((cx - 130, y1 - 4, cx + 130, y1 + 10), 8, fill=(170, 178, 180))
    return img, (x0, y0, x1, y1 + 30)


def pill(img, xy, text, size=34, fill=TEAL, color=WHITE, pad=(34, 16), weight="SemiBold", anchor="l"):
    d = ImageDraw.Draw(img)
    f = font(size, weight)
    tw = d.textlength(text, font=f)
    x, y = xy
    w, h = tw + 2 * pad[0], size + 2 * pad[1]
    if anchor == "c":
        x -= w / 2
    d.rounded_rectangle((x, y, x + w, y + h), h / 2, fill=fill)
    d.text((x + pad[0], y + pad[1] - size * 0.12), text, font=f, fill=color)
    return x + w


def text(img, xy, s, size, weight="Regular", color=DARK, anchor="la", spacing=10, max_w=None):
    d = ImageDraw.Draw(img)
    f = font(size, weight)
    if max_w:
        words, lines, cur = s.split(), [], ""
        for w_ in words:
            t = (cur + " " + w_).strip()
            if d.textlength(t, font=f) <= max_w:
                cur = t
            else:
                lines.append(cur)
                cur = w_
        lines.append(cur)
        s = "\n".join(lines)
    d.multiline_text(xy, s, font=f, fill=color, anchor=anchor, spacing=spacing)
    bbox = d.multiline_textbbox(xy, s, font=f, anchor=anchor, spacing=spacing)
    return bbox


def icon_bullet(img, xy, icon_png_bytes, title, body, w=700, circle=TEAL, title_size=40, body_size=30):
    import io
    x, y = xy
    d = ImageDraw.Draw(img)
    d.ellipse((x, y, x + 84, y + 84), fill=circle)
    ic = Image.open(io.BytesIO(icon_png_bytes)).convert("RGBA").resize((46, 46), Image.LANCZOS)
    img.paste(ic, (x + 19, y + 19), ic)
    b = text(img, (x + 110, y + 2), title, title_size, "Bold", DARK)
    b2 = text(img, (x + 110, b[3] + 12), body, body_size, "Regular", GREY, max_w=w - 110)
    return max(b2[3], y + 84)


def heading(img, title, sub=None, y=110, size=92, color=NAVY):
    b = text(img, (W // 2, y), title, size, "ExtraBold", color, anchor="ma")
    if sub:
        b = text(img, (W // 2, b[3] + 30), sub, 44, "Medium", TEAL, anchor="ma")
    return b[3]


def footer(img, s="Instant download  ·  Excel + Google Sheets  ·  No macros"):
    d = ImageDraw.Draw(img)
    d.rectangle((0, H - 96, W, H), fill=NAVY)
    text(img, (W // 2, H - 48), s, 34, "SemiBold", WHITE, anchor="mm")
