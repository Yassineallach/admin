# Ultimate Productivity Bundle — Global Design System

One visual identity shared by all four products (Project Manager, OneNote Planner,
Weekly Planner Pro, Budget Spreadsheet). Machine-readable tokens live in
`design-tokens.json`; the spreadsheet generators import the same values from
`build/common.py`, so the palette is defined in one place.

## Palette (v2 — teal theme)

Role names are unchanged from v1 so every generator picks the theme up automatically
(`deep_navy` is simply "the darkest brand colour").

| Role | Token key | Hex | Used for |
|---|---|---|---|
| Darkest brand | deep_navy | `#0B4F4C` | Sidebar, hero headers, headings, donut "done" |
| Dark brand | midnight_blue | `#0F6E68` | Highlighted columns, emphasis |
| Primary accent | professional_blue | `#14958B` | Primary series, accents |
| Input fill | soft_blue | `#E1F3F0` | **User input cells** (light mint) |
| Accent | teal / soft_teal | `#1FA99C` / `#DDF3EF` | Completed, positive |
| Secondary | lavender / soft_lavender | `#9B7BE0` / `#F1ECFB` | Secondary series, optional fields |
| Canvas | background | `#EDF5F4` | Sheet background behind cards |
| Calculated | light_gray | `#E7EFEE` | **Calculated cells** |
| Text | dark_text / secondary_text | `#1F3533` / `#5F7472` | Body / labels |
| Border | border | `#D5E5E2` | Thin card edges |
| Status | success / warning / danger / info | `#1E9E75` / `#EE8A3A` / `#CF3A43` / `#2F6FAA` | Done / due soon / overdue / in progress |

Dashboard extras: highlight-tile gradient `#1EB5A6 → #86DDD3`, card shadow `#0F6E68` at 16 % opacity,
inactive chart bars `#B4C1C0`.

## Excel shape layer (dashboards)

Rounded cards, soft shadows, the gradient highlight tile, the sidebar and its icons are real Excel shapes
injected by `build/drawing_inject.py`. Numbers on cards are text boxes **linked to cells** (live). Google Sheets
does not import Excel shapes, so every dashboard also has a complete cell layer underneath that renders the same
layout flat (square corners, text navigation instead of icons).

## Cell conventions (shown as a legend on every working sheet)

| Fill | Meaning |
|---|---|
| Light mint `#E1F3F0` | User input — type or choose from the dropdown |
| White | Standard information |
| Light grey `#E7EFEE` | Calculated — formula, do not overwrite |
| Light teal `#E2F4F0` | Positive result |
| Light red `#FCEAEC` | Warning / negative result |
| Lavender `#F0EDFC` | Optional / secondary information |

## Layout rules

- Gridlines hidden on every sheet; structure comes from fills and thin `#DCE3EA` borders.
- Column A is a narrow gutter; content starts in column B.
- Row 2 = navy title bar (sheet name), row 3 = subtitle + "⌂ Dashboard" link.
- Tables: navy header row with white bold text, 10 pt body, freeze panes below the header.
- KPI cards: label (9 pt, secondary text) / value (20 pt bold, blue or status colour) / sub-label.
- Conditional formatting references **only cells on the same sheet** (a Google Sheets requirement),
  so every sheet carries its own "today" cell and helper columns.
- Dates `mmm d, yyyy`; currency `#,##0.00` with the currency symbol shown in headers/cards;
  percentages `0%`.

## Typography

- Excel edition: **Aptos** (Office 365 default; older Office substitutes Calibri).
- Google Sheets edition: **Arial**.
- OneNote: Segoe UI headings / body (OneNote desktop default family).
