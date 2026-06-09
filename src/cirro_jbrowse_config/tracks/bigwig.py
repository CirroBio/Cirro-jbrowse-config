"""BigWig track builder."""

from __future__ import annotations

import re

from cirro_jbrowse_config.tracks.base import BaseTrack


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name.lower())


class BigWigTrack(BaseTrack):
    """Builds a JBrowse2 QuantitativeTrack backed by BigWigAdapter."""

    _schema_name = "bigwig"

    def build(self) -> dict:
        spec = self.track_spec
        self.validate_spec(spec)
        return {
            "type": "QuantitativeTrack",
            "trackId": _slugify(spec["name"]),
            "name": spec["name"],
            "assemblyNames": [self.assembly_name],
            "adapter": {
                "type": "BigWigAdapter",
                "bigWigLocation": {"uri": spec["bigwig_url"], "locationType": "UriLocation"},
            },
        }
