"""Doctors module tests - written BEFORE clinic/doctors.py (TDD)."""
import pytest

from clinic.doctors import DoctorService
from clinic.errors import NotFoundError, ValidationError


@pytest.fixture
def doctors(db):
    return DoctorService(db)


def test_add_doctor(doctors):
    d = doctors.add_doctor("Dr. Nasreen", "Cardiology", "800")
    assert d["fee"] == 800.0
    assert doctors.get_doctor(d["id"])["specialty"] == "Cardiology"


@pytest.mark.parametrize("name, specialty, fee, message", [
    ("", "ENT", 500, "Name is required"),
    ("Dr. A", "", 500, "Specialty is required"),
    ("Dr. A", "ENT", "free", "Fee must be a number"),
    ("Dr. A", "ENT", 0, "Fee must be more than 0"),
])
def test_add_doctor_rejects_bad_data(doctors, name, specialty, fee, message):
    with pytest.raises(ValidationError, match=message):
        doctors.add_doctor(name, specialty, fee)


def test_unknown_doctor(doctors):
    with pytest.raises(NotFoundError):
        doctors.get_doctor(42)


def test_api_doctors(client):
    assert client.post("/api/doctors", json={"name": "Dr. A", "specialty": "ENT",
                                             "fee": 500}).status_code == 201
    assert client.post("/api/doctors", json={"name": "Dr. B"}).status_code == 400
    assert client.get("/api/doctors").get_json()[0]["name"] == "Dr. A"


def test_doctors_page(client):
    assert b"Fee must be more than 0" in client.post(
        "/doctors", data={"name": "Dr. A", "specialty": "ENT", "fee": "0"}).data
    client.post("/doctors", data={"name": "Dr. A", "specialty": "ENT", "fee": "500"})
    assert b"Dr. A" in client.get("/doctors").data
