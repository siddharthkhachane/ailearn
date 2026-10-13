"""CSV export for the old accounting system.

Replaced by reporting.py in 2022. Delete once finance confirms nobody uses it.
Nothing imports this module any more.
"""
import csv


def export_invoices(invoices, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["number", "customer", "date", "net", "tax", "gross"])
        for inv in invoices:
            w.writerow([inv.number, inv.customerId, inv.issued, inv.netAmount, inv.taxAmount,
                        inv.grossAmount])


def export_line_items(invoices, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        for inv in invoices:
            for item in inv.lineItems:
                w.writerow([inv.number, item["desc"], item["qty"], item["price"]])
