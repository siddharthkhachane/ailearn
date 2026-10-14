from billing.errors import ValidationError
from billing.models.customer import Customer
from billing.repos.memory import MemoryRepo
from billing.utils.misc import new_id


class CustomerService:
    def __init__(self, repo=None):
        self.repo = repo or MemoryRepo("customer")

    def create(self, name, email, region="US-CA", payment_token=None, timezone="UTC"):
        if not name or not name.strip():
            raise ValidationError("name is required")
        # TODO: real email validation (regex? verification mail?)
        if "@" not in email:
            raise ValidationError("invalid email: %s" % email)
        if self.find_by_email(email):
            raise ValidationError("email already registered")
        customer = Customer(new_id("cus"), name.strip(), email.strip().lower(), region,
                            timezone, payment_token)
        return self.repo.add(customer)

    def get(self, customer_id):
        return self.repo.get(customer_id)

    def find_by_email(self, email):
        wanted = email.strip().lower()
        for c in self.repo.all():
            if c.email == wanted:
                return c
        return None

    def set_region(self, customer_id, region):
        customer = self.get(customer_id)
        customer.region = region
        return customer

    def add_credit(self, customer_id, amount):
        return self.get(customer_id).add_credit(amount)

    def list_page(self, page=1, per_page=20):
        customers = sorted(self.repo.all(), key=lambda c: c.id)
        start = (page - 1) * per_page
        return customers[start:start + per_page]
