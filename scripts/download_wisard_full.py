#!/usr/bin/env python3
"""One-time download and S3 upload of the full WiSARD dataset.

Usage:
    python scripts/download_wisard_full.py

Prerequisites:
    - AWS credentials configured (~/.aws/credentials or env vars)
    - Python environment with uv: uv run python scripts/download_wisard_full.py
"""

from __future__ import annotations

import os
from pathlib import Path

import boto3
import gdown

# Dataset configuration
GOOGLE_DRIVE_FILE_ID = "1PKjGCqUszHH1nMbXUBTwPSDqRabAt_ht"
S3_BUCKET = "ssl-aerial-person-detection-data-eu-west1"
S3_REGION = "eu-west-1"
LOCAL_ARCHIVE = Path("data/archives/WiSARD_Multi_Modal_Full.zip")


def download_from_gdrive() -> None:
    """Download full WiSARD dataset from Google Drive."""
    print(f"Downloading WiSARD full dataset from Google Drive...")
    print(f"  File ID: {GOOGLE_DRIVE_FILE_ID}")
    print(f"  Destination: {LOCAL_ARCHIVE}")

    LOCAL_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)

    gdown.download(
        id=GOOGLE_DRIVE_FILE_ID,
        output=str(LOCAL_ARCHIVE),
        resume=True,
        quiet=False,
    )
    print(f"✓ Download complete: {LOCAL_ARCHIVE}")
    print(f"  File size: {LOCAL_ARCHIVE.stat().st_size / 1e9:.2f} GB")


def upload_to_s3() -> None:
    """Upload downloaded archive to S3."""
    if not LOCAL_ARCHIVE.exists():
        raise FileNotFoundError(f"Archive not found: {LOCAL_ARCHIVE}")

    print(f"\nUploading to S3...")
    print(f"  Bucket: {S3_BUCKET}")
    print(f"  Region: {S3_REGION}")

    s3 = boto3.client("s3", region_name=S3_REGION)

    # Ensure bucket exists
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
        print(f"✓ Bucket exists: {S3_BUCKET}")
    except Exception:
        print(f"Creating bucket: {S3_BUCKET}")
        s3.create_bucket(
            Bucket=S3_BUCKET,
            CreateBucketConfiguration={"LocationConstraint": S3_REGION},
        )

    s3_key = "wisard/archives/WiSARD_Multi_Modal_Full.zip"
    file_size = LOCAL_ARCHIVE.stat().st_size

    print(f"Uploading {file_size / 1e9:.2f} GB to s3://{S3_BUCKET}/{s3_key}")
    s3.upload_file(str(LOCAL_ARCHIVE), S3_BUCKET, s3_key)
    print(f"✓ Upload complete")


def main() -> None:
    """Download and upload WiSARD full dataset."""
    print("=" * 70)
    print("WiSARD Full Dataset: Download & S3 Upload")
    print("=" * 70)

    try:
        download_from_gdrive()
        upload_to_s3()

        print("\n" + "=" * 70)
        print("✓ Success! Dataset is now available in S3.")
        print("\nNext steps:")
        print("  1. Extract locally: uv run aerial-search fetch wisard-full")
        print("  2. Prepare manifests: uv run aerial-search prepare data/raw/wisard-full")
        print("  3. Explore data: jupyter notebook reports/01_data_exploration.ipynb")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()
