from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from billing.errors import BillingError
from billing.models.invoice import Invoice

D = Decimal
TODAY = date(2024, 2, 15)


# --- Invoice model --------------------------------------------------------

def test_totals():
    inv = Invoice("cus_1", issue_date=TODAY)
    inv.add_line("a", 2, D("10.00"))
    inv.add_line("b", 1, D("5.50"))
    inv.discount_total = D("3.00")
    inv.tax_total = D("1.00")
    assert inv.subtotal == D("25.50")
    assert inv.total == D("23.50")
    assert inv.amount_due == D("23.50")


def test_due_date_uses_net_terms():
    assert Invoice("cus_1", issue_date=TODAY).due_date == date(2024, 2, 29)


def test_lines_property_returns_copies():
    inv = Invoice("cus_1")
    inv.add_line("a", 1, D("1.00"))
    inv.lines[0]["amount"] = D("999")
    assert inv.subtotal == D("1.00")


def test_cannot_edit_after_finalize():
    inv = Invoice("cus_1")
    inv.add_line("a", 1, D("1.00"))
    inv.finalize("INV-1")
    assert inv.status == "open"
    with pytest.raises(BillingError):
        inv.add_line("b", 1, D("1.00"))
    with pytest.raises(BillingError):
        inv.finalize("INV-2")


def test_zero_total_invoice_is_born_paid():
    inv = Invoice("cus_1")
    inv.add_line("free", 1, D("0.00"))
    inv.finalize("INV-1")
    assert inv.status == "paid"


def test_partial_payment_keeps_invoice_open():
    inv = Invoice("cus_1")
    inv.add_line("a", 1, D("10.00"))
    inv.finalize("INV-1")
    inv.mark_paid(D("4.00"))
    assert inv.status == "open"
    assert inv.amount_due == D("6.00")
    inv.mark_paid(D("6.00"))
    assert inv.status == "paid"
    assert inv.paid_at is not None


def test_void_rules():
    inv = Invoice("cus_1")
    inv.void()
    assert inv.status == "void"
    with pytest.raises(BillingError):
        inv.void()


def test_is_overdue():
    inv = Invoice("cus_1", issue_date=TODAY)
    inv.add_line("a", 1, D("1.00"))
    inv.finalize("INV-1")
    assert not inv.is_overdue(date(2024, 2, 29))
    assert inv.is_overdue(date(2024, 3, 1))


# --- InvoiceService -------------------------------------------------------

def test_build_renewal_invoice_returns_invoice(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    inv = app.invoicing.build_renewal_invoice(sub, TODAY)
    assert inv is not None


def test_renewal_invoice_basic_amounts(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    inv = app.invoicing.build_renewal_invoice(sub, TODAY)
    assert inv.status == "open"
    assert inv.number == "INV-2024-00001"
    assert inv.total == D("10.00")
    assert len(inv.lines) == 1


def test_invoice_numbers_increment(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    first = app.invoicing.build_renewal_invoice(sub, TODAY)
    second = app.invoicing.build_renewal_invoice(sub, TODAY)
    assert (first.number, second.number) == ("INV-2024-00001", "INV-2024-00002")


def test_usage_overage_added(app, customer, jan15):
    sub = app.subs.create(customer.id, "pro", start=jan15)
    ts = datetime(2024, 1, 20, 9, 0, tzinfo=timezone.utc)
    app.usage.record(sub.id, 160, ts)
    inv = app.invoicing.build_renewal_invoice(
        sub, TODAY, usage_period=(date(2024, 1, 15), date(2024, 2, 15)))
    assert inv.subtotal == D("60.00")        # 30.00 plan + 60 billable units * 0.50
    assert [l["kind"] for l in inv.lines] == ["subscription", "usage"]


def test_no_usage_line_within_allowance(app, customer, jan15):
    sub = app.subs.create(customer.id, "pro", start=jan15)
    app.usage.record(sub.id, 100, datetime(2024, 1, 20, tzinfo=timezone.utc))
    inv = app.invoicing.build_renewal_invoice(
        sub, TODAY, usage_period=(date(2024, 1, 15), date(2024, 2, 15)))
    assert len(inv.lines) == 1


def test_percent_coupon_discount(app, customer, jan15):
    app.coupons.create("TEN", "percent", 10)
    sub = app.subs.create(customer.id, "pro", start=jan15, coupon_codes=["TEN"])
    inv = app.invoicing.build_renewal_invoice(sub, TODAY)
    assert inv.discount_total == D("3.00")
    assert inv.coupon_codes == ["TEN"]
    assert inv.total == D("27.00")


def test_regional_tax_applied(app, jan15):
    cust = app.customers.create("Hans", "hans@example.de", region="DE")
    sub = app.subs.create(cust.id, "pro", start=jan15)
    inv = app.invoicing.build_renewal_invoice(sub, TODAY)
    assert inv.tax_total == D("5.70")
    assert inv.total == D("35.70")


def test_expired_duration_coupon_not_applied(app, customer, jan15):
    app.coupons.create("ONCE", "fixed", 5, duration_months=1)
    sub = app.subs.create(customer.id, "basic", start=jan15, coupon_codes=["ONCE"])
    sub.current_period_start = date(2024, 9, 15)
    inv = app.invoicing.build_renewal_invoice(sub, date(2024, 9, 15))
    assert inv.discount_total == D("0")


def test_plan_change_invoice_for_upgrade(app, customer):
    sub = app.subs.create(customer.id, "basic", start=date(2023, 2, 1))
    result = app.subs.change_plan(sub.id, "pro", change_date=date(2023, 2, 15))
    inv = app.invoicing.invoice_for_plan_change(sub, result, date(2023, 2, 15))
    assert inv.total == D("10.00")
    assert [l["amount"] for l in inv.lines] == [D("-5.00"), D("15.00")]


def test_plan_change_downgrade_becomes_credit(app, customer):
    sub = app.subs.create(customer.id, "pro", start=date(2023, 2, 1))
    result = app.subs.change_plan(sub.id, "basic", change_date=date(2023, 2, 15))
    assert app.invoicing.invoice_for_plan_change(sub, result, date(2023, 2, 15)) is None
    assert customer.credit_balance == D("10.00")


def test_to_dict_serialises_money_as_strings():
    inv = Invoice("cus_1", issue_date=TODAY)
    inv.add_line("a", 2, D("10.00"))
    inv.finalize("INV-9")
    d = inv.to_dict()
    assert d["total"] == "20.00"
    assert d["lines"][0]["amount"] == "20.00"
    assert d["due_date"] == "2024-02-29"
    assert d["status"] == "open"
