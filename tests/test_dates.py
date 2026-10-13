from datetime import date, datetime, timezone

import pytest

from billing.utils.dates import (
    add_months, as_date, days_in_month, months_between, parse_date,
)


@pytest.mark.parametrize("start,months,expected", [
    (date(2024, 1, 15), 1, date(2024, 2, 15)),
    (date(2024, 1, 31), 1, date(2024, 2, 29)),
    (date(2023, 1, 31), 1, date(2023, 2, 28)),
    (date(2024, 11, 30), 3, date(2025, 2, 28)),
    (date(2024, 12, 15), 1, date(2025, 1, 15)),
    (date(2024, 3, 31), -1, date(2024, 2, 29)),
    (date(2024, 2, 29), 12, date(2025, 2, 28)),
    (date(2024, 5, 10), 0, date(2024, 5, 10)),
])
def test_add_months(start, months, expected):
    assert add_months(start, months) == expected


def test_days_in_month_leap():
    assert days_in_month(2024, 2) == 29
    assert days_in_month(2023, 2) == 28
    assert days_in_month(2024, 12) == 31


def test_months_between_ignores_day():
    assert months_between(date(2024, 1, 31), date(2024, 2, 1)) == 1
    assert months_between(date(2024, 1, 1), date(2025, 1, 1)) == 12
    assert months_between(date(2024, 3, 1), date(2024, 1, 1)) == -2


def test_parse_date():
    assert parse_date("2024-02-29") == date(2024, 2, 29)


def test_as_date_variants():
    assert as_date("2024-01-02") == date(2024, 1, 2)
    assert as_date(date(2024, 1, 2)) == date(2024, 1, 2)
    assert as_date(datetime(2024, 1, 2, 23, 59, tzinfo=timezone.utc)) == date(2024, 1, 2)


@pytest.mark.parametrize("year,month,days", [
    (2024, 1, 31), (2024, 4, 30), (2024, 6, 30), (2024, 9, 30), (2024, 11, 30),
    (2100, 2, 28), (2000, 2, 29),
])
def test_days_in_month_table(year, month, days):
    assert days_in_month(year, month) == days


@pytest.mark.parametrize("start,months,expected", [
    (date(2024, 8, 31), 1, date(2024, 9, 30)),
    (date(2024, 1, 31), 2, date(2024, 3, 31)),
    (date(2024, 1, 31), 12, date(2025, 1, 31)),
    (date(2024, 10, 31), 4, date(2025, 2, 28)),
    (date(2024, 6, 15), -6, date(2023, 12, 15)),
])
def test_add_months_more_cases(start, months, expected):
    assert add_months(start, months) == expected
