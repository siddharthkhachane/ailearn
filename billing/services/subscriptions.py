from datetime import timedelta

from billing import clock
from billing.errors import ValidationError
from billing.models.subscription import (
    ACTIVE, TRIALING, Subscription,
)
from billing.repos.memory import MemoryRepo
from billing.services import proration
from billing.utils.dates import add_months
from billing.utils.misc import new_id


class SubscriptionService:
    def __init__(self, plans, customers, repo=None):
        self.plans = plans
        self.customers = customers
        self.repo = repo or MemoryRepo("subscription")

    def create(self, customer_id, plan_id, start=None, coupon_codes=None):
        plan = self.plans.get(plan_id)
        self.customers.get(customer_id)
        if not plan.active:
            raise ValidationError("plan %s is not available" % plan_id)
        start = start or clock.today()
        sub = Subscription(
            id=new_id("sub"),
            customer_id=customer_id,
            plan_id=plan_id,
            anchor_day=start.day,
            coupon_codes=list(coupon_codes or []),
            coupon_start=start,
            current_period_start=start,
        )
        if plan.trial_days:
            sub.status = TRIALING
            sub.trial_end = start + timedelta(days=plan.trial_days)
            sub.current_period_end = sub.trial_end
        else:
            sub.status = ACTIVE
            sub.current_period_end = add_months(start, plan.months)
        return self.repo.add(sub)

    def get(self, sub_id):
        return self.repo.get(sub_id)

    def renew(self, sub):
        plan = self.plans.get(sub.plan_id)
        sub.current_period_start = sub.current_period_end
        sub.current_period_end = add_months(sub.current_period_start, plan.months)
        return sub

    def activate_after_trial(self, sub):
        plan = self.plans.get(sub.plan_id)
        sub.transition(ACTIVE)
        sub.current_period_start = sub.trial_end
        sub.current_period_end = add_months(sub.current_period_start, plan.months)
        return sub

    def cancel(self, sub_id, at_period_end=False):
        sub = self.get(sub_id)
        if at_period_end:
            sub.cancel_at_period_end = True
        else:
            sub.cancel()
        return sub

    def pause(self, sub_id):
        sub = self.get(sub_id)
        sub.pause()
        return sub

    def resume(self, sub_id):
        sub = self.get(sub_id)
        sub.resume()
        return sub

    def change_plan(self, sub_id, new_plan_id, change_date=None):
        sub = self.get(sub_id)
        if sub.status != ACTIVE:
            raise ValidationError("can only change plan on an active subscription")
        old_plan = self.plans.get(sub.plan_id)
        new_plan = self.plans.get(new_plan_id)
        # TODO: annual <-> monthly switches (needs a proper period reset)
        if old_plan.interval != new_plan.interval:
            raise ValidationError("changing billing interval is not supported")
        change_date = change_date or clock.today()
        if not (sub.current_period_start <= change_date < sub.current_period_end):
            raise ValidationError("change date outside current period")
        ratio = proration.remaining_ratio(
            sub.current_period_start, sub.current_period_end, change_date)
        result = proration.prorate(
            old_plan.price_for_interval(), new_plan.price_for_interval(), ratio)
        sub.plan_id = new_plan.id
        return result

    def due_for_renewal(self, today):
        return [s for s in self.repo.all()
                if s.status in (ACTIVE, TRIALING) and s.current_period_end <= today]
