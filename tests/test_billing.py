"""Billing tests - written BEFORE clinic/billing.py (TDD).
The payment gateway is a MOCK, so no real money and no network."""
from datetime import date
from unittest.mock import Mock

import pytest

from clinic.appointments import AppointmentService
from clinic.billing import (BillingService, ChildFee, FeeStrategy, RegularFee,
                            SeniorCitizenFee, choose_fee_strategy)
from clinic.doctors import DoctorService
from clinic.errors import NotFoundError, PaymentError, ValidationError
from clinic.patients import PatientService
from clinic.payment import PaymentResult


# ---- Strategy pattern ----
@pytest.mark.parametrize("strategy, expected", [
    (RegularFee(), 1000),
    (SeniorCitizenFee(), 700),
    (ChildFee(), 800),
])
def test_fee_strategies(strategy, expected):
    assert strategy.calculate(1000) == pytest.approx(expected)


@pytest.mark.parametrize("age, strategy_class", [
    (11, ChildFee), (12, RegularFee), (59, RegularFee), (60, SeniorCitizenFee),
])
def test_choose_fee_strategy_by_age(age, strategy_class):
    assert isinstance(choose_fee_strategy(age), strategy_class)


def test_base_strategy_must_be_overridden():
    with pytest.raises(NotImplementedError):
        FeeStrategy().calculate(100)


# ---- BillingService ----
@pytest.fixture
def billing(db):
    patients, doctors = PatientService(db), DoctorService(db)
    appointments = AppointmentService(db, patients, doctors, Mock(),
                                      today=lambda: date(2026, 11, 20))
    gateway = Mock()
    gateway.charge.return_value = PaymentResult(success=True, transaction_id="QP-TEST1")
    service = BillingService(db, appointments, gateway)

    senior = patients.add_patient("Old Man", "", "", 70)
    doctor = doctors.add_doctor("Dr. A", "ENT", 1000)
    appt = appointments.book(senior["id"], doctor["id"], "2026-12-01", "10:00")
    return service, gateway, appointments, appt


def test_create_bill_uses_senior_discount(billing):
    service, _, _, appt = billing
    bill = service.create_bill(appt["id"])
    assert bill["amount"] == 700
    assert bill["fee_type"] == "senior (30% off)"
    assert bill["status"] == "unpaid"


def test_cannot_bill_twice_or_bill_cancelled(billing):
    service, _, appointments, appt = billing
    service.create_bill(appt["id"])
    with pytest.raises(ValidationError, match="already has a bill"):
        service.create_bill(appt["id"])

    other = appointments.book(appt["patient_id"], appt["doctor_id"], "2026-12-02", "10:00")
    appointments.cancel(other["id"])
    with pytest.raises(ValidationError, match="cancelled"):
        service.create_bill(other["id"])


def test_pay_bill_charges_gateway(billing):
    service, gateway, _, appt = billing
    bill = service.create_bill(appt["id"])

    paid = service.pay(bill["id"])

    gateway.charge.assert_called_once_with(700)
    assert paid["status"] == "paid"
    assert paid["transaction_id"] == "QP-TEST1"


def test_declined_payment_keeps_bill_unpaid(billing):
    service, gateway, _, appt = billing
    gateway.charge.return_value = PaymentResult(success=False)
    bill = service.create_bill(appt["id"])

    with pytest.raises(PaymentError):
        service.pay(bill["id"])
    assert service.get_bill(bill["id"])["status"] == "unpaid"


def test_paid_bill_is_not_charged_again(billing):
    service, gateway, _, appt = billing
    bill = service.create_bill(appt["id"])
    service.pay(bill["id"])
    with pytest.raises(ValidationError, match="already paid"):
        service.pay(bill["id"])
    assert gateway.charge.call_count == 1


def test_unknown_bill(billing):
    with pytest.raises(NotFoundError):
        billing[0].pay(999)


# ---- API and pages ----
def book_one(client):
    client.post("/api/patients", json={"name": "Mina", "age": 8})
    client.post("/api/doctors", json={"name": "Dr. A", "specialty": "ENT", "fee": 500})
    client.post("/api/appointments",
                json={"patient_id": 1, "doctor_id": 1, "date": "2099-01-01", "time": "09:00"})


def test_api_bill_and_pay(client):
    book_one(client)
    bill = client.post("/api/bills", json={"appointment_id": 1}).get_json()
    assert bill["amount"] == 400  # child discount
    assert client.post("/api/bills/1/pay").get_json()["status"] == "paid"
    assert client.get("/api/bills").get_json()[0]["patient_name"] == "Mina"


def test_api_returns_402_when_gateway_declines(client):
    book_one(client)
    client.post("/api/bills", json={"appointment_id": 1})
    declining = Mock()
    declining.charge.return_value = PaymentResult(success=False)
    client.application.extensions["billing"].gateway = declining  # swap in a mock

    assert client.post("/api/bills/1/pay").status_code == 402


def test_bills_page(client):
    book_one(client)
    client.post("/bills", data={"appointment_id": "1"})
    assert b"already has a bill" in client.post("/bills", data={"appointment_id": "1"}).data
    client.post("/bills/1/pay")
    assert b"already paid" in client.post("/bills/1/pay").data
