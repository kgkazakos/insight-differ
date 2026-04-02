# insight-differ

**Compare two research reports and surface contradictions, overlaps, and gaps.**

`insight-differ` is a Python tool (CLI + Streamlit app) that takes two research reports and identifies where they agree, where they conflict, and what each covers that the other doesn't. It runs fully rule-based with no API keys required; LLM backends add a narrative synthesis layer on top.

Part of the **CPR Orbital** series — 40 open-source tools for AI-native product research infrastructure, shipping every Friday from March to December 2026.

---

## The problem

You run a lab study in Q3. Six months later a diary study revisits the same product area. You now have two substantial research reports, and a stakeholder asks: *"Do these contradict each other? What changed?"*

Reading both reports side by side, highlighting differences, and writing a comparison matrix by hand takes hours. Miss a contradiction and you've shipped a product decision on inconsistent evidence.

---

## What it does

- **Extracts segments** from both reports — paragraphs, sentences, bullet points — filtering out navigation noise like headers
- **Builds a TF-IDF similarity matrix** between every segment pair across the two reports
- **Detects overlaps** — segment pairs making the same or very similar claim (high cosine similarity, no negation signal)
- **Detects contradictions** — segment pairs on the same topic that diverge (negation words, contrast phrases like "however", "contrary to", "in contrast")
- **Detects gaps** — segments in one report with no meaningful counterpart in the other
- **Outputs JSON** for CI integration or downstream processing
- **Optional LLM narrative** — passes the structured diff to OpenAI, Anthropic, or Gemini for a methodological synthesis

---

## Quickstart

```bash
pip install insight-differ
```

### CLI

```bash
# Basic comparison
insight-differ diff study_q3.txt study_q4.txt

# With custom labels and JSON output
insight-differ diff study_q3.txt study_q4.txt \
  --name-a "Q3 Lab Study" \
  --name-b "Q4 Diary Study" \
  --json

# Save JSON to file
insight-differ diff a.txt b.txt --json --output diff_result.json

# Add LLM narrative (requires API key in environment)
insight-differ diff a.txt b.txt --llm-backend anthropic

# Inspect extracted segments (diagnostic)
insight-differ segments report_a.txt report_b.txt
```

### Streamlit app

```bash
pip install insight-differ streamlit
streamlit run app.py
```

Upload or paste both reports, adjust thresholds in the sidebar, and explore results across the Contradictions / Overlaps / Gaps / JSON tabs.

---

## LLM backends (all optional)

The tool works fully without any API key. LLM backends add a narrative synthesis layer — they do not affect the core diff logic.

| Backend | Extra | Env var |
|---------|-------|---------|
| OpenAI (gpt-4o-mini) | `pip install insight-differ[openai]` | `OPENAI_API_KEY` |
| Anthropic (claude-haiku-4-5-20251001) | `pip install insight-differ[anthropic]` | `ANTHROPIC_API_KEY` |
| Gemini (gemini-3.1-pro-preview) | `pip install insight-differ[gemini]` | `GEMINI_API_KEY` |

---

## How detection works

### Overlaps
Two segments are flagged as an overlap when their TF-IDF cosine similarity exceeds the `overlap_threshold` (default: 0.52) and no strong negation signal is present. Sorted by similarity descending.

### Contradictions
A pair is flagged as a contradiction when:
1. Similarity is above the band minimum (`0.22`) — both segments discuss the same topic
2. A negation signal is detected: one segment contains negation words (`not`, `never`, `lacks`…) while the other doesn't, or one contains explicit contrast phrases (`however`, `in contrast`, `contrary to`…)

Sorted by `contradiction_score` descending. This is a rule-based heuristic — it will produce false positives on ambiguous phrasing. The LLM backend provides a methodological review layer that catches these.

### Gaps
A segment is flagged as a gap when its maximum similarity to any segment in the other report is below `gap_threshold` (default: 0.22). Gaps are reported directionally — `missing_from: B` means the finding is in A but B never addresses it.

---

## CLI reference

```
insight-differ diff REPORT_A REPORT_B [OPTIONS]

Options:
  --name-a TEXT               Label for Report A  [default: Report A]
  --name-b TEXT               Label for Report B  [default: Report B]
  --overlap-threshold FLOAT   Cosine similarity threshold for overlaps  [default: 0.52]
  --gap-threshold FLOAT       Threshold below which a segment is a gap  [default: 0.22]
  --llm-backend [openai|anthropic|gemini]
                              Optional LLM backend for narrative enrichment
  --json                      Output JSON
  --output PATH               Write JSON to file

insight-differ segments REPORT_A REPORT_B
  Show extracted segments from both reports (diagnostic).
```

---

## JSON output schema

```json
{
  "report_a_name": "Q3 Lab Study",
  "report_b_name": "Q4 Diary Study",
  "summary": {
    "overlaps": 2,
    "contradictions": 4,
    "gaps_in_b": 3,
    "gaps_in_a": 5
  },
  "overlaps": [
    {
      "segment_a": { "id": "A_2", "text": "...", "source": "A", "index": 2 },
      "segment_b": { "id": "B_1", "text": "...", "source": "B", "index": 1 },
      "similarity": 0.681,
      "explanation": ""
    }
  ],
  "contradictions": [ ... ],
  "gaps": [
    {
      "segment": { "id": "A_5", "text": "...", "source": "A", "index": 5 },
      "missing_from": "B",
      "explanation": ""
    }
  ],
  "llm_narrative": null,
  "metadata": {
    "segments_a": 9,
    "segments_b": 10,
    "overlap_threshold": 0.52,
    "gap_threshold": 0.22
  }
}
```

---

## Input format

Both reports should be plain text (`.txt`) or Markdown (`.md`). The extractor handles:
- Paragraph-separated text (most common)
- Bullet and numbered lists (each item extracted as a separate segment)
- Markdown headers (stripped — navigation, not findings)

Minimum viable report: 4–5 paragraphs or bullet points with substantive research content.

---

## Part of the CPR Ecosystem

`insight-differ` is Tool 5 in the [CPR Orbital series](https://github.com/kgkazakos).

**Related tools:**
- [`transcript-cleaner`](https://github.com/kgkazakos/transcript-cleaner) — clean raw interview transcripts before they reach report stage
- [`qual-sniffer`](https://github.com/kgkazakos/qual-sniffer) — detect methodological weaknesses in the discussion guides that produced these reports
- [`survey-cleaner`](https://github.com/kgkazakos/survey-cleaner) — clean quantitative data that feeds mixed-methods reports
- `research-rubric` *(coming Apr 24)* — evaluate qualitative research quality across saturation, bias, and evidence dimensions

---

## Development

```bash
git clone https://github.com/kgkazakos/insight-differ
cd insight-differ
pip install -e ".[dev]"
pytest tests/ -v
ruff check insight_differ/
```

---

## License

MIT © Kostas Kazakos
