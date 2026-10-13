from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

from billing import clock
from billing.errors import InvalidTransition

TRIALING = "trialing"
ACTIVE = "active"
PAST_DUE = "past_due"
PAUSED = "paused"
CANCELED = "canceled"

TRANSITIONS = {
    TRIALING: {ACTIVE, PAST_DUE, CANCELED},
    ACTIVE: {PAST_DUE, PAUSED, CANCELED},
    PAST_DUE: {ACTIVE, CANCELED},
    PAUSED: {ACTIVE, CANCELED},
    CANCELED: set(),
}


@dataclass
class Subscription:
    id: str
    customer_id: str
    plan_id: str
    status: str = ACTIVE
    current_period_start: Optional[date] = None
    current_period_end: Optional[date] = None
    anchor_day: int = 1
    trial_end: Optional[date] = None
    coupon_codes: List[str] = field(default_factory=list)
    coupon_start: Optional[date] = None
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None

    def transition(self, new_status):
        if new_status not in TRANSITIONS[self.status]:
            raise InvalidTransition("%s -> %s" % (self.status, new_status))
        self.status = new_status

    def pause(self):
        self.transition(PAUSED)
        self.paused_at = clock.now()

    def resume(self):
        if self.status == ACTIVE:
            raise InvalidTransition("subscription is already active")
        self.status = ACTIVE
        self.paused_at = None

    def cancel(self, now=None):
        self.transition(CANCELED)
        self.canceled_at = now or clock.now()

    @property
    def is_live(self):
        return self.status in (TRIALING, ACTIVE, PAST_DUE)
