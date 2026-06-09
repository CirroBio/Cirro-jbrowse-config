# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`cirro-jbrowse-config` is a Python package that generates JBrowse2 static genome browser configurations from files stored in [Cirro](https://cirro.bio) datasets. The tool supports BAM, CRAM, BigWig, VCF, and GFF track types and publishes results back to Cirro.

## Layout

```
src/cirro_jbrowse_config/   # installable package (src layout)
  schemas/                  # JSON schemas + load_schema/validate utilities
    tracks/                 # per-track-type resolved-spec schemas
  tracks/                   # track builder classes (BaseTrack + one per type)
  cirro/                    # Cirro SDK integration (FileSelector, DatasetUploader, URL resolvers)
  cli/                      # Click CLI (demo, select, generate, serve, upload)
  generator.py              # generate_assets() entry point
  templates/                # Jinja2 templates (index.html.j2)
  examples/volvox/          # bundled Volvox demo inputs.json (no Cirro auth needed)
tests/                      # pytest test suite (187 tests)
docs/                       # MkDocs source
workflow/                   # Nextflow DSL2 workflow (main.nf, nextflow.config)
```

## Build / Install

```bash
# Editable install with dev dependencies
pip install -e ".[dev]"
```

## Test Commands

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=cirro_jbrowse_config --cov-report=term-missing

# Run a specific test file
pytest tests/test_schemas.py -v
```

## Docs Commands

```bash
# Serve docs locally
mkdocs serve

# Build static docs
mkdocs build
```

## Schema Details

- `inputs.schema.json` — validates `inputs.json` written by `cirro-jbrowse-config select` and consumed by `generate`. FileRefs are either `CirroFileRef` (`project_id`, `dataset_id`, `file_path`) or `UrlFileRef` (`url`).
- `config.schema.json` — validates the JBrowse2 `config.json` output.
- `schemas/tracks/*.schema.json` — validate fully-resolved track specs (all URLs, no FileRefs) before track builders consume them.

## Cirro Integration Patterns

- Use the Cirro Python SDK client for authentication (standard credential flow).
- `CirroFileRef` objects are resolved to presigned S3 URLs at generation time via `url_resolver` callable passed to `generate_assets()`.
- The `upload` command creates a new Cirro dataset whose type renders as an embedded JBrowse2 browser.
