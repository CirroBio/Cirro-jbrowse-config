"""JBrowse2 static site asset generator."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Callable

from jinja2 import Environment, PackageLoader

from cirro_jbrowse_config import schemas
from cirro_jbrowse_config.tracks import build_track, resolve_track_spec

logger = logging.getLogger(__name__)


def _uri_location(url: str) -> dict:
    return {"uri": url, "locationType": "UriLocation"}


def _build_assembly(assembly: dict) -> dict:
    """Build a JBrowse2 assembly dict from a URL-resolved assembly spec."""
    name = assembly["name"]
    slug = re.sub(r"[^a-z0-9_]", "_", name.lower())

    if "sequence_url" in assembly:
        seq_url: str = assembly["sequence_url"]
        lowered = seq_url.lower()

        if (lowered.endswith(".fa.gz") or lowered.endswith(".fasta.gz")) and "gzi_url" in assembly:
            adapter: dict = {
                "type": "BgzipFastaAdapter",
                "fastaLocation": _uri_location(seq_url),
                "faiLocation": _uri_location(assembly["fai_url"]),
                "gziLocation": _uri_location(assembly["gzi_url"]),
            }
        else:
            adapter = {
                "type": "IndexedFastaAdapter",
                "fastaLocation": _uri_location(seq_url),
                "faiLocation": _uri_location(assembly["fai_url"]),
            }

        sequence = {
            "type": "ReferenceSequenceTrack",
            "trackId": f"{slug}_reference_sequence",
            "adapter": adapter,
        }

    elif "chrom_sizes_url" in assembly:
        sequence = {
            "type": "ReferenceSequenceTrack",
            "trackId": f"{slug}_reference_sequence",
            "adapter": {
                "type": "ChromSizesAdapter",
                "chromSizesLocation": _uri_location(assembly["chrom_sizes_url"]),
            },
        }

    else:
        logger.warning(
            "Assembly %r has no sequence or chrom_sizes; falling back to a placeholder ChromSizesAdapter.",
            name,
        )
        sequence = {
            "type": "ReferenceSequenceTrack",
            "trackId": f"{slug}_reference_sequence",
            "adapter": {
                "type": "ChromSizesAdapter",
                "chromSizesLocation": _uri_location(""),
            },
        }

    return {"name": name, "sequence": sequence}


def _resolve_assembly(assembly_spec: dict, url_resolver: Callable[[dict], str]) -> dict:
    """Resolve FileRefs inside the assembly spec, returning URL-keyed dict."""
    resolved: dict = {"name": assembly_spec["name"]}

    if "sequence" in assembly_spec:
        resolved["sequence_url"] = url_resolver(assembly_spec["sequence"])
        if "fai" in assembly_spec:
            resolved["fai_url"] = url_resolver(assembly_spec["fai"])
        if "gzi" in assembly_spec:
            resolved["gzi_url"] = url_resolver(assembly_spec["gzi"])

    if "chrom_sizes" in assembly_spec:
        resolved["chrom_sizes_url"] = url_resolver(assembly_spec["chrom_sizes"])

    return resolved


_DISPLAY_TYPE: dict[str, str] = {
    "AlignmentsTrack": "LinearPileupDisplay",
    "QuantitativeTrack": "LinearWiggleDisplay",
    "VariantTrack": "LinearVariantDisplay",
    "FeatureTrack": "LinearBasicDisplay",
}



def generate_assets(
    inputs: dict,
    output_dir: str | Path,
    url_resolver: Callable[[dict], str],
) -> Path:
    """Generate JBrowse2 static site assets from validated inputs.

    Args:
        inputs: Validated inputs dict conforming to inputs.schema.json.
        output_dir: Directory where generated assets will be written.
        url_resolver: Callable that accepts a FileRef dict and returns a URL string.

    Returns:
        Path to the output directory containing the generated assets.
    """
    schemas.validate(inputs, "inputs")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    resolved_assembly = _resolve_assembly(inputs["assembly"], url_resolver)
    assembly_name: str = resolved_assembly["name"]
    jbrowse_assembly = _build_assembly(resolved_assembly)

    tracks = []
    for raw_track in inputs.get("tracks", []):
        resolved_spec = resolve_track_spec(raw_track, url_resolver)
        if resolved_spec["type"] in ("cram", "gtf") and "sequence_adapter" not in resolved_spec:
            track_type_label = resolved_spec["type"].upper()
            if "sequence_url" not in resolved_assembly or "fai_url" not in resolved_assembly:
                raise ValueError(
                    f"{track_type_label} tracks require a reference FASTA with an FAI index. "
                    "Provide an assembly with both 'sequence' and 'fai' fields."
                )
            sa: dict = {
                "fasta_url": resolved_assembly["sequence_url"],
                "fai_url": resolved_assembly["fai_url"],
            }
            if "gzi_url" in resolved_assembly:
                sa["gzi_url"] = resolved_assembly["gzi_url"]
            resolved_spec["sequence_adapter"] = sa
        track = build_track(resolved_spec, assembly_name)
        display_type = _DISPLAY_TYPE.get(track["type"])
        if display_type:
            track["displays"] = [{"type": display_type, "displayId": f"{track['trackId']}-{display_type}"}]
        tracks.append(track)

    config: dict = {
        "assemblies": [jbrowse_assembly],
        "tracks": tracks,
    }
    if "defaultLocation" in inputs:
        config["defaultLocation"] = inputs["defaultLocation"]

    schemas.validate(config, "config")

    config_path = output_path / "config.json"
    config_path.write_text(json.dumps(config, indent=2))

    env = Environment(
        loader=PackageLoader("cirro_jbrowse_config", "templates"),
        autoescape=False,
    )
    template = env.get_template("index.html.j2")
    html = template.render(config_json_path="config.json")
    (output_path / "index.html").write_text(html)

    from cirro_jbrowse_config.jbrowse_dist import get_bundle
    get_bundle(output_path)

    return output_path
