from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from billing.models.customer import Customer
from billing.models.invoice import Invoice
from billing.models.subscription import ACTIVE, CANCELED, PAST_DUE
from billing.services.dunning import DunningService

D = Decimal
DAY0 = date(2024, 3, 1)


@pytest.fixture
def failing(app, customer, jan15):
    """An active subscription with an open renewal invoice that cannot be collected."""
    sub = app.subs.create(customer.id, "basic", start=jan15)
    inv = app.invoicing.build_renewal_invoice(sub, DAY0)
    return sub, inv


# --- over-mocked: only checks that collaborators were poked ---------------

def test_record_failure_notifies_customer():
    customers, notifier = MagicMock(), MagicMock()
    customers.get.return_value = Customer("c1", "A", "a@b.c")
    inv = Invoice("c1", issue_date=DAY0)
    inv.add_line("x", 1, D("5"))
    inv.finalize("INV-1")

    svc = DunningService(MagicMock(), MagicMock(), MagicMock(), customers, notifier)
    case = svc.record_failure(inv, DAY0)

    notifier.send.assert_called_once()
    assert case["attempts"] == 1


def test_retry_failure_records_again():
    svc = DunningService(MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock())
    svc.payments.collect.return_value = MagicMock(status="failed")
    svc.invoices.get.return_value = MagicMock(id="inv_1", subscription_id=None)
    svc.record_failure = MagicMock()
    assert svc.retry({"invoice_id": "inv_1"}, DAY0) is False
    svc.record_failure.assert_called_once()


# --- real flow ------------------------------------------------------------

def test_first_failure_marks_subscription_past_due(app, failing):
    sub, inv = failing
    case = app.dunning.record_failure(inv, DAY0)
    assert sub.status == PAST_DUE
    assert case["state"] == "open"
    assert case["next_retry"] > DAY0
    assert len(app.mailer.outbox) == 1


def test_repeated_failures_push_retry_later(app, failing):
    _, inv = failing
    first = app.dunning.record_failure(inv, DAY0)["next_retry"]
    second = app.dunning.record_failure(inv, DAY0 + timedelta(days=3))["next_retry"]
    assert second >= first


def test_due_cases_only_after_next_retry(app, failing):
    _, inv = failing
    case = app.dunning.record_failure(inv, DAY0)
    assert app.dunning.due_cases(DAY0) == []
    assert app.dunning.due_cases(case["next_retry"]) == [case]


def test_successful_retry_recovers_subscription(app, failing):
    sub, inv = failing
    case = app.dunning.record_failure(inv, DAY0)
    assert app.dunning.retry(case, case["next_retry"]) is True
    assert case["state"] == "recovered"
    assert sub.status == ACTIVE
    assert inv.status == "paid"


def test_failed_retry_keeps_case_open(app, failing):
    _, inv = failing
    case = app.dunning.record_failure(inv, DAY0)
    app.gateway.fail_next(1)
    assert app.dunning.retry(case, case["next_retry"]) is False
    assert case["attempts"] == 2
    assert case["state"] == "open"


def test_exhausted_case_cancels_subscription(app, failing):
    sub, inv = failing
    for i in range(5):
        case = app.dunning.record_failure(inv, DAY0 + timedelta(days=i))
    assert case["state"] == "exhausted"
    assert case["next_retry"] is None
    assert sub.status == CANCELED
    assert inv.status == "uncollectible"
    assert app.dunning.due_cases(date(2030, 1, 1)) == []
