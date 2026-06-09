"""Shared pytest fixtures for cirro-jbrowse-config tests."""

from __future__ import annotations

import sys
import types

import pytest


def _install_cirro_stubs() -> None:
    """Install lightweight stub modules for the cirro SDK and boto3 so tests can
    run without the actual packages installed.  Skipped if the real packages are
    already present."""
    if "cirro" not in sys.modules:
        cirro_mod = types.ModuleType("cirro")

        class DataPortal:
            pass

        cirro_mod.DataPortal = DataPortal  # type: ignore[attr-defined]
        sys.modules["cirro"] = cirro_mod

        cirro_sdk = types.ModuleType("cirro.sdk")
        sys.modules["cirro.sdk"] = cirro_sdk

        cirro_sdk_exc = types.ModuleType("cirro.sdk.exceptions")

        class DataPortalAssetNotFound(Exception):
            pass

        cirro_sdk_exc.DataPortalAssetNotFound = DataPortalAssetNotFound  # type: ignore[attr-defined]
        sys.modules["cirro.sdk.exceptions"] = cirro_sdk_exc

    if "boto3" not in sys.modules:
        boto3_mod = types.ModuleType("boto3")
        sys.modules["boto3"] = boto3_mod


_install_cirro_stubs()


@pytest.fixture()
def minimal_inputs():
    """Minimal valid inputs.json dict for use in tests."""
    return {
        "assembly": {"name": "hg38"},
        "tracks": [],
    }


@pytest.fixture()
def cirro_file_ref():
    """A valid CirroFileRef dict."""
    return {
        "project_id": "proj-123",
        "dataset_id": "ds-456",
        "file_path": "results/sample.bam",
    }


@pytest.fixture()
def url_file_ref():
    """A valid UrlFileRef dict."""
    return {"url": "https://example.com/sample.bam"}
