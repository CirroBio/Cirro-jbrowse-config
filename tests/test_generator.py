"""Tests for the asset generator."""

from __future__ import annotations

import json

import pytest

from cirro_jbrowse_config.generator import generate_assets


def _url_resolver(ref: dict) -> str:
    return ref["url"]


@pytest.fixture()
def chrom_sizes_inputs():
    return {
        "assembly": {
            "name": "hg38",
            "chrom_sizes": {"url": "https://example.com/hg38.chrom.sizes"},
        },
        "tracks": [],
    }


@pytest.fixture()
def bgzip_fasta_inputs():
    return {
        "assembly": {
            "name": "hg38",
            "sequence": {"url": "https://example.com/hg38.fa.gz"},
            "fai": {"url": "https://example.com/hg38.fa.gz.fai"},
            "gzi": {"url": "https://example.com/hg38.fa.gz.gzi"},
        },
        "tracks": [],
    }


@pytest.fixture()
def indexed_fasta_inputs():
    return {
        "assembly": {
            "name": "hg38",
            "sequence": {"url": "https://example.com/hg38.fa"},
            "fai": {"url": "https://example.com/hg38.fa.fai"},
        },
        "tracks": [],
    }


@pytest.fixture()
def bam_track_inputs():
    return {
        "assembly": {"name": "hg38"},
        "tracks": [
            {
                "type": "bam",
                "name": "Sample BAM",
                "file": {"url": "https://example.com/s.bam"},
            }
        ],
    }


# ---------------------------------------------------------------------------
# Output files are created
# ---------------------------------------------------------------------------

class TestGenerateAssetsOutputs:
    def test_returns_path(self, tmp_path, minimal_inputs):
        result = generate_assets(minimal_inputs, tmp_path, _url_resolver)
        assert result == tmp_path

    def test_result_is_dir(self, tmp_path, minimal_inputs):
        result = generate_assets(minimal_inputs, tmp_path, _url_resolver)
        assert result.is_dir()

    def test_config_json_written(self, tmp_path, minimal_inputs):
        generate_assets(minimal_inputs, tmp_path, _url_resolver)
        assert (tmp_path / "config.json").exists()

    def test_index_html_written(self, tmp_path, minimal_inputs):
        generate_assets(minimal_inputs, tmp_path, _url_resolver)
        assert (tmp_path / "index.html").exists()

    def test_creates_output_dir_if_missing(self, tmp_path, minimal_inputs):
        new_dir = tmp_path / "subdir" / "output"
        result = generate_assets(minimal_inputs, new_dir, _url_resolver)
        assert result.is_dir()


# ---------------------------------------------------------------------------
# config.json structure
# ---------------------------------------------------------------------------

class TestConfigJson:
    def _load(self, tmp_path, inputs):
        generate_assets(inputs, tmp_path, _url_resolver)
        return json.loads((tmp_path / "config.json").read_text())

    def test_has_assemblies_key(self, tmp_path, minimal_inputs):
        config = self._load(tmp_path, minimal_inputs)
        assert "assemblies" in config

    def test_has_tracks_key(self, tmp_path, minimal_inputs):
        config = self._load(tmp_path, minimal_inputs)
        assert "tracks" in config

    def test_assembly_name(self, tmp_path, minimal_inputs):
        config = self._load(tmp_path, minimal_inputs)
        assert config["assemblies"][0]["name"] == "hg38"

    def test_empty_tracks(self, tmp_path, minimal_inputs):
        config = self._load(tmp_path, minimal_inputs)
        assert config["tracks"] == []

    def test_validates_against_config_schema(self, tmp_path, minimal_inputs):
        from cirro_jbrowse_config.schemas import validate
        config = self._load(tmp_path, minimal_inputs)
        validate(config, "config")

    def test_config_json_is_indented(self, tmp_path, minimal_inputs):
        generate_assets(minimal_inputs, tmp_path, _url_resolver)
        raw = (tmp_path / "config.json").read_text()
        assert "\n" in raw

    def test_bam_track_in_config(self, tmp_path, bam_track_inputs):
        config = self._load(tmp_path, bam_track_inputs)
        assert len(config["tracks"]) == 1
        assert config["tracks"][0]["type"] == "AlignmentsTrack"

    def test_bam_track_bai_inferred(self, tmp_path, bam_track_inputs):
        config = self._load(tmp_path, bam_track_inputs)
        index_uri = config["tracks"][0]["adapter"]["index"]["location"]["uri"]
        assert index_uri == "https://example.com/s.bam.bai"


# ---------------------------------------------------------------------------
# Assembly adapter selection
# ---------------------------------------------------------------------------

class TestAssemblyAdapters:
    def _assembly_adapter(self, tmp_path, inputs):
        generate_assets(inputs, tmp_path, _url_resolver)
        config = json.loads((tmp_path / "config.json").read_text())
        return config["assemblies"][0]["sequence"]["adapter"]

    def test_bgzip_fasta_uses_bgzip_adapter(self, tmp_path, bgzip_fasta_inputs):
        adapter = self._assembly_adapter(tmp_path, bgzip_fasta_inputs)
        assert adapter["type"] == "BgzipFastaAdapter"

    def test_bgzip_fasta_has_fasta_location(self, tmp_path, bgzip_fasta_inputs):
        adapter = self._assembly_adapter(tmp_path, bgzip_fasta_inputs)
        assert adapter["fastaLocation"]["uri"] == "https://example.com/hg38.fa.gz"

    def test_bgzip_fasta_has_fai_location(self, tmp_path, bgzip_fasta_inputs):
        adapter = self._assembly_adapter(tmp_path, bgzip_fasta_inputs)
        assert adapter["faiLocation"]["uri"] == "https://example.com/hg38.fa.gz.fai"

    def test_bgzip_fasta_has_gzi_location(self, tmp_path, bgzip_fasta_inputs):
        adapter = self._assembly_adapter(tmp_path, bgzip_fasta_inputs)
        assert adapter["gziLocation"]["uri"] == "https://example.com/hg38.fa.gz.gzi"

    def test_indexed_fasta_uses_indexed_adapter(self, tmp_path, indexed_fasta_inputs):
        adapter = self._assembly_adapter(tmp_path, indexed_fasta_inputs)
        assert adapter["type"] == "IndexedFastaAdapter"

    def test_indexed_fasta_has_fasta_location(self, tmp_path, indexed_fasta_inputs):
        adapter = self._assembly_adapter(tmp_path, indexed_fasta_inputs)
        assert adapter["fastaLocation"]["uri"] == "https://example.com/hg38.fa"

    def test_chrom_sizes_uses_chrom_sizes_adapter(self, tmp_path, chrom_sizes_inputs):
        adapter = self._assembly_adapter(tmp_path, chrom_sizes_inputs)
        assert adapter["type"] == "ChromSizesAdapter"

    def test_chrom_sizes_location_uri(self, tmp_path, chrom_sizes_inputs):
        adapter = self._assembly_adapter(tmp_path, chrom_sizes_inputs)
        assert adapter["chromSizesLocation"]["uri"] == "https://example.com/hg38.chrom.sizes"

    def test_no_sequence_falls_back_to_chrom_sizes(self, tmp_path, minimal_inputs):
        adapter = self._assembly_adapter(tmp_path, minimal_inputs)
        assert adapter["type"] == "ChromSizesAdapter"

    def test_fasta_gz_extension_detected(self, tmp_path):
        inputs = {
            "assembly": {
                "name": "hg38",
                "sequence": {"url": "https://example.com/hg38.fasta.gz"},
                "fai": {"url": "https://example.com/hg38.fasta.gz.fai"},
                "gzi": {"url": "https://example.com/hg38.fasta.gz.gzi"},
            },
            "tracks": [],
        }
        adapter = self._assembly_adapter(tmp_path, inputs)
        assert adapter["type"] == "BgzipFastaAdapter"


# ---------------------------------------------------------------------------
# index.html content
# ---------------------------------------------------------------------------

class TestIndexHtml:
    def _html(self, tmp_path, inputs=None):
        if inputs is None:
            inputs = {
                "assembly": {"name": "hg38"},
                "tracks": [],
            }
        generate_assets(inputs, tmp_path, _url_resolver)
        return (tmp_path / "index.html").read_text()

    def test_references_config_json(self, tmp_path):
        html = self._html(tmp_path)
        assert "config.json" in html

    def test_references_jbrowse_umd(self, tmp_path):
        html = self._html(tmp_path)
        assert "react-linear-genome-view" in html

    def test_uses_bundled_react(self, tmp_path):
        # The JBrowse2 UMD bundle exports its own React; we must NOT load React
        # separately from CDN (dual-instance causes hooks dispatcher conflicts).
        html = self._html(tmp_path)
        assert "react@18" not in html
        assert "react.production.min.js" not in html
        # React is destructured from the bundle, not loaded from CDN
        assert "JBrowseReactLinearGenomeView" in html
        assert "React" in html

    def test_has_root_div(self, tmp_path):
        html = self._html(tmp_path)
        assert 'id="root"' in html

    def test_is_valid_html_start(self, tmp_path):
        html = self._html(tmp_path)
        assert html.strip().startswith("<!DOCTYPE html>")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_invalid_inputs_raises(self, tmp_path):
        import jsonschema
        with pytest.raises(jsonschema.ValidationError):
            generate_assets({"assembly": {"name": "hg38"}}, tmp_path, _url_resolver)

    def test_invalid_track_type_raises(self, tmp_path):
        inputs = {
            "assembly": {"name": "hg38"},
            "tracks": [{"type": "unknown", "name": "X", "file": {"url": "https://example.com/f"}}],
        }
        with pytest.raises(Exception):
            generate_assets(inputs, tmp_path, _url_resolver)
