"""Sales tax / VAT by region.

TODO(mk): move the rate table into config or a JSON file
"""
from decimal import Decimal

from billing.money import ZERO, quantize

REGION_RATES = {
    "US-CA": Decimal("0.0725"),
    "US-NY": Decimal("0.08875"),
    "US-TX": Decimal("0.0625"),
    "US-OR": Decimal("0"),
    "DE": Decimal("0.19"),
    "FR": Decimal("0.20"),
    "GB": Decimal("0.20"),
    "JP": Decimal("0.10"),
}


def rate_for(region):
    return REGION_RATES.get((region or "").upper(), ZERO)


def tax_for_invoice(invoice, region):
    taxable = sum((l["amount"] for l in invoice._lines if l["taxable"]), ZERO)
    return quantize(max(taxable, ZERO) * rate_for(region))


def apply_tax(invoice, region):
    invoice.tax_total = tax_for_invoice(invoice, region)
    return invoice.tax_total
