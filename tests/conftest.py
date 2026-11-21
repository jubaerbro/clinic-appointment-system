"""Shared test fixtures (pytest runs this file automatically)."""
import pytest

from clinic.database import Database


@pytest.fixture
def db():
    """A brand-new, empty in-memory database for each test.
    Nothing touches the real clinic.db file."""
    Database.reset()
    database = Database(":memory:")
    yield database
    Database.reset()


@pytest.fixture
def client(tmp_path):
    """A Flask test client: lets tests call the web app without a browser."""
    from app import create_app
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    yield app.test_client()
    Database.reset()
