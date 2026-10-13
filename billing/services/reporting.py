"""Quick finance reports. Floats are fine here, these are for dashboards only."""
from collections import defaultdict


def mrr(subscriptions, plans):
    total = 0.0
    for s in subscriptions:
        if s.status not in ("active", "past_due"):
            continue
        plan = plans.get(s.plan_id)
        monthly = float(plan.monthly_price)
        if plan.interval == "year":
            monthly = float(plan.annual_price()) / 12
        total += monthly
    return round(total, 2)


def revenue_by_region(invoices, customers):
    out = defaultdict(float)
    for inv in invoices:
        if inv.status not in ("paid", "partially_refunded", "refunded"):
            continue
        region = customers.get(inv.customer_id).region
        out[region] += float(inv.amount_paid - inv.refunded_total)
    return dict(out)


def top_customers(invoices, n=5):
    spend = defaultdict(float)
    for inv in invoices:
        spend[inv.customer_id] += float(inv.amount_paid)
    ranked = sorted(spend.items(), key=lambda kv: kv[1], reverse=True)
    return ranked[:n]


def churn_rate(subscriptions, since):
    started = [s for s in subscriptions if s.current_period_start and s.current_period_start <= since]
    if not started:
        return 0.0
    canceled = [s for s in started if s.canceled_at and s.canceled_at.date() >= since]
    return len(canceled) / len(started)


def ar_aging(invoices, as_of):
    """Open invoices bucketed by days past due."""
    buckets = {"current": 0.0, "1-30": 0.0, "31-60": 0.0, "60+": 0.0}
    for inv in invoices:
        if inv.status != "open":
            continue
        days = (as_of - inv.due_date).days
        due = float(inv.amount_due)
        if days <= 0:
            buckets["current"] += due
        elif days <= 30:
            buckets["1-30"] += due
        elif days <= 60:
            buckets["31-60"] += due
        else:
            buckets["60+"] += due
    return buckets


def plan_mix(subscriptions):
    counts = defaultdict(int)
    for s in subscriptions:
        if s.status in ("active", "past_due", "trialing"):
            counts[s.plan_id] += 1
    total = sum(counts.values()) or 1
    return {plan_id: round(100.0 * n / total, 1) for plan_id, n in counts.items()}


def refund_rate(invoices):
    paid = [i for i in invoices if i.amount_paid > 0]
    if not paid:
        return 0.0
    refunded = [i for i in paid if i.refunded_total > 0]
    return round(len(refunded) / len(paid), 4)
