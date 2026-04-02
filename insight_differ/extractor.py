"""Extracts meaningful segments from research report text."""

import re
from typing import List

from .models import Segment

# Minimum number of words for a segment to be kept
MIN_WORDS = 8
# Maximum words before we try to split a paragraph into sentences
PARA_SPLIT_THRESHOLD = 60

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
_WHITESPACE = re.compile(r"\s+")
_BULLET_PREFIX = re.compile(r"^[\s]*[-•*▸▪►·]\s+")
_NUMBERED_PREFIX = re.compile(r"^[\s]*\d+[.)]\s+")
_HEADER_LINE = re.compile(r"^#{1,6}\s+.+$", re.MULTILINE)


def _clean(text: str) -> str:
    """Normalise whitespace."""
    return _WHITESPACE.sub(" ", text).strip()


def _strip_prefix(text: str) -> str:
    """Remove bullet / numbered-list prefixes."""
    text = _BULLET_PREFIX.sub("", text)
    text = _NUMBERED_PREFIX.sub("", text)
    return text.strip()


def _word_count(text: str) -> int:
    return len(text.split())


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences using punctuation heuristics."""
    parts = _SENTENCE_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip()]


def extract_segments(text: str, source: str) -> List[Segment]:
    """
    Extract meaningful segments from a research report.

    Segments are extracted at the paragraph level first; long paragraphs are
    split into sentences. Bullet points and numbered lists are each treated as
    individual segments.

    Args:
        text: Raw report text.
        source: Label for this report ("A" or "B").

    Returns:
        List of Segment objects ordered as they appear in the text.
    """
    # Remove markdown headers — they're navigation, not findings
    text = _HEADER_LINE.sub("", text)

    # Split on blank lines to get paragraphs / bullet blocks
    raw_blocks = re.split(r"\n\s*\n", text)

    candidates: List[str] = []

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.splitlines()

        # If the block looks like a bullet list, treat each line as a candidate
        if all(_BULLET_PREFIX.match(ln) or _NUMBERED_PREFIX.match(ln) for ln in lines if ln.strip()):
            for line in lines:
                line = _clean(_strip_prefix(line))
                if _word_count(line) >= MIN_WORDS:
                    candidates.append(line)
        else:
            # Plain paragraph — split long ones into sentences
            para = _clean(block)
            if _word_count(para) > PARA_SPLIT_THRESHOLD:
                for sent in _split_sentences(para):
                    sent = _clean(sent)
                    if _word_count(sent) >= MIN_WORDS:
                        candidates.append(sent)
            else:
                if _word_count(para) >= MIN_WORDS:
                    candidates.append(para)

    segments: List[Segment] = []
    seen: set = set()

    for idx, text_candidate in enumerate(candidates):
        norm = text_candidate.lower()
        if norm in seen:
            continue
        seen.add(norm)
        segments.append(
            Segment(
                id=f"{source}_{idx}",
                text=text_candidate,
                source=source,
                index=idx,
            )
        )

    return segments
