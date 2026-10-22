"""
Per-user API keys in SQLite at DATA_DIR / "app.db".

Only the SHA-256 hex digest of a key is stored. The plaintext is returned
once by create_key() and can't be recovered afterwards.
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone

from src.config import DATA_DIR

DB_PATH = DATA_DIR / "app.db"
KEY_PREFIX = "cv_"

SCHEMA = """
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    key_hash TEXT UNIQUE,
    rph INTEGER,
    daily_tokens INTEGER,
    created_at TEXT,
    revoked INTEGER DEFAULT 0
)
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    return conn


def hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


def create_key(name: str, rph: int, daily_tokens: int) -> str:
    """Create a key and return its plaintext. Raises sqlite3.IntegrityError if name exists."""
    plaintext = KEY_PREFIX + secrets.token_urlsafe(32)
    with connect() as conn:
        conn.execute(
            "INSERT INTO api_keys (name, key_hash, rph, daily_tokens, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, hash_key(plaintext), rph, daily_tokens, datetime.now(timezone.utc).isoformat()),
        )
    return plaintext


def lookup(plaintext: str) -> dict | None:
    """The key's row, or None if the key is unknown or revoked."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND revoked = 0", (hash_key(plaintext),)
        ).fetchone()
    return dict(row) if row else None


def revoke(name: str) -> bool:
    """Revoke a key by name. Returns False if no active key has that name."""
    with connect() as conn:
        cur = conn.execute("UPDATE api_keys SET revoked = 1 WHERE name = ? AND revoked = 0", (name,))
    return cur.rowcount > 0
