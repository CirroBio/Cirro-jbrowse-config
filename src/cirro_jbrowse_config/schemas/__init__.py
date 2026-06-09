"""Schema loading and validation utilities."""

import json
from pathlib import Path

import jsonschema

SCHEMAS_DIR = Path(__file__).parent


def load_schema(name: str) -> dict:
    """Load a JSON schema by name (e.g. 'inputs', 'config', 'tracks/bam')."""
    path = SCHEMAS_DIR / f"{name}.schema.json"
    with open(path) as f:
        return json.load(f)


def validate(instance: dict, schema_name: str) -> None:
    """Validate instance against a named schema. Raises jsonschema.ValidationError on failure."""
    schema = load_schema(schema_name)
    jsonschema.validate(instance, schema)
