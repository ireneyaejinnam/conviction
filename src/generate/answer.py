from openai import OpenAI

SYSTEM = """You are a financial research assistant for a personal investor.
Answer the user's question using ONLY the provided filing excerpts.
Every claim must cite [Source N] referencing the numbered excerpt.
If the excerpts don't contain the answer, say so plainly — do not guess.
Do not draw on outside knowledge."""

def format_context(chunks: list[dict]) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        m = c["metadata"]
        header = f"[Source {i}] ({m['ticker']} {m['filing_type']}, {m.get('filing_date', 'n/a')}, {m['item']} — {m['item_title']})"
        lines.append(f"{header}\n{c['text']}")
    return "\n\n".join(lines)

def answer(question: str, chunks: list[dict]) -> str:
    client = OpenAI()
    context = format_context(chunks)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"}
        ]
    )
    return resp.choices[0].message.content