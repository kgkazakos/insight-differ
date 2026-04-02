"""Tests for insight_differ.extractor"""

import pytest
from insight_differ.extractor import extract_segments

SHORT_PARA = "Users like fast checkout."  # Below MIN_WORDS threshold

SIMPLE_TEXT = """
Users consistently found the payment step confusing and disconnected from the rest of the flow.

Trust was the dominant concern. Participants frequently paused to check for security indicators before proceeding.

One-tap payments were strongly preferred by all participants who had them configured on their devices.
"""

BULLET_TEXT = """
Key findings from the study:

- Users prefer one-tap payment options over manual card entry for speed.
- Form field validation errors caused significant friction during checkout.
- Auto-fill worked reliably on iOS but failed on Android in several sessions.
- Progress indicators were largely ignored by participants throughout the study.
"""

LONG_PARA = """This study recruited twenty-four participants who were active users of the platform with at least two prior purchase completions logged in the system before screening. The checkout experience was observed across both iOS and Android devices over a two-week period. Researchers captured think-aloud protocols and session recordings for later analysis. Trust emerged as the dominant theme across all observed sessions, with participants frequently verbalising uncertainty at the payment step and checking for visual security indicators before entering payment credentials.
"""

MARKDOWN_HEADERS = """
# Mobile Checkout Study

## Key Findings

Users found the payment step confusing and disconnected from the browsing experience.

### Trust Signals

Participants looked for HTTPS and padlock indicators before entering card details on any screen.
"""


class TestExtractSegments:
    def test_returns_list(self):
        segs = extract_segments(SIMPLE_TEXT, "A")
        assert isinstance(segs, list)

    def test_source_label(self):
        segs = extract_segments(SIMPLE_TEXT, "A")
        assert all(s.source == "A" for s in segs)

    def test_source_label_b(self):
        segs = extract_segments(SIMPLE_TEXT, "B")
        assert all(s.source == "B" for s in segs)

    def test_ids_unique(self):
        segs = extract_segments(SIMPLE_TEXT, "A")
        ids = [s.id for s in segs]
        assert len(ids) == len(set(ids))

    def test_minimum_word_count(self):
        segs = extract_segments(SIMPLE_TEXT, "A")
        for s in segs:
            assert len(s.text.split()) >= 8, f"Segment too short: '{s.text}'"

    def test_extracts_multiple_segments(self):
        segs = extract_segments(SIMPLE_TEXT, "A")
        assert len(segs) >= 3

    def test_bullet_list_extraction(self):
        segs = extract_segments(BULLET_TEXT, "A")
        assert len(segs) >= 3

    def test_bullet_content_preserved(self):
        segs = extract_segments(BULLET_TEXT, "A")
        texts = " ".join(s.text for s in segs)
        assert "one-tap" in texts.lower() or "payment" in texts.lower()

    def test_long_paragraph_split(self):
        segs = extract_segments(LONG_PARA, "A")
        # A long paragraph should be split into multiple segments
        assert len(segs) >= 2

    def test_markdown_headers_excluded(self):
        segs = extract_segments(MARKDOWN_HEADERS, "A")
        texts = " ".join(s.text for s in segs)
        # Headers should not appear as segment content
        assert "#" not in texts

    def test_no_duplicate_segments(self):
        repeated = SIMPLE_TEXT + "\n\n" + SIMPLE_TEXT
        segs = extract_segments(repeated, "A")
        texts = [s.text.lower() for s in segs]
        assert len(texts) == len(set(texts))

    def test_short_only_text_returns_empty(self):
        segs = extract_segments(SHORT_PARA, "A")
        assert segs == []

    def test_empty_text_returns_empty(self):
        segs = extract_segments("", "A")
        assert segs == []

    def test_fixture_report_a(self):
        from pathlib import Path
        text = Path("tests/fixtures/report_a.txt").read_text()
        segs = extract_segments(text, "A")
        assert len(segs) >= 5

    def test_fixture_report_b(self):
        from pathlib import Path
        text = Path("tests/fixtures/report_b.txt").read_text()
        segs = extract_segments(text, "B")
        assert len(segs) >= 5
