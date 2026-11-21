"""Selenium UI test: drives a real (headless) Chrome browser through the whole
clinic flow, like a receptionist would.

Run only these:   pytest tests/ui
They are skipped automatically if Chrome is not installed.
"""
import os
import threading

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from werkzeug.serving import make_server

from app import create_app
from clinic.database import Database


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    """Start the real app on a free port in a background thread."""
    app = create_app(str(tmp_path_factory.mktemp("ui") / "ui.db"))
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    Database.reset()


@pytest.fixture(scope="module")
def browser():
    options = webdriver.ChromeOptions()
    for arg in ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1280,900"]:
        options.add_argument(arg)
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as error:  # no Chrome on this machine
        if os.environ.get("REQUIRE_BROWSER"):  # set in CI: there, a missing browser is a failure
            raise
        pytest.skip(f"Chrome not available: {error}")
    driver.implicitly_wait(3)
    yield driver
    driver.quit()


def fill(browser, element_id, text):
    box = browser.find_element(By.ID, element_id)
    box.clear()
    box.send_keys(text)


def test_full_clinic_flow(browser, base_url):
    # 1. Register a 70-year-old patient
    browser.get(base_url + "/patients")
    fill(browser, "patient-name", "Rahima Begum")
    fill(browser, "patient-email", "rahima@example.com")
    fill(browser, "patient-age", "70")
    browser.find_element(By.ID, "add-patient").click()
    assert "Rahima Begum" in browser.find_element(By.ID, "patients-table").text

    # 2. Add a doctor with a 1000 Tk fee
    browser.get(base_url + "/doctors")
    fill(browser, "doctor-name", "Dr. Nasreen Akter")
    fill(browser, "doctor-specialty", "Cardiology")
    fill(browser, "doctor-fee", "1000")
    browser.find_element(By.ID, "add-doctor").click()
    assert "Dr. Nasreen Akter" in browser.find_element(By.ID, "doctors-table").text

    # 3. Book an appointment
    browser.get(base_url + "/appointments")
    fill(browser, "appt-date", "2099-01-15")
    Select(browser.find_element(By.ID, "appt-time")).select_by_visible_text("10:00")
    browser.find_element(By.ID, "book-appointment").click()
    table = browser.find_element(By.ID, "appointments-table").text
    assert "2099-01-15" in table and "booked" in table

    # 4. Booking the same slot again shows an error
    fill(browser, "appt-date", "2099-01-15")
    Select(browser.find_element(By.ID, "appt-time")).select_by_visible_text("10:00")
    browser.find_element(By.ID, "book-appointment").click()
    assert "already booked" in browser.find_element(By.ID, "error").text

    # 5. Create the bill: senior gets 30% off -> 700.00
    browser.get(base_url + "/bills")
    browser.find_element(By.ID, "create-bill").click()
    bills = browser.find_element(By.ID, "bills-table").text
    assert "700.00" in bills and "unpaid" in bills

    # 6. Pay it (wait for the reloaded page, otherwise we might read the old one)
    browser.find_element(By.ID, "pay-1").click()
    WebDriverWait(browser, 5).until(
        EC.text_to_be_present_in_element((By.ID, "bill-status-1"), "paid"))
    assert browser.find_element(By.ID, "bill-status-1").text == "paid"

    # 7. The patient was notified about the booking
    browser.get(base_url + "/notifications")
    assert "booked for 2099-01-15" in browser.find_element(By.ID, "notifications-table").text

    # 8. Dashboard shows the counts
    browser.get(base_url + "/")
    assert browser.find_element(By.ID, "count-patients").text == "1"
    assert browser.find_element(By.ID, "count-unpaid").text == "0"


def test_swagger_docs_page_loads(browser, base_url):
    browser.get(base_url + "/apidocs/")
    assert "Clinic Appointment System API" in browser.find_element(By.TAG_NAME, "body").text
