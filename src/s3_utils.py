import os
import sys
import types

# Work around broken pyOpenSSL/cryptography on some servers by preventing
# botocore -> urllib3 from importing and injecting pyOpenSSL. Standard library
# ssl provides SNI and is sufficient for AWS endpoints.
try:
    if "urllib3.contrib.pyopenssl" not in sys.modules:
        _pyopenssl_stub = types.ModuleType("urllib3.contrib.pyopenssl")

        def _noop():
            return None

        _pyopenssl_stub.inject_into_urllib3 = _noop
        _pyopenssl_stub.extract_from_urllib3 = _noop
        sys.modules["urllib3.contrib.pyopenssl"] = _pyopenssl_stub
except Exception:
    # Best-effort: if anything goes wrong, fall back to default behavior.
    pass

import boto3
from botocore.client import Config
from urllib.parse import urljoin

AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

_session = boto3.session.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=AWS_REGION,
)

s3 = _session.resource("s3")
client = _session.client("s3", config=Config(signature_version="s3v4"))
_bucket = s3.Bucket(S3_BUCKET_NAME) if S3_BUCKET_NAME else None


def ensure_bucket():
    if not S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME is not set in environment")
    return _bucket


def upload_bytes(key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    bucket = ensure_bucket()
    bucket.put_object(Key=key, Body=data, ContentType=content_type)
    return f"s3://{S3_BUCKET_NAME}/{key}"


def upload_file(local_path: str, key: str, content_type: str | None = None) -> str:
    bucket = ensure_bucket()
    extra_args = {"ContentType": content_type} if content_type else None
    if extra_args:
        bucket.upload_file(local_path, key, ExtraArgs=extra_args)
    else:
        bucket.upload_file(local_path, key)
    return f"s3://{S3_BUCKET_NAME}/{key}"


def list_objects(prefix: str) -> list[dict]:
    ensure_bucket()
    paginator = client.get_paginator("list_objects_v2")
    results = []
    for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix):
        for obj in page.get("Contents", []) :
            results.append(obj)
    return results


def generate_s3_http_url(key: str) -> str:
    # Assumes object is publicly accessible OR presigned URLs used elsewhere.
    return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{key}"


def presigned_url(key: str, expires_in: int = 3600) -> str:
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )
