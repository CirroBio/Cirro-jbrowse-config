from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import questionary
from cirro import DataPortal

from cirro_jbrowse_config.schemas import validate


TRACK_TYPE_CHOICES = ["bam", "cram", "bigwig", "vcf", "gff"]

# Extensions that can be loaded as tracks in JBrowse2.
_TRACK_EXTENSIONS = {
    ".bam",
    ".cram",
    ".bw",
    ".bigwig",
    ".vcf.gz",
    ".vcf",
    ".gff.gz",
    ".gff3.gz",
    ".gff",
    ".gff3",
}

# Maps file extension to the JBrowse2 track type it unambiguously implies.
_EXTENSION_TO_TRACK_TYPE: dict[str, str] = {
    ".bam": "bam",
    ".cram": "cram",
    ".bw": "bigwig",
    ".bigwig": "bigwig",
    ".vcf.gz": "vcf",
    ".vcf": "vcf",
    ".gff.gz": "gff",
    ".gff3.gz": "gff",
    ".gff": "gff",
    ".gff3": "gff",
}

# File extensions that require an explicit index file alongside the main file.
_INDEX_EXTENSIONS = {
    ".bam": (".bai", "BAI index"),
    ".cram": (".crai", "CRAI index"),
    ".vcf.gz": (".tbi", "TBI index"),
    ".gff.gz": (".tbi", "TBI index"),
    ".gff3.gz": (".tbi", "TBI index"),
}


def _is_jbrowse_compatible(file_path: str) -> bool:
    lower = file_path.lower()
    return any(lower.endswith(ext) for ext in _TRACK_EXTENSIONS)


def _infer_track_type(file_path: str) -> str | None:
    """Return the track type implied by the file extension, or None if ambiguous."""
    lower = file_path.lower()
    for ext, track_type in _EXTENSION_TO_TRACK_TYPE.items():
        if lower.endswith(ext):
            return track_type
    return None


def _default_track_name(file_path: str) -> str:
    """Derive a display name from the filename by stripping all recognised extensions."""
    name = Path(file_path).name
    lower = name.lower()
    for ext in sorted(_TRACK_EXTENSIONS, key=len, reverse=True):
        if lower.endswith(ext):
            return name[: -len(ext)]
    # Fallback: strip one extension.
    return Path(name).stem


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
        dataset_map = {f"{d.name}  ({d.id})": d for d in datasets}
        dataset_key = questionary.autocomplete(
            "Select a dataset:",
            choices=list(dataset_map.keys()),
            match_middle=True,
        ).ask()
        dataset = dataset_map[dataset_key]

        files = list(dataset.list_files())
        file_paths = [f.relative_path for f in files if _is_jbrowse_compatible(f.relative_path)]

        selected_paths = questionary.checkbox(
            "Select files to include as tracks:",
            choices=file_paths,
        ).ask()

        customize_names = questionary.confirm(
            "Customize track display names?",
            default=False,
        ).ask()

        needs_index = any(_needs_index_prompt(p) for p in selected_paths)
        customize_indices = needs_index and questionary.confirm(
            "Provide custom index file paths? (skip to let generator infer)",
            default=False,
        ).ask()

        track_specs: list[dict] = []
        for path in selected_paths:
            inferred_type = _infer_track_type(path)
            if inferred_type is not None:
                track_type = inferred_type
            else:
                track_type = questionary.select(
                    f"Track type for {path}:",
                    choices=TRACK_TYPE_CHOICES,
                ).ask()

            if customize_names:
                name = questionary.text(
                    f"Display name for {path}:",
                    default=_default_track_name(path),
                ).ask()
            else:
                name = _default_track_name(path)

            index_path: str | None = None
            if customize_indices and _needs_index_prompt(path) is not None:
                _, label = _needs_index_prompt(path)
                index_path = questionary.select(
                    f"Select {label} for {Path(path).name}:",
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
            fasta_source = questionary.select(
                "How would you like to provide the reference FASTA?",
                choices=["Enter S3 URI directly", "Select from a Cirro dataset"],
            ).ask()

            if fasta_source == "Enter S3 URI directly":
                fasta_uri = questionary.text("S3 URI for the FASTA file:").ask()
                assembly_fasta = {"url": fasta_uri}
                fai_uri = questionary.text(
                    "FAI index URI:",
                    default=fasta_uri + ".fai",
                ).ask()
                assembly_fai: Optional[dict] = {"url": fai_uri}
            else:
                fasta_projects = list(self.portal.list_projects())
                fasta_project_name = questionary.select(
                    "Select project containing the FASTA:",
                    choices=[p.name for p in fasta_projects],
                ).ask()
                fasta_project = next(p for p in fasta_projects if p.name == fasta_project_name)

                fasta_datasets = list(fasta_project.list_datasets())
                fasta_dataset_map = {f"{d.name}  ({d.id})": d for d in fasta_datasets}
                fasta_dataset_key = questionary.autocomplete(
                    "Select dataset containing the FASTA:",
                    choices=list(fasta_dataset_map.keys()),
                    match_middle=True,
                ).ask()
                fasta_dataset = fasta_dataset_map[fasta_dataset_key]

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
                fai_file_path = questionary.text(
                    "FAI index file path (within same dataset):",
                    default=fasta_file_path + ".fai",
                ).ask()
                assembly_fai = {
                    "project_id": fasta_project.id,
                    "dataset_id": fasta_dataset.id,
                    "file_path": fai_file_path,
                }
        else:
            assembly_fai = None

        inputs = self._build_inputs(
            assembly_name=assembly_name,
            track_specs=track_specs,
            assembly_fasta=assembly_fasta,
            assembly_fai=assembly_fai,
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
        assembly_fai: Optional[dict] = None,
    ) -> dict:
        """Shared: build and validate the inputs dict from resolved selections."""
        assembly: dict = {"name": assembly_name}
        if assembly_fasta is not None:
            if "url" in assembly_fasta:
                assembly["sequence"] = {"url": assembly_fasta["url"]}
            else:
                assembly["sequence"] = _make_file_ref(
                    assembly_fasta["project_id"],
                    assembly_fasta["dataset_id"],
                    assembly_fasta["file_path"],
                )
        if assembly_fai is not None:
            if "url" in assembly_fai:
                assembly["fai"] = {"url": assembly_fai["url"]}
            else:
                assembly["fai"] = _make_file_ref(
                    assembly_fai["project_id"],
                    assembly_fai["dataset_id"],
                    assembly_fai["file_path"],
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
