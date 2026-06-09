"""GFF track builder."""

from __future__ import annotations

import re

from cirro_jbrowse_config.tracks.base import BaseTrack


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


class GffTrack(BaseTrack):
    """Builds a JBrowse2 FeatureTrack backed by Gff3TabixAdapter."""

    _schema_name = "gff"

    def build(self) -> dict:
        spec = self.track_spec
        self.validate_spec(spec)
        return {
            "type": "FeatureTrack",
            "trackId": _slugify(spec["name"]),
            "name": spec["name"],
            "assemblyNames": [self.assembly_name],
            "adapter": {
                "type": "Gff3TabixAdapter",
                "gffGzLocation": {"uri": spec["gff_gz_url"], "locationType": "UriLocation"},
                "index": {
                    "indexType": "TBI",
                    "location": {"uri": spec["tbi_url"], "locationType": "UriLocation"},
                },
            },
        }
