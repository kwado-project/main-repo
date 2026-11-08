"""Private object storage on Cloudflare R2 (S3-compatible API).

Files are never public. Clients download via short-lived presigned URLs and
only after a server-side ownership check. In development a local-disk backend
is used instead (`STORAGE_PROVIDER=local`).
"""
from pathlib import Path

from django.conf import settings

_r2 = None


def _client():
    global _r2
    if _r2 is None:
        import boto3
        from botocore.config import Config

        _r2 = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )
    return _r2


def _local_path(key: str) -> Path:
    root = Path(settings.LOCAL_STORAGE_ROOT).resolve()
    p = (root / key).resolve()
    if root not in p.parents:
        raise ValueError("invalid storage key")
    return p


def put_object(key: str, data: bytes, content_type: str) -> None:
    if settings.STORAGE_PROVIDER == "r2":
        _client().put_object(
            Bucket=settings.R2_BUCKET, Key=key, Body=data, ContentType=content_type
        )
        return
    p = _local_path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def get_object(key: str) -> bytes:
    if settings.STORAGE_PROVIDER == "r2":
        return _client().get_object(Bucket=settings.R2_BUCKET, Key=key)["Body"].read()
    return _local_path(key).read_bytes()


def delete_object(key: str) -> None:
    if settings.STORAGE_PROVIDER == "r2":
        _client().delete_object(Bucket=settings.R2_BUCKET, Key=key)
        return
    p = _local_path(key)
    if p.exists():
        p.unlink()


def presigned_download_url(key: str, filename: str) -> str | None:
    """Return a short-lived URL, or None in local mode (served by the API)."""
    if settings.STORAGE_PROVIDER == "r2":
        return _client().generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.R2_BUCKET,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=settings.R2_PRESIGN_SECONDS,
        )
    return None
