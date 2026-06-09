"""Tests for the built-in Volvox demo."""

from __future__ import annotations

import json
from importlib.resources import files
from unittest import mock

import pytest
from click.testing import CliRunner

from cirro_jbrowse_config import schemas
from cirro_jbrowse_config.cli.main import main
from cirro_jbrowse_config.generator import generate_assets


@pytest.fixture()
def volvox_inputs() -> dict:
    raw = files("cirro_jbrowse_config.examples.volvox").joinpath("inputs.json").read_text()
    return json.loads(raw)


def test_demo_inputs_validates_against_schema(volvox_inputs):
    schemas.validate(volvox_inputs, "inputs")


def test_generate_assets_with_demo_inputs(volvox_inputs, tmp_path):
    out = generate_assets(volvox_inputs, tmp_path, lambda ref: ref["url"])

    config_path = out / "config.json"
    index_path = out / "index.html"
    assert config_path.exists()
    assert index_path.exists()

    config = json.loads(config_path.read_text())
    schemas.validate(config, "config")

    assert config["assemblies"][0]["name"] == "volvox"
    track_types = {t["adapter"]["type"] for t in config["tracks"]}
    assert track_types == {"BamAdapter", "BigWigAdapter", "VcfTabixAdapter", "Gff3TabixAdapter"}


def test_demo_cli_generates_and_starts_server(tmp_path):
    runner = CliRunner()
    with mock.patch("http.server.HTTPServer") as mock_server_cls:
        instance = mock_server_cls.return_value
        instance.serve_forever.side_effect = KeyboardInterrupt

        result = runner.invoke(main, ["demo", "--output-dir", str(tmp_path), "--port", "9999"])

    assert result.exit_code == 0
    assert "http://localhost:9999" in result.output
    mock_server_cls.assert_called_once_with(("", 9999), mock.ANY)
    instance.serve_forever.assert_called_once()
