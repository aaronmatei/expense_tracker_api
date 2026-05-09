from datetime import date
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models import Category, Transaction
from app.models.category import CategoryType
from app.schemas.transaction import TransactionCreate, TransactionUpdate


def list_transactions(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    category_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Transaction]:
    stmt = select(Transaction).where(Transaction.user_id == user_id)

    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if start_date is not None:
        stmt = stmt.where(Transaction.transaction_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Transaction.transaction_date <= end_date)

    stmt = (
        stmt.order_by(Transaction.transaction_date.desc(),
                      Transaction.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(stmt))


def get_transaction(
    db: Session, transaction_id: int, user_id: int
) -> Transaction | None:
    return db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )


def create_transaction(
    db: Session, transaction_in: TransactionCreate, user_id: int
) -> Transaction:
    transaction = Transaction(**transaction_in.model_dump(), user_id=user_id)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def update_transaction(
    db: Session,
    transaction: Transaction,
    transaction_in: TransactionUpdate,
) -> Transaction:
    update_data = transaction_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transaction, field, value)
    db.commit()
    db.refresh(transaction)
    return transaction


def delete_transaction(db: Session, transaction: Transaction) -> None:
    db.delete(transaction)
    db.commit()


def get_summary(
    db: Session, user_id: int, start_date: date, end_date: date
) -> dict:
    """Overall income/expense/net totals for a user in a date range."""
    income_stmt = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Category.type == CategoryType.INCOME,
        )
    )
    expense_stmt = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
            Category.type == CategoryType.EXPENSE,
        )
    )
    count_stmt = select(func.count(Transaction.id)).where(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date,
    )

    total_income = Decimal(db.scalar(income_stmt) or 0)
    total_expenses = Decimal(db.scalar(expense_stmt) or 0)
    transaction_count = db.scalar(count_stmt) or 0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net": total_income - total_expenses,
        "transaction_count": transaction_count,
    }


def get_summary_by_category(
    db: Session, user_id: int, start_date: date, end_date: date
) -> list[dict]:
    """Per-category totals — what powers the pie chart."""
    stmt = (
        select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            Category.type.label("type"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .group_by(Category.id, Category.name, Category.type)
        .order_by(func.sum(Transaction.amount).desc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            "category_id": row.category_id,
            "category_name": row.category_name,
            "type": row.type,
            "total": Decimal(row.total),
            "transaction_count": row.transaction_count,
        }
        for row in rows
    ]


def get_summary_by_month(
    db: Session, user_id: int, year: int
) -> list[dict]:
    """Monthly income vs expense totals for a given year — what powers the trend chart."""
    stmt = (
        select(
            extract("month", Transaction.transaction_date).label("month"),
            Category.type.label("type"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            extract("year", Transaction.transaction_date) == year,
        )
        .group_by(extract("month", Transaction.transaction_date), Category.type)
    )
    rows = db.execute(stmt).all()

    # Reshape so each month has both income and expenses on one object.
    by_month: dict[int, dict] = {}
    for row in rows:
        m = int(row.month)
        bucket = by_month.setdefault(
            m,
            {"year": year, "month": m, "income": Decimal(
                0), "expenses": Decimal(0)},
        )
        if row.type == CategoryType.INCOME:
            bucket["income"] = Decimal(row.total)
        else:
            bucket["expenses"] = Decimal(row.total)

    return sorted(by_month.values(), key=lambda b: b["month"])
