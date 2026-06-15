"""GTF track builder."""

from __future__ import annotations

from cirro_jbrowse_config.tracks.base import BaseTrack, _slugify


class GtfTrack(BaseTrack):
    """Builds a JBrowse2 FeatureTrack backed by GtfTabixAdapter."""

    _schema_name = "gtf"

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
            "type": "FeatureTrack",
            "trackId": _slugify(spec["name"]),
            "name": spec["name"],
            "assemblyNames": [self.assembly_name],
            "adapter": {
                "type": "GtfTabixAdapter",
                "gtfGzLocation": {"uri": spec["gtf_gz_url"], "locationType": "UriLocation"},
                "index": {
                    "indexType": "TBI",
                    "location": {"uri": spec["tbi_url"], "locationType": "UriLocation"},
                },
                "sequenceAdapter": seq_adapter,
            },
        }
