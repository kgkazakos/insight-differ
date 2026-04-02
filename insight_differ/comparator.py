"""Rule-based comparison engine for research report diffing."""

from typing import List, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import Contradiction, DiffResult, Gap, Overlap, Segment

# ─── Thresholds ────────────────────────────────────────────────────────────────
# Pairs above this are likely talking about the same claim
OVERLAP_THRESHOLD = 0.52

# Pairs in this band on the same topic but diverging
CONTRADICTION_SIM_MIN = 0.22
CONTRADICTION_SIM_MAX = OVERLAP_THRESHOLD

# Pairs below this threshold → the segment has no meaningful coverage in the other report
GAP_THRESHOLD = 0.22

# Negation / contradiction markers
_NEGATION_WORDS: Set[str] = {
    "not",
    "no",
    "never",
    "neither",
    "nor",
    "lack",
    "lacking",
    "failed",
    "fails",
    "cannot",
    "unable",
    "unlikely",
    "rarely",
    "didn't",
    "doesn't",
    "wasn't",
    "weren't",
    "don't",
    "won't",
    "wouldn't",
    "couldn't",
}

_CONTRAST_PHRASES: List[str] = [
    "however",
    "contrary to",
    "unlike",
    "in contrast",
    "on the other hand",
    "whereas",
    "but rather",
    "despite",
    "although",
    "even though",
    "contradict",
    "contradicts",
    "disagrees",
    "inconsistent",
    "different from",
    "opposite",
]


def _negation_score(text_a: str, text_b: str) -> float:
    """
    Estimate how likely two thematically similar segments are contradicting
    each other rather than agreeing.

    Returns a float in [0, 1]; higher means more likely contradictory.
    """
    la = text_a.lower()
    lb = text_b.lower()
    combined = la + " " + lb

    # Exact contrast phrases are the strongest signal
    if any(p in combined for p in _CONTRAST_PHRASES):
        return 0.75

    words_a = set(la.split())
    words_b = set(lb.split())

    neg_a = bool(words_a & _NEGATION_WORDS)
    neg_b = bool(words_b & _NEGATION_WORDS)

    # One says "not X", the other asserts X — classic contradiction pattern
    if neg_a != neg_b:
        return 0.65

    # Both contain negation but they may be aligned ("neither A nor B")
    if neg_a and neg_b:
        return 0.35

    return 0.05


def _build_tfidf_matrix(
    segments_a: List[Segment], segments_b: List[Segment]
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Vectorise both segment lists together then split into two matrices.

    Returns (sim_matrix, tfidf_all) where sim_matrix has shape (len_a, len_b).
    """
    texts_a = [s.text for s in segments_a]
    texts_b = [s.text for s in segments_b]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        sublinear_tf=True,
        max_features=10_000,
    )
    tfidf = vectorizer.fit_transform(texts_a + texts_b)

    tfidf_a = tfidf[: len(texts_a)]
    tfidf_b = tfidf[len(texts_a) :]

    sim_matrix = cosine_similarity(tfidf_a, tfidf_b)
    return sim_matrix, tfidf


def compare_reports(
    segments_a: List[Segment],
    segments_b: List[Segment],
    overlap_threshold: float = OVERLAP_THRESHOLD,
    gap_threshold: float = GAP_THRESHOLD,
    max_per_category: int = 15,
) -> DiffResult:
    """
    Compare two lists of segments and return a structured DiffResult.

    The algorithm:
    1. TF-IDF vectorise all segments jointly.
    2. Compute A×B cosine similarity matrix.
    3. High-similarity pairs → check for negation → overlap or contradiction.
    4. Moderate-similarity pairs with strong negation markers → contradiction.
    5. Segments with no partner above gap_threshold → gap.

    Args:
        segments_a: Segments from Report A.
        segments_b: Segments from Report B.
        overlap_threshold: Cosine similarity above which segments are considered
            to cover the same claim.
        gap_threshold: Cosine similarity below which a segment is considered
            unaddressed in the other report.
        max_per_category: Cap on items per category to keep output readable.

    Returns:
        DiffResult with overlaps, contradictions, and gaps populated.
    """
    if not segments_a or not segments_b:
        return DiffResult(
            metadata={
                "error": "One or both reports produced no usable segments.",
                "segments_a": len(segments_a),
                "segments_b": len(segments_b),
            }
        )

    sim_matrix, _ = _build_tfidf_matrix(segments_a, segments_b)

    overlaps: List[Overlap] = []
    contradictions: List[Contradiction] = []

    # Collect all candidate pairs and sort by similarity descending
    # so we process the most confident matches first
    all_pairs = []
    for i in range(len(segments_a)):
        for j in range(len(segments_b)):
            all_pairs.append((float(sim_matrix[i, j]), i, j))
    all_pairs.sort(reverse=True)

    # Track which segments have been "claimed" (we still allow them in gaps
    # but mark overlap/contradiction only once per segment pair)
    seen_pairs: Set[Tuple[int, int]] = set()

    for sim, i, j in all_pairs:
        if (i, j) in seen_pairs:
            continue

        seg_a = segments_a[i]
        seg_b = segments_b[j]

        if sim >= overlap_threshold:
            neg = _negation_score(seg_a.text, seg_b.text)
            if neg >= 0.60:
                if len(contradictions) < max_per_category:
                    contradictions.append(
                        Contradiction(
                            segment_a=seg_a,
                            segment_b=seg_b,
                            similarity=sim,
                            contradiction_score=neg,
                        )
                    )
            else:
                if len(overlaps) < max_per_category:
                    overlaps.append(
                        Overlap(segment_a=seg_a, segment_b=seg_b, similarity=sim)
                    )
            seen_pairs.add((i, j))

        elif CONTRADICTION_SIM_MIN <= sim < overlap_threshold:
            neg = _negation_score(seg_a.text, seg_b.text)
            if neg >= 0.55 and len(contradictions) < max_per_category:
                contradictions.append(
                    Contradiction(
                        segment_a=seg_a,
                        segment_b=seg_b,
                        similarity=sim,
                        contradiction_score=neg,
                    )
                )
                seen_pairs.add((i, j))

        else:
            # Below any relevant threshold — no further pairs will be interesting
            break

    # Identify gaps
    gaps: List[Gap] = []

    for i, seg_a in enumerate(segments_a):
        max_sim = float(np.max(sim_matrix[i, :]))
        if max_sim < gap_threshold and len(gaps) < max_per_category:
            gaps.append(Gap(segment=seg_a, missing_from="B"))

    for j, seg_b in enumerate(segments_b):
        max_sim = float(np.max(sim_matrix[:, j]))
        if max_sim < gap_threshold and len(gaps) < max_per_category:
            gaps.append(Gap(segment=seg_b, missing_from="A"))

    # Sort final lists
    overlaps.sort(key=lambda x: x.similarity, reverse=True)
    contradictions.sort(key=lambda x: x.contradiction_score, reverse=True)

    return DiffResult(
        overlaps=overlaps,
        contradictions=contradictions,
        gaps=gaps,
        metadata={
            "segments_a": len(segments_a),
            "segments_b": len(segments_b),
            "overlap_threshold": overlap_threshold,
            "gap_threshold": gap_threshold,
        },
    )
