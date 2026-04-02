"""Basic usage example for insight-differ."""

from insight_differ import compare_reports, extract_segments

# ─── Two short synthetic reports ──────────────────────────────────────────────

REPORT_A = """
Users consistently reported that the payment step felt disconnected and jarring.
The transition to a third-party WebView broke the sense of continuity that participants
had built up during browsing and cart review.

Trust was the dominant concern at the payment stage. Eighteen of twenty-four participants
explicitly checked for security indicators — the padlock icon and HTTPS — before entering
card details. Several participants paused for several seconds before proceeding.

One-tap payment options were strongly preferred by users who had them configured.
Participants described Apple Pay and Google Pay as frictionless and said the manual card
entry flow felt dated by comparison.

Form field validation errors were the most common cause of observed session abandonment.
Participants on smaller screens struggled to identify which field contained the error.
"""

REPORT_B = """
Contrary to the lab study findings, diary participants rarely noticed or reacted to
the WebView transition. Most described the checkout as a single continuous experience
regardless of the technical implementation underneath.

Security concerns were not prominent in the diary entries. Only two of sixteen participants
mentioned checking for security indicators. The majority proceeded directly without
any apparent hesitation or trust verification behaviour.

One-tap payment options were used when available but participants described them as
a convenience rather than a necessity. Several noted that they actively preferred
manual card entry for high-value purchases to maintain a sense of control.

Error recovery was less problematic than the lab study suggested. Participants who
encountered form errors generally resolved them quickly and did not abandon the purchase.
"""

# ─── Extract and compare ──────────────────────────────────────────────────────

segs_a = extract_segments(REPORT_A, "A")
segs_b = extract_segments(REPORT_B, "B")

print(f"Report A: {len(segs_a)} segments")
print(f"Report B: {len(segs_b)} segments\n")

result = compare_reports(segs_a, segs_b)
result.report_a_name = "Q3 Lab Study"
result.report_b_name = "Q4 Diary Study"

summary = result.summary()
print(f"Overlaps:       {summary['overlaps']}")
print(f"Contradictions: {summary['contradictions']}")
print(f"Gaps in B:      {summary['gaps_in_b']}")
print(f"Gaps in A:      {summary['gaps_in_a']}\n")

if result.contradictions:
    print("Top contradiction:")
    c = result.contradictions[0]
    print(f"  A: {c.segment_a.text[:120]}")
    print(f"  B: {c.segment_b.text[:120]}")
    print(f"  sim={c.similarity:.2f}  contradiction_score={c.contradiction_score:.2f}\n")

# ─── JSON output ─────────────────────────────────────────────────────────────

import json
print("Full JSON result:")
print(json.dumps(result.to_dict(), indent=2)[:800] + "\n…")
