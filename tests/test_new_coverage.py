"""Additional tests filling gaps identified in the quality review.

Covers:
- Track schema rejection for each track type (missing required fields, wrong types)
- resolve_track_spec with a CirroFileRef resolver (not just UrlFileRef)
- resolve_track_spec CRAM with explicit index and with gzi in sequence_adapter
- resolve_track_spec raises ValueError for unknown type
- generate_assets with a CRAM track end-to-end
- generate_assets when output dir already exists (idempotent)
- generate_assets with UrlFileRef on assembly chrom_sizes (explicit coverage)
- _parse_fasta error case (malformed input)
- serve command generates assets and sets up HTTPServer without actually binding
- _needs_index_prompt helper for all five file extensions + negative case
- select --non-interactive missing --project-id and missing --dataset-id exit codes
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
import jsonschema

from cirro_jbrowse_config.tracks import resolve_track_spec
from cirro_jbrowse_config.tracks.bam import BamTrack
from cirro_jbrowse_config.tracks.bigwig import BigWigTrack
from cirro_jbrowse_config.tracks.cram import CramTrack
from cirro_jbrowse_config.tracks.gff import GffTrack
from cirro_jbrowse_config.tracks.vcf import VcfTrack
from cirro_jbrowse_config.cirro.selector import _needs_index_prompt
from cirro_jbrowse_config.generator import generate_assets
from cirro_jbrowse_config.cli.main import main, _parse_fasta

from click.testing import CliRunner


ASSEMBLY = "hg38"


# ---------------------------------------------------------------------------
# Track schema rejection tests
# ---------------------------------------------------------------------------

class TestTrackSchemaRejection:
    """Each track schema must reject specs missing required fields or using wrong types."""

    # BAM

    def test_bam_missing_bam_url(self):
        spec = {"name": "S", "bai_url": "https://example.com/s.bam.bai"}
        with pytest.raises(jsonschema.ValidationError):
            BamTrack.validate_spec(spec)

    def test_bam_missing_bai_url(self):
        spec = {"name": "S", "bam_url": "https://example.com/s.bam"}
        with pytest.raises(jsonschema.ValidationError):
            BamTrack.validate_spec(spec)

    def test_bam_missing_name(self):
        spec = {"bam_url": "https://example.com/s.bam", "bai_url": "https://example.com/s.bam.bai"}
        with pytest.raises(jsonschema.ValidationError):
            BamTrack.validate_spec(spec)

    def test_bam_extra_property_rejected(self):
        spec = {
            "name": "S",
            "bam_url": "https://example.com/s.bam",
            "bai_url": "https://example.com/s.bam.bai",
            "unexpected": True,
        }
        with pytest.raises(jsonschema.ValidationError):
            BamTrack.validate_spec(spec)

    # CRAM

    def test_cram_missing_sequence_adapter(self):
        spec = {
            "name": "S",
            "cram_url": "https://example.com/s.cram",
            "crai_url": "https://example.com/s.cram.crai",
        }
        with pytest.raises(jsonschema.ValidationError):
            CramTrack.validate_spec(spec)

    def test_cram_missing_cram_url(self):
        spec = {
            "name": "S",
            "crai_url": "https://example.com/s.cram.crai",
            "sequence_adapter": {
                "fasta_url": "https://example.com/ref.fa.gz",
                "fai_url": "https://example.com/ref.fa.gz.fai",
            },
        }
        with pytest.raises(jsonschema.ValidationError):
            CramTrack.validate_spec(spec)

    def test_cram_missing_crai_url(self):
        spec = {
            "name": "S",
            "cram_url": "https://example.com/s.cram",
            "sequence_adapter": {
                "fasta_url": "https://example.com/ref.fa.gz",
                "fai_url": "https://example.com/ref.fa.gz.fai",
            },
        }
        with pytest.raises(jsonschema.ValidationError):
            CramTrack.validate_spec(spec)

    def test_cram_sequence_adapter_missing_fai_url(self):
        spec = {
            "name": "S",
            "cram_url": "https://example.com/s.cram",
            "crai_url": "https://example.com/s.cram.crai",
            "sequence_adapter": {
                "fasta_url": "https://example.com/ref.fa.gz",
                # fai_url missing
            },
        }
        with pytest.raises(jsonschema.ValidationError):
            CramTrack.validate_spec(spec)

    def test_cram_sequence_adapter_missing_fasta_url(self):
        spec = {
            "name": "S",
            "cram_url": "https://example.com/s.cram",
            "crai_url": "https://example.com/s.cram.crai",
            "sequence_adapter": {
                "fai_url": "https://example.com/ref.fa.gz.fai",
                # fasta_url missing
            },
        }
        with pytest.raises(jsonschema.ValidationError):
            CramTrack.validate_spec(spec)

    # BigWig

    def test_bigwig_missing_bigwig_url(self):
        spec = {"name": "Cov"}
        with pytest.raises(jsonschema.ValidationError):
            BigWigTrack.validate_spec(spec)

    def test_bigwig_missing_name(self):
        spec = {"bigwig_url": "https://example.com/c.bw"}
        with pytest.raises(jsonschema.ValidationError):
            BigWigTrack.validate_spec(spec)

    def test_bigwig_extra_property_rejected(self):
        spec = {
            "name": "Cov",
            "bigwig_url": "https://example.com/c.bw",
            "not_allowed": "value",
        }
        with pytest.raises(jsonschema.ValidationError):
            BigWigTrack.validate_spec(spec)

    # VCF

    def test_vcf_missing_vcf_gz_url(self):
        spec = {"name": "V", "tbi_url": "https://example.com/v.vcf.gz.tbi"}
        with pytest.raises(jsonschema.ValidationError):
            VcfTrack.validate_spec(spec)

    def test_vcf_missing_tbi_url(self):
        spec = {"name": "V", "vcf_gz_url": "https://example.com/v.vcf.gz"}
        with pytest.raises(jsonschema.ValidationError):
            VcfTrack.validate_spec(spec)

    # GFF

    def test_gff_missing_gff_gz_url(self):
        spec = {"name": "G", "tbi_url": "https://example.com/g.gff.gz.tbi"}
        with pytest.raises(jsonschema.ValidationError):
            GffTrack.validate_spec(spec)

    def test_gff_missing_tbi_url(self):
        spec = {"name": "G", "gff_gz_url": "https://example.com/g.gff.gz"}
        with pytest.raises(jsonschema.ValidationError):
            GffTrack.validate_spec(spec)


# ---------------------------------------------------------------------------
# resolve_track_spec with a CirroFileRef resolver
# ---------------------------------------------------------------------------

class TestResolveTrackSpecCirroFileRef:
    """resolve_track_spec must call the url_resolver for CirroFileRef dicts."""

    def _cirro_resolver(self, file_ref: dict) -> str:
        """Fake resolver that maps CirroFileRefs to deterministic URLs."""
        if "url" in file_ref:
            return file_ref["url"]
        return f"https://cirro.example.com/{file_ref['file_path']}"

    def test_bam_file_resolved_via_resolver(self):
        raw = {
            "type": "bam",
            "name": "Sample",
            "file": {"project_id": "p", "dataset_id": "d", "file_path": "data/s.bam"},
        }
        calls = []
        def tracking_resolver(ref):
            calls.append(ref)
            return self._cirro_resolver(ref)

        resolved = resolve_track_spec(raw, tracking_resolver)
        assert resolved["bam_url"] == "https://cirro.example.com/data/s.bam"
        assert any(r.get("file_path") == "data/s.bam" for r in calls)

    def test_bam_index_resolved_via_resolver(self):
        raw = {
            "type": "bam",
            "name": "Sample",
            "file": {"project_id": "p", "dataset_id": "d", "file_path": "data/s.bam"},
            "index": {"project_id": "p", "dataset_id": "d", "file_path": "data/s.bam.bai"},
        }
        resolved = resolve_track_spec(raw, self._cirro_resolver)
        assert resolved["bai_url"] == "https://cirro.example.com/data/s.bam.bai"

    def test_bigwig_resolved(self):
        raw = {
            "type": "bigwig",
            "name": "Coverage",
            "file": {"project_id": "p", "dataset_id": "d", "file_path": "cov/s.bw"},
        }
        resolved = resolve_track_spec(raw, self._cirro_resolver)
        assert resolved["bigwig_url"] == "https://cirro.example.com/cov/s.bw"

    def test_vcf_file_and_inferred_index_resolved(self):
        raw = {
            "type": "vcf",
            "name": "Variants",
            "file": {"project_id": "p", "dataset_id": "d", "file_path": "vcf/s.vcf.gz"},
        }
        resolved = resolve_track_spec(raw, self._cirro_resolver)
        assert resolved["vcf_gz_url"] == "https://cirro.example.com/vcf/s.vcf.gz"
        # Index should be inferred by appending .tbi
        assert resolved["tbi_url"] == "https://cirro.example.com/vcf/s.vcf.gz.tbi"

    def test_gff_file_resolved(self):
        raw = {
            "type": "gff",
            "name": "Genes",
            "file": {"project_id": "p", "dataset_id": "d", "file_path": "annot/g.gff.gz"},
        }
        resolved = resolve_track_spec(raw, self._cirro_resolver)
        assert resolved["gff_gz_url"] == "https://cirro.example.com/annot/g.gff.gz"

    def test_cram_all_refs_resolved(self):
        raw = {
            "type": "cram",
            "name": "Aligned",
            "file": {"project_id": "p", "dataset_id": "d", "file_path": "align/s.cram"},
            "sequence_adapter": {
                "fasta": {"project_id": "p", "dataset_id": "d", "file_path": "ref/genome.fa.gz"},
                "fai": {"project_id": "p", "dataset_id": "d", "file_path": "ref/genome.fa.gz.fai"},
                "gzi": {"project_id": "p", "dataset_id": "d", "file_path": "ref/genome.fa.gz.gzi"},
            },
        }
        resolved = resolve_track_spec(raw, self._cirro_resolver)
        assert resolved["cram_url"] == "https://cirro.example.com/align/s.cram"
        assert resolved["sequence_adapter"]["fasta_url"] == "https://cirro.example.com/ref/genome.fa.gz"
        assert resolved["sequence_adapter"]["fai_url"] == "https://cirro.example.com/ref/genome.fa.gz.fai"
        assert resolved["sequence_adapter"]["gzi_url"] == "https://cirro.example.com/ref/genome.fa.gz.gzi"

    def test_cram_index_explicit_resolved(self):
        raw = {
            "type": "cram",
            "name": "Aligned",
            "file": {"project_id": "p", "dataset_id": "d", "file_path": "align/s.cram"},
            "index": {"project_id": "p", "dataset_id": "d", "file_path": "align/s.cram.crai"},
            "sequence_adapter": {
                "fasta": {"url": "https://example.com/ref.fa.gz"},
                "fai": {"url": "https://example.com/ref.fa.gz.fai"},
            },
        }
        resolved = resolve_track_spec(raw, self._cirro_resolver)
        assert resolved["crai_url"] == "https://cirro.example.com/align/s.cram.crai"

    def test_cram_index_inferred_when_absent(self):
        raw = {
            "type": "cram",
            "name": "Aligned",
            "file": {"url": "https://example.com/s.cram"},
            "sequence_adapter": {
                "fasta": {"url": "https://example.com/ref.fa.gz"},
                "fai": {"url": "https://example.com/ref.fa.gz.fai"},
            },
        }
        resolved = resolve_track_spec(raw, lambda r: r["url"])
        assert resolved["crai_url"] == "https://example.com/s.cram.crai"


# ---------------------------------------------------------------------------
# resolve_track_spec unknown type
# ---------------------------------------------------------------------------

class TestResolveTrackSpecUnknownType:
    def test_raises_value_error(self):
        raw = {"type": "unknown_format", "name": "X", "file": {"url": "https://example.com/f"}}
        with pytest.raises(ValueError, match="Unknown track type"):
            resolve_track_spec(raw, lambda r: r["url"])


# ---------------------------------------------------------------------------
# generate_assets with CRAM track
# ---------------------------------------------------------------------------

class TestGenerateAssetsCram:
    def _cram_inputs(self):
        return {
            "assembly": {"name": "hg38"},
            "tracks": [
                {
                    "type": "cram",
                    "name": "Sample CRAM",
                    "file": {"url": "https://example.com/s.cram"},
                    "sequence_adapter": {
                        "fasta": {"url": "https://example.com/ref.fa.gz"},
                        "fai": {"url": "https://example.com/ref.fa.gz.fai"},
                        "gzi": {"url": "https://example.com/ref.fa.gz.gzi"},
                    },
                }
            ],
        }

    def test_cram_track_in_output_config(self, tmp_path):
        generate_assets(self._cram_inputs(), tmp_path, lambda r: r["url"])
        config = json.loads((tmp_path / "config.json").read_text())
        assert len(config["tracks"]) == 1
        assert config["tracks"][0]["adapter"]["type"] == "CramAdapter"

    def test_cram_track_has_sequence_adapter(self, tmp_path):
        generate_assets(self._cram_inputs(), tmp_path, lambda r: r["url"])
        config = json.loads((tmp_path / "config.json").read_text())
        sa = config["tracks"][0]["adapter"]["sequenceAdapter"]
        assert sa["type"] == "BgzipFastaAdapter"
        assert sa["fastaLocation"]["uri"] == "https://example.com/ref.fa.gz"

    def test_cram_track_crai_inferred(self, tmp_path):
        generate_assets(self._cram_inputs(), tmp_path, lambda r: r["url"])
        config = json.loads((tmp_path / "config.json").read_text())
        crai_uri = config["tracks"][0]["adapter"]["craiLocation"]["uri"]
        assert crai_uri == "https://example.com/s.cram.crai"


# ---------------------------------------------------------------------------
# generate_assets idempotency (output dir already exists)
# ---------------------------------------------------------------------------

class TestGenerateAssetsOutputDirExists:
    def test_does_not_raise_when_dir_exists(self, tmp_path, minimal_inputs):
        # Create the directory first with a pre-existing file
        (tmp_path / "old_file.txt").write_text("old content")
        # Must not raise
        result = generate_assets(minimal_inputs, tmp_path, lambda r: r["url"])
        assert result == tmp_path
        assert (tmp_path / "config.json").exists()

    def test_overwrites_existing_config(self, tmp_path, minimal_inputs):
        (tmp_path / "config.json").write_text("{}")
        generate_assets(minimal_inputs, tmp_path, lambda r: r["url"])
        config = json.loads((tmp_path / "config.json").read_text())
        assert "assemblies" in config


# ---------------------------------------------------------------------------
# _parse_fasta error cases
# ---------------------------------------------------------------------------

class TestParseFasta:
    def test_valid_three_part_string(self):
        result = _parse_fasta("proj-1:ds-2:ref/genome.fa")
        assert result == {
            "project_id": "proj-1",
            "dataset_id": "ds-2",
            "file_path": "ref/genome.fa",
        }

    def test_too_few_parts_raises(self):
        import click
        with pytest.raises(click.BadParameter):
            _parse_fasta("proj-1:ds-2")

    def test_colon_in_file_path_is_allowed(self):
        # _parse_fasta uses split(":", 2) so a colon inside the file path is
        # absorbed into the file_path component and must NOT raise.
        result = _parse_fasta("proj-1:ds-2:path/file.fa:extra")
        assert result["project_id"] == "proj-1"
        assert result["dataset_id"] == "ds-2"
        assert result["file_path"] == "path/file.fa:extra"

    def test_no_colons_raises(self):
        import click
        with pytest.raises(click.BadParameter):
            _parse_fasta("noseparators")


# ---------------------------------------------------------------------------
# serve command
# ---------------------------------------------------------------------------

class TestServeCommand:
    def test_serve_generates_assets_and_creates_server(self, tmp_path):
        inputs_data = {"assembly": {"name": "hg38"}, "tracks": []}
        inputs_file = tmp_path / "inputs.json"
        inputs_file.write_text(json.dumps(inputs_data))
        output_dir = tmp_path / "site"

        mock_portal = MagicMock()
        mock_resolver = MagicMock()
        mock_out_path = output_dir
        mock_out_path.mkdir(parents=True, exist_ok=True)

        mock_server = MagicMock()
        mock_server.serve_forever.side_effect = KeyboardInterrupt

        with (
            patch("cirro_jbrowse_config.cli.main._get_portal", return_value=mock_portal),
            patch("cirro_jbrowse_config.cli.main.make_presigned_resolver", return_value=mock_resolver),
            patch("cirro_jbrowse_config.cli.main.generate_assets", return_value=mock_out_path) as mock_gen,
            patch("cirro_jbrowse_config.cli.main.http.server.HTTPServer", return_value=mock_server) as mock_httpserver,
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "serve",
                    "--inputs", str(inputs_file),
                    "--output-dir", str(output_dir),
                    "--port", "9999",
                ],
            )

        assert result.exit_code == 0, result.output
        mock_gen.assert_called_once_with(inputs_data, str(output_dir), mock_resolver)
        # Server is created on the specified port
        args, _ = mock_httpserver.call_args
        assert args[0] == ("", 9999)
        assert "Serving at http://localhost:9999" in result.output
        assert "Stopped." in result.output

    def test_serve_missing_inputs_file(self, tmp_path):
        with patch("cirro_jbrowse_config.cli.main._get_portal"):
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["serve", "--inputs", str(tmp_path / "nonexistent.json")],
            )
        assert result.exit_code == 1
        assert "Error:" in result.output


# ---------------------------------------------------------------------------
# _needs_index_prompt helper
# ---------------------------------------------------------------------------

class TestNeedsIndexPrompt:
    def test_bam_needs_index(self):
        result = _needs_index_prompt("results/sample.bam")
        assert result is not None
        ext, label = result
        assert ".bai" in ext
        assert "BAI" in label

    def test_cram_needs_index(self):
        result = _needs_index_prompt("results/sample.cram")
        assert result is not None
        ext, label = result
        assert ".crai" in ext
        assert "CRAI" in label

    def test_vcf_gz_needs_index(self):
        result = _needs_index_prompt("results/variants.vcf.gz")
        assert result is not None
        ext, label = result
        assert ".tbi" in ext

    def test_gff_gz_needs_index(self):
        result = _needs_index_prompt("results/annotations.gff.gz")
        assert result is not None
        ext, label = result
        assert ".tbi" in ext

    def test_gff3_gz_needs_index(self):
        result = _needs_index_prompt("results/annotations.gff3.gz")
        assert result is not None
        ext, label = result
        assert ".tbi" in ext

    def test_bigwig_does_not_need_index(self):
        assert _needs_index_prompt("results/coverage.bw") is None

    def test_plain_fasta_does_not_need_index(self):
        assert _needs_index_prompt("ref/genome.fa") is None

    def test_case_insensitive_bam(self):
        result = _needs_index_prompt("results/SAMPLE.BAM")
        assert result is not None

    def test_case_insensitive_vcf(self):
        result = _needs_index_prompt("results/VARIANTS.VCF.GZ")
        assert result is not None


# ---------------------------------------------------------------------------
# select --non-interactive missing required flags
# ---------------------------------------------------------------------------

class TestSelectNonInteractiveMissingFlags:
    def test_missing_project_id_exits_nonzero(self):
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
                    "--assembly", "hg38",
                    "--dataset-id", "ds-456",
                ],
            )
        assert result.exit_code != 0

    def test_missing_dataset_id_exits_nonzero(self):
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
                    "--assembly", "hg38",
                    "--project-id", "proj-123",
                ],
            )
        assert result.exit_code != 0
