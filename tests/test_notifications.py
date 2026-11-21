"""Notifications tests - the email service is MOCKED so no real email is sent."""
from unittest.mock import Mock

import pytest

from clinic.notifications import ConsoleEmailSender, NotificationService
from clinic.patients import PatientService


@pytest.fixture
def patient(db):
    return PatientService(db).add_patient("Rahim", "", "rahim@example.com", 40)


def test_notify_sends_email_and_saves_message(db, patient):
    email = Mock()
    service = NotificationService(db, email)

    status = service.notify(patient, "Hello")

    email.send.assert_called_once_with("rahim@example.com", "Clinic update", "Hello")
    assert status == "sent"
    assert service.list_notifications()[0]["message"] == "Hello"


def test_email_failure_does_not_crash(db, patient):
    email = Mock()
    email.send.side_effect = ConnectionError("SMTP server down")  # simulate outage

    status = NotificationService(db, email).notify(patient, "Hello")

    assert status == "failed"  # saved, but marked as failed


def test_patient_without_email_is_not_emailed(db):
    no_email = PatientService(db).add_patient("Karim", "", "", 30)
    email = Mock()

    status = NotificationService(db, email).notify(no_email, "Hello")

    email.send.assert_not_called()
    assert status == "no-email"


def test_console_sender_prints(capsys):
    assert ConsoleEmailSender().send("a@b.com", "Hi", "Body") is True
    assert "a@b.com" in capsys.readouterr().out


def test_notifications_page_and_api(client):
    assert client.get("/api/notifications").get_json() == []
    assert b"No notifications yet" in client.get("/notifications").data
