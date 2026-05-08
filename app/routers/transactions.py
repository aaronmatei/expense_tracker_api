from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import category as category_crud
from app.crud import transaction as transaction_crud
from app.database import get_db
from app.models import User
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


@router.get("", response_model=list[TransactionPublic])
def list_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    category_id: int | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return transaction_crud.list_transactions(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
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
    return transaction_crud.create_transaction(db, transaction_in, current_user.id)


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
        _verify_category_ownership(
            db, transaction_in.category_id, current_user.id)
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
