"""Run provenance: tie every run to a commit on main, or mark it as scratch.

Call `start_run` first in every experiment entry point. A normal run starts
only from a clean working tree whose HEAD is on the local `origin/main`. A
scratch run starts from any state and is labelled so its numbers cannot be
quoted. The check fails closed: if git cannot answer, a normal run is refused.

Runs are never overwritten. If `outputs/<run-name>/` already exists, the call
raises `ProvenanceError`; choose another run name.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

MAIN_REF = "refs/remotes/origin/main"
SCRATCH_PREFIX = "scratch-"
PACKAGES = ("torch", "torchvision")


class ProvenanceError(RuntimeError):
    """A normal run was refused, or the run directory cannot be created."""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        k: v for k, v in os.environ.items() if not k.startswith("GIT_")
    }  # a hook's GIT_DIR must not redirect us to another repository
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except OSError as error:
        raise ProvenanceError(f"cannot run git: {error}") from error


def _git_ok(repo: Path, *args: str) -> str:
    result = _git(repo, *args)
    if result.returncode != 0:
        raise ProvenanceError(
            f"`git {' '.join(args)}` failed: {result.stderr.strip() or 'no output'}"
        )
    return result.stdout


def _inspect(repo: Path) -> dict[str, Any]:
    """Return commit, dirty output and on-main status. Raise if git cannot tell."""
    commit = _git_ok(repo, "rev-parse", "HEAD").strip()
    # Untracked files are listed; ignored files are not.
    dirty = _git_ok(repo, "status", "--porcelain")
    if _git(repo, "rev-parse", "--verify", "--quiet", MAIN_REF).returncode != 0:
        raise ProvenanceError(
            "origin/main is not known in this repository, so it cannot be "
            "checked whether HEAD is on main. A `git fetch` may be needed."
        )
    ancestor = _git(repo, "merge-base", "--is-ancestor", "HEAD", MAIN_REF)
    if ancestor.returncode not in (0, 1):
        raise ProvenanceError(f"cannot compare HEAD with origin/main: {ancestor.stderr}")
    return {
        "commit": commit,
        "dirty": dirty,
        "commit_on_main": ancestor.returncode == 0,
    }


def _package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in PACKAGES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    return versions


def start_run(
    name: str,
    config: dict[str, Any],
    seed: int,
    *,
    device: str,
    scratch: bool = False,
    argv: list[str] | None = None,
    repo: Path | None = None,
) -> Path:
    """Check provenance, create `outputs/[scratch-]<name>/`, write `run.json`.

    Returns the run directory. Raises `ProvenanceError` if a normal run is not
    from a clean tree on main, if git cannot tell, or if the directory exists.
    """
    repo = (repo or Path.cwd()).resolve()
    state: dict[str, Any]
    try:
        state = _inspect(repo)
    except ProvenanceError as error:
        if not scratch:
            raise
        state = {"commit": None, "dirty": None, "commit_on_main": None}
        state["git_error"] = str(error)
        if state["git_error"].startswith("origin/main is not known"):
            # git works; only origin/main is missing. Keep what we can.
            state["commit"] = _git(repo, "rev-parse", "HEAD").stdout.strip() or None
            state["dirty"] = _git(repo, "status", "--porcelain").stdout

    if not scratch:
        if state["dirty"]:
            raise ProvenanceError(
                "the working tree has uncommitted changes (including untracked "
                "files not in .gitignore). Commit them, or pass --scratch:\n"
                + state["dirty"]
            )
        if not state["commit_on_main"]:
            raise ProvenanceError(
                f"HEAD {state['commit']} is not on origin/main. Merge it first, "
                "or pass --scratch. If it was merged recently, a `git fetch` "
                "may be needed."
            )

    directory = repo / "outputs" / (f"{SCRATCH_PREFIX}{name}" if scratch else name)
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise ProvenanceError(
            f"{directory} exists; runs are never overwritten. Choose another name."
        ) from error

    record = {
        "run_name": directory.name,
        "scratch": scratch,
        **state,
        "config": config,
        "seed": seed,
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
    (directory / "run.json").write_text(
        json.dumps(record, indent=2, default=str) + "\n"
    )
    return directory
