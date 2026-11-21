"""Tests for the app skeleton (dashboard and shared error handling)."""
from clinic.errors import NotFoundError, PaymentError, ValidationError


def test_dashboard_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_errors_carry_http_status_codes():
    assert ValidationError.status == 400
    assert NotFoundError.status == 404
    assert PaymentError.status == 402
