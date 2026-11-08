"""Minimal line/solid icons rendered with Pillow (drawn at 4x, downsampled for smooth edges)."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw

S = 256  # working canvas


def _new():
    return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def _rgb(hexs, a=255):
    h = hexs.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def _out(img, size):
    buf = io.BytesIO()
    img.resize((size, size), Image.LANCZOS).save(buf, "PNG")
    return buf.getvalue()


def bar_chart(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    for i, h in enumerate((90, 150, 120, 190)):
        x = 40 + i * 48
        d.rounded_rectangle((x, 220 - h, x + 30, 220), 8, fill=col)
    return _out(im, size)


def people(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.ellipse((150, 50, 210, 110), fill=col)
    d.rounded_rectangle((128, 122, 236, 200), 40, fill=col)
    d.ellipse((50, 40, 126, 116), fill=col)
    d.rounded_rectangle((20, 130, 156, 226), 48, fill=col)
    return _out(im, size)


def donut(c="FFFFFF", size=64, accent=None):
    im = _new(); d = ImageDraw.Draw(im)
    d.ellipse((24, 24, 232, 232), fill=_rgb(c))
    if accent:
        d.pieslice((24, 24, 232, 232), -90, 10, fill=_rgb(accent))
    d.ellipse((84, 84, 172, 172), fill=(0, 0, 0, 0))
    return _out(im, size)


def money(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.rounded_rectangle((20, 70, 236, 186), 14, outline=col, width=16)
    d.ellipse((100, 100, 156, 156), outline=col, width=14)
    d.ellipse((46, 118, 66, 138), fill=col)
    d.ellipse((190, 118, 210, 138), fill=col)
    return _out(im, size)


def clipboard(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.rounded_rectangle((50, 40, 206, 236), 16, outline=col, width=16)
    d.rounded_rectangle((92, 20, 164, 60), 10, fill=col)
    for y in (100, 140, 180):
        d.rounded_rectangle((84, y, 104, y + 14), 4, fill=col)
        d.rounded_rectangle((116, y, 176, y + 14), 4, fill=col)
    return _out(im, size)


def calendar(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.rounded_rectangle((30, 50, 226, 226), 18, outline=col, width=16)
    d.rectangle((30, 50, 226, 100), fill=col)
    for x in (70, 170):
        d.rounded_rectangle((x, 24, x + 18, 72), 8, fill=col)
    for i in range(3):
        for j in range(2):
            d.rounded_rectangle((64 + i * 48, 124 + j * 44, 92 + i * 48, 148 + j * 44), 5, fill=col)
    return _out(im, size)


def kanban(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    for i, h in enumerate((170, 120, 190)):
        x = 30 + i * 70
        d.rounded_rectangle((x, 36, x + 56, 36 + h), 12, fill=col)
    return _out(im, size)


def gantt(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    for i, (x0, x1) in enumerate(((30, 140), (80, 200), (120, 230), (60, 170))):
        y = 36 + i * 50
        d.rounded_rectangle((x0, y, x1, y + 32), 12, fill=col)
    return _out(im, size)


def gear(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    for y, k in ((60, 80), (128, 170), (196, 110)):
        d.rounded_rectangle((30, y - 8, 226, y + 8), 8, fill=col)
        d.ellipse((k - 22, y - 22, k + 22, y + 22), fill=col)
    return _out(im, size)


def filt(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.polygon([(26, 40), (230, 40), (150, 134), (150, 216), (106, 236), (106, 134)], fill=col)
    return _out(im, size)


def book(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.rounded_rectangle((30, 40, 124, 220), 12, outline=col, width=16)
    d.rounded_rectangle((132, 40, 226, 220), 12, outline=col, width=16)
    return _out(im, size)


def scale(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.rounded_rectangle((120, 30, 136, 220), 6, fill=col)
    d.rounded_rectangle((40, 60, 216, 76), 6, fill=col)
    d.pieslice((20, 70, 110, 160), 0, 180, fill=col)
    d.pieslice((146, 70, 236, 160), 0, 180, fill=col)
    d.rounded_rectangle((80, 210, 176, 230), 8, fill=col)
    return _out(im, size)


ICONS = {"bar_chart": bar_chart, "people": people, "donut": donut, "money": money, "clipboard": clipboard,
         "calendar": calendar, "kanban": kanban, "gantt": gantt, "gear": gear, "filter": filt, "book": book, "scale": scale}


def clock(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.ellipse((24, 24, 232, 232), outline=col, width=18)
    d.rounded_rectangle((119, 64, 137, 136), 8, fill=col)
    d.rounded_rectangle((119, 120, 186, 138), 8, fill=col)
    return _out(im, size)


def question(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.ellipse((24, 24, 232, 232), outline=col, width=16)
    d.arc((86, 60, 170, 140), 180, 60, fill=col, width=18)
    d.rounded_rectangle((119, 128, 137, 160), 8, fill=col)
    d.ellipse((116, 176, 140, 200), fill=col)
    return _out(im, size)


def table(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.rounded_rectangle((26, 40, 230, 216), 14, outline=col, width=16)
    d.rectangle((26, 40, 230, 92), fill=col)
    d.rounded_rectangle((26, 144, 230, 156), 4, fill=col)
    d.rounded_rectangle((100, 92, 112, 216), 4, fill=col)
    return _out(im, size)


def repeat(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.arc((36, 36, 220, 220), 200, 340, fill=col, width=20)
    d.arc((36, 36, 220, 220), 20, 160, fill=col, width=20)
    d.polygon([(198, 52), (232, 106), (172, 108)], fill=col)
    d.polygon([(58, 204), (24, 150), (84, 148)], fill=col)
    return _out(im, size)


def week(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.rounded_rectangle((30, 50, 226, 226), 18, outline=col, width=16)
    d.rectangle((30, 50, 226, 100), fill=col)
    for x in (70, 170):
        d.rounded_rectangle((x, 24, x + 18, 72), 8, fill=col)
    d.rounded_rectangle((60, 140, 196, 170), 8, fill=col)
    return _out(im, size)


def stack(c="FFFFFF", size=64):
    im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
    d.polygon([(128, 30), (230, 82), (128, 134), (26, 82)], fill=col)
    d.line([(26, 128), (128, 180), (230, 128)], fill=col, width=18)
    d.line([(26, 172), (128, 224), (230, 172)], fill=col, width=18)
    return _out(im, size)


ICONS.update({"clock": clock, "question": question, "table": table, "repeat": repeat, "week": week, "stack": stack})


def week_num(n):
    """Calendar icon with a bold number on it (Week 1-6 tabs)."""
    from PIL import ImageFont

    def make(c="FFFFFF", size=64):
        im = _new(); d = ImageDraw.Draw(im); col = _rgb(c)
        d.rounded_rectangle((30, 50, 226, 226), 18, outline=col, width=16)
        d.rectangle((30, 50, 226, 100), fill=col)
        for x in (70, 170):
            d.rounded_rectangle((x, 24, x + 18, 72), 8, fill=col)
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 118)
        d.text((128, 166), str(n), font=f, fill=col, anchor="mm")
        return _out(im, size)
    return make
