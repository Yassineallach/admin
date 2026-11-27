"""DEMO DATA for PRODUCT 3 — Weekly Planner Pro.

Story: Jordan Lee, a marketing lead, plans six weeks from Monday 2 Nov 2026. The demo's "today" is Wednesday
11 Nov 2026 (week 2), so week 1 is complete, week 2 is in progress and weeks 3-6 are planned ahead.
Deterministic (seeded), so rebuilding gives identical files.
"""
from __future__ import annotations

import datetime as dt
import random

FIRST_WEEK = dt.date(2026, 11, 2)
ANCHOR = dt.date(2026, 11, 11)

NAME = "Jordan Lee"
TITLE = "Jordan's Weekly Planner"
EMAIL = "jordan@example.com"
MOTTO = "Focus"

CATEGORIES = ["Work", "Personal", "Health", "Family", "Finance", "Learning", "Home", "Errands", "Social", "Admin"]
PRIORITIES = [("High", "Must happen today"), ("Medium", "Important, can move"), ("Low", "Nice to have")]
STATUSES = ["Not started", "In progress", "Done", "Waiting", "Postponed", "Cancelled"]
DONE = "Done"
HABITS = ["Wake up by 6:30", "Read 20 minutes", "Meditate 10 min", "Walk 8,000 steps", "Journal", "Stretch",
          "No phone after 9 pm", "Plan tomorrow"]
EXERCISE = ["Walk", "Run", "Gym", "Yoga", "Cycling", "Swim", "HIIT", "Pilates", "Sports", "Rest day"]

WEEKS = [
    ("Launch the winter campaign brief", ["Finish campaign brief", "Book dentist", "3 gym sessions"]),
    ("Present the Q4 report and clear the inbox", ["Q4 report deck", "Inbox zero by Friday", "Call Mum"]),
    ("Hire the content designer", ["Final interviews", "Draft offer", "Plan Sam's birthday"]),
    ("Holiday budget and gift list", ["Set gift budget", "Order gifts", "Finish online course module 3"]),
    ("Year-end reviews", ["Write 4 team reviews", "Self-review", "Book holiday flights"]),
    ("Plan 2027", ["Draft 2027 goals", "Clean up files", "Team celebration"]),
]

TASKS = {
    "Work": ["Reply to client emails", "Campaign brief draft", "Review ad creatives", "1:1 with Priya", "Update project tracker",
             "Prepare Q4 report", "Team stand-up notes", "Budget review with finance", "Write blog outline",
             "Approve social posts", "Interview candidate", "Send meeting recap"],
    "Personal": ["Call Mum", "Plan weekend trip", "Sort photos", "Write thank-you card"],
    "Health": ["Book dentist", "Meal prep", "Order vitamins", "Yoga class"],
    "Family": ["School pickup", "Help with homework", "Family dinner", "Buy birthday present"],
    "Finance": ["Pay credit card", "Check budget", "Submit expenses", "Review subscriptions"],
    "Learning": ["Course module 2", "Read industry article", "Practice Spanish 15 min"],
    "Home": ["Laundry", "Water plants", "Fix kitchen tap", "Clean fridge"],
    "Errands": ["Post office", "Pick up dry cleaning", "Groceries"],
    "Social": ["Coffee with Alex", "Book table for Friday"],
    "Admin": ["Renew car insurance", "File receipts", "Update calendar"],
}
APPTS = [("09:30", "Team stand-up"), ("11:00", "Client call — Brightside"), ("13:00", "Lunch with Sam"),
         ("14:30", "Design review"), ("16:00", "Dentist"), ("10:00", "1:1 with Priya"), ("15:00", "Finance sync"),
         ("18:30", "Yoga class"), ("12:30", "Interview — content designer")]
SCHEDULE = ["Deep work: campaign brief", "Email & admin", "Meetings", "Lunch break", "Creative review", "Planning",
            "Focus block", "Calls", "Report writing", "Learning", "Wrap-up & plan tomorrow"]
NOTES = ["Ask Priya about the new brand colours.", "Remember: invoices due Friday.", "Good energy today — keep mornings meeting-free.",
         "Follow up with Brightside next week.", "Try the new focus playlist.", "Pick up the parcel before 6 pm."]
REFLECTION = [
    ("Shipped the campaign brief a day early.", "Too many meetings on Tuesday.", "Block focus time before 11 am.",
     "Q4 report and inbox zero", 8),
    ("Q4 report draft done; good feedback from the team.", "Slept badly Monday, low energy.", "Protect the evening routine.",
     "Hiring and interviews", 7),
]


def _rng(seed):
    return random.Random(seed)


def week(n: int, today: dt.date = ANCHOR):
    """Content for week tab n (1-6). Returns a dict the builder writes into the sheet."""
    start = FIRST_WEEK + dt.timedelta(days=7 * (n - 1))
    goal, prios = WEEKS[n - 1]
    r = _rng(n * 101)
    full = n <= 3                       # weeks 1-3 fully planned; 4-6 lighter
    days = []
    for d in range(7):
        date = start + dt.timedelta(days=d)
        past = date < today
        is_today = date == today
        weekend = d >= 5
        k = r.randint(2, 4) if weekend else r.randint(5, 8)
        if not full:
            k = r.randint(1, 3) if not weekend else r.randint(0, 2)
        cats = (["Family", "Home", "Social", "Personal", "Health", "Errands"] if weekend else
                ["Work", "Work", "Work", "Work", "Admin", "Finance", "Health", "Learning", "Personal", "Errands"])
        tasks, used = [], set()
        for i in range(k):
            for _ in range(20):
                cat = r.choice(cats)
                t = r.choice(TASKS[cat])
                if t not in used:
                    break
            used.add(t)
            pr = r.choices(["High", "Medium", "Low"], [3, 4, 2])[0]
            if past:
                st = r.choices(["Done", "Postponed", "Cancelled", "Waiting"], [12, 2, 1, 1])[0]
            elif is_today:
                st = ["Done", "Done", "In progress"][i] if i < 3 else "Not started"
            else:
                st = "Not started" if r.random() < 0.85 else "Waiting"
            tasks.append((t, cat, pr, st))
        pri = [(("✓" if past or (is_today and i == 0) else None), tasks[i][0]) for i in range(min(3, len(tasks)))]
        appts = [] if weekend or not full else r.sample(APPTS, r.randint(1, 3))
        appts.sort()
        sched = {}
        if full and not weekend:
            for s in sorted(r.sample(range(9), r.randint(4, 6))):
                sched[s] = r.choice(SCHEDULE)
        note = r.choice(NOTES) if full and r.random() < 0.6 else None
        days.append(dict(date=date, tasks=tasks, priorities=pri, appts=appts, schedule=sched, note=note))
    tracked = [start + dt.timedelta(days=d) < today or start + dt.timedelta(days=d) == today for d in range(7)]
    habits = []
    for h in range(len(HABITS)):
        row = []
        for d in range(7):
            if not tracked[d]:
                row.append(None)
            else:
                row.append("✓" if r.random() < 0.72 else "✗")
        habits.append(row)
    water = [r.randint(5, 10) if tracked[d] else None for d in range(7)]
    ex_type = [r.choice(EXERCISE[:9]) if tracked[d] and r.random() < 0.7 else ("Rest day" if tracked[d] else None) for d in range(7)]
    ex_min = [None if (t is None or t == "Rest day") else r.choice([20, 30, 30, 45, 45, 60]) for t in ex_type]
    score = [r.randint(5, 9) if tracked[d] else None for d in range(7)]
    refl = REFLECTION[n - 1] if n <= len(REFLECTION) and start + dt.timedelta(days=6) < today else None
    pdone = [("✓" if start + dt.timedelta(days=6) < today or (i == 0 and n == 2) else None) for i in range(3)]
    return dict(start=start, goal=goal, priorities=list(zip(pdone, prios)), days=days, habits=habits, water=water,
                ex_type=ex_type, ex_min=ex_min, score=score, reflection=refl)


IMPORTANT = [(dt.date(2026, 11, 5), "Sam's birthday", "Family"), (dt.date(2026, 11, 11), "Remembrance Day", "Personal"),
             (dt.date(2026, 11, 14), "Weekend away — Lake District", "Personal"), (dt.date(2026, 11, 20), "Payday", "Finance"),
             (dt.date(2026, 11, 26), "Thanksgiving dinner", "Family"), (dt.date(2026, 11, 26), "Office closed", "Work"),
             (dt.date(2026, 12, 4), "Team celebration", "Social"), (dt.date(2026, 12, 18), "Last day before holidays", "Work"),
             (dt.date(2026, 12, 25), "Christmas Day", "Family"), (dt.date(2026, 10, 31), "Halloween", "Family")]
DEADLINES = [("Campaign brief", dt.date(2026, 11, 6), "High", "Done"),
             ("Expense report", dt.date(2026, 11, 9), "Medium", "In progress"),
             ("Q4 report deck", dt.date(2026, 11, 13), "High", "In progress"),
             ("Content designer offer", dt.date(2026, 11, 20), "High", "Not started"),
             ("Gift orders placed", dt.date(2026, 11, 27), "Medium", "Not started"),
             ("Team reviews submitted", dt.date(2026, 12, 4), "High", "Not started"),
             ("Car insurance renewal", dt.date(2026, 11, 17), "Low", "Not started"),
             ("2027 goals draft", dt.date(2026, 12, 11), "Medium", "Not started")]
MONTH_PRIORITIES = {11: ["Launch the winter campaign", "Hire the content designer", "Exercise 3× a week"],
                    12: ["Year-end reviews", "Holiday with family", "Plan 2027 goals"]}
