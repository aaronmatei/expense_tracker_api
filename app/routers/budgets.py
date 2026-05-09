from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import budget as budget_crud
from app.crud import category as category_crud
from app.database import get_db
from app.models import User
from app.schemas.budget import (
    BudgetCreate,
    BudgetPublic,
    BudgetUpdate,
    BudgetWithSpending,
)

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _verify_category_ownership(db: Session, category_id: int, user_id: int) -> None:
    if category_crud.get_category(db, category_id, user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found or does not belong to you",
        )


@router.get("/summary", response_model=list[BudgetWithSpending])
def get_budget_summary(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return budget_crud.get_budget_summary(db, current_user.id, year, month)


@router.get("", response_model=list[BudgetPublic])
def list_budgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return budget_crud.list_budgets(db, current_user.id)


@router.post("", response_model=BudgetPublic, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget_in: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _verify_category_ownership(db, budget_in.category_id, current_user.id)
    if budget_crud.get_budget_for_category(db, current_user.id, budget_in.category_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A budget already exists for this category",
        )
    return budget_crud.create_budget(db, budget_in, current_user.id)


@router.get("/{budget_id}", response_model=BudgetPublic)
def get_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = budget_crud.get_budget(db, budget_id, current_user.id)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


@router.patch("/{budget_id}", response_model=BudgetPublic)
def update_budget(
    budget_id: int,
    budget_in: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = budget_crud.get_budget(db, budget_id, current_user.id)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget_crud.update_budget(db, budget, budget_in)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    budget = budget_crud.get_budget(db, budget_id, current_user.id)
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    budget_crud.delete_budget(db, budget)
