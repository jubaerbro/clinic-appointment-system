"""Module 4: Appointments - book and cancel appointments.

Rules:
  * patient and doctor must exist
  * date must be YYYY-MM-DD and not in the past
  * time must be one of the clinic's slots
  * a doctor cannot have two bookings in the same slot (no double booking)
  * the patient gets a notification when booking or cancelling
"""
from datetime import date

from flask import Blueprint, current_app, jsonify, redirect, render_template, request

from clinic.database import Database
from clinic.errors import ClinicError, NotFoundError, ValidationError

SLOTS = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
         "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"]


class AppointmentService:
    def __init__(self, db, patients, doctors, notifier, today=date.today):
        self.db = db
        self.patients = patients
        self.doctors = doctors
        self.notifier = notifier
        self.today = today  # passed in so tests can fix "today" to a known date

    def book(self, patient_id, doctor_id, day, time):
        patient = self.patients.get_patient(patient_id)
        doctor = self.doctors.get_doctor(doctor_id)

        try:
            booking_date = date.fromisoformat(day or "")
        except ValueError:
            raise ValidationError("Date must look like YYYY-MM-DD")
        if booking_date < self.today():
            raise ValidationError("Cannot book a date in the past")
        if time not in SLOTS:
            raise ValidationError("Please choose one of the clinic's time slots")

        clash = self.db.query_one(
            "SELECT id FROM appointments WHERE doctor_id = ? AND date = ? AND time = ? "
            "AND status = 'booked'",
            (doctor["id"], booking_date.isoformat(), time),
        )
        if clash:
            raise ValidationError("This doctor is already booked at that time")

        new_id = self.db.execute(
            "INSERT INTO appointments (patient_id, doctor_id, date, time) VALUES (?, ?, ?, ?)",
            (patient["id"], doctor["id"], booking_date.isoformat(), time),
        )
        self.notifier.notify(
            patient, f"Your appointment with {doctor['name']} is booked for {booking_date} at {time}."
        )
        return self.get_appointment(new_id)

    def cancel(self, appointment_id):
        appointment = self.get_appointment(appointment_id)
        if appointment["status"] == "cancelled":
            raise ValidationError("Appointment is already cancelled")
        self.db.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?",
                        (appointment_id,))
        patient = self.patients.get_patient(appointment["patient_id"])
        self.notifier.notify(
            patient, f"Your appointment on {appointment['date']} at {appointment['time']} was cancelled."
        )
        return self.get_appointment(appointment_id)

    def get_appointment(self, appointment_id):
        appointment = self.db.query_one("SELECT * FROM appointments WHERE id = ?",
                                        (appointment_id,))
        if appointment is None:
            raise NotFoundError(f"Appointment {appointment_id} not found")
        return appointment

    def list_appointments(self):
        return self.db.query(
            "SELECT a.*, p.name AS patient_name, d.name AS doctor_name "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "ORDER BY a.date, a.time"
        )


# ---------------- Web layer (Flask) ----------------
bp = Blueprint("appointments", __name__)


def setup(app):
    app.extensions["appointments"] = AppointmentService(
        Database(),
        app.extensions["patients"],
        app.extensions["doctors"],
        app.extensions["notifications"],
    )


def service():
    return current_app.extensions["appointments"]


@bp.route("/appointments", methods=["GET", "POST"])
def appointments_page():
    error = None
    if request.method == "POST":
        try:
            service().book(request.form.get("patient_id", type=int),
                           request.form.get("doctor_id", type=int),
                           request.form.get("date"), request.form.get("time"))
            return redirect("/appointments")
        except ClinicError as e:
            error = str(e)
    return render_template(
        "appointments.html",
        appointments=service().list_appointments(),
        patients=service().patients.list_patients(),
        doctors=service().doctors.list_doctors(),
        slots=SLOTS,
        error=error,
    )


@bp.post("/appointments/<int:appointment_id>/cancel")
def cancel_page(appointment_id):
    service().cancel(appointment_id)
    return redirect("/appointments")


@bp.get("/api/appointments")
def api_list_appointments():
    return jsonify(service().list_appointments())


@bp.post("/api/appointments")
def api_book():
    data = request.get_json(silent=True) or {}
    appointment = service().book(data.get("patient_id"), data.get("doctor_id"),
                                 data.get("date"), data.get("time"))
    return jsonify(appointment), 201


@bp.post("/api/appointments/<int:appointment_id>/cancel")
def api_cancel(appointment_id):
    return jsonify(service().cancel(appointment_id))
