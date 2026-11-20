"""Copy and screenshot choices for every Brass Ledger listing image set (see brand_listing.py for the layout).

Voice: plain, direct, practical. Lead with the outcome. No hype words, no exclamation marks.
Crops are (left, top, right, bottom) fractions of the real screenshot.
"""
from minis_content import MINIS

import build_minis as M

SHEETS_KICK = "Excel and Google Sheets"
COMPAT_SHEETS = [
    (True, "Microsoft Excel, Windows and Mac", "Recommended. Clickable icon sidebar and protected formula cells."),
    (True, "Excel for the web", "Opens the same Excel file in your browser."),
    (True, "Google Sheets", "A separate edition with the same formulas and charts. A free Google account is enough."),
    (False, "Apple Numbers", "Not supported."),
]
FILES_SHEETS = [("Excel workbook, DEMO", "Sample data to explore"), ("Excel workbook, BLANK", "Ready for your own data"),
                ("Google Sheets workbook, DEMO", "Sample data to explore"), ("Google Sheets workbook, BLANK", "Ready for your own data"),
                ("PDF user guide", "Set-up, formulas, troubleshooting"), ("Start Here PDF", "How to open each file")]
NOTES_SHEETS = ["Instant digital download. Nothing is shipped.", "No macros and no add-ons.",
                "Formulas only use functions that Excel 2016 and later and Google Sheets share.", "For personal use. Please do not resell the files."]
STEPS_SHEETS = [("Download", "Get the files from your Etsy Purchases page as soon as you check out."),
                ("Open", "Open the Excel file, or upload the Google Sheets file to Google Drive and open it with Google Sheets.")]

PM = dict(
    prod="01_Ultimate_Project_Manager", name="Ultimate Project Manager",
    hero=dict(kicker=f"Project manager · {SHEETS_KICK}", headline="See every project, task and deadline in one place.",
              sub="Enter your projects and tasks once. The dashboard, Gantt chart, Kanban board and calendars update themselves.",
              facts=["15 connected tabs", "Excel and Google Sheets editions", "Demo and blank files", "No macros"]),
    hero_shot=("AllinOne_Dashboard", (0, 0, 1, 0.53)),
    included=dict(headline="15 tabs that work from one set of data.", columns=[
        ("Set up and plan", ["Setup: team, currency and every dropdown list", "Project Overview: progress, budget, cost, revenue and margin",
                             "Project Manager: one project in detail", "Project Budget: planned against actual", "Instructions"]),
        ("Tasks", ["Variable Tasks: a 500-row task list", "Recurring Tasks: daily to annual, next dates worked out for you",
                   "Task Schedule: block time for tasks", "Task Filter: 10 filters and keyword search", "Decision Matrix: weighted scoring and an Eisenhower view"]),
        ("Views that update", ["All-in-One Dashboard: 4 KPI tiles and 6 charts", "Monthly Calendar", "Weekly Calendar", "Gantt Chart: daily or weekly, with a today marker",
                               "Kanban Board: cards move when a status changes"]),
    ]),
    main=dict(kicker="The task list", headline="Log a task once. Every view picks it up.", shot="Variable_Tasks", crop=(0, 0, 0.62, 0.46), points=[
        ("One row per task", "Project, owner, dates, priority, status, hours and progress."),
        ("Dropdowns from your lists", "Edit a list on Setup and every dropdown follows."),
        ("Room for 500 tasks", "Recurring tasks have their own tab and work out their next dates."),
    ]),
    summary=dict(kicker="The dashboard", headline="Know what is due, late and over budget.", shot="AllinOne_Dashboard", crop=(0, 0, 1, 0.6), points=[
        ("4 KPI tiles and 6 charts", "For the full year or any month you pick."),
        ("Due today, upcoming, overdue", "Three lists built from your tasks."),
        ("Project performance", "Progress, budget and health for each project, and workload for each person."),
    ]),
    steps=dict(headline="Set up once, then keep the task list current.", steps=STEPS_SHEETS + [
        ("Fill in Setup", "Add your team and lists, then your projects and tasks. The other tabs update as you type.")]),
    compat=dict(headline="Works in the spreadsheet app you already use.", rows=COMPAT_SHEETS),
    receive=dict(headline="Four workbooks and two guides.", files=FILES_SHEETS, notes=NOTES_SHEETS),
)

WP = dict(
    prod="03_Weekly_Planner_Pro", name="Weekly Planner Pro",
    hero=dict(kicker=f"Weekly planner · {SHEETS_KICK}", headline="Plan the week and see what got done.",
              sub="Six reusable week tabs with tasks, a time schedule and trackers, plus a monthly calendar that fills itself from your plans.",
              facts=["8 tabs, undated", "Excel and Google Sheets editions", "Demo and blank files", "No macros"]),
    hero_shot=("week_top", None),
    included=dict(headline="Six week tabs, one setup tab, one calendar.", columns=[
        ("Setup", ["Week start: Monday or Sunday", "Week 1 date. The other weeks follow", "Working hours and slot length", "Water and exercise goals",
                   "Your lists: categories, priorities, statuses, habits", "Six-week overview with progress"]),
        ("Each week tab", ["Main goal and top 3 priorities", "8 live tiles", "7 day cards with 10 tasks each", "10-slot time schedule and appointments",
                           "Habit, water, exercise and productivity trackers", "2 charts and a weekly reflection"]),
        ("Monthly calendar", ["Pick any month from a dropdown", "Important dates and deadlines", "Tasks counted from your week tabs", "Each week's main goal and progress",
                              "Monthly priorities"]),
    ]),
    main=dict(kicker="The day card", headline="One card per day: priorities, tasks, schedule.", shot="day_card", points=[
        ("10 tasks a day", "Each with a category, priority and status dropdown."),
        ("A schedule from your hours", "10 time slots built from the working hours you set."),
        ("Progress as you go", "Done tasks strike through and the day shows its share complete."),
    ]),
    summary=dict(kicker="The monthly calendar", headline="Your month fills itself from the week tabs.", shot="calendar", points=[
        ("Tasks counted per day", "Read from all six week tabs."),
        ("Dates and deadlines", "Late deadlines turn red."),
        ("Week goals alongside", "Each week's main goal and progress next to its row."),
    ]),
    steps=dict(headline="Pick a start date, then plan.", steps=STEPS_SHEETS + [
        ("Set your week", "Choose the week start and the Week 1 date on Setup. Then fill in the day cards.")]),
    compat=dict(headline="Works in the spreadsheet app you already use.", rows=COMPAT_SHEETS),
    receive=dict(headline="Four workbooks and two guides.", files=FILES_SHEETS,
                 notes=["Instant digital download. Nothing is shipped.", "Undated. Reuse the week tabs in any year.", "No macros and no add-ons.",
                        "For personal use. Please do not resell the files."]),
)

BG = dict(
    prod="04_Ultimate_Budget_Spreadsheet", name="Ultimate Budget Spreadsheet",
    hero=dict(kicker=f"Budget spreadsheet · {SHEETS_KICK}", headline="Know where your money went, and what is left.",
              sub="Log income and spending in one place. Twelve monthly budgets, a dashboard, a bill calendar and a debt plan update themselves.",
              facts=["28 tabs, any currency", "Start the budget year in any month", "Excel and Google Sheets editions", "No macros"]),
    hero_shot=("dashboard", (0, 0, 1, 0.44)),
    included=dict(headline="28 tabs. You type in five of them.", columns=[
        ("You enter", ["Easy Setup: currency, year, categories and budgets", "Bank Accounts", "Recurring Transactions: bills and pay that post themselves",
                       "Payments: one-off bills with due dates", "Variable Transactions: a 1,000-row log"]),
        ("You review", ["All-in-One Dashboard: 8 KPIs and 6 charts", "Annual Totals", "Automated Calendar", "Paycheck Dashboard", "12 monthly budgets, January to December"]),
        ("You plan ahead", ["50/30/20 Dashboard", "Expense Distribution", "Sinking Funds", "Debt Calculator: snowball or avalanche", "Net Worth",
                            "Investment Forecast", "No-Spending Challenge"]),
    ]),
    main=dict(kicker="The monthly budget", headline="Budget against actual for every category.", shot="month", crop=(0, 0, 1, 0.62), points=[
        ("12 month tabs", "Income, fixed and variable expenses, savings and debt payments."),
        ("Budget, actual, difference", "Over-budget categories turn red."),
        ("That month's transactions", "Listed at the bottom of each tab."),
    ]),
    summary=dict(kicker="The dashboard", headline="Income, spending and savings on one page.", shot="dashboard", crop=(0, 0, 1, 0.66), points=[
        ("8 key numbers", "Income, expenses, net cash flow, savings, savings rate, budget, remaining and total debt."),
        ("6 charts", "For the full year or any single month."),
        ("One source", "Every tab reads the same totals, so the numbers agree."),
    ]),
    steps=dict(headline="Set it up in about 15 minutes.", steps=STEPS_SHEETS + [
        ("Fill in Easy Setup", "Add your categories, accounts and recurring bills. Then log spending as it happens.")]),
    compat=dict(headline="Works in the spreadsheet app you already use.", rows=COMPAT_SHEETS),
    receive=dict(headline="Four workbooks and two guides.", files=FILES_SHEETS,
                 notes=["Instant digital download. Nothing is shipped.", "No macros and no add-ons.",
                        "A planning tool, not financial advice. The investment forecast is a hypothetical projection.",
                        "For personal use. Please do not resell the files."]),
)

PL = dict(
    prod="02_Ultimate_OneNote_Planner", name="Ultimate Planner 2027",
    hero=dict(kicker="Digital planner · OneNote and PDF", headline="Your year, your weeks and your work notes in one place.",
              sub="A OneNote notebook for Windows and a 226-page hyperlinked PDF for note apps. An index and tabs, so each page is one tap away.",
              facts=["OneNote notebook and PDF planner", "Dated 2027 and undated PDF editions", "12 months and 53 weekly trackers", "111 work templates, 8 note layouts"]),
    hero_shots=[("02_Ultimate_OneNote_Planner", "index", None), ("02_Ultimate_OneNote_Planner", "w1", None), ("02_Ultimate_OneNote_Planner", "m1_cal", None)],
    included=dict(headline="212 planner pages, all linked from one index.", columns=[
        ("Start", ["General Index", "How to use", "Yearly Goals", "Year at a Glance", "Resources"]),
        ("The year", ["12 monthly sections", "Calendar, goals and reflection for each month", "53 weekly trackers, Monday to Sunday",
                      "Goals, priorities, daily plan, habits and reflection each week"]),
        ("Your work", ["111 templates in 10 categories", "Tasks, projects, meetings, goals and time", "Clients, invoices, reports and brainstorming",
                       "8 note layouts", "A linked contents page for each category"]),
    ]),
    main=dict(kicker="The weekly tracker", headline="One page for the week: goals, plan, habits.", shot="w1", points=[
        ("Top 3 goals and priorities", "Decide what matters before the week starts."),
        ("A plan for each day", "With appointments and notes."),
        ("Habits and reflection", "Tick habits daily and review the week at the end."),
    ]),
    summary=dict(kicker="The general index", headline="Every page is one tap from the index.", shot="index", points=[
        ("In OneNote", "Sections for each month and template category, with linked contents pages."),
        ("In the PDF", "Side tabs on every page and a linked index."),
        ("Back to the index", "From any page, in one tap. Pages shown are from the PDF edition."),
    ]),
    steps=dict(headline="Open the file for your app and start at the index.", steps=[
        ("Download", "Get the files from your Etsy Purchases page as soon as you check out."),
        ("Open", "Double-click the .onepkg in OneNote for Windows, or import the PDF into your note app."),
        ("Plan", "Start at the General Index. Every month, week and template is one tap away."),
    ]),
    compat=dict(headline="Opens in the note app you already use.", rows=[
        (True, "OneNote for Windows", "The OneNote notebook: typed pages, tick boxes and tables you can add rows to."),
        (True, "OneNote for Mac, web and iPad", "Insert the PDF as printouts. Links inside printouts do not click."),
        (True, "GoodNotes, Notability, Noteshelf", "Hyperlinked PDF. Tabs and index links work."),
        (True, "Xodo, Drawboard, Samsung Notes", "Hyperlinked PDF on Android and Windows."),
        (True, "Paper", "Print at home: landscape, US Letter, fit to page."),
    ]),
    receive=dict(headline="A notebook, two PDF planners and two guides.", files=[
        ("OneNote notebook (.onepkg)", "For OneNote for Windows"), ("Planner PDF, dated 2027", "226 pages, landscape"),
        ("Planner PDF, undated", "The same pages, blank dates"), ("PDF user guide", "How the planner is organised"),
        ("Start Here PDF", "Which file for which app")],
        notes=["Instant digital download. Nothing is shipped.", "The .onepkg opens in OneNote for Windows. Use the PDF on Mac, iPad and web.",
               "The undated PDF can be reused every year.", "For personal use. Please do not resell the files."]),
)

BUNDLE = dict(
    prod="06_Ultimate_Productivity_Bundle", name="Ultimate Productivity Bundle",
    hero=dict(kicker=f"Three templates · {SHEETS_KICK}", headline="Run your projects, your week and your money.",
              sub="Three complete workbooks at one price. Each updates itself as you type.",
              facts=["Project Manager, 15 tabs", "Weekly Planner Pro, 8 tabs", "Budget Spreadsheet, 28 tabs", "Excel and Google Sheets editions"]),
    hero_shots=[("01_Ultimate_Project_Manager", "AllinOne_Dashboard", (0, 0, 1, 0.5)), ("03_Weekly_Planner_Pro", "week_top", None),
                ("04_Ultimate_Budget_Spreadsheet", "dashboard", (0, 0, 1, 0.5))],
    included=dict(headline="Three workbooks, 51 tabs in total.", columns=[
        ("Project Manager · 15 tabs", ["Dashboard with KPIs and charts", "500-row task list and recurring tasks", "Gantt chart and Kanban board",
                                        "Monthly and weekly calendars", "Project budget, revenue and margin"]),
        ("Weekly Planner Pro · 8 tabs", ["Six reusable week tabs", "Day cards with tasks and a time schedule", "Habit, water and exercise trackers",
                                          "A monthly calendar that fills itself"]),
        ("Budget Spreadsheet · 28 tabs", ["12 monthly budgets and a dashboard", "Recurring bills that post themselves", "Bill calendar and paycheck planner",
                                           "Debt plan, sinking funds and net worth"]),
    ]),
    main=dict(kicker="Project Manager", headline="See every project, task and deadline in one place.", prod="01_Ultimate_Project_Manager",
              shot="AllinOne_Dashboard", crop=(0, 0, 1, 0.6), points=[
        ("Log a task once", "The dashboard, Gantt chart, Kanban board and calendars pick it up."),
        ("Know what is due and late", "Lists for today, upcoming and overdue."),
        ("Track cost", "Budget against actual for each project."),
    ]),
    summary=dict(kicker="Budget Spreadsheet", headline="Know where your money went, and what is left.", prod="04_Ultimate_Budget_Spreadsheet",
                 shot="dashboard", crop=(0, 0, 1, 0.66), points=[
        ("12 monthly budgets", "Budget against actual for every category."),
        ("Bills post themselves", "Recurring items are counted on their due dates."),
        ("A debt plan", "Snowball or avalanche, with payoff dates."),
    ]),
    steps=dict(headline="Start with whichever workbook you need first.", steps=STEPS_SHEETS + [
        ("Fill in Setup", "Each workbook has a Setup tab. Fill it in, then add your own data.")]),
    compat=dict(headline="Works in the spreadsheet app you already use.", rows=COMPAT_SHEETS),
    receive=dict(headline="Twelve workbooks and four guides.", files=[
        ("Project Manager", "4 workbooks and a PDF guide"), ("Weekly Planner Pro", "4 workbooks and a PDF guide"),
        ("Budget Spreadsheet", "4 workbooks and a PDF guide"), ("Start Here PDF", "How to open each file")],
        notes=["Each template comes as Excel and Google Sheets editions, DEMO and BLANK.", "Costs less than buying the three separately.",
               "Instant digital download. Nothing is shipped.", "No macros and no add-ons."]),
)

# ------------------------------------------------------------------ minis
MINI_COPY = {
    "debt": dict(kick="Debt payoff calculator", hero="Know the date you will be debt-free.",
                 sub="List your debts and pick snowball or avalanche. You get a payoff date for each debt and a month-by-month plan.",
                 main=("The calculator", "List your debts. The plan updates as you type."), summary=("The payoff schedule", "A balance for every debt, every month."),
                 second="schedule"),
    "funds": dict(kick="Sinking funds tracker", hero="Save for each goal and see if you are on track.",
                  sub="Set a target and a date for up to 15 funds. Log deposits and the tracker shows progress and what is still needed.",
                  main=("The funds", "Target, balance and progress for every fund."), summary=("The contributions log", "Log a deposit. The balances update."),
                  second="log"),
    "networth": dict(kick="Net worth tracker", hero="See what you own, what you owe and the difference.",
                     sub="List assets and liabilities once. Record the totals each month and follow the change over two years.",
                     main=("The statement", "Assets minus liabilities, totalled for you."), summary=("The history", "Follow the change month by month."),
                     second="history"),
    "nospend": dict(kick="No-spend challenge tracker", hero="Count your no-spend days and what they saved.",
                    sub="Set your dates and mark each day. The tracker keeps your streak, success rate and an estimate of money saved.",
                    main=("The daily log", "Mark each day. Streaks and savings update."), summary=("The progress grid", "Every day of the challenge on one grid."),
                    second=None),
    "invest": dict(kick="Investment growth calculator", hero="See what regular investing could be worth.",
                   sub="Enter a starting amount, a contribution and a return assumption. The projection shows contributions and growth year by year.",
                   main=("The forecast", "Change an assumption. The projection updates."), summary=("Compare scenarios", "Three return rates side by side."),
                   second="compare"),
    "habits": dict(kick="Habit tracker", hero="See which habits you keep, month by month.",
                   sub="Tick each day for up to 12 habits. Each month shows success rates against your goal, and the year sits on one page.",
                   main=("The monthly grid", "Tick each day. Success rates update."), summary=("The year overview", "Every habit and every month on one page."),
                   second="year"),
}
MINI_CROPS = {  # hero crop, main crop, summary crop (l, t, r, b)
    "debt": ((0, 0, 0.6, 1), None, None), "funds": ((0, 0, 0.62, 1), None, None), "networth": ((0, 0, 0.75, 0.78), (0, 0, 1, 0.78), None),
    "nospend": ((0, 0, 1, 0.62), (0, 0, 1, 0.6), (0, 0.38, 1, 1)), "invest": ((0, 0, 1, 0.62), None, None), "habits": ((0, 0, 1, 0.62), None, (0, 0, 1, 0.74)),
}


def mini_spec(key):
    c, cp = MINIS[key], MINI_COPY[key]
    name, slug, order = M.PRODUCTS[key]
    hero_c, main_c, sum_c = MINI_CROPS[key]
    clean = lambda s: s.replace("✓ No spend, ✗ Spent or ★ Exception", "No spend, spent or exception").replace(" & ", " and ")
    f1 = [(clean(t), clean(b)) for _i, t, b in c["f1"][2]]
    f2 = [(clean(t), clean(b)) for _i, t, b in c["f2"][2]] if c["f2"] else f1[2:]
    tabs = order if len(order) <= 4 else ["Start", "Year Overview", "12 monthly tabs, January to December"]
    notes = ["Instant digital download. Nothing is shipped.", "No macros and no add-ons.", "Any currency." if key != "habits" else "Works for any year.",
             "For personal use. Please do not resell the files."]
    if key == "invest":
        notes[2] = "Hypothetical projections for planning, not financial advice."
    if key == "debt":
        notes[2] = "A planning tool, not financial advice."
    return dict(
        prod=f"05_Minis/{slug}", name=name,
        hero=dict(kicker=f"{cp['kick']} · {SHEETS_KICK}", headline=cp["hero"], sub=cp["sub"], facts=[clean(x) for x in c["hero"][2]]),
        hero_shot=("main", hero_c),
        included=dict(headline=f"{len(tabs) if len(order) <= 4 else 14} tabs, ready to fill in.", columns=[
            ("Tabs", tabs), ("What it works out", [t for t, _b in (f1 + (f2 if c["f2"] else []))][:6]),
            ("Start tab", ["Settings in one place", "Instructions inside the file", "Links to every tab"])]),
        main=dict(kicker=cp["main"][0], headline=cp["main"][1], shot="main", crop=main_c, points=f1[:4] if c["f2"] else f1[:2]),
        summary=dict(kicker=cp["summary"][0], headline=cp["summary"][1], shot=cp["second"] or "main", crop=sum_c, points=f2[:3]),
        steps=dict(headline="Three steps, a few minutes.", steps=[(s, "") for s in c["steps"]]),
        compat=dict(headline="Works in the spreadsheet app you already use.", rows=COMPAT_SHEETS),
        receive=dict(headline="Four workbooks and a guide.", files=FILES_SHEETS[:4] + [("Start Here PDF", "Set-up steps")], notes=notes),
    )


MAINS = {"pm": PM, "planner": PL, "wp": WP, "bg": BG, "bundle": BUNDLE}


def all_specs():
    return {**MAINS, **{f"mini_{k}": mini_spec(k) for k in MINIS}}
