"""Base track class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from cirro_jbrowse_config import schemas


class BaseTrack(ABC):
    """Abstract base for all JBrowse2 track builders."""

    #: Subclasses set this to the schema name suffix, e.g. "bam", "cram".
    _schema_name: str = ""

    def __init__(self, track_spec: dict, assembly_name: str) -> None:
        self.track_spec = track_spec
        self.assembly_name = assembly_name

    @classmethod
    def validate_spec(cls, spec: dict) -> None:
        """Validate a resolved spec against the per-type schema."""
        schemas.validate(spec, f"tracks/{cls._schema_name}")

    @abstractmethod
    def build(self) -> dict:
        """Return a JBrowse2-compatible track configuration dict."""
        raise NotImplementedError
