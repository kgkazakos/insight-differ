"""Optional LLM enrichment for insight-differ.

All LLM calls are gated behind --llm-backend. The tool works fully without
any API keys; this module is only imported when a backend is requested.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import DiffResult

_SYSTEM_PROMPT = """You are a senior UX research methodologist reviewing a structured
comparison of two research reports. Your job is to produce a concise, rigorous
narrative synthesis — not a restatement of the raw data.

Focus on:
1. The most consequential contradiction and why it matters for product decisions.
2. The most critical gap and what it signals about research coverage.
3. Whether the overlaps reinforce or merely repeat findings.
4. A one-paragraph recommendation for the research team.

Be specific, methodologically grounded, and direct. Avoid hedging language."""


def _build_prompt(result: "DiffResult") -> str:
    summary = result.summary()
    lines = [
        f"Report A: {result.report_a_name}",
        f"Report B: {result.report_b_name}",
        "",
        f"Summary: {summary['overlaps']} overlaps, {summary['contradictions']} "
        f"contradictions, {summary['gaps_in_b']} gaps in B, {summary['gaps_in_a']} gaps in A.",
        "",
    ]

    if result.contradictions:
        lines.append("TOP CONTRADICTIONS:")
        for c in result.contradictions[:3]:
            lines.append(
                f"  A: \"{c.segment_a.text[:200]}\"\n"
                f"  B: \"{c.segment_b.text[:200]}\"\n"
                f"  similarity={c.similarity:.2f}, contradiction_score={c.contradiction_score:.2f}"
            )
        lines.append("")

    if result.overlaps:
        lines.append("TOP OVERLAPS:")
        for o in result.overlaps[:3]:
            lines.append(
                f"  A: \"{o.segment_a.text[:200]}\"\n"
                f"  B: \"{o.segment_b.text[:200]}\"\n"
                f"  similarity={o.similarity:.2f}"
            )
        lines.append("")

    if result.gaps:
        lines.append("TOP GAPS (sample):")
        for g in result.gaps[:4]:
            direction = f"present in {g.segment.source}, absent in {g.missing_from}"
            lines.append(f"  [{direction}] \"{g.segment.text[:200]}\"")
        lines.append("")

    lines.append("Provide your narrative synthesis.")
    return "\n".join(lines)


def enrich_openai(result: "DiffResult", model: str = "gpt-4o-mini") -> str:
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as exc:
        raise ImportError("Install openai: pip install insight-differ[openai]") from exc

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(result)},
        ],
        temperature=0.3,
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()


def enrich_anthropic(result: "DiffResult", model: str = "claude-haiku-4-5-20251001") -> str:
    try:
        import anthropic  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Install anthropic: pip install insight-differ[anthropic]"
        ) from exc

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=800,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(result)}],
    )
    return message.content[0].text.strip()


def enrich_gemini(result: "DiffResult", model: str = "gemini-4-argon") -> str:
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "Install google-genai: pip install insight-differ[gemini]"
        ) from exc

    client = genai.Client()
    response = client.models.generate_content(
        model=model,
        contents=_build_prompt(result),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            max_output_tokens=800,
            temperature=0.3,
        ),
    )
    return response.text.strip()


_BACKEND_MAP = {
    "openai": enrich_openai,
    "anthropic": enrich_anthropic,
    "gemini": enrich_gemini,
}


def enrich(result: "DiffResult", backend: str) -> "DiffResult":
    """
    Attach an LLM narrative to a DiffResult in-place and return it.

    Args:
        result: A completed DiffResult.
        backend: One of "openai", "anthropic", "gemini".

    Returns:
        The same DiffResult with llm_narrative populated.
    """
    backend = backend.lower()
    if backend not in _BACKEND_MAP:
        raise ValueError(f"Unknown backend '{backend}'. Choose from: {list(_BACKEND_MAP)}")

    fn = _BACKEND_MAP[backend]
    result.llm_narrative = fn(result)
    return result
