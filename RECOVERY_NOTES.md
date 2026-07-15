# Recovery Notes — Conviction

Status audit performed 2026-07-07. Do not fix today — log only.

---

## What works

| Component | Status | Notes |
|-----------|--------|-------|
| EDGAR ingest (`fetch_filing`) | Working | 4 tickers downloaded (NVDA, AMD, MSFT, GOOGL) |
| 10-K parsing (`parse_filing`) | Working | Section-aware, finds Items 1/1A/7/8, last-occurrence trick handles TOC duplication |
| Section-aware chunking | Working | 800-token chunks, 100-token overlap, paragraph/sentence boundary-aware |
| Embedding + Chroma store | Working | ~11MB Chroma DB, upsert-based, cosine similarity, text-embedding-3-small |
| Retrieval (`search.py`) | Working | Metadata filtering works (ticker, doc_type) |
| Answer generation (`answer.py`) | Working | GPT-4o, citation grounding prompt, refuses out-of-scope questions |
| Full pipeline (`scripts/ask`) | Working | End-to-end Q&A with citations verified against NVDA risk factors query |
| Watchlist ingest (`ingest_watchlist.py`) | Working | Batch ingest of 4 tickers with EDGAR rate-limit politeness |

---

## What's broken

### 1. `parser.py` missing `import json` (will crash transcript ingestion)

`src/ingest/parser.py` defines `parse_transcript()` which calls `json.loads()`, but the module never imports `json`. Any call to `ingest_transcript` will fail at runtime with `NameError: name 'json' is not defined`.

Location: `src/ingest/parser.py:240` — `json.loads(Path(filepath).read_text())`

### 2. Transcript ingestion is untested/unverified

Beyond the missing import, there's no evidence transcript ingestion has ever run successfully:
- No `data/transcripts/` directory exists
- The FMP API URL pattern and param names have a `# CONFIRM` comment in `src/ingest/transcripts.py`
- `TRANSCRIPT_API_KEY` is set in `.env` but may be stale

### 3. `risk_diff.py` uses a different download path than `ingest_one`

`risk_diff` calls `fetch_recent_filings()` which looks for `primary-document.html`, while `ingest_one` calls `fetch_filing()` which looks for `full-submission.txt`. These are different code paths with different fallback logic. `risk_diff` hasn't been verified to work with the current downloaded filings.

### 4. WEEK1_NOTES.md is mostly unfilled

Nearly every data field is still a `[fill in]` placeholder:
- Parsing artifact observations (TOC fragments, headers/footers, Item 8 bleed)
- Chunking stats (total chunks, per-item distribution, token-count range)
- Citation verification (22%/14% revenue concentration numbers)
- Time tracking (all blocks are `~[fill in] hr`)

### 5. Eval set exists but has no automated runner

`data/eval/nvda.jsonl` has 5 well-structured eval questions, but there's no script to run them and compare against expected behavior. `smoke_week2.py` runs 3 hardcoded checks but doesn't use the eval JSONL.

### 6. Cross-ticker bleed in unscoped queries

Running `scripts/ask` without `--ticker` returns sources from multiple tickers (GOOGL Item 1A, MSFT Item 1 appeared in an NVDA risk factors query). Not a bug — expected behavior when no filter is set — but worth noting for UX.

---

## Features that don't exist yet (planned but unbuilt)

| Feature | Where mentioned | Status |
|---------|----------------|--------|
| Cross-section retrieval diversity | WEEK1_NOTES.md backlog item #1 | No code. Top-k is still pure similarity, no re-ranking or per-section retrieval. |
| Decision journal | DECISIONS.md ("tracks the user's own decisions against outcomes over time") | No code, no schema, no UI. Core differentiator per design doc. |
| Eval automation | WEEK1_NOTES.md, DECISIONS.md ("eval: hand-written Q&A pairs") | JSONL exists, no runner. |
| Multi-ticker comparison | WEEK1_NOTES.md backlog item #3 | Parser tested on 4 tickers but no explicit comparison tooling. |
| Management tone analysis | WEEK1_NOTES.md ("Week 3 deliverable") | Depends on transcript ingestion, which is broken. |
