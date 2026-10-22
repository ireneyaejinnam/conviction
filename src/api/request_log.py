"""
One structured JSON line per request, printed to stdout when it finishes.

Endpoints add details to request.state.log (a dict the middleware creates);
anything not set is logged as null. Never put the API key, the
Authorization header, or the question text in it: the question is logged
only as its length and a short hash.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request

# Set by endpoints, logged between status and latency_ms in this order.
FIELDS = ["ticker", "q_len", "q_hash", "chunk_ids", "distances", "cited_sources", "refused"]


def question_fields(question: str) -> dict:
    return {"q_len": len(question),
            "q_hash": hashlib.sha256(question.encode()).hexdigest()[:12]}


def _ms(x: float | None) -> float | None:
    return None if x is None else round(x, 1)


async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.log = log = {}
    start = time.perf_counter()
    status = 500                          # if the app raises, this is what the client gets
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        stages = log.get("latency_ms") or {}
        route = request.scope.get("route")
        line = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "key_name": log.get("key_name"),
            "method": request.method,
            "endpoint": route.path if route else request.url.path,
            "status": status,
            **{f: log.get(f) for f in FIELDS},
            "latency_ms": {"embed": _ms(stages.get("embed")),
                           "retrieve": _ms(stages.get("retrieve")),
                           "generate": _ms(stages.get("generate")),
                           "total": _ms((time.perf_counter() - start) * 1000)},
            "tokens": log.get("tokens"),
            "cost_usd": log.get("cost_usd"),
        }
        print(json.dumps(line), flush=True)
