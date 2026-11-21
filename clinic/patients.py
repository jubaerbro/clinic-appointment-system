"""Module 1: Patients - register patients and look them up."""
from flask import Blueprint, current_app, jsonify, redirect, render_template, request

from clinic.database import Database
from clinic.errors import ClinicError, NotFoundError, ValidationError


class PatientService:
    """All the rules about patients live here (no Flask code),
    so they can be unit-tested without a web server."""

    def __init__(self, db):
        self.db = db

    def add_patient(self, name, phone, email, age):
        name = (name or "").strip()
        email = (email or "").strip()
        if not name:
            raise ValidationError("Name is required")
        try:
            age = int(age)
        except (TypeError, ValueError):
            raise ValidationError("Age must be a whole number")
        if not 0 <= age <= 120:
            raise ValidationError("Age must be between 0 and 120")
        if email and "@" not in email:
            raise ValidationError("Email address is not valid")

        new_id = self.db.execute(
            "INSERT INTO patients (name, phone, email, age) VALUES (?, ?, ?, ?)",
            (name, (phone or "").strip(), email, age),
        )
        return self.get_patient(new_id)

    def get_patient(self, patient_id):
        patient = self.db.query_one("SELECT * FROM patients WHERE id = ?", (patient_id,))
        if patient is None:
            raise NotFoundError(f"Patient {patient_id} not found")
        return patient

    def list_patients(self):
        return self.db.query("SELECT * FROM patients ORDER BY name")


# ---------------- Web layer (Flask) ----------------
bp = Blueprint("patients", __name__)


def setup(app):
    app.extensions["patients"] = PatientService(Database())


def service():
    return current_app.extensions["patients"]


@bp.route("/patients", methods=["GET", "POST"])
def patients_page():
    error = None
    if request.method == "POST":
        try:
            service().add_patient(request.form.get("name"), request.form.get("phone"),
                                  request.form.get("email"), request.form.get("age"))
            return redirect("/patients")
        except ClinicError as e:
            error = str(e)
    return render_template("patients.html", patients=service().list_patients(), error=error)


@bp.get("/api/patients")
def api_list_patients():
    return jsonify(service().list_patients())


@bp.post("/api/patients")
def api_add_patient():
    data = request.get_json(silent=True) or {}
    patient = service().add_patient(data.get("name"), data.get("phone"),
                                    data.get("email"), data.get("age"))
    return jsonify(patient), 201


@bp.get("/api/patients/<int:patient_id>")
def api_get_patient(patient_id):
    return jsonify(service().get_patient(patient_id))
