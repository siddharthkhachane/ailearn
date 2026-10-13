from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from billing.errors import CouponError
from billing.models.subscription import ACTIVE, CANCELED, PAST_DUE

D = Decimal


def test_run_with_nothing_due_returns_summary(app):
    summary = app.billing_run.run(date(2024, 1, 1))
    assert isinstance(summary, dict)


def test_run_before_period_end_does_nothing(app, customer, jan15):
    app.subs.create(customer.id, "basic", start=jan15)
    summary = app.billing_run.run(date(2024, 2, 14))
    assert summary["invoiced"] == 0


def test_renewal_invoices_and_charges(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    summary = app.billing_run.run(date(2024, 2, 15))
    assert summary["invoiced"] == 1
    assert summary["paid"] == 1
    assert sub.current_period_start == date(2024, 2, 15)
    assert sub.current_period_end == date(2024, 3, 15)
    assert app.gateway.charges[0]["amount_cents"] == 1000
    assert len(app.mailer.sent_to(customer.email)) == 1


def test_two_consecutive_cycles(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    app.billing_run.run(date(2024, 2, 15))
    app.billing_run.run(date(2024, 3, 15))
    assert sub.current_period_end == date(2024, 4, 15)
    assert len(app.gateway.charges) == 2


def test_running_twice_same_day_does_not_double_bill(app, customer, jan15):
    app.subs.create(customer.id, "basic", start=jan15)
    app.billing_run.run(date(2024, 2, 15))
    again = app.billing_run.run(date(2024, 2, 15))
    assert again["invoiced"] == 0


def test_trial_converts_and_bills(app, customer, jan15):
    sub = app.subs.create(customer.id, "trial", start=jan15)
    summary = app.billing_run.run(date(2024, 1, 29))
    assert summary["paid"] == 1
    assert sub.status == ACTIVE
    assert sub.current_period_end == date(2024, 2, 29)
    assert app.gateway.charges[0]["amount_cents"] == 2000


def test_cancel_at_period_end_stops_renewal(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    app.subs.cancel(sub.id, at_period_end=True)
    summary = app.billing_run.run(date(2024, 2, 15))
    assert summary["canceled"] == 1
    assert summary["invoiced"] == 0
    assert sub.status == CANCELED


def test_failed_payment_starts_dunning(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    app.gateway.fail_next(1)
    summary = app.billing_run.run(date(2024, 2, 15))
    assert summary["failed"] == 1
    assert sub.status == PAST_DUE
    assert len(app.dunning.cases) == 1


def test_dunning_retry_recovers_on_later_run(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    app.gateway.fail_next(1)
    app.billing_run.run(date(2024, 2, 15))
    summary = app.billing_run.run(date(2024, 3, 1))
    assert summary["retried"] == 1
    assert summary["recovered"] == 1
    assert sub.status == ACTIVE


def test_usage_is_billed_on_renewal(app, customer, jan15):
    sub = app.subs.create(customer.id, "pro", start=jan15)
    app.usage.record(sub.id, 120, datetime(2024, 1, 20, 8, 0, tzinfo=timezone.utc))
    app.billing_run.run(date(2024, 2, 15))
    assert app.gateway.charges[0]["amount_cents"] == 4000   # 30.00 + 20 units * 0.50


def test_subscribe_redeems_coupons(app, customer):
    app.coupons.create("WELCOME", "percent", 20, max_redemptions=1)
    app.subscribe(customer.id, "pro", coupon_codes=["WELCOME"])
    assert app.coupons.get("WELCOME").times_redeemed == 1


def test_subscribe_with_unknown_coupon_fails_before_creating(app, customer):
    with pytest.raises(CouponError):
        app.subscribe(customer.id, "pro", coupon_codes=["NOPE"])
    assert len(app.subs.repo) == 0


def test_app_change_plan_invoices_and_charges(app, customer):
    sub = app.subscribe(customer.id, "basic", start=date(2023, 2, 1))
    result, invoice = app.change_plan(sub.id, "pro", date(2023, 2, 15))
    assert result["net"] == D("10.00")
    assert invoice.status == "paid"


def test_multiple_customers_billed_independently(app, jan15):
    a = app.customers.create("A", "a@x.io", region="US-OR", payment_token="tok_a")
    b = app.customers.create("B", "b@x.io", region="US-OR")      # no card on file
    app.subs.create(a.id, "basic", start=jan15)
    app.subs.create(b.id, "basic", start=jan15)
    summary = app.billing_run.run(date(2024, 2, 15))
    assert (summary["invoiced"], summary["paid"], summary["failed"]) == (2, 1, 1)


def test_credit_balance_reduces_renewal_charge(app, customer, jan15):
    customer.addCredit(D("4.00"))
    app.subs.create(customer.id, "basic", start=jan15)
    app.billing_run.run(date(2024, 2, 15))
    assert app.gateway.charges[0]["amount_cents"] == 600


def test_full_discount_invoice_needs_no_charge(app, customer, jan15):
    app.coupons.create("FREE", "percent", 100)
    app.subs.create(customer.id, "basic", start=jan15, coupon_codes=["FREE"])
    summary = app.billing_run.run(date(2024, 2, 15))
    assert summary["paid"] == 1
    assert app.gateway.charges == []
