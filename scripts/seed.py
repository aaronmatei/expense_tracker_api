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
]

PASSWORD = "password123"


def rand_decimal(lo: float, hi: float) -> Decimal:
    return Decimal(str(random.uniform(lo, hi))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, max(0, (end - start).days)))


def wipe(db) -> None:
    db.query(Transaction).delete()
    db.query(Budget).delete()
    db.query(Category).delete()
    db.query(Account).delete()
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
    counts = {"users": 0, "categories": 0, "accounts": 0, "transactions": 0, "budgets": 0}

    for user_data in USERS:
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
            ("Main Checking", AccountType.CHECKING,     1500,  5000),
            ("Savings",       AccountType.SAVINGS,      3000, 15000),
            ("Credit Card",   AccountType.CREDIT_CARD, -1200,  -200),
        ]:
            acc = Account(
                name=name,
                account_type=atype,
                current_balance=rand_decimal(lo, hi),
                currency="USD",
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

        add_tx(rand_decimal(4000, 6000), "Monthly salary", random_date(prev_start, prev_end), "Salary", "Main Checking")
        add_tx(rand_decimal(4000, 6000), "Monthly salary", random_date(first_of_month, today), "Salary", "Main Checking")

        for _ in range(random.randint(2, 3)):
            acc_name = random.choice(["Main Checking", "Credit Card"])
            add_tx(rand_decimal(30, 200), "Grocery shopping", random_date(last_30, today), "Groceries", acc_name)

        for _ in range(random.randint(1, 2)):
            acc_name = random.choice(["Main Checking", "Credit Card"])
            add_tx(rand_decimal(10, 80), "Transport", random_date(last_30, today), "Transport", acc_name)

        acc_name = random.choice(["Main Checking", "Credit Card"])
        add_tx(rand_decimal(15, 60), "Entertainment", random_date(last_30, today), "Entertainment", acc_name)

        add_tx(rand_decimal(80, 200), "Utilities bill", random_date(last_30, today), "Utilities", "Main Checking")

        for cat_name, lo, hi in [
            ("Groceries",     400, 700),
            ("Entertainment", 100, 200),
            ("Transport",     150, 300),
        ]:
            db.add(Budget(
                amount=rand_decimal(lo, hi),
                period=BudgetPeriod.MONTHLY,
                start_date=first_of_month,
                category_id=cat_map[cat_name].id,
                user_id=user.id,
            ))
            counts["budgets"] += 1

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
