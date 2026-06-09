from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import questionary
from cirro import DataPortal

from cirro_jbrowse_config.schemas import validate


TRACK_TYPE_CHOICES = ["bam", "cram", "bigwig", "vcf", "gff"]

# File extensions that require an explicit index file alongside the main file.
_INDEX_EXTENSIONS = {
    ".bam": (".bai", "BAI index"),
    ".cram": (".crai", "CRAI index"),
    ".vcf.gz": (".tbi", "TBI index"),
    ".gff.gz": (".tbi", "TBI index"),
    ".gff3.gz": (".tbi", "TBI index"),
}


def _needs_index_prompt(file_path: str) -> tuple[str, str] | None:
    """Return (expected_ext, label) if this file type benefits from an index prompt, else None."""
    lower = file_path.lower()
    for suffix, info in _INDEX_EXTENSIONS.items():
        if lower.endswith(suffix):
            return info
    return None


def _make_file_ref(project_id: str, dataset_id: str, file_path: str) -> dict:
    return {"project_id": project_id, "dataset_id": dataset_id, "file_path": file_path}


class FileSelector:
    def __init__(self, portal: DataPortal) -> None:
        self.portal = portal

    def run_interactive(self, output_path: str | Path) -> dict:
        """TUI workflow: prompts user to pick project, dataset, files, assembly."""
        projects = list(self.portal.list_projects())
        project_name = questionary.select(
            "Select a project:",
            choices=[p.name for p in projects],
        ).ask()
        project = next(p for p in projects if p.name == project_name)

        datasets = list(project.list_datasets())
        dataset_name = questionary.select(
            "Select a dataset:",
            choices=[d.name for d in datasets],
        ).ask()
        dataset = next(d for d in datasets if d.name == dataset_name)

        files = list(dataset.list_files())
        file_paths = [f.relative_path for f in files]

        selected_paths = questionary.checkbox(
            "Select files to include as tracks:",
            choices=file_paths,
        ).ask()

        track_specs: list[dict] = []
        for path in selected_paths:
            track_type = questionary.select(
                f"Track type for {path}:",
                choices=TRACK_TYPE_CHOICES,
            ).ask()

            default_name = Path(path).stem
            name = questionary.text(
                f"Display name for {path}:",
                default=default_name,
            ).ask()

            index_path: str | None = None
            index_info = _needs_index_prompt(path)
            if index_info is not None:
                expected_ext, label = index_info
                specify = questionary.confirm(
                    f"Specify the {label} for {path} explicitly? (skip to let generator infer)",
                    default=False,
                ).ask()
                if specify:
                    index_path = questionary.select(
                        f"Select {label} file:",
                        choices=file_paths,
                    ).ask()

            spec: dict = {
                "project_id": project.id,
                "dataset_id": dataset.id,
                "file_path": path,
                "track_type": track_type,
                "name": name,
            }
            if index_path is not None:
                spec["index_path"] = index_path
            track_specs.append(spec)

        assembly_name = questionary.text("Assembly name (e.g. hg38):").ask()

        assembly_fasta: Optional[dict] = None
        has_fasta = questionary.confirm("Do you have a reference FASTA?", default=False).ask()
        if has_fasta:
            fasta_projects = list(self.portal.list_projects())
            fasta_project_name = questionary.select(
                "Select project containing the FASTA:",
                choices=[p.name for p in fasta_projects],
            ).ask()
            fasta_project = next(p for p in fasta_projects if p.name == fasta_project_name)

            fasta_datasets = list(fasta_project.list_datasets())
            fasta_dataset_name = questionary.select(
                "Select dataset containing the FASTA:",
                choices=[d.name for d in fasta_datasets],
            ).ask()
            fasta_dataset = next(d for d in fasta_datasets if d.name == fasta_dataset_name)

            fasta_files = list(fasta_dataset.list_files())
            fasta_file_path = questionary.select(
                "Select the FASTA file:",
                choices=[f.relative_path for f in fasta_files],
            ).ask()

            assembly_fasta = {
                "project_id": fasta_project.id,
                "dataset_id": fasta_dataset.id,
                "file_path": fasta_file_path,
            }

        inputs = self._build_inputs(
            assembly_name=assembly_name,
            track_specs=track_specs,
            assembly_fasta=assembly_fasta,
        )
        output_path = Path(output_path)
        output_path.write_text(json.dumps(inputs, indent=2))
        return inputs

    def run_non_interactive(
        self,
        output_path: str | Path,
        *,
        assembly_name: str,
        tracks: list[dict],
        assembly_fasta: Optional[dict] = None,
    ) -> dict:
        """Non-interactive mode for Nextflow: builds inputs.json from explicit params.

        Each entry in tracks must contain: project_id, dataset_id, file_path,
        track_type, name. Optionally: index_path.
        """
        inputs = self._build_inputs(
            assembly_name=assembly_name,
            track_specs=tracks,
            assembly_fasta=assembly_fasta,
        )
        output_path = Path(output_path)
        output_path.write_text(json.dumps(inputs, indent=2))
        return inputs

    def _build_inputs(
        self,
        assembly_name: str,
        track_specs: list[dict],
        assembly_fasta: Optional[dict] = None,
    ) -> dict:
        """Shared: build and validate the inputs dict from resolved selections."""
        assembly: dict = {"name": assembly_name}
        if assembly_fasta is not None:
            assembly["sequence"] = _make_file_ref(
                assembly_fasta["project_id"],
                assembly_fasta["dataset_id"],
                assembly_fasta["file_path"],
            )

        tracks = []
        for spec in track_specs:
            track: dict = {
                "type": spec["track_type"],
                "name": spec["name"],
                "file": _make_file_ref(
                    spec["project_id"],
                    spec["dataset_id"],
                    spec["file_path"],
                ),
            }
            if "index_path" in spec and spec["index_path"] is not None:
                track["index"] = _make_file_ref(
                    spec["project_id"],
                    spec["dataset_id"],
                    spec["index_path"],
                )
            tracks.append(track)

        inputs = {"assembly": assembly, "tracks": tracks}
        validate(inputs, "inputs")
        return inputs
