from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.schemas.account import AccountCreate, AccountTypeBreakdown, AccountsSummary, AccountUpdate


def list_accounts(db: Session, user_id: int) -> list[Account]:
    return list(
        db.scalars(
            select(Account)
            .where(Account.user_id == user_id)
            .order_by(Account.name)
        )
    )


def get_account(db: Session, account_id: int, user_id: int) -> Account | None:
    return db.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )


def create_account(db: Session, account_in: AccountCreate, user_id: int) -> Account:
    account = Account(**account_in.model_dump(), user_id=user_id)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def update_account(db: Session, account: Account, account_in: AccountUpdate) -> Account:
    for field, value in account_in.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


def delete_account(db: Session, account: Account) -> None:
    db.delete(account)
    db.commit()


def get_accounts_summary(db: Session, user_id: int) -> AccountsSummary:
    total_balance_stmt = select(
        func.coalesce(func.sum(Account.current_balance), 0)
    ).where(Account.user_id == user_id, Account.include_in_total == True)

    total_balance = Decimal(db.scalar(total_balance_stmt) or 0)

    breakdown_stmt = (
        select(
            Account.account_type,
            func.coalesce(func.sum(Account.current_balance), 0).label("total"),
            func.count(Account.id).label("count"),
        )
        .where(Account.user_id == user_id)
        .group_by(Account.account_type)
        .order_by(Account.account_type)
    )
    rows = db.execute(breakdown_stmt).all()

    breakdown = [
        AccountTypeBreakdown(
            account_type=row.account_type,
            total=Decimal(row.total),
            count=row.count,
        )
        for row in rows
    ]

    return AccountsSummary(
        total_balance=total_balance,
        account_count=sum(b.count for b in breakdown),
        breakdown=breakdown,
    )
