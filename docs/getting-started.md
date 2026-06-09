# Getting Started

## Installation

```bash
pip install cirro-jbrowse-config
```

Python 3.9 or later is required. You also need an active Cirro account with access to at least one project that contains genomic data files.

---

## Quick demo (no Cirro account needed)

If you want to see the tool working before connecting it to your own data, run:

```bash
cirro-jbrowse-config demo
```

This generates a JBrowse2 browser loaded with built-in [Volvox](https://github.com/GMOD/jbrowse-components/tree/main/test_data/volvox) example data (a small synthetic genome used in JBrowse2's own test suite) and starts a local server. Open [http://localhost:8080](http://localhost:8080) to see all four supported track types — BAM alignments, BigWig coverage, VCF variants, and GFF3 gene annotations.

Press `Ctrl+C` to stop the server.

```bash
# Optional flags
cirro-jbrowse-config demo --port 9090 --output-dir /tmp/volvox-demo
```

---

## Authentication

The first time you run any `cirro-jbrowse-config` command, a browser window will open and ask you to log in to Cirro. After you complete the login, your credentials are saved locally and reused for all subsequent commands. You will not be prompted again unless your session expires.

---

## Interactive workflow

This is the recommended approach when you are working at the command line and want to browse your Cirro projects to select files.

### Step 1 — Select your assembly and tracks

```bash
cirro-jbrowse-config select
```

A text interface opens in your terminal. You will be guided through:

1. Choosing a Cirro project
2. Choosing a dataset that contains your reference FASTA (`.fa.gz` with `.fai` and `.gzi` index files)
3. Naming the assembly (for example, `hg38` or `mm10`)
4. Adding one or more tracks — for each track you select the type (bam, vcf, bigwig, etc.), give it a display name, and choose the file from a dataset

When you finish, the tool writes an `inputs.json` file in the current directory. This file records all your selections and is used by every subsequent command.

You can specify a different output path with `--output`:

```bash
cirro-jbrowse-config select --output my-config/inputs.json
```

### Step 2 — Preview locally or publish to Cirro

**To preview in your browser:**

```bash
cirro-jbrowse-config serve
```

This builds a JBrowse2 site in `jbrowse-site/` and starts a local web server. Open [http://localhost:8080](http://localhost:8080) in your browser to view the genome browser. Press `Ctrl+C` to stop the server.

The URLs embedded in the configuration expire after one hour. If the browser stops loading tracks, re-run `serve` to generate fresh URLs.

**To publish to Cirro:**

```bash
cirro-jbrowse-config upload \
  --project-id <project-id> \
  --name "Sample 1 alignments — hg38"
```

This builds the JBrowse2 site and uploads it to Cirro as a new dataset. The dataset will appear in the portal and render as an interactive genome browser for anyone with access to the project. You can optionally add a description:

```bash
cirro-jbrowse-config upload \
  --project-id <project-id> \
  --name "Sample 1 alignments — hg38" \
  --description "RNA-seq alignments for sample 1, mapped to hg38"
```

---

## Non-interactive workflow

Use the `--non-interactive` flag when you want to run `select` from a script, a Nextflow pipeline, or any environment where you cannot interact with a terminal.

You must supply all required values as command-line flags. The `--track` flag can be repeated to add multiple tracks.

```bash
cirro-jbrowse-config select \
  --non-interactive \
  --assembly hg38 \
  --fasta PROJECT_ID:DATASET_ID:ref/hg38.fa.gz \
  --project-id PROJECT_ID \
  --dataset-id DATASET_ID \
  --track bam:"Sample 1":alignments/sample1.bam \
  --track bigwig:"Coverage":coverage/sample1.bw \
  --track vcf:"Variants":variants/sample1.vcf.gz
```

**Flag reference for `--track`:**

```
--track TYPE:NAME:FILE_PATH
--track TYPE:NAME:FILE_PATH:INDEX_PATH
```

- `TYPE` — one of `bam`, `cram`, `bigwig`, `vcf`, `gff` (see [Track Types](track-types.md))
- `NAME` — display name shown in the genome browser
- `FILE_PATH` — path to the file within the dataset specified by `--dataset-id`
- `INDEX_PATH` — optional; if omitted, the index is inferred by appending `.bai` or `.tbi` to the file path

**Flag reference for `--fasta`:**

```
--fasta PROJECT_ID:DATASET_ID:FILE_PATH
```

The FASTA file must be bgzipped (`.fa.gz`) and accompanied by `.fai` and `.gzi` index files in the same dataset directory. Index paths are inferred automatically.

**Full non-interactive example with generate and upload:**

```bash
# Build inputs.json
cirro-jbrowse-config select \
  --non-interactive \
  --assembly hg38 \
  --fasta proj123:ds456:ref/hg38.fa.gz \
  --project-id proj123 \
  --dataset-id ds789 \
  --track bam:"Sample 1":alignments/sample1.bam \
  --track vcf:"Variants":variants/calls.vcf.gz

# Build the static site
cirro-jbrowse-config generate

# Publish to Cirro
cirro-jbrowse-config upload \
  --project-id proj123 \
  --name "Sample 1 — hg38 browser"
```

---

## Command reference

Each command accepts `--help` for a full list of options.

### `demo`

Generates and serves the built-in Volvox example site. No Cirro auth required.

| Flag | Description | Default |
|------|-------------|---------|
| `--output-dir` / `-o` | Directory to write the demo site into | `demo-site` |
| `--port` / `-p` | Port for the local server | `8080` |

### `select`

Produces `inputs.json`. Run interactively or with `--non-interactive`.

| Flag | Description | Default |
|------|-------------|---------|
| `--output` / `-o` | Path to write `inputs.json` | `inputs.json` |
| `--non-interactive` | Disable the terminal UI; require explicit flags | — |
| `--assembly` / `-a` | Assembly name (required in non-interactive mode) | — |
| `--project-id` | Cirro project ID (non-interactive) | — |
| `--dataset-id` | Cirro dataset ID (non-interactive) | — |
| `--track` | `TYPE:NAME:FILE_PATH[:INDEX_PATH]` — repeatable | — |
| `--fasta` | `PROJECT_ID:DATASET_ID:FILE_PATH` | — |

### `generate`

Builds the JBrowse2 site without starting a server.

| Flag | Description | Default |
|------|-------------|---------|
| `--inputs` / `-i` | Path to `inputs.json` | `inputs.json` |
| `--output-dir` / `-o` | Directory to write the site into | `jbrowse-site` |

### `serve`

Builds the site and starts a local HTTP server.

| Flag | Description | Default |
|------|-------------|---------|
| `--inputs` / `-i` | Path to `inputs.json` | `inputs.json` |
| `--output-dir` / `-o` | Directory to write the site into | `jbrowse-site` |
| `--port` / `-p` | Port for the local server | `8080` |

### `upload`

Builds the site and publishes it to Cirro.

| Flag | Description | Default |
|------|-------------|---------|
| `--inputs` / `-i` | Path to `inputs.json` | `inputs.json` |
| `--output-dir` / `-o` | Directory to write the site into | `jbrowse-site` |
| `--project-id` | Cirro project to upload into | required |
| `--name` | Dataset name in Cirro | required |
| `--description` | Dataset description | — |
