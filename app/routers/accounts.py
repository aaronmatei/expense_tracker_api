from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import account as account_crud
from app.database import get_db
from app.models import User
from app.schemas.account import (
    AccountCreate,
    AccountPublic,
    AccountsSummary,
    AccountUpdate,
)

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/summary", response_model=AccountsSummary)
def get_accounts_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return account_crud.get_accounts_summary(db, current_user.id)


@router.get("", response_model=list[AccountPublic])
def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return account_crud.list_accounts(db, current_user.id)


@router.post("", response_model=AccountPublic, status_code=status.HTTP_201_CREATED)
def create_account(
    account_in: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return account_crud.create_account(db, account_in, current_user.id)


@router.get("/{account_id}", response_model=AccountPublic)
def get_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = account_crud.get_account(db, account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


@router.patch("/{account_id}", response_model=AccountPublic)
def update_account(
    account_id: int,
    account_in: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = account_crud.get_account(db, account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account_crud.update_account(db, account, account_in)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = account_crud.get_account(db, account_id, current_user.id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    account_crud.delete_account(db, account)
