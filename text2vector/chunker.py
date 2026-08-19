"""
Text chunking utilities.

Strategy:
  1. Split by paragraph (blank lines).
  2. Split each paragraph into sentences (Chinese + English punctuation).
  3. Greedily merge sentences into chunks up to `max_chars`, preferring to
     break at paragraph boundaries.
  4. If a single sentence exceeds `max_chars`, fall back to clause splits
     (，；：,;:) and finally hard character-count splits as a last resort.
"""

import re
from typing import List

# Sentence-ending punctuation (Chinese + English).
# English: must be followed by whitespace + uppercase or Chinese char to avoid
# splitting on "3.14" or "Dr. Smith".
_SENTENCE_END = re.compile(
    r"(?<=[。！？…])"
    r"|(?<=[!?])"
    r"|(?<=\.)\s+(?=[A-Z\u4e00-\u9fff])"
)

# Clause-level punctuation used as a last-resort split point.
_CLAUSE_END = re.compile(r"(?<=[，,；;：:])")

# Paragraph separator: one or more blank lines.
_PARA_SEP = re.compile(r"\n[ \t]*\n")


def _split_sentences(text: str) -> List[str]:
    parts = _SENTENCE_END.split(text)
    return [p.strip() for p in parts if p.strip()]


def _force_split(text: str, max_chars: int) -> List[str]:
    """Split a single over-long string that has no sentence boundaries."""
    # Try clause punctuation first.
    parts = _CLAUSE_END.split(text)
    chunks: List[str] = []
    buf = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) > max_chars:
            # Hard split: no natural boundary at all.
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(part), max_chars):
                chunks.append(part[i : i + max_chars])
        elif not buf:
            buf = part
        elif len(buf) + len(part) <= max_chars:
            buf += part
        else:
            chunks.append(buf)
            buf = part
    if buf:
        chunks.append(buf)
    return chunks


def chunk_text(text: str, max_chars: int = 500) -> List[str]:
    """
    Split *text* into chunks no longer than *max_chars* characters.

    Chunks respect paragraph and sentence boundaries — text is never cut
    mid-sentence unless a single sentence itself exceeds *max_chars*.

    Args:
        text:      The source text (may contain newlines / paragraphs).
        max_chars: Soft upper limit per chunk (characters, not tokens).

    Returns:
        A list of non-empty strings.
    """
    if not text or not text.strip():
        return []

    # --- Step 1: parse into atomic units (sentence + paragraph index) -------
    paragraphs = _PARA_SEP.split(text)

    # Each unit: (sentence_text, paragraph_index)
    units: List[tuple[str, int]] = []
    for para_idx, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue
        for sent in _split_sentences(para):
            units.append((sent, para_idx))
        # If no sentence boundary was found, _split_sentences returns the whole
        # paragraph as one unit — that is intentional.

    # --- Step 2: greedy merge ------------------------------------------------
    chunks: List[str] = []
    buf = ""
    buf_para: int = -1

    def flush():
        nonlocal buf, buf_para
        if buf:
            chunks.append(buf)
        buf = ""
        buf_para = -1

    for sent, para_idx in units:
        # Handle over-long single sentences immediately.
        if len(sent) > max_chars:
            flush()
            chunks.extend(_force_split(sent, max_chars))
            continue

        # Determine separator when appending to current buffer.
        if not buf:
            buf = sent
            buf_para = para_idx
            continue

        sep = "\n\n" if para_idx != buf_para else ""
        candidate = buf + sep + sent

        if len(candidate) <= max_chars:
            buf = candidate
            buf_para = para_idx
        else:
            flush()
            buf = sent
            buf_para = para_idx

    flush()
    return chunks
