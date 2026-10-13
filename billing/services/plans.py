from billing.errors import ValidationError
from billing.models.plan import Plan
from billing.repos.memory import MemoryRepo


class PlanCatalog:
    def __init__(self, repo=None):
        self.repo = repo or MemoryRepo("plan")

    def add(self, plan):
        if plan.monthly_price < 0:
            raise ValidationError("price cannot be negative")
        if plan.interval not in ("month", "year"):
            raise ValidationError("unknown interval: %s" % plan.interval)
        if not plan.name or not plan.name.strip():
            raise ValidationError("name cannot be empty")
        if plan.trial_days < 0:
            raise ValidationError("trial_days cannot be negative")
        if plan.included_units < 0:
            raise ValidationError("included_units cannot be negative")
        return self.repo.add(plan)

    def get(self, plan_id):
        return self.repo.get(plan_id)

    def list_active(self):
        return sorted(self.repo.find(lambda p: p.active), key=lambda p: p.monthly_price)

    def deactivate(self, plan_id):
        plan = self.get(plan_id)
        plan.active = False
        return plan

    def load_json(self, store, name="plans"):
        count = 0
        for raw in store.read(name, []):
            self.add(Plan.from_dict(raw))
            count += 1
        return count

    def save_json(self, store, name="plans"):
        store.write(name, [p.to_dict() for p in self.repo.all()])
