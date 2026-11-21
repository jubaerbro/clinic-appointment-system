"""Appointment tests - written BEFORE clinic/appointments.py (TDD).
The notifier is a MOCK, and "today" is fixed so the tests never go stale."""
from datetime import date
from unittest.mock import Mock

import pytest

from clinic.appointments import AppointmentService
from clinic.doctors import DoctorService
from clinic.errors import NotFoundError, ValidationError
from clinic.patients import PatientService

TODAY = date(2026, 11, 20)


@pytest.fixture
def setup(db):
    patients = PatientService(db)
    doctors = DoctorService(db)
    notifier = Mock()
    service = AppointmentService(db, patients, doctors, notifier, today=lambda: TODAY)
    patient = patients.add_patient("Rahim", "", "rahim@example.com", 40)
    doctor = doctors.add_doctor("Dr. Nasreen", "Cardiology", 800)
    return service, notifier, patient, doctor


def test_book_appointment_and_notify_patient(setup):
    service, notifier, patient, doctor = setup

    appt = service.book(patient["id"], doctor["id"], "2026-12-01", "10:00")

    assert appt["status"] == "booked"
    notifier.notify.assert_called_once()
    notified_patient, message = notifier.notify.call_args.args
    assert notified_patient["id"] == patient["id"]
    assert "2026-12-01" in message


def test_booking_today_is_allowed(setup):
    service, _, patient, doctor = setup
    assert service.book(patient["id"], doctor["id"], "2026-11-20", "09:00")["id"] == 1


@pytest.mark.parametrize("day, time, message", [
    ("2026-11-19", "10:00", "past"),
    ("01/12/2026", "10:00", "YYYY-MM-DD"),
    ("2026-12-01", "13:00", "time slots"),
])
def test_book_rejects_bad_date_or_time(setup, day, time, message):
    service, notifier, patient, doctor = setup
    with pytest.raises(ValidationError, match=message):
        service.book(patient["id"], doctor["id"], day, time)
    notifier.notify.assert_not_called()


def test_no_double_booking(setup):
    service, _, patient, doctor = setup
    service.book(patient["id"], doctor["id"], "2026-12-01", "10:00")
    with pytest.raises(ValidationError, match="already booked"):
        service.book(patient["id"], doctor["id"], "2026-12-01", "10:00")


def test_unknown_patient_or_doctor(setup):
    service, _, patient, doctor = setup
    with pytest.raises(NotFoundError):
        service.book(999, doctor["id"], "2026-12-01", "10:00")
    with pytest.raises(NotFoundError):
        service.book(patient["id"], 999, "2026-12-01", "10:00")


def test_cancel_notifies_patient(setup):
    service, notifier, patient, doctor = setup
    appt = service.book(patient["id"], doctor["id"], "2026-12-01", "10:00")

    assert service.cancel(appt["id"])["status"] == "cancelled"
    assert notifier.notify.call_count == 2
    assert "cancelled" in notifier.notify.call_args.args[1]


# ---- API and pages ----
def make_patient_and_doctor(client):
    client.post("/api/patients", json={"name": "Rahim", "age": 40})
    client.post("/api/doctors", json={"name": "Dr. A", "specialty": "ENT", "fee": 500})


def test_api_book_list_cancel(client):
    make_patient_and_doctor(client)
    r = client.post("/api/appointments",
                    json={"patient_id": 1, "doctor_id": 1, "date": "2099-01-01", "time": "09:00"})
    assert r.status_code == 201
    assert client.get("/api/appointments").get_json()[0]["doctor_name"] == "Dr. A"
    assert client.post("/api/appointments/1/cancel").get_json()["status"] == "cancelled"
    assert client.post("/api/appointments/9/cancel").status_code == 404


def test_appointments_page(client):
    make_patient_and_doctor(client)
    form = {"patient_id": "1", "doctor_id": "1", "date": "2099-01-01", "time": "09:00"}
    client.post("/appointments", data=form)
    assert b"already booked" in client.post("/appointments", data=form).data
    client.post("/appointments/1/cancel")
    assert b"cancelled" in client.get("/appointments").data
