"""BAM track builder."""

from __future__ import annotations

from cirro_jbrowse_config.tracks.base import BaseTrack, _slugify


class BamTrack(BaseTrack):
    """Builds a JBrowse2 AlignmentsTrack backed by BamAdapter."""

    _schema_name = "bam"

    def build(self) -> dict:
        spec = self.track_spec
        self.validate_spec(spec)
        return {
            "type": "AlignmentsTrack",
            "trackId": _slugify(spec["name"]),
            "name": spec["name"],
            "assemblyNames": [self.assembly_name],
            "adapter": {
                "type": "BamAdapter",
                "bamLocation": {"uri": spec["bam_url"], "locationType": "UriLocation"},
                "index": {
                    "indexType": "BAI",
                    "location": {"uri": spec["bai_url"], "locationType": "UriLocation"},
                },
            },
        }
