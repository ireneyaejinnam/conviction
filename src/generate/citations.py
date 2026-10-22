"""
Parse [Source N] citations out of an answer. Shared by the eval (citation
rows to hand-label) and the API's request log (cited_sources).
"""

from __future__ import annotations

import re

# "[Source 3]", "[Source 4, Source 5]", "[Sources 1, 2]"
CITATION_RE = re.compile(r"\[Sources?\s*\d+(?:\s*,\s*(?:Source\s*)?\d+)*\]", re.I)


def source_numbers(citation: str) -> list[int]:
    """The source numbers in one citation match, e.g. "[Sources 1, 2]" -> [1, 2]."""
    return [int(x) for x in re.findall(r"\d+", citation)]


def cited_sources(text: str) -> list[int]:
    """Every distinct source number cited in text, sorted."""
    return sorted({n for c in CITATION_RE.findall(text) for n in source_numbers(c)})
