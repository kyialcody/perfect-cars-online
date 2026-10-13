"""S3 / MinIO helpers (reused by the seed script and, later, admin uploads)."""
from __future__ import annotations

import boto3

from app.core.config import get_settings


def get_s3_client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name="us-east-1",
    )


def ensure_bucket(client, bucket: str) -> None:
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if bucket not in existing:
        client.create_bucket(Bucket=bucket)


def put_object(client, bucket: str, key: str, body: bytes, content_type: str) -> None:
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)


def public_url(key: str | None) -> str | None:
    """Browser-reachable URL for an S3 object key (None-safe)."""
    if not key:
        return None
    if key.startswith(("http://", "https://")):
        return key
    s = get_settings()
    return f"{s.s3_public_endpoint}/{s.s3_bucket}/{key}"
