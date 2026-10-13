from datetime import date
from decimal import Decimal

from billing.services.proration import prorate, remaining_ratio

D = Decimal
START = date(2023, 2, 1)
END = date(2023, 3, 1)       # 28 days


def test_full_period_remaining():
    assert remaining_ratio(START, END, START) == D("1.00")


def test_half_period_remaining():
    assert remaining_ratio(START, END, date(2023, 2, 15)) == D("0.50")


def test_nothing_remaining_at_period_end():
    assert remaining_ratio(START, END, END) == D("0.00")


def test_change_date_outside_period_is_clamped():
    assert remaining_ratio(START, END, date(2023, 1, 1)) == D("1.00")
    assert remaining_ratio(START, END, date(2023, 4, 1)) == D("0.00")


def test_zero_length_period():
    assert remaining_ratio(START, START, START) == D("0")


def test_prorate_upgrade():
    r = prorate(D("10.00"), D("30.00"), D("0.50"))
    assert r["credit"] == D("5.00")
    assert r["charge"] == D("15.00")
    assert r["net"] == D("10.00")


def test_prorate_downgrade_is_negative():
    r = prorate(D("30.00"), D("10.00"), D("0.50"))
    assert r["net"] == D("-10.00")


def test_prorate_full_ratio_is_price_difference():
    r = prorate(D("12.34"), D("20.00"), D("1.00"))
    assert r["net"] == D("7.66")
