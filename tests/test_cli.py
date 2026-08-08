from aerial_search.cli import build_parser


def test_fetch_command_parses() -> None:
    args = build_parser().parse_args(["fetch", "wisard-sample", "--no-extract"])

    assert args.command == "fetch"
    assert args.dataset == "wisard-sample"
    assert args.no_extract is True


def test_prepare_command_parses() -> None:
    args = build_parser().parse_args(["prepare", "data/raw/wisard-sample"])

    assert args.command == "prepare"
