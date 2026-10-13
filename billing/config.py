"""Service-wide settings.

Not everything lives here yet -- tax rates are in services/tax.py, retry
offsets in services/dunning.py, the refund window in services/refunds.py.
"""

DEFAULT_CURRENCY = "USD"
NET_TERMS_DAYS = 14
INVOICE_PREFIX = "INV"
DEFAULT_REGION = "US-CA"
DATA_DIR = "data"

# TODO(mk): feature flag for the new invoice numbering, never got wired up
USE_YEARLY_INVOICE_NUMBERS = True
