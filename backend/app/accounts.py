"""SQLite accounts, short-lived login proofs and opaque sessions."""
from contextlib import contextmanager
import sqlite3
from threading import Lock


class AccountStore:
    def __init__(self, path):
        self.path = path
        self._lock = Lock()
        self._initialized = False

    @contextmanager
    def connect(self, *, write: bool = False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys = ON')
            if not self._initialized:
                with self._lock:
                    if not self._initialized:
                        self._initialize(db)
                        self._initialized = True
            with db:
                if write:
                    db.execute('BEGIN IMMEDIATE')
                yield db
        finally:
            db.close()

    @staticmethod
    def _initialize(db):
        db.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                google_sub TEXT UNIQUE,
                display_name TEXT NOT NULL DEFAULT '',
                photo TEXT,
                course TEXT NOT NULL DEFAULT '',
                semester INTEGER,
                goal TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                digest TEXT PRIMARY KEY,
                account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                expires_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS auth_sessions_expiry ON auth_sessions(expires_at);
            CREATE TABLE IF NOT EXISTS auth_codes (
                email TEXT NOT NULL,
                scope TEXT NOT NULL,
                digest TEXT NOT NULL,
                issued_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                remaining INTEGER NOT NULL DEFAULT 5,
                PRIMARY KEY (email, scope)
            );
            CREATE INDEX IF NOT EXISTS auth_codes_issued ON auth_codes(issued_at);
            CREATE TABLE IF NOT EXISTS auth_google_proofs (
                digest TEXT PRIMARY KEY,
                nonce TEXT,
                google_sub TEXT,
                email TEXT,
                expires_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS auth_google_expiry ON auth_google_proofs(expires_at);
        """)
