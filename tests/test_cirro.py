"""Tests for Cirro SDK integration: resolvers, FileSelector, and DatasetUploader."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from cirro_jbrowse_config.cirro import (
    make_presigned_resolver,
    make_render_service_resolver,
    RENDER_SERVICE_WORKER_PREFIX,
    PUBWEB_S3_PREFIX,
)
from cirro_jbrowse_config.cirro.selector import FileSelector
from cirro_jbrowse_config.cirro.uploader import DatasetUploader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_portal_with_file(project_id: str, dataset_id: str, file_path: str, s3_uri: str):
    """Build a mock DataPortal that returns a file with the given absolute_path."""
    mock_file = MagicMock()
    mock_file.absolute_path = s3_uri

    mock_dataset = MagicMock()
    mock_dataset.get_file.return_value = mock_file

    mock_project = MagicMock()
    mock_project.get_dataset.return_value = mock_dataset

    mock_portal = MagicMock()
    mock_portal.get_project.return_value = mock_project

    return mock_portal, mock_project, mock_dataset, mock_file


# ---------------------------------------------------------------------------
# make_presigned_resolver
# ---------------------------------------------------------------------------

class TestMakePresignedResolver:
    def test_resolves_cirro_file_ref(self):
        mock_portal, mock_project, mock_dataset, _ = _make_portal_with_file(
            "proj-1", "ds-1", "data/sample.bam", "s3://my-bucket/path/to/sample.bam"
        )
        expected_url = "https://presigned.example.com/sample.bam?X-Amz-Signature=abc"

        with patch("cirro_jbrowse_config.cirro.boto3") as mock_boto3:
            mock_s3_client = MagicMock()
            mock_boto3.client.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = expected_url

            resolver = make_presigned_resolver(mock_portal)
            result = resolver({"project_id": "proj-1", "dataset_id": "ds-1", "file_path": "data/sample.bam"})

        assert result == expected_url
        mock_portal.get_project.assert_called_once_with("proj-1")
        mock_project.get_dataset.assert_called_once_with("ds-1")
        mock_dataset.get_file.assert_called_once_with("data/sample.bam")
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "my-bucket", "Key": "path/to/sample.bam"},
            ExpiresIn=3600,
        )

    def test_passes_through_url_file_ref(self):
        mock_portal = MagicMock()
        resolver = make_presigned_resolver(mock_portal)
        result = resolver({"url": "https://example.com/sample.bam"})
        assert result == "https://example.com/sample.bam"
        mock_portal.get_project.assert_not_called()

    def test_pubweb_url_file_ref_uses_render_service(self):
        resolver = make_presigned_resolver(MagicMock())
        result = resolver({"url": "s3://pubweb-references/genomes/hg38.fa"})
        assert result == RENDER_SERVICE_WORKER_PREFIX + "pubweb-references/genomes/hg38.fa"

    def test_bucket_and_key_with_nested_key(self):
        mock_portal, _, _, _ = _make_portal_with_file(
            "p", "d", "f.bam", "s3://bucket/a/b/c/file.bam"
        )
        with patch("cirro_jbrowse_config.cirro.boto3") as mock_boto3:
            mock_s3_client = MagicMock()
            mock_boto3.client.return_value = mock_s3_client
            mock_s3_client.generate_presigned_url.return_value = "https://presigned.url"

            resolver = make_presigned_resolver(mock_portal)
            resolver({"project_id": "p", "dataset_id": "d", "file_path": "f.bam"})

        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "bucket", "Key": "a/b/c/file.bam"},
            ExpiresIn=3600,
        )


# ---------------------------------------------------------------------------
# make_render_service_resolver
# ---------------------------------------------------------------------------

class TestMakeRenderServiceResolver:
    def test_transforms_s3_uri(self):
        mock_portal, _, _, _ = _make_portal_with_file(
            "proj-1", "ds-1", "data/sample.bw", "s3://my-bucket/path/sample.bw"
        )
        resolver = make_render_service_resolver(mock_portal)
        result = resolver({"project_id": "proj-1", "dataset_id": "ds-1", "file_path": "data/sample.bw"})

        assert result == RENDER_SERVICE_WORKER_PREFIX + "my-bucket/path/sample.bw"

    def test_passes_through_url_file_ref(self):
        mock_portal = MagicMock()
        resolver = make_render_service_resolver(mock_portal)
        url = "https://example.com/sample.bigwig"
        result = resolver({"url": url})
        assert result == url
        mock_portal.get_project.assert_not_called()

    def test_render_service_pubweb_url_file_ref(self):
        mock_portal = MagicMock()
        resolver = make_render_service_resolver(mock_portal)
        result = resolver({"url": "s3://pubweb-references/genomes/hg38.fa"})
        assert result == RENDER_SERVICE_WORKER_PREFIX + "pubweb-references/genomes/hg38.fa"
        mock_portal.get_project.assert_not_called()

    def test_prefix_format(self):
        assert RENDER_SERVICE_WORKER_PREFIX == "https://cirrobio.github.io/render-service-worker/s3/"

    def test_nested_key_in_bucket(self):
        mock_portal, _, _, _ = _make_portal_with_file(
            "p", "d", "f", "s3://bucket/a/b/c/d.bw"
        )
        resolver = make_render_service_resolver(mock_portal)
        result = resolver({"project_id": "p", "dataset_id": "d", "file_path": "f"})
        assert result == RENDER_SERVICE_WORKER_PREFIX + "bucket/a/b/c/d.bw"


# ---------------------------------------------------------------------------
# FileSelector._build_inputs
# ---------------------------------------------------------------------------

class TestBuildInputs:
    def setup_method(self):
        self.selector = FileSelector(portal=MagicMock())

    def test_minimal_no_tracks(self):
        result = self.selector._build_inputs(
            assembly_name="hg38",
            track_specs=[],
        )
        assert result["assembly"]["name"] == "hg38"
        assert result["tracks"] == []
        assert "sequence" not in result["assembly"]

    def test_with_assembly_fasta(self):
        result = self.selector._build_inputs(
            assembly_name="hg38",
            track_specs=[],
            assembly_fasta={
                "project_id": "p1",
                "dataset_id": "d1",
                "file_path": "ref/hg38.fa",
            },
        )
        assert result["assembly"]["sequence"] == {
            "project_id": "p1",
            "dataset_id": "d1",
            "file_path": "ref/hg38.fa",
        }

    def test_with_track_without_index(self):
        result = self.selector._build_inputs(
            assembly_name="hg38",
            track_specs=[
                {
                    "project_id": "p1",
                    "dataset_id": "d1",
                    "file_path": "data/sample.bw",
                    "track_type": "bigwig",
                    "name": "Coverage",
                }
            ],
        )
        assert len(result["tracks"]) == 1
        track = result["tracks"][0]
        assert track["type"] == "bigwig"
        assert track["name"] == "Coverage"
        assert track["file"] == {"project_id": "p1", "dataset_id": "d1", "file_path": "data/sample.bw"}
        assert "index" not in track

    def test_with_track_with_explicit_index(self):
        result = self.selector._build_inputs(
            assembly_name="hg38",
            track_specs=[
                {
                    "project_id": "p1",
                    "dataset_id": "d1",
                    "file_path": "data/sample.bam",
                    "track_type": "bam",
                    "name": "Alignments",
                    "index_path": "data/sample.bam.bai",
                }
            ],
        )
        track = result["tracks"][0]
        assert track["index"] == {
            "project_id": "p1",
            "dataset_id": "d1",
            "file_path": "data/sample.bam.bai",
        }

    def test_index_path_none_excluded(self):
        result = self.selector._build_inputs(
            assembly_name="hg38",
            track_specs=[
                {
                    "project_id": "p1",
                    "dataset_id": "d1",
                    "file_path": "data/sample.bam",
                    "track_type": "bam",
                    "name": "Alignments",
                    "index_path": None,
                }
            ],
        )
        track = result["tracks"][0]
        assert "index" not in track

    def test_multiple_tracks(self):
        result = self.selector._build_inputs(
            assembly_name="mm10",
            track_specs=[
                {
                    "project_id": "p",
                    "dataset_id": "d",
                    "file_path": "a.bam",
                    "track_type": "bam",
                    "name": "Track A",
                },
                {
                    "project_id": "p",
                    "dataset_id": "d",
                    "file_path": "b.bw",
                    "track_type": "bigwig",
                    "name": "Track B",
                },
            ],
        )
        assert len(result["tracks"]) == 2

    def test_invalid_track_type_raises(self):
        import jsonschema
        with pytest.raises(jsonschema.ValidationError):
            self.selector._build_inputs(
                assembly_name="hg38",
                track_specs=[
                    {
                        "project_id": "p",
                        "dataset_id": "d",
                        "file_path": "a.txt",
                        "track_type": "invalid_type",
                        "name": "Bad Track",
                    }
                ],
            )


# ---------------------------------------------------------------------------
# FileSelector.run_non_interactive
# ---------------------------------------------------------------------------

class TestRunNonInteractive:
    def test_writes_valid_inputs_json(self, tmp_path):
        selector = FileSelector(portal=MagicMock())
        output_path = tmp_path / "inputs.json"

        result = selector.run_non_interactive(
            output_path,
            assembly_name="hg38",
            tracks=[
                {
                    "project_id": "proj-1",
                    "dataset_id": "ds-1",
                    "file_path": "data/sample.bam",
                    "track_type": "bam",
                    "name": "My BAM",
                }
            ],
        )

        assert output_path.exists()
        written = json.loads(output_path.read_text())
        assert written == result
        assert written["assembly"]["name"] == "hg38"
        assert len(written["tracks"]) == 1

    def test_returns_dict_matching_file(self, tmp_path):
        selector = FileSelector(portal=MagicMock())
        output_path = tmp_path / "out.json"

        result = selector.run_non_interactive(
            output_path,
            assembly_name="mm10",
            tracks=[],
        )

        written = json.loads(output_path.read_text())
        assert written == result

    def test_with_assembly_fasta(self, tmp_path):
        selector = FileSelector(portal=MagicMock())
        output_path = tmp_path / "inputs.json"

        result = selector.run_non_interactive(
            output_path,
            assembly_name="hg38",
            tracks=[],
            assembly_fasta={
                "project_id": "p1",
                "dataset_id": "d1",
                "file_path": "ref/hg38.fa",
            },
        )

        assert result["assembly"]["sequence"]["file_path"] == "ref/hg38.fa"

    def test_with_track_index(self, tmp_path):
        selector = FileSelector(portal=MagicMock())
        output_path = tmp_path / "inputs.json"

        result = selector.run_non_interactive(
            output_path,
            assembly_name="hg38",
            tracks=[
                {
                    "project_id": "p1",
                    "dataset_id": "d1",
                    "file_path": "data/sample.vcf.gz",
                    "track_type": "vcf",
                    "name": "Variants",
                    "index_path": "data/sample.vcf.gz.tbi",
                }
            ],
        )

        track = result["tracks"][0]
        assert track["index"]["file_path"] == "data/sample.vcf.gz.tbi"

    def test_accepts_pathlib_output_path(self, tmp_path):
        selector = FileSelector(portal=MagicMock())
        output_path = tmp_path / "sub" / "inputs.json"
        output_path.parent.mkdir(parents=True)

        selector.run_non_interactive(
            output_path,
            assembly_name="hg38",
            tracks=[],
        )

        assert output_path.exists()


# ---------------------------------------------------------------------------
# DatasetUploader.upload
# ---------------------------------------------------------------------------

class TestDatasetUploader:
    def _make_portal_with_process(self, process_name: str = "Upload Files"):
        mock_process = MagicMock()
        mock_process.name = process_name

        mock_dataset = MagicMock()
        mock_dataset.id = "new-dataset-id-123"

        mock_project = MagicMock()
        mock_project.upload_dataset.return_value = mock_dataset

        mock_portal = MagicMock()
        mock_portal.get_project.return_value = mock_project
        mock_portal.get_process_by_name.return_value = mock_process

        return mock_portal, mock_project, mock_process, mock_dataset

    def test_upload_returns_dataset_id(self, tmp_path):
        mock_portal, mock_project, mock_process, mock_dataset = self._make_portal_with_process()
        uploader = DatasetUploader(mock_portal)

        dataset_id = uploader.upload(
            source_dir=tmp_path,
            project_id="proj-abc",
            dataset_name="My JBrowse Config",
        )

        assert dataset_id == "new-dataset-id-123"

    def test_upload_calls_get_project(self, tmp_path):
        mock_portal, mock_project, _, _ = self._make_portal_with_process()
        uploader = DatasetUploader(mock_portal)

        uploader.upload(tmp_path, "proj-abc", "My Config")

        mock_portal.get_project.assert_called_once_with("proj-abc")

    def test_upload_calls_upload_dataset_with_correct_args(self, tmp_path):
        mock_portal, mock_project, mock_process, _ = self._make_portal_with_process()
        uploader = DatasetUploader(mock_portal)

        uploader.upload(tmp_path, "proj-abc", "My Config", description="Generated by JBrowse")

        mock_project.upload_dataset.assert_called_once_with(
            name="My Config",
            description="Generated by JBrowse",
            process=mock_process,
            upload_folder=str(tmp_path),
        )

    def test_upload_uses_get_process_by_name(self, tmp_path):
        mock_portal, _, mock_process, _ = self._make_portal_with_process()
        uploader = DatasetUploader(mock_portal)

        uploader.upload(tmp_path, "proj-abc", "Config")

        mock_portal.get_process_by_name.assert_called_once_with("Files", ingest=True)

    def test_default_description_is_empty_string(self, tmp_path):
        mock_portal, mock_project, mock_process, _ = self._make_portal_with_process()
        uploader = DatasetUploader(mock_portal)

        uploader.upload(tmp_path, "proj-abc", "Config")

        _, kwargs = mock_project.upload_dataset.call_args
        assert kwargs["description"] == ""
