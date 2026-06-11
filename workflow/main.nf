nextflow.enable.dsl = 2

process GENERATE_SITE {

    publishDir params.outdir, mode: 'copy', overwrite: true

    input:
    path inputs_json
    path source_dir

    output:
    path '*'

    script:
    """
    uv pip install --system "./${source_dir}"
    cirro-jbrowse-config generate \
        --inputs '${inputs_json}' \
        --output-dir .
    """
}

workflow {
    if (!params.outdir) {
        error "params.outdir must be set"
    }

    inputs_ch = channel.fromPath(params.inputs)
    source_ch = channel.value(file(workflow.projectDir).parent)

    GENERATE_SITE(inputs_ch, source_ch)
}
