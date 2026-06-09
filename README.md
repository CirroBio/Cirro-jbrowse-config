# cirro-jbrowse-config

Generate an interactive [JBrowse2](https://jbrowse.org/jb2/) genome browser from files stored in [Cirro](https://cirro.bio) datasets. Point the tool at your BAM, BigWig, VCF, and GFF files; it produces a self-contained static site you can preview locally or publish back to Cirro.

## Installation

```bash
pip install cirro-jbrowse-config
```

Requires Python 3.11+.

## Try the demo (no Cirro account needed)

```bash
cirro-jbrowse-config demo
```

Opens a local JBrowse2 browser at <http://localhost:8080> pre-loaded with all four track types from the built-in [Volvox](https://github.com/GMOD/jbrowse-components/tree/main/test_data/volvox) example genome — BAM alignments, BigWig coverage, VCF variants, and GFF3 gene annotations. No authentication required. Tracks appear immediately without any additional clicks.

```bash
cirro-jbrowse-config demo --port 9090 --output-dir /tmp/demo-site
```

## Workflow

### 1. Select files

```bash
cirro-jbrowse-config select
```

A terminal UI walks you through choosing a Cirro project, dataset, assembly, and tracks. When finished it writes `inputs.json` — a file that records all your selections. The first time you run any command a browser window opens for Cirro login; credentials are cached for subsequent runs.

### 2. Preview locally

```bash
cirro-jbrowse-config serve
```

Resolves each file to a temporary presigned S3 URL (1-hour TTL), builds `config.json` + `index.html` in `jbrowse-site/`, and starts a local server at <http://localhost:8080>.

### 3. Publish to Cirro

```bash
cirro-jbrowse-config upload --project-id <id> --name "My Browser"
```

Uses render-service-worker URLs (resolved to fresh presigned URLs by the Cirro portal at view time), builds the static site, and uploads it as a new Cirro dataset. Anyone with project access can open it directly in the portal.

## CLI reference

| Command | Purpose |
|---------|---------|
| `demo` | Generate + serve built-in Volvox demo (no auth) |
| `select` | Interactively pick files from Cirro → `inputs.json` |
| `generate` | Build `config.json` + `index.html` from `inputs.json` |
| `serve` | Build + serve locally with presigned URLs |
| `upload` | Build + upload to Cirro as a new dataset |

Every command accepts `--help` for full option details.

### `select` options

| Flag | Default | Description |
|------|---------|-------------|
| `--output` / `-o` | `inputs.json` | Where to write the inputs file |
| `--non-interactive` | — | Skip the TUI; use explicit flags (for scripting/Nextflow) |
| `--assembly` / `-a` | — | Assembly name, e.g. `hg38` (required in non-interactive mode) |
| `--project-id` | — | Cirro project ID (non-interactive) |
| `--dataset-id` | — | Cirro dataset ID (non-interactive) |
| `--track` | — | `TYPE:NAME:FILE_PATH[:INDEX_PATH]` — repeatable |
| `--fasta` | — | `PROJECT_ID:DATASET_ID:FILE_PATH` |

### `serve` / `generate` options

| Flag | Default | Description |
|------|---------|-------------|
| `--inputs` / `-i` | `inputs.json` | Path to inputs file |
| `--output-dir` / `-o` | `jbrowse-site` | Output directory |
| `--port` / `-p` | `8080` | Port (`serve` and `demo` only) |

### `upload` options

| Flag | Default | Description |
|------|---------|-------------|
| `--inputs` / `-i` | `inputs.json` | Path to inputs file |
| `--output-dir` / `-o` | `jbrowse-site` | Output directory |
| `--project-id` | required | Cirro project to upload into |
| `--name` | required | Dataset name in Cirro |
| `--description` | — | Dataset description |

## Supported track types

| Type | Files required | Index |
|------|---------------|-------|
| `bam` | `.bam` | `.bai` (inferred if omitted) |
| `cram` | `.cram` + reference FASTA | `.crai` (inferred if omitted) |
| `bigwig` | `.bw` or `.bigwig` | none |
| `vcf` | `.vcf.gz` | `.tbi` (inferred if omitted) |
| `gff` | `.gff.gz` or `.gff3.gz` | `.tbi` (inferred if omitted) |

VCF and GFF files must be bgzip-compressed and tabix-indexed. BAM/CRAM files must be coordinate-sorted and indexed. See [Track Types](docs/track-types.md) for preparation commands.

## `inputs.json` format

`select` writes this file; `generate`, `serve`, and `upload` read it.

```json
{
  "assembly": {
    "name": "hg38",
    "sequence": { "project_id": "proj123", "dataset_id": "ds456", "file_path": "ref/hg38.fa.gz" },
    "fai":      { "project_id": "proj123", "dataset_id": "ds456", "file_path": "ref/hg38.fa.gz.fai" },
    "gzi":      { "project_id": "proj123", "dataset_id": "ds456", "file_path": "ref/hg38.fa.gz.gzi" }
  },
  "tracks": [
    {
      "type": "bam",
      "name": "Sample 1",
      "file": { "project_id": "proj123", "dataset_id": "ds789", "file_path": "alignments/sample1.bam" }
    },
    {
      "type": "bigwig",
      "name": "Coverage",
      "file": { "url": "https://example.org/coverage.bw" }
    }
  ]
}
```

File references are either a **Cirro ref** (`project_id` + `dataset_id` + `file_path`) or a **direct URL** (`url`). You can mix both in the same file.

## Non-interactive usage (Nextflow)

```bash
cirro-jbrowse-config select \
  --non-interactive \
  --assembly hg38 \
  --project-id proj123 \
  --dataset-id ds789 \
  --track bam:"Sample 1":alignments/sample1.bam \
  --track bigwig:Coverage:coverage/sample1.bw \
  --fasta proj123:ds456:ref/hg38.fa.gz

cirro-jbrowse-config upload \
  --project-id proj123 \
  --name "My JBrowse Browser"
```

A ready-to-use Nextflow DSL2 workflow is in [`workflow/`](workflow/). See [`workflow/README.md`](workflow/README.md) for usage.

## Development

```bash
git clone https://github.com/yourorg/cirro-jbrowse-config
cd cirro-jbrowse-config
pip install -e ".[dev]"
pytest
```

Docs are built with MkDocs:

```bash
mkdocs serve   # live preview at http://localhost:8000
mkdocs build   # static output in site/
```
