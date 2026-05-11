from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)
    transaction_date: date
    category_id: int
    account_id: int


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    description: str | None = Field(default=None, max_length=500)
    transaction_date: date | None = None
    category_id: int | None = None
    account_id: int | None = None


class TransactionPublic(TransactionBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
