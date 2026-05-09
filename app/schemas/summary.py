from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.category import CategoryType


class TransactionSummary(BaseModel):
    start_date: date
    end_date: date
    total_income: Decimal
    total_expenses: Decimal
    net: Decimal
    transaction_count: int


class CategorySummary(BaseModel):
    category_id: int
    category_name: str
    type: CategoryType
    total: Decimal
    transaction_count: int


class MonthSummary(BaseModel):
    year: int
    month: int  # 1-12
    income: Decimal
    expenses: Decimal
