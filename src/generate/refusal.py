"""
Refusal-phrase heuristic: does an answer say the filings don't cover the
question? Shared by the eval (abstention accuracy, false-refusal rate) and
the API's `refused` flag, so both use the same definition.
"""

from __future__ import annotations

REFUSAL_PHRASES = [
    "do not contain", "does not contain", "don't contain", "doesn't contain",
    "not mentioned", "no information", "not addressed", "cannot answer",
    "not covered", "does not mention", "do not mention", "not discussed",
    "does not provide", "do not provide",
    "do not discuss", "does not discuss", "no mention", "do not include",
    "does not include", "cannot determine", "do not indicate", "does not indicate",
]


def refusal_phrase(text: str) -> str | None:
    """The first refusal phrase found in text, or None."""
    lower = text.lower()
    return next((p for p in REFUSAL_PHRASES if p in lower), None)


def is_refusal(text: str) -> bool:
    return refusal_phrase(text) is not None
