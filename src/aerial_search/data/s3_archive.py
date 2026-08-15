"""Archive and restore WiSARD data to/from S3."""

from __future__ import annotations

import shutil
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

DEFAULT_BUCKET = "ssl-aerial-person-detection-data-eu-west1"
DEFAULT_REGION = "eu-west-1"


def ensure_bucket(bucket: str = DEFAULT_BUCKET, region: str = DEFAULT_REGION) -> None:
    """Create S3 bucket if it doesn't exist; idempotent."""
    s3 = boto3.client("s3", region_name=region)
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            if region == "us-east-1":
                s3.create_bucket(Bucket=bucket)
            else:
                s3.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )
        else:
            raise


def sync_up(local_dir: Path, bucket: str, prefix: str) -> int:
    """Upload files from local_dir to s3://bucket/prefix, skipping unchanged files."""
    local_dir = local_dir.resolve()
    s3 = boto3.client("s3", region_name=DEFAULT_REGION)

    # Build remote index by file size
    remote_files: dict[str, int] = {}
    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                remote_files[obj["Key"]] = obj["Size"]
    except ClientError:
        pass  # bucket might not exist yet or is empty

    uploaded = 0
    for local_path in sorted(local_dir.rglob("*")):
        if local_path.is_dir():
            continue
        rel_path = local_path.relative_to(local_dir)
        s3_key = f"{prefix.rstrip('/')}/{rel_path}".lstrip("/")
        local_size = local_path.stat().st_size
        if remote_files.get(s3_key) == local_size:
            continue  # skip unchanged
        s3.upload_file(str(local_path), bucket, s3_key)
        uploaded += 1
    return uploaded


def sync_down(bucket: str, prefix: str, local_dir: Path) -> int:
    """Download files from s3://bucket/prefix to local_dir, skipping unchanged files."""
    local_dir = local_dir.resolve()
    local_dir.mkdir(parents=True, exist_ok=True)
    s3 = boto3.client("s3", region_name=DEFAULT_REGION)

    downloaded = 0
    paginator = s3.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if "Contents" not in page:
                continue
            for obj in page["Contents"]:
                s3_key = obj["Key"]
                remote_size = obj["Size"]

                # Compute local path by stripping prefix
                if s3_key.startswith(prefix.rstrip("/") + "/"):
                    rel_path = s3_key[len(prefix.rstrip("/")) + 1 :]
                elif s3_key == prefix.rstrip("/"):
                    continue
                else:
                    continue
                local_path = local_dir / rel_path
                local_path.parent.mkdir(parents=True, exist_ok=True)

                # Skip if local file already matches remote
                if local_path.exists() and local_path.stat().st_size == remote_size:
                    continue

                s3.download_file(bucket, s3_key, str(local_path))
                downloaded += 1
    except ClientError:
        pass  # nothing to download
    return downloaded


def archive_to_s3(
    dataset: str,
    data_root: Path,
    *,
    bucket: str = DEFAULT_BUCKET,
    delete_local_raw: bool = False,
    delete_local_archive: bool = False,
) -> dict[str, int]:
    """Sync raw and processed data to S3; optionally delete local copies."""
    data_root = data_root.resolve()
    ensure_bucket(bucket, DEFAULT_REGION)

    uploaded: dict[str, int] = {}

    # Sync archives
    archive_dir = data_root / "archives"
    if archive_dir.exists():
        uploaded["archives"] = sync_up(archive_dir, bucket, "wisard/archives")

    # Sync raw data
    raw_dir = data_root / "raw" / dataset
    if raw_dir.exists():
        uploaded["raw"] = sync_up(raw_dir, bucket, f"wisard/raw/{dataset}")

    # Sync processed (manifests) — always keep locally
    processed_dir = data_root / "processed" / dataset
    if processed_dir.exists():
        uploaded["processed"] = sync_up(
            processed_dir, bucket, f"wisard/processed/{dataset}"
        )

    # Delete local copies if requested
    if delete_local_raw and raw_dir.exists():
        shutil.rmtree(raw_dir)
    if delete_local_archive and archive_dir.exists():
        archive_path = archive_dir / "WiSARD_Multi_Modal_Full.zip"
        if archive_path.exists():
            archive_path.unlink()

    return uploaded


def restore_from_s3(
    dataset: str, data_root: Path, *, bucket: str = DEFAULT_BUCKET
) -> int:
    """Download raw data from S3 to data_root/raw/{dataset}."""
    data_root = data_root.resolve()
    raw_dir = data_root / "raw" / dataset
    return sync_down(bucket, f"wisard/raw/{dataset}", raw_dir)
