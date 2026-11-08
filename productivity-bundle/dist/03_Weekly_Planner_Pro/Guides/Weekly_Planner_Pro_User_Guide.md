# Weekly Planner Pro — User Guide

An 8-tab weekly planner for Excel and Google Sheets. Plan six weeks at a time: goals, priorities, a task checklist, a time schedule and trackers for each week, plus a monthly calendar that gathers everything together.

## What's in this folder

| File | Use it for |
|---|---|
| Excel/Weekly_Planner_Pro_Excel_DEMO.xlsx | Excel (Microsoft 365, Excel 2019/2021, Excel 2016) with demo data so you can explore |
| Excel/Weekly_Planner_Pro_Excel_BLANK.xlsx | The same workbook without demo data: start planning here |
| Google_Sheets/Weekly_Planner_Pro_GoogleSheets_DEMO.xlsx | Import into Google Sheets (demo data) |
| Google_Sheets/Weekly_Planner_Pro_GoogleSheets_BLANK.xlsx | Import into Google Sheets (blank) |

The Excel edition has a clickable icon sidebar drawn with Excel shapes. Google Sheets doesn't import Excel shapes, so its sidebar is a dark column with text links. Everything else is the same: formulas, dropdowns, colours and charts. The Google Sheets edition uses Arial and has no sheet protection.

## Installation / import

**Excel:** open the .xlsx file. If you see "Protected View", click *Enable Editing*. The file has no macros.

**Google Sheets:**

1. Go to drive.google.com › New › File upload, and choose the *GoogleSheets* .xlsx file.
2. Right-click the uploaded file › Open with › Google Sheets.
3. File › Save as Google Sheets. Work in that copy; you can delete the uploaded .xlsx afterwards.
4. Check File › Settings › Locale (for example United States) so dates and times read the way you expect.

## The 8 tabs

| Tab | What it does |
|---|---|
| Setup | Your details, planning preferences (week start day, Week 1 date, water and exercise goals, the "done" status), working hours, the six-week overview with progress, and every dropdown list |
| Week 1 … Week 6 | Six identical weekly planners. Each has a week overview, seven day cards and trackers (see below) |
| Monthly Calendar | Month selector, a calendar grid with important dates, deadlines and the tasks from your week tabs, each week's main goal, monthly priorities and month statistics |

### Inside each week tab

- **Week overview:** week number (ISO), start and end dates, weekly main goal, top three priorities, and eight live tiles: weekly progress, tasks done, habits done, days the water goal was met, exercise minutes against your goal, and average productivity.
- **Seven day cards (Monday to Sunday):** the date, top three priorities with a ✓ column, a 10-row task checklist (category, priority and status dropdowns), a 10-slot time schedule built from your working hours, three appointments, notes, and the day's progress ("4 of 8 done · 50%").
- **Habit tracker:** your 8 habits from Setup, with a ✓ or ✗ for each day and a weekly count.
- **Daily trackers:** water (glasses), whether the water goal was met, exercise type and minutes, a productivity score from 1 to 10, and the share of tasks completed each day.
- **Charts:** productivity score by day and tasks completed by day.
- **Weekly reflection:** what went well, what was challenging, what you learned, your focus for next week, and a 1–10 rating shown as stars.

The row of links under the overview jumps to any day, the trackers or the reflection. Today's day card turns teal.

## Getting started (5 minutes)

1. **Setup:** type your name and planner title. Choose the day your week starts on and set **Week 1 starts on**. Leave it blank to start this week. Weeks 2–6 follow automatically, 7 days apart.
2. Check your working hours and slot length. The day cards show 10 schedule slots from the start time.
3. Edit the lists (categories, priority levels, task statuses, habits, exercise types) to suit you.
4. Open **Week 1**: write your main goal and top 3 priorities, then fill in the day cards.
5. Open **Monthly Calendar** and add birthdays, events, deadlines and monthly priorities in the tables under the calendar.

### Cell colours

| Colour | Meaning |
|---|---|
| Light mint | Type here |
| Grey | Calculated: don't type over it |
| Lavender | Optional, or a system list |
| Teal tint | Done or good result |
| Light red | Warning: overdue, or a habit or goal missed |

## Reusing a week tab

Each week tab is independent. To use one for any other week:

1. Type the new week's date in **Week starts on (optional)**. Any day of that week works; it moves back to your week-start day.
2. Clear the old entries: select the mint cells and press Delete.
   - **Excel shortcut:** type `Week1_Inputs` (or Week2_Inputs, and so on) in the Name Box, top left, and press Enter. This selects every input cell on that tab. Then press Delete.
   - Grey cells hold formulas, so leave them in place.
3. To return a tab to its automatic date, clear its **Week starts on** cell.

For a fresh six weeks, change **Setup › Week 1 starts on** and clear the week tabs. Or keep a clean copy of the BLANK file and duplicate it.

## How the automation works (formula guide)

- **Dates:** Setup › Week 1 start = the date you typed, or today, moved back to your week-start day: `date − MOD(WEEKDAY(date) − 1 or 2, 7)`. Week *n* starts on Week 1 + 7 × (n − 1), unless the tab has its own date. Each week tab keeps its start date in a hidden helper cell (`N3`). Every day, tracker heading and the calendar link read from it.
- **Week number:** ISO 8601 week, worked out from the week's Thursday. It's an arithmetic formula, so it gives the same result in every spreadsheet app.
- **Progress:** a task counts as done when its Status equals Setup › *Status that means "done"*:
  - Day: `COUNTIFS(tasks, "?*", status, done) / COUNTIF(tasks, "?*")`
  - Week: the same over all seven days. It appears on the overview, the Setup table and the calendar.
- **Schedule slots:** start time + slot × slot length. A slot is blank once it reaches the end of your working day.
- **Trackers:** the water goal is met when glasses ≥ your daily goal. Exercise is compared with your weekly goal. Productivity is averaged over the days you scored. Habits count the ✓ marks.
- **Monthly Calendar:**
  - Builds a 6 × 7 grid from the first day of the chosen month, moved back to your week-start day.
  - **★ important date** and **⚑ deadline:** the first one on each date, found with a "date|n" key and INDEX/MATCH. Further entries show as "+N more".
  - **☑ tasks:** counted from all six week tabs with COUNTIF and COUNTIFS on each task's date. That date sits in a hidden helper column on each week tab.
  - **Week goal column:** finds which week tab starts in that calendar row (SUMPRODUCT), then shows its goal and progress.
- **Deadlines:** the Due column reads "In 5d", "Today", "Late 2d" or "✓ Done". Late deadlines turn red, here and on the calendar.
- **Compatibility:** only functions that Excel 2013+, Excel 365, Google Sheets and LibreOffice all support: COUNTIFS, SUMPRODUCT, INDEX, MATCH, IFERROR, EDATE, WEEKDAY, TEXT and HYPERLINK. There are no dynamic arrays, LET, XLOOKUP or macros. Conditional formatting only refers to cells on its own tab, as Google Sheets requires.
- **No Excel Tables here:** the planner pages are laid out as cards, with merged cells for writing space. Excel Tables can't contain merged cells, so the lists use plain ranges with dropdowns. The formulas cover the full range of rows, so nothing needs to "grow".

## Demo data

The DEMO files show Jordan Lee's six weeks starting Monday 2 Nov 2026. The demo's "today" is fixed at **Wednesday 11 Nov 2026** (Setup › Today's date override):
- Week 1 is complete.
- Week 2 is in progress.
- Weeks 3–6 are planned ahead.

Every tab's subtitle says **DEMO DATA**.

**Remove it:** start from the BLANK file. To clear the demo file by hand:
1. Clear the mint cells on each week tab (see *Reusing a week tab*).
2. Clear the Important Dates, Task Deadlines and Monthly Priorities tables on Monthly Calendar.
3. On Setup, clear your details and the **Today's date override**.

## Capacity

- 6 week tabs.
- Each day: 3 priorities, 10 tasks, 10 schedule slots, 3 appointments and notes.
- 8 habits.
- 30 important dates and 30 deadlines.
- 12 months of priorities.

To plan further ahead, reuse a week tab or duplicate the file.

## Troubleshooting

| Symptom | Fix |
|---|---|
| A week shows the wrong dates | Check Setup › Week starts on and Week 1 starts on. Clear the tab's own *Week starts on (optional)* cell to go back to the automatic date |
| Progress stays at 0 % | A task only counts when its Status matches Setup › *Status that means "done"* exactly. Use the dropdown |
| A day card says "No tasks yet" | Type a task in the Task checklist column; Category, Priority and Status alone don't count |
| Schedule times are blank | Setup › Day starts / Day ends must be times (for example 8:00 AM), and the end must be after the start |
| A habit row is empty | The habit list on Setup has fewer than 8 names; add more |
| The calendar is missing a task or deadline | The calendar shows the first important date and the first deadline per day, then "+N more". Tasks appear only for dates covered by one of the six week tabs |
| A date or time shows as a number | Format the cell as a Date or Time |
| You can't change the layout (Excel) | Tabs are protected against accidental overwrites. Use Review › Unprotect Sheet; there's no password |
| A chart looks different in Google Sheets | Click the chart › Edit chart. The data ranges are kept |

## Quality assurance performed

- All four workbooks (2 editions × demo/blank) were recalculated headlessly in LibreOffice with **0 formula errors**.
- An independent script, `build/validate_weekly_planner.py`, recomputes the expected results from the demo data and compares them with the spreadsheet: **3,018 checks** across the four files. They cover:
  - week dates and ISO week numbers;
  - every schedule slot;
  - day, week and six-week progress;
  - habits, water, exercise and productivity;
  - every calendar cell and month statistic;
  - deadline status;
  - week goals in the calendar;
  - blank-state messages;
  - dropdown wiring, sheet protection and the reset names.
- **Scenario tests** on a modified copy passed:
  - a Sunday week start;
  - a week tab moved to a different month;
  - 30-minute slots;
  - renaming the "done" status.
- A layout check found no clipped text, "###" values or overlapping charts.

**Not yet verified:** the files have not been opened in Microsoft Excel or Google Sheets themselves, because neither was available in the build environment. Before you sell, open each file once in both apps and look through the charts, dropdowns and conditional formatting.
