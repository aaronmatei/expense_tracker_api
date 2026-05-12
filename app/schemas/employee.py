from datetime import date, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.enums import EmploymentType, Gender, PayFrequency
from app.schemas.transaction import TransactionPublic

_WEEKDAYS = ["monday", "tuesday", "wednesday",
             "thursday", "friday", "saturday", "sunday"]


class EmployeeBase(BaseModel):
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    date_of_birth: date | None = None
    national_id: str | None = Field(default=None, max_length=50)
    gender: Gender | None = None

    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)

    position: str | None = Field(default=None, max_length=100)
    employment_type: EmploymentType = EmploymentType.permanent
    start_date: date
    is_active: bool = True
    notes: str | None = None

    kra_pin: str | None = Field(default=None, max_length=20)
    nhif_number: str | None = Field(default=None, max_length=20)
    nssf_number: str | None = Field(default=None, max_length=20)

    bank_name: str | None = Field(default=None, max_length=100)
    bank_account_number: str | None = Field(default=None, max_length=50)
    bank_branch: str | None = Field(default=None, max_length=100)

    pay_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    pay_frequency: PayFrequency = PayFrequency.semi_monthly
    pay_day_config: dict
    default_account_id: int | None = None
    default_category_id: int | None = None

    @model_validator(mode="after")
    def validate_pay_day_config(self) -> "EmployeeBase":
        freq = self.pay_frequency
        config = self.pay_day_config

        if freq == PayFrequency.monthly:
            if not isinstance(config, dict) or "day" not in config:
                raise ValueError("monthly pay_day_config must be {'day': int}")
            day = config["day"]
            if not isinstance(day, int) or not 1 <= day <= 31:
                raise ValueError("monthly day must be an integer 1–31")

        elif freq == PayFrequency.semi_monthly:
            if not isinstance(config, dict) or "days" not in config:
                raise ValueError(
                    "semi_monthly pay_day_config must be {'days': [v1, v2]}")
            days = config["days"]
            if not isinstance(days, list) or len(days) != 2:
                raise ValueError(
                    "semi_monthly days must be a list of exactly 2 values")
            for v in days:
                if v != "last" and (not isinstance(v, int) or not 1 <= v <= 31):
                    raise ValueError(
                        "semi_monthly days must each be an int 1–31 or the string 'last'"
                    )

        elif freq == PayFrequency.weekly:
            if not isinstance(config, dict) or "weekday" not in config:
                raise ValueError(
                    "weekly pay_day_config must be {'weekday': '<weekday>'}")
            if config["weekday"] not in _WEEKDAYS:
                raise ValueError(f"weekly weekday must be one of {_WEEKDAYS}")

        elif freq == PayFrequency.biweekly:
            if not isinstance(config, dict) or "weekday" not in config or "anchor_date" not in config:
                raise ValueError(
                    "biweekly pay_day_config must be {'weekday': '<weekday>', 'anchor_date': 'YYYY-MM-DD'}"
                )
            if config["weekday"] not in _WEEKDAYS:
                raise ValueError(
                    f"biweekly weekday must be one of {_WEEKDAYS}")
            try:
                date.fromisoformat(config["anchor_date"])
            except (ValueError, TypeError):
                raise ValueError(
                    "biweekly anchor_date must be a valid YYYY-MM-DD date string")

        return self


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    national_id: str | None = Field(default=None, max_length=50)
    gender: Gender | None = None

    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)

    position: str | None = Field(default=None, max_length=100)
    employment_type: EmploymentType | None = None
    start_date: date | None = None
    is_active: bool | None = None
    notes: str | None = None

    kra_pin: str | None = Field(default=None, max_length=20)
    nhif_number: str | None = Field(default=None, max_length=20)
    nssf_number: str | None = Field(default=None, max_length=20)

    bank_name: str | None = Field(default=None, max_length=100)
    bank_account_number: str | None = Field(default=None, max_length=50)
    bank_branch: str | None = Field(default=None, max_length=100)

    pay_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2)
    pay_frequency: PayFrequency | None = None
    pay_day_config: dict | None = None
    default_account_id: int | None = None
    default_category_id: int | None = None


class EmployeeRead(EmployeeBase):
    id: int
    user_id: int
    last_paid_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @computed_field
    @property
    def next_pay_date(self) -> date | None:
        from app.services.payroll import get_next_pay_date
        try:
            after = (
                self.last_paid_date
                if self.last_paid_date is not None
                else self.start_date - timedelta(days=1)
            )
            return get_next_pay_date(
                after, self.pay_frequency, self.pay_day_config, self.start_date
            )
        except Exception:
            return None

    @computed_field
    @property
    def is_due_for_pay(self) -> bool:
        from app.services.payroll import is_due_for_pay
        return is_due_for_pay(self, date.today())


# ---------------------------------------------------------------------------
# Payroll request / response schemas
# ---------------------------------------------------------------------------

class PayEmployeeRequest(BaseModel):
    amount: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2)
    transaction_date: date | None = None
    account_id: int | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=500)


class BulkPayEmployeeItem(BaseModel):
    employee_id: int
    amount: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2)
    transaction_date: date | None = None
    account_id: int | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=500)


class BulkPayRequest(BaseModel):
    payments: list[BulkPayEmployeeItem]


class BulkPayError(BaseModel):
    employee_id: int
    error: str


class BulkPayResponse(BaseModel):
    successful: list[TransactionPublic]
    failed: list[BulkPayError]
