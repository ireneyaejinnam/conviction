from dotenv import load_dotenv
from src.pipeline import ask
load_dotenv()

CHECKS = [
    ("watchlist multi-ticker", "Compare NVDA and AMD data center exposure"),
    ("risk retrieval",         "What are NVDA's primary risk factors?"),
]
for label, q in CHECKS:
    r = ask(q)
    assert r["answer"] and len(r["answer"]) > 40, f"empty answer: {label}"
    assert "Source" in r["answer"] or r["sources_used"], f"no citations: {label}"
    print(f"✓ {label}: {len(r['sources_used'])} sources")
print("Week-2 pipeline intact.")