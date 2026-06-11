nextflow.enable.dsl = 2

process GENERATE_SITE {

    publishDir params.outdir, mode: 'copy', overwrite: true

    input:
    path inputs_json

    output:
    path '*'

    script:
    """
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

    GENERATE_SITE(inputs_ch)
}
