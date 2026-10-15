from datetime import date
from decimal import Decimal

from billing.models.customer import Customer
from billing.models.invoice import Invoice
from billing.notify import templates

D = Decimal


def make_invoice():
    inv = Invoice("c1", issue_date=date(2024, 1, 15))
    inv.add_line("Basic", 1, D("1234.50"))
    inv.finalize("INV-2024-00001")
    return inv


def make_customer():
    return Customer("c1", "Ada", "ada@example.com")


def test_invoice_ready_shows_total_and_due_date():
    inv = make_invoice()
    inv.credit_applied = D("34.50")  # total ($1,234.50) differs from the amount due
    subject, body = templates.invoice_ready(make_customer(), inv)
    assert subject == "Your invoice INV-2024-00001"
    assert "Ada" in body
    assert "$1,234.50" in body
    assert "$1,200.00" not in body
    assert str(inv.due_date) in body


def test_invoice_ready_without_credit_shows_total():
    subject, body = templates.invoice_ready(make_customer(), make_invoice())
    assert subject == "Your invoice INV-2024-00001"
    assert "$1,234.50" in body


def test_payment_failed_uses_amount_due_and_shows_next_retry():
    inv = make_invoice()
    inv.credit_applied = D("34.50")  # amount due ($1,200.00) differs from the invoice total
    subject, body = templates.payment_failed(make_customer(), inv, next_retry=date(2024, 1, 20))
    assert subject == "Payment failed for invoice INV-2024-00001"
    assert "Ada" in body
    assert "$1,200.00" in body
    assert "$1,234.50" not in body
    assert "We will try again on 2024-01-20." in body


def test_payment_failed_without_next_retry_has_no_retry_line():
    subject, body = templates.payment_failed(make_customer(), make_invoice())
    assert subject == "Payment failed for invoice INV-2024-00001"
    assert "Ada" in body
    assert "$1,234.50" in body
    assert "try again" not in body


def test_refund_issued_shows_refund_amount_not_invoice_total():
    subject, body = templates.refund_issued(make_customer(), make_invoice(), D("5"))
    assert subject == "Refund issued for invoice INV-2024-00001"
    assert "Ada" in body
    assert "$5.00" in body
    assert "$1,234.50" not in body


def test_subscription_canceled():
    subject, body = templates.subscription_canceled(make_customer())
    assert subject == "Your subscription has been canceled"
    assert "Ada" in body
    assert "canceled" in body
