import calendar
from datetime import date, datetime


def days_in_month(year, month):
    return calendar.monthrange(year, month)[1]


def add_months(d, months):
    """Add calendar months, clamping the day to the end of the target month."""
    idx = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(idx, 12)
    month = month0 + 1
    return d.replace(year=year, month=month, day=min(d.day, days_in_month(year, month)))


def months_between(start, end):
    """Whole calendar months from start's month to end's month."""
    return (end.year - start.year) * 12 + (end.month - start.month)


def parse_date(value):
    return date.fromisoformat(value)


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return parse_date(value)
