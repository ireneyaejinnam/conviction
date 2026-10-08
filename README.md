# Conviction

A personal investor's decision-support agent — answers questions about SEC filings
with inline, verifiable citations, and refuses when the filing doesn't cover it.

**[Live demo](URL)** · **[2-min video](URL)** · [Design decisions](DECISIONS.md)

## What it does
- **Cited QA** over 10-K filings for NVDA, AMD, MSFT, GOOGL. Every claim carries a
  `[Source N]` that expands to the underlying filing passage.
- **Risk-factor diff** — what changed in a company's Item 1A year over year.
- **Refuses out-of-scope questions** rather than guessing.

## Architecture
EDGAR ingest → section-aware parsing (Items 1/1A/7/8) → 800-token chunking with
100-token overlap (never split across Items) → OpenAI embeddings → ChromaDB with
filterable metadata → scoped dense retrieval → citation-enforced GPT-4o generation.

The risk-factor diff runs a separate path: it fetches two filings, extracts Item 1A
from each, and asks GPT-4o for a structured comparison — no retrieval involved,
because a diff is a whole-document question, not a top-k one.

## Run it
```bash
pip install -r requirements.txt
cp .env.example .env          # add OPENAI_API_KEY and EDGAR_USER_AGENT
python -m scripts.ingest_watchlist
streamlit run app.py