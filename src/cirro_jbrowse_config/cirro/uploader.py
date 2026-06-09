from __future__ import annotations

import sys
from pathlib import Path

from cirro import DataPortal
from cirro.sdk.exceptions import DataPortalAssetNotFound


class DatasetUploader:
    def __init__(self, portal: DataPortal) -> None:
        self.portal = portal

    def upload(
        self,
        source_dir: str | Path,
        project_id: str,
        dataset_name: str,
        description: str = "",
    ) -> str:
        """Upload source_dir as a new Cirro dataset. Returns the dataset ID."""
        project = self.portal.get_project(project_id)
        process = self._get_ingest_process()
        dataset = project.upload_dataset(
            name=dataset_name,
            description=description,
            process=process,
            upload_folder=str(Path(source_dir)),
        )
        return dataset.id

    def _get_ingest_process(self):
        try:
            return self.portal.get_process_by_name("Upload Files", ingest=True)
        except DataPortalAssetNotFound:
            processes = list(self.portal.list_processes(ingest=True))
            if not processes:
                raise RuntimeError("No ingest processes found in this Cirro instance")
            chosen = processes[0]
            print(
                f'Warning: process "Upload Files" not found; falling back to "{chosen.name}"',
                file=sys.stderr,
            )
            return chosen
