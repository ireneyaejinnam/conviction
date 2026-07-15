"""Year-over-year risk-factor (Item 1A) diff for one ticker. Prototype."""
import json
from openai import OpenAI

from src.ingest.edgar import fetch_recent_filings
from src.ingest.parser import parse_filing

MODEL = "gpt-4o"
MAX_CHARS = 40_000   # ~15k tokens/section; keeps two years inside gpt-4o's window

SYSTEM = """You are a financial analyst comparing two years of a company's 10-K risk factors (Item 1A).
You are given the Item 1A text for a CURRENT year and a PRIOR year.
Produce a structured diff using ONLY the provided text. Do not invent risks.

Return STRICT JSON (no markdown, no prose) with exactly this schema:
{
  "new":     [{"risk": "...", "evidence": "short paraphrase", "year": "<current filing_date>"}],
  "removed": [{"risk": "...", "evidence": "short paraphrase", "year": "<prior filing_date>"}],
  "changed": [{"risk": "...", "what_changed": "...", "year_current": "<date>", "year_prior": "<date>"}]
}
Every item must cite the year (filing_date) it came from. If a category is empty, return []."""


def _find_item_1a(sections):
    for s in sections:
        if "1A" in s.item.replace(" ", "").upper():   # matches "Item 1A", "1A", etc.
            return s
    raise ValueError("Item 1A not found in parsed filing")


def risk_diff(ticker, model=MODEL):
    ticker = ticker.upper().strip()
    paths = fetch_recent_filings(ticker, "10-K", limit=2)
    if len(paths) < 2:
        raise ValueError(f"Need 2 filings to diff; found {len(paths)} for {ticker}")

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
            {"role": "system", "content": SYSTEM},
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