import calendar
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.transaction import Transaction
from app.schemas.budget import BudgetCreate, BudgetUpdate


def list_budgets(db: Session, user_id: int) -> list[Budget]:
    return list(db.scalars(select(Budget).where(Budget.user_id == user_id)))


def get_budget(db: Session, budget_id: int, user_id: int) -> Budget | None:
    return db.scalar(
        select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
    )


def get_budget_for_category(
    db: Session, user_id: int, category_id: int
) -> Budget | None:
    return db.scalar(
        select(Budget).where(
            Budget.user_id == user_id, Budget.category_id == category_id
        )
    )


def create_budget(db: Session, budget_in: BudgetCreate, user_id: int) -> Budget:
    budget = Budget(**budget_in.model_dump(), user_id=user_id)
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def update_budget(db: Session, budget: Budget, budget_in: BudgetUpdate) -> Budget:
    for field, value in budget_in.model_dump(exclude_unset=True).items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    return budget


def delete_budget(db: Session, budget: Budget) -> None:
    db.delete(budget)
    db.commit()


def get_budget_summary(
    db: Session, user_id: int, year: int, month: int
) -> list[dict]:
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    budgets = list_budgets(db, user_id)
    result = []

    for budget in budgets:
        spent_stmt = select(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).where(
            Transaction.user_id == user_id,
            Transaction.category_id == budget.category_id,
            Transaction.transaction_date >= first_day,
            Transaction.transaction_date <= last_day,
        )
        spent = Decimal(db.scalar(spent_stmt) or 0)
        remaining = budget.amount - spent
        percentage_used = float(spent / budget.amount * 100) if budget.amount else 0.0

        result.append(
            {
                "id": budget.id,
                "amount": budget.amount,
                "period": budget.period,
                "start_date": budget.start_date,
                "notify_at_80_percent": budget.notify_at_80_percent,
                "notify_when_exceeded": budget.notify_when_exceeded,
                "category_id": budget.category_id,
                "user_id": budget.user_id,
                "created_at": budget.created_at,
                "updated_at": budget.updated_at,
                "category_name": budget.category.name,
                "spent": spent,
                "remaining": remaining,
                "percentage_used": percentage_used,
                "is_over_budget": spent > budget.amount,
            }
        )

    return result
