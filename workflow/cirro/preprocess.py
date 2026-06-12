#!/usr/bin/env python3

import json
import re
import boto3
from pathlib import PurePosixPath
from cirro.helpers.preprocess_dataset import PreprocessDataset


s3 = boto3.client("s3")

# Match any S3 URI whose final extension is .fa / .fasta / .fna (optionally .gz),
# not followed by another extension (e.g. excludes .fa.fai, .fasta.gz.fai).
FASTA_URI_PATTERN = re.compile(
    r"(s3://\S+\.(?:fa|fasta|fna)(?:\.gz)?)(?=\s|$)",
    re.MULTILINE,
)


def parse_s3_uri(s3_uri):
    """Split s3://bucket/key into (bucket, key)."""
    without_scheme = s3_uri.removeprefix("s3://")
    bucket, _, key = without_scheme.partition("/")
    return bucket, key


def make_file_ref(s3_uri):
    """
    Build a FileRef dict from an S3 URI.

    Cirro-hosted paths (s3://bucket/{project_uuid}/{dataset_uuid}/...) become
    CirroFileRef so the generate step can issue presigned URLs.  Everything else
    becomes a UrlFileRef used as-is.
    """
    m = re.match(
        r"s3://[^/]+/([0-9a-f-]{36})/([0-9a-f-]{36})/(.+)",
        s3_uri,
    )
    if m:
        return {"project_id": m.group(1), "dataset_id": m.group(2), "file_path": m.group(3)}
    return {"url": s3_uri}


def s3_exists(s3_uri):
    bucket, key = parse_s3_uri(s3_uri)
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def find_index(file_uri, suffixes):
    """Return the first adjacent index URI that exists on S3, or None."""
    for suffix in suffixes:
        candidate = file_uri + suffix
        if s3_exists(candidate):
            return candidate
    return None


def selected_paths(params, key):
    """Return a list of S3 URIs from a comma-separated param value."""
    value = params.get(key, "")
    if not isinstance(value, str) or not value.strip():
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def infer_name(s3_uri):
    """Derive a display name from the filename (first dot-delimited segment)."""
    return PurePosixPath(s3_uri).name.split(".")[0]


def find_fasta_in_logs(s3_base):
    """
    Read {s3_base}/artifacts/process.log and return the set of FASTA S3 URIs
    found by FASTA_URI_PATTERN.
    """
    log_uri = s3_base.rstrip("/") + "/artifacts/process.log"
    bucket, key = parse_s3_uri(log_uri)
    body = (
        s3.get_object(Bucket=bucket, Key=key)["Body"]
        .read()
        .decode("utf-8", errors="replace")
    )
    return {m.group(1) for m in FASTA_URI_PATTERN.finditer(body)}


if __name__ == "__main__":
    ds = PreprocessDataset.from_running()

    ds.logger.info("Params: " + json.dumps(ds.params, default=str))

    # Resolve reference FASTA: use the form param if provided, otherwise scan logs
    fasta_uri = ds.params.get("fasta") or None
    if fasta_uri:
        ds.logger.info(f"Using user-supplied reference FASTA: {fasta_uri}")
    else:
        fasta_by_dataset = {}
        for d in ds.metadata.get("inputs", []):
            paths = find_fasta_in_logs(d["s3"])
            if paths:
                fasta_by_dataset[d["id"]] = paths
                ds.logger.info(f"Dataset {d['id']}: found FASTA candidates {paths}")

        all_fasta = set().union(*fasta_by_dataset.values()) if fasta_by_dataset else set()
        if len(all_fasta) > 1:
            raise ValueError(f"Input datasets reference different FASTA files: {all_fasta}")
        fasta_uri = next(iter(all_fasta), None)
        if not fasta_uri:
            ds.logger.info("No reference FASTA found in execution logs")

    # Assembly
    assembly_name = ds.params.get("assembly_name")
    if not assembly_name and fasta_uri:
        stem = PurePosixPath(fasta_uri).name
        if stem.endswith(".gz"):
            stem = stem[:-3]
        assembly_name = PurePosixPath(stem).stem
    assembly_name = assembly_name or "unknown"

    assembly = {"name": assembly_name}
    if fasta_uri:
        assembly["sequence"] = make_file_ref(fasta_uri)
        fai_uri = fasta_uri + ".fai"
        if s3_exists(fai_uri):
            assembly["fai"] = make_file_ref(fai_uri)
        ds.logger.info(f"Reference FASTA: {fasta_uri}")

    # Tracks
    tracks = []

    for path in selected_paths(ds.params, "bam"):
        idx = find_index(path, [".bai"])
        track = {"type": "bam", "name": infer_name(path), "file": make_file_ref(path)}
        if idx:
            track["index"] = make_file_ref(idx)
        tracks.append(track)

    for path in selected_paths(ds.params, "cram"):
        idx = find_index(path, [".crai"])
        track = {"type": "cram", "name": infer_name(path), "file": make_file_ref(path)}
        if idx:
            track["index"] = make_file_ref(idx)
        if "sequence" in assembly and "fai" in assembly:
            track["sequence_adapter"] = {
                "fasta": assembly["sequence"],
                "fai": assembly["fai"],
            }
        tracks.append(track)

    for path in selected_paths(ds.params, "vcf"):
        idx = find_index(path, [".tbi", ".csi"])
        track = {"type": "vcf", "name": infer_name(path), "file": make_file_ref(path)}
        if idx:
            track["index"] = make_file_ref(idx)
        tracks.append(track)

    for path in selected_paths(ds.params, "bigwig"):
        track = {"type": "bigwig", "name": infer_name(path), "file": make_file_ref(path)}
        tracks.append(track)

    inputs_data = {"assembly": assembly, "tracks": tracks}
    ds.logger.info("inputs.json:\n" + json.dumps(inputs_data, indent=2))

    with open("inputs.json", "w") as fh:
        json.dump(inputs_data, fh, indent=2)
