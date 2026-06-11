"""Isolated test for presigned URL generation against s3://pubweb-references/."""

import urllib.request
import boto3
import botocore

S3_URI = "s3://pubweb-references/igenomes/Escherichia_coli_K_12_DH10B/Ensembl/EB1/Sequence/WholeGenomeFasta/genome.fa"
BUCKET = "pubweb-references"
KEY = "igenomes/Escherichia_coli_K_12_DH10B/Ensembl/EB1/Sequence/WholeGenomeFasta/genome.fa"


def check_credentials():
    session = boto3.session.Session()
    creds = session.get_credentials()
    if creds is None:
        print("ERROR: No AWS credentials found")
        return False
    resolved = creds.get_frozen_credentials()
    print(f"Credentials: access_key={resolved.access_key[:8]}... method={creds.method}")
    print(f"Region: {session.region_name or '(not set)'}")
    return True


def check_bucket_region():
    s3 = boto3.client("s3", region_name="us-east-1")
    try:
        loc = s3.get_bucket_location(Bucket=BUCKET)
        region = loc["LocationConstraint"] or "us-east-1"
        print(f"Bucket region: {region}")
        return region
    except botocore.exceptions.ClientError as e:
        print(f"get_bucket_location error: {e}")
        return None


def try_presign(region=None):
    kwargs = {}
    if region:
        kwargs["region_name"] = region
    s3 = boto3.client("s3", **kwargs)
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": KEY},
            ExpiresIn=3600,
        )
        print(f"Generated URL: {url[:120]}...")
        return url
    except Exception as e:
        print(f"generate_presigned_url error: {e}")
        return None


def try_fetch(url):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Range", "bytes=0-63")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"HTTP {resp.status}: fetched first {len(resp.read())} bytes — URL is valid")
            return True
    except urllib.error.HTTPError as e:
        body = e.read(500).decode(errors="replace")
        print(f"HTTP {e.code} {e.reason}: {body}")
        return False
    except Exception as e:
        print(f"Fetch error: {e}")
        return False


if __name__ == "__main__":
    print(f"Target: {S3_URI}\n")

    print("--- Credentials ---")
    if not check_credentials():
        raise SystemExit(1)

    print("\n--- Bucket region ---")
    region = check_bucket_region()

    print("\n--- Presign (default region) ---")
    url = try_presign()
    if url:
        print("\n--- Fetch test (default region) ---")
        ok = try_fetch(url)

    if region and not ok:
        print(f"\n--- Presign (bucket region: {region}) ---")
        url2 = try_presign(region=region)
        if url2:
            print("\n--- Fetch test (bucket region) ---")
            try_fetch(url2)
