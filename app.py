"""Clinic Appointment System - start here.

Run the app:   python app.py      then open http://127.0.0.1:5000
"""
import os

from flask import Flask, jsonify, render_template

from clinic.database import Database
from clinic.errors import ClinicError
from clinic import patients
from clinic import doctors
from clinic import notifications
from clinic import appointments

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Every feature module plugs in here. To add a new feature, write a module
# with `bp` and `setup(app)` and add it to this list.
# Order matters: appointments needs patients, doctors and notifications;
# billing needs appointments.
MODULES = [
    patients,
    doctors,
    notifications,
    appointments,
]


def create_app(db_path=None):
    app = Flask(__name__)

    # Singleton: this first call opens the database; every module's later
    # Database() call gets this same object back.
    Database.reset()
    db = Database(db_path or os.environ.get("CLINIC_DB", os.path.join(BASE_DIR, "clinic.db")))

    for module in MODULES:
        module.setup(app)
        app.register_blueprint(module.bp)

    # Any ClinicError raised by an API route becomes a JSON error response.
    @app.errorhandler(ClinicError)
    def handle_clinic_error(error):
        return jsonify(error=str(error)), error.status

    @app.get("/")
    def home():
        counts = {
            "patients": db.query_one("SELECT COUNT(*) AS n FROM patients")["n"],
            "doctors": db.query_one("SELECT COUNT(*) AS n FROM doctors")["n"],
            "appointments": db.query_one(
                "SELECT COUNT(*) AS n FROM appointments WHERE status = 'booked'")["n"],
            "unpaid_bills": db.query_one(
                "SELECT COUNT(*) AS n FROM bills WHERE status = 'unpaid'")["n"],
        }
        return render_template("index.html", counts=counts)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
