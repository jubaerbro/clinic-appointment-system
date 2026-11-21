"""Module 5: Billing - create a bill for an appointment and take payment.

Fee calculation uses the STRATEGY pattern (behavioural).

Problem it solves:
    Different patients pay different fees: seniors (60+) get 30% off,
    children (under 12) get 20% off, everyone else pays the full fee.
    New discount types (e.g. students) will be added later.

How:
    Each rule is its own small class with a calculate() method.
    choose_fee_strategy() picks the right class for the patient, and
    BillingService just calls strategy.calculate(fee) without caring which one.

Rejected alternative:
    One big if/elif block inside create_bill(). It works for three rules but
    every new rule means editing (and re-testing) the billing code itself.
"""
from flask import Blueprint, current_app, jsonify, redirect, render_template, request

from clinic.database import Database
from clinic.errors import ClinicError, NotFoundError, PaymentError, ValidationError
from clinic.payment import QuickPayAdapter


# ---------------- Strategy pattern ----------------
class FeeStrategy:
    name = "base"

    def calculate(self, base_fee):
        raise NotImplementedError


class RegularFee(FeeStrategy):
    name = "regular"

    def calculate(self, base_fee):
        return base_fee


class SeniorCitizenFee(FeeStrategy):
    name = "senior (30% off)"

    def calculate(self, base_fee):
        return base_fee * 0.50


class ChildFee(FeeStrategy):
    name = "child (20% off)"

    def calculate(self, base_fee):
        return base_fee * 0.80


def choose_fee_strategy(age):
    if age >= 60:
        return SeniorCitizenFee()
    if age < 12:
        return ChildFee()
    return RegularFee()


# ---------------- Billing service ----------------
class BillingService:
    def __init__(self, db, appointments, gateway):
        self.db = db
        self.appointments = appointments  # AppointmentService
        self.gateway = gateway            # anything with charge(amount) -> PaymentResult

    def create_bill(self, appointment_id):
        appointment = self.appointments.get_appointment(appointment_id)
        if appointment["status"] == "cancelled":
            raise ValidationError("Cannot bill a cancelled appointment")
        if self.db.query_one("SELECT id FROM bills WHERE appointment_id = ?", (appointment_id,)):
            raise ValidationError("This appointment already has a bill")

        patient = self.appointments.patients.get_patient(appointment["patient_id"])
        doctor = self.appointments.doctors.get_doctor(appointment["doctor_id"])
        strategy = choose_fee_strategy(patient["age"])
        amount = round(strategy.calculate(doctor["fee"]), 2)

        new_id = self.db.execute(
            "INSERT INTO bills (appointment_id, amount, fee_type) VALUES (?, ?, ?)",
            (appointment_id, amount, strategy.name),
        )
        return self.get_bill(new_id)

    def pay(self, bill_id):
        bill = self.get_bill(bill_id)
        if bill["status"] == "paid":
            raise ValidationError("Bill is already paid")
        result = self.gateway.charge(bill["amount"])
        if not result.success:
            raise PaymentError("Payment was declined by the gateway")
        self.db.execute("UPDATE bills SET status = 'paid', transaction_id = ? WHERE id = ?",
                        (result.transaction_id, bill_id))
        return self.get_bill(bill_id)

    def get_bill(self, bill_id):
        bill = self.db.query_one("SELECT * FROM bills WHERE id = ?", (bill_id,))
        if bill is None:
            raise NotFoundError(f"Bill {bill_id} not found")
        return bill

    def list_bills(self):
        return self.db.query(
            "SELECT b.*, p.name AS patient_name, d.name AS doctor_name, a.date, a.time "
            "FROM bills b JOIN appointments a ON a.id = b.appointment_id "
            "JOIN patients p ON p.id = a.patient_id JOIN doctors d ON d.id = a.doctor_id "
            "ORDER BY b.id DESC"
        )

    def unbilled_appointments(self):
        return self.db.query(
            "SELECT a.*, p.name AS patient_name, d.name AS doctor_name FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id JOIN doctors d ON d.id = a.doctor_id "
            "WHERE a.status = 'booked' AND a.id NOT IN (SELECT appointment_id FROM bills) "
            "ORDER BY a.date, a.time"
        )


# ---------------- Web layer (Flask) ----------------
bp = Blueprint("billing", __name__)


def setup(app):
    app.extensions["billing"] = BillingService(
        Database(), app.extensions["appointments"], QuickPayAdapter()
    )


def service():
    return current_app.extensions["billing"]


def render_bills(error=None):
    return render_template("bills.html", bills=service().list_bills(),
                           unbilled=service().unbilled_appointments(), error=error)


@bp.get("/bills")
def bills_page():
    return render_bills()


@bp.post("/bills")
def create_bill_page():
    try:
        service().create_bill(request.form.get("appointment_id", type=int))
    except ClinicError as e:
        return render_bills(str(e))
    return redirect("/bills")


@bp.post("/bills/<int:bill_id>/pay")
def pay_page(bill_id):
    try:
        service().pay(bill_id)
    except ClinicError as e:
        return render_bills(str(e))
    return redirect("/bills")


@bp.get("/api/bills")
def api_list_bills():
    return jsonify(service().list_bills())


@bp.post("/api/bills")
def api_create_bill():
    data = request.get_json(silent=True) or {}
    return jsonify(service().create_bill(data.get("appointment_id"))), 201


@bp.post("/api/bills/<int:bill_id>/pay")
def api_pay(bill_id):
    return jsonify(service().pay(bill_id))
