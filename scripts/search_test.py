from dotenv import load_dotenv
from src.retrieve.search import search

load_dotenv()

queries = [
    "what are NVDA's main risk factors?",
    "how does NVDA describe its data center business?",
    "what is NVDA's customer concentration?",
]

for q in queries:
    print(f"\n{'=' * 70}")
    print(f"QUERY: {q}")
    print("=" * 70)
    results = search(q, k=5)
    for i, r in enumerate(results, 1):
        m = r["metadata"]
        print(f"\n[{i}] {m['item']} — {m['item_title']} "
              f"(chunk {m['chunk_idx']}, distance {r['distance']:.3f})")
        print(f"    {r['text'][:200]}...")