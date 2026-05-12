from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.category import CategoryType
from app.models.enums import RecurringFrequency

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category
    from app.models.transaction import Transaction
    from app.models.user import User


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    transaction_type: Mapped[CategoryType] = mapped_column(Enum(CategoryType))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    frequency: Mapped[RecurringFrequency] = mapped_column(Enum(RecurringFrequency))
    day_config: Mapped[dict] = mapped_column(JSON)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    max_occurrences: Mapped[int | None] = mapped_column(nullable=True)
    occurrences_count: Mapped[int] = mapped_column(default=0)
    last_generated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="recurring_transactions")
    category: Mapped["Category"] = relationship()
    account: Mapped["Account"] = relationship()
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="recurring_transaction"
    )

    @property
    def category_name(self) -> str:
        return self.category.name if self.category else ""

    @property
    def account_name(self) -> str:
        return self.account.name if self.account else ""
