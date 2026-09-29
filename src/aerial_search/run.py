"""Run provenance: tie every run to a commit on main, or mark it as scratch.

Call `start_run` first in every experiment entry point, and `finish_run` when
the experiment returns or raises. A normal run starts only from a clean
working tree whose HEAD is on the local `origin/main`. A scratch run starts
from any state and is labelled so its numbers cannot be quoted. The check
fails closed: if git cannot answer, a normal run is refused.

The repository inspected is the one that holds this module (the running
code), never the current directory. `outputs/` is created at its root.
A non-editable install, whose code is not inside a git work tree, cannot make
a normal run.

A normal run is quotable only if its `run.json` says `"status": "completed"`.
`start_run` writes `"started"`; `finish_run` sets `"completed"` or `"failed"`.
A run left at `"started"` crashed or is still running: do not quote it.

Inputs (`inputs`, `checkpoint`) are recorded with their SHA-256. A normal run
that starts from a checkpoint needs a `run.json` beside it with `scratch`
false; its name and commit are recorded as `parent`.

Runs are never overwritten. If `outputs/<run-name>/` already exists,
`start_run` raises `ProvenanceError`; choose another run name.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

MAIN_REF = "refs/remotes/origin/main"
SCRATCH_PREFIX = "scratch-"
PACKAGES = ("torch", "torchvision")


class ProvenanceError(RuntimeError):
    """A normal run was refused, or the run directory cannot be created."""


class GitError(ProvenanceError):
    """Git is missing or cannot answer (for example, not a work tree)."""


def _code_location() -> Path:
    """The directory of the running code. Tests replace this."""
    return Path(__file__).resolve().parent


def _git(where: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # A hook's GIT_DIR must not redirect us to another repository.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        return subprocess.run(
            ["git", "-C", str(where), *args],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except OSError as error:
        raise GitError(f"cannot run git: {error}") from error


def _git_ok(where: Path, *args: str) -> str:
    result = _git(where, *args)
    if result.returncode != 0:
        raise GitError(
            f"`git {' '.join(args)}` failed: {result.stderr.strip() or 'no output'}"
        )
    return result.stdout


def _repo_root(start: Path) -> Path:
    result = _git(start, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        raise GitError(
            f"{start} is not inside a git work tree (a non-editable install?), "
            f"so the running code cannot be tied to a commit: {result.stderr.strip()}"
        )
    return Path(result.stdout.strip()).resolve()


def _inspect(root: Path, start: Path) -> dict[str, Any]:
    """Commit, dirty output, hidden changes and on-main status of `root`."""
    if _git(root, "check-ignore", "-q", str(start)).returncode == 0:
        raise GitError(
            f"{start} is ignored by git, so it is not code the commit describes "
            "(a virtualenv install?)."
        )
    commit = _git_ok(root, "rev-parse", "HEAD").strip()
    # Untracked files are listed; ignored files are not.
    dirty = _git_ok(root, "status", "--porcelain")
    # Tracked files hidden from status: assume-unchanged (lowercase tag) or
    # skip-worktree ("S").
    hidden = [
        line[2:]
        for line in _git_ok(root, "ls-files", "-v").splitlines()
        if line[:1].islower() or line[:1] == "S"
    ]
    main_error = None
    on_main = None
    if _git(root, "rev-parse", "--verify", "--quiet", MAIN_REF).returncode != 0:
        main_error = (
            "origin/main is not known in this repository, so it cannot be "
            "checked whether HEAD is on main. A `git fetch` may be needed."
        )
    else:
        ancestor = _git(root, "merge-base", "--is-ancestor", "HEAD", MAIN_REF)
        if ancestor.returncode in (0, 1):
            on_main = ancestor.returncode == 0
        else:
            main_error = f"cannot compare HEAD with origin/main: {ancestor.stderr}"
    return {
        "commit": commit,
        "dirty": dirty,
        "hidden_changes": hidden,
        "commit_on_main": on_main,
        "main_error": main_error,
    }


def _package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in PACKAGES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
    except OSError as error:
        raise ProvenanceError(f"cannot read input {path}: {error}") from error
    return digest.hexdigest()


def _parent(checkpoint: Path, scratch: bool) -> dict[str, Any] | None:
    """The run that produced `checkpoint`. A normal run requires a normal one."""
    record_path = checkpoint.parent / "run.json"
    try:
        record = json.loads(record_path.read_text())
        parent = {
            "run_name": record.get("run_name"),
            "commit": record.get("commit"),
            "path": str(record_path),
        }
        is_scratch = record.get("scratch") is not False
    except (OSError, ValueError):
        if scratch:
            return None
        raise ProvenanceError(
            f"{record_path} is missing or unreadable, so checkpoint {checkpoint} "
            "cannot be traced to a run. Use a checkpoint from a normal run, or "
            "pass --scratch."
        ) from None
    if is_scratch and not scratch:
        raise ProvenanceError(
            f"checkpoint {checkpoint} comes from a scratch run ({record_path} "
            'has "scratch" not false). Use a checkpoint from a normal run, or '
            "pass --scratch."
        )
    return parent


def start_run(
    name: str,
    config: dict[str, Any],
    seed: int,
    *,
    device: str,
    scratch: bool = False,
    argv: list[str] | None = None,
    repo: Path | None = None,
    inputs: Sequence[Path] = (),
    checkpoint: Path | None = None,
) -> Path:
    """Check provenance, create `outputs/[scratch-]<name>/`, write `run.json`.

    `repo` is for tests; by default the repository holding this module is
    used. Returns the run directory, the only place the experiment may write.
    Raises `ProvenanceError` if a normal run is not from a clean tree on main,
    if git cannot tell, if a checkpoint has no normal parent run, or if the
    directory exists.
    """
    start = (repo or _code_location()).resolve()
    state: dict[str, Any]
    try:
        root = _repo_root(start)
        state = _inspect(root, start)
    except GitError as error:
        if not scratch:
            raise
        root = start if repo else Path.cwd().resolve()
        state = {
            "commit": None,
            "dirty": None,
            "hidden_changes": None,
            "commit_on_main": None,
            "main_error": None,
            "git_error": str(error),
        }

    if not scratch:
        if state["dirty"]:
            raise ProvenanceError(
                "the working tree has uncommitted changes (including untracked "
                "files not in .gitignore). Commit them, or pass --scratch:\n"
                + state["dirty"]
            )
        if state["hidden_changes"]:
            raise ProvenanceError(
                "tracked files are hidden from git status (skip-worktree or "
                "assume-unchanged): " + ", ".join(state["hidden_changes"])
            )
        if state["main_error"]:
            raise ProvenanceError(state["main_error"])
        if not state["commit_on_main"]:
            raise ProvenanceError(
                f"HEAD {state['commit']} is not on origin/main. Merge it first, "
                "or pass --scratch. If it was merged recently, a `git fetch` "
                "may be needed."
            )

    input_paths = [*inputs, *([checkpoint] if checkpoint else [])]
    recorded_inputs = [
        {"path": str(path), "sha256": _sha256(path)} for path in input_paths
    ]
    parent = _parent(checkpoint, scratch) if checkpoint else None

    directory = root / "outputs" / (f"{SCRATCH_PREFIX}{name}" if scratch else name)
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise ProvenanceError(
            f"{directory} exists; runs are never overwritten. Choose another name."
        ) from error

    record = {
        "run_name": directory.name,
        "status": "started",
        "scratch": scratch,
        **{k: v for k, v in state.items() if k != "main_error"},
        "main_error": state["main_error"],
        "config": config,
        "seed": seed,
        "inputs": recorded_inputs,
        "parent": parent,
        "command": list(sys.argv if argv is None else argv),
        "started_at": datetime.now(UTC).isoformat(),
        "machine": {
            "platform": platform.platform(),
            "processor": platform.machine(),
            "python": platform.python_version(),
            "device": device,
        },
        "packages": _package_versions(),
    }
    _write(directory, record)
    return directory


def _write(directory: Path, record: dict[str, Any]) -> None:
    (directory / "run.json").write_text(
        json.dumps(record, indent=2, default=str) + "\n"
    )


def finish_run(directory: Path, error: BaseException | None = None) -> None:
    """Mark the run `completed`, or `failed` with the error's type and message."""
    record = json.loads((directory / "run.json").read_text())
    record["finished_at"] = datetime.now(UTC).isoformat()
    if error is None:
        record["status"] = "completed"
    else:
        record["status"] = "failed"
        record["error"] = {"type": type(error).__name__, "message": str(error)}
    _write(directory, record)
