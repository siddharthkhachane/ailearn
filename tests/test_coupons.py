from datetime import date
from decimal import Decimal

import pytest

from billing.errors import CouponError
from billing.services.coupons import CouponService, apply_coupons

D = Decimal
TODAY = date(2024, 6, 1)


@pytest.fixture
def svc():
    return CouponService()


def test_create_uppercases_code_and_get_is_case_insensitive(svc):
    svc.create("save10", "percent", 10)
    assert svc.get("SaVe10").code == "SAVE10"


@pytest.mark.parametrize("kind,value", [("percent", 0), ("percent", 101), ("fixed", -1),
                                        ("bogus", 5)])
def test_create_rejects_bad_values(svc, kind, value):
    with pytest.raises(CouponError):
        svc.create("X", kind, value)


def test_get_unknown(svc):
    with pytest.raises(CouponError):
        svc.get("nope")


def test_expired_coupon_rejected(svc):
    c = svc.create("OLD", "percent", 10, expires_on=date(2024, 5, 31))
    with pytest.raises(CouponError):
        svc.check_redeemable(c, D("100"), TODAY)


def test_coupon_valid_on_expiry_day(svc):
    c = svc.create("LAST", "percent", 10, expires_on=TODAY)
    svc.check_redeemable(c, D("100"), TODAY)


def test_redemption_limit_exceeded(svc):
    c = svc.create("LIM", "percent", 10, max_redemptions=2)
    c.times_redeemed = 5
    with pytest.raises(CouponError):
        svc.check_redeemable(c, D("100"), TODAY)


def test_redeem_increments_counter(svc):
    svc.create("LIM", "percent", 10, max_redemptions=3)
    assert svc.redeem("lim", D("50"), TODAY).times_redeemed == 1
    assert svc.redeem("lim", D("50"), TODAY).times_redeemed == 2


def test_min_subtotal_enforced(svc):
    c = svc.create("BIG", "fixed", 5, min_subtotal=D("50"))
    with pytest.raises(CouponError):
        svc.check_redeemable(c, D("49.99"), TODAY)
    svc.check_redeemable(c, D("50"), TODAY)


def test_forever_coupon_always_active(svc):
    c = svc.create("FOREVER", "percent", 10)
    assert svc.is_active_for_period(c, date(2024, 1, 1), date(2030, 1, 1))


def test_repeating_coupon_window(svc):
    c = svc.create("THREE", "percent", 10, duration_months=3)
    start = date(2024, 1, 10)
    assert svc.is_active_for_period(c, start, date(2024, 1, 10))
    assert svc.is_active_for_period(c, start, date(2024, 3, 10))
    assert not svc.is_active_for_period(c, start, date(2024, 8, 10))


def test_select_first_non_stackable_wins(svc):
    a = svc.create("A", "percent", 10)
    b = svc.create("B", "fixed", 5, stackable=True)
    c = svc.create("C", "percent", 20, stackable=True)
    assert svc.select([a, b, c]) == [a]
    assert svc.select([b, c]) == [b, c]


def test_apply_single_percent(svc):
    c = svc.create("P", "percent", 15)
    discount, applied = apply_coupons(D("80.00"), [c])
    assert discount == D("12.00")
    assert applied == [c]


def test_apply_fixed_capped_at_subtotal(svc):
    c = svc.create("F", "fixed", 500)
    discount, _ = apply_coupons(D("20.00"), [c])
    assert discount == D("20.00")


def test_apply_percent_then_fixed_stack(svc):
    p = svc.create("P", "percent", 10, stackable=True)
    f = svc.create("F", "fixed", 5, stackable=True)
    discount, applied = apply_coupons(D("100.00"), [p, f])
    assert discount == D("15.00")
    assert applied == [p, f]


def test_apply_stops_when_nothing_left(svc):
    f1 = svc.create("F1", "fixed", 60, stackable=True)
    f2 = svc.create("F2", "fixed", 60, stackable=True)
    f3 = svc.create("F3", "fixed", 60, stackable=True)
    discount, applied = apply_coupons(D("100.00"), [f1, f2, f3])
    assert discount == D("100.00")
    assert applied == [f1, f2]


def test_apply_no_coupons():
    assert apply_coupons(D("10"), []) == (D("0"), [])
