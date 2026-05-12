import sys
import os
import argparse
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User
from app.models.category import Category, CategoryType
from app.models.account import Account, AccountType
from app.models.transaction import Transaction
from app.models.budget import Budget, BudgetPeriod
from app.models.employee import Employee
from app.models.enums import EmploymentType, PayFrequency
from app.models.recurring_transaction import RecurringTransaction
from app.models.transfer import Transfer
from app.core.security import hash_password


USERS = [
    {"email": "alice@example.com", "full_name": "Alice Anderson"},
    {"email": "bob@example.com", "full_name": "Bob Brown"},
    {"email": "carol@example.com", "full_name": "Carol Carter"},
    {"email": "david@example.com", "full_name": "David Davis"},
    {"email": "eve@example.com", "full_name": "Eve Evans"},
]

CATEGORIES_DEF = [
    {"name": "Salary",        "type": CategoryType.INCOME,  "icon": "💼", "color": "#10b981"},
    {"name": "Groceries",     "type": CategoryType.EXPENSE, "icon": "🛒", "color": "#f59e0b"},
    {"name": "Transport",     "type": CategoryType.EXPENSE, "icon": "🚌", "color": "#6366f1"},
    {"name": "Entertainment", "type": CategoryType.EXPENSE, "icon": "🎬", "color": "#ec4899"},
    {"name": "Utilities",     "type": CategoryType.EXPENSE, "icon": "⚡", "color": "#f97316"},
    {"name": "Payroll",       "type": CategoryType.EXPENSE, "icon": "💼", "color": "#8b5cf6"},
    {"name": "Housing",       "type": CategoryType.EXPENSE, "icon": "🏠", "color": "#64748b"},
]

EMPLOYEE_TEMPLATES = [
    {
        "first_name": "Brian", "last_name": "Otieno",
        "employment_type": EmploymentType.permanent,
        "pay_amount": Decimal("50000.00"),
        "pay_frequency": PayFrequency.semi_monthly,
        "pay_day_config": {"days": [15, "last"]},
        "start_date_offset_months": 6,
        "position": "Senior Developer",
        "kra_pin": "A123456789P",
        "national_id": "12345678",
        "nhif_number": "23456789",
        "nssf_number": "34567890",
        "bank_name": "Equity Bank",
        "bank_account_number": "123456789012",
    },
    {
        "first_name": "Faith", "last_name": "Wanjiru",
        "employment_type": EmploymentType.contract,
        "pay_amount": Decimal("30000.00"),
        "pay_frequency": PayFrequency.monthly,
        "pay_day_config": {"day": 25},
        "start_date_offset_months": 3,
        "position": "Designer",
        "kra_pin": "A987654321Q",
        "national_id": "87654321",
        "nhif_number": "76543210",
        "nssf_number": "65432109",
        "bank_name": "KCB",
        "bank_account_number": "210987654321",
    },
]

# Alternate bank names for variety across users
_BANKS = ["Equity Bank", "KCB", "NCBA", "Co-op Bank"]

PASSWORD = "password123"


def rand_decimal(lo: float, hi: float) -> Decimal:
    return Decimal(str(random.uniform(lo, hi))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, max(0, (end - start).days)))


def months_ago(n: int, today: date) -> date:
    month = today.month - n
    year = today.year
    while month <= 0:
        month += 12
        year -= 1
    # Clamp to valid day (e.g. Jan 31 minus 1 month → Jan 31 not valid in Feb)
    import calendar
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(today.day, last))


def wipe(db) -> None:
    db.query(Transfer).delete()
    db.query(Transaction).delete()
    db.query(RecurringTransaction).delete()
    db.query(Employee).delete()
    db.query(Budget).delete()
    db.query(Account).delete()
    db.query(Category).delete()
    db.query(User).delete()
    db.commit()
    print("Existing data wiped.")


def seed(db) -> dict:
    random.seed(42)
    today = date.today()
    first_of_month = today.replace(day=1)

    if first_of_month.month == 1:
        prev_start = date(first_of_month.year - 1, 12, 1)
    else:
        prev_start = date(first_of_month.year, first_of_month.month - 1, 1)
    prev_end = first_of_month - timedelta(days=1)

    last_30 = today - timedelta(days=30)

    hashed_pw = hash_password(PASSWORD)
    counts = {
        "users": 0, "categories": 0, "accounts": 0,
        "transactions": 0, "budgets": 0, "employees": 0,
        "recurring_transactions": 0, "transfers": 0,
    }

    for user_idx, user_data in enumerate(USERS):
        user = User(
            email=user_data["email"],
            full_name=user_data["full_name"],
            hashed_password=hashed_pw,
            is_active=True,
        )
        db.add(user)
        db.flush()
        counts["users"] += 1

        cat_map: dict[str, Category] = {}
        for cat_def in CATEGORIES_DEF:
            cat = Category(
                name=cat_def["name"],
                type=cat_def["type"],
                icon=cat_def["icon"],
                color=cat_def["color"],
                user_id=user.id,
            )
            db.add(cat)
            db.flush()
            cat_map[cat_def["name"]] = cat
            counts["categories"] += 1

        acc_map: dict[str, Account] = {}
        for name, atype, lo, hi in [
            ("Main Checking", AccountType.CHECKING,     150000,  500000),
            ("Savings",       AccountType.SAVINGS,      200000, 1000000),
            ("Credit Card",   AccountType.CREDIT_CARD, -50000,   -5000),
        ]:
            acc = Account(
                name=name,
                account_type=atype,
                current_balance=rand_decimal(lo, hi),
                currency="KES",
                user_id=user.id,
            )
            db.add(acc)
            acc_map[name] = acc
            counts["accounts"] += 1
        db.flush()

        def add_tx(amount: Decimal, desc: str, tx_date: date, cat_name: str, acc_name: str) -> None:
            cat = cat_map[cat_name]
            acc = acc_map[acc_name]
            db.add(Transaction(
                amount=amount,
                description=desc,
                transaction_date=tx_date,
                category_id=cat.id,
                account_id=acc.id,
                user_id=user.id,
            ))
            if cat.type == CategoryType.INCOME:
                acc.current_balance += amount
            else:
                acc.current_balance -= amount
            counts["transactions"] += 1

        add_tx(rand_decimal(80000, 120000), "Monthly salary", random_date(prev_start, prev_end), "Salary", "Main Checking")
        add_tx(rand_decimal(80000, 120000), "Monthly salary", random_date(first_of_month, today), "Salary", "Main Checking")

        for _ in range(random.randint(2, 3)):
            acc_name = random.choice(["Main Checking", "Credit Card"])
            add_tx(rand_decimal(500, 3000), "Grocery shopping", random_date(last_30, today), "Groceries", acc_name)

        for _ in range(random.randint(1, 2)):
            acc_name = random.choice(["Main Checking", "Credit Card"])
            add_tx(rand_decimal(200, 1500), "Transport", random_date(last_30, today), "Transport", acc_name)

        acc_name = random.choice(["Main Checking", "Credit Card"])
        add_tx(rand_decimal(300, 2000), "Entertainment", random_date(last_30, today), "Entertainment", acc_name)

        add_tx(rand_decimal(2000, 8000), "Utilities bill", random_date(last_30, today), "Utilities", "Main Checking")

        for cat_name, lo, hi in [
            ("Groceries",     8000,  15000),
            ("Entertainment", 3000,   7000),
            ("Transport",     4000,  10000),
        ]:
            db.add(Budget(
                amount=rand_decimal(lo, hi),
                period=BudgetPeriod.MONTHLY,
                start_date=first_of_month,
                category_id=cat_map[cat_name].id,
                user_id=user.id,
            ))
            counts["budgets"] += 1

        # Employees — 2 per user, no transactions seeded (test Mark Paid flow)
        for tmpl in EMPLOYEE_TEMPLATES:
            start_date = months_ago(tmpl["start_date_offset_months"], today)
            bank = _BANKS[(user_idx + EMPLOYEE_TEMPLATES.index(tmpl)) % len(_BANKS)]
            emp = Employee(
                user_id=user.id,
                first_name=tmpl["first_name"],
                last_name=tmpl["last_name"],
                employment_type=tmpl["employment_type"],
                pay_amount=tmpl["pay_amount"],
                pay_frequency=tmpl["pay_frequency"],
                pay_day_config=tmpl["pay_day_config"],
                start_date=start_date,
                position=tmpl["position"],
                kra_pin=tmpl["kra_pin"],
                national_id=tmpl["national_id"],
                nhif_number=tmpl["nhif_number"],
                nssf_number=tmpl["nssf_number"],
                bank_name=bank,
                bank_account_number=tmpl["bank_account_number"],
                default_account_id=acc_map["Main Checking"].id,
                default_category_id=cat_map["Payroll"].id,
                last_paid_date=None,
                is_active=True,
            )
            db.add(emp)
            counts["employees"] += 1

        # Recurring templates — 2 per user, both monthly, no last_generated_date so they're due
        from app.models.category import CategoryType as _CT
        from app.models.enums import RecurringFrequency
        for tmpl_def in [
            {
                "description": "Rent",
                "amount": Decimal("25000.00"),
                "transaction_type": _CT.EXPENSE,
                "category": "Housing",
                "frequency": RecurringFrequency.monthly,
                "day_config": {"day": 1},
                "start_date_offset_months": 6,
            },
            {
                "description": "Netflix subscription",
                "amount": Decimal("1100.00"),
                "transaction_type": _CT.EXPENSE,
                "category": "Entertainment",
                "frequency": RecurringFrequency.monthly,
                "day_config": {"day": 15},
                "start_date_offset_months": 3,
            },
        ]:
            rt = RecurringTransaction(
                user_id=user.id,
                description=tmpl_def["description"],
                amount=tmpl_def["amount"],
                transaction_type=tmpl_def["transaction_type"],
                category_id=cat_map[tmpl_def["category"]].id,
                account_id=acc_map["Main Checking"].id,
                frequency=tmpl_def["frequency"],
                day_config=tmpl_def["day_config"],
                start_date=months_ago(tmpl_def["start_date_offset_months"], today),
                is_active=True,
                occurrences_count=0,
                last_generated_date=None,
            )
            db.add(rt)
            counts["recurring_transactions"] += 1

        # Transfers — 2 per user from Main Checking → Savings
        for days_ago, amount, desc in [
            (30, Decimal("5000.00"), "Monthly savings transfer"),
            (15, Decimal("10000.00"), "Extra savings"),
        ]:
            from_acc = acc_map["Main Checking"]
            to_acc = acc_map["Savings"]
            transfer = Transfer(
                user_id=user.id,
                from_account_id=from_acc.id,
                to_account_id=to_acc.id,
                amount=amount,
                transfer_date=today - timedelta(days=days_ago),
                description=desc,
            )
            db.add(transfer)
            from_acc.current_balance -= amount
            to_acc.current_balance += amount
            counts["transfers"] += 1

    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the database with test data.")
    parser.add_argument("--reset", action="store_true",
                        help="Wipe all existing data before seeding.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if db.query(User).first() and not args.reset:
            print("Database already contains users. Run with --reset to wipe and reseed.")
            return

        if args.reset:
            wipe(db)

        counts = seed(db)

        print("Seeded:")
        print(f"  {counts['users']} users")
        print(f"  {counts['categories']} categories")
        print(f"  {counts['accounts']} accounts")
        print(f"  ~{counts['transactions']} transactions  (exact count varies)")
        print(f"  {counts['budgets']} budgets")
        print(f"  {counts['employees']} employees")
        print(f"  {counts['recurring_transactions']} recurring transactions")
        print(f"  {counts['transfers']} transfers")
        print()
        print("Sign in with any of:")
        for u in USERS:
            print(f"  {u['email']} / {PASSWORD}")

    except Exception as exc:
        db.rollback()
        print(f"Seeding failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
