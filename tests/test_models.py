"""Tests for insight_differ.models"""

import json
import pytest
from insight_differ.models import (
    Contradiction,
    DiffResult,
    Gap,
    Overlap,
    Segment,
)


def make_seg(source: str = "A", idx: int = 0, text: str = "Users prefer faster checkout flows.") -> Segment:
    return Segment(id=f"{source}_{idx}", text=text, source=source, index=idx)


class TestSegment:
    def test_to_dict_keys(self):
        s = make_seg()
        d = s.to_dict()
        assert set(d.keys()) == {"id", "text", "source", "index"}

    def test_to_dict_values(self):
        s = make_seg("B", 3, "Trust matters during payment.")
        d = s.to_dict()
        assert d["source"] == "B"
        assert d["index"] == 3


class TestOverlap:
    def test_to_dict(self):
        o = Overlap(
            segment_a=make_seg("A", 0),
            segment_b=make_seg("B", 0),
            similarity=0.72,
            explanation="Both discuss checkout speed.",
        )
        d = o.to_dict()
        assert d["similarity"] == 0.72
        assert "segment_a" in d
        assert "segment_b" in d

    def test_similarity_rounded(self):
        o = Overlap(make_seg("A"), make_seg("B"), similarity=0.123456789)
        assert o.to_dict()["similarity"] == 0.123


class TestContradiction:
    def test_to_dict(self):
        c = Contradiction(
            segment_a=make_seg("A"),
            segment_b=make_seg("B"),
            similarity=0.45,
            contradiction_score=0.75,
        )
        d = c.to_dict()
        assert "contradiction_score" in d
        assert d["contradiction_score"] == 0.75

    def test_scores_rounded(self):
        c = Contradiction(make_seg("A"), make_seg("B"), 0.456789, 0.654321)
        d = c.to_dict()
        assert d["similarity"] == 0.457
        assert d["contradiction_score"] == 0.654


class TestGap:
    def test_missing_from_b(self):
        g = Gap(segment=make_seg("A", 1, "Mobile users have distinct needs."), missing_from="B")
        d = g.to_dict()
        assert d["missing_from"] == "B"

    def test_missing_from_a(self):
        g = Gap(segment=make_seg("B", 2, "Desktop patterns differ."), missing_from="A")
        d = g.to_dict()
        assert d["missing_from"] == "A"


class TestDiffResult:
    def _make_result(self) -> DiffResult:
        seg_a = make_seg("A", 0, "Users abandon when errors appear in payment forms.")
        seg_b1 = make_seg("B", 0, "Users rarely abandon due to form errors in checkout.")
        seg_b2 = make_seg("B", 1, "Trust signals are important during payment.")
        return DiffResult(
            overlaps=[Overlap(make_seg("A", 2, "Speed matters."), seg_b2, similarity=0.6)],
            contradictions=[Contradiction(seg_a, seg_b1, similarity=0.55, contradiction_score=0.8)],
            gaps=[
                Gap(make_seg("A", 3, "Mobile auto-fill is unreliable on Android devices."), missing_from="B"),
                Gap(make_seg("B", 4, "Social proof affects payment decisions significantly."), missing_from="A"),
            ],
            report_a_name="Q3 Study",
            report_b_name="Q4 Study",
        )

    def test_summary(self):
        r = self._make_result()
        s = r.summary()
        assert s["overlaps"] == 1
        assert s["contradictions"] == 1
        assert s["gaps_in_b"] == 1
        assert s["gaps_in_a"] == 1

    def test_gaps_in_b_property(self):
        r = self._make_result()
        assert all(g.missing_from == "B" for g in r.gaps_in_b)

    def test_gaps_in_a_property(self):
        r = self._make_result()
        assert all(g.missing_from == "A" for g in r.gaps_in_a)

    def test_to_dict_keys(self):
        r = self._make_result()
        d = r.to_dict()
        assert "overlaps" in d
        assert "contradictions" in d
        assert "gaps" in d
        assert "summary" in d
        assert "llm_narrative" in d

    def test_to_dict_is_json_serialisable(self):
        r = self._make_result()
        serialised = json.dumps(r.to_dict())
        parsed = json.loads(serialised)
        assert parsed["report_a_name"] == "Q3 Study"

    def test_llm_narrative_none_by_default(self):
        r = DiffResult()
        assert r.llm_narrative is None

    def test_empty_result_summary(self):
        r = DiffResult()
        s = r.summary()
        assert all(v == 0 for v in s.values())
