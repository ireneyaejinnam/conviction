"""
Section-aware chunking.

Splits a Section's text into ~800-token chunks with ~100-token overlap,
respecting natural boundaries (paragraphs, then sentences) so chunks don't
break mid-thought. Every chunk carries the section's metadata plus its own
index and token count.

Why boundary-aware instead of naive token slicing:
  - A chunk that ends mid-sentence retrieves worse (the embedding captures
    a fragment) and reads worse when cited back to the user.
  - Filings are paragraph-structured prose (especially Item 1A / Item 7),
    so paragraph boundaries are natural and cheap to respect.

Overlap exists so a fact sitting on a chunk boundary still appears whole in
at least one chunk — important for retrieval recall.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

from src.ingest.parser import Section


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TARGET_TOKENS = 800       # soft ceiling per chunk
OVERLAP_TOKENS = 100      # tokens carried from end of one chunk into next
ENCODING_NAME = "cl100k_base"  # tokenizer; see note below

# A single tokenizer instance, reused. tiktoken encoders are cheap to call
# but non-trivial to construct, so we build once at module load.
_ENC = tiktoken.get_encoding(ENCODING_NAME)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    text: str
    metadata: dict

    def __repr__(self) -> str:
        m = self.metadata
        return (
            f"Chunk({m.get('ticker')} {m.get('item')} "
            f"#{m.get('chunk_idx')} {m.get('token_count')}tok)"
        )


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _count_tokens(text: str) -> int:
    return len(_ENC.encode(text))


# ---------------------------------------------------------------------------
# Splitting the raw text into atomic units we can pack
# ---------------------------------------------------------------------------

def _split_into_units(text: str) -> list[str]:
    """
    Break text into the smallest units we'll pack into chunks: paragraphs,
    and — if a single paragraph is itself larger than the token budget —
    sentences within it.

    Returns a flat list of text units, each (ideally) <= TARGET_TOKENS.
    A unit can still exceed the budget if a single sentence is enormous;
    that's rare in filings and handled gracefully by the packer.
    """
    # Paragraphs: split on blank lines (our parser normalized to \n\n).
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    units: list[str] = []
    for para in paragraphs:
        if _count_tokens(para) <= TARGET_TOKENS:
            units.append(para)
        else:
            # Paragraph too big — break into sentences.
            units.extend(_split_into_sentences(para))
    return units


def _split_into_sentences(text: str) -> list[str]:
    """
    Lightweight sentence splitter. Not linguistically perfect (won't handle
    every abbreviation), but adequate for chunking — a slightly-off sentence
    boundary inside a chunk doesn't hurt retrieval.

    Splits after . ! ? when followed by whitespace and a capital/number.
    """
    # Keep the delimiter attached to the sentence it ends.
    pieces = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [p.strip() for p in pieces if p.strip()]


# ---------------------------------------------------------------------------
# Packing units into overlapping chunks
# ---------------------------------------------------------------------------

def _pack_units(units: list[str]) -> list[str]:
    """
    Greedily pack text units into chunks up to TARGET_TOKENS, then start a
    new chunk that begins with OVERLAP_TOKENS worth of trailing context
    from the previous chunk.

    Returns a list of chunk texts (strings); metadata is attached later.
    """
    chunks: list[str] = []
    current: list[str] = []        # units in the chunk being built
    current_tokens = 0

    for unit in units:
        unit_tokens = _count_tokens(unit)

        # If adding this unit would overflow and we already have content,
        # close the current chunk first.
        if current and current_tokens + unit_tokens > TARGET_TOKENS:
            chunk_text = "\n\n".join(current)
            chunks.append(chunk_text)

            # Seed the next chunk with overlap drawn from the end of this one.
            overlap_units = _take_overlap(current)
            current = list(overlap_units)
            current_tokens = sum(_count_tokens(u) for u in current)

        current.append(unit)
        current_tokens += unit_tokens

    # Flush the final chunk.
    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _take_overlap(units: list[str]) -> list[str]:
    """
    Return the trailing units of a just-completed chunk whose combined token
    count is closest to (but not wildly over) OVERLAP_TOKENS. Walk backwards
    accumulating units until we hit the overlap budget.
    """
    overlap: list[str] = []
    tokens = 0
    for unit in reversed(units):
        unit_tokens = _count_tokens(unit)
        if tokens + unit_tokens > OVERLAP_TOKENS and overlap:
            break
        overlap.insert(0, unit)
        tokens += unit_tokens
    return overlap


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def chunk_section(section: Section) -> list[Chunk]:
    """
    Split one Section into a list of Chunk objects.

    Each chunk's metadata carries the section's identity plus the chunk's
    own index (within this section) and token count.
    """
    units = _split_into_units(section.text)
    chunk_texts = _pack_units(units)

    chunks: list[Chunk] = []
    for idx, text in enumerate(chunk_texts):
        chunks.append(
            Chunk(
                text=text,
                metadata={
                    "ticker": section.ticker,
                    "filing_type": section.filing_type,
                    "filing_date": section.filing_date,
                    "item": section.item,
                    "item_title": section.item_title,
                    "doc_type": getattr(section, "doc_type", "10-K"),  # NEW
                    "chunk_idx": idx,
                    "token_count": _count_tokens(text),
                },
            )
        )
    return chunks


def chunk_filing(sections: list[Section]) -> list[Chunk]:
    """Map chunk_section over all sections in a filing."""
    all_chunks: list[Chunk] = []
    for section in sections:
        all_chunks.extend(chunk_section(section))
    return all_chunks