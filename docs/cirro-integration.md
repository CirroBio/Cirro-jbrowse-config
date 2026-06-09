# Cirro Integration

## Authentication

`cirro-jbrowse-config` authenticates using the Cirro Python SDK. The first time you run any command, a browser window opens and takes you to the Cirro login page. After you log in, your credentials are cached locally and reused automatically on all subsequent runs.

If your session expires (for example, after an extended period of inactivity), the browser login window will open again the next time you run a command.

No manual configuration is needed — authentication is handled entirely by the SDK's standard login flow.

---

## How file access works: two modes

The tool can access files from Cirro in two ways depending on whether you are previewing locally or publishing to Cirro.

### Local mode (`serve`)

When you run `cirro-jbrowse-config serve`, each Cirro file reference is resolved to a **temporary presigned S3 URL**. These URLs grant direct read access to the file for approximately one hour without requiring authentication.

- The `config.json` written into your output directory contains these presigned URLs.
- The local web server serves the site from that directory.
- After about one hour, the URLs expire and tracks will stop loading. Re-run `serve` to generate a fresh set of URLs.

This mode is intended for active review sessions on your own machine, not for sharing or long-term access.

### Upload mode (`upload`)

When you run `cirro-jbrowse-config upload`, each Cirro file reference is embedded in the configuration as a **render-service-worker URL** — a special URL format that the Cirro data portal resolves to a fresh presigned S3 URL at the moment each viewer opens the browser.

This means:

- The published browser never contains expired URLs.
- Access is controlled by Cirro — only users with access to the project can view the data.
- You do not need to re-publish when URLs would otherwise expire.

The dataset appears in your Cirro project and renders as an interactive JBrowse2 genome browser directly inside the Cirro UI.

---

## The `inputs.json` file

The `select` command produces an `inputs.json` file that records your assembly and track selections. This file is the input to `generate`, `serve`, and `upload`.

Each file entry in `inputs.json` is a file reference in one of two forms:

**Cirro file reference** — points to a file in a specific Cirro project and dataset:

```json
{
  "project_id": "proj123",
  "dataset_id": "ds456",
  "file_path": "alignments/sample1.bam"
}
```

At generation time, this reference is resolved to a URL appropriate for the chosen mode (presigned URL for local use, render-service-worker URL for upload).

**Direct URL** — used as-is, with no Cirro resolution:

```json
{
  "url": "https://example.org/coverage.bw"
}
```

You can mix both types within the same `inputs.json`. Direct URLs are useful for publicly accessible reference data or files hosted outside Cirro.

### Example `inputs.json`

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

---

## Re-publishing an updated browser

The `upload` command always creates a **new** Cirro dataset. To update a previously published browser — for example, after adding new tracks — re-run `upload` with the same `--name` or a new one. The previous dataset remains in Cirro and is not overwritten.

```bash
# Add a new track to inputs.json by re-running select, then re-upload
cirro-jbrowse-config select
cirro-jbrowse-config upload \
  --project-id proj123 \
  --name "Sample 1 — hg38 browser (updated)"
```

---

## Nextflow usage

The `workflow/` directory in this repository contains a Nextflow workflow that wraps the non-interactive `select` and `upload` commands. This lets you generate and publish a JBrowse2 browser as a step in a larger pipeline.

Refer to the files in `workflow/` for configuration details. The non-interactive command syntax used in that workflow follows the same flags described in [Getting Started](getting-started.md#non-interactive-workflow).
