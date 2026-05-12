from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class TransferBase(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal
    transfer_date: date
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v

    @model_validator(mode="after")
    def accounts_must_differ(self) -> "TransferBase":
        if self.from_account_id == self.to_account_id:
            raise ValueError("From and to accounts must be different")
        return self


class TransferCreate(TransferBase):
    pass


class TransferUpdate(BaseModel):
    from_account_id: int | None = None
    to_account_id: int | None = None
    amount: Decimal | None = None
    transfer_date: date | None = None
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v


class TransferRead(TransferBase):
    id: int
    user_id: int
    from_account_name: str
    to_account_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
