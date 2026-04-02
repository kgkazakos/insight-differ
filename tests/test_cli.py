"""Tests for insight_differ.cli"""

import json
import pytest
from click.testing import CliRunner
from insight_differ.cli import cli

FIXTURE_A = "tests/fixtures/report_a.txt"
FIXTURE_B = "tests/fixtures/report_b.txt"


@pytest.fixture
def runner():
    return CliRunner()


class TestDiffCommand:
    def test_basic_run(self, runner):
        result = runner.invoke(cli, ["diff", FIXTURE_A, FIXTURE_B])
        assert result.exit_code == 0

    def test_output_mentions_overlaps(self, runner):
        result = runner.invoke(cli, ["diff", FIXTURE_A, FIXTURE_B])
        assert "overlap" in result.output.lower() or "Overlaps" in result.output

    def test_output_mentions_contradictions(self, runner):
        result = runner.invoke(cli, ["diff", FIXTURE_A, FIXTURE_B])
        assert "contradiction" in result.output.lower()

    def test_json_output(self, runner):
        result = runner.invoke(cli, ["diff", FIXTURE_A, FIXTURE_B, "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert "summary" in parsed
        assert "overlaps" in parsed
        assert "contradictions" in parsed
        assert "gaps" in parsed

    def test_json_summary_keys(self, runner):
        result = runner.invoke(cli, ["diff", FIXTURE_A, FIXTURE_B, "--json"])
        parsed = json.loads(result.output)
        summary = parsed["summary"]
        assert "overlaps" in summary
        assert "contradictions" in summary
        assert "gaps_in_b" in summary
        assert "gaps_in_a" in summary

    def test_custom_names(self, runner):
        result = runner.invoke(
            cli,
            ["diff", FIXTURE_A, FIXTURE_B, "--name-a", "Q3 Study", "--name-b", "Q4 Study", "--json"],
        )
        parsed = json.loads(result.output)
        assert parsed["report_a_name"] == "Q3 Study"
        assert parsed["report_b_name"] == "Q4 Study"

    def test_missing_file_exits(self, runner):
        result = runner.invoke(cli, ["diff", "nonexistent_a.txt", FIXTURE_B])
        assert result.exit_code != 0

    def test_custom_overlap_threshold(self, runner):
        result_strict = runner.invoke(
            cli, ["diff", FIXTURE_A, FIXTURE_B, "--overlap-threshold", "0.90", "--json"]
        )
        result_loose = runner.invoke(
            cli, ["diff", FIXTURE_A, FIXTURE_B, "--overlap-threshold", "0.30", "--json"]
        )
        strict = json.loads(result_strict.output)
        loose = json.loads(result_loose.output)
        assert strict["summary"]["overlaps"] <= loose["summary"]["overlaps"]

    def test_output_to_file(self, runner, tmp_path):
        out = tmp_path / "diff_result.json"
        result = runner.invoke(cli, ["diff", FIXTURE_A, FIXTURE_B, "--json", "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        parsed = json.loads(out.read_text())
        assert "summary" in parsed


class TestSegmentsCommand:
    def test_basic_run(self, runner):
        result = runner.invoke(cli, ["segments", FIXTURE_A, FIXTURE_B])
        assert result.exit_code == 0

    def test_shows_segment_count(self, runner):
        result = runner.invoke(cli, ["segments", FIXTURE_A, FIXTURE_B])
        assert "segments" in result.output.lower()

    def test_shows_both_reports(self, runner):
        result = runner.invoke(cli, ["segments", FIXTURE_A, FIXTURE_B])
        assert "Report A" in result.output or "A_" in result.output
        assert "Report B" in result.output or "B_" in result.output


class TestCLIHelp:
    def test_main_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "insight-differ" in result.output

    def test_diff_help(self, runner):
        result = runner.invoke(cli, ["diff", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_segments_help(self, runner):
        result = runner.invoke(cli, ["segments", "--help"])
        assert result.exit_code == 0
