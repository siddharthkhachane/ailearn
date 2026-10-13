from datetime import date

import pytest

from billing.errors import InvalidTransition, ValidationError
from billing.models.subscription import (
    ACTIVE, CANCELED, PAST_DUE, PAUSED, TRIALING, Subscription,
)


def test_create_active_subscription(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    assert sub.status == ACTIVE
    assert sub.current_period_start == jan15
    assert sub.current_period_end == date(2024, 2, 15)
    assert sub.anchor_day == 15


def test_create_with_trial(app, customer, jan15):
    sub = app.subs.create(customer.id, "trial", start=jan15)
    assert sub.status == TRIALING
    assert sub.trial_end == date(2024, 1, 29)
    assert sub.current_period_end == sub.trial_end


def test_create_unknown_customer_or_plan(app, customer):
    from billing.errors import NotFound
    with pytest.raises(NotFound):
        app.subs.create("cus_nope", "basic")
    with pytest.raises(NotFound):
        app.subs.create(customer.id, "nope")


def test_create_on_inactive_plan_rejected(app, customer):
    app.plans.deactivate("basic")
    with pytest.raises(ValidationError):
        app.subs.create(customer.id, "basic")


def test_renew_moves_period_forward(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    app.subs.renew(sub)
    assert sub.current_period_start == date(2024, 2, 15)
    assert sub.current_period_end == date(2024, 3, 15)
    app.subs.renew(sub)
    assert sub.current_period_end == date(2024, 4, 15)


def test_activate_after_trial(app, customer, jan15):
    sub = app.subs.create(customer.id, "trial", start=jan15)
    app.subs.activate_after_trial(sub)
    assert sub.status == ACTIVE
    assert sub.current_period_start == date(2024, 1, 29)
    assert sub.current_period_end == date(2024, 2, 29)


def test_cancel_immediately(app, customer):
    sub = app.subs.create(customer.id, "basic")
    app.subs.cancel(sub.id)
    assert sub.status == CANCELED
    assert sub.canceled_at is not None


def test_cancel_at_period_end_keeps_status(app, customer):
    sub = app.subs.create(customer.id, "basic")
    app.subs.cancel(sub.id, at_period_end=True)
    assert sub.status == ACTIVE
    assert sub.cancel_at_period_end is True


def test_cancel_twice_is_invalid(app, customer):
    sub = app.subs.create(customer.id, "basic")
    app.subs.cancel(sub.id)
    with pytest.raises(InvalidTransition):
        app.subs.cancel(sub.id)


def test_pause_and_resume(app, customer):
    sub = app.subs.create(customer.id, "basic")
    app.subs.pause(sub.id)
    assert sub.status == PAUSED
    assert sub.paused_at is not None
    app.subs.resume(sub.id)
    assert sub.status == ACTIVE
    assert sub.paused_at is None


def test_resume_active_raises(app, customer):
    sub = app.subs.create(customer.id, "basic")
    with pytest.raises(InvalidTransition):
        app.subs.resume(sub.id)


def test_cannot_pause_past_due():
    sub = Subscription("s1", "c1", "p1", status=PAST_DUE)
    with pytest.raises(InvalidTransition):
        sub.pause()


def test_transition_table_blocks_canceled_to_active():
    sub = Subscription("s1", "c1", "p1", status=CANCELED)
    with pytest.raises(InvalidTransition):
        sub.transition(ACTIVE)


def test_is_live():
    assert Subscription("s", "c", "p", status=PAST_DUE).is_live
    assert not Subscription("s", "c", "p", status=CANCELED).is_live


def test_change_plan_halfway_through_period(app, customer):
    sub = app.subs.create(customer.id, "basic", start=date(2023, 2, 1))
    result = app.subs.change_plan(sub.id, "pro", change_date=date(2023, 2, 15))
    assert str(result["ratio"]) == "0.50"
    assert str(result["credit"]) == "5.00"
    assert str(result["charge"]) == "15.00"
    assert str(result["net"]) == "10.00"
    assert sub.plan_id == "pro"


def test_change_plan_requires_active(app, customer):
    sub = app.subs.create(customer.id, "basic")
    app.subs.pause(sub.id)
    with pytest.raises(ValidationError):
        app.subs.change_plan(sub.id, "pro")


def test_change_plan_outside_period_rejected(app, customer, jan15):
    sub = app.subs.create(customer.id, "basic", start=jan15)
    with pytest.raises(ValidationError):
        app.subs.change_plan(sub.id, "pro", change_date=date(2024, 3, 1))


def test_change_plan_interval_switch_not_supported(app, customer):
    from billing.models.plan import Plan
    from decimal import Decimal
    app.plans.add(Plan("yearly", "Yearly", Decimal("10.00"), interval="year"))
    sub = app.subs.create(customer.id, "basic")
    with pytest.raises(ValidationError):
        app.subs.change_plan(sub.id, "yearly")


def test_due_for_renewal_filters_by_date_and_status(app, customer, jan15):
    a = app.subs.create(customer.id, "basic", start=jan15)
    b = app.subs.create(customer.id, "basic", start=date(2024, 1, 20))
    app.subs.cancel(b.id)
    assert app.subs.due_for_renewal(date(2024, 2, 14)) == []
    assert app.subs.due_for_renewal(date(2024, 2, 15)) == [a]


@pytest.mark.parametrize("start,expected_end", [
    (date(2024, 1, 10), date(2024, 2, 10)),
    (date(2024, 12, 31), date(2025, 1, 31)),
    (date(2024, 1, 31), date(2024, 2, 29)),
])
def test_first_period_end(app, customer, start, expected_end):
    assert app.subs.create(customer.id, "basic", start=start).current_period_end == expected_end


def test_yearly_plan_period(app, customer):
    from billing.models.plan import Plan
    from decimal import Decimal
    app.plans.add(Plan("yr", "Yearly", Decimal("10.00"), interval="year"))
    sub = app.subs.create(customer.id, "yr", start=date(2024, 3, 1))
    assert sub.current_period_end == date(2025, 3, 1)
