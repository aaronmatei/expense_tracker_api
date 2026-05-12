from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.crud.transaction import STRICT_BALANCE_TYPES
from app.models.account import Account
from app.models.transfer import Transfer
from app.schemas.transfer import TransferCreate, TransferUpdate


def _apply_transfer_to_balances(
    from_account: Account, to_account: Account, amount: Decimal
) -> None:
    """Debit from_account, credit to_account. Raises 400 if from_account would go negative."""
    new_from = from_account.current_balance - amount
    if from_account.account_type in STRICT_BALANCE_TYPES and new_from < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Transfer would push {from_account.name} below zero",
        )
    from_account.current_balance = new_from
    to_account.current_balance = to_account.current_balance + amount


def _reverse_transfer_from_balances(
    from_account: Account, to_account: Account, amount: Decimal
) -> None:
    """Undo the effect of a transfer."""
    from_account.current_balance = from_account.current_balance + amount
    to_account.current_balance = to_account.current_balance - amount


def _load_transfer(db: Session, transfer_id: int, user_id: int) -> Transfer | None:
    return db.scalar(
        select(Transfer)
        .options(joinedload(Transfer.from_account), joinedload(Transfer.to_account))
        .where(Transfer.id == transfer_id, Transfer.user_id == user_id)
    )


def get_transfer_for_user(db: Session, transfer_id: int, user_id: int) -> Transfer | None:
    return _load_transfer(db, transfer_id, user_id)


def get_transfers_for_user(
    db: Session,
    user_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    account_id: int | None = None,
) -> list[Transfer]:
    stmt = (
        select(Transfer)
        .options(joinedload(Transfer.from_account), joinedload(Transfer.to_account))
        .where(Transfer.user_id == user_id)
    )
    if start_date is not None:
        stmt = stmt.where(Transfer.transfer_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Transfer.transfer_date <= end_date)
    if account_id is not None:
        stmt = stmt.where(
            or_(Transfer.from_account_id == account_id, Transfer.to_account_id == account_id)
        )
    stmt = stmt.order_by(Transfer.transfer_date.desc(), Transfer.id.desc())
    return list(db.scalars(stmt))


def create_transfer(db: Session, payload: TransferCreate, user_id: int) -> Transfer:
    from_account = db.scalar(
        select(Account).where(Account.id == payload.from_account_id, Account.user_id == user_id)
    )
    if from_account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    to_account = db.scalar(
        select(Account).where(Account.id == payload.to_account_id, Account.user_id == user_id)
    )
    if to_account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if from_account.currency != to_account.currency:
        raise HTTPException(
            status_code=400,
            detail="Cannot transfer between accounts of different currencies",
        )

    _apply_transfer_to_balances(from_account, to_account, payload.amount)

    transfer = Transfer(
        user_id=user_id,
        from_account_id=payload.from_account_id,
        to_account_id=payload.to_account_id,
        amount=payload.amount,
        transfer_date=payload.transfer_date,
        description=payload.description,
    )
    db.add(transfer)
    db.commit()

    return _load_transfer(db, transfer.id, user_id)  # type: ignore[return-value]


def update_transfer(
    db: Session, transfer: Transfer, payload: TransferUpdate, user_id: int
) -> Transfer:
    update_data = payload.model_dump(exclude_unset=True)

    # Validate effective account IDs won't be equal after the update
    effective_from_id = update_data.get("from_account_id", transfer.from_account_id)
    effective_to_id = update_data.get("to_account_id", transfer.to_account_id)
    if effective_from_id == effective_to_id:
        raise HTTPException(status_code=422, detail="From and to accounts must be different")

    # Reverse old effect using old account IDs (identity map ensures correct objects)
    old_from = db.get(Account, transfer.from_account_id)
    old_to = db.get(Account, transfer.to_account_id)
    _reverse_transfer_from_balances(old_from, old_to, transfer.amount)

    # Apply field updates
    for field, value in update_data.items():
        setattr(transfer, field, value)

    # Fetch (possibly new) accounts with ownership check
    new_from = db.scalar(
        select(Account).where(Account.id == transfer.from_account_id, Account.user_id == user_id)
    )
    if new_from is None:
        raise HTTPException(status_code=404, detail="Account not found")

    new_to = db.scalar(
        select(Account).where(Account.id == transfer.to_account_id, Account.user_id == user_id)
    )
    if new_to is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if new_from.currency != new_to.currency:
        raise HTTPException(
            status_code=400,
            detail="Cannot transfer between accounts of different currencies",
        )

    _apply_transfer_to_balances(new_from, new_to, transfer.amount)
    db.commit()

    return _load_transfer(db, transfer.id, user_id)  # type: ignore[return-value]


def delete_transfer(db: Session, transfer: Transfer) -> None:
    from_account = db.get(Account, transfer.from_account_id)
    to_account = db.get(Account, transfer.to_account_id)
    _reverse_transfer_from_balances(from_account, to_account, transfer.amount)
    db.delete(transfer)
    db.commit()
