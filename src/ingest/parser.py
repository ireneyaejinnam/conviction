"""
Parse a downloaded SEC 10-K filing into structured Section objects.

Input: full-submission.txt path returned by fetch_filing().
Output: list of Section objects for Items 1, 1A, 7, and 8.

Two-stage problem:
  1. The input is an SGML container holding multiple <DOCUMENT> blocks
     (the 10-K plus exhibits/XBRL). We extract the main 10-K HTML.
  2. 10-K HTML has no reliable machine-readable section markers, so we
     locate "Item N" headers via regex on the cleaned text and slice
     between them.

This is a "good enough for V1" parser. Filings vary wildly in formatting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Section:
    ticker: str
    filing_type: str
    filing_date: str          # "2025-02-26" or ""
    item: str                 # "Item 1A"
    item_title: str           # "Risk Factors"
    text: str
    source_path: str
    doc_type: str = "10-K"

    def __repr__(self) -> str:
        return (
            f"Section({self.ticker} {self.filing_type} {self.item} "
            f"'{self.item_title}' {len(self.text)} chars)"
        )


# ---------------------------------------------------------------------------
# Target items. Order matters: we use the sequence to find each item's
# END (= the next item's START). The "next item after 8" anchor lets us
# bound Item 8 without parsing everything after it.
# ---------------------------------------------------------------------------

TARGET_ITEMS = {
    "Item 1":  "Business",
    "Item 1A": "Risk Factors",
    "Item 7":  "Management's Discussion and Analysis",
    "Item 8":  "Financial Statements and Supplementary Data",
}

# Items we use only as END anchors (to know where a target item stops).
# Item 1B follows 1A; Item 2 follows 1; Item 7A follows 7; Item 9 follows 8.
ANCHOR_ITEMS = ["Item 1B", "Item 2", "Item 7A", "Item 9"]


# ---------------------------------------------------------------------------
# Stage 1: pull the main 10-K document out of the SGML container
# ---------------------------------------------------------------------------

def _extract_main_document(raw: str) -> str:
    """
    The full-submission.txt is an SGML wrapper with multiple <DOCUMENT>
    blocks. Return the HTML/text of the first one whose <TYPE> is 10-K.
    Falls back to the whole file if the structure isn't found.
    """
    # Each document block looks like:
    #   <DOCUMENT>
    #   <TYPE>10-K
    #   <SEQUENCE>1
    #   ...
    #   <TEXT>
    #   ...actual filing html...
    #   </TEXT>
    #   </DOCUMENT>
    doc_blocks = re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", raw, re.DOTALL)

    for block in doc_blocks:
        type_match = re.search(r"<TYPE>\s*([^\s<]+)", block)
        if type_match and type_match.group(1).upper().startswith("10-K"):
            # Grab the content inside <TEXT>...</TEXT> if present,
            # else the whole block.
            text_match = re.search(r"<TEXT>(.*?)</TEXT>", block, re.DOTALL)
            return text_match.group(1) if text_match else block

    # Fallback: no clean structure found, return everything.
    return raw


def _extract_filing_date(raw: str) -> str:
    """
    Pull the filing date from the SGML header. EDGAR headers contain a
    line like 'FILED AS OF DATE: 20250226'. Returns ISO format or "".
    """
    m = re.search(r"FILED AS OF DATE:\s*(\d{8})", raw)
    if not m:
        # Alternate header field sometimes present.
        m = re.search(r"<acceptance-datetime>(\d{8})", raw)
    if m:
        d = m.group(1)
        return f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
    return ""


# ---------------------------------------------------------------------------
# Stage 2: HTML -> clean text
# ---------------------------------------------------------------------------

def _html_to_text(html: str) -> str:
    """
    Convert filing HTML to plain text. Uses a separator so that block-level
    elements don't get concatenated into run-on words, which would break
    Item-header detection.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Remove script/style noise.
    for tag in soup(["script", "style"]):
        tag.decompose()

    # get_text with a separator keeps token boundaries intact.
    text = soup.get_text(separator="\n")

    # Normalize whitespace: collapse runs of blank lines, strip trailing
    # spaces, and replace the non-breaking spaces filings love to use.
    text = text.replace("\xa0", " ")
    # Collapse 3+ newlines to 2.
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing spaces on each line.
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text


# ---------------------------------------------------------------------------
# Stage 3: find item boundaries
# ---------------------------------------------------------------------------

def _item_pattern(item_id: str) -> re.Pattern:
    """
    Build a regex matching an item header like 'Item 1A' at the start of
    a line, tolerant of:
      - varying whitespace
      - an optional period or colon after the number ('Item 1A.' / 'Item 1A:')
      - case insensitivity
    e.g. item_id 'Item 1A' -> matches 'Item 1A.', 'ITEM 1A', 'Item  1A:'
    """
    # Split 'Item 1A' into 'Item' + '1A'
    number = item_id.split(maxsplit=1)[1]
    # \b around the number prevents 'Item 1' from matching 'Item 1A'.
    pattern = rf"(?im)^\s*item\s+{re.escape(number)}\b[\.\:\s]"
    return re.compile(pattern)


def _find_all_item_positions(text: str) -> list[tuple[int, str]]:
    """
    Find character positions of every target + anchor item header in the
    text. Returns a sorted list of (position, item_id).

    Key subtlety: each item typically appears TWICE — once in the table
    of contents near the top, once at the real section. We want the real
    section, which is the LAST occurrence. So for each item we take the
    match with the greatest position.
    """
    all_items = list(TARGET_ITEMS.keys()) + ANCHOR_ITEMS
    positions: list[tuple[int, str]] = []

    for item_id in all_items:
        matches = list(_item_pattern(item_id).finditer(text))
        if matches:
            # Take the last occurrence (skips the table-of-contents hit).
            positions.append((matches[-1].start(), item_id))

    positions.sort()
    return positions


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_filing(filepath: str | Path, ticker: str) -> list[Section]:
    """
    Parse a downloaded 10-K into Section objects for Items 1, 1A, 7, 8.

    Args:
        filepath: path to full-submission.txt (from fetch_filing).
        ticker: stock ticker, used for metadata.

    Returns:
        List of Section objects, one per target item that was found.
        Items that can't be located are skipped (and their absence is a
        signal worth logging).
    """
    filepath = Path(filepath)
    raw = filepath.read_text(encoding="utf-8", errors="replace")

    filing_date = _extract_filing_date(raw)

    # primary-document.html has no SGML header; try sibling full-submission.txt
    if not filing_date and filepath.name != "full-submission.txt":
        fs = filepath.parent / "full-submission.txt"
        if fs.exists():
            filing_date = _extract_filing_date(
                fs.read_text(encoding="utf-8", errors="replace")
            )
    main_html = _extract_main_document(raw)
    text = _html_to_text(main_html)

    positions = _find_all_item_positions(text)

    # Build a lookup of where each item starts, so for a given target item
    # we can find the next header (of ANY kind) to mark its end.
    sections: list[Section] = []

    for i, (start, item_id) in enumerate(positions):
        if item_id not in TARGET_ITEMS:
            continue  # anchor-only item, not something we emit

        # End = start of the next header in the sorted list, or EOF.
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        body = text[start:end].strip()

        sections.append(
            Section(
                ticker=ticker.upper(),
                filing_type="10-K",
                filing_date=filing_date,
                item=item_id,
                item_title=TARGET_ITEMS[item_id],
                text=body,
                source_path=str(filepath),
            )
        )

    return sections
