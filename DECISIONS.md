# Conviction

Conviction is a decision-support agent for personal investors. It surfaces signal hidden in primary-source SEC filings, forces users to confront the bear case before buying, and tracks the user's own decisions against outcomes over time — closing the feedback loop that most retail investors never close. Grounded in SEC filings with full citation transparency. No black box, no predictions. Built as a portfolio piece and a tool I'd actually use myself.

---

## Stack & rationale

### Language: Python
Python is the default for anything LLM-adjacent — every SDK I'm using (OpenAI, Chroma, LangChain) is Python-first, and the data tooling around it (pydantic, tiktoken, pytest) is mature. I considered TypeScript briefly since it'd be nicer for a future web UI, but I'd lose half the ecosystem.

### LLM: OpenAI GPT-4o
Picked GPT-4o for V1 because it's the most-tutorialized model for RAG, which means fewer dead-ends when something breaks. Claude would also work fine — the interface is nearly identical and I can swap providers later. I'm not committing to OpenAI as the *only* model: in Project D-1 (Week 3) I'm running an explicit head-to-head benchmark of Claude vs. GPT-4o vs. Gemini on a Korean RAG task, which is a more honest place to compare them than inside this project.

### Embeddings: OpenAI text-embedding-3-small
Same API key, cheap (~$0.02 per million tokens), good enough for English financial text. Embedding output is a 1536-dimensional vector — basically a list of 1536 numbers that captures the "meaning" of a chunk. Chunks that mean similar things end up with vectors that are close together in that 1536-D space, which is what makes semantic search possible. I considered `text-embedding-3-large` (3072 dimensions, ~2x cost) but the quality gap doesn't show up on documents this domain-specific.

### Vector store: Chroma, local, persistent
Chroma runs in-process and saves to a folder on disk. No separate service, no API keys, no free-tier juggling. It also has metadata filtering built in (which I need — being able to query "only NVDA's 10-K, only Item 1A" matters). 

Alternatives considered and ruled out for V1:
- **Pinecone / Weaviate Cloud / Qdrant Cloud**: hosted, accounts to manage, overkill for a single-user system.
- **FAISS**: fast but doesn't support metadata filtering natively, and I need that.
- **pgvector**: would be a great choice if I already had Postgres running. I don't.

If Conviction outgrows Chroma later (it won't this summer), swapping to Qdrant is roughly a one-day job because I'm abstracting the store interface.

### Framework: hybrid
The most common choice in this space is LangChain for everything. I'm using LangChain *only* for document loading (parsing EDGAR HTML is genuinely tedious and not the thing I'm trying to learn), and writing the chunking, embedding, retrieval, and generation loop directly against the OpenAI and Chroma SDKs.

Two reasons. First, the retrieval-generation loop is ~150 lines of Python — a framework hides it and makes me worse at the thing I'm trying to learn. Second, writing the primitives myself produces a stronger portfolio artifact: the repo shows I understand the building blocks, not just how to configure someone else's abstraction. LangChain saves a day on parsing; writing the rest myself is the point.

### Chunking strategy: section-aware
Chunks are ~800 tokens with 100-token overlap, but never split across Items. Filings have semantic structure — Item 1A (Risk Factors) is a coherent unit of meaning, and naive splits would scatter it across chunks that lose context. Every chunk carries metadata identifying which ticker, filing, filing date, Item, and Item title it came from. That metadata is the backbone of the citation feature: when the agent says "according to Item 1A," that claim is backed by a specific chunk with verifiable provenance.

### Eval: hand-written Q&A pairs
A `data/eval/` folder with growing JSONL files of (question, expected behavior) pairs. Starting with 5 questions on NVDA in Week 1, growing to 20-30 across multiple tickers by Week 3. Without a held-out eval set, "the system works" is a vibe, not a claim. With one, I can actually measure whether changes to chunking, retrieval, or prompts help or hurt.

---

## Scope decisions (V1)

**Cut: earnings-call transcript ingestion and management tone analysis.**
Transcript data requires a paid API (FMP) and the ingestion path was never
verified end-to-end. The value didn't justify the dependency for V1, so the
code was removed rather than left dead in the repo. Filing-grounded QA and
risk-factor diffing deliver the core thesis — decision support grounded in
primary sources — without it.

**Cut: decision journal.** The strongest long-term differentiator, but it's a
persistence + UI surface, not a retrieval problem. Deferred deliberately.

**Kept: risk-factor diff.** Year-over-year Item 1A comparison shows what
retrieval alone can't — what *changed*.

---

## Related work

The "search and Q&A over SEC filings" category is mature. The incumbents are **AlphaSense** (enterprise-tier, $15k+/seat/year, used by hedge funds and corporates), **Hebbia** (newer, AI-native, multi-billion valuation, targeting institutional investors), and **Rogo** (YC-backed, focused on investment bankers). Consumer-leaning options like **FinChat**, **Quartr AI**, and **Perplexity Finance** target retail but mostly stop at Q&A.

Conviction's scope is intentionally different in three ways. First, it's built for *one* personal investor, not an institutional workflow — so it can be more opinionated and surface signal that an enterprise tool would hedge on for liability reasons. Second, transparency is a design constraint, not a marketing line: the retrieval is inspectable, the prompts are visible in the repo, and every citation links back to the source chunk. Third, the decision journal — logging your thesis and confronting it with reality over time — isn't something the incumbents do, because it's a behavior-change feature for an individual rather than a research feature for a desk.