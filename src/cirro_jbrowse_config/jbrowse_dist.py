"""Download and cache the JBrowse2 UMD distribution bundle."""

from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

JBROWSE_VERSION = "4.3.0"
_BUNDLE_FILENAME = "react-linear-genome-view.umd.production.min.js"
_UNPKG_URL = (
    f"https://unpkg.com/@jbrowse/react-linear-genome-view2"
    f"@{JBROWSE_VERSION}/dist/{_BUNDLE_FILENAME}"
)
_CACHE_PATH = (
    Path.home()
    / ".cache"
    / "cirro_jbrowse_config"
    / "jbrowse"
    / JBROWSE_VERSION
    / _BUNDLE_FILENAME
)


def get_bundle(output_dir: Path) -> None:
    """Copy the JBrowse2 UMD bundle into output_dir, downloading to cache if needed."""
    if not _CACHE_PATH.exists():
        print(f"Downloading JBrowse2 v{JBROWSE_VERSION}...", flush=True)
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_UNPKG_URL, _CACHE_PATH)
    shutil.copy2(_CACHE_PATH, output_dir / _BUNDLE_FILENAME)
