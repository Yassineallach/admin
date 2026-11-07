"""DEMO DATA for the Ultimate Project Manager.

Dates are anchored to ANCHOR so the demo shows a realistic mix of completed, in-progress,
overdue and upcoming work. Everything here is fictional.
"""
import datetime as dt
import random

ANCHOR = dt.date(2026, 11, 7)


def d(offset: int) -> dt.date:
    return ANCHOR + dt.timedelta(days=offset)


TEAM = [
    ("Ava Martinez", "Project Lead", "Operations"),
    ("Liam Chen", "Developer", "Engineering"),
    ("Sofia Rossi", "Designer", "Creative"),
    ("Noah Patel", "Marketing Lead", "Marketing"),
    ("Emma Johnson", "Analyst", "Finance"),
    ("Lucas Moreau", "Developer", "Engineering"),
    ("Mia Thompson", "Content Writer", "Marketing"),
]

# id, name, description, category, manager, start, due, priority, status
PROJECTS = [
    ("Website Redesign", "Refresh brand site, new CMS and faster pages", "Marketing", "Sofia Rossi", d(-60), d(25), "High", "In Progress"),
    ("Mobile App Launch", "Ship v1.0 of the customer app on iOS and Android", "Product Development", "Liam Chen", d(-75), d(40), "Critical", "In Progress"),
    ("Q4 Marketing Campaign", "Holiday campaign across email, social and paid", "Marketing", "Noah Patel", d(-40), d(-3), "High", "In Progress"),
    ("Office Relocation", "Move HQ team to the new office space", "Operations", "Ava Martinez", d(-90), d(-20), "Medium", "Completed"),
    ("CRM Migration", "Move customer records to the new CRM platform", "Information Technology", "Lucas Moreau", d(-30), d(60), "High", "Planning"),
    ("Annual Report 2026", "Financial statements and narrative report", "Finance", "Emma Johnson", d(-10), d(55), "Medium", "In Progress"),
    ("Product Photography", "New catalogue imagery for 40 products", "Creative", "Sofia Rossi", d(-70), d(-35), "Low", "Completed"),
    ("Customer Onboarding Revamp", "Redesign the onboarding emails and guides", "Customer Success", "Mia Thompson", d(5), d(80), "Medium", "On Hold"),
]

TASK_NAMES = {
    "Website Redesign": ["Stakeholder interviews", "Sitemap & wireframes", "Visual design system", "CMS setup", "Homepage build", "Content migration", "Accessibility audit", "Performance testing", "Launch checklist", "Go-live"],
    "Mobile App Launch": ["Feature freeze", "API integration", "Push notifications", "Beta testing round 1", "Bug bash", "App store assets", "Beta testing round 2", "Store submission", "Launch announcement", "Post-launch review"],
    "Q4 Marketing Campaign": ["Campaign brief", "Audience segments", "Creative concepts", "Email sequence", "Social calendar", "Paid ads setup", "Landing page", "Mid-campaign report"],
    "Office Relocation": ["Floor plan approval", "Movers booked", "IT network setup", "Furniture delivery", "Move day", "Snag list"],
    "CRM Migration": ["Vendor contract", "Data audit", "Field mapping", "Test import", "User training plan", "Cutover plan"],
    "Annual Report 2026": ["Data collection", "Draft financial statements", "CEO letter", "Design layout", "Auditor review", "Final sign-off"],
    "Product Photography": ["Shot list", "Studio booking", "Photo shoot day 1", "Photo shoot day 2", "Retouching", "Upload to DAM"],
    "Customer Onboarding Revamp": ["Journey mapping", "Email copy", "Help-centre guides", "Welcome video script"],
}

TASK_CATS = ["Planning", "Design", "Development", "Research", "Meeting", "Admin", "Review", "Milestone"]


def build_tasks():
    rnd = random.Random(42)
    tasks = []
    team_names = [t[0] for t in TEAM]
    for (pname, _desc, _cat, mgr, pstart, pdue, ppri, pstatus) in PROJECTS:
        names = TASK_NAMES[pname]
        n = len(names)
        span = (pdue - pstart).days
        for i, tname in enumerate(names):
            s = pstart + dt.timedelta(days=int(span * i / n))
            dur = max(1, int(span / n) + rnd.randint(-2, 3))
            due = s + dt.timedelta(days=dur)
            if due > pdue:
                due = pdue
            milestone = tname in ("Go-live", "Store submission", "Move day", "Final sign-off", "Feature freeze")
            if milestone:
                s = due
            cat = "Milestone" if milestone else rnd.choice(TASK_CATS[:-1])
            who = mgr if i % 3 == 0 else rnd.choice(team_names)
            pri = rnd.choice(["Critical", "High", "High", "Medium", "Medium", "Low"]) if not milestone else "High"
            est = rnd.choice([2, 4, 6, 8, 12, 16])
            if pstatus == "Completed":
                status, prog = "Completed", 1.0
            elif pstatus == "On Hold":
                status, prog = "Backlog", 0.0
            elif due < ANCHOR - dt.timedelta(days=4):
                # most past tasks are done; a few are deliberately overdue
                if rnd.random() < 0.8:
                    status, prog = "Completed", 1.0
                else:
                    status, prog = rnd.choice([("In Progress", 0.6), ("Review", 0.9)])
            elif s <= ANCHOR:
                status, prog = rnd.choice([("In Progress", 0.4), ("In Progress", 0.7), ("Review", 0.9), ("To Do", 0.0)])
            else:
                status, prog = rnd.choice([("To Do", 0.0), ("Backlog", 0.0), ("To Do", 0.0)])
            act = round(est * prog * rnd.uniform(0.8, 1.3), 1) if prog > 0 else None
            tasks.append(dict(
                name=tname, desc=f"{tname} for {pname}", project=pname, cat=cat, who=who,
                start=s, due=due, pri=pri, status=status, est=est, act=act, prog=prog,
                notes="Client sign-off needed" if rnd.random() < 0.12 else None,
            ))
    # a few stand-alone admin tasks due in the coming days
    extras = [
        ("Weekly status report", "Admin", "Ava Martinez", 0, 0, "Medium", "To Do"),
        ("Renew software licences", "Admin", "Emma Johnson", -2, 3, "High", "In Progress"),
        ("Team retrospective", "Meeting", "Ava Martinez", 2, 2, "Low", "To Do"),
        ("Budget forecast update", "Planning", "Emma Johnson", -5, 1, "High", "Review"),
    ]
    for (n_, c_, w_, so, do, p_, st) in extras:
        tasks.append(dict(name=n_, desc=n_, project="Annual Report 2026" if "Budget" in n_ else None, cat=c_, who=w_,
                          start=d(so), due=d(do), pri=p_, status=st, est=2, act=None,
                          prog=0.5 if st != "To Do" else 0.0, notes=None))
    return tasks


# project index (1-based) , category, planned, actual, date offset, vendor, description
BUDGET = [
    (1, "Contractors", 12000, 9800, -40, "PixelForge Studio", "Front-end development sprint"),
    (1, "Software", 2400, 2400, -55, "CMS Cloud", "Annual CMS licence"),
    (1, "Marketing", 1500, 600, -5, "Stock Images Co", "Imagery and icons"),
    (2, "Labor", 30000, 26500, -20, "Internal", "Mobile engineering hours"),
    (2, "Software", 3500, 3900, -60, "DevTools Inc", "Testing & CI services"),
    (2, "Marketing", 5000, 1200, -2, "AppPromo Ltd", "Launch promotion"),
    (3, "Marketing", 18000, 19400, -25, "AdReach", "Paid social and search"),
    (3, "Contractors", 4000, 3600, -30, "Copy Collective", "Campaign copywriting"),
    (4, "Contractors", 9000, 8700, -60, "SwiftMove", "Movers and packing"),
    (4, "Hardware", 6000, 6450, -45, "OfficeTech", "Network and AV equipment"),
    (4, "Other", 2500, 2100, -40, "FurniCo", "Furniture installation"),
    (5, "Software", 15000, 4000, -10, "CRM Vendor", "Licence deposit"),
    (5, "Contractors", 8000, 0, 15, "DataBridge", "Migration consultant"),
    (6, "Labor", 6000, 1800, -3, "Internal", "Finance team hours"),
    (6, "Contractors", 3000, 0, 20, "Layout Lab", "Report design"),
    (7, "Contractors", 5000, 4800, -50, "Studio Nine", "Photographer and studio"),
    (7, "Travel", 800, 950, -48, "City Cabs", "Product transport"),
    (8, "Labor", 4000, 0, 10, "Internal", "Customer success hours"),
]

RECURRING = [
    # name, project, cat, who, freq, custom, start offset, end offset, priority, status, last completed offset, count
    ("Daily stand-up", None, "Meeting", "Ava Martinez", "Daily", None, -120, None, "Medium", "Active", -1, 85),
    ("Weekly team sync", None, "Meeting", "Ava Martinez", "Weekly", None, -95, None, "High", "Active", -3, 13),
    ("Sprint planning", "Mobile App Launch", "Planning", "Liam Chen", "Biweekly", None, -73, 40, "High", "Active", -11, 5),
    ("Publish blog post", "Q4 Marketing Campaign", "Admin", "Mia Thompson", "Weekly", None, -38, 30, "Medium", "Active", -6, 5),
    ("Monthly budget review", None, "Review", "Emma Johnson", "Monthly", None, -250, None, "High", "Active", -37, 8),
    ("Client invoice run", None, "Admin", "Emma Johnson", "Monthly", None, -340, None, "Critical", "Active", -7, 11),
    ("Quarterly OKR review", None, "Review", "Ava Martinez", "Quarterly", None, -310, None, "High", "Active", -36, 3),
    ("Security patching", None, "Development", "Lucas Moreau", "Custom", 10, -100, None, "High", "Active", -2, 10),
    ("Annual insurance renewal", None, "Admin", "Ava Martinez", "Annually", None, -300, None, "Medium", "Active", -300, 1),
    ("Social media analytics", "Q4 Marketing Campaign", "Research", "Noah Patel", "Weekly", None, -40, None, "Low", "Paused", -14, 4),
]

# schedule: (day offset from Monday of anchor week, start hour, start minute, duration hours, task name or event)
SCHEDULE = [
    (0, 9, 0, 1, "Daily stand-up"), (0, 10, 0, 2, "Homepage build"), (0, 14, 0, 2, "Bug bash"),
    (1, 9, 0, 1, "Daily stand-up"), (1, 11, 0, 3, "Content migration"), (1, 15, 0, 1, "Weekly team sync"),
    (2, 9, 0, 1, "Daily stand-up"), (2, 10, 0, 2, "Data collection"), (2, 13, 0, 3, "Beta testing round 2"),
    (3, 9, 0, 1, "Daily stand-up"), (3, 10, 0, 1, "Budget forecast update"), (3, 14, 0, 2, "Accessibility audit"),
    (4, 9, 0, 1, "Daily stand-up"), (4, 11, 0, 2, "Renew software licences"), (4, 16, 0, 1, "Team retrospective"),
    (5, 10, 0, 2, "Weekly status report"),
    (7, 9, 0, 1, "Daily stand-up"), (7, 10, 0, 3, "Performance testing"), (8, 13, 0, 2, "Data audit"),
    (9, 9, 0, 2, "Draft financial statements"), (10, 14, 0, 2, "Field mapping"), (11, 10, 0, 1, "Launch checklist"),
]

DETAILS = [
    # project idx, type, description, owner, date offset, status
    (1, "Objective", "Increase organic conversions by 20%", "Sofia Rossi", 25, "On track"),
    (1, "Objective", "Cut page load time below 2 seconds", "Liam Chen", 25, "On track"),
    (1, "Deliverable", "Responsive design system in Figma", "Sofia Rossi", -20, "Done"),
    (1, "Deliverable", "New CMS with 120 migrated pages", "Lucas Moreau", 18, "In progress"),
    (1, "Milestone", "Design sign-off", "Sofia Rossi", -25, "Done"),
    (1, "Milestone", "Public launch", "Ava Martinez", 25, "Planned"),
    (1, "Dependency", "Brand guidelines v3 from Creative", "Sofia Rossi", -30, "Resolved"),
    (1, "Risk", "Content migration may slip — High impact", "Mia Thompson", 18, "Monitoring"),
    (1, "Note", "Hosting contract renews in January", "Ava Martinez", 60, "Info"),
    (2, "Objective", "10,000 installs in the first month", "Noah Patel", 70, "Planned"),
    (2, "Objective", "Crash-free sessions above 99.5%", "Liam Chen", 40, "On track"),
    (2, "Deliverable", "iOS and Android builds in stores", "Liam Chen", 40, "In progress"),
    (2, "Milestone", "Feature freeze", "Liam Chen", -40, "Done"),
    (2, "Milestone", "Store submission", "Liam Chen", 30, "Planned"),
    (2, "Dependency", "Payments API from Finance systems", "Lucas Moreau", 5, "Open"),
    (2, "Risk", "App store review delays — Medium impact", "Noah Patel", 30, "Monitoring"),
    (3, "Objective", "Holiday revenue +15% year over year", "Noah Patel", -3, "At risk"),
    (3, "Deliverable", "6-email nurture sequence", "Mia Thompson", -10, "Done"),
    (3, "Milestone", "Campaign live", "Noah Patel", -20, "Done"),
    (3, "Risk", "Paid media overspend — High impact", "Emma Johnson", 0, "Open"),
    (5, "Objective", "Single source of customer truth", "Lucas Moreau", 60, "Planned"),
    (5, "Milestone", "Test import complete", "Lucas Moreau", 35, "Planned"),
    (5, "Risk", "Data quality issues in legacy CRM — High impact", "Emma Johnson", 20, "Open"),
    (6, "Objective", "Publish report before Jan 31", "Emma Johnson", 55, "On track"),
    (6, "Milestone", "Auditor review", "Emma Johnson", 45, "Planned"),
]

DECISION = {
    "name": "Choose a CRM platform for 2027",
    "options": ["Option A — CloudCRM", "Option B — SalesHub", "Option C — OpenCRM"],
    "criteria": [
        ("Total cost (3 years)", 0.25, 6, 8, 9),
        ("Ease of use", 0.20, 9, 7, 5),
        ("Integrations", 0.20, 8, 9, 6),
        ("Reporting", 0.15, 7, 8, 6),
        ("Vendor support", 0.10, 8, 7, 4),
        ("Data migration effort", 0.10, 6, 7, 8),
    ],
}
