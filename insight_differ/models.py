"""Core data models for insight-differ."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Segment:
    """A meaningful unit of text extracted from a research report."""

    id: str
    text: str
    source: str  # "A" or "B"
    index: int

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "text": self.text, "source": self.source, "index": self.index}


@dataclass
class Overlap:
    """Two segments from different reports that say the same or similar thing."""

    segment_a: Segment
    segment_b: Segment
    similarity: float
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_a": self.segment_a.to_dict(),
            "segment_b": self.segment_b.to_dict(),
            "similarity": round(self.similarity, 3),
            "explanation": self.explanation,
        }


@dataclass
class Contradiction:
    """Two segments from different reports that conflict with each other."""

    segment_a: Segment
    segment_b: Segment
    similarity: float
    contradiction_score: float
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_a": self.segment_a.to_dict(),
            "segment_b": self.segment_b.to_dict(),
            "similarity": round(self.similarity, 3),
            "contradiction_score": round(self.contradiction_score, 3),
            "explanation": self.explanation,
        }


@dataclass
class Gap:
    """A segment from one report with no meaningful coverage in the other."""

    segment: Segment
    missing_from: str  # "B" means: present in A, absent in B
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment": self.segment.to_dict(),
            "missing_from": self.missing_from,
            "explanation": self.explanation,
        }


@dataclass
class DiffResult:
    """The full comparison result between two research reports."""

    overlaps: List[Overlap] = field(default_factory=list)
    contradictions: List[Contradiction] = field(default_factory=list)
    gaps: List[Gap] = field(default_factory=list)
    report_a_name: str = "Report A"
    report_b_name: str = "Report B"
    llm_narrative: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def gaps_in_b(self) -> List[Gap]:
        """Segments present in A that B doesn't address."""
        return [g for g in self.gaps if g.missing_from == "B"]

    @property
    def gaps_in_a(self) -> List[Gap]:
        """Segments present in B that A doesn't address."""
        return [g for g in self.gaps if g.missing_from == "A"]

    def summary(self) -> Dict[str, int]:
        return {
            "overlaps": len(self.overlaps),
            "contradictions": len(self.contradictions),
            "gaps_in_b": len(self.gaps_in_b),
            "gaps_in_a": len(self.gaps_in_a),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_a_name": self.report_a_name,
            "report_b_name": self.report_b_name,
            "summary": self.summary(),
            "overlaps": [o.to_dict() for o in self.overlaps],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "gaps": [g.to_dict() for g in self.gaps],
            "llm_narrative": self.llm_narrative,
            "metadata": self.metadata,
        }
