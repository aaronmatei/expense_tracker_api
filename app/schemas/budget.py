from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.budget import BudgetPeriod


class BudgetBase(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    start_date: date
    notify_at_80_percent: bool = True
    notify_when_exceeded: bool = True
    category_id: int


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    amount: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2)
    period: BudgetPeriod | None = None
    start_date: date | None = None
    notify_at_80_percent: bool | None = None
    notify_when_exceeded: bool | None = None


class BudgetPublic(BudgetBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetWithSpending(BudgetPublic):
    category_name: str
    spent: Decimal
    remaining: Decimal
    percentage_used: float
    is_over_budget: bool
