import hashlib
import subprocess
from pathlib import Path

import pytest

from aerial_search.data import checksums
from aerial_search.data.checksums import (
    DataMismatchError,
    Differences,
    compare,
    ensure_directory,
    hash_tree,
    read_list,
    root_hash,
    write_list,
)


def make_tree(root: Path) -> None:
    (root / "a_0001").mkdir(parents=True)
    (root / "a_0001" / "x.jpg").write_bytes(b"xx")
    (root / "a_0001" / "x.txt").write_bytes(b"label")
    (root / "b_0002" / "sub").mkdir(parents=True)
    (root / "b_0002" / "sub" / "y.jpg").write_bytes(b"yyy")


def test_hash_tree_lists_every_file_with_size_and_sha256(tmp_path: Path) -> None:
    make_tree(tmp_path)
    entries = hash_tree(tmp_path)
    assert [e.path for e in entries] == [
        "a_0001/x.jpg",
        "a_0001/x.txt",
        "b_0002/sub/y.jpg",
    ]
    assert entries[0].size == 2
    assert entries[0].sha256 == hashlib.sha256(b"xx").hexdigest()


def test_list_round_trips_and_root_hash_is_stable(tmp_path: Path) -> None:
    make_tree(tmp_path / "data")
    entries = hash_tree(tmp_path / "data")
    write_list(entries, tmp_path / "one.gz")
    write_list(entries, tmp_path / "two.gz")
    assert read_list(tmp_path / "one.gz") == entries
    # the file is byte-identical across writes, so a re-run shows no diff
    assert (tmp_path / "one.gz").read_bytes() == (tmp_path / "two.gz").read_bytes()
    assert root_hash(entries) == root_hash(read_list(tmp_path / "one.gz"))


def test_root_hash_changes_with_any_file(tmp_path: Path) -> None:
    make_tree(tmp_path)
    before = root_hash(hash_tree(tmp_path))
    (tmp_path / "a_0001" / "x.txt").write_bytes(b"labeL")
    assert root_hash(hash_tree(tmp_path)) != before


def test_changed_file_detected(tmp_path: Path) -> None:
    make_tree(tmp_path)
    pinned = hash_tree(tmp_path)
    (tmp_path / "a_0001" / "x.jpg").write_bytes(b"XX")  # same size, new content
    diff = compare(hash_tree(tmp_path), pinned)
    assert diff == Differences(changed=["a_0001/x.jpg"], missing=[], added=[])


def test_missing_file_detected(tmp_path: Path) -> None:
    make_tree(tmp_path)
    pinned = hash_tree(tmp_path)
    (tmp_path / "b_0002" / "sub" / "y.jpg").unlink()
    diff = compare(hash_tree(tmp_path), pinned)
    assert diff.missing == ["b_0002/sub/y.jpg"]
    assert not diff.changed and not diff.added


def test_added_file_detected(tmp_path: Path) -> None:
    make_tree(tmp_path)
    pinned = hash_tree(tmp_path)
    (tmp_path / "a_0001" / "extra.jpg").write_bytes(b"e")
    diff = compare(hash_tree(tmp_path), pinned)
    assert diff.added == ["a_0001/extra.jpg"]
    assert not diff.changed and not diff.missing


def test_identical_trees_have_no_differences(tmp_path: Path) -> None:
    make_tree(tmp_path)
    pinned = hash_tree(tmp_path)
    assert not compare(hash_tree(tmp_path), pinned)


# --- fetch, with the aws command faked -------------------------------------


class FakeAws:
    """Stands in for subprocess.run: 'downloads' a prepared tree."""

    def __init__(self, source: Path, *, corrupt: bool = False) -> None:
        self.source = source
        self.corrupt = corrupt
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str], **kwargs: object):
        self.calls.append(command)
        destination = Path(command[command.index("--recursive") + 2])
        destination.mkdir(parents=True, exist_ok=True)
        for path in self.source.rglob("*"):
            if path.is_file():
                target = destination / path.relative_to(self.source)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        if self.corrupt:
            (destination / "x.jpg").write_bytes(b"bad")
        return subprocess.CompletedProcess(command, 0, "", "")


@pytest.fixture
def pinned_tree(tmp_path: Path):
    source = tmp_path / "remote" / "a_0001"
    source.mkdir(parents=True)
    (source / "x.jpg").write_bytes(b"xx")
    entries = [e for e in hash_tree(tmp_path / "remote")]
    return source, entries


def test_fetch_downloads_absent_directory_and_verifies(
    tmp_path: Path, pinned_tree
) -> None:
    source, entries = pinned_tree
    aws = FakeAws(source)
    data = tmp_path / "raw"
    data.mkdir()
    result = ensure_directory(
        "a_0001", data, expected=entries, runner=aws, profile="p", bucket_uri="s3://b/k"
    )
    assert result == data / "a_0001"
    assert (result / "x.jpg").read_bytes() == b"xx"
    (command,) = aws.calls
    assert command[:3] == ["aws", "s3", "cp"]
    assert "s3://b/k/a_0001" in command
    assert command[command.index("--profile") + 1] == "p"
    assert [p.name for p in data.iterdir()] == ["a_0001"]  # no temp left behind


def test_fetch_refuses_and_removes_a_directory_that_does_not_match(
    tmp_path: Path, pinned_tree
) -> None:
    source, entries = pinned_tree
    data = tmp_path / "raw"
    data.mkdir()
    with pytest.raises(DataMismatchError, match=r"a_0001/x\.jpg"):
        ensure_directory(
            "a_0001",
            data,
            expected=entries,
            runner=FakeAws(source, corrupt=True),
            profile="p",
            bucket_uri="s3://b/k",
        )
    assert list(data.iterdir()) == []


def test_fetch_does_not_run_when_present_and_matching(
    tmp_path: Path, pinned_tree
) -> None:
    source, entries = pinned_tree
    data = tmp_path / "raw"
    (data / "a_0001").mkdir(parents=True)
    (data / "a_0001" / "x.jpg").write_bytes(b"xx")
    aws = FakeAws(source)
    ensure_directory(
        "a_0001", data, expected=entries, runner=aws, profile="p", bucket_uri="s3://b/k"
    )
    assert aws.calls == []


def test_present_but_different_directory_is_refused_and_kept(
    tmp_path: Path, pinned_tree
) -> None:
    source, entries = pinned_tree
    data = tmp_path / "raw"
    (data / "a_0001").mkdir(parents=True)
    (data / "a_0001" / "x.jpg").write_bytes(b"zz")
    aws = FakeAws(source)
    with pytest.raises(DataMismatchError):
        ensure_directory(
            "a_0001",
            data,
            expected=entries,
            runner=aws,
            profile="p",
            bucket_uri="s3://b/k",
        )
    assert aws.calls == []
    assert (data / "a_0001" / "x.jpg").read_bytes() == b"zz"


def test_unknown_directory_name_is_refused(tmp_path: Path, pinned_tree) -> None:
    _, entries = pinned_tree
    for name in ("nope", "../a_0001", "a_0001/x.jpg"):
        with pytest.raises(ValueError):
            ensure_directory(
                name,
                tmp_path,
                expected=entries,
                runner=FakeAws(tmp_path),
                profile="p",
                bucket_uri="s3://b/k",
            )


def test_profile_comes_from_project_settings(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text('{"env": {"AWS_PROFILE": "ssl-aerial"}}')
    assert checksums.aws_profile(settings) == "ssl-aerial"
    settings.write_text("{}")
    with pytest.raises(RuntimeError, match="AWS_PROFILE"):
        checksums.aws_profile(settings)


def test_committed_list_is_readable_and_has_a_root_hash() -> None:
    entries = checksums.committed_list("wisard-full")
    assert len(entries) > 100_000
    assert len(checksums.committed_root_hash("wisard-full")) == 64
