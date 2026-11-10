"""Etsy listing images for PRODUCT 2 — Ultimate OneNote Planner (10 images, 2400x1800).

Every screenshot is a real page of the hyperlinked PDF planner (rendered with pdftoppm), so the images never
show pages the product doesn't have. The footer says so: the OneNote notebook holds the same pages, but
OneNote draws them with its own fonts, so the PDF is what the pictures show.

Usage: python listing_images_planner.py
Output: listings/02_Ultimate_OneNote_Planner/images/01_hero.png ... 10_*.png
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import icons  # noqa: E402
import planner_content as PC  # noqa: E402
import planner_pdf as PP  # noqa: E402
from listing_kit import (CORAL, DARK, GREY, LAV, MINT, NAVY, ORANGE, TEAL, W, WHITE, canvas, card,  # noqa: E402
                         footer, framed, heading, icon_bullet, pill, shadow, text)

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "dist" / "02_Ultimate_OneNote_Planner" / "PDF_Planner" / "Ultimate_Planner_2027_Hyperlinked.pdf"
OUT = ROOT / "listings" / "02_Ultimate_OneNote_Planner"
SCREENS, IMAGES = OUT / "screens", OUT / "images"
# The OneNote notebook (.onepkg) only exists once the seller has exported it. Without it, the images sell the product
# as what the buyer really gets: a hyperlinked PDF planner.
HAS_ONEPKG = any((d / "Ultimate_Planner_2027.onepkg").exists() for d in (OUT, ROOT / "dist" / "02_Ultimate_OneNote_Planner"))
FOOT = ("Instant download  ·  OneNote notebook + hyperlinked PDF  ·  Pages shown from the PDF edition" if HAS_ONEPKG
        else "Instant download  ·  Hyperlinked PDF planner  ·  GoodNotes, Notability & more")
BLUE = (47, 111, 170)
GREEN = (31, 169, 156)


def page_numbers():
    PP.MARKS.clear()
    PP.build_pdf(Path(tempfile.mkdtemp()) / "marks.pdf")
    return dict(PP.MARKS)


def render_pages(keys):
    SCREENS.mkdir(parents=True, exist_ok=True)
    marks = page_numbers()
    for k in keys:
        out = SCREENS / f"{k}.png"
        if not out.exists():
            n = str(marks[k])
            subprocess.run(["pdftoppm", "-f", n, "-l", n, "-r", "220", "-png", "-singlefile", str(PDF), str(out)[:-4]], check=True)


def shot(key, top=0.0, bottom=1.0, left=0.0, right=1.0):
    im = Image.open(SCREENS / f"{key}.png").convert("RGB")
    w, h = im.size
    return im.crop((int(w * left), int(h * top), int(w * right), int(h * bottom)))


def ic(name, color="FFFFFF"):
    return icons.ICONS[name](c=color, size=96)


def save(img, name):
    IMAGES.mkdir(parents=True, exist_ok=True)
    img.save(IMAGES / name, "PNG", optimize=True)
    print("wrote", name)


def tablet(img, s, x, y, screen_w):
    """Landscape tablet mockup with `s` filling the screen; returns (img, box)."""
    sh = int(screen_w * s.height / s.width)
    bez = 34
    box = (x, y, x + screen_w + 2 * bez, y + sh + 2 * bez)
    img = shadow(img, box, radius=56, blur=50, offset=(0, 30), color=(11, 79, 76, 85))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, 56, fill=(28, 36, 38))
    img.paste(s.resize((screen_w, sh), Image.LANCZOS), (x + bez, y + bez))
    d = ImageDraw.Draw(img)
    d.ellipse((x + 12, y + bez + sh // 2 - 7, x + 26, y + bez + sh // 2 + 7), fill=(60, 70, 72))
    return img, box


def stats_row(img, y, items, x0=130, x1=W - 130):
    w = (x1 - x0 - 30 * (len(items) - 1)) // len(items)
    x = x0
    for n, label, color in items:
        img = card(img, (x, y, x + w, y + 210), radius=34)
        text(img, (x + w // 2, y + 40), n, 84, "ExtraBold", color, anchor="ma")
        text(img, (x + w // 2, y + 150), label, 30, "SemiBold", GREY, anchor="ma")
        x += w + 30
    return img


# ------------------------------------------------------------------ 1 hero
def hero():
    img = canvas()
    text(img, (150, 170), "ULTIMATE", 64, "SemiBold", TEAL)
    text(img, (150, 250), ("OneNote" if HAS_ONEPKG else "Digital") + "\nPlanner 2027", 140, "ExtraBold", NAVY, spacing=0)
    text(img, (150, 590), "Digital planner for OneNote,\nGoodNotes & PDF apps" if HAS_ONEPKG
         else "Hyperlinked PDF for GoodNotes,\nNotability & PDF apps", 46, "Medium", DARK)
    y = 760
    for t_ in ("Yearly, monthly & 53 weekly pages", "111 professional templates", "8 note layouts", "Fully hyperlinked index & tabs"):
        img = card(img, (150, y, 900, y + 92), radius=46, shade=False, fill=WHITE)
        text(img, (200, y + 46), "✓", 42, "Bold", TEAL, anchor="lm")
        text(img, (260, y + 46), t_, 38, "SemiBold", DARK, anchor="lm")
        y += 118
    pill(img, (150, 1270), "212 PAGES", 40, NAVY)
    pill(img, (470, 1270), "6,400+ LINKS", 40, TEAL)
    pill(img, (150, 1380), "DATED 2027 + UNDATED EDITION", 40, ORANGE)
    img, _ = tablet(img, shot("m1_cal"), 1300, 760, 960)
    img, _ = tablet(img, shot("index"), 1180, 300, 1000)
    footer(img, FOOT)
    save(img, "01_hero.png")


# ------------------------------------------------------------------ 2 what's included
def included():
    img = canvas()
    heading(img, "What's included", "One planner, 212 pages, every page one click from the index")
    img = stats_row(img, 360, [("12", "monthly sections", TEAL), ("53", "weekly trackers", BLUE),
                               ("111", "templates", GREEN), ("8", "note layouts", LAV), ("5", "yearly & start pages", NAVY)])
    img = card(img, (130, 640, W - 130, 1370), radius=40)
    text(img, (190, 690), "111 TEMPLATES IN 10 CATEGORIES", 32, "Bold", TEAL)
    colors = [GREEN, (43, 179, 166), BLUE, LAV, ORANGE, (106, 90, 205), TEAL, CORAL, (70, 100, 130), (226, 110, 30)]
    cats = list(PC.EXPECTED.items())
    for i, (name, n) in enumerate(cats):
        cx, cy = 190 + (i % 2) * 1060, 770 + (i // 2) * 112
        ImageDraw.Draw(img).ellipse((cx, cy + 6, cx + 50, cy + 56), fill=colors[i])
        text(img, (cx + 25, cy + 31), str(n), 26, "Bold", WHITE, anchor="mm")
        text(img, (cx + 80, cy + 31), name, 40, "SemiBold", DARK, anchor="lm")
    img = card(img, (130, 1430, W - 130, 1640), radius=40)
    text(img, (190, 1470), "YOU RECEIVE", 30, "Bold", TEAL)
    x = 190
    for f_ in (("OneNote notebook (.onepkg)",) if HAS_ONEPKG else ()) + ("2027 planner (PDF)", "Undated planner (PDF)", "PDF user guide", "Start Here guide"):
        x = pill(img, (x, 1530), f_, 32, MINT, NAVY) + 26
    footer(img, FOOT)
    save(img, "02_whats_included.png")


# ------------------------------------------------------------------ 3 hyperlinked
def hyperlinked():
    img = canvas()
    heading(img, "Every page is one tap away", "A General Index, contents pages and side tabs on every page")
    img, _ = framed(img, shot("index"), 110, 360, 1450, 1330)
    x, y = 1640, 400
    for icon, t_, b_ in (("book", "General Index", "Jump to any month, week, template or note page"),
                         ("stack", "26 side tabs", "Year, Jan–Dec, Weeks and every template category — on every page"),
                         ("table", "Contents pages", "Each category and the weekly section has its own linked contents"),
                         ("repeat", "⌂ Index link", "Top right of every page takes you straight back"),
                         ("question", "How to use", "A built-in start page explains everything")):
        y = icon_bullet(img, (x, y), ic(icon), t_, b_, w=680, title_size=40, body_size=29) + 46
    footer(img, FOOT)
    save(img, "03_hyperlinked.png")


# ------------------------------------------------------------------ 4 monthly
def monthly():
    img = canvas()
    heading(img, "12 monthly sections", "Calendar  ·  Goals  ·  Reflection — dated 2027, plus an undated edition")
    img, b = framed(img, shot("m1_cal"), 110, 440, 1500, 1240)
    img, b2 = framed(img, shot("m1_goals"), 1660, 440, 630, 560)
    img, b3 = framed(img, shot("m1_refl"), 1660, b2[3] + 110, 630, 560)
    pill(img, (b[0], 360), "Calendar", 36, TEAL)
    pill(img, (b2[0], 360), "Goals", 36, BLUE)
    pill(img, (b3[0], b2[3] + 30), "Reflection", 36, LAV)
    footer(img, FOOT)
    save(img, "04_monthly.png")


# ------------------------------------------------------------------ 5 weekly
def weekly():
    img = canvas()
    heading(img, "53 weekly trackers", "Dated for every week of 2027 — or use the undated edition any year")
    img, _ = framed(img, shot("w1"), 110, 360, 1450, 1330)
    x, y = 1640, 400
    for icon, t_, b_ in (("stack", "Top 3 goals & priorities", "Tick-box lists for the week's focus"),
                         ("calendar", "Daily plan", "Tasks and appointments for each day"),
                         ("repeat", "Habit tracker", "Seven tick boxes per habit"),
                         ("clipboard", "Achievements & notes", "Space to capture the wins"),
                         ("bar_chart", "Weekly reflection", "What went well, what to change, 1–10 score")):
        y = icon_bullet(img, (x, y), ic(icon, ), t_, b_, w=680, circle=BLUE, title_size=40, body_size=29) + 46
    footer(img, FOOT)
    save(img, "05_weekly.png")


# ------------------------------------------------------------------ 6 templates grid
def templates():
    img = canvas()
    heading(img, "111 professional templates", "Projects, meetings, goals, clients, invoices, reports, ideas & more")
    picks = [("project_1", "Project Charter"), ("task_2", "Priority Matrix"), ("meeting_1", "Meeting Notes"),
             ("goal_5", "Habit Tracker"), ("client_4", "Sales Pipeline"), ("invoice_1", "Invoice")]
    cw, chh = 700, 560
    for i, (k, label) in enumerate(picks):
        x, y = 130 + (i % 3) * (cw + 35), 360 + (i // 3) * (chh + 40)
        img, box = framed(img, shot(k, 0, 0.78, 0.035, 1), x, y + 70, cw, chh - 70)
        pill(img, (x, y), label, 32, NAVY)
    footer(img, FOOT)
    save(img, "06_templates.png")


# ------------------------------------------------------------------ 7 categories with names
def categories():
    img = canvas()
    heading(img, "Inside the template library", "Each category opens with a linked contents page")
    secs = {s.name: s for s in PC.build(PC.YEAR)}
    show = ["Project Management", "Professional Development", "Creative Brainstorming", "Task Management",
            "Client & Customer Tracking", "Invoice & Expense Tracking"]
    colors = [(43, 179, 166), (106, 90, 205), (226, 110, 30), GREEN, TEAL, CORAL]
    cw = (W - 260 - 60) // 3
    for i, name in enumerate(show):
        x, y = 130 + (i % 3) * (cw + 30), 330 + (i // 3) * 690
        img = card(img, (x, y, x + cw, y + 650), radius=36)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((x, y, x + cw, y + 90), 36, fill=colors[i])
        d.rectangle((x, y + 50, x + cw, y + 90), fill=colors[i])
        text(img, (x + 34, y + 45), f"{name}  ({len(secs[name].pages)})", 32, "Bold", WHITE, anchor="lm")
        titles = [p.title for p in secs[name].pages]
        more = len(titles) - 7
        lines = titles[:7] + ([f"+ {more} more"] if more > 0 else [])
        for j, t_ in enumerate(lines):
            plus = t_.startswith("+")
            text(img, (x + 40, y + 130 + j * 62), ("" if plus else "•  ") + t_, 30,
                 "SemiBold" if plus else "Regular", TEAL if plus else DARK)
    footer(img, FOOT)
    save(img, "07_template_categories.png")


# ------------------------------------------------------------------ 8 notes
def notes():
    img = canvas()
    heading(img, "8 note layouts", "General, Quick, Research, Meeting, Reading, Project, Ideas, Reflection")
    img, _ = framed(img, shot("note_1"), 110, 360, 1450, 1330)
    x, y = 1640, 400
    for icon, t_, b_ in (("book", "Undated", "Reuse them every year"),
                         ("stack", "Duplicate any page", "Copy a layout as often as you need"),
                         ("clipboard", "Type or handwrite", "Works with keyboard, pen or stylus"),
                         ("calendar", "Linked from the index", "One tap from anywhere in the planner")):
        y = icon_bullet(img, (x, y), ic(icon), t_, b_, w=680, circle=LAV, title_size=40, body_size=29) + 46
    footer(img, FOOT)
    save(img, "08_notes.png")


# ------------------------------------------------------------------ 9 compatibility
def compatibility():
    img = canvas()
    if HAS_ONEPKG:
        heading(img, "Which file do I use?", "Two formats included — pick the one for your app")
    else:
        heading(img, "Works with your favourite apps", "One hyperlinked PDF — open it wherever you take notes")
    rows = [("✓", TEAL, "OneNote for Windows (Microsoft 365)", "OneNote notebook (.onepkg) — real pages, tick boxes, tables, links") if HAS_ONEPKG
            else ("✓", TEAL, "iPad & tablets", "Write with Apple Pencil or a stylus in your favourite PDF note app"),
            ("✓", TEAL, "OneNote (any device)", "Insert the PDF as printouts and write on top (links don't click in printouts)"),
            ("✓", TEAL, "GoodNotes, Notability, Xodo, Drawboard, Samsung Notes", "Hyperlinked PDF — tabs and index links click"),
            ("✓", TEAL, "Paper", "Print the PDF (landscape, US Letter)"),
            ("✗", CORAL, "Not a physical product", "Nothing is shipped — instant digital download")]
    img = card(img, (130, 360, W - 130, 1620), radius=40)
    y = 430
    for mark, color, t_, b_ in rows:
        text(img, (200, y), mark, 50, "Bold", color)
        text(img, (290, y), t_, 40, "SemiBold", DARK, max_w=1000)
        text(img, (1330, y + 6), b_, 32, "Regular", GREY, max_w=900)
        y += 230
    footer(img, FOOT)
    save(img, "09_which_file.png")


# ------------------------------------------------------------------ 10 how it works
def how_it_works():
    img = canvas()
    heading(img, "Start planning in minutes", "Download, open, tap the index")
    steps = [("book", "1. Download", "Get the files from your Etsy Purchases page after checkout."),
             ("stack", "2. Open", "Double-click the .onepkg in OneNote for Windows, or import the PDF into your note app." if HAS_ONEPKG
              else "Import the PDF into GoodNotes, Notability or any PDF note app."),
             ("calendar", "3. Plan", "Start at the General Index. Every month, week and template is one tap away.")]
    x = 130
    for icon, t_, b_ in steps:
        img = card(img, (x, 380, x + 680, 960), radius=40)
        import io
        d = ImageDraw.Draw(img)
        d.ellipse((x + 50, 430, x + 190, 570), fill=TEAL)
        icim = Image.open(io.BytesIO(ic(icon))).convert("RGBA").resize((80, 80), Image.LANCZOS)
        img.paste(icim, (x + 80, 460), icim)
        text(img, (x + 50, 620), t_, 46, "Bold", NAVY)
        text(img, (x + 50, 700), b_, 32, "Regular", GREY, max_w=580)
        x += 735
    img, _ = framed(img, shot("howto", 0, 0.62), 330, 1030, 1740, 620)
    footer(img, FOOT)
    save(img, "10_how_it_works.png")


def main():
    render_pages(["index", "howto", "m1_cal", "m1_goals", "m1_refl", "w1", "project_1", "task_2", "meeting_1",
                  "goal_5", "client_4", "invoice_1", "note_1"])
    for f in (hero, included, hyperlinked, monthly, weekly, templates, categories, notes, compatibility, how_it_works):
        f()


if __name__ == "__main__":
    main()
