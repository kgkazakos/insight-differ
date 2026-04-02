"""Click CLI for insight-differ."""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .comparator import compare_reports
from .extractor import extract_segments
from .models import DiffResult

console = Console()


def _load_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        console.print(f"[red]File not found:[/] {path}")
        sys.exit(1)
    return p.read_text(encoding="utf-8")


def _print_result(result: DiffResult, report_a: str, report_b: str) -> None:
    summary = result.summary()

    console.print()
    console.print(
        Panel(
            f"[bold]insight-differ[/] · CPR Orbital Tool 5\n"
            f"[dim]Comparing:[/] {report_a}  ↔  {report_b}",
            expand=False,
            border_style="bright_blue",
        )
    )

    # Summary row
    console.print()
    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    t.add_column("Category", style="bold")
    t.add_column("Count", justify="right")
    t.add_row("Overlaps", f"[green]{summary['overlaps']}[/]")
    t.add_row("Contradictions", f"[red]{summary['contradictions']}[/]")
    t.add_row(f"Gaps (in {result.report_b_name})", f"[yellow]{summary['gaps_in_b']}[/]")
    t.add_row(f"Gaps (in {result.report_a_name})", f"[yellow]{summary['gaps_in_a']}[/]")
    console.print(t)

    # Contradictions
    if result.contradictions:
        console.print("\n[bold red]⚠  Contradictions[/]")
        for idx, c in enumerate(result.contradictions, 1):
            console.print(f"\n  [dim]{idx}.[/] sim={c.similarity:.2f}  contradiction_score={c.contradiction_score:.2f}")
            console.print(f"  [cyan]A:[/] {c.segment_a.text[:200]}")
            console.print(f"  [magenta]B:[/] {c.segment_b.text[:200]}")

    # Overlaps
    if result.overlaps:
        console.print("\n[bold green]✓  Overlaps[/]")
        for idx, o in enumerate(result.overlaps[:8], 1):
            console.print(f"\n  [dim]{idx}.[/] sim={o.similarity:.2f}")
            console.print(f"  [cyan]A:[/] {o.segment_a.text[:200]}")
            console.print(f"  [magenta]B:[/] {o.segment_b.text[:200]}")

    # Gaps
    gaps_b = result.gaps_in_b
    gaps_a = result.gaps_in_a
    if gaps_b or gaps_a:
        console.print("\n[bold yellow]△  Gaps[/]")
        if gaps_b:
            console.print("\n  In [cyan]A[/] but not addressed in [magenta]B[/]:")
            for g in gaps_b[:5]:
                console.print(f"    • {g.segment.text[:180]}")
        if gaps_a:
            console.print("\n  In [magenta]B[/] but not addressed in [cyan]A[/]:")
            for g in gaps_a[:5]:
                console.print(f"    • {g.segment.text[:180]}")

    # LLM narrative
    if result.llm_narrative:
        console.print()
        console.print(
            Panel(
                result.llm_narrative,
                title="[bold]LLM Narrative[/]",
                border_style="dim",
                expand=False,
            )
        )

    console.print()


@click.group()
@click.version_option(package_name="insight-differ")
def cli() -> None:
    """insight-differ — compare two research reports to surface contradictions,
    overlaps, and gaps.

    Part of the CPR Orbital series: github.com/kgkazakos
    """


@cli.command()
@click.argument("report_a", type=click.Path(exists=True))
@click.argument("report_b", type=click.Path(exists=True))
@click.option("--name-a", default="Report A", help="Label for Report A.")
@click.option("--name-b", default="Report B", help="Label for Report B.")
@click.option(
    "--overlap-threshold",
    default=0.52,
    show_default=True,
    type=float,
    help="Cosine similarity threshold for overlaps.",
)
@click.option(
    "--gap-threshold",
    default=0.22,
    show_default=True,
    type=float,
    help="Cosine similarity threshold below which a segment is a gap.",
)
@click.option(
    "--llm-backend",
    type=click.Choice(["openai", "anthropic", "gemini"]),
    default=None,
    help="Optional LLM backend for narrative enrichment.",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Output JSON.")
@click.option("--output", type=click.Path(), default=None, help="Write output to file.")
def diff(
    report_a: str,
    report_b: str,
    name_a: str,
    name_b: str,
    overlap_threshold: float,
    gap_threshold: float,
    llm_backend: Optional[str],
    as_json: bool,
    output: Optional[str],
) -> None:
    """Compare two research reports.

    REPORT_A and REPORT_B are paths to plain-text (.txt) or markdown (.md) files.

    \b
    Example:
        insight-differ diff study_q1.txt study_q2.txt --name-a "Q1 Study" --name-b "Q2 Study"
        insight-differ diff a.txt b.txt --llm-backend anthropic --json
    """
    text_a = _load_text(report_a)
    text_b = _load_text(report_b)

    with console.status("Extracting segments…"):
        segs_a = extract_segments(text_a, "A")
        segs_b = extract_segments(text_b, "B")

    with console.status("Comparing reports…"):
        result = compare_reports(
            segs_a,
            segs_b,
            overlap_threshold=overlap_threshold,
            gap_threshold=gap_threshold,
        )
        result.report_a_name = name_a
        result.report_b_name = name_b

    if llm_backend:
        from .llm import enrich

        with console.status(f"Enriching with {llm_backend}…"):
            result = enrich(result, llm_backend)

    if as_json:
        out = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
        if output:
            Path(output).write_text(out, encoding="utf-8")
            console.print(f"[green]Saved:[/] {output}")
        else:
            print(out)
    else:
        _print_result(result, report_a, report_b)
        if output:
            Path(output).write_text(
                json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            console.print(f"[green]JSON also saved:[/] {output}")


@cli.command()
@click.argument("report_a", type=click.Path(exists=True))
@click.argument("report_b", type=click.Path(exists=True))
def segments(report_a: str, report_b: str) -> None:
    """Show extracted segments from both reports (diagnostic command).

    \b
    Example:
        insight-differ segments report_a.txt report_b.txt
    """
    text_a = _load_text(report_a)
    text_b = _load_text(report_b)

    segs_a = extract_segments(text_a, "A")
    segs_b = extract_segments(text_b, "B")

    console.print(f"\n[cyan]Report A[/] — {len(segs_a)} segments from {report_a}")
    for s in segs_a:
        console.print(f"  [{s.id}] {s.text[:140]}")

    console.print(f"\n[magenta]Report B[/] — {len(segs_b)} segments from {report_b}")
    for s in segs_b:
        console.print(f"  [{s.id}] {s.text[:140]}")

    console.print()


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
