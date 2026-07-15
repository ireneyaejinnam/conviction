import argparse
from dotenv import load_dotenv
from src.pipeline import ask

load_dotenv()


def main():
    p = argparse.ArgumentParser(description="Ask Conviction a question.")
    p.add_argument("question", help="Natural-language question")
    p.add_argument("--ticker", default=None, help="Scope to one ticker, e.g. NVDA")
    p.add_argument("--doc-type", dest="doc_type", default=None,
                   help='Scope to a doc type: "10-K" or "transcript"')
    p.add_argument("-k", type=int, default=8, help="Chunks to retrieve")
    args = p.parse_args()

    result = ask(args.question, k=args.k, ticker=args.ticker, doc_type=args.doc_type)
    print("ANSWER:\n", result["answer"])
    print("\nSOURCES USED:")
    for i, c in enumerate(result["sources_used"], 1):
        m = c["metadata"]
        print(f"  [{i}] {m['ticker']} {m.get('doc_type', '?')} {m['item']} — {m['item_title']}")


if __name__ == "__main__":
    main()