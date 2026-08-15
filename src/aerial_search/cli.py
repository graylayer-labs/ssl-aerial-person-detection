"""Command-line entry point for project workflows."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from aerial_search.data.fetch import WISARD_FULL, WISARD_SAMPLE, fetch_dataset
from aerial_search.data.wisard import prepare_manifests

DATASETS = {WISARD_SAMPLE.name: WISARD_SAMPLE, WISARD_FULL.name: WISARD_FULL}


def build_parser() -> argparse.ArgumentParser:
    """Build the project command-line parser."""
    parser = argparse.ArgumentParser(prog="aerial-search")
    subcommands = parser.add_subparsers(dest="command", required=True)

    fetch = subcommands.add_parser("fetch", help="fetch a public dataset")
    fetch.add_argument("dataset", choices=list(DATASETS.keys()))
    fetch.add_argument("--data-root", type=Path, default=Path("data"))
    fetch.add_argument("--no-extract", action="store_true")

    prepare = subcommands.add_parser("prepare", help="prepare WiSARD manifests")
    prepare.add_argument("source", type=Path)
    prepare.add_argument(
        "--output", type=Path, default=Path("data/processed/wisard-sample")
    )

    train = subcommands.add_parser("train-ssl", help="run the paired SSL experiment")
    train.add_argument("--data-root", type=Path, default=Path("data/raw/wisard-sample"))
    train.add_argument(
        "--manifests", type=Path, default=Path("data/processed/wisard-sample")
    )
    train.add_argument("--output", type=Path, default=Path("outputs/ssl-sample"))
    train.add_argument("--epochs", type=int, default=10)
    train.add_argument("--batch-size", type=int, default=16)

    detect = subcommands.add_parser("train-detector", help="run a detection baseline")
    detect.add_argument("modality", choices=["rgb", "thermal"])
    detect.add_argument("initialization", choices=["scratch", "ssl"])
    detect.add_argument(
        "--data-root", type=Path, default=Path("data/raw/wisard-sample")
    )
    detect.add_argument(
        "--manifests", type=Path, default=Path("data/processed/wisard-sample")
    )
    detect.add_argument("--output", type=Path, default=Path("outputs/detection-sample"))
    detect.add_argument("--epochs", type=int, default=5)
    detect.add_argument("--ssl-checkpoint", type=Path)

    return parser


def main(argv: list[str] | None = None) -> None:
    """Run a project data command."""
    args = build_parser().parse_args(argv)
    if args.command == "fetch":
        source = DATASETS[args.dataset]
        destination = fetch_dataset(
            source,
            args.data_root,
            extract=not args.no_extract,
        )
        print(destination)
        return

    if args.command == "prepare":
        counts = prepare_manifests(args.source, args.output)
        print(", ".join(f"{name}: {count}" for name, count in counts.items()))
        return

    if args.command == "train-detector":
        from aerial_search.experiments.detection_experiment import (
            run_detection_experiment,
        )

        result = run_detection_experiment(
            args.data_root,
            args.manifests,
            args.output,
            modality=args.modality,
            initialization=args.initialization,
            ssl_checkpoint=args.ssl_checkpoint,
            epochs=args.epochs,
        )
        print(json.dumps(asdict(result), indent=2))
        return

    from aerial_search.experiments.ssl_experiment import run_experiment

    result = run_experiment(
        args.data_root,
        args.manifests,
        args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
