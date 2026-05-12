import calendar
from datetime import date, timedelta

from app.models.enums import PayFrequency

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def apply_weekend_adjustment(d: date) -> date:
    """Saturday -> Friday; Sunday -> Monday. Other days unchanged."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def compute_pay_dates_for_month(
    year: int, month: int, frequency: PayFrequency, config: dict
) -> list[date]:
    """All weekend-adjusted pay dates in the given month for this frequency+config, sorted."""
    last_day = calendar.monthrange(year, month)[1]

    if frequency == PayFrequency.monthly:
        day = min(int(config["day"]), last_day)
        return [apply_weekend_adjustment(date(year, month, day))]

    if frequency == PayFrequency.semi_monthly:
        result = []
        for v in config["days"]:
            day = last_day if v == "last" else min(int(v), last_day)
            result.append(apply_weekend_adjustment(date(year, month, day)))
        return sorted(result)

    if frequency == PayFrequency.weekly:
        weekday_idx = _WEEKDAYS.index(config["weekday"])
        result = []
        d = date(year, month, 1)
        while d.month == month:
            if d.weekday() == weekday_idx:
                result.append(apply_weekend_adjustment(d))
            d += timedelta(days=1)
        return sorted(result)

    if frequency == PayFrequency.biweekly:
        anchor = date.fromisoformat(config["anchor_date"])
        start_of_month = date(year, month, 1)
        end_of_month = date(year, month, last_day)

        # Find the first occurrence in or before the start of the month
        if anchor <= start_of_month:
            days_diff = (start_of_month - anchor).days
            n = days_diff // 14
            current = anchor + timedelta(days=n * 14)
        else:
            # anchor is after start_of_month; step backwards
            days_diff = (anchor - start_of_month).days
            n = (days_diff + 13) // 14
            current = anchor - timedelta(days=n * 14)

        # advance until we're within the month
        while current < start_of_month:
            current += timedelta(days=14)

        result = []
        while current <= end_of_month:
            result.append(apply_weekend_adjustment(current))
            current += timedelta(days=14)
        return sorted(result)

    return []


def get_most_recent_pay_date(
    today: date, frequency: PayFrequency, config: dict, start_date: date
) -> date | None:
    """Most recent pay date <= today that is also >= start_date. None if none yet."""
    candidates: list[date] = []
    year, month = today.year, today.month

    for _ in range(4):
        for d in compute_pay_dates_for_month(year, month, frequency, config):
            if start_date <= d <= today:
                candidates.append(d)
        # Stop scanning once we're past start_date's month
        if date(year, month, 1) <= start_date:
            break
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    return max(candidates) if candidates else None


def get_next_pay_date(
    after: date, frequency: PayFrequency, config: dict, start_date: date
) -> date:
    """Next pay date strictly after `after`, respecting start_date."""
    year, month = after.year, after.month

    for _ in range(4):
        for d in sorted(compute_pay_dates_for_month(year, month, frequency, config)):
            if d > after and d >= start_date:
                return d
        month += 1
        if month == 13:
            month = 1
            year += 1

    raise ValueError(
        f"Could not find next pay date after {after} within 4 months"
    )


def is_due_for_pay(employee, today: date) -> bool:
    """True if a pay date has passed since last_paid_date (or since start_date if never paid)."""
    after = (
        employee.last_paid_date
        if employee.last_paid_date is not None
        else employee.start_date - timedelta(days=1)
    )
    most_recent = get_most_recent_pay_date(
        today, employee.pay_frequency, employee.pay_day_config, employee.start_date
    )
    if most_recent is None:
        return False
    return most_recent > after
