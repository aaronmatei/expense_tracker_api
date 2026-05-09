from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.budget import Budget
    from app.models.category import Category
    from app.models.transaction import Transaction


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(
        String(20), unique=True, index=True, nullable=True)
    id_number: Mapped[str | None] = mapped_column(
        String(10), unique=True, index=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    categories: Mapped[list["Category"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]
                         ] = relationship(back_populates="owner", cascade="all, delete-orphan")
    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    accounts: Mapped[list["Account"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
