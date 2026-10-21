"""
Eval metrics over data/eval/conviction.jsonl.

Run mode (default):
  - retrieval on answerable questions, top 8, ticker-filtered:
      item-level hit@8: any retrieved chunk's item is in expected_items
      chunk-level hit@8: evidence_chunk_id is among the retrieved ids
      answer-text recall@8: the evidence sentence (whitespace-normalized)
        appears in any retrieved chunk's text
  - abstention accuracy on should_refuse questions, false-refusal rate on
    answerable ones (both via a refusal-phrase heuristic, no LLM judge)
  - every [Source N] citation written to citations_to_label.csv for hand
    labeling; the supports column is left blank
  - raw per-question results saved to data/eval/run_<timestamp>.json

Score mode (--score):
  - citation precision = rows labeled 1 / rows labeled 0 or 1

Usage:
  python -m scripts.eval_metrics
  python -m scripts.eval_metrics --score
  python -m scripts.eval_metrics --rescore run_<timestamp>.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime

from src.config import EVAL_DIR, ROOT
from src.index.store import _chunk_id, get_collection
from src.pipeline import ask
from src.retrieve.search import search

EVAL_PATH = EVAL_DIR / "conviction.jsonl"
CSV_PATH = EVAL_DIR / "citations_to_label.csv"
K = 8

REFUSAL_PHRASES = [
    "do not contain", "does not contain", "don't contain", "doesn't contain",
    "not mentioned", "no information", "not addressed", "cannot answer",
    "not covered", "does not mention", "do not mention", "not discussed",
    "does not provide", "do not provide",
    "do not discuss", "does not discuss", "no mention", "do not include",
    "does not include", "cannot determine", "do not indicate", "does not indicate",
]

CSV_COLUMNS = ["row_id", "q_id", "ticker", "question", "claim", "source_n",
               "cited_item", "chunk_id", "chunk_text", "supports", "note"]

# "[Source 3]", "[Source 4, Source 5]", "[Sources 1, 2]"
CITATION_RE = re.compile(r"\[Sources?\s*\d+(?:\s*,\s*(?:Source\s*)?\d+)*\]", re.I)


def refusal_phrase(text: str) -> str | None:
    """The first refusal phrase found in text, or None."""
    lower = text.lower()
    return next((p for p in REFUSAL_PHRASES if p in lower), None)


def split_sentences(text: str) -> list[str]:
    parts = []
    for line in text.split("\n"):
        parts += re.split(r"(?<=[.!?])\s+(?=[A-Z0-9*\[(\"“])", line)
    return [p.strip() for p in parts if p.strip()]


def citation_rows(row: dict, answer: str, sources: list[dict]) -> list[dict]:
    out = []
    for sentence in split_sentences(answer):
        for cite in CITATION_RE.findall(sentence):
            for n in (int(x) for x in re.findall(r"\d+", cite)):
                if 1 <= n <= len(sources):
                    meta = sources[n - 1]["metadata"]
                    cited_item, chunk_id, chunk_text = meta["item"], _chunk_id(meta), sources[n - 1]["text"]
                else:
                    cited_item, chunk_id, chunk_text = "", "", "INVALID SOURCE NUMBER"
                out.append({"q_id": row["id"], "ticker": row["ticker"], "question": row["question"],
                            "claim": sentence, "source_n": n, "cited_item": cited_item,
                            "chunk_id": chunk_id, "chunk_text": chunk_text, "supports": "", "note": ""})
    return out


def csv_has_labels() -> bool:
    if not CSV_PATH.exists():
        return False
    with CSV_PATH.open(newline="") as f:
        return any((r.get("supports") or "").strip() for r in csv.DictReader(f))


def pct(x: int, n: int) -> str:
    return f"{x}/{n} ({x / n:.1%})" if n else f"{x}/0 (n/a)"


def evidence_in(evidence: str, texts: list[str]) -> bool:
    """True if the evidence sentence (whitespace-normalized) appears in any of texts."""
    ev = " ".join(evidence.split())
    return any(ev in " ".join(t.split()) for t in texts)


def print_retrieval(ans: list[dict]):
    """Item-level hit, chunk-level hit and answer-text recall, overall and credit-only."""
    credit = [x for x in ans if x["credit"]]
    for label, key in [("Item-level hit", "hit"), ("Chunk-level hit", "chunk_hit"),
                       ("Answer-text recall", "text_hit")]:
        print(f"{label + f'@{K}:':24}{pct(sum(x[key] for x in ans), len(ans))}")
        print(f"  credit:               {pct(sum(x[key] for x in credit), len(credit))}")


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def run():
    if csv_has_labels():
        print(f"Refusing to run: {CSV_PATH} already has values in the supports column.\n"
              f"Move or rename it first so labels aren't overwritten.")
        sys.exit(1)

    rows = [json.loads(l) for l in EVAL_PATH.read_text().splitlines() if l.strip()]
    answerable = [r for r in rows if not r["should_refuse"]]
    refusals = [r for r in rows if r["should_refuse"]]
    results, cites = [], []

    for r in answerable:
        retrieved = search(r["question"], k=K, filters={"ticker": r["ticker"]})
        items = [c["metadata"]["item"] for c in retrieved]
        hit = any(i in r["expected_items"] for i in items)
        chunk_hit = r["evidence_chunk_id"] in [_chunk_id(c["metadata"]) for c in retrieved]
        text_hit = evidence_in(r["evidence"], [c["text"] for c in retrieved])

        res = ask(r["question"], k=K, ticker=r["ticker"])
        phrase = refusal_phrase(res["answer"])
        rc = citation_rows(r, res["answer"], res["sources_used"]) if res["ok"] else []
        cites += rc

        results.append({
            "id": r["id"], "ticker": r["ticker"], "credit": r["credit"], "should_refuse": False,
            "expected_items": r["expected_items"], "hit": hit,
            "evidence_chunk_id": r["evidence_chunk_id"], "chunk_hit": chunk_hit, "text_hit": text_hit,
            "retrieved": [{"id": _chunk_id(c["metadata"]), "item": c["metadata"]["item"],
                           "distance": c["distance"]} for c in retrieved],
            "ok": res["ok"], "answer": res["answer"], "refusal_phrase": phrase,
            "answer_sources": [_chunk_id(c["metadata"]) for c in res["sources_used"]],
            "citation_rows": len(rc),
        })
        print(f"  {r['id']:10} hit={'Y' if hit else 'N'}  chunk_hit={'Y' if chunk_hit else 'N'}  "
              f"text_hit={'Y' if text_hit else 'N'}  "
              f"refused={'Y' if phrase else 'N'}  "
              f"citations={len(rc)}  items={items}")

    for r in refusals:
        res = ask(r["question"], k=K, ticker=r["ticker"])
        phrase = refusal_phrase(res["answer"])
        results.append({"id": r["id"], "ticker": r["ticker"], "credit": r["credit"], "should_refuse": True,
                        "ok": res["ok"], "answer": res["answer"], "refusal_phrase": phrase,
                        "answer_sources": [_chunk_id(c["metadata"]) for c in res["sources_used"]]})
        print(f"  {r['id']:10} refusal detected={'Y' if phrase else 'N'}")

    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for i, c in enumerate(cites, 1):
            w.writerow({"row_id": i, **c})

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_path = EVAL_DIR / f"run_{stamp}.json"
    run_path.write_text(json.dumps({"timestamp": stamp, "commit": git_commit(), "k": K,
                                    "eval_file": EVAL_PATH.name, "results": results}, indent=2) + "\n")

    ans = [x for x in results if not x["should_refuse"]]
    ref = [x for x in results if x["should_refuse"]]
    failed = [x["id"] for x in results if not x["ok"]]
    missed_refusals = [x for x in ref if not x["refusal_phrase"]]
    false_refusals = [x for x in ans if x["refusal_phrase"]]
    invalid = sum(c["chunk_text"] == "INVALID SOURCE NUMBER" for c in cites)

    for x in missed_refusals:
        print(f"\n--- {x['id']}: refusal heuristic did NOT fire. Full answer:\n{x['answer']}")

    print("\n=== Summary ===")
    print(f"Answerable questions:   {len(ans)}")
    print(f"Refusal questions:      {len(ref)}")
    print_retrieval(ans)
    print(f"Abstention accuracy:    {pct(len(ref) - len(missed_refusals), len(ref))}")
    print(f"False-refusal rate:     {pct(len(false_refusals), len(ans))}"
          + (f"  -> {[(x['id'], x['refusal_phrase']) for x in false_refusals]}" if false_refusals else ""))
    print(f"Citation rows written:  {len(cites)} ({invalid} invalid source numbers) -> {CSV_PATH.name}")
    if failed:
        print(f"Pipeline errors (ok=False): {failed}")
    print(f"Raw results:            {run_path.name}")


def rescore(run_file: str):
    """
    Re-apply the current REFUSAL_PHRASES to a saved run's answers, and compute
    chunk-level hit@K and answer-text recall@K from its saved retrieved ids.
    Evidence fields come from the eval file and chunk texts from the local
    Chroma index (runs saved before these metrics were recorded). No API calls.
    """
    path = EVAL_DIR / run_file
    results = json.loads(path.read_text())["results"]
    rows = {r["id"]: r for r in (json.loads(l) for l in EVAL_PATH.read_text().splitlines() if l.strip())}
    evidence = {i: r["evidence_chunk_id"] for i, r in rows.items()}
    ans = [x for x in results if not x["should_refuse"]]
    ref = [x for x in results if x["should_refuse"]]
    collection = get_collection()
    for x in ans:
        ids = [c["id"] for c in x["retrieved"]]
        x["chunk_hit"] = evidence[x["id"]] in ids
        x["text_hit"] = evidence_in(rows[x["id"]]["evidence"], collection.get(ids=ids)["documents"])

    print(f"Rescoring {path.name} with {len(REFUSAL_PHRASES)} refusal phrases\n")
    for x in ref:
        old, new = x["refusal_phrase"], refusal_phrase(x["answer"])
        print(f"  {x['id']:10} refusal detected={'Y' if new else 'N'}  phrase={new!r}  (saved: {old!r})")

    missed = [x for x in ref if not refusal_phrase(x["answer"])]
    flagged = [x for x in ans if refusal_phrase(x["answer"])]
    for x in flagged:
        print(f"\n--- {x['id']} (answerable) flagged as refusal by {refusal_phrase(x['answer'])!r}. "
              f"Full answer:\n{x['answer']}")

    item_only = [x for x in ans if x["hit"] and not x["chunk_hit"]]
    if item_only:
        print("\nItem-level hit, evidence chunk not retrieved:")
        for x in item_only:
            print(f"  {x['id']:10} evidence={evidence[x['id']]}  "
                  f"text_hit={'Y' if x['text_hit'] else 'N'}  "
                  f"refused={'Y' if refusal_phrase(x['answer']) else 'N'}")

    print("\n=== Rescore summary ===")
    print_retrieval(ans)
    print(f"Abstention accuracy:    {pct(len(ref) - len(missed), len(ref))}"
          + (f"  -> missed {[x['id'] for x in missed]}" if missed else ""))
    print(f"False-refusal rate:     {pct(len(flagged), len(ans))}"
          + (f"  -> {[x['id'] for x in flagged]}" if flagged else ""))


def score():
    if not CSV_PATH.exists():
        print(f"No {CSV_PATH.name} found. Run without --score first.")
        sys.exit(1)
    with CSV_PATH.open(newline="") as f:
        rows = list(csv.DictReader(f))
    vals = [(r["row_id"], (r.get("supports") or "").strip()) for r in rows]
    ones = sum(v == "1" for _, v in vals)
    zeros = sum(v == "0" for _, v in vals)
    unlabeled = [rid for rid, v in vals if v == ""]
    bad = [(rid, v) for rid, v in vals if v not in ("", "0", "1")]
    labeled = ones + zeros

    print(f"Labeled: {labeled}/{len(rows)} rows  (supports=1: {ones}, supports=0: {zeros})")
    print(f"Citation precision: {pct(ones, labeled)}")
    if bad:
        print(f"Rows with values other than 0/1 (not counted): {bad}")
    if unlabeled:
        print(f"Unlabeled rows ({len(unlabeled)}): {', '.join(unlabeled)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Eval metrics for the conviction eval set.")
    p.add_argument("--score", action="store_true", help="Score hand-labeled citations_to_label.csv")
    p.add_argument("--rescore", metavar="RUN_FILE",
                   help="Re-apply refusal phrases to a saved run in data/eval (no API calls)")
    args = p.parse_args()
    if args.rescore:
        rescore(args.rescore)
    elif args.score:
        score()
    else:
        run()
