"""Command-line entry point for project workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from aerial_search.data.fetch import WISARD_SAMPLE, fetch_dataset


def build_parser() -> argparse.ArgumentParser:
    """Build the project command-line parser."""
    parser = argparse.ArgumentParser(prog="aerial-search")
    subcommands = parser.add_subparsers(dest="command", required=True)

    fetch = subcommands.add_parser("fetch", help="fetch a public dataset")
    fetch.add_argument("dataset", choices=[WISARD_SAMPLE.name])
    fetch.add_argument("--data-root", type=Path, default=Path("data"))
    fetch.add_argument("--no-extract", action="store_true")

    inspect = subcommands.add_parser("inspect", help="locate data for an audit")
    inspect.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run a project data command."""
    args = build_parser().parse_args(argv)
    if args.command == "fetch":
        destination = fetch_dataset(
            WISARD_SAMPLE,
            args.data_root,
            extract=not args.no_extract,
        )
        print(destination)
        return

    path: Path = args.path
    if not path.exists():
        raise SystemExit(f"Data path does not exist: {path}")
    file_count = sum(item.is_file() for item in path.rglob("*"))
    print(f"{path}: {file_count:,} files")


if __name__ == "__main__":
    main()
