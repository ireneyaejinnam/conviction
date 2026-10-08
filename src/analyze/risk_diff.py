"""
Year-over-year risk-factor (Item 1A) diff for one ticker.

Diffs are computed at ingest time (compute_risk_diff + save_risk_diff) and
served from disk (load_risk_diff), so the app never calls EDGAR or GPT-4o
when a user views a diff.
"""
from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI

from src.config import DIFFS_DIR
from src.ingest.edgar import fetch_filings
from src.ingest.parser import parse_filing

MODEL = "gpt-4o"
# Guard only: every watchlist Item 1A (largest: AMD, 131k chars / 23k gpt-4o
# tokens) is sent in full, so the diff sees the whole section in both years.
MAX_CHARS = 150_000

def _system_prompt(current_date, prior_date):
    return f"""You are a financial analyst comparing two years of a company's 10-K risk factors (Item 1A).
You are given the Item 1A text for a CURRENT year and a PRIOR year.
Produce a structured diff using ONLY the provided text. Do not invent risks.

Return STRICT JSON (no markdown, no prose) with exactly this schema:
{{
  "new":     [{{"risk": "...", "evidence": "short paraphrase", "year": "{current_date}"}}],
  "removed": [{{"risk": "...", "evidence": "short paraphrase", "year": "{prior_date}"}}],
  "changed": [{{"risk": "...", "what_changed": "...", "year_current": "{current_date}", "year_prior": "{prior_date}"}}]
}}
Every item must cite the year (filing_date) it came from. If a category is empty, return []."""


def _find_item_1a(sections):
    for s in sections:
        if "1A" in s.item.replace(" ", "").upper():   # matches "Item 1A", "1A", etc.
            return s
    raise ValueError("Item 1A not found in parsed filing")


def compute_risk_diff(ticker, model=MODEL) -> dict:
    """Fetch the two most recent 10-Ks and diff their Item 1A with GPT-4o."""
    ticker = ticker.upper().strip()
    paths = fetch_filings(ticker, "10-K", count=2)

    # parse both, grab Item 1A from each, sort by filing_date so newest = current
    item1a = [_find_item_1a(parse_filing(p, ticker)) for p in paths]
    item1a.sort(key=lambda s: s.filing_date, reverse=True)
    current, prior = item1a[0], item1a[1]

    user = (
        f"TICKER: {ticker}\n\n"
        f"=== CURRENT YEAR (filing_date {current.filing_date}) — Item 1A ===\n"
        f"{current.text[:MAX_CHARS]}\n\n"
        f"=== PRIOR YEAR (filing_date {prior.filing_date}) — Item 1A ===\n"
        f"{prior.text[:MAX_CHARS]}"
    )

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _system_prompt(current.filing_date, prior.filing_date)},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},   # forces valid JSON (needs "json" in prompt — it's there)
    )
    diff = json.loads(resp.choices[0].message.content)
    return {
        "ticker": ticker,
        "current_year": current.filing_date,
        "prior_year": prior.filing_date,
        "diff": diff,
    }


def diff_path(ticker: str, current_year: str, prior_year: str) -> Path:
    return DIFFS_DIR / f"{ticker.upper()}_{current_year}_vs_{prior_year}.json"


def save_risk_diff(diff: dict) -> Path:
    path = diff_path(diff["ticker"], diff["current_year"], diff["prior_year"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(diff, indent=2) + "\n")
    return path


def cached_diff_files(ticker: str) -> list[Path]:
    """Cached diff files for a ticker, newest first. Dates are ISO, so names sort."""
    if not DIFFS_DIR.exists():
        return []
    return sorted(DIFFS_DIR.glob(f"{ticker.upper().strip()}_*_vs_*.json"), reverse=True)


def load_risk_diff(ticker: str) -> dict | None:
    """Read the newest cached diff for a ticker. Never touches the network."""
    files = cached_diff_files(ticker)
    if not files:
        return None
    return json.loads(files[0].read_text())
