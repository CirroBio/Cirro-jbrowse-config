"""Tests for track builder implementations."""

from __future__ import annotations

import pytest

from cirro_jbrowse_config.tracks import TRACK_BUILDERS, build_track
from cirro_jbrowse_config.tracks.bam import BamTrack
from cirro_jbrowse_config.tracks.bigwig import BigWigTrack
from cirro_jbrowse_config.tracks.cram import CramTrack
from cirro_jbrowse_config.tracks.gff import GffTrack
from cirro_jbrowse_config.tracks.vcf import VcfTrack


ASSEMBLY = "hg38"


# ---------------------------------------------------------------------------
# BamTrack
# ---------------------------------------------------------------------------

class TestBamTrack:
    def _spec(self, bam_url="https://example.com/s.bam", bai_url="https://example.com/s.bam.bai"):
        return {"name": "Sample BAM", "bam_url": bam_url, "bai_url": bai_url}

    def test_type(self):
        track = BamTrack(self._spec(), ASSEMBLY).build()
        assert track["type"] == "AlignmentsTrack"

    def test_track_id_slugified(self):
        track = BamTrack(self._spec(), ASSEMBLY).build()
        assert track["trackId"] == "sample_bam"

    def test_assembly_names(self):
        track = BamTrack(self._spec(), ASSEMBLY).build()
        assert track["assemblyNames"] == [ASSEMBLY]

    def test_adapter_type(self):
        track = BamTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["type"] == "BamAdapter"

    def test_bam_location(self):
        track = BamTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["bamLocation"]["uri"] == "https://example.com/s.bam"

    def test_bai_location(self):
        track = BamTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["index"]["location"]["uri"] == "https://example.com/s.bam.bai"

    def test_index_type_is_bai(self):
        track = BamTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["index"]["indexType"] == "BAI"

    def test_required_jbrowse_keys(self):
        track = BamTrack(self._spec(), ASSEMBLY).build()
        for key in ("type", "trackId", "name", "assemblyNames", "adapter"):
            assert key in track


# ---------------------------------------------------------------------------
# CramTrack
# ---------------------------------------------------------------------------

class TestCramTrack:
    def _spec(self, include_gzi=True):
        sa = {
            "fasta_url": "https://example.com/ref.fa.gz",
            "fai_url": "https://example.com/ref.fa.gz.fai",
        }
        if include_gzi:
            sa["gzi_url"] = "https://example.com/ref.fa.gz.gzi"
        return {
            "name": "Sample CRAM",
            "cram_url": "https://example.com/s.cram",
            "crai_url": "https://example.com/s.cram.crai",
            "sequence_adapter": sa,
        }

    def test_type(self):
        track = CramTrack(self._spec(), ASSEMBLY).build()
        assert track["type"] == "AlignmentsTrack"

    def test_adapter_type(self):
        track = CramTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["type"] == "CramAdapter"

    def test_cram_location(self):
        track = CramTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["cramLocation"]["uri"] == "https://example.com/s.cram"

    def test_crai_location(self):
        track = CramTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["craiLocation"]["uri"] == "https://example.com/s.cram.crai"

    def test_sequence_adapter_type(self):
        track = CramTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["sequenceAdapter"]["type"] == "BgzipFastaAdapter"

    def test_sequence_adapter_fasta_location(self):
        track = CramTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["sequenceAdapter"]["fastaLocation"]["uri"] == "https://example.com/ref.fa.gz"

    def test_sequence_adapter_gzi_present_when_given(self):
        track = CramTrack(self._spec(include_gzi=True), ASSEMBLY).build()
        assert "gziLocation" in track["adapter"]["sequenceAdapter"]

    def test_sequence_adapter_gzi_absent_when_not_given(self):
        track = CramTrack(self._spec(include_gzi=False), ASSEMBLY).build()
        assert "gziLocation" not in track["adapter"]["sequenceAdapter"]

    def test_sequence_adapter_uses_indexed_fasta_when_no_gzi(self):
        # Without a .gzi index the builder must use IndexedFastaAdapter, not
        # BgzipFastaAdapter (which requires gzi and would fail to load in JBrowse2).
        track = CramTrack(self._spec(include_gzi=False), ASSEMBLY).build()
        assert track["adapter"]["sequenceAdapter"]["type"] == "IndexedFastaAdapter"

    def test_sequence_adapter_uses_bgzip_fasta_when_gzi_present(self):
        track = CramTrack(self._spec(include_gzi=True), ASSEMBLY).build()
        assert track["adapter"]["sequenceAdapter"]["type"] == "BgzipFastaAdapter"

    def test_assembly_names(self):
        track = CramTrack(self._spec(), ASSEMBLY).build()
        assert track["assemblyNames"] == [ASSEMBLY]


# ---------------------------------------------------------------------------
# BigWigTrack
# ---------------------------------------------------------------------------

class TestBigWigTrack:
    def _spec(self):
        return {"name": "Coverage", "bigwig_url": "https://example.com/coverage.bw"}

    def test_type(self):
        track = BigWigTrack(self._spec(), ASSEMBLY).build()
        assert track["type"] == "QuantitativeTrack"

    def test_adapter_type(self):
        track = BigWigTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["type"] == "BigWigAdapter"

    def test_bigwig_location(self):
        track = BigWigTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["bigWigLocation"]["uri"] == "https://example.com/coverage.bw"

    def test_track_id(self):
        track = BigWigTrack(self._spec(), ASSEMBLY).build()
        assert track["trackId"] == "coverage"

    def test_assembly_names(self):
        track = BigWigTrack(self._spec(), ASSEMBLY).build()
        assert track["assemblyNames"] == [ASSEMBLY]


# ---------------------------------------------------------------------------
# VcfTrack
# ---------------------------------------------------------------------------

class TestVcfTrack:
    def _spec(self):
        return {
            "name": "Variants",
            "vcf_gz_url": "https://example.com/v.vcf.gz",
            "tbi_url": "https://example.com/v.vcf.gz.tbi",
        }

    def test_type(self):
        track = VcfTrack(self._spec(), ASSEMBLY).build()
        assert track["type"] == "VariantTrack"

    def test_adapter_type(self):
        track = VcfTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["type"] == "VcfTabixAdapter"

    def test_vcf_gz_location(self):
        track = VcfTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["vcfGzLocation"]["uri"] == "https://example.com/v.vcf.gz"

    def test_tbi_location(self):
        track = VcfTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["index"]["location"]["uri"] == "https://example.com/v.vcf.gz.tbi"

    def test_index_type_is_tbi(self):
        track = VcfTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["index"]["indexType"] == "TBI"

    def test_assembly_names(self):
        track = VcfTrack(self._spec(), ASSEMBLY).build()
        assert track["assemblyNames"] == [ASSEMBLY]


# ---------------------------------------------------------------------------
# GffTrack
# ---------------------------------------------------------------------------

class TestGffTrack:
    def _spec(self):
        return {
            "name": "Genes",
            "gff_gz_url": "https://example.com/genes.gff.gz",
            "tbi_url": "https://example.com/genes.gff.gz.tbi",
        }

    def test_type(self):
        track = GffTrack(self._spec(), ASSEMBLY).build()
        assert track["type"] == "FeatureTrack"

    def test_adapter_type(self):
        track = GffTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["type"] == "Gff3TabixAdapter"

    def test_gff_gz_location(self):
        track = GffTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["gffGzLocation"]["uri"] == "https://example.com/genes.gff.gz"

    def test_tbi_location(self):
        track = GffTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["index"]["location"]["uri"] == "https://example.com/genes.gff.gz.tbi"

    def test_index_type_is_tbi(self):
        track = GffTrack(self._spec(), ASSEMBLY).build()
        assert track["adapter"]["index"]["indexType"] == "TBI"

    def test_assembly_names(self):
        track = GffTrack(self._spec(), ASSEMBLY).build()
        assert track["assemblyNames"] == [ASSEMBLY]


# ---------------------------------------------------------------------------
# build_track dispatcher
# ---------------------------------------------------------------------------

class TestBuildTrack:
    def test_dispatches_bam(self):
        spec = {"type": "bam", "name": "S", "bam_url": "https://example.com/s.bam", "bai_url": "https://example.com/s.bam.bai"}
        track = build_track(spec, ASSEMBLY)
        assert track["type"] == "AlignmentsTrack"
        assert track["adapter"]["type"] == "BamAdapter"

    def test_dispatches_bigwig(self):
        spec = {"type": "bigwig", "name": "Cov", "bigwig_url": "https://example.com/c.bw"}
        track = build_track(spec, ASSEMBLY)
        assert track["type"] == "QuantitativeTrack"

    def test_dispatches_vcf(self):
        spec = {"type": "vcf", "name": "V", "vcf_gz_url": "https://example.com/v.vcf.gz", "tbi_url": "https://example.com/v.vcf.gz.tbi"}
        track = build_track(spec, ASSEMBLY)
        assert track["type"] == "VariantTrack"

    def test_dispatches_gff(self):
        spec = {"type": "gff", "name": "G", "gff_gz_url": "https://example.com/g.gff.gz", "tbi_url": "https://example.com/g.gff.gz.tbi"}
        track = build_track(spec, ASSEMBLY)
        assert track["type"] == "FeatureTrack"

    def test_dispatches_cram(self):
        spec = {
            "type": "cram",
            "name": "C",
            "cram_url": "https://example.com/s.cram",
            "crai_url": "https://example.com/s.cram.crai",
            "sequence_adapter": {
                "fasta_url": "https://example.com/ref.fa.gz",
                "fai_url": "https://example.com/ref.fa.gz.fai",
                "gzi_url": "https://example.com/ref.fa.gz.gzi",
            },
        }
        track = build_track(spec, ASSEMBLY)
        assert track["type"] == "AlignmentsTrack"
        assert track["adapter"]["type"] == "CramAdapter"

    def test_unknown_type_raises(self):
        with pytest.raises(KeyError):
            build_track({"type": "unknown", "name": "X"}, ASSEMBLY)

    def test_track_builders_registry_keys(self):
        assert set(TRACK_BUILDERS.keys()) == {"bam", "cram", "bigwig", "vcf", "gff"}


# ---------------------------------------------------------------------------
# Index inference
# ---------------------------------------------------------------------------

class TestIndexInference:
    def test_bai_inferred_from_bam_url(self):
        from cirro_jbrowse_config.tracks import resolve_track_spec
        raw = {"type": "bam", "name": "S", "file": {"url": "https://example.com/s.bam"}}
        resolved = resolve_track_spec(raw, lambda ref: ref["url"])
        assert resolved["bai_url"] == "https://example.com/s.bam.bai"

    def test_bai_explicit_overrides_inference(self):
        from cirro_jbrowse_config.tracks import resolve_track_spec
        raw = {
            "type": "bam",
            "name": "S",
            "file": {"url": "https://example.com/s.bam"},
            "index": {"url": "https://example.com/custom.bai"},
        }
        resolved = resolve_track_spec(raw, lambda ref: ref["url"])
        assert resolved["bai_url"] == "https://example.com/custom.bai"

    def test_tbi_inferred_from_vcf_url(self):
        from cirro_jbrowse_config.tracks import resolve_track_spec
        raw = {"type": "vcf", "name": "V", "file": {"url": "https://example.com/v.vcf.gz"}}
        resolved = resolve_track_spec(raw, lambda ref: ref["url"])
        assert resolved["tbi_url"] == "https://example.com/v.vcf.gz.tbi"

    def test_tbi_inferred_from_gff_url(self):
        from cirro_jbrowse_config.tracks import resolve_track_spec
        raw = {"type": "gff", "name": "G", "file": {"url": "https://example.com/g.gff.gz"}}
        resolved = resolve_track_spec(raw, lambda ref: ref["url"])
        assert resolved["tbi_url"] == "https://example.com/g.gff.gz.tbi"

    def test_crai_inferred_from_cram_url(self):
        from cirro_jbrowse_config.tracks import resolve_track_spec
        raw = {
            "type": "cram",
            "name": "C",
            "file": {"url": "https://example.com/s.cram"},
            "sequence_adapter": {
                "fasta": {"url": "https://example.com/ref.fa.gz"},
                "fai": {"url": "https://example.com/ref.fa.gz.fai"},
            },
        }
        resolved = resolve_track_spec(raw, lambda ref: ref["url"])
        assert resolved["crai_url"] == "https://example.com/s.cram.crai"


# ---------------------------------------------------------------------------
# Slug generation
# ---------------------------------------------------------------------------

class TestSlugGeneration:
    def test_spaces_become_underscores(self):
        track = BigWigTrack(
            {"name": "My Coverage Track", "bigwig_url": "https://example.com/c.bw"},
            ASSEMBLY,
        ).build()
        assert track["trackId"] == "my_coverage_track"

    def test_uppercase_lowercased(self):
        track = BigWigTrack(
            {"name": "Coverage", "bigwig_url": "https://example.com/c.bw"},
            ASSEMBLY,
        ).build()
        assert track["trackId"] == "coverage"

    def test_special_chars_become_underscores(self):
        track = BigWigTrack(
            {"name": "Sample-1 (rep2)", "bigwig_url": "https://example.com/c.bw"},
            ASSEMBLY,
        ).build()
        assert track["trackId"] == "sample_1__rep2_"
