"""
Run the eval set and report citation grounding.
Usage: python -m scripts.run_eval
"""

import json
from dotenv import load_dotenv
from src.config import EVAL_DIR
from src.pipeline import ask

load_dotenv()
EVAL_PATH = EVAL_DIR / "nvda.jsonl"

def main():
    rows = [json.loads(l) for l in EVAL_PATH.read_text().splitlines() if l.strip()]
    passed = 0

    for row in rows:
        q = row["question"]
        result = ask(q, k=8, ticker="NVDA")
        text = result["answer"]

        cited = "[Source" in text
        refused = "does not" in text.lower() or "not contain" in text.lower()
        ok = result["ok"] and (cited or refused)

        print(f"\n{'PASS' if ok else 'FAIL'} — {q}")
        print(f"  cited={cited}  refused={refused}  sources={len(result['sources_used'])}")
        print(f"  expected: {row.get('good_answer_notes','')[:100]}")
        print(f"  got: {text[:200]}...")
        passed += ok

    print(f"\n{passed}/{len(rows)} passed automated checks.")
    print("Manual step: for 2 answers, open the cited chunk and confirm the claim appears in it.")


if __name__ == "__main__":
    main()