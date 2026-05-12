from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.models.category import CategoryType
from app.models.enums import RecurringFrequency
from app.schemas.transaction import TransactionPublic

_WEEKDAYS = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]


class RecurringTransactionBase(BaseModel):
    description: str = Field(max_length=500)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    transaction_type: CategoryType
    category_id: int
    account_id: int
    frequency: RecurringFrequency
    day_config: dict
    start_date: date
    end_date: date | None = None
    max_occurrences: int | None = Field(default=None, gt=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_day_config(self) -> "RecurringTransactionBase":
        freq = self.frequency
        cfg = self.day_config

        if freq == RecurringFrequency.daily:
            if not isinstance(cfg, dict):
                raise ValueError("daily day_config must be an empty dict {}")

        elif freq == RecurringFrequency.weekly:
            if not isinstance(cfg, dict) or "weekday" not in cfg:
                raise ValueError("weekly day_config must be {'weekday': '<weekday>'}")
            if cfg["weekday"] not in _WEEKDAYS:
                raise ValueError(f"weekly weekday must be one of {_WEEKDAYS}")

        elif freq == RecurringFrequency.biweekly:
            if not isinstance(cfg, dict) or "weekday" not in cfg or "anchor_date" not in cfg:
                raise ValueError(
                    "biweekly day_config must be {'weekday': '...', 'anchor_date': 'YYYY-MM-DD'}"
                )
            if cfg["weekday"] not in _WEEKDAYS:
                raise ValueError(f"biweekly weekday must be one of {_WEEKDAYS}")
            try:
                date.fromisoformat(cfg["anchor_date"])
            except (ValueError, TypeError):
                raise ValueError("biweekly anchor_date must be a valid YYYY-MM-DD date string")

        elif freq == RecurringFrequency.monthly:
            if not isinstance(cfg, dict) or "day" not in cfg:
                raise ValueError("monthly day_config must be {'day': int}")
            day = cfg["day"]
            if not isinstance(day, int) or not 1 <= day <= 31:
                raise ValueError("monthly day must be an integer 1–31")

        elif freq == RecurringFrequency.quarterly:
            if not isinstance(cfg, dict) or "month_offset" not in cfg or "day" not in cfg:
                raise ValueError(
                    "quarterly day_config must be {'month_offset': 0–2, 'day': 1–31}"
                )
            month_offset = cfg["month_offset"]
            day = cfg["day"]
            if not isinstance(month_offset, int) or not 0 <= month_offset <= 2:
                raise ValueError("quarterly month_offset must be 0, 1, or 2")
            if not isinstance(day, int) or not 1 <= day <= 31:
                raise ValueError("quarterly day must be an integer 1–31")

        elif freq == RecurringFrequency.yearly:
            if not isinstance(cfg, dict) or "month" not in cfg or "day" not in cfg:
                raise ValueError("yearly day_config must be {'month': 1–12, 'day': 1–31}")
            month = cfg["month"]
            day = cfg["day"]
            if not isinstance(month, int) or not 1 <= month <= 12:
                raise ValueError("yearly month must be an integer 1–12")
            if not isinstance(day, int) or not 1 <= day <= 31:
                raise ValueError("yearly day must be an integer 1–31")

        return self


class RecurringTransactionCreate(RecurringTransactionBase):
    pass


class RecurringTransactionUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    transaction_type: CategoryType | None = None
    category_id: int | None = None
    account_id: int | None = None
    frequency: RecurringFrequency | None = None
    day_config: dict | None = None
    start_date: date | None = None
    end_date: date | None = None
    max_occurrences: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class RecurringTransactionRead(RecurringTransactionBase):
    id: int
    user_id: int
    occurrences_count: int
    last_generated_date: date | None
    created_at: datetime
    category_name: str
    account_name: str

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def next_due_date(self) -> date | None:
        from app.services.recurrence import compute_next_due_date
        try:
            return compute_next_due_date(self, date.today())
        except Exception:
            return None

    @computed_field
    @property
    def is_due(self) -> bool:
        from app.services.recurrence import is_template_due
        try:
            return is_template_due(self, date.today())
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Materialize request / response schemas
# ---------------------------------------------------------------------------

class MaterializeRequest(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    transaction_date: date | None = None
    description: str | None = Field(default=None, max_length=500)


class BulkMaterializeItem(BaseModel):
    recurring_transaction_id: int
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    transaction_date: date | None = None
    description: str | None = Field(default=None, max_length=500)


class BulkMaterializeRequest(BaseModel):
    items: list[BulkMaterializeItem]


class BulkMaterializeFailure(BaseModel):
    recurring_transaction_id: int
    error: str


class BulkMaterializeResponse(BaseModel):
    successful: list[TransactionPublic]
    failed: list[BulkMaterializeFailure]
