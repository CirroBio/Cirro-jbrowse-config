"""Track builder dispatcher."""

from __future__ import annotations

from typing import Callable

from cirro_jbrowse_config.tracks.bam import BamTrack
from cirro_jbrowse_config.tracks.bigwig import BigWigTrack
from cirro_jbrowse_config.tracks.cram import CramTrack
from cirro_jbrowse_config.tracks.gff import GffTrack
from cirro_jbrowse_config.tracks.vcf import VcfTrack

TRACK_BUILDERS = {
    "bam": BamTrack,
    "cram": CramTrack,
    "bigwig": BigWigTrack,
    "vcf": VcfTrack,
    "gff": GffTrack,
}


def resolve_track_spec(track_spec: dict, url_resolver: Callable[[dict], str]) -> dict:
    """Convert a raw TrackSpec (with FileRefs) into a resolved spec (URL strings).

    The returned dict includes a ``type`` key so that ``build_track`` can dispatch
    to the correct builder class.
    """
    track_type = track_spec["type"]
    name = track_spec["name"]
    file_url = url_resolver(track_spec["file"])

    if track_type == "bam":
        bai_url = url_resolver(track_spec["index"]) if "index" in track_spec else file_url + ".bai"
        return {"type": "bam", "name": name, "bam_url": file_url, "bai_url": bai_url}

    if track_type == "cram":
        crai_url = url_resolver(track_spec["index"]) if "index" in track_spec else file_url + ".crai"
        raw_sa = track_spec.get("sequence_adapter", {})
        seq_adapter: dict = {
            "fasta_url": url_resolver(raw_sa["fasta"]),
            "fai_url": url_resolver(raw_sa["fai"]),
        }
        if "gzi" in raw_sa:
            seq_adapter["gzi_url"] = url_resolver(raw_sa["gzi"])
        return {
            "type": "cram",
            "name": name,
            "cram_url": file_url,
            "crai_url": crai_url,
            "sequence_adapter": seq_adapter,
        }

    if track_type == "bigwig":
        return {"type": "bigwig", "name": name, "bigwig_url": file_url}

    if track_type == "vcf":
        tbi_url = url_resolver(track_spec["index"]) if "index" in track_spec else file_url + ".tbi"
        return {"type": "vcf", "name": name, "vcf_gz_url": file_url, "tbi_url": tbi_url}

    if track_type == "gff":
        tbi_url = url_resolver(track_spec["index"]) if "index" in track_spec else file_url + ".tbi"
        return {"type": "gff", "name": name, "gff_gz_url": file_url, "tbi_url": tbi_url}

    raise ValueError(f"Unknown track type: {track_type!r}")


def build_track(track_spec_with_urls: dict, assembly_name: str) -> dict:
    """Build a JBrowse2 track configuration dict from a resolved track spec.

    Args:
        track_spec_with_urls: Resolved track spec where all file refs are URL strings.
            Must contain a ``type`` key matching one of the supported track types.
        assembly_name: JBrowse2 assembly name to associate with this track.

    Returns:
        JBrowse2-compatible track configuration dict.
    """
    track_type = track_spec_with_urls["type"]
    cls = TRACK_BUILDERS[track_type]
    # Strip the routing ``type`` key before handing to the builder; the
    # per-type resolved schemas use ``additionalProperties: false`` and do
    # not define a ``type`` property.
    spec_for_builder = {k: v for k, v in track_spec_with_urls.items() if k != "type"}
    return cls(spec_for_builder, assembly_name).build()
