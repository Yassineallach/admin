"""DEMO DATA for PRODUCT 4 — Ultimate Budget Spreadsheet.

Story: Sam Rivera budgets the calendar year 2026. The demo's "today" is 7 Nov 2026, so January–October are complete
and November is in progress. Deterministic (seeded): rebuilding gives identical files.
"""
from __future__ import annotations

import datetime as dt
import random

YEAR, START_MONTH = 2026, "January"
ANCHOR = dt.date(2026, 11, 7)
NAME = "Sam Rivera"

INCOME = [("Salary", 5200), ("Freelance", 400), ("Bonus", 0), ("Interest", 10), ("Gifts received", 0), ("Refunds", 0),
          ("Other income", 0)]
# (category, group, bucket, monthly budget)
EXPENSE = [("Rent", "Fixed", "Needs", 1450), ("Utilities", "Fixed", "Needs", 190), ("Internet", "Fixed", "Needs", 60),
           ("Phone", "Fixed", "Needs", 45), ("Insurance", "Fixed", "Needs", 140), ("Subscriptions", "Fixed", "Wants", 40),
           ("Gym", "Fixed", "Wants", 40), ("Groceries", "Variable", "Needs", 520), ("Transport & fuel", "Variable", "Needs", 180),
           ("Health", "Variable", "Needs", 60), ("Household", "Variable", "Needs", 70), ("Pets", "Variable", "Needs", 60),
           ("Dining out", "Variable", "Wants", 220), ("Entertainment", "Variable", "Wants", 90), ("Shopping", "Variable", "Wants", 150),
           ("Personal care", "Variable", "Wants", 50), ("Gifts & donations", "Variable", "Wants", 60), ("Travel", "Variable", "Wants", 150),
           ("Education", "Variable", "Wants", 40), ("Miscellaneous", "Variable", "Wants", 50)]
PAY_METHODS = ["Debit card", "Credit card", "Cash", "Bank transfer", "Direct debit", "Mobile pay"]
ACCOUNTS = [("Everyday Checking", "Checking", "First Community Bank", 2350.00),
            ("High-Yield Savings", "Savings", "Online Savings Co.", 5100.00),
            ("Rewards Credit Card", "Credit card", "First Community Bank", 0.00),
            ("Cash Wallet", "Cash", "—", 120.00)]
# (fund, target, starting balance, monthly contribution, target date, account)
FUNDS = [("Emergency fund", 10000, 4200, 300, dt.date(2027, 12, 31), "High-Yield Savings"),
         ("Vacation 2027", 3000, 600, 200, dt.date(2027, 6, 30), "High-Yield Savings"),
         ("New laptop", 1800, 300, 100, dt.date(2027, 3, 31), "High-Yield Savings"),
         ("Holiday gifts", 800, 100, 80, dt.date(2026, 12, 1), "High-Yield Savings"),
         ("Car maintenance", 1200, 250, 50, dt.date(2027, 9, 30), "High-Yield Savings")]
# (debt, starting balance, current balance, APR %, minimum, additional, type)
DEBTS = [("Credit card balance", 3400, 2150, 21.9, 75, 50, "Credit card"),
         ("Car loan", 14000, 9800, 6.4, 310, 0, "Loan"),
         ("Student loan", 18500, 15200, 4.5, 190, 0, "Loan")]
EXTRA_DEBT = 100
# (name, amount, frequency, category, account, start, end, status)
RECURRING = [("Salary — Northwind Co.", 2400, "Biweekly", "Salary", "Everyday Checking", dt.date(2026, 1, 9), None, "Active"),
             ("Rent", 1450, "Monthly", "Rent", "Everyday Checking", dt.date(2026, 1, 1), None, "Active"),
             ("Electricity & gas", 160, "Monthly", "Utilities", "Everyday Checking", dt.date(2026, 1, 15), None, "Active"),
             ("Water & sewer", 90, "Quarterly", "Utilities", "Everyday Checking", dt.date(2026, 1, 30), None, "Active"),
             ("Internet", 60, "Monthly", "Internet", "Everyday Checking", dt.date(2026, 1, 20), None, "Active"),
             ("Phone plan", 45, "Monthly", "Phone", "Rewards Credit Card", dt.date(2026, 1, 22), None, "Active"),
             ("Car insurance", 120, "Monthly", "Insurance", "Everyday Checking", dt.date(2026, 1, 5), None, "Active"),
             ("Streaming service", 15.99, "Monthly", "Subscriptions", "Rewards Credit Card", dt.date(2026, 1, 12), None, "Active"),
             ("Music service", 10.99, "Monthly", "Subscriptions", "Rewards Credit Card", dt.date(2026, 1, 18), None, "Active"),
             ("Cloud storage", 29.99, "Annually", "Subscriptions", "Rewards Credit Card", dt.date(2026, 2, 14), None, "Active"),
             ("Gym membership", 40, "Monthly", "Gym", "Rewards Credit Card", dt.date(2026, 1, 3), None, "Active"),
             ("Language app", 12.99, "Monthly", "Education", "Rewards Credit Card", dt.date(2026, 2, 6), dt.date(2026, 7, 31), "Active"),
             ("Emergency fund transfer", 300, "Monthly", "Emergency fund", "Everyday Checking", dt.date(2026, 1, 10), None, "Active"),
             ("Vacation savings", 200, "Monthly", "Vacation 2027", "Everyday Checking", dt.date(2026, 1, 10), None, "Active"),
             ("Laptop savings", 100, "Monthly", "New laptop", "Everyday Checking", dt.date(2026, 1, 10), None, "Active"),
             ("Gift savings", 80, "Monthly", "Holiday gifts", "Everyday Checking", dt.date(2026, 1, 10), None, "Active"),
             ("Car maintenance savings", 50, "Monthly", "Car maintenance", "Everyday Checking", dt.date(2026, 1, 10), None, "Paused"),
             ("Car loan payment", 310, "Monthly", "Car loan", "Everyday Checking", dt.date(2026, 1, 25), None, "Active"),
             ("Student loan payment", 190, "Monthly", "Student loan", "Everyday Checking", dt.date(2026, 1, 28), None, "Active"),
             ("Credit card payment", 125, "Monthly", "Credit card balance", "Everyday Checking", dt.date(2026, 1, 21), None, "Active")]
# (name, amount, due, status, method, category, account)
PAYMENTS = [("Car registration", 210, dt.date(2026, 3, 15), "Paid", "Debit card", "Transport & fuel", "Everyday Checking"),
            ("Tax preparation", 150, dt.date(2026, 4, 10), "Paid", "Credit card", "Miscellaneous", "Rewards Credit Card"),
            ("Dentist", 180, dt.date(2026, 4, 22), "Paid", "Debit card", "Health", "Everyday Checking"),
            ("Vet check-up", 160, dt.date(2026, 6, 12), "Paid", "Credit card", "Pets", "Rewards Credit Card"),
            ("Wedding gift", 120, dt.date(2026, 8, 20), "Paid", "Bank transfer", "Gifts & donations", "Everyday Checking"),
            ("Concert tickets", 95, dt.date(2026, 10, 5), "Paid", "Credit card", "Entertainment", "Rewards Credit Card"),
            ("Doctor co-pay", 40, dt.date(2026, 11, 3), "Unpaid", "Debit card", "Health", "Everyday Checking"),
            ("Holiday flights", 640, dt.date(2026, 11, 14), "Scheduled", "Credit card", "Travel", "Rewards Credit Card"),
            ("Car service", 260, dt.date(2026, 11, 20), "Unpaid", "Debit card", "Transport & fuel", "Everyday Checking"),
            ("Renters insurance (annual)", 180, dt.date(2026, 12, 1), "Unpaid", "Direct debit", "Insurance", "Everyday Checking"),
            ("Holiday gifts", 300, dt.date(2026, 12, 10), "Unpaid", "Credit card", "Gifts & donations", "Rewards Credit Card")]

# variable spending patterns: category -> (times per month range, amount range, account, method, descriptions)
PATTERNS = {
    "Groceries": ((4, 5), (70, 140), "Rewards Credit Card", "Credit card", ["Supermarket", "Farmers market", "Grocery store"]),
    "Transport & fuel": ((2, 3), (35, 60), "Everyday Checking", "Debit card", ["Fuel", "Parking", "Train ticket"]),
    "Dining out": ((3, 6), (18, 65), "Rewards Credit Card", "Credit card", ["Pizza night", "Lunch with friends", "Café", "Sushi"]),
    "Entertainment": ((1, 2), (15, 45), "Rewards Credit Card", "Credit card", ["Cinema", "Bowling", "Museum"]),
    "Shopping": ((1, 3), (25, 90), "Rewards Credit Card", "Credit card", ["Clothes", "Shoes", "Online order", "Books"]),
    "Personal care": ((1, 1), (25, 55), "Everyday Checking", "Debit card", ["Haircut", "Pharmacy"]),
    "Household": ((1, 2), (15, 50), "Everyday Checking", "Debit card", ["Cleaning supplies", "Hardware store"]),
    "Pets": ((1, 1), (35, 60), "Everyday Checking", "Debit card", ["Pet food"]),
    "Health": ((0, 1), (15, 45), "Everyday Checking", "Debit card", ["Pharmacy", "Vitamins"]),
    "Gifts & donations": ((0, 1), (20, 60), "Everyday Checking", "Mobile pay", ["Birthday gift", "Charity donation"]),
    "Miscellaneous": ((0, 1), (10, 40), "Cash Wallet", "Cash", ["Market stall", "Tips"]),
    "Education": ((0, 1), (15, 40), "Rewards Credit Card", "Credit card", ["Online course", "Workbook"]),
}


def transactions():
    """Variable transactions from 1 Jan to ANCHOR. Returns list of (date, description, category, account, method, amount, note)."""
    r = random.Random(4242)
    out = []
    for m in range(1, 12):
        last = (dt.date(2026, m + 1, 1) - dt.timedelta(days=1)).day if m < 12 else 31
        days = last if m < ANCHOR.month else ANCHOR.day
        for cat, ((lo, hi), (a, b), acc, meth, descs) in PATTERNS.items():
            n = r.randint(lo, hi)
            if m == ANCHOR.month:
                n = max(0, round(n * days / last))
            for _ in range(n):
                d = dt.date(2026, m, r.randint(1, days))
                out.append((d, r.choice(descs), cat, acc, meth, round(r.uniform(a, b), 2), None))
        if r.random() < 0.7 and (m < ANCHOR.month or ANCHOR.day > 15):
            out.append((dt.date(2026, m, r.randint(5, min(25, days))), "Freelance project", "Freelance", "Everyday Checking",
                        "Bank transfer", float(r.choice([250, 300, 400, 450, 600])), "Invoice paid"))
        if m < ANCHOR.month:
            out.append((dt.date(2026, m, min(28, last)), "Savings interest", "Interest", "High-Yield Savings", "Bank transfer",
                        round(r.uniform(8, 14), 2), None))
        cash = 60 if m % 2 else 0
        if cash and m < ANCHOR.month:
            out.append((dt.date(2026, m, 2), "Cash withdrawal for wallet", "Miscellaneous", "Everyday Checking", "Cash", 0.0, "Note only"))
    out.append((dt.date(2026, 7, 12), "Summer trip — hotel", "Travel", "Rewards Credit Card", "Credit card", 680.0, "4 nights"))
    out.append((dt.date(2026, 7, 13), "Summer trip — activities", "Travel", "Rewards Credit Card", "Credit card", 210.0, None))
    out.append((dt.date(2026, 3, 30), "Annual bonus", "Bonus", "Everyday Checking", "Bank transfer", 1500.0, "After tax"))
    out.append((dt.date(2026, 5, 18), "Birthday money", "Gifts received", "Cash Wallet", "Cash", 100.0, None))
    out.append((dt.date(2026, 9, 9), "Returned jacket", "Refunds", "Rewards Credit Card", "Credit card", 65.0, None))
    out = [t for t in out if t[5] > 0]
    out += card_payoffs(out)
    out.sort(key=lambda t: t[0])
    return out


CARD = "Rewards Credit Card"


def card_spend(month, txns):
    """What was charged to the credit card in a month: logged purchases + recurring card items + paid card bills."""
    total = sum(t[5] for t in txns if t[0].month == month and t[3] == CARD and t[2] not in [c for c, _ in INCOME])
    total -= sum(t[5] for t in txns if t[0].month == month and t[3] == CARD and t[2] in [c for c, _ in INCOME])
    for nm, amt, fr, cat, acc, st, en, status in RECURRING:
        if acc != CARD or status != "Active":
            continue
        d = dt.date(2026, month, min(st.day, 28))
        if d < st or (en and d > en):
            continue
        if fr == "Monthly" or (fr == "Annually" and month == st.month):
            total += amt
    total += sum(p[1] for p in PAYMENTS if p[6] == CARD and p[3] == "Paid" and p[2].month == month)
    return round(total, 2)


def card_payoffs(txns):
    """Pay last month's card bill in full from checking on the 5th (a Transfer, so it isn't counted twice)."""
    out = []
    for m in range(1, ANCHOR.month):
        d = dt.date(2026, m + 1, 5)
        if d <= ANCHOR:
            out.append((d, f"Credit card bill — {dt.date(2026, m, 1):%B}", "Transfer", "Everyday Checking", "Bank transfer",
                        card_spend(m, txns), "Paid in full", CARD))
    return out


def paychecks():
    out, d = [], dt.date(2026, 1, 9)
    while d <= ANCHOR:
        out.append((d, "Northwind Co.", 3250.0, 620.0, 230.0, 400.0))
        d += dt.timedelta(days=14)
    return out


NET_WORTH_ITEMS = [("Cash", "Emergency cash at home", 150), ("Investments", "401(k)", 28400), ("Investments", "Brokerage account", 6200),
                   ("Other assets", "Car (estimated value)", 11500)]
NET_WORTH_LIABS = [("Other liabilities", "Family loan", 500)]
NET_WORTH_HISTORY = [(m, 61000 + 950 * m + (300 if m % 3 == 0 else 0), 30500 - 270 * m) for m in range(1, 11)]
CHALLENGE = ("November no-spend challenge", dt.date(2026, 11, 1), 30, 25.0,
             ["✓ No spend", "✓ No spend", "★ Exception", "✓ No spend", "✗ Spent", "✓ No spend", "✓ No spend"])
CHALLENGE_NOTES = {3: ("Groceries (allowed)", 64.20), 5: ("Coffee with colleague", 6.50)}
EXCEPTIONS = ["Groceries", "Bills & rent", "Fuel / transport", "Medicine", "Pet food"]
INVEST = (5000, 250, "Monthly", 0.06, 20, 0.025)
