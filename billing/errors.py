class BillingError(Exception):
    """Base class for everything we raise on purpose."""


class ValidationError(BillingError):
    pass


class NotFound(BillingError):
    pass


class InvalidTransition(BillingError):
    pass


class PaymentError(BillingError):
    pass


class CouponError(BillingError):
    pass


class RefundError(BillingError):
    pass
