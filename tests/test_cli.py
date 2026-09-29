from aerial_search.cli import build_parser


def test_fetch_command_parses() -> None:
    args = build_parser().parse_args(["fetch", "wisard-sample", "--no-extract"])

    assert args.command == "fetch"
    assert args.dataset == "wisard-sample"
    assert args.no_extract is True


def test_prepare_command_parses() -> None:
    args = build_parser().parse_args(["prepare", "data/raw/wisard-sample"])

    assert args.command == "prepare"


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
