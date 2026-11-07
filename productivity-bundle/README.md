# The Ultimate Productivity Bundle

Four standalone products that share one design system:

| # | Product | Status | Formats |
|---|---|---|---|
| 1 | Ultimate Project Manager (15 tabs) | ✅ Built and validated | Excel .xlsx + Google Sheets edition, each as DEMO and BLANK |
| 2 | Ultimate OneNote Planner | ⏳ Next | OneNote-importable pages + PDF guide |
| 3 | Weekly Planner Pro (8 tabs) | ⏳ Planned | Excel + Google Sheets |
| 4 | Ultimate Budget Spreadsheet (28 tabs) | ⏳ Planned | Excel + Google Sheets |

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
