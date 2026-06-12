from __future__ import annotations

from pathlib import Path

from cirro import DataPortal


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
        process = self.portal.get_process_by_name("Files", ingest=True)
        dataset = project.upload_dataset(
            name=dataset_name,
            description=description,
            process=process,
            upload_folder=str(Path(source_dir)),
        )
        return dataset.id
