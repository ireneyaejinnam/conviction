"""
Per-key and global rate limits, counted in the usage table of app.db.

Windows are fixed, in UTC: "hour" starts at the top of the hour, "day" at
00:00. Each (key, window, window_start) row holds that window's request and
token counts.

Flow for a metered request:
  1. reserve(): in one BEGIN IMMEDIATE transaction, check the limits and add
     1 request to the key's hour and day rows. Doing the check and the
     increment together is what stops two simultaneous requests from both
     seeing rph - 1 and both getting through.
  2. On success, record_tokens() adds the request's real token usage.
     On failure, refund() takes the reserved request back off, so only
     successful requests count.

Tokens are checked before the request runs, and the request's real usage
is only known after GPT-4o answers. So a single request can push a key (or
the global total) past its budget by that one request's size. That's
acceptable: each /ask is bounded (at most 12 retrieved chunks, a 1000-char
question, and one answer), the overshoot is only the requests already in
flight when the budget is crossed, the next request after that is refused,
and the global cap sits under
the OpenAI project's hard monthly budget anyway. Reserving tokens up front
instead would mean guessing the completion length before it exists.

Known gaps:
  - If generation fails after the query was embedded, that embedding's
    tokens aren't counted (only successful requests record tokens). This is
    acceptable because it's one short query's embedding, and only on failed
    requests.

Single-process, single-instance only: counters live in one SQLite file.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.api.keys import connect as connect_keys

GLOBAL_DAILY_TOKENS = int(os.environ.get("GLOBAL_DAILY_TOKENS") or 1_000_000)

SCHEMA = """
CREATE TABLE IF NOT EXISTS usage (
    key_id INTEGER,
    window TEXT,
    window_start TEXT,
    requests INTEGER,
    tokens INTEGER,
    PRIMARY KEY (key_id, window, window_start)
)
"""


class LimitExceeded(Exception):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.message = message
        self.retry_after = retry_after


@dataclass(frozen=True)
class Reservation:
    """The windows a request was counted in, so later updates hit the same rows."""
    key_id: int
    hour_start: str
    day_start: str


def connect():
    conn = connect_keys()
    conn.isolation_level = None          # explicit BEGIN/COMMIT below
    conn.execute(SCHEMA)
    return conn


def _windows(now: datetime) -> tuple[datetime, datetime]:
    hour = now.replace(minute=0, second=0, microsecond=0)
    day = hour.replace(hour=0)
    return hour, day


def _seconds_until(t: datetime, now: datetime) -> int:
    return max(1, math.ceil((t - now).total_seconds()))


def _add(conn, key_id: int, window: str, start: str, requests: int, tokens: int):
    conn.execute(
        """INSERT INTO usage (key_id, window, window_start, requests, tokens) VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (key_id, window, window_start)
           DO UPDATE SET requests = requests + excluded.requests, tokens = tokens + excluded.tokens""",
        (key_id, window, start, requests, tokens),
    )


def reserve(key: dict, now: datetime | None = None) -> Reservation:
    """Check every limit and count one request. Raises LimitExceeded (nothing counted) if over."""
    now = now or datetime.now(timezone.utc)
    hour, day = _windows(now)
    hour_s, day_s = hour.isoformat(), day.isoformat()

    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT requests FROM usage WHERE key_id = ? AND window = 'hour' AND window_start = ?",
                           (key["id"], hour_s)).fetchone()
        hour_requests = row["requests"] if row else 0
        row = conn.execute("SELECT tokens FROM usage WHERE key_id = ? AND window = 'day' AND window_start = ?",
                           (key["id"], day_s)).fetchone()
        day_tokens = row["tokens"] if row else 0
        global_tokens = conn.execute("SELECT COALESCE(SUM(tokens), 0) FROM usage WHERE window = 'day' AND window_start = ?",
                                     (day_s,)).fetchone()[0]

        if hour_requests >= key["rph"]:
            raise LimitExceeded(f"hourly request limit reached ({key['rph']} requests/hour)",
                                _seconds_until(hour + timedelta(hours=1), now))
        if day_tokens >= key["daily_tokens"]:
            raise LimitExceeded(f"daily token budget reached ({key['daily_tokens']} tokens/day)",
                                _seconds_until(day + timedelta(days=1), now))
        if global_tokens >= GLOBAL_DAILY_TOKENS:
            raise LimitExceeded("global daily token budget reached",
                                _seconds_until(day + timedelta(days=1), now))

        _add(conn, key["id"], "hour", hour_s, 1, 0)
        _add(conn, key["id"], "day", day_s, 1, 0)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return Reservation(key["id"], hour_s, day_s)


def record_tokens(r: Reservation, tokens: int):
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        _add(conn, r.key_id, "hour", r.hour_start, 0, tokens)
        _add(conn, r.key_id, "day", r.day_start, 0, tokens)
        conn.execute("COMMIT")
    finally:
        conn.close()


def refund(r: Reservation):
    """Undo a reservation's request count when the request didn't succeed."""
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        _add(conn, r.key_id, "hour", r.hour_start, -1, 0)
        _add(conn, r.key_id, "day", r.day_start, -1, 0)
        conn.execute("COMMIT")
    finally:
        conn.close()
