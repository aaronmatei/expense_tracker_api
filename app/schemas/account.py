from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.account import AccountType


class AccountBase(BaseModel):
    name: str = Field(max_length=100)
    account_type: AccountType
    institution: str | None = Field(default=None, max_length=100)
    currency: str = Field(default="USD", max_length=3)
    description: str | None = Field(default=None, max_length=255)
    include_in_total: bool = True


class AccountCreate(AccountBase):
    current_balance: Decimal = Field(
        default=Decimal("0"), max_digits=14, decimal_places=2
    )


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    account_type: AccountType | None = None
    institution: str | None = Field(default=None, max_length=100)
    current_balance: Decimal | None = Field(
        default=None, max_digits=14, decimal_places=2
    )
    currency: str | None = Field(default=None, max_length=3)
    description: str | None = Field(default=None, max_length=255)
    include_in_total: bool | None = None


class AccountPublic(AccountBase):
    id: int
    current_balance: Decimal
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountTypeBreakdown(BaseModel):
    account_type: AccountType
    total: Decimal
    count: int


class AccountsSummary(BaseModel):
    total_balance: Decimal
    account_count: int
    breakdown: list[AccountTypeBreakdown]
