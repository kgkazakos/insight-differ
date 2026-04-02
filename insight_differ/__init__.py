"""insight-differ — compare two research reports to surface contradictions,
overlaps, and gaps.

Part of the CPR Orbital series: github.com/kgkazakos
"""

__version__ = "0.1.0"

from .comparator import compare_reports
from .extractor import extract_segments
from .models import Contradiction, DiffResult, Gap, Overlap, Segment

__all__ = [
    "compare_reports",
    "extract_segments",
    "Contradiction",
    "DiffResult",
    "Gap",
    "Overlap",
    "Segment",
]
