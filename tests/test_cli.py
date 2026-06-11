"""Tests for the CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cirro_jbrowse_config.cli.main import main, _parse_track


# ---------------------------------------------------------------------------
# Help tests (existing)
# ---------------------------------------------------------------------------

def test_main_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "JBrowse2" in result.output


def test_select_subcommand_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["select", "--help"])
    assert result.exit_code == 0


def test_generate_subcommand_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["generate", "--help"])
    assert result.exit_code == 0


def test_serve_subcommand_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["serve", "--help"])
    assert result.exit_code == 0


def test_upload_subcommand_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["upload", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# _parse_track unit tests
# ---------------------------------------------------------------------------

def test_parse_track_without_index():
    result = _parse_track("bigwig:Coverage:coverage/sample1.bw")
    assert result == {"track_type": "bigwig", "name": "Coverage", "file_path": "coverage/sample1.bw"}
    assert "index_path" not in result


def test_parse_track_with_index():
    result = _parse_track("bam:Sample1:alignments/sample1.bam:alignments/sample1.bam.bai")
    assert result == {
        "track_type": "bam",
        "name": "Sample1",
        "file_path": "alignments/sample1.bam",
        "index_path": "alignments/sample1.bam.bai",
    }


def test_parse_track_invalid_raises():
    import click
    with pytest.raises(click.BadParameter):
        _parse_track("onlyonefield")


def test_parse_track_two_parts_raises():
    import click
    with pytest.raises(click.BadParameter):
        _parse_track("bam:Sample1")


# ---------------------------------------------------------------------------
# select --non-interactive
# ---------------------------------------------------------------------------

def test_select_non_interactive(tmp_path):
    output_file = tmp_path / "inputs.json"

    mock_inputs = {"assembly": {"name": "hg38"}, "tracks": []}

    with (
        patch("cirro_jbrowse_config.cli.main._get_portal") as mock_portal,
        patch("cirro_jbrowse_config.cli.main.FileSelector") as MockSelector,
    ):
        mock_selector_instance = MagicMock()
        mock_selector_instance.run_non_interactive.return_value = mock_inputs
        MockSelector.return_value = mock_selector_instance

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "select",
                "--non-interactive",
                "--assembly", "hg38",
                "--project-id", "proj-123",
                "--dataset-id", "ds-456",
                "--track", "bigwig:Coverage:coverage/sample.bw",
                "--output", str(output_file),
            ],
        )

    assert result.exit_code == 0, result.output
    mock_selector_instance.run_non_interactive.assert_called_once()
    call_kwargs = mock_selector_instance.run_non_interactive.call_args
    assert call_kwargs.kwargs["assembly_name"] == "hg38"
    assert call_kwargs.kwargs["assembly_fasta"] is None
    tracks_passed = call_kwargs.kwargs["tracks"]
    assert len(tracks_passed) == 1
    assert tracks_passed[0]["track_type"] == "bigwig"
    assert tracks_passed[0]["name"] == "Coverage"
    assert tracks_passed[0]["file_path"] == "coverage/sample.bw"
    assert tracks_passed[0]["project_id"] == "proj-123"
    assert tracks_passed[0]["dataset_id"] == "ds-456"


def test_select_non_interactive_with_index_track(tmp_path):
    output_file = tmp_path / "inputs.json"
    mock_inputs = {"assembly": {"name": "hg38"}, "tracks": []}

    with (
        patch("cirro_jbrowse_config.cli.main._get_portal"),
        patch("cirro_jbrowse_config.cli.main.FileSelector") as MockSelector,
    ):
        mock_selector_instance = MagicMock()
        mock_selector_instance.run_non_interactive.return_value = mock_inputs
        MockSelector.return_value = mock_selector_instance

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "select",
                "--non-interactive",
                "--assembly", "hg38",
                "--project-id", "proj-123",
                "--dataset-id", "ds-456",
                "--track", "bam:Sample1:alignments/s1.bam:alignments/s1.bam.bai",
                "--output", str(output_file),
            ],
        )

    assert result.exit_code == 0, result.output
    tracks_passed = mock_selector_instance.run_non_interactive.call_args.kwargs["tracks"]
    assert tracks_passed[0]["index_path"] == "alignments/s1.bam.bai"


def test_select_non_interactive_with_fasta(tmp_path):
    output_file = tmp_path / "inputs.json"
    mock_inputs = {"assembly": {"name": "hg38"}, "tracks": []}

    with (
        patch("cirro_jbrowse_config.cli.main._get_portal"),
        patch("cirro_jbrowse_config.cli.main.FileSelector") as MockSelector,
    ):
        mock_selector_instance = MagicMock()
        mock_selector_instance.run_non_interactive.return_value = mock_inputs
        MockSelector.return_value = mock_selector_instance

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "select",
                "--non-interactive",
                "--assembly", "hg38",
                "--project-id", "proj-123",
                "--dataset-id", "ds-456",
                "--fasta", "fasta-proj:fasta-ds:ref/genome.fa",
                "--output", str(output_file),
            ],
        )

    assert result.exit_code == 0, result.output
    fasta_arg = mock_selector_instance.run_non_interactive.call_args.kwargs["assembly_fasta"]
    assert fasta_arg == {
        "project_id": "fasta-proj",
        "dataset_id": "fasta-ds",
        "file_path": "ref/genome.fa",
    }


def test_select_non_interactive_missing_assembly(tmp_path):
    with (
        patch("cirro_jbrowse_config.cli.main._get_portal"),
        patch("cirro_jbrowse_config.cli.main.FileSelector"),
    ):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "select",
                "--non-interactive",
                "--project-id", "proj-123",
                "--dataset-id", "ds-456",
            ],
        )
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

def test_generate_url_only_skips_portal(tmp_path):
    """When all refs are URLs, generate should not connect to Cirro."""
    inputs_data = {"assembly": {"name": "hg38"}, "tracks": []}
    inputs_file = tmp_path / "inputs.json"
    inputs_file.write_text(json.dumps(inputs_data))
    output_dir = tmp_path / "site"

    mock_out_path = Path(str(output_dir))

    with (
        patch("cirro_jbrowse_config.cli.main._get_portal") as mock_get_portal,
        patch("cirro_jbrowse_config.cli.main.generate_assets", return_value=mock_out_path) as mock_gen,
    ):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["generate", "--inputs", str(inputs_file), "--output-dir", str(output_dir)],
        )

    assert result.exit_code == 0, result.output
    mock_get_portal.assert_not_called()
    (called_data, called_dir, called_resolver), _ = mock_gen.call_args
    assert called_data == inputs_data
    assert called_dir == str(output_dir)
    assert str(output_dir) in result.output


def test_generate_cirro_refs_uses_portal(tmp_path):
    """When inputs contain CirroFileRefs, generate should connect to Cirro."""
    inputs_data = {
        "assembly": {"name": "hg38"},
        "tracks": [{"type": "bam", "name": "s1", "file": {"project_id": "p", "dataset_id": "d", "file_path": "f.bam"}}],
    }
    inputs_file = tmp_path / "inputs.json"
    inputs_file.write_text(json.dumps(inputs_data))
    output_dir = tmp_path / "site"

    mock_portal = MagicMock()
    mock_resolver = MagicMock()
    mock_out_path = Path(str(output_dir))

    with (
        patch("cirro_jbrowse_config.cli.main._get_portal", return_value=mock_portal),
        patch("cirro_jbrowse_config.cli.main.make_presigned_resolver", return_value=mock_resolver) as mock_make_resolver,
        patch("cirro_jbrowse_config.cli.main.generate_assets", return_value=mock_out_path) as mock_gen,
    ):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["generate", "--inputs", str(inputs_file), "--output-dir", str(output_dir)],
        )

    assert result.exit_code == 0, result.output
    mock_make_resolver.assert_called_once_with(mock_portal)
    mock_gen.assert_called_once_with(inputs_data, str(output_dir), mock_resolver)
    assert str(output_dir) in result.output


def test_generate_missing_inputs_file(tmp_path):
    with patch("cirro_jbrowse_config.cli.main._get_portal"):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["generate", "--inputs", str(tmp_path / "nonexistent.json")],
        )
    assert result.exit_code == 1
    assert "Error:" in result.output


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------

def test_upload_calls_uploader(tmp_path):
    inputs_data = {"assembly": {"name": "hg38"}, "tracks": []}
    inputs_file = tmp_path / "inputs.json"
    inputs_file.write_text(json.dumps(inputs_data))
    output_dir = tmp_path / "site"

    mock_portal = MagicMock()
    mock_resolver = MagicMock()
    mock_out_path = Path(str(output_dir))

    with (
        patch("cirro_jbrowse_config.cli.main._get_portal", return_value=mock_portal),
        patch("cirro_jbrowse_config.cli.main.make_render_service_resolver", return_value=mock_resolver),
        patch("cirro_jbrowse_config.cli.main.generate_assets", return_value=mock_out_path),
        patch("cirro_jbrowse_config.cli.main.DatasetUploader") as MockUploader,
    ):
        mock_uploader_instance = MagicMock()
        mock_uploader_instance.upload.return_value = "new-dataset-id"
        MockUploader.return_value = mock_uploader_instance

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "upload",
                "--inputs", str(inputs_file),
                "--output-dir", str(output_dir),
                "--project-id", "proj-abc",
                "--name", "My JBrowse Dataset",
                "--description", "A test upload",
            ],
        )

    assert result.exit_code == 0, result.output
    mock_uploader_instance.upload.assert_called_once_with(
        mock_out_path, "proj-abc", "My JBrowse Dataset", "A test upload"
    )
    assert "new-dataset-id" in result.output
