# Brass Ledger — Design System

One identity for every product, guide PDF, listing image and pin. Tokens live in `design-tokens.json`;
`build/common.py` (spreadsheets) and `build/brand.py` (images, PDFs, logo) read the same values.

**Brand.** Brass Ledger. Tagline: "Simple tools for small business numbers." Descriptor under the logo: SMALL BUSINESS TOOLS.
**Voice.** Plain, direct, practical. Lead with the outcome. No hype words, no exclamation marks.

## Colours

| Role | Hex | Used for |
|---|---|---|
| Ledger green | `#1F3D36` | Title bars, primary blocks, heading text, sidebar |
| Brass | `#D29A3A` | Accents, rules, key numbers, kickers |
| Paper | `#FAF7F2` | Backgrounds |
| Ink / secondary | `#222222` / `#444444` | Body text / secondary text |
| Border | `#E6E1D8` | Cell and card borders |
| White | `#FFFFFF` | Input cells and cards |
| Positive | `#2E7D4F` | Done, income, on track |
| Supporting shades | `#F1ECE2` calculated cells · `#F6EBD3` brass tint · `#E4EFE8` green tint · `#B3382C` / `#F8E4E0` warning |

Token keys keep their older role names (`deep_navy` is the darkest brand colour, now ledger green) so every generator picks the palette up.

## Type

- Headings: Fraunces 600, optical size 144, letter-spacing −0.02em.
- Body, labels and all spreadsheet cells: Inter.
- Kickers: Inter 700, uppercase, letter-spacing 0.2–0.3em, brass.
- Spreadsheet titles: Georgia in the Excel editions (Fraunces is not available in Excel), Fraunces in the Google Sheets editions.
- Inter is not bundled with Excel. Where it is not installed, Excel shows its fallback font; layout is checked with a 10 % width margin.

## Logo

Wordmark "Brass Ledger" in Fraunces 600 with a full-width brass double rule beneath: thick 0.075em, gap 0.05em, thin 0.022em.
Green on light, paper on green. Monogram "BL": paper on green with the same double rule. Drawn by `brand.wordmark()` and `brand.monogram()`; reference art in `brand/`.

## Spreadsheets

- Title bar: green fill, paper title, "BRASS LEDGER" small in brass at the right.
- Sheet background paper; input cells white with `#E6E1D8` borders; calculated cells shaded.
- Results: green blocks with the main figure in brass (`common.green_tile`).
- Section labels: uppercase green kickers under a brass rule (`common.section`).
- Gridlines hidden; column A is a gutter; conditional formatting only refers to its own sheet (a Google Sheets requirement).
- Excel editions add a shape layer (sidebar icons, dashboard cards) from `build/drawing_inject.py`; Google Sheets editions use a cell sidebar with text links.

## Listing images (`build/brand_listing.py`)

2700 × 2025 px (4:3). Paper background, brass kicker, large green Fraunces headline, short brass double rule under it, logo bottom-left.
Always seven, in this order: 1 hero with the product on screen · 2 what's included · 3 main tool close-up · 4 dashboard or summary ·
5 how it works in three steps · 6 compatibility · 7 what you receive. Only real screenshots of the finished product.
Copy and screenshot choices: `build/brand_listings_content.py`. Pins (1000 × 1500) follow the same rules: `build/pins.py`.

## Guide PDFs (`build/md_to_pdf.py`) and planner (`build/planner_pdf.py`)

Paper pages, green title block with a brass kicker and double rule, Fraunces headings, Inter body, wordmark bottom-left on every page.
