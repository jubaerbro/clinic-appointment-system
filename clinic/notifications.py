"""Module 3: Notifications - tell patients when something happens.

Every message is saved in the database and also emailed if the patient
gave an email address. Email is an EXTERNAL dependency, so in tests it is
replaced by a mock (see tests/test_notifications.py).
"""
from flask import Blueprint, current_app, jsonify, render_template

from clinic.database import Database


class ConsoleEmailSender:
    """Stand-in for a real email service (SMTP, SendGrid, ...).
    It prints the email instead of sending it, so the demo works offline."""

    def send(self, to, subject, body):
        print(f"[EMAIL] to={to} subject={subject!r} body={body!r}")
        return True


class NotificationService:
    def __init__(self, db, email_sender):
        self.db = db
        self.email_sender = email_sender

    def notify(self, patient, message):
        """Save the message and try to email it.
        A failed email must NOT stop a booking, so errors are caught."""
        if not patient.get("email"):
            email_status = "no-email"
        else:
            try:
                self.email_sender.send(patient["email"], "Clinic update", message)
                email_status = "sent"
            except Exception:
                email_status = "failed"

        self.db.execute(
            "INSERT INTO notifications (patient_id, message, email_status) VALUES (?, ?, ?)",
            (patient["id"], message, email_status),
        )
        return email_status

    def list_notifications(self):
        return self.db.query(
            "SELECT n.*, p.name AS patient_name FROM notifications n "
            "JOIN patients p ON p.id = n.patient_id ORDER BY n.id DESC"
        )


# ---------------- Web layer (Flask) ----------------
bp = Blueprint("notifications", __name__)


def setup(app):
    app.extensions["notifications"] = NotificationService(Database(), ConsoleEmailSender())


def service():
    return current_app.extensions["notifications"]


@bp.get("/notifications")
def notifications_page():
    return render_template("notifications.html", notifications=service().list_notifications())


@bp.get("/api/notifications")
def api_list_notifications():
    return jsonify(service().list_notifications())
