"""Tests for the Singleton database."""
from clinic.database import Database


def test_database_is_a_singleton(db):
    assert Database() is db
    assert Database("some/other/path.db") is db  # path is ignored once created


def test_reset_creates_a_new_instance(db):
    Database.reset()
    new_db = Database(":memory:")
    assert new_db is not db
    Database.reset()


def test_execute_returns_new_id_and_query_returns_dicts(db):
    new_id = db.execute("INSERT INTO doctors (name, specialty, fee) VALUES (?, ?, ?)",
                        ("Dr. A", "ENT", 500))
    assert new_id == 1
    assert db.query("SELECT name FROM doctors") == [{"name": "Dr. A"}]


def test_query_one_returns_none_when_nothing_found(db):
    assert db.query_one("SELECT * FROM patients WHERE id = 99") is None
