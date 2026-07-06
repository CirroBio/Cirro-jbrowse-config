"""Tests for JSON schema loading and validation."""

import pytest
import jsonschema

from cirro_jbrowse_config.schemas import load_schema, validate


def test_load_inputs_schema():
    schema = load_schema("inputs")
    assert schema["title"] == "JBrowse Inputs"


def test_load_config_schema():
    schema = load_schema("config")
    assert schema["title"] == "JBrowse2 Config"


def test_load_track_schema_bam():
    schema = load_schema("tracks/bam")
    assert "bam_url" in schema["required"]
    assert "bai_url" in schema["required"]


def test_load_track_schema_cram():
    schema = load_schema("tracks/cram")
    assert "cram_url" in schema["required"]
    assert "crai_url" in schema["required"]
    assert "sequence_adapter" in schema["required"]


def test_load_track_schema_bigwig():
    schema = load_schema("tracks/bigwig")
    assert "bigwig_url" in schema["required"]


def test_load_track_schema_vcf():
    schema = load_schema("tracks/vcf")
    assert "vcf_gz_url" in schema["required"]
    assert "tbi_url" in schema["required"]


def test_load_track_schema_gff():
    schema = load_schema("tracks/gff")
    assert "gff_gz_url" in schema["required"]
    assert "tbi_url" in schema["required"]


def test_validate_minimal_inputs(minimal_inputs):
    validate(minimal_inputs, "inputs")


def test_validate_inputs_missing_assembly():
    with pytest.raises(jsonschema.ValidationError):
        validate({"tracks": []}, "inputs")


def test_validate_inputs_missing_tracks():
    with pytest.raises(jsonschema.ValidationError):
        validate({"assembly": {"name": "hg38"}}, "inputs")


def test_validate_inputs_extra_property_rejected():
    with pytest.raises(jsonschema.ValidationError):
        validate({"assembly": {"name": "hg38"}, "tracks": [], "extra": True}, "inputs")


def test_validate_inputs_url_file_ref(url_file_ref):
    inputs = {
        "assembly": {
            "name": "hg38",
            "sequence": url_file_ref,
        },
        "tracks": [],
    }
    validate(inputs, "inputs")


def test_validate_inputs_cirro_file_ref(cirro_file_ref):
    inputs = {
        "assembly": {
            "name": "hg38",
            "sequence": cirro_file_ref,
        },
        "tracks": [],
    }
    validate(inputs, "inputs")


def test_load_schema_not_found():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent")
