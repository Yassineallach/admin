"""PRODUCT 2 — Ultimate OneNote Planner: content model (shared by the OneNote, HTML and PDF renderers).

A planner is a list of Sections; each Section has Pages; each Page is a list of Blocks.
Block types (tuples):
  ("h", text)                         sub-heading
  ("fields", [labels], cols)          label + blank answer cells, `cols` label/answer pairs per row
  ("check", items_or_count)           checklist (OneNote to-do tags / PDF boxes)
  ("table", headers, rows_or_count)   table; rows is int (blank rows) or list of row lists
  ("lines", n)                        blank writing lines
  ("calendar", year, month)           month grid
  ("habit", habits_or_count, days)    habit grid: habits x days
  ("scale", label, n)                 1..n rating row
  ("note", text)                      tip / callout
  ("cols", [blocks], [blocks])        two columns side by side
"""
from __future__ import annotations

import calendar as cal
import datetime as dt
from dataclasses import dataclass, field

YEAR = 2027
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# section colours (teal theme)
C = {"index": "0B4F4C", "year": "0F6E68", "month": "14958B", "week": "2F6FAA", "task": "1E9E75", "project": "2BB3A6",
     "meeting": "2F6FAA", "goal": "9B7BE0", "time": "EE8A3A", "pro": "6F5BD0", "client": "1FA99C", "invoice": "CF3A43",
     "report": "4D6A8A", "creative": "D9670F", "notes": "9B7BE0"}


@dataclass
class Page:
    title: str
    blocks: list
    subtitle: str = ""
    key: str = ""          # unique id used for links
    section: str = ""


@dataclass
class Section:
    name: str
    color: str
    group: str             # section group (OneNote) / tab group (PDF)
    pages: list = field(default_factory=list)
    key: str = ""
    short: str = ""        # tab label


# ---------------------------------------------------------------- block helpers
def H(t): return ("h", t)
def F(*labels, cols=2): return ("fields", list(labels), cols)
def CK(x): return ("check", x)
def T(headers, rows): return ("table", list(headers), rows)
def LN(n): return ("lines", n)
def NOTE(t): return ("note", t)
def SC(label, n=10): return ("scale", label, n)
def HB(habits, days=7): return ("habit", habits, days)
def COLS(a, b): return ("cols", a, b)


# ---------------------------------------------------------------- yearly + monthly + weekly
def year_pages(year):
    pages = []
    pages.append(Page("How to use this planner", [
        NOTE("Every page is a reusable template. Duplicate a page (right-click › Copy, then paste in the page list) to reuse it."),
        H("Navigation"),
        CK(["Start on the General Index — every section is one click away",
            "Each page has a ⌂ Index link at the top",
            "Monthly sections: Calendar · Goals · Reflection",
            "Weekly Tracker: one page per week (53 pages)",
            "Templates: 111 ready-made pages in 10 categories",
            "Notes: 8 note-taking layouts"]),
        H("Colour code"),
        T(["Colour", "Section"], [["Teal", "Year & months"], ["Blue", "Weekly tracker, meetings"], ["Green", "Tasks"],
                                  ["Lavender", "Goals & notes"], ["Orange", "Time management, creative"], ["Red", "Invoices & expenses"]]),
        H("Tips for OneNote"),
        CK(["Click any checkbox to tick it (Ctrl+1 adds a new one)", "Tab moves to the next table cell; Tab in the last cell adds a row",
            "Ctrl+K inserts a link to another page", "Use the search box (Ctrl+E) to find anything in the planner"]),
    ], key="howto"))
    pages.append(Page(f"Yearly Goals {year}", [
        F("My word for the year", "Biggest priority", "I will be proud if…", "Main obstacle to watch", cols=1),
        H("Goals by area"),
        T(["Area", "Goal", "Why it matters", "Target date", "Status"],
          [[a, "", "", "", ""] for a in ("Career / work", "Business", "Finance", "Health", "Learning", "Relationships", "Personal", "Fun & travel")]),
        H("Quarterly milestones"),
        T(["Quarter", "Milestones", "Done?"], [[q, "", "☐"] for q in ("Q1", "Q2", "Q3", "Q4")]),
        H("Habits to build"), CK(5),
    ], key="year_goals"))
    pages.append(Page(f"Year at a Glance {year}", [("yearcal", year)], key="year_glance"))
    pages.append(Page("Resources", [
        H("Important links"), T(["Name", "Link / location", "Notes"], 8),
        H("Key contacts"), T(["Name", "Role", "Email / phone"], 6),
        H("Logins I need (never store passwords here)"), T(["Service", "Username", "Where the password is kept"], 5),
        H("Reference notes"), LN(6),
    ], key="resources"))
    return pages


def month_pages(year, m):
    name = MONTHS[m - 1]
    return [
        Page(f"{name} {year} — Calendar", [
            ("calendar", year, m),
            COLS([H("Important dates"), T(["Date", "Event"], 5)], [H("Deadlines"), T(["Date", "Deadline"], 5)]),
            COLS([H("Appointments"), T(["Date", "Time", "With"], 4)], [H("Events"), T(["Date", "Event"], 4)]),
        ], subtitle="Monthly calendar", key=f"m{m}_cal"),
        Page(f"{name} {year} — Goals", [
            F("Focus for the month", "One thing that would make this month great", cols=1),
            H("Main goals"),
            T(["Goal", "Category", "Action steps", "Target date", "Progress", "Status"], 6),
            H("Action checklist"), CK(8),
            SC("How confident am I about these goals?", 10),
        ], subtitle="Monthly goals", key=f"m{m}_goals"),
        Page(f"{name} {year} — Reflection", [
            COLS([H("Major achievements"), LN(4)], [H("Challenges"), LN(4)]),
            COLS([H("What went well"), LN(4)], [H("What needs improvement"), LN(4)]),
            H("Lessons learned"), LN(3),
            H("Priorities for next month"), CK(5),
            SC("Overall, how was this month?", 10),
        ], subtitle="Monthly reflection", key=f"m{m}_refl"),
    ]


def week_dates(year, w):
    """Monday of ISO week w (weeks past the year's last ISO week are 'spare' pages)."""
    last = dt.date(year, 12, 28).isocalendar()[1]
    if w > last:
        return None, None, last
    mon = dt.date.fromisocalendar(year, w, 1)
    return mon, mon + dt.timedelta(days=6), last


def week_page(year, w):
    mon, sun, last = week_dates(year, w)
    if mon:
        span = f"{mon:%b %d} – {sun:%b %d, %Y}".replace(" 0", " ")
        days_rows = [[f"{DAYS[i]} {(mon + dt.timedelta(days=i)).day}", "", ""] for i in range(7)]
    else:
        span = "Spare week — fill in your dates"
        days_rows = [[d, "", ""] for d in DAYS]
    return Page(f"Week {w:02d}", [
        F("Dates", "Weekly main goal", cols=1),
        COLS([H("Top 3 goals"), CK(3)], [H("Weekly priorities"), CK(4)]),
        H("Daily plan"),
        T(["Day", "Tasks", "Appointments"], days_rows),
        H("Habit tracker"),
        HB(5, 7),
        COLS([H("Weekly achievements"), LN(3)], [H("Notes"), LN(3)]),
        H("Weekly reflection"),
        F("What went well?", "What will I do differently next week?", cols=1),
        SC("Productivity this week", 10),
    ], subtitle=span, key=f"w{w}")


# ---------------------------------------------------------------- template catalog (111) + notes (8)
def tpl(title, *blocks):
    return (title, list(blocks))


TEMPLATES = {
    ("Task Management", "task", "Tasks"): [
        tpl("Daily To-Do List", F("Date", "Top priority", cols=2), H("Must do today"), CK(6), H("Should do"), CK(5), H("Could do"), CK(4), H("Notes"), LN(3)),
        tpl("Priority Matrix (Eisenhower)", NOTE("Sort tasks by urgency and importance."),
            COLS([H("Do first — urgent & important"), CK(5)], [H("Schedule — important, not urgent"), CK(5)]),
            COLS([H("Delegate — urgent, not important"), CK(5)], [H("Eliminate — neither"), CK(5)])),
        tpl("Task Tracker", T(["Task", "Project", "Owner", "Start", "Due", "Priority", "Status"], 14)),
        tpl("Weekly Task Planner", F("Week of", "Focus", cols=2), T(["Day", "Task", "Time needed", "Done"], [[d, "", "", "☐"] for d in DAYS]),
            H("Carry over to next week"), CK(4)),
        tpl("Delegation Tracker", T(["Task", "Delegated to", "Date given", "Due", "Check-in date", "Status"], 12)),
        tpl("Errands & Quick Tasks", COLS([H("Calls"), CK(5)], [H("Emails"), CK(5)]), COLS([H("Errands"), CK(5)], [H("Under 5 minutes"), CK(5)])),
        tpl("Follow-Up Tracker", T(["Who", "About", "Last contact", "Next follow-up", "Channel", "Done"], 12)),
        tpl("Routine Checklist", COLS([H("Morning routine"), CK(6)], [H("Evening routine"), CK(6)]), H("Weekly reset"), CK(6)),
        tpl("Someday / Maybe List", T(["Idea or task", "Category", "Why it matters", "Review date"], 12)),
    ],
    ("Project Management", "project", "Projects"): [
        tpl("Project Charter", F("Project name", "Sponsor", "Project manager", "Start date", "End date", "Budget", cols=2),
            H("Purpose"), LN(2), H("Objectives"), CK(4), H("Scope — in"), LN(2), H("Scope — out"), LN(2), H("Success criteria"), CK(4),
            H("Approval"), F("Approved by", "Date", cols=2)),
        tpl("Project Brief", F("Project", "Client / team", "Deadline", "Budget", cols=2), H("Background"), LN(3), H("Goals"), CK(4),
            H("Audience"), LN(2), H("Deliverables"), CK(5), H("Constraints"), LN(2)),
        tpl("Scope Statement", F("Project", "Version", cols=2), H("Justification"), LN(2), H("Deliverables"), T(["Deliverable", "Description", "Acceptance criteria"], 6),
            H("Exclusions"), LN(2), H("Assumptions"), LN(2)),
        tpl("Stakeholder Register", T(["Name", "Role", "Interest", "Influence", "Expectations", "Engagement plan"], 12)),
        tpl("RACI Matrix", NOTE("R = Responsible · A = Accountable · C = Consulted · I = Informed"),
            T(["Task / deliverable", "Person 1", "Person 2", "Person 3", "Person 4", "Person 5"], 12)),
        tpl("Work Breakdown Structure", T(["WBS #", "Work package", "Owner", "Estimate (h)", "Depends on"], 16)),
        tpl("Project Timeline", T(["Phase", "Start", "End", "Key activities", "Owner"], 10)),
        tpl("Milestone Tracker", T(["Milestone", "Target date", "Actual date", "Owner", "Status"], 12)),
        tpl("Gantt Planning Sheet", NOTE("Shade the weeks each task runs."),
            T(["Task", "W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"], 12)),
        tpl("Risk Register", T(["Risk", "Probability", "Impact", "Score", "Mitigation", "Owner", "Status"], 12)),
        tpl("Issue Log", T(["#", "Issue", "Raised by", "Date", "Priority", "Owner", "Resolution"], 12)),
        tpl("Change Request Log", T(["#", "Change", "Requested by", "Impact", "Decision", "Date"], 12)),
        tpl("Decision Log", T(["Date", "Decision", "Options considered", "Made by", "Rationale"], 10)),
        tpl("Assumptions & Constraints", COLS([H("Assumptions"), T(["Assumption", "Validated?"], 8)], [H("Constraints"), T(["Constraint", "Type"], 8)])),
        tpl("Dependency Tracker", T(["Task", "Depends on", "Type", "Owner", "Due", "Status"], 12)),
        tpl("Resource Plan", T(["Resource", "Role", "Allocation %", "Start", "End", "Cost"], 12)),
        tpl("Budget Plan", T(["Category", "Planned", "Actual", "Variance", "Notes"],
                             [[c, "", "", "", ""] for c in ("Labour", "Contractors", "Software", "Hardware", "Marketing", "Travel", "Training", "Other", "TOTAL")])),
        tpl("Communication Plan", T(["Audience", "Information", "Channel", "Frequency", "Owner"], 10)),
        tpl("Status Report", F("Project", "Period", "Overall status", "Prepared by", cols=2), H("Progress this period"), CK(5),
            H("Planned next period"), CK(5), H("Risks & issues"), T(["Item", "Impact", "Action"], 4), H("Decisions needed"), LN(2)),
        tpl("Sprint Planning", F("Sprint #", "Dates", "Sprint goal", "Capacity (points)", cols=2), T(["Story / task", "Points", "Owner", "Status"], 12)),
        tpl("Sprint Retrospective", F("Sprint #", "Date", cols=2), COLS([H("What went well"), LN(5)], [H("What didn't"), LN(5)]),
            H("Action items"), T(["Action", "Owner", "Due"], 5)),
        tpl("Kanban Snapshot", T(["Backlog", "To do", "In progress", "Review", "Done"], 10)),
        tpl("Requirements List", T(["ID", "Requirement", "Type", "Priority", "Source", "Status"], 14)),
        tpl("User Story Map", NOTE("As a <user>, I want <goal>, so that <benefit>."),
            T(["User story", "Acceptance criteria", "Priority", "Estimate"], 10)),
        tpl("Quality Checklist", F("Deliverable", "Reviewer", "Date", cols=3), CK(12), H("Findings"), LN(3)),
        tpl("Lessons Learned", T(["Area", "What happened", "Impact", "Lesson", "Recommendation"], 10)),
        tpl("Project Closure Report", F("Project", "Close date", "Final cost", "Final status", cols=2), H("Objectives met?"),
            T(["Objective", "Met?", "Evidence"], 5), H("Handover checklist"), CK(6), H("Sign-off"), F("Sponsor", "Date", cols=2)),
        tpl("Vendor Tracker", T(["Vendor", "Service", "Contact", "Contract value", "Start", "End", "Rating"], 10)),
        tpl("Project Dashboard Summary", F("Project", "Manager", "Start", "Due", "Budget", "Spent", cols=3),
            T(["Measure", "Target", "Actual", "Status"], [["Schedule", "", "", ""], ["Budget", "", "", ""], ["Scope", "", "", ""],
                                                          ["Quality", "", "", ""], ["Team", "", "", ""]]),
            H("Highlights"), LN(3)),
    ],
    ("Meeting Notes", "meeting", "Meetings"): [
        tpl("General Meeting Notes", F("Meeting", "Date", "Time", "Location / link", cols=2), H("Attendees"), LN(2), H("Agenda"), CK(5),
            H("Notes"), LN(6), H("Action items"), T(["Action", "Owner", "Due"], 6)),
        tpl("One-on-One Meeting", F("With", "Date", cols=2), COLS([H("Their topics"), CK(4)], [H("My topics"), CK(4)]),
            H("Wins since last time"), LN(2), H("Blockers"), LN(2), H("Agreed next steps"), T(["Action", "Owner", "Due"], 4)),
        tpl("Team Stand-up", F("Date", cols=1), T(["Name", "Yesterday", "Today", "Blockers"], 8)),
        tpl("Client Meeting", F("Client", "Date", "Attendees", "Project", cols=2), H("Objectives"), CK(3), H("Discussion"), LN(5),
            H("Client requests"), CK(4), H("Follow-ups"), T(["Action", "Owner", "Due"], 5)),
        tpl("Project Kickoff Meeting", F("Project", "Date", cols=2), H("Agenda"),
            CK(["Introductions & roles", "Goals & success criteria", "Scope & deliverables", "Timeline & milestones", "Risks", "Communication plan", "Next steps"]),
            H("Notes"), LN(5), H("Decisions"), LN(2)),
        tpl("Brainstorming Session", F("Topic", "Date", "Facilitator", cols=2), H("Ideas"), T(["Idea", "Proposed by", "Votes"], 12), H("Top 3 ideas"), CK(3)),
        tpl("Board / Leadership Meeting", F("Date", "Chair", "Minute taker", cols=3), T(["Agenda item", "Discussion", "Decision", "Owner"], 8),
            H("Next meeting"), F("Date", "Location", cols=2)),
        tpl("Interview Notes", F("Candidate", "Role", "Date", "Interviewer", cols=2), T(["Question", "Answer notes", "Score 1–5"], 8),
            H("Strengths"), LN(2), H("Concerns"), LN(2), F("Recommendation", cols=1)),
    ],
    ("Goal Setting", "goal", "Goals"): [
        tpl("Annual Vision", H("Where I want to be in one year"), LN(4), T(["Life area", "Vision", "Score today (1–10)"],
            [[a, "", ""] for a in ("Work", "Money", "Health", "Relationships", "Growth", "Fun")])),
        tpl("SMART Goal Planner", F("Goal", cols=1), T(["", "Answer"], [["Specific", ""], ["Measurable", ""], ["Achievable", ""], ["Relevant", ""], ["Time-bound", ""]]),
            H("Steps"), CK(6)),
        tpl("Quarterly Goals (OKRs)", F("Quarter", cols=1), T(["Objective", "Key result", "Target", "Current", "Score"], 9)),
        tpl("Goal Action Plan", F("Goal", "Deadline", cols=2), T(["Step", "Resources needed", "Due", "Done"], 10), H("Possible obstacles & solutions"), LN(3)),
        tpl("Monthly Habit Tracker", F("Month", cols=1), HB(8, 31)),
        tpl("Vision Board Planner", NOTE("Paste images or links here — OneNote lets you drop pictures anywhere on the page."),
            COLS([H("Career"), LN(3)], [H("Lifestyle"), LN(3)]), COLS([H("Health"), LN(3)], [H("Experiences"), LN(3)])),
        tpl("90-Day Plan", F("Start date", "End date", "Big goal", cols=2), T(["Month", "Focus", "Milestone", "Done"],
                                                                                    [["Month 1", "", "", "☐"], ["Month 2", "", "", "☐"], ["Month 3", "", "", "☐"]]),
            H("Weekly actions"), CK(8)),
        tpl("Goal Review & Progress", T(["Goal", "Progress %", "What's working", "Adjustments", "Next review"], 8), SC("Overall progress", 10)),
    ],
    ("Time Management", "time", "Time"): [
        tpl("Time Blocking Planner", F("Date", cols=1), T(["Time", "Block", "Notes"], [[f"{h}:00", "", ""] for h in range(6, 22)])),
        tpl("Pomodoro Tracker", F("Date", "Daily goal (pomodoros)", cols=2), T(["Task", "🍅 1", "🍅 2", "🍅 3", "🍅 4", "Done"], 10)),
        tpl("Time Audit Log", F("Date", cols=1), T(["Time", "Activity", "Category", "Productive?"], [[f"{h}:00", "", "", ""] for h in range(7, 21)])),
        tpl("Weekly Schedule", T(["Time"] + [d[:3] for d in DAYS], [[f"{h}:00"] + [""] * 7 for h in range(7, 21)])),
        tpl("Daily Routine Planner", COLS([H("Morning"), T(["Time", "Activity"], 6)], [H("Evening"), T(["Time", "Activity"], 6)]), H("Non-negotiables"), CK(4)),
        tpl("Focus & Energy Tracker", T(["Time", "Energy 1–5", "Focus 1–5", "What I did"], [[f"{h}:00", "", "", ""] for h in range(8, 20, 2)]),
            H("Patterns I notice"), LN(3)),
        tpl("Deadline Planner", T(["Deadline", "Project", "Due", "Days left", "Next step", "Status"], 12)),
    ],
    ("Professional Development", "pro", "Growth"): [
        tpl("Skills Inventory", T(["Skill", "Current level 1–5", "Target level", "How I'll improve"], 12)),
        tpl("Learning Plan", F("Learning goal", "By when", cols=2), T(["Topic", "Resource", "Hours", "Done"], 10), H("How I'll apply it"), LN(3)),
        tpl("Course Tracker", T(["Course", "Platform", "Start", "Progress", "Certificate?", "Notes"], 10)),
        tpl("Book Notes", F("Title", "Author", "Started", "Finished", cols=2), H("Key ideas"), CK(5), H("Quotes"), LN(3), H("Actions I'll take"), CK(3), SC("Rating", 5)),
        tpl("Reading List", T(["Title", "Author", "Category", "Status", "Rating"], 14)),
        tpl("Certification Tracker", T(["Certification", "Provider", "Exam date", "Cost", "Expiry", "Status"], 8)),
        tpl("Career Roadmap", F("Current role", "Target role", "Timeframe", cols=3), T(["Milestone", "Skills needed", "Target date", "Status"], 8)),
        tpl("Performance Review Prep", F("Review period", cols=1), H("Key achievements"), CK(6), H("Challenges & how I handled them"), LN(3),
            H("Goals for next period"), CK(4), H("Questions for my manager"), CK(3)),
        tpl("Feedback Log", T(["Date", "From", "Feedback", "Action I'll take"], 10)),
        tpl("Mentorship Notes", F("Mentor", "Date", cols=2), H("Topics"), CK(4), H("Advice received"), LN(4), H("Commitments"), CK(3)),
        tpl("Networking Tracker", T(["Name", "Company", "Met at", "Follow-up date", "Notes"], 12)),
        tpl("Conference Notes", F("Event", "Date", "Location", cols=3), T(["Session", "Speaker", "Key takeaways"], 6), H("People to follow up"), CK(4)),
        tpl("Personal SWOT", COLS([H("Strengths"), LN(4)], [H("Weaknesses"), LN(4)]), COLS([H("Opportunities"), LN(4)], [H("Threats"), LN(4)])),
        tpl("Accomplishments Log", T(["Date", "Accomplishment", "Impact / numbers", "Who noticed"], 12)),
        tpl("Job Application Tracker", T(["Company", "Role", "Applied", "Contact", "Stage", "Next step"], 12)),
        tpl("Interview Preparation", F("Company", "Role", "Date", cols=3), H("Why this company?"), LN(2),
            T(["Likely question", "My answer (key points)"], 8), H("Questions to ask"), CK(4)),
    ],
    ("Client & Customer Tracking", "client", "Clients"): [
        tpl("Client Directory", T(["Client", "Contact", "Email", "Phone", "Since", "Status"], 14)),
        tpl("Client Profile", F("Client", "Industry", "Main contact", "Email", "Phone", "Website", cols=2), H("Needs & goals"), LN(3),
            H("Projects"), T(["Project", "Dates", "Value"], 4), H("Notes"), LN(3)),
        tpl("Lead Tracker", T(["Lead", "Source", "Contact", "Interest", "Next action", "Status"], 12)),
        tpl("Sales Pipeline", T(["Deal", "Stage", "Value", "Probability", "Close date", "Owner"], 12)),
        tpl("Client Onboarding Checklist", F("Client", "Start date", cols=2),
            CK(["Welcome email sent", "Contract signed", "Invoice / deposit paid", "Kickoff call booked", "Access & accounts set up",
                "Questionnaire received", "Project folder created", "Timeline shared", "First check-in booked"])),
        tpl("Proposal Tracker", T(["Client", "Proposal", "Sent", "Value", "Follow-up", "Outcome"], 10)),
        tpl("Customer Feedback Log", T(["Date", "Customer", "Feedback", "Rating", "Action"], 12)),
        tpl("Client Communication Log", F("Client", cols=1), T(["Date", "Channel", "Summary", "Follow-up"], 12)),
        tpl("Contract & Renewal Tracker", T(["Client", "Contract", "Start", "End", "Value", "Renewal date", "Status"], 10)),
    ],
    ("Invoice & Expense Tracking", "invoice", "Money"): [
        tpl("Invoice", F("Invoice #", "Date", "Due date", "Bill to", "Your business", "Payment terms", cols=2),
            T(["Description", "Qty", "Rate", "Amount"], 8), F("Subtotal", "Tax", "Total due", cols=3), H("Payment details"), LN(2)),
        tpl("Invoice Tracker", T(["Invoice #", "Client", "Issued", "Due", "Amount", "Paid on", "Status"], 14)),
        tpl("Expense Log", T(["Date", "Item", "Category", "Amount", "Paid with", "Receipt?"], 16)),
        tpl("Monthly Budget", F("Month", "Income", cols=2), T(["Category", "Budget", "Actual", "Difference"],
            [[c, "", "", ""] for c in ("Housing", "Utilities", "Food", "Transport", "Insurance", "Subscriptions", "Savings", "Debt", "Fun", "Other", "TOTAL")])),
        tpl("Receipt Log", T(["Date", "Vendor", "Amount", "Category", "Stored where"], 14)),
        tpl("Mileage Log", T(["Date", "From", "To", "Purpose", "Start km/mi", "End km/mi", "Distance"], 14)),
        tpl("Subscription Tracker", T(["Service", "Cost", "Billing cycle", "Renewal date", "Keep?"], 12)),
        tpl("Payment Reminder Tracker", T(["Client", "Invoice #", "Amount", "Due", "Reminder 1", "Reminder 2", "Paid"], 10)),
    ],
    ("Reports & Analytics", "report", "Reports"): [
        tpl("Weekly Report", F("Week", "Prepared by", cols=2), H("Highlights"), CK(4), H("Metrics"), T(["Metric", "Target", "Actual", "Trend"], 5),
            H("Challenges"), LN(2), H("Next week"), CK(4)),
        tpl("Monthly Report", F("Month", "Prepared by", cols=2), T(["Metric", "Last month", "This month", "Change"], 8),
            H("Wins"), CK(3), H("Lessons"), LN(2), H("Priorities next month"), CK(3)),
        tpl("KPI Tracker", T(["KPI", "Target", "Jan", "Feb", "Mar", "Apr", "May", "Jun"], 8), T(["KPI", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Year"], 8)),
        tpl("Quarterly Business Review", F("Quarter", "Date", cols=2), T(["Area", "Goal", "Result", "Notes"], 6), H("Key insights"), LN(3), H("Next quarter priorities"), CK(4)),
        tpl("Project Health Report", F("Project", "Date", cols=2), T(["Dimension", "Status (G/A/R)", "Comment"],
            [[d, "", ""] for d in ("Schedule", "Budget", "Scope", "Quality", "Risks", "Team")]), H("Recovery actions"), CK(4)),
        tpl("Data Analysis Notes", F("Question", "Data source", cols=2), H("Method"), LN(2), H("Findings"), CK(5), H("Recommendations"), LN(3)),
    ],
    ("Creative Brainstorming", "creative", "Ideas"): [
        tpl("Mind Map Planner", F("Central idea", cols=1), T(["Branch", "Sub-ideas"], 8), H("Connections I notice"), LN(3)),
        tpl("Idea Inbox", T(["Date", "Idea", "Category", "Next step"], 16)),
        tpl("Brainstorm Session", F("Challenge", "Date", cols=2), H("Rapid ideas"), T(["#", "Idea"], [[str(i), ""] for i in range(1, 13)]), H("Best idea & why"), LN(2)),
        tpl("Content Calendar", T(["Date", "Channel", "Topic", "Format", "Status"], 16)),
        tpl("Content Idea Bank", T(["Idea", "Audience", "Format", "Priority"], 14)),
        tpl("Blog Post Planner", F("Working title", "Target keyword", "Publish date", cols=2), H("Outline"), CK(6), H("Call to action"), LN(1),
            H("Checklist"), CK(["Draft", "Images", "SEO title & description", "Proofread", "Published", "Shared"])),
        tpl("Social Media Planner", T(["Day", "Platform", "Post idea", "Caption / hashtags", "Posted"], [[d, "", "", "", "☐"] for d in DAYS])),
        tpl("Product Idea Evaluation", F("Idea", cols=1), T(["Criteria", "Score 1–5", "Notes"], [[c, "", ""] for c in ("Customer need", "Market size", "Competition",
                                                                                                                         "Cost to build", "Fit with my skills", "Profit potential")]),
            F("Total score", "Decision", cols=2)),
        tpl("Design Brief", F("Project", "Client", "Deadline", cols=3), H("Objective"), LN(2), H("Audience"), LN(2), H("Style & tone"), LN(2),
            H("Deliverables"), CK(4)),
        tpl("Moodboard Notes", NOTE("Paste images, colours and links here."), COLS([H("Colours"), LN(3)], [H("Fonts"), LN(3)]), H("Inspiration links"), T(["Link", "What I like"], 6)),
        tpl("SCAMPER Worksheet", F("Product / idea", cols=1), T(["Prompt", "Ideas"], [["Substitute", ""], ["Combine", ""], ["Adapt", ""], ["Modify", ""],
                                                                                       ["Put to another use", ""], ["Eliminate", ""], ["Reverse", ""]])),
    ],
}

NOTES = [
    tpl("General Notes", F("Topic", "Date", cols=2), LN(14)),
    tpl("Quick Notes", NOTE("Capture first, organise later."), CK(10), LN(6)),
    tpl("Research Notes", F("Topic", "Question", "Date", cols=2), T(["Source", "Key points", "Reliability"], 6), H("Summary"), LN(4)),
    tpl("Meeting Notes", F("Meeting", "Date", "Attendees", cols=2), H("Notes"), LN(8), H("Actions"), T(["Action", "Owner", "Due"], 4)),
    tpl("Reading Notes", F("Title", "Author", "Chapter / pages", cols=3), H("Key ideas"), CK(5), H("Quotes"), LN(3), H("My thoughts"), LN(3)),
    tpl("Project Notes", F("Project", "Date", cols=2), H("Updates"), LN(5), H("Questions"), CK(3), H("Next steps"), CK(4)),
    tpl("Ideas & Brainstorming", F("Theme", cols=1), T(["Idea", "Why it's interesting", "Next step"], 10)),
    tpl("Personal Reflection", F("Date", "Mood", cols=2), H("Today I'm grateful for"), CK(3), H("What's on my mind"), LN(5), H("What I learned"), LN(3),
        SC("Energy today", 10)),
]


# ---------------------------------------------------------------- assemble
def build(year=YEAR):
    secs = []
    s = Section("Start", C["index"], "Start", year_pages(year), key="start", short="Start")
    secs.append(s)
    for m in range(1, 13):
        secs.append(Section(MONTHS[m - 1], C["month"], "Months", month_pages(year, m), key=f"m{m}", short=MONTHS[m - 1][:3]))
    secs.append(Section("Weekly Tracker", C["week"], "Weekly", [week_page(year, w) for w in range(1, 54)], key="weekly", short="Weeks"))
    for (cat, ckey, short), items in TEMPLATES.items():
        pages = [Page(t, b, subtitle=cat, key=f"{ckey}_{i + 1}") for i, (t, b) in enumerate(items)]
        secs.append(Section(cat, C[ckey], "Templates", pages, key=ckey, short=short))
    secs.append(Section("Notes", C["notes"], "Notes", [Page(t, b, subtitle="Note template", key=f"note_{i + 1}") for i, (t, b) in enumerate(NOTES)],
                        key="notes", short="Notes"))
    for sec in secs:
        for p in sec.pages:
            p.section = sec.key
    return secs


EXPECTED = {"Task Management": 9, "Project Management": 29, "Meeting Notes": 8, "Goal Setting": 8, "Time Management": 7,
            "Professional Development": 16, "Client & Customer Tracking": 9, "Invoice & Expense Tracking": 8,
            "Reports & Analytics": 6, "Creative Brainstorming": 11}

if __name__ == "__main__":
    secs = build()
    total = sum(len(s.pages) for s in secs)
    for s in secs:
        print(f"{s.group:10s} {s.name:28s} {len(s.pages):3d}")
    print("TOTAL pages:", total)
    for name, n in EXPECTED.items():
        got = next(len(s.pages) for s in secs if s.name == name)
        assert got == n, (name, got, n)
    assert len(next(s for s in secs if s.key == "weekly").pages) == 53
    assert len(next(s for s in secs if s.key == "notes").pages) == 8
    print("spec counts OK")
