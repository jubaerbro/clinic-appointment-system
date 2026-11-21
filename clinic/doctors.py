"""Module 2: Doctors - add doctors with their specialty and consultation fee."""
from flask import Blueprint, current_app, jsonify, redirect, render_template, request

from clinic.database import Database
from clinic.errors import ClinicError, NotFoundError, ValidationError


class DoctorService:
    def __init__(self, db):
        self.db = db

    def add_doctor(self, name, specialty, fee):
        name = (name or "").strip()
        specialty = (specialty or "").strip()
        if not name:
            raise ValidationError("Name is required")
        if not specialty:
            raise ValidationError("Specialty is required")
        try:
            fee = float(fee)
        except (TypeError, ValueError):
            raise ValidationError("Fee must be a number")
        if fee <= 0:
            raise ValidationError("Fee must be more than 0")

        new_id = self.db.execute(
            "INSERT INTO doctors (name, specialty, fee) VALUES (?, ?, ?)",
            (name, specialty, fee),
        )
        return self.get_doctor(new_id)

    def get_doctor(self, doctor_id):
        doctor = self.db.query_one("SELECT * FROM doctors WHERE id = ?", (doctor_id,))
        if doctor is None:
            raise NotFoundError(f"Doctor {doctor_id} not found")
        return doctor

    def list_doctors(self):
        return self.db.query("SELECT * FROM doctors ORDER BY name")


# ---------------- Web layer (Flask) ----------------
bp = Blueprint("doctors", __name__)


def setup(app):
    app.extensions["doctors"] = DoctorService(Database())


def service():
    return current_app.extensions["doctors"]


@bp.route("/doctors", methods=["GET", "POST"])
def doctors_page():
    error = None
    if request.method == "POST":
        try:
            service().add_doctor(request.form.get("name"), request.form.get("specialty"),
                                 request.form.get("fee"))
            return redirect("/doctors")
        except ClinicError as e:
            error = str(e)
    return render_template("doctors.html", doctors=service().list_doctors(), error=error)


@bp.get("/api/doctors")
def api_list_doctors():
    return jsonify(service().list_doctors())


@bp.post("/api/doctors")
def api_add_doctor():
    data = request.get_json(silent=True) or {}
    doctor = service().add_doctor(data.get("name"), data.get("specialty"), data.get("fee"))
    return jsonify(doctor), 201
