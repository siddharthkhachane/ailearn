"""Plain-text email templates. Each returns (subject, body)."""
from billing.utils.misc import fmt_money


def invoice_ready(customer, invoice):
    subject = "Your invoice %s" % invoice.number
    body = "Hi %s,\n\nInvoice %s for %s is due on %s.\n" % (
        customer.name, invoice.number, fmt_money(invoice.total), invoice.due_date)
    return subject, body


def payment_failed(customer, invoice, next_retry=None):
    subject = "Payment failed for invoice %s" % invoice.number
    body = "Hi %s,\n\nWe could not charge %s.\n" % (customer.name, fmt_money(invoice.amount_due))
    if next_retry:
        body += "We will try again on %s.\n" % next_retry
    return subject, body


def refund_issued(customer, invoice, amount):
    subject = "Refund issued for invoice %s" % invoice.number
    body = "Hi %s,\n\nWe refunded %s to your card.\n" % (customer.name, fmt_money(amount))
    return subject, body


def subscription_canceled(customer):
    subject = "Your subscription has been canceled"
    body = "Hi %s,\n\nYour subscription is canceled. We hope to see you again.\n" % customer.name
    return subject, body
