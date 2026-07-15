# Week 1 Notes — Conviction

**Goal:** ship a walking skeleton — ask a question about NVDA's 10-K, get a cited answer back.
**Outcome:** ✅ Skeleton works end-to-end. 5/5 eval questions returned reasonable answers; out-of-scope refusal worked on first try.

---

## What worked

- **End-to-end pipeline is functional on Day 1 of having it.** Ingest → parse → chunk → embed → store → retrieve → generate with citations all runs from one CLI call (`python -m scripts.ask "..."`).
- **Citation grounding is holding.** The agent stayed inside the retrieved excerpts on every question I ran. The quantum computing question (out-of-scope) was correctly refused — the model didn't pull from training data when retrieval came back empty-handed. This was the single biggest risk in the design and it works.
- **Retrieval is sharper than I expected.** Risk questions consistently pulled Item 1A, business strategy questions pulled Item 1, financial questions pulled Item 7. The section-aware chunking + metadata is doing real work here — the system is using the structure of filings, not just text similarity.
- **The agent surfaced specific numbers (22% / 14% customer concentration) on the revenue concentration question.** Verified [against / pending verification against] the actual filing — citation fidelity is [solid / TBC].
- **Section-aware parsing held up better than I feared on NVDA.** All 4 target items (1, 1A, 7, 8) were found with substantial content. The "last occurrence wins" trick for handling table-of-contents duplication worked cleanly.
- **Re-running ingestion was painless** thanks to `upsert` — meaningful for the iteration speed I'll need in Week 2.

## What's broken

### Parsing artifacts

- [Fill in: any TOC fragments you saw leaking into Item 1?]
- [Fill in: page headers/footers ("NVIDIA Corporation and Subsidiaries", page numbers) repeated through the text?]
- [Fill in: what does the bottom of Item 8 look like? Did it bleed into Item 9 territory, or did the anchor catch it cleanly?]
- Item 8 (Financial Statements) is mostly flattened tables — readable as raw text, but column alignment is gone. This will hurt retrieval quality for any question that depends on specific line items in the financials. Expected; not fixing in Week 1.
- [Fill in: was the filing_date scraped correctly from the SGML header? Should look like "2025-02-26" or similar in metadata.]

### Chunking observations

- Total chunks across NVDA 10-K: [fill in from your run]
- Per-item distribution: [fill in — Item 1: __, Item 1A: __, Item 7: __, Item 8: __]
- Token-count range: min [__] / max [__] / avg [__]
- Oversized chunks (>800 tokens)? [fill in count] — most likely Item 8 table sections with no paragraph breaks for the splitter to use.

### Retrieval misses

- "competitive position" question pulled 7/8 chunks from Item 1 — heavy on Item 1, light on Item 7 (which has forward-looking competitive framing). Could benefit from cross-section retrieval (boost diversity in top-k).
- "data center vs. gaming" comparative question pulled mostly Item 1; missed some of the relevant Item 7 segment-financials context. Not wrong, but a more sophisticated query would have surfaced both.
- [Fill in any other weird-looking retrievals from your runs.]

### Citation issues

- [Fill in: when you spot-checked the 22% / 14% revenue concentration numbers in the actual filing, did they match exactly? If yes, citation fidelity is verified on at least one numerical claim. If no, log specifically what differed.]
- The `SOURCES USED` output shows the item and chunk, but doesn't show *which specific source numbers in the answer correspond to which chunk*. The model is citing "[Source 1]", "[Source 5]" inline, but the trailing list is in retrieval order — you have to read the prompt to match them up. Mild UX issue; worth a fix.

### Pipeline / DX

- No `filing_date` validation — if EDGAR's header format changes or the regex misses, `filing_date` becomes `""` and propagates silently into Chroma metadata as an empty string. Should warn loudly.
- Re-running on the same ticker keeps the previous filing's chunks if I download a newer filing (since the IDs would differ on date). Not a bug today, but I should think about a "delete previous filings for this ticker" option in Week 2.

---

## Week 2 backlog — top 3 fixes

Not fixing this week. Locking these in for Sunday's planning session.

1. **Cross-section retrieval diversity.** Top-k is currently dominated by whichever section the query best matches. For synthesis and comparative questions, I want top-k to span multiple relevant sections. Likely fix: retrieve more (e.g., k=20) and re-rank, or per-section retrieval then merge. This is the highest-leverage fix because it unblocks the "What Changed" and synthesis features that are the Conviction differentiator.

2. **Earnings call transcripts as a second corpus.** Adding Q4 FY25 earnings call transcripts alongside the 10-K. The 10-K gives the official narrative; the earnings call gives the unscripted version. Side-by-side retrieval over both is where management tone analysis becomes possible — which is the Week 3 deliverable per the Phase 2 plan.

3. **Parser robustness on a second ticker.** Right now the parser works on NVDA. The regex-based item header detection is going to be brittle on smaller-cap filings, filings with unusual section ordering, or filings that use slight title variations. Need to test on at least one other ticker (AMD or a Korean ADR like CPNG) and log where it breaks. This is a "find the bug" task, not a "fix everything" task.

---

## Time spent

- Block 1-3 (setup + DECISIONS.md): ~[fill in] hr
- Block 4-5 (ingest + parse): ~[fill in] hr — [the big sink point of the week / smoother than expected]
- Block 6-7 (chunk + store): ~[fill in] hr
- Block 8-9 (retrieve + generate): ~[fill in] hr
- Block 10 (eval + this file): ~[fill in] hr
- **Total:** ~[fill in] hr

[Within / over / under the 17-19 hour budget.]

---

## Sunday May 31 prep

- Bring this file to the planning session.
- Lock D-1 scope (Korean RAG with frontier-LLM benchmarks).
- Draft Week 2 daily plan: continue Conviction (multi-ticker, earnings call ingest, cross-section retrieval), ignite D-1, draft Sift case study #1 by Friday.