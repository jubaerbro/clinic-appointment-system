"""Database access - uses the SINGLETON pattern (creational).

Problem it solves:
    Every module (patients, doctors, billing, ...) needs to talk to the same
    SQLite file. If each module opened its own connection we could get
    "database is locked" errors and wasted resources.

How:
    Database() always returns the SAME object. The first call creates the
    connection; every later call just gives back that existing object.

Rejected alternative:
    A global variable `db = sqlite3.connect(...)` at the top of a file.
    It is simpler, but any code can overwrite it, and tests cannot easily
    swap it for a fresh database. The singleton has a reset() for that.
"""
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    phone   TEXT,
    email   TEXT,
    age     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS doctors (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL,
    specialty TEXT NOT NULL,
    fee       REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS appointments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    doctor_id  INTEGER NOT NULL REFERENCES doctors(id),
    date       TEXT NOT NULL,
    time       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'booked'
);
CREATE TABLE IF NOT EXISTS bills (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointments(id),
    amount         REAL NOT NULL,
    fee_type       TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'unpaid',
    transaction_id TEXT
);
CREATE TABLE IF NOT EXISTS notifications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id   INTEGER NOT NULL REFERENCES patients(id),
    message      TEXT NOT NULL,
    email_status TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class Database:
    _instance = None  # the one and only Database object

    def __new__(cls, path="clinic.db"):
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._connect(path)
            cls._instance = instance
        return cls._instance

    def _connect(self, path):
        self.path = path
        # check_same_thread=False lets the web server's threads share it;
        # the lock makes sure only one thread uses it at a time.
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # rows behave like dicts
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript(SCHEMA)
        self.lock = threading.Lock()

    @classmethod
    def reset(cls):
        """Close the connection and forget the instance (used by tests)."""
        if cls._instance is not None:
            cls._instance.connection.close()
        cls._instance = None

    def execute(self, sql, params=()):
        """Run INSERT/UPDATE/DELETE. Returns the id of the new row."""
        with self.lock:
            cursor = self.connection.execute(sql, params)
            self.connection.commit()
            return cursor.lastrowid

    def query(self, sql, params=()):
        """Run SELECT. Returns a list of dicts."""
        with self.lock:
            rows = self.connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def query_one(self, sql, params=()):
        """Run SELECT for one row. Returns a dict or None."""
        rows = self.query(sql, params)
        return rows[0] if rows else None
