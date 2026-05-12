import math
import calendar
from datetime import date, timedelta
from typing import TYPE_CHECKING

from app.models.enums import RecurringFrequency
from app.services.payroll import apply_weekend_adjustment

if TYPE_CHECKING:
    from app.models.recurring_transaction import RecurringTransaction

_WEEKDAYS = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]


def _first_occurrence_on_or_after(
    start_date: date, frequency: RecurringFrequency, config: dict
) -> date:
    """First occurrence of this cycle on or after start_date (before weekend adjustment)."""
    if frequency == RecurringFrequency.daily:
        return start_date

    elif frequency == RecurringFrequency.weekly:
        weekday_idx = _WEEKDAYS.index(config["weekday"])
        days_ahead = (weekday_idx - start_date.weekday()) % 7
        return start_date + timedelta(days=days_ahead)

    elif frequency == RecurringFrequency.biweekly:
        anchor = date.fromisoformat(config["anchor_date"])
        # The cycle is anchor ± n*14 for any integer n; find min >= start_date.
        n = math.ceil((start_date - anchor).days / 14)
        return anchor + timedelta(days=n * 14)

    elif frequency == RecurringFrequency.monthly:
        day = config["day"]
        y, m = start_date.year, start_date.month
        last = calendar.monthrange(y, m)[1]
        candidate = date(y, m, min(day, last))
        if candidate < start_date:
            m += 1
            if m > 12:
                m, y = 1, y + 1
            last = calendar.monthrange(y, m)[1]
            candidate = date(y, m, min(day, last))
        return candidate

    elif frequency == RecurringFrequency.quarterly:
        month_offset = config["month_offset"]
        day = config["day"]
        y, m = start_date.year, start_date.month
        for _ in range(8):
            if (m - 1) % 3 == month_offset:
                last = calendar.monthrange(y, m)[1]
                candidate = date(y, m, min(day, last))
                if candidate >= start_date:
                    return candidate
            m += 1
            if m > 12:
                m, y = 1, y + 1
        raise ValueError("Could not find quarterly start")

    elif frequency == RecurringFrequency.yearly:
        month = config["month"]
        day = config["day"]
        for y in range(start_date.year, start_date.year + 3):
            last = calendar.monthrange(y, month)[1]
            candidate = date(y, month, min(day, last))
            if candidate >= start_date:
                return candidate
        raise ValueError("Could not find yearly start")

    raise ValueError(f"Unknown frequency: {frequency}")


def compute_next_occurrence_after(
    after: date,
    frequency: RecurringFrequency,
    config: dict,
    start_date: date,
) -> date:
    """Next valid occurrence strictly after `after`, respecting start_date."""
    if frequency == RecurringFrequency.daily:
        candidate = max(after + timedelta(days=1), start_date)
        return apply_weekend_adjustment(candidate)

    elif frequency == RecurringFrequency.weekly:
        first = _first_occurrence_on_or_after(start_date, frequency, config)
        if first > after:
            return apply_weekend_adjustment(first)
        n = (after - first).days // 7 + 1
        return apply_weekend_adjustment(first + timedelta(weeks=n))

    elif frequency == RecurringFrequency.biweekly:
        first = _first_occurrence_on_or_after(start_date, frequency, config)
        if first > after:
            return apply_weekend_adjustment(first)
        n = (after - first).days // 14 + 1
        return apply_weekend_adjustment(first + timedelta(days=n * 14))

    elif frequency == RecurringFrequency.monthly:
        day = config["day"]
        y, m = after.year, after.month
        for _ in range(24):
            last = calendar.monthrange(y, m)[1]
            candidate = apply_weekend_adjustment(date(y, m, min(day, last)))
            if candidate > after and candidate >= start_date:
                return candidate
            m += 1
            if m > 12:
                m, y = 1, y + 1
        raise ValueError(f"Could not find next monthly occurrence after {after}")

    elif frequency == RecurringFrequency.quarterly:
        month_offset = config["month_offset"]
        day = config["day"]
        y, m = after.year, after.month
        for _ in range(16):
            if (m - 1) % 3 == month_offset:
                last = calendar.monthrange(y, m)[1]
                candidate = apply_weekend_adjustment(date(y, m, min(day, last)))
                if candidate > after and candidate >= start_date:
                    return candidate
            m += 1
            if m > 12:
                m, y = 1, y + 1
        raise ValueError(f"Could not find next quarterly occurrence after {after}")

    elif frequency == RecurringFrequency.yearly:
        month = config["month"]
        day = config["day"]
        for y in range(after.year, after.year + 10):
            last = calendar.monthrange(y, month)[1]
            candidate = apply_weekend_adjustment(date(y, month, min(day, last)))
            if candidate > after and candidate >= start_date:
                return candidate
        raise ValueError(f"Could not find next yearly occurrence after {after}")

    raise ValueError(f"Unknown frequency: {frequency}")


def get_most_recent_occurrence_on_or_before(
    today: date,
    frequency: RecurringFrequency,
    config: dict,
    start_date: date,
) -> date | None:
    """Most recent expected occurrence on/before today, not before start_date."""
    if today < start_date:
        return None

    if frequency == RecurringFrequency.daily:
        d = today
        while d >= start_date:
            adj = apply_weekend_adjustment(d)
            if adj <= today and adj >= start_date:
                return adj
            d -= timedelta(days=1)
        return None

    elif frequency in (RecurringFrequency.weekly, RecurringFrequency.biweekly):
        period = 7 if frequency == RecurringFrequency.weekly else 14
        first = _first_occurrence_on_or_after(start_date, frequency, config)
        if first > today:
            return None
        n = (today - first).days // period
        while n >= 0:
            candidate = apply_weekend_adjustment(first + timedelta(days=n * period))
            if candidate <= today and candidate >= start_date:
                return candidate
            n -= 1
        return None

    elif frequency == RecurringFrequency.monthly:
        day = config["day"]
        y, m = today.year, today.month
        for _ in range(36):
            last = calendar.monthrange(y, m)[1]
            candidate = apply_weekend_adjustment(date(y, m, min(day, last)))
            if start_date <= candidate <= today:
                return candidate
            if date(y, m, 1) <= start_date:
                break
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        return None

    elif frequency == RecurringFrequency.quarterly:
        month_offset = config["month_offset"]
        day = config["day"]
        y, m = today.year, today.month
        for _ in range(18):
            if (m - 1) % 3 == month_offset:
                last = calendar.monthrange(y, m)[1]
                candidate = apply_weekend_adjustment(date(y, m, min(day, last)))
                if start_date <= candidate <= today:
                    return candidate
            if date(y, m, 1) <= start_date:
                break
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        return None

    elif frequency == RecurringFrequency.yearly:
        month = config["month"]
        day = config["day"]
        for y in range(today.year, today.year - 3, -1):
            last = calendar.monthrange(y, month)[1]
            candidate = apply_weekend_adjustment(date(y, month, min(day, last)))
            if start_date <= candidate <= today:
                return candidate
        return None

    return None


def compute_next_due_date(
    template: "RecurringTransaction", today: date
) -> date | None:
    """Next date this template should fire after last_generated_date. None if exhausted."""
    if not template.is_active:
        return None
    if (
        template.max_occurrences is not None
        and template.occurrences_count >= template.max_occurrences
    ):
        return None

    after = (
        template.last_generated_date
        if template.last_generated_date is not None
        else template.start_date - timedelta(days=1)
    )

    try:
        next_date = compute_next_occurrence_after(
            after, template.frequency, template.day_config, template.start_date
        )
    except ValueError:
        return None

    if template.end_date is not None and next_date > template.end_date:
        return None

    return next_date


def is_template_due(template: "RecurringTransaction", today: date) -> bool:
    """True if there's at least one un-materialized occurrence on or before today."""
    if not template.is_active:
        return False
    if (
        template.max_occurrences is not None
        and template.occurrences_count >= template.max_occurrences
    ):
        return False

    after = (
        template.last_generated_date
        if template.last_generated_date is not None
        else template.start_date - timedelta(days=1)
    )

    most_recent = get_most_recent_occurrence_on_or_before(
        today, template.frequency, template.day_config, template.start_date
    )
    if most_recent is None:
        return False

    if template.end_date is not None and most_recent > template.end_date:
        return False

    return most_recent > after
