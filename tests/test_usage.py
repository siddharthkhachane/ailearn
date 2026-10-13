from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from billing.errors import ValidationError
from billing.models.plan import Plan
from billing.services.usage import (
    UsageService, billable_units, tiered_charge, usage_charge,
)

D = Decimal
UTC = timezone.utc


def ts(y, m, d, h=12):
    return datetime(y, m, d, h, 0, tzinfo=UTC)


def test_record_validates_units():
    svc = UsageService()
    for bad in (0, -5, 1.5, "3"):
        with pytest.raises(ValidationError):
            svc.record("sub_1", bad)


def test_records_for_period_filters_by_sub_and_window():
    svc = UsageService()
    svc.record("sub_1", 10, ts(2024, 1, 10))
    svc.record("sub_1", 20, ts(2024, 1, 31))
    svc.record("sub_1", 99, ts(2024, 2, 1))
    svc.record("sub_2", 7, ts(2024, 1, 15))
    got = svc.records_for_period("sub_1", date(2024, 1, 1), date(2024, 2, 1))
    assert [r["units"] for r in got] == [10, 20]
    assert svc.total_units("sub_1", date(2024, 1, 1), date(2024, 2, 1)) == 30


def test_record_defaults_to_now():
    rec = UsageService().record("sub_1", 1)
    assert rec["ts"].tzinfo is not None


def test_billable_units_respects_allowance():
    plan = Plan("p", "P", D("1"), included_units=100)
    assert billable_units(plan, 80) == 0
    assert billable_units(plan, 100) == 0
    assert billable_units(plan, 130) == 30


def test_usage_charge():
    plan = Plan("p", "P", D("1"), included_units=100, overage_rate=D("0.015"))
    assert usage_charge(plan, 100) == D("0.00")
    assert usage_charge(plan, 300) == D("3.00")
    assert usage_charge(plan, 101) == D("0.02")


TIERS = [{"up_to": 100, "rate": "0.10"}, {"up_to": None, "rate": "0.05"}]


@pytest.mark.parametrize("units,expected", [
    (0, "0.00"),
    (50, "5.00"),
    (100, "10.00"),
    (150, "12.50"),
])
def test_tiered_charge(units, expected):
    assert tiered_charge(units, TIERS) == D(expected)
