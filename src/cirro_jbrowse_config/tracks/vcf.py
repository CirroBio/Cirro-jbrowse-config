"""VCF track builder."""

from __future__ import annotations

from cirro_jbrowse_config.tracks.base import BaseTrack, _slugify


class VcfTrack(BaseTrack):
    """Builds a JBrowse2 VariantTrack backed by VcfTabixAdapter."""

    _schema_name = "vcf"

    def build(self) -> dict:
        spec = self.track_spec
        self.validate_spec(spec)
        return {
            "type": "VariantTrack",
            "trackId": _slugify(spec["name"]),
            "name": spec["name"],
            "assemblyNames": [self.assembly_name],
            "adapter": {
                "type": "VcfTabixAdapter",
                "vcfGzLocation": {"uri": spec["vcf_gz_url"], "locationType": "UriLocation"},
                "index": {
                    "indexType": "TBI",
                    "location": {"uri": spec["tbi_url"], "locationType": "UriLocation"},
                },
            },
        }
