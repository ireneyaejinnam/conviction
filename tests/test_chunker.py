import random

import pytest

from src.chunk.section_aware import OVERLAP_TOKENS, TARGET_TOKENS, _count_tokens, chunk_filing
from src.ingest.parser import Section

WORDS = ("revenue supply demand customer export regulation margin inventory data center "
         "competition semiconductor manufacturing capacity pricing risk").split()


def _paragraph(rng: random.Random, sentences: int) -> str:
    out = []
    for _ in range(sentences):
        words = [rng.choice(WORDS) for _ in range(rng.randint(8, 25))]
        out.append(" ".join(words).capitalize() + ".")
    return " ".join(out)


def _section(item: str, tag: str, seed: int, paragraphs: int = 40) -> Section:
    rng = random.Random(seed)
    # Each paragraph starts with a marker so we can tell which Item a chunk's text came from.
    paras = [f"{tag}{i} " + _paragraph(rng, rng.randint(2, 12)) for i in range(paragraphs)]
    # One oversized paragraph forces the sentence-level split path.
    paras.insert(paragraphs // 2, f"{tag}big " + _paragraph(rng, 120))
    return Section(ticker="NVDA", filing_type="10-K", filing_date="2026-02-25", item=item,
                   item_title=f"Title {item}", text="\n\n".join(paras), source_path="x")


def _sections():
    return [_section("Item 1", "ALPHA", 1), _section("Item 1A", "BRAVO", 2),
            _section("Item 7", "CHARLIE", 3)]


def test_no_chunk_spans_two_items():
    sections = _sections()
    tags = {"Item 1": "ALPHA", "Item 1A": "BRAVO", "Item 7": "CHARLIE"}
    chunks = chunk_filing(sections)
    assert chunks
    for c in chunks:
        own = tags[c.metadata["item"]]
        others = [t for t in tags.values() if t != own]
        assert not any(t in c.text for t in others), f"{c!r} contains text from another Item"
        assert c.metadata["item_title"] == f"Title {c.metadata['item']}"


def test_token_count_within_max():
    chunks = chunk_filing(_sections())
    for c in chunks:
        assert c.metadata["token_count"] == _count_tokens(c.text)
        assert c.metadata["token_count"] <= TARGET_TOKENS, repr(c)


def test_overlap_between_consecutive_chunks_in_same_item():
    chunks = chunk_filing(_sections())
    pairs = 0
    for prev, nxt in zip(chunks, chunks[1:]):
        if prev.metadata["item"] != nxt.metadata["item"]:
            continue
        pairs += 1
        # The next chunk starts with one or more trailing units (paragraphs or
        # sentences) of the previous one.
        units = nxt.text.split("\n\n")
        overlap = next(("\n\n".join(units[:n]) for n in range(len(units) - 1, 0, -1)
                        if prev.text.endswith("\n\n".join(units[:n]))), None)
        assert overlap, f"no overlap between {prev!r} and {nxt!r}"
        assert _count_tokens(overlap) > 0
    assert pairs > 0
    assert OVERLAP_TOKENS > 0


@pytest.mark.xfail(reason="known: overlap can carry an oversized unit; 16 of 416 real chunks exceed "
                          "1,000 tokens (max 1,554, mostly AMD). Fix planned with a re-run of the eval.",
                   strict=True)
def test_token_count_within_max_with_large_paragraphs():
    # Paragraphs just under the budget: the whole previous paragraph is carried as overlap.
    para = lambda tag: " ".join([f"{tag} supply risk word."] * 150)
    text = "\n\n".join(para(t) for t in ("Alpha", "Bravo", "Charlie"))
    section = Section(ticker="NVDA", filing_type="10-K", filing_date="2026-02-25", item="Item 1A",
                      item_title="Risk Factors", text=text, source_path="x")
    for c in chunk_filing([section]):
        assert c.metadata["token_count"] <= TARGET_TOKENS, repr(c)
