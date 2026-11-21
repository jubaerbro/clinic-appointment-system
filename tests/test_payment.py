"""Adapter tests - the third-party QuickPay SDK is MOCKED (no network)."""
from unittest.mock import Mock

from clinic.payment import QuickPayAdapter, QuickPayClient


def test_adapter_converts_taka_to_paisa():
    sdk = Mock()
    sdk.make_transaction.return_value = {"status": "APPROVED", "txn_ref": "QP-1"}

    result = QuickPayAdapter(sdk).charge(560.50)

    sdk.make_transaction.assert_called_once_with(56050, "BDT")
    assert result.success is True
    assert result.transaction_id == "QP-1"


def test_adapter_reports_declined_payment():
    sdk = Mock()
    sdk.make_transaction.return_value = {"status": "DECLINED"}

    result = QuickPayAdapter(sdk).charge(100)

    assert result.success is False
    assert result.transaction_id is None


def test_default_client_is_the_offline_simulator():
    result = QuickPayAdapter().charge(100)
    assert result.success and result.transaction_id.startswith("QP-")
    assert isinstance(QuickPayAdapter().client, QuickPayClient)
