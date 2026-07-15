import sys
import json
from dotenv import load_dotenv
from src.analyze.risk_diff import risk_diff

load_dotenv()

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    result = risk_diff(ticker)
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