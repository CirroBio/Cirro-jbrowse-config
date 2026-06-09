"""CRAM track builder."""

from __future__ import annotations

import re

from cirro_jbrowse_config.tracks.base import BaseTrack


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


class CramTrack(BaseTrack):
    """Builds a JBrowse2 AlignmentsTrack backed by CramAdapter."""

    _schema_name = "cram"

    def build(self) -> dict:
        spec = self.track_spec
        self.validate_spec(spec)
        sa = spec["sequence_adapter"]

        if "gzi_url" in sa:
            seq_adapter: dict = {
                "type": "BgzipFastaAdapter",
                "fastaLocation": {"uri": sa["fasta_url"], "locationType": "UriLocation"},
                "faiLocation": {"uri": sa["fai_url"], "locationType": "UriLocation"},
                "gziLocation": {"uri": sa["gzi_url"], "locationType": "UriLocation"},
            }
        else:
            seq_adapter = {
                "type": "IndexedFastaAdapter",
                "fastaLocation": {"uri": sa["fasta_url"], "locationType": "UriLocation"},
                "faiLocation": {"uri": sa["fai_url"], "locationType": "UriLocation"},
            }

        return {
            "type": "AlignmentsTrack",
            "trackId": _slugify(spec["name"]),
            "name": spec["name"],
            "assemblyNames": [self.assembly_name],
            "adapter": {
                "type": "CramAdapter",
                "cramLocation": {"uri": spec["cram_url"], "locationType": "UriLocation"},
                "craiLocation": {"uri": spec["crai_url"], "locationType": "UriLocation"},
                "sequenceAdapter": seq_adapter,
            },
        }
