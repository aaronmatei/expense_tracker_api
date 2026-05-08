from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Transaction
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
