"""Storage abstraction for document uploads.

Local filesystem storage remains the default for development and Docker. Production
can use Cloudflare R2 through its S3-compatible API without changing the document
model or ingestion pipeline.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import tempfile
import uuid

from app.core.config import Settings

R2_PREFIX = "r2://"


def company_upload_dir(settings: Settings, company_id: str) -> Path:
    path = Path(settings.upload_dir) / company_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _r2_client(settings: Settings):
    if settings.storage_backend != "r2":
        raise RuntimeError("R2 client requested while STORAGE_BACKEND is not 'r2'")
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _r2_key(company_id: str, safe_name: str) -> str:
    return f"companies/{company_id}/{uuid.uuid4().hex[:12]}_{safe_name}"


def store_upload(settings: Settings, company_id: str, safe_name: str, data: bytes) -> str:
    """Store an upload and return a stable storage reference."""
    if settings.storage_backend == "r2":
        key = _r2_key(company_id, safe_name)
        client = _r2_client(settings)
        client.put_object(
            Bucket=settings.r2_bucket,
            Key=key,
            Body=data,
        )
        return f"{R2_PREFIX}{settings.r2_bucket}/{key}"

    base = company_upload_dir(settings, company_id)
    path = base / f"{uuid.uuid4().hex[:12]}_{safe_name}"
    path.write_bytes(data)
    return str(path)


def _parse_r2_reference(storage_path: str) -> tuple[str, str]:
    if not storage_path.startswith(R2_PREFIX):
        raise ValueError("Not an R2 storage reference")
    reference = storage_path[len(R2_PREFIX):]
    bucket, separator, key = reference.partition("/")
    if not separator or not bucket or not key:
        raise ValueError("Invalid R2 storage reference")
    return bucket, key


@contextmanager
def materialize_upload(settings: Settings, storage_path: str):
    """Yield a local path suitable for document parsers, cleaning up R2 temp files."""
    if not storage_path.startswith(R2_PREFIX):
        yield Path(storage_path)
        return

    bucket, key = _parse_r2_reference(storage_path)
    client = _r2_client(settings)
    suffix = Path(key).suffix
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="dd-r2-", suffix=suffix, delete=False) as tmp:
            temp_path = Path(tmp.name)
            response = client.get_object(Bucket=bucket, Key=key)
            while True:
                chunk = response["Body"].read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
        yield temp_path
    finally:
        response_body = locals().get("response", {}).get("Body")
        if response_body is not None:
            response_body.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def read_stored_file(settings: Settings, storage_path: str) -> bytes:
    """Read a stored upload into memory for authenticated file responses."""
    if storage_path.startswith(R2_PREFIX):
        bucket, key = _parse_r2_reference(storage_path)
        response = _r2_client(settings).get_object(Bucket=bucket, Key=key)
        try:
            return response["Body"].read()
        finally:
            response["Body"].close()
    return Path(storage_path).read_bytes()


def delete_stored_file(settings: Settings, storage_path: str | None) -> None:
    if not storage_path:
        return
    try:
        if storage_path.startswith(R2_PREFIX):
            bucket, key = _parse_r2_reference(storage_path)
            _r2_client(settings).delete_object(Bucket=bucket, Key=key)
        else:
            Path(storage_path).unlink(missing_ok=True)
    except (OSError, ValueError) as exc:
        # Keep document deletion idempotent even if the physical object is already gone.
        # R2 client exceptions are intentionally allowed to propagate so operators can
        # see a real storage outage rather than silently losing a delete operation.
        if storage_path.startswith(R2_PREFIX):
            raise
        _ = exc
