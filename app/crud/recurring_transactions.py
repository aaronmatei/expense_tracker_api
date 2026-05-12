from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.crud.transaction import _assert_balance_ok, _signed_delta
from app.models.account import Account
from app.models.category import Category
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.schemas.recurring_transaction import (
    BulkMaterializeFailure,
    BulkMaterializeRequest,
    BulkMaterializeResponse,
    MaterializeRequest,
    RecurringTransactionCreate,
    RecurringTransactionUpdate,
)


def _with_relations(stmt):
    return stmt.options(
        joinedload(RecurringTransaction.category),
        joinedload(RecurringTransaction.account),
    )


def _verify_category_owned(db: Session, category_id: int, user_id: int) -> Category:
    cat = db.scalar(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    if cat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")
    return cat


def _verify_account_owned(db: Session, account_id: int, user_id: int) -> Account:
    acc = db.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    if acc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Account not found")
    return acc


def create(
    db: Session, payload: RecurringTransactionCreate, user_id: int
) -> RecurringTransaction:
    _verify_category_owned(db, payload.category_id, user_id)
    _verify_account_owned(db, payload.account_id, user_id)
    template = RecurringTransaction(**payload.model_dump(), user_id=user_id)
    db.add(template)
    db.commit()
    return get_for_user(db, template.id, user_id)


def get_for_user(
    db: Session, recurring_transaction_id: int, user_id: int
) -> RecurringTransaction:
    template = db.scalar(
        _with_relations(
            select(RecurringTransaction).where(
                RecurringTransaction.id == recurring_transaction_id,
                RecurringTransaction.user_id == user_id,
            )
        )
    )
    if template is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Recurring transaction not found"
        )
    return template


def list_for_user(
    db: Session,
    user_id: int,
    is_active: bool | None = None,
    transaction_type=None,
) -> list[RecurringTransaction]:
    stmt = _with_relations(
        select(RecurringTransaction).where(RecurringTransaction.user_id == user_id)
    )
    if is_active is not None:
        stmt = stmt.where(RecurringTransaction.is_active == is_active)
    if transaction_type is not None:
        stmt = stmt.where(RecurringTransaction.transaction_type == transaction_type)
    stmt = stmt.order_by(RecurringTransaction.created_at.desc())
    return list(db.scalars(stmt).unique())


def update(
    db: Session,
    template: RecurringTransaction,
    payload: RecurringTransactionUpdate,
    user_id: int,
) -> RecurringTransaction:
    update_data = payload.model_dump(exclude_unset=True)
    if "category_id" in update_data:
        _verify_category_owned(db, update_data["category_id"], user_id)
    if "account_id" in update_data:
        _verify_account_owned(db, update_data["account_id"], user_id)
    for field, value in update_data.items():
        setattr(template, field, value)
    db.commit()
    return get_for_user(db, template.id, user_id)


def delete(db: Session, template: RecurringTransaction) -> None:
    db.delete(template)
    db.commit()


def _check_not_exhausted(template: RecurringTransaction) -> None:
    """Raise 400 if the template cannot produce more materializations."""
    if not template.is_active:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Recurring transaction is inactive",
        )
    if (
        template.max_occurrences is not None
        and template.occurrences_count >= template.max_occurrences
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Template has reached its maximum of {template.max_occurrences} occurrences",
        )
    if template.end_date is not None:
        from app.services.recurrence import compute_next_due_date
        if compute_next_due_date(template, date.today()) is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Template is exhausted (no future occurrences within its end date)",
            )


def _stage_materialize(
    db: Session,
    template: RecurringTransaction,
    payload: MaterializeRequest,
    user_id: int,
) -> Transaction:
    """Build and stage a materialized transaction without committing."""
    today = date.today()
    amount: Decimal = payload.amount if payload.amount is not None else template.amount
    description: str = (
        payload.description if payload.description is not None else template.description
    )
    tx_date: date = (
        payload.transaction_date if payload.transaction_date is not None else today
    )

    category = db.get(Category, template.category_id)
    account = db.get(Account, template.account_id)

    if category is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Category not found")
    if account is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Account not found")

    delta = _signed_delta(amount, category)
    _assert_balance_ok(account, delta)

    tx = Transaction(
        amount=amount,
        description=description,
        transaction_date=tx_date,
        category_id=template.category_id,
        account_id=template.account_id,
        user_id=user_id,
        recurring_transaction_id=template.id,
    )
    db.add(tx)
    account.current_balance += delta
    template.occurrences_count += 1
    template.last_generated_date = tx_date
    return tx


def materialize(
    db: Session,
    template: RecurringTransaction,
    payload: MaterializeRequest,
    user_id: int,
) -> Transaction:
    _check_not_exhausted(template)
    tx = _stage_materialize(db, template, payload, user_id)
    db.commit()
    db.refresh(tx)
    return tx


def materialize_bulk(
    db: Session, payload: BulkMaterializeRequest, user_id: int
) -> BulkMaterializeResponse:
    from fastapi import HTTPException as _HTTPException

    successful: list[Transaction] = []
    failed: list[BulkMaterializeFailure] = []

    for item in payload.items:
        savepoint = db.begin_nested()
        try:
            template = get_for_user(db, item.recurring_transaction_id, user_id)
            _check_not_exhausted(template)
            req = MaterializeRequest(
                amount=item.amount,
                transaction_date=item.transaction_date,
                description=item.description,
            )
            tx = _stage_materialize(db, template, req, user_id)
            db.flush()
            savepoint.commit()
            successful.append(tx)
        except Exception as exc:
            savepoint.rollback()
            error_msg = exc.detail if isinstance(exc, _HTTPException) else str(exc)
            failed.append(
                BulkMaterializeFailure(
                    recurring_transaction_id=item.recurring_transaction_id,
                    error=error_msg,
                )
            )

    if successful:
        db.commit()
        for tx in successful:
            db.refresh(tx)

    return BulkMaterializeResponse(successful=successful, failed=failed)


def get_due_for_user(
    db: Session, user_id: int, today: date
) -> list[RecurringTransaction]:
    from app.services.recurrence import is_template_due

    active = list_for_user(db, user_id, is_active=True)
    return [t for t in active if is_template_due(t, today)]
