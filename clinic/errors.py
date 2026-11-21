"""Errors used by every module.

Each error carries the HTTP status code the API should return,
so app.py can turn any of them into a JSON response in one place.
"""


class ClinicError(Exception):
    """Base class for all errors in this app."""
    status = 400


class ValidationError(ClinicError):
    """The user sent bad data (empty name, negative fee, ...)."""
    status = 400


class NotFoundError(ClinicError):
    """The requested patient/doctor/appointment/bill does not exist."""
    status = 404


class PaymentError(ClinicError):
    """The payment gateway declined the payment."""
    status = 402
