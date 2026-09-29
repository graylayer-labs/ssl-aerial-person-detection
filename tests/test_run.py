import json
import subprocess
from pathlib import Path

import pytest

from aerial_search.run import ProvenanceError, start_run


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def commit(repo: Path, name: str) -> str:
    (repo / name).write_text(name)
    git(repo, "add", name)
    git(repo, "commit", "-m", name)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo whose HEAD equals a fake origin/main."""
    path = tmp_path / "repo"
    path.mkdir()
    git(path, "init", "-b", "main")
    (path / ".gitignore").write_text("outputs/\nignored.txt\n")
    git(path, "add", ".gitignore")
    git(path, "commit", "-m", "init")
    git(path, "update-ref", "refs/remotes/origin/main", "HEAD")
    return path


def run(repo: Path, **kwargs):
    defaults = dict(
        name="exp",
        config={"epochs": 2, "path": Path("x")},
        seed=7,
        device="cpu",
        argv=["aerial-search", "train-ssl"],
        repo=repo,
    )
    return start_run(**{**defaults, **kwargs})


def test_clean_head_equal_to_origin_main_is_allowed(repo: Path) -> None:
    out = run(repo)
    assert out == repo / "outputs" / "exp"
    data = json.loads((out / "run.json").read_text())
    assert data["commit"] == git(repo, "rev-parse", "HEAD")
    assert data["scratch"] is False
    assert data["seed"] == 7
    assert data["config"] == {"epochs": 2, "path": "x"}
    assert data["command"] == ["aerial-search", "train-ssl"]
    assert data["started_at"]
    assert data["machine"]["platform"]
    assert data["machine"]["device"] == "cpu"
    assert set(data["packages"]) == {"torch", "torchvision"}
    assert all(data["packages"].values())


def test_head_behind_origin_main_is_allowed(repo: Path) -> None:
    commit(repo, "a")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "checkout", "-q", "HEAD~1")
    assert run(repo).exists()


def test_dirty_tracked_file_refused(repo: Path) -> None:
    (repo / ".gitignore").write_text("changed\n")
    with pytest.raises(ProvenanceError, match="uncommitted"):
        run(repo)
    assert not (repo / "outputs").exists()


def test_untracked_file_refused_but_ignored_file_allowed(repo: Path) -> None:
    (repo / "ignored.txt").write_text("x")
    assert run(repo, name="a").exists()
    (repo / "new.py").write_text("x")
    with pytest.raises(ProvenanceError, match="uncommitted"):
        run(repo, name="b")


def test_commit_not_on_main_refused(repo: Path) -> None:
    commit(repo, "a")
    with pytest.raises(ProvenanceError, match="origin/main"):
        run(repo)


def test_missing_origin_main_refused(repo: Path) -> None:
    git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    with pytest.raises(ProvenanceError, match="git fetch"):
        run(repo)


def test_not_a_git_repo_refused(tmp_path: Path) -> None:
    with pytest.raises(ProvenanceError):
        run(tmp_path)


def test_git_missing_refused(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")
    with pytest.raises(ProvenanceError, match="git"):
        run(repo)


def test_scratch_allows_dirty_and_off_main(repo: Path) -> None:
    base = commit(repo, "a")
    (repo / "new.py").write_text("x")
    out = run(repo, scratch=True)
    assert out.name == "scratch-exp"
    data = json.loads((out / "run.json").read_text())
    assert data["scratch"] is True
    assert data["commit"] == base
    assert "new.py" in data["dirty"]
    assert data["commit_on_main"] is False


def test_scratch_records_clean_tree_as_empty_dirty(repo: Path) -> None:
    data = json.loads((run(repo, scratch=True) / "run.json").read_text())
    assert data["dirty"] == ""


def test_scratch_allowed_without_git(tmp_path: Path) -> None:
    out = run(tmp_path, scratch=True)
    data = json.loads((out / "run.json").read_text())
    assert data["scratch"] is True
    assert data["commit"] is None


def test_existing_run_is_never_overwritten(repo: Path) -> None:
    out = run(repo)
    (out / "keep.txt").write_text("x")
    with pytest.raises(ProvenanceError, match="exists"):
        run(repo)
    assert (out / "keep.txt").read_text() == "x"


def test_existing_scratch_run_is_never_overwritten(repo: Path) -> None:
    run(repo, scratch=True)
    with pytest.raises(ProvenanceError, match="exists"):
        run(repo, scratch=True)
