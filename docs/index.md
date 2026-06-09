# cirro-jbrowse-config

`cirro-jbrowse-config` is a command-line tool that lets you build an interactive [JBrowse2](https://jbrowse.org/jb2/) genome browser directly from files stored in your [Cirro](https://cirro.bio) datasets. You select your reference assembly and tracks, and the tool produces a complete, self-contained browser — no manual configuration required.

## Choose your workflow

**Local preview** — use `serve` when you want to explore your data in a browser on your own machine. The tool generates a browser configuration and starts a local web server. URLs expire after one hour, so this mode is meant for active review sessions, not sharing.

**Publish to Cirro** — use `upload` when you want to share a genome browser with collaborators or embed it in the Cirro data portal. The tool generates a browser configuration that resolves file access through Cirro at view time, then uploads it as a new dataset. Anyone with access to your Cirro project can open the browser directly in the portal.

## Try the demo (no account needed)

```bash
pip install cirro-jbrowse-config
cirro-jbrowse-config demo
```

Opens a local JBrowse2 browser at [http://localhost:8080](http://localhost:8080) loaded with built-in Volvox example data — BAM alignments, BigWig coverage, VCF variants, and GFF3 gene annotations. No Cirro account required.

## Quick start with your own data

```bash
# Install
pip install cirro-jbrowse-config

# Interactively select your assembly and tracks from Cirro
cirro-jbrowse-config select

# Preview locally
cirro-jbrowse-config serve

# Or publish to Cirro
cirro-jbrowse-config upload --project-id <project-id> --name "My JBrowse View"
```

The first time you run any command, a browser window will open for you to log in to Cirro. Your credentials are cached for subsequent runs.

See [Getting Started](getting-started.md) for a full walkthrough, [Track Types](track-types.md) for supported file formats, and [Cirro Integration](cirro-integration.md) for details on authentication and how files are accessed.
