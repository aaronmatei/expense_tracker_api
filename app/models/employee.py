from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import EmploymentType, Gender, PayFrequency

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category
    from app.models.transaction import Transaction
    from app.models.user import User


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Identity
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender), nullable=True)

    # Contact
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Employment
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[EmploymentType] = mapped_column(
        Enum(EmploymentType), default=EmploymentType.permanent
    )
    start_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Statutory (Kenya)
    kra_pin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nhif_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nssf_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Banking
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_account_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bank_branch: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Payroll
    pay_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    pay_frequency: Mapped[PayFrequency] = mapped_column(
        Enum(PayFrequency), default=PayFrequency.semi_monthly
    )
    pay_day_config: Mapped[dict] = mapped_column(JSON)
    default_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    default_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"), nullable=True
    )
    last_paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="employees")
    default_account: Mapped["Account | None"] = relationship(
        foreign_keys=[default_account_id]
    )
    default_category: Mapped["Category | None"] = relationship(
        foreign_keys=[default_category_id]
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="employee"
    )
