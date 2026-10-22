# Eval results

| | |
|---|---|
| Date | 2026-10-21 |
| Official run | `data/eval/run_20261021_162828.json` |
| Commit at run time | `1e17a43` (the run used `scripts/eval_metrics.py` before it was committed; `src/` and `app.py` were unchanged from `1e17a43`) |
| Eval set | `data/eval/conviction.jsonl` |
| Retrieval depth | k = 8, filtered to the question's ticker |

All numbers below come from the official run only. Refusal metrics were re-scored from that run's saved answers with the current phrase list, and chunk-level hit and answer-text recall were computed from its saved retrieved ids (`python -m scripts.eval_metrics --rescore run_20261021_162828.json`); no answers were regenerated. Citation precision comes from `python -m scripts.eval_metrics --score` over the hand-labeled `data/eval/citations_to_label.csv`, which was produced by the same run.

## Corpus

From `python -m scripts.stats`:

| Ticker | Filing | Filed | Chunks |
|---|---|---|---|
| AMD | 10-K | 2026-02-04 | 121 |
| GOOGL | 10-K | 2026-02-05 | 101 |
| MSFT | 10-K | 2026-07-29 | 87 |
| NVDA | 10-K | 2026-02-25 | 107 |
| **Total** | 4 filings | | **416** |

## Eval set

29 questions: 23 answerable, 6 that should be refused (the answer is not in the filing). 10 of the answerable questions are tagged `credit` (debt, liquidity, ratings, maturities).

## Results

| Metric | Result |
|---|---|
| Item-level hit@8 | 23/23 (100.0%) |
| Item-level hit@8, credit only | 10/10 (100.0%) |
| Chunk-level hit@8 | 9/23 (39.1%) |
| Chunk-level hit@8, credit only | 4/10 (40.0%) |
| Answer-text recall@8 | 12/23 (52.2%) |
| Answer-text recall@8, credit only | 4/10 (40.0%) |
| Abstention accuracy | 6/6 (100.0%) |
| False-refusal rate | 2/23 (8.7%) |
| Citation precision | 47/58 (81.0%) |

## Method

Every question and its expected Item and evidence passage was reviewed against the filing and approved by hand before the run.

**Item-level hit@8.** A question counts as a hit if any of its 8 retrieved chunks comes from a 10-K item listed in its `expected_items`. When a question lists more than one item, a chunk from any one of them is enough, so multi-item questions can hit on one item alone (nvda_002 expects Item 1A and Item 15 and hit on Item 15 only).

**Chunk-level hit@8.** A question counts as a hit only if its `evidence_chunk_id`, the chunk holding the quoted evidence sentence, is among the 8 retrieved ids.

Item-level is lenient: an item like Item 7 or Item 8 spans dozens of chunks, so retrieving any chunk from the right item says little about whether the answer itself reached the model. Two questions show this directly:

- **msft_002** (Microsoft's credit rating): retrieval returned Item 8 chunks, so it is an item-level hit, but not `Item 8_16`, which holds "our long-term unsecured debt rating was AAA". The model answered that the excerpts do not include the credit rating.
- **googl_005** (whether capex will rise): retrieval returned Item 7 chunks, an item-level hit, but not `Item 7_1`, which holds "in 2026, we expect to significantly increase, relative to 2025, our investment in our technical infrastructure". The model answered that the excerpts do not mention capex plans.

Both refusals were caused by retrieval, not by the model ignoring retrieved evidence: in both cases the evidence sentence appears in none of the 8 retrieved chunks.

**Answer-text recall@8.** A question counts as a hit if its evidence sentence, with whitespace normalized, appears in the text of any of its 8 retrieved chunks. Chunk-level hit is too strict: chunks overlap, so the evidence sentence can also sit in a neighboring chunk that was retrieved. That happened for 3 of the 14 chunk-level misses (nvda_002, nvda_004, googl_004). Answer-text recall counts those, so it measures whether the answer reached the model regardless of which chunk carried it.

Item-level hit@8 is near-saturated because each ticker has only 4 items indexed (5 for NVDA, whose financial statements are under Item 15), so answer-text recall@8 is the primary retrieval metric.

**Abstention accuracy and false-refusal rate.** An answer counts as a refusal if it contains any phrase from `REFUSAL_PHRASES` in `scripts/eval_metrics.py` (substring match, no model judge). Abstention accuracy is the share of should-refuse questions that got a refusal; false-refusal rate is the share of answerable questions that got one. Both false refusals were checked by hand against the filing: the answer exists in each case.

**Citation precision.** Each `[Source N]` in an answer to an answerable question was written out as a (sentence, cited chunk) row and labeled by hand: 1 if the cited chunk supports the sentence, 0 if not. Precision is rows labeled 1 over all labeled rows. All 58 rows were labeled.

## Retrieval misses

There were no item-level misses. These are the 14 chunk-level misses, with what was retrieved instead (ids shortened to item and chunk index; all from the question's ticker).

| Question | Evidence chunk | Retrieved instead | Answer-text hit | Refused |
|---|---|---|---|---|
| nvda_001 | Item 1A_0 | Item 1A_11, Item 15_13, Item 1A_32, Item 7_0, Item 1A_4, Item 7_1, Item 15_11, Item 1_6 | No | No |
| nvda_002 | Item 1A_17 | Item 7_9, Item 7_7, Item 15_36, Item 15_13, Item 7_1, Item 15_2, Item 15_35, Item 15_16 | Yes | No |
| nvda_003 | Item 1_9 | Item 1_7, Item 1_6, Item 7_1, Item 1_8, Item 1_2, Item 1_5, Item 1_3, Item 1_0 | No | No |
| nvda_004 | Item 1_12 | Item 1A_25, Item 1A_21, Item 1_14, Item 1A_24, Item 1A_22, Item 1_13, Item 1A_20, Item 1A_23 | Yes | No |
| nvda_006 | Item 7_14 | Item 15_25, Item 15_26, Item 15_22, Item 15_23, Item 15_24, Item 15_37, Item 15_20, Item 15_8 | No | No |
| nvda_007 | Item 7_13 | Item 15_13, Item 15_25, Item 15_26, Item 7_1, Item 15_20, Item 15_22, Item 1_18, Item 7_7 | No | No |
| nvda_008 | Item 7_13 | Item 15_6, Item 15_5, Item 15_3, Item 15_4, Item 7_7, Item 15_17, Item 15_19, Item 7_0 | No | No |
| amd_001 | Item 7_10 | Item 8_5, Item 7_0, Item 1_19, Item 1_0, Item 8_13, Item 8_6, Item 1_1, Item 1_16 | No | No |
| amd_002 | Item 7_10 | Item 8_5, Item 7_0, Item 8_13, Item 1_0, Item 1_19, Item 1_2, Item 8_6, Item 7_1 | No | No |
| msft_002 | Item 8_16 | Item 8_32, Item 7_12, Item 1_11, Item 8_33, Item 7_0, Item 1_0, Item 7_2, Item 8_2 | No | Yes |
| msft_005 | Item 7_7 | Item 8_33, Item 8_32, Item 7_0, Item 1_11, Item 8_34, Item 7_12, Item 8_2, Item 1_0 | No | No |
| googl_001 | Item 7_13 | Item 8_32, Item 8_20, Item 8_3, Item 8_5, Item 8_33, Item 1A_18, Item 7_14, Item 8_42 | No | No |
| googl_004 | Item 1_0 | Item 7_1, Item 8_52, Item 7_0, Item 1_3, Item 8_8, Item 1_6, Item 7_3, Item 8_4 | Yes | No |
| googl_005 | Item 7_1 | Item 7_8, Item 7_6, Item 7_5, Item 7_10, Item 8_19, Item 7_7, Item 7_2, Item 8_53 | No | Yes |

A chunk-level miss does not mean the answer was wrong: the same facts often appear in more than one place in a 10-K (for example, NVDA's debt and buyback figures appear in both Item 7 and the Item 15 notes).

## Notable failures

- **Alphabet long-term debt direction (citation row 45, googl_001).** The answer said total long-term debt was "$46,547 million, down from $10,883 million in the previous year". The numbers match the cited chunk, but debt went up, not down. Citation precision counts this row as unsupported; it is a factual error, not only a citation error.
- **Wrong-source citations (rows 18–19, nvda_004).** The sentence "The complexity and frequent changes in export control rules pose a significant compliance burden" cited Source 2 and Source 7. Neither supports it: Source 2 has no compliance-burden language, and Source 7 covers compliance costs from law changes generally. The supporting sentence ("Repeated changes in the export control rules...") was in Source 5, which was retrieved but not cited for this claim.
- **Wrong-passage citation (row 25, nvda_007).** "NVIDIA gets its liquidity from several sources, including cash and cash equivalents, marketable securities, and financial policies that focus on high liquidity and credit security" cited a chunk that is the accounting policy defining cash equivalents, not a description of liquidity sources; "financial policies focused on credit security" is not stated.
- **Citation attached to a statement of absence (row 33, amd_001).** "There is no specific information in the provided excerpts about how much of this debt is short-term" cited Source 2. A citation cannot support an absence, and the debt due in 2026 is stated in another AMD chunk.
- **False refusals (msft_002, googl_005).** Both answers exist in the filing, but the chunk holding them was not retrieved; see Method.

## Run-to-run variation

Two full runs were made on the same commit and eval set: `run_20261021_154933.json` and the official `run_20261021_162828.json`. Answers differ between runs, so the original refusal phrase list caught different refusals in each: it missed msft_006 in the first run ("do not discuss", "no mention") and nvda_011 in the second ("do not include", "cannot determine"). Those phrases were added after reviewing every should-refuse answer from both runs. In the first run, googl_005 also gave a partial answer (2025 capex with a note that 2026 plans are not stated) that the expanded phrase list counts as a refusal. The metrics above are from one run and do not measure this variation.
