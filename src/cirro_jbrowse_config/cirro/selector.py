from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Optional

import boto3
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
    ".gtf.gz",
    ".gtf",
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
    ".gtf.gz": "gtf",
    ".gtf": "gtf",
}

# File extensions that require an explicit index file alongside the main file.
_INDEX_EXTENSIONS = {
    ".bam": (".bai", "BAI index"),
    ".cram": (".crai", "CRAI index"),
    ".vcf.gz": (".tbi", "TBI index"),
    ".gff.gz": (".tbi", "TBI index"),
    ".gff3.gz": (".tbi", "TBI index"),
    ".gtf.gz": (".tbi", "TBI index"),
}

# Matches any S3 URI whose final extension is .fa / .fasta / .fna (optionally .gz),
# not followed by another extension (e.g. excludes .fa.fai).
FASTA_URI_PATTERN = re.compile(
    r"(s3://\S+\.(?:fa|fasta|fna)(?:\.gz)?)(?=\s|$)",
    re.MULTILINE,
)
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

# Detects Cirro-hosted paths: s3://bucket/{project_uuid}/{dataset_uuid}/...
_CIRRO_S3_RE = re.compile(r"s3://[^/]+/([0-9a-f-]{36})/([0-9a-f-]{36})/(.+)")


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


def _make_file_ref_from_uri(s3_uri: str) -> dict:
    """Build a FileRef from an S3 URI — CirroFileRef for Cirro paths, UrlFileRef otherwise."""
    m = _CIRRO_S3_RE.match(s3_uri)
    if m:
        return {"project_id": m.group(1), "dataset_id": m.group(2), "file_path": m.group(3)}
    return {"url": s3_uri}


def _assembly_name_from_fasta(fasta_uri: str) -> str:
    """Derive an assembly display name from a FASTA filename."""
    stem = PurePosixPath(fasta_uri).name
    if stem.endswith(".gz"):
        stem = stem[:-3]
    return PurePosixPath(stem).stem


def _find_fasta_in_dataset(dataset) -> tuple[str | None, str | None]:
    """
    Read artifacts/process.log from the dataset and return (fasta_uri, fai_uri).

    Returns (None, None) if the log is absent or contains no FASTA URIs.
    Raises ValueError if multiple distinct FASTA URIs are found.
    """
    try:
        body = dataset.get_logs()
    except Exception:
        return None, None

    found = set(FASTA_URI_PATTERN.findall(_ANSI_ESCAPE.sub("", body)))
    if not found:
        return None, None
    if len(found) > 1:
        raise ValueError(f"Multiple FASTA files found in execution log: {found}")
    fasta_uri = found.pop()

    fai_uri = fasta_uri + ".fai"
    if not fasta_uri.startswith("s3://pubweb-references/"):
        try:
            bucket, key = fai_uri.removeprefix("s3://").split("/", 1)
            boto3.client("s3").head_object(Bucket=bucket, Key=key)
        except Exception:
            fai_uri = None

    return fasta_uri, fai_uri


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

        # Auto-detect reference FASTA from execution log
        detected_fasta_uri, detected_fai_uri = _find_fasta_in_dataset(dataset)

        default_assembly = _assembly_name_from_fasta(detected_fasta_uri) if detected_fasta_uri else ""
        assembly_name = questionary.text(
            "Assembly name (e.g. hg38):",
            default=default_assembly,
        ).ask()

        assembly_fasta: Optional[dict] = None
        assembly_fai: Optional[dict] = None

        if detected_fasta_uri:
            print(f"Detected reference FASTA from execution log: {detected_fasta_uri}")
            assembly_fasta = _make_file_ref_from_uri(detected_fasta_uri)
            if detected_fai_uri:
                assembly_fai = _make_file_ref_from_uri(detected_fai_uri)
        else:
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
                    assembly_fai = {"url": fai_uri}
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
        assembly_name: Optional[str] = None,
        tracks: list[dict],
        assembly_fasta: Optional[dict] = None,
        assembly_fai: Optional[dict] = None,
    ) -> dict:
        """Non-interactive mode: builds inputs.json from explicit params.

        Each entry in tracks must contain: project_id, dataset_id, file_path,
        track_type, name. Optionally: index_path.

        If assembly_fasta is not provided, the reference FASTA is detected from
        the first track's dataset execution log (artifacts/process.log).
        If assembly_name is not provided, it is inferred from the FASTA filename.
        """
        if assembly_fasta is None and tracks:
            first = tracks[0]
            try:
                project = self.portal.get_project(first["project_id"])
                dataset = project.get_dataset(first["dataset_id"])
                detected_uri, detected_fai_uri = _find_fasta_in_dataset(dataset)
                if detected_uri:
                    if not assembly_name:
                        assembly_name = _assembly_name_from_fasta(detected_uri)
                    assembly_fasta = _make_file_ref_from_uri(detected_uri)
                    if detected_fai_uri and assembly_fai is None:
                        assembly_fai = _make_file_ref_from_uri(detected_fai_uri)
            except Exception:
                pass

        if not assembly_name:
            assembly_name = "unknown"

        inputs = self._build_inputs(
            assembly_name=assembly_name,
            track_specs=tracks,
            assembly_fasta=assembly_fasta,
            assembly_fai=assembly_fai,
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
