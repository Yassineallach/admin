# The Ultimate Productivity Bundle

Four standalone products that share one design system:

| # | Product | Status | Formats |
|---|---|---|---|
| 1 | Ultimate Project Manager (15 tabs) | ✅ Built, validated, Etsy listing ready | Excel .xlsx + Google Sheets edition, each as DEMO and BLANK |
| 2 | Ultimate OneNote Planner (212 pages) | ✅ Built, validated, Etsy listing ready (seller exports the .onepkg) | OneNote notebook via Graph importer → .onepkg, plus hyperlinked PDF |
| 3 | Weekly Planner Pro (8 tabs) | ✅ Built, validated, Etsy listing ready | Excel .xlsx + Google Sheets edition, each as DEMO and BLANK |
| 4 | Ultimate Budget Spreadsheet (28 tabs) | ✅ Built, validated, Etsy listing ready | Excel .xlsx + Google Sheets edition, each as DEMO and BLANK |

## Layout

```
productivity-bundle/
  design-system/        design-tokens.json + DESIGN_SYSTEM.md (palette, cell conventions, typography)
  build/                Python generators and validators (openpyxl, LibreOffice for recalculation)
    common.py           shared styles/helpers built from design-tokens.json
    build_project_manager.py      -> dist/01_Ultimate_Project_Manager/
    validate_project_manager.py   independent QA (recalc + 530 value checks)
    md_to_pdf.py        branded PDF guides from Markdown
  dist/                 deliverables, one folder per product (zipped at the end)
```

## Rebuild Product 1

```bash
cd productivity-bundle/build
python3 build_project_manager.py          # writes the 4 workbooks
python3 validate_project_manager.py       # needs LibreOffice; exits non-zero on any failure
python3 md_to_pdf.py ../dist/01_Ultimate_Project_Manager/Guides/*.md
```

Requirements: Python 3.10+, `openpyxl`, `reportlab`, and LibreOffice (`soffice`) for recalculation.
The validator uses a recalc helper script; pass `--recalc /path/to/recalc.py` if it isn't found automatically.

## Rebuild Product 2

```bash
cd productivity-bundle/build
python3 onenote_html.py                   # OneNote pages + manifest -> dist/02_Ultimate_OneNote_Planner/OneNote_Import/
python3 planner_pdf.py                    # hyperlinked PDF planner (226 pages)
python3 validate_planner.py               # spec counts, dates, HTML subset, links, PDF, importer vs mock Graph
python3 md_to_pdf.py ../dist/02_Ultimate_OneNote_Planner/Guides/*.md
cp onenote_import.py ../dist/02_Ultimate_OneNote_Planner/OneNote_Import/
python3 listing_images_planner.py         # 10 listing photos from real PDF pages
python3 build_listing_package_planner.py  # etsy_upload/ (add the exported .onepkg first)
```

The native notebook is built in the seller's Microsoft account by `onenote_import.py` (Microsoft Graph) and exported
from OneNote for Windows as `.onepkg`. See `Guides/Seller_Guide_Build_And_Export_OneNote.md`.

## Rebuild Product 3

```bash
cd productivity-bundle/build
python3 build_weekly_planner.py           # writes the 4 workbooks -> dist/03_Weekly_Planner_Pro/
python3 validate_weekly_planner.py        # LibreOffice recalc + 3,018 value/scenario checks
python3 md_to_pdf.py ../dist/03_Weekly_Planner_Pro/Guides/*.md
python3 listing_images_wp.py --reshoot    # real screenshots -> 10 listing photos
python3 build_listing_package_wp.py       # etsy_upload/ (ZIP + START_HERE.pdf)
```

## Rebuild Product 4

```bash
cd productivity-bundle/build
python3 build_budget.py                   # writes the 4 workbooks -> dist/04_Ultimate_Budget_Spreadsheet/
python3 validate_budget.py                # LibreOffice recalc + 2,283 checks against an independent Python model
python3 md_to_pdf.py ../dist/04_Ultimate_Budget_Spreadsheet/Guides/*.md
python3 listing_images_bg.py --reshoot    # real screenshots -> 10 listing photos
python3 build_listing_package_bg.py       # etsy_upload/ (ZIP + START_HERE.pdf)
```

## Mini-products (focused variants, separate listings)

`build_minis.py` builds six standalone trackers from the same tested engine — Debt Payoff Calculator, Sinking Funds
Tracker, Net Worth Tracker, No-Spend Challenge Tracker, Investment Growth Calculator, Habit Tracker — each in Excel and
Google Sheets editions, DEMO and BLANK (`dist/05_Mini_Products/`).

```bash
cd productivity-bundle/build
python3 build_minis.py                    # 24 workbooks
python3 validate_minis.py                 # LibreOffice recalc (0 errors) + 562 value checks
python3 listing_minis.py --reshoot        # screenshots, 6 images, LISTING.md, etsy_upload/ per product
```

## Bundle, pins and videos

```bash
cd productivity-bundle/build
python3 build_bundle.py       # listings/06_Ultimate_Productivity_Bundle/: one ZIP with the three spreadsheets, 6 images, LISTING.md
python3 pins.py               # listings/pins/: one 1000x1500 Pinterest pin per listing + PINS.md (titles, descriptions)
python3 listing_video.py      # a 14 s slideshow video per listing
python3 stress_dates.py       # future-date test: leap day 2028, July-June budget year, Sunday start, 2030
```

Both spreadsheet editions use Arial, so the layout is the same in every Excel version, Google Sheets and the test renderer.
The planner ships as two PDFs: dated 2027 and undated (`planner_pdf.py` builds both).

## Etsy listings (built alongside each product)

Every product gets a matching listing in `listings/<product>/`:

| File | What it is |
|---|---|
| `LISTING.md` | Title, 13 tags, description, details, price suggestion, FAQ, photo order + alt text, seller checklist |
| `listing_config.json` | Your Google Sheets "make a copy" links and shop name |
| `images/` *(generated)* | 10 listing photos, 2400×1800, built from real screenshots of the product |
| `etsy_upload/` *(generated)* | The files buyers download: product ZIP + START_HERE.pdf |

```bash
cd productivity-bundle/build
python3 render_screens.py ../dist/01_Ultimate_Project_Manager/Excel/Ultimate_Project_Manager_Excel_DEMO.xlsx \
        ../listings/01_Ultimate_Project_Manager/screens      # real screenshots of every tab
python3 listing_images_pm.py                                 # 10 listing photos
python3 build_listing_package_pm.py                          # etsy_upload/ (ZIP + START_HERE.pdf)
```

`listing_kit.py` holds the shared image toolkit (brand canvas, laptop mockup, framed screenshots, pills, icon bullets),
so later products reuse the same look.
