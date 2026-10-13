from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from billing.errors import RefundError
from billing.models.invoice import Invoice

D = Decimal
PAID_AT = datetime(2024, 2, 15, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def paid_invoice(app, customer):
    inv = Invoice(customer.id, issue_date=date(2024, 2, 15))
    inv.add_line("plan", 1, D("40.00"))
    inv.finalize("INV-R1")
    app.invoice_repo.add(inv)
    app.payments.collect(inv, now=PAID_AT)
    return inv


def test_full_refund(app, customer, paid_invoice):
    refund = app.refunds.refund(paid_invoice.id, now=PAID_AT + timedelta(days=3))
    assert refund.amount == D("40.00")
    assert refund.amount_cents == 4000
    assert paid_invoice.status == "refunded"
    assert app.gateway.refunds[0]["amount_cents"] == 4000


def test_partial_refunds_accumulate(app, paid_invoice):
    now = PAID_AT + timedelta(days=1)
    app.refunds.refund(paid_invoice.id, D("15.00"), now=now)
    assert paid_invoice.status == "partially_refunded"
    app.refunds.refund(paid_invoice.id, D("25.00"), now=now)
    assert paid_invoice.status == "refunded"
    assert paid_invoice.refunded_total == D("40.00")


def test_cannot_refund_more_than_invoice(app, paid_invoice):
    with pytest.raises(RefundError):
        app.refunds.refund(paid_invoice.id, D("40.01"), now=PAID_AT)


def test_cannot_refund_twice_the_remainder(app, paid_invoice):
    app.refunds.refund(paid_invoice.id, D("30.00"), now=PAID_AT)
    with pytest.raises(RefundError):
        app.refunds.refund(paid_invoice.id, D("20.00"), now=PAID_AT)


def test_zero_or_negative_amount_rejected(app, paid_invoice):
    for bad in (D("0"), D("-5")):
        with pytest.raises(RefundError):
            app.refunds.refund(paid_invoice.id, bad, now=PAID_AT)


def test_unpaid_invoice_cannot_be_refunded(app, customer):
    inv = Invoice(customer.id)
    inv.add_line("plan", 1, D("5.00"))
    inv.finalize("INV-R2")
    app.invoice_repo.add(inv)
    with pytest.raises(RefundError):
        app.refunds.refund(inv.id)


def test_refund_window(app, paid_invoice):
    with pytest.raises(RefundError):
        app.refunds.refund(paid_invoice.id, now=PAID_AT + timedelta(days=200))


def test_refund_sends_email(app, customer, paid_invoice):
    app.refunds.refund(paid_invoice.id, D("10.00"), now=PAID_AT)
    assert len(app.mailer.sent_to(customer.email)) == 1


def test_refund_returns_object(app, paid_invoice):
    refund = app.refunds.refund(paid_invoice.id, D("1.00"), now=PAID_AT)
    assert refund
