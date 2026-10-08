import sys
import json
from dotenv import load_dotenv
from src.analyze.risk_diff import load_risk_diff

load_dotenv()

if __name__ == "__main__":
    ticker = (sys.argv[1] if len(sys.argv) > 1 else "NVDA").upper()
    result = load_risk_diff(ticker)
    if result is None:
        print(f"No precomputed diff for {ticker}. Run: python -m scripts.ingest_watchlist")
        sys.exit(1)
    d = result["diff"]

    print(f"\nRISK-FACTOR DIFF — {result['ticker']} "
          f"({result['prior_year']} → {result['current_year']})\n")

    print(f"NEW RISKS ({len(d.get('new', []))}):")
    for r in d.get("new", []):
        print(f"  + [{r.get('year')}] {r['risk']}")

    print(f"\nREMOVED RISKS ({len(d.get('removed', []))}):")
    for r in d.get("removed", []):
        print(f"  - [{r.get('year')}] {r['risk']}")

    print(f"\nMATERIALLY CHANGED ({len(d.get('changed', []))}):")
    for r in d.get("changed", []):
        print(f"  ~ {r['risk']}: {r.get('what_changed', '')}")

    print("\n--- raw JSON (for later UI / eval) ---")
    print(json.dumps(result, indent=2))