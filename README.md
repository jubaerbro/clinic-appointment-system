# Clinic Appointment System

A small web app for a neighbourhood clinic: register patients and doctors, book
appointments without double-booking, bill patients with age-based discounts,
take payment through a payment gateway, and notify patients by email.

Built for **CSE 3206 – Software Engineering Sessional (RUET)**, following the full SDLC.

## Features (5 modules)

| Module | What it does |
|---|---|
| Patients | Register patients (name, phone, email, age) with validation |
| Doctors | Add doctors with specialty and consultation fee |
| Appointments | Book / cancel; no past dates; fixed time slots; no double booking |
| Billing | Bill an appointment (senior 30% off, child 20% off) and pay via gateway |
| Notifications | Every booking/cancellation is saved and emailed to the patient |

Data is stored in a SQLite file (`clinic.db`), so it is kept between runs.

## Run it

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. API documentation (Swagger UI): http://127.0.0.1:5000/apidocs

## Run the tests

```bash
pytest                                              # all tests (Selenium needs Chrome)
pytest --ignore=tests/ui --cov=clinic --cov=app     # unit tests + coverage
pytest tests/ui -v                                  # Selenium browser tests only
```

GitHub Actions runs both on every push and pull request (`.github/workflows/ci.yml`).

## Project structure

```
app.py                  starts the app, plugs in all modules, serves Swagger UI
openapi.yaml            OpenAPI 3 description of the JSON API
clinic/
  database.py           SQLite access            - Singleton pattern
  patients.py           Module 1
  doctors.py            Module 2
  notifications.py      Module 3
  appointments.py       Module 4
  billing.py            Module 5                 - Strategy pattern (fees)
  payment.py            payment gateway          - Adapter pattern
  errors.py             shared error types
templates/              HTML pages
tests/                  pytest unit tests (mocks for DB, email and payment)
tests/ui/               Selenium end-to-end tests
```

Every module follows the same shape: a `Service` class with the business rules
(no web code, easy to unit test), a Flask `bp` (blueprint) with the page and
API routes, and a `setup(app)` function. **To add a feature**, write a new
module with that shape and add it to `MODULES` in `app.py`.

## Design patterns

| Pattern | Type | Where | Why |
|---|---|---|---|
| Singleton | Creational | `clinic/database.py` | One shared database connection for all modules |
| Adapter | Structural | `clinic/payment.py` | Wraps the third-party QuickPay SDK behind a simple `charge()` |
| Strategy | Behavioural | `clinic/billing.py` | Swappable fee rules (regular / senior / child) |

## Git workflow

* Branches: `feature/<module>` for features, `docs/<topic>` for documentation.
* Commits: [Conventional Commits](https://www.conventionalcommits.org) – `feat:`, `test:`, `fix:`, `docs:`, `chore:`.
* TDD: on each feature branch the `test:` commit (failing tests) comes before the `feat:` commit (code that makes them pass).
* Every change reaches `main` through a reviewed pull request with CI passing.

## Self-learned tool: Swagger / OpenAPI

`openapi.yaml` describes every API endpoint, its inputs, outputs and errors.
[flasgger](https://github.com/flasgger/flasgger) turns it into the interactive
page at `/apidocs`, where each endpoint can be tried from the browser.
`tests/test_api_docs.py` validates the file and fails the build if any `/api`
route in the code is missing from the documentation.

## Use of AI tools

Code and documentation were drafted with help from Claude (Anthropic), then
read, run, tested and adjusted by me. I can explain every part.
