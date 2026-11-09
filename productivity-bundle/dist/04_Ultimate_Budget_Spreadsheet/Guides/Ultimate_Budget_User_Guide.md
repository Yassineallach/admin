# Ultimate Budget Spreadsheet — User Guide

A 28-tab personal finance system for Excel and Google Sheets. You log your money in three places; the dashboards, the 12 monthly budgets, the calendar and the analysis tabs all update themselves.

## What's in this folder

| File | Use it for |
|---|---|
| Excel/Ultimate_Budget_Spreadsheet_Excel_DEMO.xlsx | Excel (Microsoft 365, Excel 2019/2021, Excel 2016) with demo data so you can explore |
| Excel/Ultimate_Budget_Spreadsheet_Excel_BLANK.xlsx | The same workbook without demo data: start your budget here |
| Google_Sheets/Ultimate_Budget_Spreadsheet_GoogleSheets_DEMO.xlsx | Import into Google Sheets (demo data) |
| Google_Sheets/Ultimate_Budget_Spreadsheet_GoogleSheets_BLANK.xlsx | Import into Google Sheets (blank) |

The Excel edition has:
- a clickable icon sidebar drawn with Excel shapes;
- Excel Tables on the data-entry tabs;
- protected formula tabs (no password).

The Google Sheets edition uses the same formulas, charts and layout. It has:
- a dark sidebar column with text links instead of the icons;
- filters instead of Excel Tables;
- no sheet protection.

## Installation / import

**Excel:** open the .xlsx file. If you see "Protected View", click *Enable Editing*. The file has no macros.

**Google Sheets:**

1. Go to drive.google.com › New › File upload, and choose the *GoogleSheets* .xlsx file.
2. Right-click it › Open with › Google Sheets.
3. File › Save as Google Sheets. Work in that copy.
4. Check File › Settings › Locale so dates and currency read the way you expect.

## The 28 tabs

| Section | Tabs |
|---|---|
| A — Transactions | Easy Setup · Bank Accounts · Recurring Transactions · Payments · Variable Transactions |
| B — Dashboards | All-in-One Dashboard · Annual Totals · Automated Calendar · Paycheck Dashboard |
| C — Monthly insights | January … December (12 monthly budgets) |
| D — Build your wealth | 50/30/20 Dashboard · Expense Distribution · Sinking Funds · Debt Calculator · Net Worth · Investment Forecast · No-Spending Challenge |

The icon sidebar (or text links in Google Sheets) jumps to every section. The Months icon opens January, and each month tab has a Jan–Dec strip.

## Getting started (15 minutes)

1. **Easy Setup:** set the following.
   - Choose your currency, budget year and the **first month of your budget**. The budget year can start in any month.
   - Edit the **income categories** (with the amount you expect each month).
   - Edit the **expense categories**. For each, choose Fixed or Variable and Needs or Wants, and set a monthly budget.
2. **Bank Accounts:** add each account with its opening balance at the start of your budget period.
3. **Sinking Funds:** add savings goals (target, starting balance, monthly contribution, target date and the account they're held in).
4. **Debt Calculator:** add each debt (current balance, interest rate, minimum payment, any extra payment).
5. **Recurring Transactions:** add salary, rent, bills, subscriptions, savings transfers and loan payments, each with a frequency and start date.
6. **Variable Transactions:** log day-to-day income and spending as it happens.
7. **Payments:** add one-off bills with due dates. Set their status to Paid when you pay them.

### Cell colours

| Colour | Meaning |
|---|---|
| Light mint | Type here |
| Grey | Calculated: don't type over it |
| Lavender | Optional, or a system list |
| Teal tint | Income, or a good result |
| Light red | Expenses, warnings, overdue or over budget |
| Blue | Savings |
| Lavender accents | Financial goals |

## How the automation works (formula guide)

**One engine.** Every amount ends up in a single **category × month matrix** at the bottom of Annual Totals. Each cell adds three sources:

`SUMIFS(transactions) + SUMIFS(recurring occurrences) + SUMIFS(paid payments)`

The 12 month tabs, the dashboard, 50/30/20, Expense Distribution, Sinking Funds and the debt "paid this period" figures all read from that matrix. So a number can never disagree between tabs.

**Type comes from the category.** A Salary entry is income, Groceries is an expense, a Sinking Fund's name is savings, a debt's name is a debt payment. The special category **Transfer** moves money between your accounts without counting as spending: pick the destination in *Transfer to*. Amounts are always positive.

**Recurring items post themselves.** For each budget month, the sheet counts how many times an item occurs up to today:
- weekly and biweekly items step from the start date;
- monthly, quarterly and annual items land on the same day of the month, or the last day of a shorter month.

The count respects end dates and Paused status. Easy Setup › *Auto-post recurring items* = No turns posting off.

**Next payment** is the next occurrence on or after today. It shows "Ended" after the end date and "Paused" when paused.

**Any start month.** Month tab *March* is the March inside your 12-month budget period. With a budget starting in April 2026, the January tab shows January 2027.

**Bank balances** = opening balance + income − money out + transfers in.
- Money out covers expenses, savings transfers, debt payments and transfers sent.
- Transfers in covers transfers from your other accounts plus savings into funds held in the account.

**Automated Calendar.** A hidden daily table tests every recurring item against every date (SUMPRODUCT). The grid then shows each day's scheduled income ↑, bills ↓, savings ◆ and payment deadlines ⚑.

**Paycheck Dashboard.** Bills before the next pay = recurring bills, loan payments and one-off payments due from the pay date to the day before the next pay date.

**Debt Calculator:**
- **Months to payoff** uses NPER with your own payments.
- **The plan** simulates up to 360 months. Every debt gets its minimum. The extra amount plus all additional payments go to the focus debt: smallest balance first (snowball) or highest interest first (avalanche). When a debt is paid off, its minimum rolls into the extra.
- Money left over in a debt's final month isn't carried over, so the plan is slightly conservative.

**Investment Forecast:** future value with compounding each contribution period: `P(1+i)^N + C((1+i)^N − 1)/i`. It is a hypothetical projection and is labelled as such in the file.

**Compatibility:** the formulas use SUMIFS, COUNTIFS, SUMPRODUCT, INDEX/MATCH, EDATE, EOMONTH, NPER, LARGE and SMALL, which work in Excel 2013+, Excel 365, Google Sheets and LibreOffice. There are no dynamic arrays, LET, XLOOKUP or macros. Conditional formatting only refers to its own tab.

## Demo data

The DEMO files show Sam Rivera's budget for 2026, with "today" fixed at **7 Nov 2026** (Easy Setup › Today's date override). January–October are complete and November is in progress.

The demo includes:
- 4 accounts and 20 recurring items (biweekly salary, rent, bills, subscriptions, savings transfers, loan payments);
- 11 one-off payments;
- about 240 logged transactions, including monthly credit-card payoffs as transfers;
- 5 savings goals and 3 debts;
- a net worth history, an investment plan and a no-spend challenge.

Every tab's subtitle says **DEMO DATA**.

**Remove it:** start from the BLANK file. To clear the demo by hand:
1. Clear the mint cells on Bank Accounts, Recurring Transactions, Payments, Variable Transactions, Paycheck Dashboard, Sinking Funds, Debt Calculator, Net Worth and the No-Spending Challenge log.
2. Clear Easy Setup › Today's date override.

## Capacity

- 1,000 transactions, 60 recurring items and 100 payments.
- 10 accounts, 10 savings goals and 10 debts.
- 52 paychecks.
- 12 income categories and 30 expense categories.

In Excel, the Tables on the data-entry tabs grow when you type below them. Copy the formulas in grey columns down with the new rows.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Type shows "Unknown" | The category isn't in any list. Pick it from the dropdown, or add it on Easy Setup (or as a Sinking Fund / debt) |
| A month shows nothing | The date is outside your 12-month budget period (Easy Setup › Budget year / First month) |
| Recurring items don't count | Check Easy Setup › Auto-post = Yes, a start date is set, and the status isn't Paused. Only occurrences up to today count |
| A bill isn't in the budget | Payments count once their Status is Paid |
| A bank balance looks off | Check the opening balance date matches the start of your budget, and use Transfer for money moved between accounts. Otherwise the money is counted as spending |
| Debt payoff says "Raise payment" | The payment doesn't cover the monthly interest |
| Charts look different in Google Sheets | Click the chart › Edit chart. The data ranges are kept |
| You can't type on a dashboard (Excel) | Analysis tabs are protected against accidental edits. Use Review › Unprotect Sheet; there's no password |

## How this template was tested

- Every formula in all four files was recalculated with **zero errors** (about 32,000 formulas per file).
- More than 2,000 automated checks compare the workbook's results with an independent calculation of the same data: every category and month total, all 12 month tabs, bank balances, recurring dates, payment status, the calendar, paycheck bills, 50/30/20, sinking funds, the debt payoff plan, net worth and the investment forecast.
- Scenario tests: a budget year starting in April, a different budget year and "today", recurring posting switched off and the avalanche method.
- Blank files were checked for clear empty-state messages instead of errors.

If something doesn't behave as described, send me a message on Etsy and I'll help.

*The Investment Forecast and debt plan are estimates for planning, not financial advice.*
