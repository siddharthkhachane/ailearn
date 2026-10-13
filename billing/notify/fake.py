from billing.notify.base import EmailSender


class FakeEmailSender(EmailSender):
    def __init__(self):
        self.outbox = []

    def send(self, to, subject, body):
        self.outbox.append({"to": to, "subject": subject, "body": body})

    def sent_to(self, address):
        return [m for m in self.outbox if m["to"] == address]
