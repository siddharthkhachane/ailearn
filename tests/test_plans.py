from decimal import Decimal

import pytest

from billing.errors import NotFound, ValidationError
from billing.models.plan import Plan
from billing.repos.json_store import JsonStore
from billing.services.plans import PlanCatalog

D = Decimal


def test_monthly_plan_price_is_monthly_price():
    p = Plan("a", "A", D("12.50"))
    assert p.price_for_interval() == D("12.50")
    assert p.months == 1


def test_annual_price_with_discount():
    p = Plan("a", "A", D("10.00"), interval="year", annual_discount=0.5)
    assert p.annual_price() == D("60.00")
    assert p.price_for_interval() == D("60.00")
    assert p.months == 12


def test_annual_price_no_discount():
    p = Plan("a", "A", D("10.00"), interval="year")
    assert p.annual_price() == D("120.00")


def test_from_dict_coerces_types():
    p = Plan.from_dict({"id": "x", "name": "X", "monthly_price": 9.5, "trial_days": "7",
                        "overage_rate": "0.02"})
    assert p.monthly_price == D("9.5")
    assert p.trial_days == 7
    assert p.overage_rate == D("0.02")
    assert p.active is True


def test_catalog_add_get():
    cat = PlanCatalog()
    cat.add(Plan("a", "A", D("5")))
    assert cat.get("a").name == "A"
    with pytest.raises(NotFound):
        cat.get("missing")


def test_catalog_rejects_negative_price_and_bad_interval():
    cat = PlanCatalog()
    with pytest.raises(ValidationError):
        cat.add(Plan("a", "A", D("-1")))
    with pytest.raises(ValidationError):
        cat.add(Plan("b", "B", D("1"), interval="week"))


@pytest.mark.parametrize("name", ["", "   "])
def test_catalog_rejects_empty_or_whitespace_name(name):
    cat = PlanCatalog()
    with pytest.raises(ValidationError):
        cat.add(Plan("a", name, D("1")))


def test_catalog_rejects_negative_trial_days():
    cat = PlanCatalog()
    with pytest.raises(ValidationError):
        cat.add(Plan("a", "A", D("1"), trial_days=-1))


def test_catalog_rejects_negative_included_units():
    cat = PlanCatalog()
    with pytest.raises(ValidationError):
        cat.add(Plan("a", "A", D("1"), included_units=-1))


def test_catalog_accepts_zero_trial_days_and_included_units():
    cat = PlanCatalog()
    cat.add(Plan("a", "A", D("1"), trial_days=0, included_units=0))
    assert cat.get("a").trial_days == 0
    assert cat.get("a").included_units == 0


def test_list_active_sorted_by_price_and_skips_inactive():
    cat = PlanCatalog()
    cat.add(Plan("big", "Big", D("50")))
    cat.add(Plan("small", "Small", D("5")))
    cat.add(Plan("old", "Old", D("1")))
    cat.deactivate("old")
    assert [p.id for p in cat.list_active()] == ["small", "big"]


def test_json_roundtrip(tmp_path):
    store = JsonStore(str(tmp_path))
    cat = PlanCatalog()
    cat.add(Plan("a", "A", D("5.25"), included_units=10, overage_rate=D("0.01")))
    cat.save_json(store)

    fresh = PlanCatalog()
    assert fresh.load_json(store) == 1
    loaded = fresh.get("a")
    assert loaded.monthly_price == D("5.25")
    assert loaded.included_units == 10


def test_load_json_missing_file_loads_nothing(tmp_path):
    assert PlanCatalog().load_json(JsonStore(str(tmp_path))) == 0
