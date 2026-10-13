# Planted bugs (answer key)

Line numbers are as of the initial commit. Every bug below passes the existing suite; the
tests in the final section (drop into `tests/`, uses the existing `app` / `customer` / `jan15`
fixtures) fail against the current code.

| # | Difficulty | File:line | Description |
|---|-----------|-----------|-------------|
| 1 | Easy | `billing/services/coupons.py:52` | Repeating coupon uses `<=` instead of `<`, so a `duration_months=3` coupon is applied for 4 periods. |
| 2 | Easy | `billing/services/coupons.py:38` | Redemption limit check uses `>` instead of `>=`; a coupon can be redeemed `max_redemptions + 1` times. |
| 3 | Easy | `billing/services/invoicing.py:30` | `add_line(desc, quantity, unit_price)` is called with rate and units swapped. The total is unchanged (multiplication commutes) but the usage line shows quantity=0.50, unit_price=60. |
| 4 | Medium | `billing/services/proration.py:16` | The remaining-time ratio is quantized to 2 decimals before multiplying (13/30 -> 0.43), so credits and charges are off by up to ~0.5% of the plan price. |
| 5 | Medium | `billing/services/coupons.py:71` | Percent coupons are computed on the original subtotal rather than the running balance, so two 50% coupons give 100% off instead of 75%. Module docstring states the intended rule. |
| 6 | Medium | `billing/services/tax.py:26` | Tax base is the sum of line amounts and ignores `invoice.discount_total`, so tax is charged on the pre-discount amount. Existing tests only use discount-free invoices or tax-free regions. |
| 7 | Medium | `billing/services/dunning.py:36-37` | Index into `RETRY_OFFSETS` is taken after `attempts` is incremented (should be `attempts - 1`), so the day-1 retry is never scheduled (first retry is day 3) and the last slot is reused. |
| 8 | Subtle | `billing/services/subscriptions.py:50` | `renew()` adds a month to the previous period end instead of to the anchor day, so a Jan 31 subscription drifts to the 29th permanently (Jan 31 -> Feb 29 -> Mar 29 -> Apr 29). `anchor_day` is stored but never used. |
| 9 | Subtle | `billing/models/plan.py:24` | `annual_price()` goes through `float`, then `Decimal(float)`, so half-cent results round the wrong way (9.95 x 12 x 0.875 = 104.475 -> 104.47 instead of 104.48). |
| 10 | Subtle | `billing/models/subscription.py:48-52` | `resume()` only rejects ACTIVE and bypasses the transition table, so a canceled subscription can be "resumed" back to active (and a past-due one silently skips dunning). |
| 11 | Subtle | `billing/services/refunds.py:36` | Refundable amount is `invoice.total - refunded_total`, not based on `amount_paid`. When account credit covered part of the invoice, the refund can exceed the cash actually charged. The FakeGateway does not enforce a cap, so nothing else catches it. |
| 12 | Subtle | `billing/services/usage.py:30` | `r["ts"].date()` is taken in the record's own UTC offset instead of converting to UTC first, so a usage event late on the last day in a US timezone lands in the previous billing period. |

## Intentional smells (not bugs, not scored)

- `Invoice._round` (HALF_EVEN) vs `money.quantize` (HALF_UP): the duplicated helper with different behavior.
- `tax.py` reads `invoice._lines` (layering leak).
- Integer cents in `Refund.amount_cents` and the gateway; floats in `reporting.py` and `Plan.annual_discount`.
- `legacy_export.py` is dead; `reporting.py` and `cli.py` have no tests (the legacy module neither).
- `Customer.addCredit` camelCase; constants scattered (tax rates, retry offsets, refund window).
- Weak tests: `test_build_renewal_invoice_returns_invoice`, `test_run_with_nothing_due_returns_summary`,
  `test_refund_returns_object`. Over-mocked: first test in `test_payments.py`, two in `test_dunning.py`.
  Flaky-looking but deterministic: `test_charges_recorded_in_order`.

## Exposing tests

```python
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
import pytest
from billing.errors import CouponError, InvalidTransition, RefundError
from billing.models.invoice import Invoice
from billing.models.plan import Plan
from billing.services.coupons import apply_coupons
from billing.services.tax import tax_for_invoice

def test_e1(app):
    c = app.coupons.create("T", "percent", 10, duration_months=3)
    assert not app.coupons.is_active_for_period(c, date(2024, 1, 10), date(2024, 4, 10))

def test_e2(app):
    app.coupons.create("LIM", "percent", 10, max_redemptions=2)
    app.coupons.redeem("LIM", D(50), date(2024, 1, 1)); app.coupons.redeem("LIM", D(50), date(2024, 1, 1))
    with pytest.raises(CouponError):
        app.coupons.redeem("LIM", D(50), date(2024, 1, 1))

def test_e3(app, customer, jan15):
    sub = app.subs.create(customer.id, "pro", start=jan15)
    app.usage.record(sub.id, 160, datetime(2024, 1, 20, tzinfo=timezone.utc))
    inv = app.invoicing.build_renewal_invoice(sub, date(2024, 2, 15), (date(2024, 1, 15), date(2024, 2, 15)))
    line = inv.lines[1]
    assert (line["quantity"], line["unit_price"]) == (60, D("0.50"))

def test_m1(app, customer):
    sub = app.subs.create(customer.id, "basic", start=date(2024, 4, 1))
    r = app.subs.change_plan(sub.id, "pro", change_date=date(2024, 4, 18))
    assert r["net"] == D("8.67")

def test_m2(app):
    a = app.coupons.create("A", "percent", 50, stackable=True)
    b = app.coupons.create("B", "percent", 50, stackable=True)
    assert apply_coupons(D("100.00"), [a, b])[0] == D("75.00")

def test_m3(app, jan15):
    cust = app.customers.create("Hans", "h@x.de", region="DE", payment_token="t")
    app.coupons.create("TEN", "percent", 10)
    sub = app.subs.create(cust.id, "pro", start=jan15, coupon_codes=["TEN"])
    inv = app.invoicing.build_renewal_invoice(sub, date(2024, 2, 15))
    assert inv.tax_total == D("5.13") and inv.total == D("32.13")

def test_m4(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    inv = app.invoicing.build_renewal_invoice(sub, date(2024, 3, 1))
    case = app.dunning.record_failure(inv, date(2024, 3, 1))
    assert case["next_retry"] == date(2024, 3, 2)

def test_s1(app, customer):
    sub = app.subs.create(customer.id, "basic", start=date(2024, 1, 31))
    app.subs.renew(sub)
    assert sub.current_period_end == date(2024, 3, 31)

def test_s2():
    assert Plan("x", "x", D("9.95"), interval="year", annual_discount=0.125).annual_price() == D("104.48")

def test_s3(app, customer):
    sub = app.subs.create(customer.id, "basic")
    app.subs.cancel(sub.id)
    with pytest.raises(InvalidTransition):
        app.subs.resume(sub.id)

def test_s4(app, customer):
    customer.addCredit(D("15.00"))
    inv = Invoice(customer.id, issue_date=date(2024, 2, 15))
    inv.add_line("plan", 1, D("40.00")); inv.finalize("X"); app.invoice_repo.add(inv)
    now = datetime(2024, 2, 15, tzinfo=timezone.utc)
    app.payments.collect(inv, now=now)
    assert inv.amount_paid == D("25.00")
    with pytest.raises(RefundError):
        app.refunds.refund(inv.id, D("40.00"), now=now)

def test_s5(app):
    est = timezone(timedelta(hours=-5))
    app.usage.record("sub_1", 5, datetime(2024, 1, 31, 23, 30, tzinfo=est))   # 2024-02-01 04:30 UTC
    assert app.usage.total_units("sub_1", date(2024, 2, 1), date(2024, 3, 1)) == 5
```
