nextflow.enable.dsl = 2

// ─── Process 1: select files ───────────────────────────────────────────────

process SELECT_FILES {

    tag { "${project_id}/${dataset_id}" }

    input:
    val project_id
    val dataset_id
    val assembly
    val tracks
    val fasta

    output:
    path 'inputs.json'

    script:
    def track_flags = tracks.collect { "--track '${it}'" }.join(' ')
    def fasta_flag  = fasta ? "--fasta '${fasta}'" : ''
    """
    cirro-jbrowse-config select \
        --non-interactive \
        --assembly '${assembly}' \
        --project-id '${project_id}' \
        --dataset-id '${dataset_id}' \
        ${track_flags} \
        ${fasta_flag} \
        --output inputs.json
    """
}

// ─── Process 2: generate + upload ──────────────────────────────────────────

process GENERATE_AND_UPLOAD {

    tag { upload_project_id }

    input:
    path inputs_json
    val  upload_project_id
    val  dataset_name
    val  description

    output:
    path 'upload_result.txt'

    script:
    """
    cirro-jbrowse-config upload \
        --inputs '${inputs_json}' \
        --output-dir '${params.output_dir}' \
        --project-id '${upload_project_id}' \
        --name '${dataset_name}' \
        --description '${description}' \
    | tee upload_result.txt
    """
}

// ─── Workflow ───────────────────────────────────────────────────────────────

workflow {
    inputs_ch = SELECT_FILES(
        params.project_id,
        params.dataset_id,
        params.assembly,
        params.tracks,
        params.fasta
    )

    GENERATE_AND_UPLOAD(
        inputs_ch,
        params.upload_project_id,
        params.dataset_name,
        params.description
    )
}
