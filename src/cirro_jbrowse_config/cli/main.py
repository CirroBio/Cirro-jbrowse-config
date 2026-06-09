"""Command-line interface for cirro-jbrowse-config."""

from __future__ import annotations

import functools
import http.server
import json
from importlib.resources import files
from pathlib import Path
from typing import Optional

import click

from cirro_jbrowse_config.cirro import make_presigned_resolver, make_render_service_resolver
from cirro_jbrowse_config.cirro.selector import FileSelector
from cirro_jbrowse_config.cirro.uploader import DatasetUploader
from cirro_jbrowse_config.generator import generate_assets


def _get_portal():
    """Return an authenticated DataPortal, printing a friendly message if auth is needed."""
    from cirro import DataPortal
    return DataPortal()


def _parse_track(value: str) -> dict:
    """Parse a --track option string into a track dict.

    Accepted formats:
        TYPE:NAME:FILE_PATH
        TYPE:NAME:FILE_PATH:INDEX_PATH
    """
    parts = value.split(":", 3)
    if len(parts) < 3:
        raise click.BadParameter(
            f"Expected TYPE:NAME:FILE_PATH[:INDEX_PATH], got: {value!r}",
            param_hint="--track",
        )
    track: dict = {
        "track_type": parts[0],
        "name": parts[1],
        "file_path": parts[2],
    }
    if len(parts) == 4:
        track["index_path"] = parts[3]
    return track


def _parse_fasta(value: str) -> dict:
    """Parse --fasta option string PROJECT_ID:DATASET_ID:FILE_PATH."""
    parts = value.split(":", 2)
    if len(parts) != 3:
        raise click.BadParameter(
            f"Expected PROJECT_ID:DATASET_ID:FILE_PATH, got: {value!r}",
            param_hint="--fasta",
        )
    return {"project_id": parts[0], "dataset_id": parts[1], "file_path": parts[2]}


@click.group()
@click.version_option(package_name="cirro-jbrowse-config")
def main() -> None:
    """Generate JBrowse2 static genome browser configurations from Cirro datasets."""


@main.command()
@click.option("--output", "-o", default="inputs.json", show_default=True, help="Path for the generated inputs.json.")
@click.option("--non-interactive", is_flag=True, default=False, help="Build inputs.json from explicit parameters without a TUI.")
@click.option("--assembly", "-a", default=None, help="Assembly name (required in non-interactive mode).")
@click.option("--project-id", default=None, help="Cirro project ID (non-interactive).")
@click.option("--dataset-id", default=None, help="Cirro dataset ID (non-interactive).")
@click.option("--track", "tracks", multiple=True, help="Track spec: TYPE:NAME:FILE_PATH[:INDEX_PATH] (repeatable, non-interactive).")
@click.option("--fasta", default=None, help="Reference FASTA: PROJECT_ID:DATASET_ID:FILE_PATH (non-interactive).")
def select(
    output: str,
    non_interactive: bool,
    assembly: Optional[str],
    project_id: Optional[str],
    dataset_id: Optional[str],
    tracks: tuple,
    fasta: Optional[str],
) -> None:
    """Interactively select files from Cirro and write inputs.json."""
    try:
        portal = _get_portal()
        selector = FileSelector(portal)

        if non_interactive:
            if not assembly:
                raise click.UsageError("--assembly is required in non-interactive mode.")
            if not project_id:
                raise click.UsageError("--project-id is required in non-interactive mode.")
            if not dataset_id:
                raise click.UsageError("--dataset-id is required in non-interactive mode.")

            parsed_tracks = []
            for t in tracks:
                parsed = _parse_track(t)
                parsed["project_id"] = project_id
                parsed["dataset_id"] = dataset_id
                parsed_tracks.append(parsed)

            assembly_fasta = _parse_fasta(fasta) if fasta else None

            selector.run_non_interactive(
                output_path=output,
                assembly_name=assembly,
                tracks=parsed_tracks,
                assembly_fasta=assembly_fasta,
            )
        else:
            selector.run_interactive(output_path=output)

        click.echo(f"Wrote inputs to {output}")
    except (click.UsageError, click.BadParameter):
        raise
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("--output-dir", "-o", default="demo-site", show_default=True, help="Output directory for the demo site.")
@click.option("--port", "-p", default=8080, show_default=True, help="Port to listen on.")
def demo(output_dir: str, port: int) -> None:
    """Generate and serve a demo JBrowse2 site using built-in Volvox example data.

    No Cirro account or authentication required.
    """
    try:
        data = json.loads(
            files("cirro_jbrowse_config.examples.volvox").joinpath("inputs.json").read_text()
        )
        out = generate_assets(data, output_dir, lambda ref: ref["url"])
        serve_dir = str(Path(out).resolve())
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=serve_dir)
        server = http.server.HTTPServer(("", port), handler)
        click.echo(f"Demo site ready. Open http://localhost:{port} in your browser.")
        click.echo("Press Ctrl+C to stop.")
        server.serve_forever()
    except KeyboardInterrupt:
        click.echo("\nStopped.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("--inputs", "-i", default="inputs.json", show_default=True, help="Path to inputs.json.")
@click.option("--output-dir", "-o", default="jbrowse-site", show_default=True, help="Output directory for static site assets.")
def generate(inputs: str, output_dir: str) -> None:
    """Generate JBrowse2 static site assets from inputs.json."""
    try:
        inputs_path = Path(inputs)
        if not inputs_path.exists():
            raise FileNotFoundError(f"inputs file not found: {inputs}")
        data = json.loads(inputs_path.read_text())

        portal = _get_portal()
        url_resolver = make_presigned_resolver(portal)
        out = generate_assets(data, output_dir, url_resolver)
        click.echo(f"Generated site at {out}")
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("--inputs", "-i", default="inputs.json", show_default=True, help="Path to inputs.json.")
@click.option("--output-dir", "-o", default="jbrowse-site", show_default=True, help="Output directory for static site assets.")
@click.option("--port", "-p", default=8080, show_default=True, help="Port to listen on.")
def serve(inputs: str, output_dir: str, port: int) -> None:
    """Generate and serve the JBrowse2 static site locally for preview."""
    try:
        inputs_path = Path(inputs)
        if not inputs_path.exists():
            raise FileNotFoundError(f"inputs file not found: {inputs}")
        data = json.loads(inputs_path.read_text())

        portal = _get_portal()
        url_resolver = make_presigned_resolver(portal)
        out = generate_assets(data, output_dir, url_resolver)

        serve_dir = str(Path(out).resolve())
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=serve_dir)
        server = http.server.HTTPServer(("", port), handler)
        click.echo(f"Serving at http://localhost:{port}")
        click.echo("Press Ctrl+C to stop.")
        server.serve_forever()
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except KeyboardInterrupt:
        click.echo("\nStopped.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@main.command()
@click.option("--inputs", "-i", default="inputs.json", show_default=True, help="Path to inputs.json.")
@click.option("--output-dir", "-o", default="jbrowse-site", show_default=True, help="Output directory for static site assets.")
@click.option("--project-id", required=True, help="Cirro project ID to upload into.")
@click.option("--name", required=True, help="Dataset name.")
@click.option("--description", default="", show_default=True, help="Dataset description.")
def upload(inputs: str, output_dir: str, project_id: str, name: str, description: str) -> None:
    """Generate with render-service URLs and upload as a new Cirro dataset."""
    try:
        inputs_path = Path(inputs)
        if not inputs_path.exists():
            raise FileNotFoundError(f"inputs file not found: {inputs}")
        data = json.loads(inputs_path.read_text())

        portal = _get_portal()
        url_resolver = make_render_service_resolver(portal)
        out = generate_assets(data, output_dir, url_resolver)

        dataset_id = DatasetUploader(portal).upload(out, project_id, name, description)
        click.echo(f"Uploaded dataset: {dataset_id}")
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
