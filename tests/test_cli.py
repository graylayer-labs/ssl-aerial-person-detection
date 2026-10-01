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


def test_folds_commands_take_the_raw_images_and_the_manifests() -> None:
    parser = build_parser()
    for command in ("folds", "check-folds"):
        args = parser.parse_args(
            [command, "data/raw/wisard-full", "data/manifests/wisard-full"]
        )
        assert args.command == command
        assert str(args.source) == "data/raw/wisard-full"
        assert str(args.manifests) == "data/manifests/wisard-full"


def test_experiments_need_a_fold() -> None:
    import pytest

    with pytest.raises(SystemExit):
        build_parser().parse_args(["train-ssl"])
    with pytest.raises(SystemExit):
        build_parser().parse_args(["train-detector", "rgb", "scratch"])


def test_detection_command_parses() -> None:
    args = build_parser().parse_args(
        ["train-detector", "thermal", "ssl", "--fold", "220109_Baker"]
    )

    assert args.command == "train-detector"
    assert args.modality == "thermal"
    assert args.initialization == "ssl"


def test_experiment_commands_accept_scratch_flag() -> None:
    parser = build_parser()
    assert (
        parser.parse_args(["train-ssl", "--fold", "220109_Baker", "--scratch"]).scratch
        is True
    )
    assert parser.parse_args(["train-ssl", "--fold", "220109_Baker"]).scratch is False
    assert parser.parse_args(
        ["train-detector", "rgb", "scratch", "--fold", "220109_Baker", "--scratch"]
    ).scratch


def test_experiment_refuses_to_start_outside_a_git_repo(tmp_path, monkeypatch) -> None:
    import pytest

    from aerial_search.cli import main

    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="refusing to start"):
        main(["train-ssl", "--fold", "220109_Baker"])
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
    view = manifests / "folds" / "220109_Baker" / "paired"
    view.mkdir(parents=True)
    (view / "train_100pct.jsonl").write_text("{}\n")
    (view / "validation.jsonl").write_text("{}\n")
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
        cli.main(["train-detector", "rgb", "scratch", "--fold", "220109_Baker"])
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
        seen["manifests"] = manifests
        seen["seed"] = kwargs["seed"]
        return Result()

    monkeypatch.setattr(ssl_experiment, "run_experiment", fake)
    cli.main(
        [
            "train-ssl",
            "--manifests",
            str(manifests),
            "--fold",
            "220109_Baker",
            "--run-name",
            "a",
        ]
    )
    assert seen["output"] == repo / "outputs" / "a"
    data = json.loads((seen["output"] / "run.json").read_text())
    assert data["status"] == "completed"
    assert data["seed"] == seen["seed"]
    assert (data["fold"], data["view"]) == ("220109_Baker", "paired")
    assert {i["path"] for i in data["inputs"]} == {
        str(manifests / "folds" / "220109_Baker" / "paired" / "train_100pct.jsonl"),
        str(manifests / "folds" / "220109_Baker" / "paired" / "validation.jsonl"),
    }
    assert seen["manifests"] == manifests / "folds" / "220109_Baker" / "paired"


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
        cli.main(
            [
                "train-ssl",
                "--manifests",
                str(manifests),
                "--fold",
                "220109_Baker",
                "--run-name",
                "a",
            ]
        )
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
    cli.main(
        [
            "train-detector",
            "rgb",
            "scratch",
            "--manifests",
            str(manifests),
            "--fold",
            "220109_Baker",
        ]
    )
    assert seen["output"] == repo / "outputs" / "detector-rgb-scratch"
    assert seen["seed"] == cli.SEED


def test_detector_refuses_a_checkpoint_pretrained_in_another_fold(
    tmp_path, monkeypatch
) -> None:
    import json

    import pytest

    from aerial_search import cli
    from aerial_search.experiments import detection_experiment

    repo, manifests = _fake_repo(tmp_path, monkeypatch)
    parent = tmp_path / "ssl-mterie"
    parent.mkdir()
    (parent / "model.pt").write_text("weights")
    (parent / "run.json").write_text(
        json.dumps(
            {
                "run_name": "ssl-mterie",
                "scratch": False,
                "commit": "abc",
                "status": "completed",
                "fold": "210417_MtErie",
                "view": "paired",
            }
        )
    )
    monkeypatch.setattr(
        detection_experiment, "run_detection_experiment", lambda *a, **k: None
    )
    with pytest.raises(SystemExit, match="210417_MtErie.*220109_Baker"):
        cli.main(
            [
                "train-detector",
                "rgb",
                "ssl",
                "--manifests",
                str(manifests),
                "--fold",
                "220109_Baker",
                "--ssl-checkpoint",
                str(parent / "model.pt"),
            ]
        )
    assert not (repo / "outputs").exists()


def _check_folds_output(monkeypatch, capsys, report) -> tuple[str, int]:
    from aerial_search import cli

    monkeypatch.setattr(cli, "check_folds", lambda *a, **k: report)
    monkeypatch.setattr(cli, "_image_size", lambda source: None)
    code = 0
    try:
        cli.main(["check-folds", "raw", "manifests"])
    except SystemExit as exit_:
        code = exit_.code
    return capsys.readouterr().out, code


def test_check_folds_marks_every_line_of_a_passing_check(monkeypatch, capsys) -> None:
    from aerial_search.data.folds import CheckReport

    out, code = _check_folds_output(
        monkeypatch, capsys, CheckReport(lines=["no leaks", "gap 250"])
    )

    assert code == 0
    assert out.splitlines() == ["OK   no leaks", "OK   gap 250"]


def test_check_folds_prints_only_the_failures_of_a_failing_check(
    monkeypatch, capsys
) -> None:
    from aerial_search.data.folds import CheckReport

    report = CheckReport(lines=["no leaks", "gap 250"], problems=["train holds test"])

    out, code = _check_folds_output(monkeypatch, capsys, report)

    assert code == 1
    assert out.splitlines() == ["FAIL train holds test"]
