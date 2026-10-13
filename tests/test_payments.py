from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from billing.errors import PaymentError
from billing.models.customer import Customer
from billing.models.invoice import Invoice
from billing.services.payments import PaymentService

D = Decimal


def open_invoice(customer_id, amount="25.00"):
    inv = Invoice(customer_id, issue_date=date(2024, 2, 15))
    inv.add_line("plan", 1, D(amount))
    inv.finalize("INV-TEST")
    return inv


# --- mock-heavy: written when the gateway was still a stub ---------------

def test_collect_calls_gateway_with_cents():
    gateway = MagicMock()
    gateway.charge.return_value = {"ok": True, "ref": "ch_1", "error": None}
    customers = MagicMock()
    customers.get.return_value = Customer("c1", "A", "a@b.c", payment_token="tok")
    payments = MagicMock()
    payments.find.return_value = []

    svc = PaymentService(gateway, customers, payments)
    inv = open_invoice("c1")
    svc.collect(inv)

    gateway.charge.assert_called_once()
    assert gateway.charge.call_args[0][1] == 2500
    payments.add.assert_called_once()
    assert inv.status == "paid"


# --- real collaborators ---------------------------------------------------

def test_successful_charge_marks_invoice_paid(app, customer):
    inv = open_invoice(customer.id)
    p = app.payments.collect(inv)
    assert p.status == "succeeded"
    assert p.gateway_ref == "ch_0001"
    assert inv.status == "paid"
    assert inv.amount_paid == D("25.00")


def test_declined_charge_leaves_invoice_open(app, customer):
    app.gateway.declined_tokens.add("tok_ok")
    inv = open_invoice(customer.id)
    p = app.payments.collect(inv)
    assert p.status == "failed"
    assert p.error == "card_declined"
    assert inv.status == "open"
    assert inv.amount_due == D("25.00")


def test_credit_is_used_before_card(app, customer):
    customer.add_credit(D("10.00"))
    inv = open_invoice(customer.id)
    app.payments.collect(inv)
    assert app.gateway.charges[0]["amount_cents"] == 1500
    assert inv.credit_applied == D("10.00")
    assert customer.credit_balance == D("0.00")


def test_credit_covering_everything_skips_gateway(app, customer):
    customer.add_credit(D("100.00"))
    inv = open_invoice(customer.id)
    p = app.payments.collect(inv)
    assert p.status == "succeeded"
    assert p.amount == D("0")
    assert app.gateway.charges == []
    assert inv.status == "paid"
    assert customer.credit_balance == D("75.00")


def test_cannot_collect_paid_invoice(app, customer):
    inv = open_invoice(customer.id)
    app.payments.collect(inv)
    with pytest.raises(PaymentError):
        app.payments.collect(inv)


def test_retry_uses_new_idempotency_key(app, customer):
    app.gateway.fail_next(1)
    inv = open_invoice(customer.id)
    assert app.payments.collect(inv).status == "failed"
    assert app.payments.collect(inv).status == "succeeded"
    assert len(app.payments.payments_for(inv.id)) == 2


@pytest.mark.parametrize("amount,cents", [("0.99", 99), ("100.00", 10000), ("19.995", 2000)])
def test_charge_amounts_are_converted_to_cents(app, customer, amount, cents):
    from billing.models.invoice import Invoice
    inv = Invoice(customer.id, issue_date=date(2024, 2, 15))
    inv.add_line("x", 1, D(amount))
    inv.finalize("INV-C")
    app.payments.collect(inv)
    assert app.gateway.charges[0]["amount_cents"] == cents
