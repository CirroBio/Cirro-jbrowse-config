from __future__ import annotations

import boto3
from cirro import DataPortal

RENDER_SERVICE_WORKER_PREFIX = "https://cirrobio.github.io/render-service-worker/s3/"
PUBWEB_S3_PREFIX = "s3://pubweb-references/"


def _presign_s3_uri(s3_uri: str) -> str:
    bucket, key = s3_uri.removeprefix("s3://").split("/", 1)
    return boto3.client("s3").generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600,
    )


def _render_service_url(s3_uri: str) -> str:
    return RENDER_SERVICE_WORKER_PREFIX + s3_uri.removeprefix("s3://")


def make_presigned_resolver(portal: DataPortal):
    """Returns a url_resolver that generates S3 presigned URLs for CirroFileRefs."""
    def resolve(file_ref: dict) -> str:
        if "url" in file_ref:
            url = file_ref["url"]
            if url.startswith(PUBWEB_S3_PREFIX):
                return _render_service_url(url)
            return url
        project = portal.get_project(file_ref["project_id"])
        dataset = project.get_dataset(file_ref["dataset_id"])
        f = dataset.get_file(file_ref["file_path"])
        return _presign_s3_uri(f.absolute_path)
    return resolve


def make_render_service_resolver(portal: DataPortal):
    """Returns a url_resolver that maps S3 URIs to render-service-worker URLs for Cirro portal viewing."""
    def resolve(file_ref: dict) -> str:
        if "url" in file_ref:
            url = file_ref["url"]
            if url.startswith(PUBWEB_S3_PREFIX):
                return _render_service_url(url)
            return url
        project = portal.get_project(file_ref["project_id"])
        dataset = project.get_dataset(file_ref["dataset_id"])
        f = dataset.get_file(file_ref["file_path"])
        return _render_service_url(f.absolute_path)
    return resolve
