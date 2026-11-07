# Ultimate Project Manager — User Guide

15-tab project management system for Excel and Google Sheets. Enter projects and tasks once; dashboards, calendars, the Kanban board and the Gantt chart update automatically.

## What's in this folder

| File | Use it for |
|---|---|
| Excel/Ultimate_Project_Manager_Excel_DEMO.xlsx | Excel (Microsoft 365, Excel 2019/2021, Excel 2016) with demo data so you can explore |
| Excel/Ultimate_Project_Manager_Excel_BLANK.xlsx | Same workbook, no demo rows: start your real workspace here |
| Google_Sheets/Ultimate_Project_Manager_GoogleSheets_DEMO.xlsx | Import into Google Sheets (demo data) |
| Google_Sheets/Ultimate_Project_Manager_GoogleSheets_BLANK.xlsx | Import into Google Sheets (blank) |

The Excel edition's dashboard uses real Excel shapes (rounded cards, shadows, gradient tile, clickable sidebar icons) with numbers linked live to cells. Google Sheets doesn't import Excel shapes, so its dashboard shows the same layout and live numbers flat, with text links in the sidebar.

The Google Sheets edition is built from the same generator, adapted for Google Sheets: Arial font, plain ranges with filters (Google Sheets doesn't import Excel Table objects cleanly), no sheet protection (use Data › Protect sheets and ranges instead), and conditional formatting that only refers to its own sheet.

## Installation / import

**Excel:** open the .xlsx file. If you see "Protected View", click *Enable Editing*. The file has no macros.

**Google Sheets:**

1. Go to drive.google.com › New › File upload, and choose the *GoogleSheets* .xlsx file.
2. Right-click the uploaded file › Open with › Google Sheets.
3. File › Save as Google Sheets. This gives you a native Google Sheet; you can delete the uploaded .xlsx afterwards.
4. Check File › Settings › Locale (for example United States) so dates read the way you expect.

## The 15 tabs

| # | Tab | Section | Purpose |
|---|---|---|---|
| 1 | Setup | Setup | Workspace details, currency, week start, every dropdown list |
| 2 | All-in-One Dashboard | Dashboards | 4 tiles (projects, task completion, remaining budget, this period), a status strip (due today, due this week, overdue, recurring today), 6 charts, and 6 lists including the project performance table. A Period picker drives the period figures |
| 3 | Monthly Calendar | Dashboards | Pick a year and month. Shows tasks due (coloured by category), project deadlines and scheduled blocks |
| 4 | Weekly Calendar | Dashboards | Monday–Sunday, 7 AM–8 PM time grid, tasks due, daily workload and weekly statistics |
| 5 | Project Overview | Projects | Portfolio table: progress, budget, actual, remaining and health are calculated. Optional Revenue gives profit and margin |
| 6 | Project Manager | Projects | Pick a project to see its details, timeline, team, objectives, deliverables, milestones, dependencies, risks and notes |
| 7 | Project Budget | Projects | Planned vs actual budget lines, utilisation, alerts, category summary |
| 8 | Variable Tasks | Tasks | Main database of one-time tasks (500 rows), with Completed On and Urgent?/Important? fields |
| 9 | Recurring Tasks | Tasks | Daily, weekly, biweekly, monthly, quarterly, annual or custom repeats, with the next date calculated |
| 10 | Task Schedule | Tasks | Time blocks (date, start and end time). Feeds the Weekly Calendar |
| 11 | Task Filter | Tasks | Filter by 10 criteria, including keyword search |
| 12 | Decision Matrix | Extras | Weighted scoring of 3 options against up to 10 criteria, plus an Eisenhower matrix of open tasks (Do first / Schedule / Delegate / Eliminate) |
| 13 | Kanban Board | Extras | 5 columns built from the first five Task Statuses |
| 14 | Gantt Chart | Extras | Timeline drawn from task dates, in daily or weekly view |
| 15 | Instructions | Extras | In-workbook help |

## Getting started (10 minutes)

1. **Setup:** type your name and workspace, then choose a currency and a week start. Replace the Team Members with your team. Adjust the categories if you like.
2. **Project Overview:** add a row for each project. Fill in the name, category, manager, start date, due date, priority and status. Project IDs (P-001…) are already filled in.
3. **Project Budget:** pick the Project ID, choose a category, and enter the Planned Budget. Add the Actual Expenses as money is spent.
4. **Variable Tasks:** add tasks and link each one to a project with the dropdown. Keep Status and Progress up to date.
5. Optionally, add **Recurring Tasks** and **Task Schedule** blocks.
6. Open the **All-in-One Dashboard**. Choose a **Year**, **From** and **To** month with the ▾ cells in the Period card; the tiles, donut and highlighted months follow that period.

### Cell colours

| Colour | Meaning |
|---|---|
| Light mint | Input: type a value or choose one from the dropdown |
| Light grey | Formula: don't overwrite |
| White | Information |
| Light teal | Positive result |
| Light red | Warning or negative result |
| Lavender | Optional or system list |

## How the automation works (formula guide)

- **Today.** Every "today" calculation reads *Setup › Effective today*, which is `=IF(override="",TODAY(),override)`. Type a date into the override to see the whole workbook as of that date.
- **Status logic.** The 5th Task Status (default "Completed") means *done* everywhere. The first five Task Statuses become the Kanban columns. Projects with the status Planning or In Progress count as *active*.
- **Project roll-ups** (Project Overview):
  - Progress is `AVERAGEIFS` over each task's effective progress; a task marked Completed counts as 100%.
  - Budget and Actual are `SUMIFS` over Project Budget by Project ID.
  - Task counts use `COUNTIFS`.
  - Health is a decision chain: Completed › Cancelled › Overdue › Over budget › At risk › On track.
- **Filtered and sorted lists.** Helper columns on *Variable Tasks* (headed in grey) give matching rows a running number (1, 2, 3…). The dashboard lists, Task Filter, Kanban and Gantt fetch those rows with `INDEX/MATCH`. Upcoming and overdue lists are sorted with `SMALL()` on a rank value (due date plus a tiny row offset). This method gives the same results in Excel 2010+, Microsoft 365, Google Sheets and LibreOffice, with no dynamic-array formulas.
- **Calendars.** Each task gets a key made of its due date and a running number (`46333|1`, `46333|2`…). A calendar cell looks up `date|1` and `date|2`, and project deadlines work the same way.
- **Completion date.** When a task is marked Completed, type its *Completed On* date (the cell turns amber until you do). The dashboard's "completed" line counts tasks by that date; if it's blank, the due date is used instead.
- **Recurring tasks on calendars.** For every recurring task, hidden helper columns test each day shown on the Monthly and Weekly calendars (and today). Matching days list the task with ↻, after that day's one-time tasks. The same test feeds the dashboard's *Due today* list and *recurring today* count.
- **Eisenhower matrix.** *Urgent?* and *Important?* (Yes/No) on Variable Tasks give each open task a quadrant: both Yes → Do first, only Important → Schedule, only Urgent → Delegate, neither → Eliminate. Completed tasks drop off.
- **Revenue and margin.** Profit = Revenue − actual cost; Margin = Profit ÷ Revenue. Projects without revenue show "—".
- **Recurring next date:**
  - Day-based frequencies (daily, weekly, biweekly, custom) add whole intervals to the start date: `start + ROUNDUP((base−start)/step,0)×step`.
  - Month-based frequencies (monthly, quarterly, annually) use `EDATE`, so month-end dates stay valid.
  - The base date is the later of today and the day after *Last Completed*. A row shows "Ended" after the End Date and "Paused" when its status is Paused.
- **Gantt.** Conditional-formatting rules compare each timeline column's date with the task's start and end dates.
  - Darker blue shows the share of the bar covered by progress.
  - Teal means completed, red means overdue, and ◆ marks a milestone (start date = due date).
  - The amber column is today.
- **Currency.** Amounts are stored as plain numbers. The Setup currency symbol appears in KPI labels.

## Demo data

Rows marked **DEMO DATA** belong to a fictional company, "Northwind Studio". The DEMO file's *Today's date override* (Setup) is set to Nov 7, 2026 so the demo always looks current; clear that cell to use the real date. The demo has 8 projects, 60 tasks, 18 budget lines, 10 recurring tasks, 22 schedule blocks, 25 project details and 1 decision.

**Remove it:** the easiest way is to start from the BLANK file. To clear the demo file by hand, select the light-mint cells that contain data on Project Overview, Project Budget, Variable Tasks, Recurring Tasks, Task Schedule, the Project Manager database and Decision Matrix, then press Delete. Never delete whole rows or the grey helper columns.

## Capacity

The workbook has room for 100 projects, 500 tasks, 500 budget lines, 200 recurring tasks, 300 schedule blocks and 300 project details. To go beyond that, copy the last row's formulas further down. In Excel, a table grows when you type directly below it. For a separate workspace, duplicate the file.

## Troubleshooting

| Symptom | Fix |
|---|---|
| A task isn't on the dashboard, calendar or Gantt | It needs a Task Name. Date views also need a Due Date (and a Start Date for the Gantt). Pick the Project from the dropdown so the name matches exactly |
| A Kanban card is missing | Its Status must be one of the first five Task Statuses. Each column shows up to 15 cards |
| A Completed On cell is amber | The task is Completed but has no completion date yet; type the date you finished it |
| A dropdown is empty | Its source list on Setup is empty |
| "+N more" appears on the calendar | More than 2 tasks are due that day. Use Task Filter with a date range to see them all |
| A date shows as a number | Format the cell as a Date |
| The period buttons don't react to clicks | They show the selection; choose Year / From / To with the ▾ cells above them (no macros needed) |
| You can't type on a dashboard tab (Excel) | Display tabs are protected against accidental edits. Use Review › Unprotect Sheet (there's no password) |
| A chart looks slightly different in Google Sheets | Click the chart › Edit chart. The data ranges are kept |

## Quality assurance performed

- Every workbook (2 editions × demo/blank) was recalculated headlessly in LibreOffice: 31,831 formulas each, **0 errors**.
- An independent Python script (`build/validate_project_manager.py`) re-calculates the expected results from the demo data and compares them with the spreadsheet's values. It covers 962 checks across all four files:
  - KPIs and sorted lists
  - Project roll-ups
  - Recurring next dates and occurrences this month
  - Kanban
  - Monthly and weekly calendar placement
  - Gantt
  - Task Filter
  - Decision Matrix
  - Blank-state messages
- The date logic was re-tested with "today" set to Sep 1 2026, Oct 15 2026, Dec 31 2026 and Jan 4 2027, all passing.

**Not yet verified:** the files have not been opened in Microsoft Excel or Google Sheets themselves, because neither was available in the build environment.

- Formulas are limited to functions documented for both products: SUMIFS, COUNTIFS, AVERAGEIFS, INDEX, MATCH, IFERROR, EDATE, EOMONTH, WEEKNUM, SMALL, LARGE, HYPERLINK and SEARCH.
- Before you sell, open each file once in Excel and in Google Sheets and look through the charts and conditional formatting.
