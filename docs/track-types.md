# Supported Track Types

`cirro-jbrowse-config` supports five track types. Each type maps to a specific JBrowse2 track and requires particular file formats.

| Type | Display in JBrowse2 | Required files | Index handling |
|------|---------------------|----------------|----------------|
| `bam` | Alignments track | `.bam` + `.bai` | `.bai` inferred if not specified |
| `cram` | Alignments track | `.cram` + `.crai` + reference FASTA | `.crai` inferred if not specified |
| `bigwig` | Quantitative track | `.bw` or `.bigwig` | No index required |
| `vcf` | Variant track | `.vcf.gz` + `.tbi` | `.tbi` inferred if not specified |
| `gff` | Feature track | `.gff.gz` or `.gff3.gz` + `.tbi` | `.tbi` inferred if not specified |

---

## Index inference

For `bam`, `vcf`, and `gff` tracks, if you do not specify an index path the tool appends the expected extension to the main file path and looks for it in the same dataset:

- `sample1.bam` → index assumed at `sample1.bam.bai`
- `calls.vcf.gz` → index assumed at `calls.vcf.gz.tbi`
- `annotation.gff.gz` → index assumed at `annotation.gff.gz.tbi`

You can always specify the index explicitly as the fourth component of a `--track` flag:

```
--track bam:"Sample 1":alignments/sample1.bam:alignments/sample1.bam.bai
```

---

## Preparing files before use

### BAM files

BAM files must be **coordinate-sorted and indexed**. If your BAM is not yet sorted and indexed:

```bash
samtools sort -o sample1.sorted.bam sample1.bam
samtools index sample1.sorted.bam
```

Upload both `sample1.sorted.bam` and `sample1.sorted.bam.bai` to Cirro.

### CRAM files

CRAM files must be sorted and indexed, just like BAM files:

```bash
samtools index sample1.cram
```

CRAM tracks also require a reference FASTA. The reference is specified separately as the `--fasta` argument during `select`, and must be bgzipped with `.fai` and `.gzi` index files present in the same dataset (see [Getting Started](getting-started.md)).

### VCF files

VCF files must be **bgzipped and tabix-indexed**. Plain `.vcf` and gzip-compressed `.vcf.gz` files produced by tools like `gzip` will not work — you must use `bgzip`:

```bash
bgzip calls.vcf                  # produces calls.vcf.gz
tabix -p vcf calls.vcf.gz        # produces calls.vcf.gz.tbi
```

Upload both `calls.vcf.gz` and `calls.vcf.gz.tbi` to Cirro.

### GFF files

GFF files (both `.gff` and `.gff3`) must also be **bgzipped and tabix-indexed**:

```bash
bgzip annotation.gff3              # produces annotation.gff3.gz
tabix -p gff annotation.gff3.gz   # produces annotation.gff3.gz.tbi
```

Upload both files to Cirro. Either the `.gff.gz` or `.gff3.gz` extension is accepted.

### BigWig files

BigWig files (`.bw` or `.bigwig`) are already in a binary indexed format and require no further preparation.

---

## Reference FASTA

All assemblies require a bgzipped, indexed reference FASTA with three files present in the same dataset:

| File | Description |
|------|-------------|
| `reference.fa.gz` | The bgzipped FASTA |
| `reference.fa.gz.fai` | FASTA index (produced by `samtools faidx`) |
| `reference.fa.gz.gzi` | bgzip block index (produced alongside `bgzip`) |

To prepare a reference:

```bash
bgzip reference.fa                        # produces reference.fa.gz + reference.fa.gz.gzi
samtools faidx reference.fa.gz            # produces reference.fa.gz.fai
```

Upload all three files to a Cirro dataset before running `select`.
