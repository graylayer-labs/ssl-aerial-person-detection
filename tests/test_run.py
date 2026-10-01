import json
import subprocess
from pathlib import Path

import pytest

from aerial_search import run as run_module
from aerial_search.run import ProvenanceError, finish_run, start_run


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


def run(
    repo: Path | None,
    name: str = "exp",
    scratch: bool = False,
    inputs: tuple[Path, ...] = (),
    checkpoint: Path | None = None,
    fold: str | None = None,
    view: str | None = None,
) -> Path:
    return start_run(
        name,
        {"epochs": 2, "path": Path("x")},
        7,
        device="cpu",
        scratch=scratch,
        argv=["aerial-search", "train-ssl"],
        repo=repo,
        inputs=inputs,
        checkpoint=checkpoint,
        fold=fold,
        view=view,
    )


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


def read(directory: Path) -> dict:
    return json.loads((directory / "run.json").read_text())


def test_run_is_marked_started_then_completed(repo: Path) -> None:
    out = run(repo)
    assert read(out)["status"] == "started"
    finish_run(out)
    data = read(out)
    assert data["status"] == "completed"
    assert data["finished_at"]


def test_run_is_marked_failed_with_error(repo: Path) -> None:
    out = run(repo)
    finish_run(out, ValueError("boom"))
    data = read(out)
    assert data["status"] == "failed"
    assert data["error"] == {"type": "ValueError", "message": "boom"}


def test_code_repository_is_used_not_current_directory(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-b", "main")
    git(other, "commit", "--allow-empty", "-m", "i")
    git(other, "update-ref", "refs/remotes/origin/main", "HEAD")
    (repo / "new.py").write_text("x")  # the code repo is dirty
    monkeypatch.setattr(run_module, "_code_location", lambda: repo)
    monkeypatch.chdir(other)
    with pytest.raises(ProvenanceError, match="uncommitted"):
        run(None)
    assert not (other / "outputs").exists()


def test_outputs_are_created_at_the_repository_root(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sub = repo / "src" / "pkg"
    sub.mkdir(parents=True)
    monkeypatch.setattr(run_module, "_code_location", lambda: sub)
    monkeypatch.chdir(tmp_path)
    assert run(None) == repo / "outputs" / "exp"


def test_code_outside_a_git_work_tree_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run_module, "_code_location", lambda: tmp_path)
    with pytest.raises(ProvenanceError, match="git work tree"):
        run(None)


def test_inputs_are_recorded_with_sha256(repo: Path, tmp_path: Path) -> None:
    f = tmp_path / "train.jsonl"
    f.write_text("abc")
    data = read(run(repo, inputs=(f,)))
    assert data["inputs"] == [
        {
            "path": str(f),
            "sha256": (
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
            ),
        }
    ]


def make_checkpoint(
    directory: Path, scratch: bool, status: str = "completed", **fields: str
) -> Path:
    directory.mkdir()
    (directory / "model.pt").write_text("weights")
    (directory / "run.json").write_text(
        json.dumps(
            {
                "run_name": "parent",
                "scratch": scratch,
                "commit": "abc",
                "status": status,
                **fields,
            }
        )
    )
    return directory / "model.pt"


def test_fold_and_view_are_recorded_at_the_top_level(repo: Path) -> None:
    data = read(run(repo, fold="220109_Baker", view="paired"))
    assert data["fold"] == "220109_Baker"
    assert data["view"] == "paired"


def test_checkpoint_from_the_same_fold_and_view_is_accepted(
    repo: Path, tmp_path: Path
) -> None:
    ckpt = make_checkpoint(
        tmp_path / "p", scratch=False, fold="220109_Baker", view="paired"
    )
    data = read(run(repo, checkpoint=ckpt, fold="220109_Baker", view="paired"))
    assert data["parent"]["fold"] == "220109_Baker"
    assert data["parent"]["mismatch"] == []


def test_checkpoint_from_another_fold_is_refused(repo: Path, tmp_path: Path) -> None:
    # Pretraining in the MtErie fold saw Baker; a detector scored on Baker
    # must not start from it.
    ckpt = make_checkpoint(
        tmp_path / "p", scratch=False, fold="210417_MtErie", view="paired"
    )
    with pytest.raises(ProvenanceError, match="210417_MtErie.*220109_Baker"):
        run(repo, checkpoint=ckpt, fold="220109_Baker", view="paired")
    assert not (repo / "outputs").exists()


def test_checkpoint_from_another_view_is_refused(repo: Path, tmp_path: Path) -> None:
    ckpt = make_checkpoint(
        tmp_path / "p", scratch=False, fold="220109_Baker", view="rgb"
    )
    with pytest.raises(ProvenanceError, match="view.*rgb.*paired"):
        run(repo, checkpoint=ckpt, fold="220109_Baker", view="paired")


def test_checkpoint_whose_run_has_no_fold_is_refused(
    repo: Path, tmp_path: Path
) -> None:
    ckpt = make_checkpoint(tmp_path / "p", scratch=False)
    with pytest.raises(ProvenanceError, match="fold null.*220109_Baker"):
        run(repo, checkpoint=ckpt, fold="220109_Baker", view="paired")


def test_scratch_run_may_cross_folds_and_records_it(repo: Path, tmp_path: Path) -> None:
    ckpt = make_checkpoint(
        tmp_path / "p", scratch=False, fold="210417_MtErie", view="paired"
    )
    data = read(
        run(repo, scratch=True, checkpoint=ckpt, fold="220109_Baker", view="paired")
    )
    assert data["parent"]["fold"] == "210417_MtErie"
    assert len(data["parent"]["mismatch"]) == 1
    assert "210417_MtErie" in data["parent"]["mismatch"][0]


def test_normal_run_accepts_checkpoint_from_normal_run(
    repo: Path, tmp_path: Path
) -> None:
    ckpt = make_checkpoint(tmp_path / "p", scratch=False)
    data = read(run(repo, checkpoint=ckpt))
    assert data["parent"]["run_name"] == "parent"
    assert data["parent"]["commit"] == "abc"
    assert data["inputs"][0]["path"] == str(ckpt)
    assert len(data["inputs"][0]["sha256"]) == 64


def test_normal_run_refuses_scratch_checkpoint(repo: Path, tmp_path: Path) -> None:
    ckpt = make_checkpoint(tmp_path / "p", scratch=True)
    with pytest.raises(ProvenanceError, match="scratch"):
        run(repo, checkpoint=ckpt)


@pytest.mark.parametrize("status", ["started", "failed"])
def test_normal_run_refuses_checkpoint_from_unfinished_run(
    repo: Path, tmp_path: Path, status: str
) -> None:
    # A run that crashed may have saved a checkpoint partway through.
    ckpt = make_checkpoint(tmp_path / "p", scratch=False, status=status)
    with pytest.raises(ProvenanceError, match=status):
        run(repo, checkpoint=ckpt)
    assert not (repo / "outputs").exists()


def test_normal_run_refuses_checkpoint_without_run_json(
    repo: Path, tmp_path: Path
) -> None:
    ckpt = make_checkpoint(tmp_path / "p", scratch=False)
    (ckpt.parent / "run.json").unlink()
    with pytest.raises(ProvenanceError, match=r"run\.json"):
        run(repo, checkpoint=ckpt)
    assert not (repo / "outputs").exists()


def test_scratch_run_accepts_any_checkpoint(repo: Path, tmp_path: Path) -> None:
    ckpt = make_checkpoint(tmp_path / "p", scratch=True)
    assert run(repo, scratch=True, checkpoint=ckpt).exists()
    bare = tmp_path / "bare.pt"
    bare.write_text("w")
    assert run(repo, name="b", scratch=True, checkpoint=bare).exists()


def test_skip_worktree_and_assume_unchanged_refused(repo: Path) -> None:
    (repo / "t.py").write_text("1")
    git(repo, "add", "t.py")
    git(repo, "commit", "-m", "t")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    git(repo, "update-index", "--skip-worktree", "t.py")
    (repo / "t.py").write_text("2")
    with pytest.raises(ProvenanceError, match=r"t\.py"):
        run(repo)
    git(repo, "update-index", "--no-skip-worktree", "t.py")
    git(repo, "update-index", "--assume-unchanged", "t.py")
    with pytest.raises(ProvenanceError, match=r"t\.py"):
        run(repo)


def test_scratch_without_origin_main_keeps_commit_and_dirty(repo: Path) -> None:
    git(repo, "update-ref", "-d", "refs/remotes/origin/main")
    (repo / "new.py").write_text("x")
    data = read(run(repo, scratch=True))
    assert data["commit"] == git(repo, "rev-parse", "HEAD")
    assert "new.py" in data["dirty"]
    assert data["commit_on_main"] is None


def test_code_in_an_ignored_directory_refused(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ignored = repo / "outputs" / "site-packages"
    ignored.mkdir(parents=True)
    monkeypatch.setattr(run_module, "_code_location", lambda: ignored)
    with pytest.raises(ProvenanceError, match="ignored"):
        run(None)
