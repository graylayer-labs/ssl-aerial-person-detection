from aerial_search.cli import build_parser


def test_fetch_command_parses() -> None:
    args = build_parser().parse_args(["fetch", "wisard-sample", "--no-extract"])

    assert args.command == "fetch"
    assert args.dataset == "wisard-sample"
    assert args.no_extract is True


def test_prepare_command_parses() -> None:
    args = build_parser().parse_args(["prepare", "data/raw/wisard-sample"])

    assert args.command == "prepare"
    assert args.collection is None


def test_prepare_takes_an_explicit_subset_of_collections() -> None:
    args = build_parser().parse_args(
        [
            "prepare",
            "data/raw/wisard-full",
            "--collection",
            "220109_Baker_Enterprise_1",
            "--collection",
            "210417_MtErie_Enterprise_0005",
        ]
    )

    assert args.collection == [
        "220109_Baker_Enterprise_1",
        "210417_MtErie_Enterprise_0005",
    ]


def test_detection_command_parses() -> None:
    args = build_parser().parse_args(["train-detector", "thermal", "ssl"])

    assert args.command == "train-detector"
    assert args.modality == "thermal"
    assert args.initialization == "ssl"


def test_experiment_commands_accept_scratch_flag() -> None:
    parser = build_parser()
    assert parser.parse_args(["train-ssl", "--scratch"]).scratch is True
    assert parser.parse_args(["train-ssl"]).scratch is False
    assert parser.parse_args(["train-detector", "rgb", "scratch", "--scratch"]).scratch


def test_experiment_refuses_to_start_outside_a_git_repo(tmp_path, monkeypatch) -> None:
    import pytest

    from aerial_search.cli import main

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="refusing to start"):
        main(["train-ssl"])
    assert not (tmp_path / "outputs").exists()


def _fake_repo(tmp_path, monkeypatch):
    import subprocess

    from aerial_search import run as run_module

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text("outputs/\n")
    g = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*g, "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run([*g, "add", ".gitignore"], cwd=repo, check=True)
    subprocess.run([*g, "commit", "-q", "-m", "i"], cwd=repo, check=True)
    subprocess.run(
        [*g, "update-ref", "refs/remotes/origin/main", "HEAD"], cwd=repo, check=True
    )
    monkeypatch.setattr(run_module, "_code_location", lambda: repo)
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "train.jsonl").write_text("{}\n")
    (manifests / "validation.jsonl").write_text("{}\n")
    return repo, manifests


def test_output_option_is_gone() -> None:
    import pytest

    with pytest.raises(SystemExit):
        build_parser().parse_args(["train-ssl", "--output", "x"])
    with pytest.raises(SystemExit):
        build_parser().parse_args(["train-detector", "rgb", "scratch", "--output", "x"])


def test_detector_calls_start_run_before_training(monkeypatch) -> None:
    import pytest

    from aerial_search import cli
    from aerial_search import run as run_module
    from aerial_search.experiments import detection_experiment

    calls: list[str] = []

    def refuse(*args, **kwargs):
        calls.append("start_run")
        raise run_module.ProvenanceError("no")

    def train(*args, **kwargs):
        calls.append("train")

    monkeypatch.setattr(run_module, "start_run", refuse)
    monkeypatch.setattr(detection_experiment, "run_detection_experiment", train)
    with pytest.raises(SystemExit, match="refusing to start"):
        cli.main(["train-detector", "rgb", "scratch"])
    assert calls == ["start_run"]


def test_ssl_run_writes_into_run_dir_and_completes(tmp_path, monkeypatch) -> None:
    import json
    from dataclasses import dataclass

    from aerial_search import cli
    from aerial_search.experiments import ssl_experiment

    repo, manifests = _fake_repo(tmp_path, monkeypatch)
    seen = {}

    @dataclass
    class Result:
        top1: float = 0.5

    def fake(data_root, manifests, output, **kwargs):
        seen["output"] = output
        seen["seed"] = kwargs["seed"]
        return Result()

    monkeypatch.setattr(ssl_experiment, "run_experiment", fake)
    cli.main(["train-ssl", "--manifests", str(manifests), "--run-name", "a"])
    assert seen["output"] == repo / "outputs" / "a"
    data = json.loads((seen["output"] / "run.json").read_text())
    assert data["status"] == "completed"
    assert data["seed"] == seen["seed"]
    assert {i["path"] for i in data["inputs"]} == {
        str(manifests / "train.jsonl"),
        str(manifests / "validation.jsonl"),
    }


def test_failed_experiment_is_marked_failed(tmp_path, monkeypatch) -> None:
    import json

    import pytest

    from aerial_search import cli
    from aerial_search.experiments import ssl_experiment

    repo, manifests = _fake_repo(tmp_path, monkeypatch)

    def crash(*args, **kwargs):
        raise RuntimeError("out of memory")

    monkeypatch.setattr(ssl_experiment, "run_experiment", crash)
    with pytest.raises(RuntimeError):
        cli.main(["train-ssl", "--manifests", str(manifests), "--run-name", "a"])
    data = json.loads((repo / "outputs" / "a" / "run.json").read_text())
    assert data["status"] == "failed"
    assert data["error"]["type"] == "RuntimeError"


def test_detector_gets_seed_and_run_dir(tmp_path, monkeypatch) -> None:
    from dataclasses import dataclass

    from aerial_search import cli
    from aerial_search.experiments import detection_experiment

    repo, manifests = _fake_repo(tmp_path, monkeypatch)
    seen = {}

    @dataclass
    class Result:
        recall: float = 0.1

    def fake(data_root, manifests, output, **kwargs):
        seen.update(output=output, **kwargs)
        return Result()

    monkeypatch.setattr(detection_experiment, "run_detection_experiment", fake)
    cli.main(["train-detector", "rgb", "scratch", "--manifests", str(manifests)])
    assert seen["output"] == repo / "outputs" / "detector-rgb-scratch"
    assert seen["seed"] == cli.SEED
