"""Payment gateway - uses the ADAPTER pattern (structural).

Problem it solves:
    We want to use a third-party payment company ("QuickPay" here). Its SDK
    works in paisa (1 taka = 100 paisa) and returns a dictionary. Our billing
    code wants something simpler: charge(amount_in_taka) -> PaymentResult.

How:
    QuickPayAdapter sits in the middle and translates between the two.
    If the clinic later switches to bKash or Stripe, we only write a new
    adapter; BillingService does not change at all.

Rejected alternative:
    Calling QuickPayClient directly inside BillingService. That ties the
    billing rules to one company's SDK and makes the code harder to test.
"""
import uuid
from dataclasses import dataclass


@dataclass
class PaymentResult:
    success: bool
    transaction_id: str = None


class QuickPayClient:
    """Pretend third-party SDK. In real life this would call QuickPay's servers
    over the internet. Here it always approves, so the demo works offline."""

    def make_transaction(self, amount_paisa, currency):
        return {"status": "APPROVED", "txn_ref": "QP-" + uuid.uuid4().hex[:8].upper()}


class QuickPayAdapter:
    """Gives QuickPayClient the simple interface our app expects."""

    def __init__(self, client=None):
        self.client = client or QuickPayClient()

    def charge(self, amount_taka):
        amount_paisa = int(round(amount_taka * 100))
        response = self.client.make_transaction(amount_paisa, "BDT")
        if response.get("status") == "APPROVED":
            return PaymentResult(success=True, transaction_id=response.get("txn_ref"))
        return PaymentResult(success=False)
