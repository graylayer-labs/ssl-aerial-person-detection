from pathlib import Path

from moto import mock_aws

from aerial_search.data.s3_archive import (
    archive_to_s3,
    ensure_bucket,
    restore_from_s3,
    sync_down,
    sync_up,
)


@mock_aws
def test_ensure_bucket_creates() -> None:
    ensure_bucket("test-bucket", "eu-west-1")
    # If this doesn't raise, the bucket exists


@mock_aws
def test_ensure_bucket_idempotent() -> None:
    ensure_bucket("test-bucket", "eu-west-1")
    ensure_bucket("test-bucket", "eu-west-1")  # Should not raise


@mock_aws
def test_sync_up_and_down(tmp_path: Path) -> None:
    bucket = "test-bucket"
    ensure_bucket(bucket, "eu-west-1")

    # Create local files
    local_dir = tmp_path / "local"
    local_dir.mkdir()
    (local_dir / "file1.txt").write_text("content1")
    (local_dir / "file2.txt").write_text("content2")

    # Upload
    uploaded = sync_up(local_dir, bucket, "prefix/")
    assert uploaded == 2

    # Re-upload should skip unchanged
    uploaded2 = sync_up(local_dir, bucket, "prefix/")
    assert uploaded2 == 0

    # Download to different location
    download_dir = tmp_path / "downloaded"
    downloaded = sync_down(bucket, "prefix/", download_dir)
    assert downloaded == 2
    assert (download_dir / "file1.txt").read_text() == "content1"
    assert (download_dir / "file2.txt").read_text() == "content2"


@mock_aws
def test_archive_to_s3_with_deletion(tmp_path: Path) -> None:
    bucket = "test-bucket"
    ensure_bucket(bucket, "eu-west-1")

    # Create data structure
    data_root = tmp_path / "data"
    (data_root / "archives").mkdir(parents=True)
    (
        data_root / "archives" / "WiSARD_Multi_Modal_Full.zip"
    ).write_text("archive_content")
    (data_root / "raw" / "wisard-full").mkdir(parents=True)
    (data_root / "raw" / "wisard-full" / "image.jpeg").write_text("image_data")
    (data_root / "processed" / "wisard-full").mkdir(parents=True)
    (data_root / "processed" / "wisard-full" / "train.jsonl").write_text("{}")

    # Archive with deletion
    uploaded = archive_to_s3(
        "wisard-full",
        data_root,
        bucket=bucket,
        delete_local_raw=True,
        delete_local_archive=True,
    )

    # Check uploads happened
    assert "archives" in uploaded or "raw" in uploaded or "processed" in uploaded

    # Check deletions
    assert not (data_root / "raw" / "wisard-full" / "image.jpeg").exists()
    assert not (data_root / "archives" / "WiSARD_Multi_Modal_Full.zip").exists()

    # Processed should still exist
    assert (data_root / "processed" / "wisard-full" / "train.jsonl").exists()


@mock_aws
def test_restore_from_s3(tmp_path: Path) -> None:
    bucket = "test-bucket"
    ensure_bucket(bucket, "eu-west-1")

    # First, upload some data
    upload_dir = tmp_path / "upload"
    upload_dir.mkdir()
    (upload_dir / "test.txt").write_text("test_content")
    sync_up(upload_dir, bucket, "wisard/raw/wisard-full/")

    # Then restore to a new location
    restore_dir = tmp_path / "restore"
    downloaded = restore_from_s3("wisard-full", restore_dir, bucket=bucket)

    # Check file was downloaded
    assert downloaded > 0
    assert (
        (restore_dir / "raw" / "wisard-full" / "test.txt").read_text()
        == "test_content"
    )
