"""Patients module tests - written BEFORE clinic/patients.py (TDD: red -> green -> refactor)."""
from unittest.mock import Mock

import pytest

from clinic.errors import NotFoundError, ValidationError
from clinic.patients import PatientService


@pytest.fixture
def patients(db):
    return PatientService(db)


def test_add_patient_saves_and_returns_patient(patients):
    p = patients.add_patient("  Rahim Uddin ", "01711000000", "rahim@example.com", "45")
    assert p["id"] == 1
    assert p["name"] == "Rahim Uddin"  # spaces trimmed
    assert p["age"] == 45              # text converted to number


@pytest.mark.parametrize("name, age, email, message", [
    ("", 30, "", "Name is required"),
    ("Karim", "abc", "", "Age must be a whole number"),
    ("Karim", -1, "", "Age must be between 0 and 120"),
    ("Karim", 121, "", "Age must be between 0 and 120"),
    ("Karim", 30, "not-an-email", "Email address is not valid"),
])
def test_add_patient_rejects_bad_data(patients, name, age, email, message):
    with pytest.raises(ValidationError, match=message):
        patients.add_patient(name, "", email, age)


def test_get_unknown_patient_raises_not_found(patients):
    with pytest.raises(NotFoundError):
        patients.get_patient(999)


def test_list_patients_sorted_by_name(patients):
    patients.add_patient("Zara", "", "", 20)
    patients.add_patient("Abul", "", "", 30)
    assert [p["name"] for p in patients.list_patients()] == ["Abul", "Zara"]


def test_add_patient_with_mocked_database():
    """MOCK: isolate PatientService from SQLite completely.
    We only check that the service asks the database to do the right thing."""
    fake_db = Mock()
    fake_db.execute.return_value = 7
    fake_db.query_one.return_value = {"id": 7, "name": "Mina", "age": 9}

    result = PatientService(fake_db).add_patient("Mina", "", "", 9)

    sql, params = fake_db.execute.call_args.args
    assert sql.startswith("INSERT INTO patients")
    assert params == ("Mina", "", "", 9)
    assert result["id"] == 7


# ---- API (through Flask) ----
def test_api_create_and_get_patient(client):
    response = client.post("/api/patients", json={"name": "Rahim", "age": 40})
    assert response.status_code == 201
    patient_id = response.get_json()["id"]
    assert client.get(f"/api/patients/{patient_id}").get_json()["name"] == "Rahim"
    assert len(client.get("/api/patients").get_json()) == 1


def test_api_returns_400_and_404(client):
    assert client.post("/api/patients", json={"age": 40}).status_code == 400
    assert client.get("/api/patients/123").status_code == 404


def test_patients_page_shows_form_error(client):
    response = client.post("/patients", data={"name": "", "age": "20"})
    assert b"Name is required" in response.data
    client.post("/patients", data={"name": "Rahim", "age": "20"})
    assert b"Rahim" in client.get("/patients").data
