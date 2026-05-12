from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import account as account_crud
from app.crud import category as category_crud
from app.crud import employees as employee_crud
from app.crud import transaction as transaction_crud
from app.database import get_db
from app.models import User

from app.schemas.summary import (
    CategorySummary,
    MonthSummary,
    TransactionSummary,
)
from app.schemas.transaction import (
    TransactionCreate,
    TransactionPublic,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _verify_category_ownership(db: Session, category_id: int, user_id: int) -> None:
    """Ensure the category exists AND belongs to the current user."""
    if category_crud.get_category(db, category_id, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or does not belong to you",
        )


def _verify_account_ownership(db: Session, account_id: int, user_id: int) -> None:
    """Ensure the account exists AND belongs to the current user."""
    if account_crud.get_account(db, account_id, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account not found or does not belong to you",
        )


def _verify_employee_ownership(db: Session, employee_id: int, user_id: int) -> None:
    """Ensure the employee exists AND belongs to the current user."""
    from sqlalchemy import select
    from app.models.employee import Employee
    emp = db.scalar(
        select(Employee).where(
            Employee.id == employee_id, Employee.user_id == user_id
        )
    )
    if emp is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee not found or does not belong to you",
        )


@router.get("", response_model=list[TransactionPublic])
def list_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    category_ids: list[int] | None = Query(default=None),
    account_id: int | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transaction_crud.list_transactions(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        category_ids=category_ids,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id,
    )


@router.post(
    "",
    response_model=TransactionPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    transaction_in: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_category_ownership(db, transaction_in.category_id, current_user.id)
    _verify_account_ownership(db, transaction_in.account_id, current_user.id)
    if transaction_in.employee_id is not None:
        _verify_employee_ownership(db, transaction_in.employee_id, current_user.id)
    return transaction_crud.create_transaction(db, transaction_in, current_user.id)


@router.get("/summary", response_model=TransactionSummary)
def get_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )
    return transaction_crud.get_summary(
        db, current_user.id, start_date, end_date
    )


@router.get("/summary/by-category", response_model=list[CategorySummary])
def get_summary_by_category(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )
    return transaction_crud.get_summary_by_category(
        db, current_user.id, start_date, end_date
    )


@router.get("/summary/by-month", response_model=list[MonthSummary])
def get_summary_by_month(
    year: int = Query(..., ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transaction_crud.get_summary_by_month(db, current_user.id, year)


@router.get("/{transaction_id}", response_model=TransactionPublic)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = transaction_crud.get_transaction(
        db, transaction_id, current_user.id
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionPublic)
def update_transaction(
    transaction_id: int,
    transaction_in: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = transaction_crud.get_transaction(
        db, transaction_id, current_user.id
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    if transaction_in.category_id is not None:
        _verify_category_ownership(db, transaction_in.category_id, current_user.id)
    if transaction_in.account_id is not None:
        _verify_account_ownership(db, transaction_in.account_id, current_user.id)
    if transaction_in.employee_id is not None:
        _verify_employee_ownership(db, transaction_in.employee_id, current_user.id)
    return transaction_crud.update_transaction(db, transaction, transaction_in)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transaction = transaction_crud.get_transaction(
        db, transaction_id, current_user.id
    )
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    transaction_crud.delete_transaction(db, transaction)
