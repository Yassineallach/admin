"""Listing content for the six mini-products: shots, image text, title, tags, description, price."""
from __future__ import annotations

import build_budget as BB

COMMON_NOTE = """━━━━━━━━━━━━━━━━━━━━
WHAT YOU RECEIVE
━━━━━━━━━━━━━━━━━━━━
• Excel file — DEMO (sample data) and BLANK versions
• Google Sheets file — DEMO and BLANK versions
• Start Here PDF with set-up steps

━━━━━━━━━━━━━━━━━━━━
COMPATIBILITY
━━━━━━━━━━━━━━━━━━━━
✔ Microsoft Excel (Windows & Mac) and Excel for the web
✔ Google Sheets (free Google account)
✘ Not for Apple Numbers
No macros, no add-ons. Any currency.

━━━━━━━━━━━━━━━━━━━━
PLEASE NOTE
━━━━━━━━━━━━━━━━━━━━
• This is a DIGITAL product. Nothing will be shipped.
• For personal use. Please don't resell or share the files.
• Want the complete system? This tracker is also included in the Ultimate Budget Spreadsheet (28 tabs) in my shop.
• Questions? Send me a message — I'm happy to help."""

MINIS = {
    "debt": dict(
        shots=[("main", BB.S_DC, "A1:X24", "DEBT CALCULATOR"), ("schedule", BB.S_DC, "B25:Q62", "PAYOFF SCHEDULE"),
               ("start", "Start", "A1:K24", "DEBT PAYOFF CALCULATOR")],
        hero_crop=(0, 1, 0, 0.6),
        hero=("DEBT PAYOFF", "Debt Payoff\nCalculator", ["Snowball or avalanche", "Debt-free date for every debt",
                                                         "Month-by-month payoff plan", "Interest saved vs no plan"]),
        f1=("Your fastest way out of debt", "List your debts — the plan and dates update instantly",
            [("card", "Up to 10 debts", "Balance, APR, minimum and extra payment"),
             ("scale", "Snowball or avalanche", "Switch methods and compare instantly"),
             ("calendar", "Debt-free date", "For each debt and overall"),
             ("money", "Interest saved", "Compared with paying each debt separately")]),
        f2=("A month-by-month plan", "Every balance for the next 30 years — paid-off minimums roll over",
            [("table", "360-month schedule", "Balance of every debt, every month"),
             ("trend", "Balance chart", "Watch the total fall over 10 years"),
             ("repeat", "Rolling payments", "Freed-up minimums snowball into the next debt")]),
        steps=["List your debts with current balances", "Pick snowball or avalanche + an extra amount", "Follow your plan to debt-free"],
        title="Debt Payoff Calculator Spreadsheet, Debt Snowball Avalanche Tracker, Excel Google Sheets, Debt Free Plan, Credit Card Payoff",
        tags="debt payoff tracker, debt snowball, debt avalanche, debt tracker, debt free, credit card payoff, loan payoff, google sheets debt, excel debt tracker, debt calculator, budget template, financial planner, debt spreadsheet",
        price=("$4.99", "$3.49", "Debt payoff trackers on Etsy commonly sell for about $3–$8."),
        desc="""Find your debt-free date in minutes. List your debts, pick snowball or avalanche, add an extra payment — this calculator builds your month-by-month payoff plan automatically. Tested formulas: works any year, any currency.

━━━━━━━━━━━━━━━━━━━━
FEATURES
━━━━━━━━━━━━━━━━━━━━
✔ Up to 10 debts: balance, interest rate (APR), minimum and additional payments
✔ Snowball (smallest balance first) or avalanche (highest interest first) — switch anytime
✔ Extra monthly payment: goes to your focus debt; paid-off minimums roll over automatically
✔ Debt-free date overall and payoff month for every debt
✔ Total interest on your plan and interest saved vs paying each debt separately
✔ Months to payoff and payoff date per debt with your own payments
✔ 360-month payoff schedule + balance chart
✔ Start tab with instructions; DEMO data so you can explore
"""),
    "funds": dict(
        shots=[("main", "Sinking Funds", "A1:O40", "SINKING FUNDS"), ("log", "Contributions", "A1:F45", "CONTRIBUTIONS"),
               ("start", "Start", "A1:K24", "SINKING FUNDS TRACKER")],
        hero_crop=(0, 1, 0, 0.62),
        hero=("SAVINGS GOALS", "Sinking Funds\nTracker", ["Up to 15 savings goals", "Progress bars & months to go",
                                                         "On-track status per goal", "Deposits & withdrawals log"]),
        f1=("Save for every goal", "Target, balance, progress and an on-track check for each fund",
            [("piggy", "15 sinking funds", "Target, starting balance, monthly plan, target date"),
             ("bar_chart", "Progress & projection", "Months to go and projected finish date"),
             ("calendar", "On-track status", "Shows what's needed per month if you're behind"),
             ("stack", "Deposits by month", "See how much you saved each month")]),
        f2=("Log in seconds", "Every deposit and withdrawal updates your balances",
            [("table", "500-entry log", "Date, fund, deposit or withdrawal, note"),
             ("money", "Totals", "Deposited, withdrawn and entries at a glance")]),
        steps=["Add your savings goals", "Log deposits and withdrawals", "Watch every goal fill up"],
        title="Sinking Funds Tracker Spreadsheet, Savings Goal Tracker Excel Google Sheets, Savings Challenge, Budget Savings Planner Template",
        tags="sinking funds, savings tracker, savings goal, sinking fund tracker, savings challenge, google sheets budget, excel savings, money saving, budget planner, savings planner, financial goals, emergency fund, savings template",
        price=("$4.49", "$2.99", "Sinking-fund and savings trackers commonly sell for about $2–$7."),
        desc="""Plan for the expenses you know are coming — holidays, car repairs, insurance, travel — and watch every savings goal fill up. Log deposits and withdrawals; balances, progress and on-track status update automatically.

━━━━━━━━━━━━━━━━━━━━
FEATURES
━━━━━━━━━━━━━━━━━━━━
✔ Up to 15 sinking funds: target, starting balance, monthly plan, target date, where it's kept
✔ Balance, remaining, progress bar, months to go and projected finish date
✔ On-track status — and how much per month you need if you're behind
✔ 500-entry contributions log (deposits and withdrawals)
✔ Deposits by month for any year + savings progress chart
✔ Start tab with instructions; DEMO data so you can explore
"""),
    "networth": dict(
        shots=[("main", BB.S_NW, "A1:K46", "NET WORTH"), ("history", "Net Worth History", "A1:N33", "NET WORTH HISTORY"),
               ("start", "Start", "A1:K24", "NET WORTH TRACKER")],
        hero_crop=(0, 0.8, 0, 0.75),
        hero=("WEALTH", "Net Worth\nTracker", ["Assets & liabilities", "Net worth & debt-to-asset", "24-month history chart",
                                              "Change month to month"]),
        f1=("Know your number", "Everything you own minus everything you owe",
            [("bank", "Assets", "Cash, bank, investments, property, other"),
             ("card", "Liabilities", "Credit cards, loans, other"),
             ("scale", "Net worth & ratio", "Totals and debt-to-asset ratio"),
             ("pie", "Where your wealth is", "Charts by asset and liability type")]),
        f2=("Watch it grow", "24 months of history with monthly change",
            [("trend", "History chart", "Net worth month by month"),
             ("bar_chart", "Change & % change", "Green when you grow, red when you don't")]),
        steps=["List assets and liabilities", "Copy totals at month end", "Track your progress"],
        title="Net Worth Tracker Spreadsheet, Assets and Liabilities Tracker Excel Google Sheets, Wealth Tracker, Financial Planner Template",
        tags="net worth tracker, net worth, wealth tracker, assets tracker, financial planner, sheets finance, excel net worth, money tracker, personal finance, debt tracker, investment tracker, finance template, budget planner",
        price=("$3.99", "$2.79", "Net worth trackers commonly sell for about $2–$6."),
        desc="""See your full financial picture in one place. List what you own and what you owe — your net worth, totals by type and debt-to-asset ratio calculate instantly. Record the totals each month to watch your net worth grow over 24 months.

━━━━━━━━━━━━━━━━━━━━
FEATURES
━━━━━━━━━━━━━━━━━━━━
✔ 20 asset rows: cash, bank accounts, investments, property, other assets
✔ 20 liability rows: credit cards, loans, other liabilities
✔ Total assets, total liabilities, net worth and debt-to-asset ratio
✔ Charts of assets and liabilities by type
✔ 24-month net worth history with change and % change + chart
✔ Start tab with instructions; DEMO data so you can explore
"""),
    "nospend": dict(
        shots=[("main", BB.S_NS, "A1:R45", "NO-SPENDING CHALLENGE"), ("start", "Start", "A1:K24", "NO-SPEND CHALLENGE TRACKER")],
        hero=("SAVE MORE", "No-Spend\nChallenge", ["Up to 60-day challenge", "Streaks & success rate", "Money saved estimate",
                                                   "Colour-coded progress grid"]),
        f1=("Build a no-spend habit", "Mark each day — streaks, success rate and savings update",
            [("ban", "Daily log", "✓ No spend, ✗ Spent or ★ Exception"),
             ("repeat", "Streaks", "Current and longest streak"),
             ("money", "Money saved", "Running total, day by day"),
             ("calendar", "Progress grid", "Every day colour-coded")]),
        f2=None,
        steps=["Set your dates and exceptions", "Mark each day", "Watch your savings grow"],
        title="No Spend Challenge Tracker Spreadsheet, 30 Day Savings Challenge Excel Google Sheets, Spending Tracker, Money Saving Challenge",
        tags="no spend challenge, savings challenge, no spend tracker, money challenge, spending tracker, frugal living, 30 day challenge, sheets tracker, excel tracker, saving money, budget challenge, habit tracker, money saving",
        price=("$2.99", "$1.99", "No-spend and savings challenges commonly sell for about $1–$5."),
        desc="""Take a no-spend challenge and see exactly how much you save. Choose the length (up to 60 days) and your allowed exceptions, then mark each day — your streaks, success rate and money saved update automatically.

━━━━━━━━━━━━━━━━━━━━
FEATURES
━━━━━━━━━━━━━━━━━━━━
✔ Challenge name, start date and length (1–60 days)
✔ Allowed exceptions (groceries, bills…) that don't break your streak
✔ Daily log: ✓ No spend, ✗ Spent or ★ Exception, with what you bought and the amount
✔ Current streak, longest streak and success rate
✔ Money saved (estimate) and a running "saved so far" total
✔ Colour-coded progress grid of every day
✔ Start tab with instructions; DEMO data so you can explore
"""),
    "invest": dict(
        shots=[("main", BB.S_IF, "A1:N41", "INVESTMENT FORECAST"), ("compare", "Compare Scenarios", "A1:J38", "COMPARE SCENARIOS"),
               ("start", "Start", "A1:K24", "INVESTMENT GROWTH CALCULATOR")],
        hero=("INVESTING", "Investment\nCalculator", ["Future value & growth", "Monthly, quarterly or annual",
                                                            "Inflation-adjusted value", "3 return scenarios"]),
        f1=("See how investing could grow", "Change any assumption and the projection updates",
            [("trend", "Future value", "Estimated balance at the end of your period"),
             ("money", "Contributions vs growth", "What you put in and what it could earn"),
             ("scale", "Today's money", "Adjusted for inflation"),
             ("table", "Year by year", "Up to 50 years")]),
        f2=("Compare three scenarios", "Conservative, moderate and optimistic returns side by side",
            [("bar_chart", "Three return rates", "Edit each scenario's assumption"),
             ("trend", "Growth chart", "All three lines on one chart")]),
        steps=["Enter amount, contribution and years", "Set a return assumption", "Compare scenarios"],
        title="Investment Growth Calculator Spreadsheet, Compound Interest Calculator Excel Google Sheets, Savings Growth, Retirement Planner",
        tags="investment tracker, compound interest, invest calculator, savings growth, retirement planner, financial planner, sheets finance, excel calculator, wealth building, money growth, finance template, investing planner, fire calculator",
        price=("$3.99", "$2.79", "Compound-interest and investment calculators commonly sell for about $2–$7."),
        desc="""See how regular investing could grow over time. Enter a starting amount, a regular contribution, an assumed return and the number of years — the future value, contributions, growth and inflation-adjusted value update instantly. Compare three return scenarios side by side.

All results are HYPOTHETICAL projections for planning and education, not guaranteed returns or financial advice.

━━━━━━━━━━━━━━━━━━━━
FEATURES
━━━━━━━━━━━━━━━━━━━━
✔ Initial investment, contribution amount and frequency (monthly, quarterly, annually)
✔ Annual return assumption and investment period (1–50 years)
✔ Estimated future value, total contributed and growth
✔ Inflation-adjusted value in today's money
✔ Growth checkpoints + stacked chart, and a year-by-year table
✔ Compare three scenarios (conservative, moderate, optimistic) with a chart
✔ Start tab with instructions; DEMO data so you can explore
"""),
    "habits": dict(
        shots=[("main", "October", "A1:AL35", "OCTOBER"), ("year", "Year Overview", "A1:O37", "YEAR OVERVIEW"),
               ("start", "Start", "A1:K36", "HABIT TRACKER")],
        hero=("HABITS", "Habit\nTracker", ["12 monthly trackers", "Up to 12 habits", "Success rates & goals",
                                           "Year overview & charts"]),
        f1=("Track every day, every habit", "Tick ✓ each day — rates and charts update themselves",
            [("week", "Monthly grids", "One row per habit, one column per day"),
             ("bar_chart", "Daily completion", "Chart of how many habits you hit each day"),
             ("scale", "Monthly goal", "See which habits meet your goal rate"),
             ("calendar", "Today highlighted", "Always know where you are")]),
        f2=("See your whole year", "Every habit's success rate, month by month",
            [("table", "Year overview", "Heat-map of success rates"),
             ("stack", "Best habit & month", "Your strongest habit and best month")]),
        steps=["Type your habits and the year", "Tick ✓ each day", "Review your month and year"],
        title="Habit Tracker Spreadsheet Google Sheets Excel, Monthly Habit Tracker, Daily Goal Tracker, Digital Habit Tracker, 12 Months",
        tags="habit tracker, digital habits, google sheets habit, habit spreadsheet, daily tracker, goal tracker, monthly tracker, routine tracker, self care tracker, productivity, excel tracker, habit planner, new year goals",
        price=("$3.99", "$2.79", "Habit trackers on Etsy range from under $1 to about $18; most sell for $2–$7."),
        desc="""Build better habits one tick at a time. Type up to 12 habits, tick ✓ each day — every month shows your success rate per habit and a daily completion chart, and the year overview shows your progress month by month.

━━━━━━━━━━━━━━━━━━━━
FEATURES
━━━━━━━━━━━━━━━━━━━━
✔ 12 monthly tabs (January–December) for any year you choose
✔ Up to 12 habits, renamed in one place
✔ Daily ✓ / ✗ dropdowns, today highlighted, extra days greyed out
✔ Done count, success rate and "on goal" check per habit (you set the goal %)
✔ Daily completion row and chart for every month
✔ Year overview: heat-map of every habit by month, best habit, best month, total ✓
✔ Start tab with instructions; DEMO data so you can explore
"""),
}
