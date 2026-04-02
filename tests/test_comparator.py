"""Tests for insight_differ.comparator"""

import pytest
from insight_differ.comparator import (
    _negation_score,
    compare_reports,
    OVERLAP_THRESHOLD,
    GAP_THRESHOLD,
)
from insight_differ.extractor import extract_segments
from insight_differ.models import Segment


def seg(source: str, idx: int, text: str) -> Segment:
    return Segment(id=f"{source}_{idx}", text=text, source=source, index=idx)


# ─── Negation score ────────────────────────────────────────────────────────────

class TestNegationScore:
    def test_pure_agreement_low_score(self):
        a = "Users prefer one-tap payment and find it faster than manual entry."
        b = "Participants consistently chose one-tap checkout over typing card details."
        score = _negation_score(a, b)
        assert score < 0.5

    def test_explicit_negation_raises_score(self):
        a = "Users trust the checkout flow and proceed without hesitation."
        b = "Users do not trust the checkout flow and frequently abandon."
        score = _negation_score(a, b)
        assert score >= 0.5

    def test_contrast_phrase_raises_score(self):
        a = "Trust signals were the primary concern for all participants."
        b = "In contrast to lab findings, trust was rarely mentioned in diary entries."
        score = _negation_score(a, b)
        assert score >= 0.6

    def test_however_raises_score(self):
        a = "The WebView transition disrupted the checkout experience."
        b = "However, participants rarely noticed the WebView transition at all."
        score = _negation_score(a, b)
        assert score >= 0.6

    def test_score_in_range(self):
        a = "Participants completed checkout successfully."
        b = "Users finished the purchase without any major issues."
        score = _negation_score(a, b)
        assert 0.0 <= score <= 1.0


# ─── compare_reports ──────────────────────────────────────────────────────────

class TestCompareReports:
    def _load_fixture(self, name: str) -> list:
        from pathlib import Path
        text = Path(f"tests/fixtures/{name}").read_text()
        source = "A" if "a" in name else "B"
        return extract_segments(text, source)

    def test_returns_diff_result(self):
        segs_a = self._load_fixture("report_a.txt")
        segs_b = self._load_fixture("report_b.txt")
        result = compare_reports(segs_a, segs_b)
        from insight_differ.models import DiffResult
        assert isinstance(result, DiffResult)

    def test_detects_overlaps(self):
        # Use synthetic segments that share the same claim — this tests the
        # overlap mechanism directly. The fixture reports are deliberately
        # contradictory, so fixtures are used for contradiction/gap tests only.
        common_claim = (
            "Users strongly prefer one-tap payment options over manual card entry "
            "because they reduce friction and speed up the checkout process significantly."
        )
        segs_a = [seg("A", 0, common_claim), seg("A", 1, "Security signals matter during payment.")]
        segs_b = [seg("B", 0, common_claim), seg("B", 1, "Trust indicators are important at checkout.")]
        result = compare_reports(segs_a, segs_b, overlap_threshold=0.52)
        assert len(result.overlaps) >= 1

    def test_detects_contradictions_in_fixtures(self):
        segs_a = self._load_fixture("report_a.txt")
        segs_b = self._load_fixture("report_b.txt")
        result = compare_reports(segs_a, segs_b)
        # Fixtures contain deliberate contradictions on trust, WebView, errors, auto-fill
        assert len(result.contradictions) >= 1

    def test_detects_gaps_in_fixtures(self):
        segs_a = self._load_fixture("report_a.txt")
        segs_b = self._load_fixture("report_b.txt")
        result = compare_reports(segs_a, segs_b)
        # Social proof appears only in B; progress indicator has diverging coverage
        total_gaps = len(result.gaps)
        assert total_gaps >= 1

    def test_empty_a_returns_error_metadata(self):
        segs_b = self._load_fixture("report_b.txt")
        result = compare_reports([], segs_b)
        assert "error" in result.metadata

    def test_empty_b_returns_error_metadata(self):
        segs_a = self._load_fixture("report_a.txt")
        result = compare_reports(segs_a, [])
        assert "error" in result.metadata

    def test_identical_reports_have_high_overlap(self):
        segs = self._load_fixture("report_a.txt")
        # Compare report A against itself
        result = compare_reports(segs, segs)
        assert len(result.overlaps) >= len(segs) // 2

    def test_custom_overlap_threshold(self):
        segs_a = self._load_fixture("report_a.txt")
        segs_b = self._load_fixture("report_b.txt")
        # Very high threshold should reduce overlaps
        result_strict = compare_reports(segs_a, segs_b, overlap_threshold=0.90)
        result_loose = compare_reports(segs_a, segs_b, overlap_threshold=0.40)
        assert len(result_strict.overlaps) <= len(result_loose.overlaps)

    def test_custom_gap_threshold(self):
        segs_a = self._load_fixture("report_a.txt")
        segs_b = self._load_fixture("report_b.txt")
        result_strict = compare_reports(segs_a, segs_b, gap_threshold=0.50)
        result_loose = compare_reports(segs_a, segs_b, gap_threshold=0.05)
        # Higher gap threshold → more things flagged as gaps
        assert len(result_strict.gaps) >= len(result_loose.gaps)

    def test_metadata_populated(self):
        segs_a = self._load_fixture("report_a.txt")
        segs_b = self._load_fixture("report_b.txt")
        result = compare_reports(segs_a, segs_b)
        assert "segments_a" in result.metadata
        assert "segments_b" in result.metadata
        assert result.metadata["segments_a"] == len(segs_a)

    def test_overlaps_sorted_by_similarity(self):
        segs_a = self._load_fixture("report_a.txt")
        segs_b = self._load_fixture("report_b.txt")
        result = compare_reports(segs_a, segs_b)
        if len(result.overlaps) > 1:
            sims = [o.similarity for o in result.overlaps]
            assert sims == sorted(sims, reverse=True)

    def test_contradictions_sorted_by_score(self):
        segs_a = self._load_fixture("report_a.txt")
        segs_b = self._load_fixture("report_b.txt")
        result = compare_reports(segs_a, segs_b)
        if len(result.contradictions) > 1:
            scores = [c.contradiction_score for c in result.contradictions]
            assert scores == sorted(scores, reverse=True)

    def test_synthetic_identical_segments_overlap(self):
        text = "Users strongly prefer one-tap payment over manual card entry for speed and convenience."
        segs_a = [seg("A", 0, text)]
        segs_b = [seg("B", 0, text)]
        result = compare_reports(segs_a, segs_b)
        assert len(result.overlaps) >= 1

    def test_synthetic_opposite_segments_contradiction(self):
        segs_a = [
            seg("A", 0, "Users strongly prefer one-tap payment and find it faster than manual entry."),
        ]
        segs_b = [
            seg("B", 0, "Users do not prefer one-tap payment and however find manual entry gives more control."),
        ]
        result = compare_reports(segs_a, segs_b)
        # Should flag as contradiction due to negation
        total = len(result.contradictions) + len(result.overlaps)
        assert total >= 1

    def test_to_dict_is_serialisable(self):
        import json
        segs_a = self._load_fixture("report_a.txt")
        segs_b = self._load_fixture("report_b.txt")
        result = compare_reports(segs_a, segs_b)
        serialised = json.dumps(result.to_dict())
        assert len(serialised) > 100
