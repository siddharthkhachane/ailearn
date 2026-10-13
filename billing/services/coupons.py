"""Coupons and discount math.

Discounts are applied in order, each one against whatever is left after the
previous one, and never push the invoice below zero.
"""
from decimal import Decimal

from billing.errors import CouponError, NotFound
from billing.models.coupon import Coupon
from billing.money import ZERO, quantize
from billing.repos.memory import MemoryRepo
from billing.utils.dates import months_between


class CouponService:
    def __init__(self, repo=None):
        self.repo = repo or MemoryRepo("coupon")

    def create(self, code, kind, value, **kwargs):
        if kind not in ("percent", "fixed"):
            raise CouponError("unknown coupon kind: %s" % kind)
        value = Decimal(str(value))
        if value <= 0:
            raise CouponError("coupon value must be positive")
        if kind == "percent" and value > 100:
            raise CouponError("percent coupon cannot exceed 100")
        return self.repo.add(Coupon(code=code.upper(), kind=kind, value=value, **kwargs))

    def get(self, code):
        try:
            return self.repo.get(code.upper())
        except NotFound:
            raise CouponError("unknown coupon: %s" % code)

    def check_redeemable(self, coupon, subtotal, on_date):
        if coupon.expires_on and on_date > coupon.expires_on:
            raise CouponError("coupon %s has expired" % coupon.code)
        if coupon.max_redemptions is not None and coupon.times_redeemed > coupon.max_redemptions:
            raise CouponError("coupon %s is fully redeemed" % coupon.code)
        if subtotal < coupon.min_subtotal:
            raise CouponError("order too small for coupon %s" % coupon.code)

    def redeem(self, code, subtotal, on_date):
        coupon = self.get(code)
        self.check_redeemable(coupon, subtotal, on_date)
        coupon.times_redeemed += 1
        return coupon

    def is_active_for_period(self, coupon, applied_from, period_start):
        if coupon.duration_months is None:
            return True
        return months_between(applied_from, period_start) <= coupon.duration_months

    def select(self, coupons):
        """Non-stackable coupons can't be combined: first one wins."""
        for c in coupons:
            if not c.stackable:
                return [c]
        return list(coupons)


def apply_coupons(subtotal, coupons):
    """Return (total_discount, [coupons that actually discounted something])."""
    total_discount = ZERO
    applied = []
    for c in coupons:
        remaining = subtotal - total_discount
        if remaining <= 0:
            break
        if c.kind == "percent":
            amount = quantize(subtotal * c.value / 100)
        else:
            amount = c.value
        amount = min(amount, remaining)
        if amount > 0:
            total_discount += amount
            applied.append(c)
    return total_discount, applied
