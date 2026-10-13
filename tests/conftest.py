from datetime import date
from decimal import Decimal

import pytest

from billing import clock
from billing.app import BillingApp
from billing.models.plan import Plan
from billing.utils.misc import reset_ids

D = Decimal


@pytest.fixture(autouse=True)
def _clean_state():
    reset_ids()
    clock.unfreeze()
    yield
    clock.unfreeze()


@pytest.fixture
def app():
    a = BillingApp()
    a.plans.add(Plan("basic", "Basic", D("10.00")))
    a.plans.add(Plan("pro", "Pro", D("30.00"), included_units=100, overage_rate=D("0.50")))
    a.plans.add(Plan("trial", "Trial Plan", D("20.00"), trial_days=14))
    return a


@pytest.fixture
def customer(app):
    # US-OR has no sales tax, which keeps the arithmetic in most tests simple
    return app.customers.create("Ada", "ada@example.com", region="US-OR", payment_token="tok_ok")


@pytest.fixture
def jan15():
    return date(2024, 1, 15)
