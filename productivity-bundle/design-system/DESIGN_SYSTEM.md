# Ultimate Productivity Bundle — Global Design System

One visual identity shared by all four products (Project Manager, OneNote Planner,
Weekly Planner Pro, Budget Spreadsheet). Machine-readable tokens live in
`design-tokens.json`; the spreadsheet generators import the same values from
`build/common.py`, so the palette is defined in one place.

## Palette

| Role | Token | Hex | Used for |
|---|---|---|---|
| Primary | Deep Navy | `#17243A` | Title bars, navigation, table headers |
| Primary | Midnight Blue | `#223653` | Section headers, secondary bars |
| Primary | Professional Blue | `#4169E1` | Key metrics, primary chart series, links |
| Primary | Soft Blue | `#EAF1FB` | **User input cells** |
| Accent | Teal | `#24A89A` | Completed / positive / income |
| Accent | Soft Teal | `#E2F4F0` | Positive result fill |
| Accent | Lavender | `#8B7BE8` | Planning / secondary categories / goals |
| Accent | Soft Lavender | `#F0EDFC` | Optional or secondary fields |
| Neutral | Background | `#F5F7FA` | Sheet canvas, card gutters |
| Neutral | Light Gray | `#E9EDF2` | **Calculated cells** |
| Neutral | Medium Gray | `#9AA5B1` | Muted labels, out-of-month days |
| Neutral | Dark Text | `#263445` | Body text |
| Neutral | Secondary Text | `#6B7785` | Notes, sub-labels |
| Neutral | Border | `#DCE3EA` | Thin borders (gridlines are hidden) |
| Status | Success / bg | `#279B70` / `#E5F5ED` | Done, on track |
| Status | Warning / bg | `#E9A23B` / `#FFF3DC` | Due soon, near budget limit |
| Status | Danger / bg | `#DC5B64` / `#FCEAEC` | Overdue, over budget |
| Status | Info / bg | `#4D8FD8` / `#EAF2FC` | In progress, informational |

Finance-specific (Product 4): income = teal, expenses = danger red, savings = blue, goals = lavender.

## Cell conventions (shown as a legend on every working sheet)

| Fill | Meaning |
|---|---|
| Light blue `#EAF1FB` | User input — type or choose from the dropdown |
| White | Standard information |
| Light gray `#E9EDF2` | Calculated — formula, do not overwrite |
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
