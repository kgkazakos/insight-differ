"""insight-differ · Streamlit UI

Compare two research reports and surface contradictions, overlaps, and gaps.
Part of the CPR Orbital series — github.com/kgkazakos
"""

import json

import streamlit as st

from insight_differ.comparator import compare_reports
from insight_differ.extractor import extract_segments
from insight_differ.models import DiffResult

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="insight-differ · CPR Orbital",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"]  { font-family: 'DM Sans', sans-serif; }
    code, .stCode { font-family: 'DM Mono', monospace !important; }

    .main-header {
        font-size: 1.6rem;
        font-weight: 600;
        letter-spacing: -0.03em;
        color: #111;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 0.85rem;
        color: #888;
        margin-top: 0;
        margin-bottom: 1.5rem;
    }
    .stat-card {
        background: #fafafa;
        border: 1px solid #e5e5e5;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        text-align: center;
    }
    .stat-num { font-size: 2rem; font-weight: 700; line-height: 1; }
    .stat-lbl { font-size: 0.75rem; color: #888; margin-top: 4px; }
    .segment-a {
        background: #e8f4fd;
        border-left: 3px solid #2196f3;
        padding: 0.6rem 0.9rem;
        border-radius: 4px;
        margin: 0.3rem 0;
        font-size: 0.88rem;
    }
    .segment-b {
        background: #fce8fd;
        border-left: 3px solid #9c27b0;
        padding: 0.6rem 0.9rem;
        border-radius: 4px;
        margin: 0.3rem 0;
        font-size: 0.88rem;
    }
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 99px;
        font-size: 0.72rem;
        font-weight: 500;
        margin-left: 6px;
    }
    .badge-sim  { background: #e3f2fd; color: #1565c0; }
    .badge-cont { background: #fce4ec; color: #b71c1c; }
    .badge-gap-a { background: #e8eaf6; color: #283593; }
    .badge-gap-b { background: #f3e5f5; color: #6a1b9a; }
    .narrative-box {
        background: #f9f9f9;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1.2rem 1.4rem;
        font-size: 0.9rem;
        line-height: 1.7;
        white-space: pre-wrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    overlap_threshold = st.slider(
        "Overlap threshold",
        min_value=0.30,
        max_value=0.80,
        value=0.52,
        step=0.01,
        help="Cosine similarity above which two segments are considered overlapping.",
    )
    gap_threshold = st.slider(
        "Gap threshold",
        min_value=0.10,
        max_value=0.40,
        value=0.22,
        step=0.01,
        help="Cosine similarity below which a segment has no meaningful counterpart.",
    )

    st.markdown("---")
    st.markdown("### 🤖 LLM Backend *(optional)*")
    llm_backend = st.selectbox(
        "Backend",
        ["None", "openai", "anthropic", "gemini"],
        index=0,
        help="Adds a narrative synthesis on top of the rule-based diff. Requires API key.",
    )
    if llm_backend != "None":
        st.caption(
            f"Requires `{llm_backend.upper()}_API_KEY` in your environment. "
            "The tool works fully without this."
        )

    st.markdown("---")
    st.caption("**insight-differ** · CPR Orbital Tool 5")
    st.caption("[github.com/kgkazakos](https://github.com/kgkazakos)")

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    '<p class="main-header">insight-differ</p>'
    '<p class="sub-header">Surface contradictions, overlaps, and gaps between two research reports</p>',
    unsafe_allow_html=True,
)

# ─── Input area ───────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2, gap="medium")

with col_a:
    st.markdown("#### 📄 Report A")
    name_a = st.text_input("Label", value="Report A", key="name_a")
    upload_a = st.file_uploader("Upload .txt or .md", type=["txt", "md"], key="upload_a")
    if upload_a:
        text_a = upload_a.read().decode("utf-8")
        st.text_area("Preview", text_a[:500] + ("…" if len(text_a) > 500 else ""), height=160, disabled=True)
    else:
        text_a = st.text_area(
            "Or paste text",
            height=260,
            key="text_a",
            placeholder="Paste your first research report here…",
        )

with col_b:
    st.markdown("#### 📄 Report B")
    name_b = st.text_input("Label", value="Report B", key="name_b")
    upload_b = st.file_uploader("Upload .txt or .md", type=["txt", "md"], key="upload_b")
    if upload_b:
        text_b = upload_b.read().decode("utf-8")
        st.text_area("Preview", text_b[:500] + ("…" if len(text_b) > 500 else ""), height=160, disabled=True)
    else:
        text_b = st.text_area(
            "Or paste text",
            height=260,
            key="text_b",
            placeholder="Paste your second research report here…",
        )

run_btn = st.button("🔍 Run comparison", type="primary", use_container_width=False)

# ─── Run ──────────────────────────────────────────────────────────────────────
if run_btn:
    if not text_a or not text_b:
        st.warning("Please provide both reports before running.")
        st.stop()

    with st.spinner("Extracting segments…"):
        segs_a = extract_segments(text_a, "A")
        segs_b = extract_segments(text_b, "B")

    if not segs_a or not segs_b:
        st.error(
            "One or both reports produced no usable segments. "
            "Make sure each report contains multiple sentences or paragraphs."
        )
        st.stop()

    with st.spinner("Comparing reports…"):
        result: DiffResult = compare_reports(
            segs_a,
            segs_b,
            overlap_threshold=overlap_threshold,
            gap_threshold=gap_threshold,
        )
        result.report_a_name = name_a
        result.report_b_name = name_b

    if llm_backend != "None":
        with st.spinner(f"Enriching with {llm_backend}…"):
            try:
                from insight_differ.llm import enrich
                result = enrich(result, llm_backend)
            except ImportError as e:
                st.warning(f"LLM backend unavailable: {e}")
            except Exception as e:
                st.warning(f"LLM call failed: {e}")

    # ─── Summary cards ────────────────────────────────────────────────────────
    st.markdown("---")
    summary = result.summary()
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f'<div class="stat-card"><div class="stat-num" style="color:#2e7d32">'
            f'{summary["overlaps"]}</div><div class="stat-lbl">Overlaps</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="stat-card"><div class="stat-num" style="color:#c62828">'
            f'{summary["contradictions"]}</div><div class="stat-lbl">Contradictions</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="stat-card"><div class="stat-num" style="color:#e65100">'
            f'{summary["gaps_in_b"]}</div><div class="stat-lbl">In A · not in B</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="stat-card"><div class="stat-num" style="color:#6a1b9a">'
            f'{summary["gaps_in_a"]}</div><div class="stat-lbl">In B · not in A</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ─── LLM narrative ────────────────────────────────────────────────────────
    if result.llm_narrative:
        st.markdown("### 🧠 LLM Narrative Synthesis")
        st.markdown(
            f'<div class="narrative-box">{result.llm_narrative}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")

    # ─── Tabs ─────────────────────────────────────────────────────────────────
    tab_contra, tab_overlaps, tab_gaps, tab_json = st.tabs(
        ["⚠️ Contradictions", "✅ Overlaps", "△ Gaps", "{ } JSON"]
    )

    with tab_contra:
        if not result.contradictions:
            st.info("No contradictions detected at the current threshold settings.")
        else:
            st.caption(
                f"**{len(result.contradictions)} contradiction(s)** — segments from A and B "
                "that appear to conflict. Sorted by contradiction score (highest first)."
            )
            for idx, c in enumerate(result.contradictions, 1):
                with st.expander(
                    f"#{idx}  sim={c.similarity:.2f}  "
                    f"contradiction_score={c.contradiction_score:.2f}  "
                    f"— {c.segment_a.text[:80]}…",
                    expanded=idx <= 3,
                ):
                    st.markdown(
                        f'<div class="segment-a"><strong>{name_a}</strong><br>{c.segment_a.text}</div>'
                        f'<div class="segment-b"><strong>{name_b}</strong><br>{c.segment_b.text}</div>',
                        unsafe_allow_html=True,
                    )
                    if c.explanation:
                        st.caption(c.explanation)

    with tab_overlaps:
        if not result.overlaps:
            st.info("No overlaps detected at the current threshold settings.")
        else:
            st.caption(
                f"**{len(result.overlaps)} overlap(s)** — segments making the same or very "
                "similar claims. Sorted by similarity (highest first)."
            )
            for idx, o in enumerate(result.overlaps, 1):
                with st.expander(
                    f"#{idx}  sim={o.similarity:.2f}  — {o.segment_a.text[:80]}…",
                    expanded=idx <= 3,
                ):
                    st.markdown(
                        f'<div class="segment-a"><strong>{name_a}</strong><br>{o.segment_a.text}</div>'
                        f'<div class="segment-b"><strong>{name_b}</strong><br>{o.segment_b.text}</div>',
                        unsafe_allow_html=True,
                    )

    with tab_gaps:
        gaps_b = result.gaps_in_b
        gaps_a = result.gaps_in_a

        if not gaps_b and not gaps_a:
            st.info("No gaps detected — both reports appear to have broad coverage overlap.")
        else:
            if gaps_b:
                st.markdown(f"##### In **{name_a}** · not addressed in **{name_b}**")
                st.caption(f"{len(gaps_b)} segment(s) from {name_a} have no meaningful counterpart in {name_b}.")
                for g in gaps_b:
                    st.markdown(
                        f'<div class="segment-a">{g.segment.text}</div>',
                        unsafe_allow_html=True,
                    )

            if gaps_a:
                st.markdown(f"##### In **{name_b}** · not addressed in **{name_a}**")
                st.caption(f"{len(gaps_a)} segment(s) from {name_b} have no meaningful counterpart in {name_a}.")
                for g in gaps_a:
                    st.markdown(
                        f'<div class="segment-b">{g.segment.text}</div>',
                        unsafe_allow_html=True,
                    )

    with tab_json:
        json_str = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
        st.code(json_str, language="json")
        st.download_button(
            label="⬇️ Download JSON",
            data=json_str,
            file_name="insight_diff.json",
            mime="application/json",
        )

    # ─── Metadata ─────────────────────────────────────────────────────────────
    with st.expander("Extraction metadata", expanded=False):
        st.json(result.metadata)
        st.caption(
            f"{name_a}: {result.metadata.get('segments_a', '?')} segments  ·  "
            f"{name_b}: {result.metadata.get('segments_b', '?')} segments"
        )
