"""
HTTP client the Streamlit app uses to call the API.

Key choice: the user's own key if they entered one, otherwise DEMO_API_KEY
from the server's environment. The demo key only ever goes into the
Authorization header of requests to API_URL; it's never returned, shown,
or logged.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass

import httpx

TIMEOUT_S = 60


@dataclass
class Result:
    ok: bool
    status: int | None
    data: dict | None
    request_id: str | None
    error: str | None = None          # plain-language message for the user


def api_url() -> str:
    return (os.environ.get("API_URL") or "http://localhost:8000").rstrip("/")


def has_own_key(user_key: str | None) -> bool:
    return bool((user_key or "").strip())


def auth_headers(user_key: str | None) -> dict:
    key = (user_key or "").strip() or os.environ.get("DEMO_API_KEY", "")
    return {"Authorization": f"Bearer {key}"} if key else {}


def error_message(status: int | None, retry_after: str | None, request_id: str | None,
                  own_key: bool = False) -> str:
    if status == 401:
        return "That API key isn't valid."
    if status == 429:
        try:
            minutes = max(1, math.ceil(int(retry_after) / 60))
        except (TypeError, ValueError):
            minutes = 60
        who = "Your API key has hit its limit." if own_key else "The demo has hit its limit for now."
        return f"{who} Try again in about {minutes} minutes."
    return f"Something went wrong (request ID: {request_id or 'unavailable'})."


def call(method: str, path: str, user_key: str | None = None, json: dict | None = None,
         ok_statuses: tuple[int, ...] = (200,)) -> Result:
    """
    Call the API. Result.ok is True for statuses in ok_statuses; otherwise
    Result.error holds the message to show. Callers that handle a status
    themselves (e.g. 404) pass it in ok_statuses and check Result.status.
    """
    try:
        r = httpx.request(method, api_url() + path, headers=auth_headers(user_key),
                          json=json, timeout=TIMEOUT_S)
    except (httpx.ConnectError, httpx.TimeoutException):
        return Result(False, None, None, None, f"Can't reach the API at {api_url()}. Is it running?")
    except httpx.HTTPError:
        return Result(False, None, None, None, error_message(None, None, None))

    request_id = r.headers.get("X-Request-ID")
    if r.status_code not in ok_statuses:
        return Result(False, r.status_code, None, request_id,
                      error_message(r.status_code, r.headers.get("Retry-After"), request_id,
                                    own_key=has_own_key(user_key)))
    try:
        data = r.json()
    except ValueError:
        return Result(False, r.status_code, None, request_id, error_message(None, None, request_id))
    return Result(True, r.status_code, data, request_id)
