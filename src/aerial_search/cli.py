"""Command-line entry point for project workflows."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from aerial_search.data import checksums
from aerial_search.data.fetch import WISARD_FULL, WISARD_SAMPLE, fetch_dataset
from aerial_search.data.folds import SEED as FOLD_SEED
from aerial_search.data.folds import (
    VALIDATION,
    ImageSize,
    check_folds,
    fold_table,
    train_file,
    view_dir,
    write_folds,
)
from aerial_search.data.wisard import (
    WISARD_COLLECTIONS,
    prepare_manifests,
    select_collections,
)

DATASETS = {WISARD_SAMPLE.name: WISARD_SAMPLE, WISARD_FULL.name: WISARD_FULL}


SEED = 7  # both experiments seed with 7; recorded in run.json
VIEW = "paired"  # both experiments read the fold's paired-view manifests


def _add_run_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scratch",
        action="store_true",
        help="debugging run: allowed from a dirty tree or off main, never quotable",
    )
    parser.add_argument(
        "--run-name", help="name under outputs/ (default: from command)"
    )


def _start_run(args: argparse.Namespace, default_name: str) -> Path:
    """Check provenance and write run.json; return the run directory.

    The run directory is the only place the experiment writes.
    """
    from aerial_search.models.components import get_device
    from aerial_search.run import ProvenanceError, start_run

    config = {k: v for k, v in vars(args).items() if k not in {"scratch", "run_name"}}
    view = _fold_manifests(args)
    inputs = [view / train_file(100), view / VALIDATION]
    try:
        return start_run(
            args.run_name or default_name,
            config,
            SEED,
            device=str(get_device()),
            scratch=args.scratch,
            inputs=inputs,
            checkpoint=getattr(args, "ssl_checkpoint", None),
            fold=args.fold,
            view=VIEW,
        )
    except ProvenanceError as error:
        raise SystemExit(f"refusing to start: {error}") from error


def _fold_manifests(args: argparse.Namespace) -> Path:
    """The paired-view manifests of the fold named by --fold."""
    return view_dir(args.manifests / "folds", args.fold, VIEW)


def _image_size(source: Path) -> ImageSize:
    from PIL import Image

    def size(path: str) -> tuple[int, int]:
        with Image.open(source / path) as image:
            return image.size

    return size


def _add_fold_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--fold",
        required=True,
        metavar="SITE_DAY",
        help="test site-day of the fold to train on, e.g. 220109_Baker; reads "
        "<manifests>/folds/<SITE_DAY>/paired/",
    )


def _finish(directory: Path, error: BaseException | None = None) -> None:
    from aerial_search.run import finish_run

    finish_run(directory, error)


def build_parser() -> argparse.ArgumentParser:
    """Build the project command-line parser."""
    parser = argparse.ArgumentParser(prog="aerial-search")
    subcommands = parser.add_subparsers(dest="command", required=True)

    fetch = subcommands.add_parser("fetch", help="fetch a public dataset")
    fetch.add_argument("dataset", choices=list(DATASETS.keys()))
    fetch.add_argument("--data-root", type=Path, default=Path("data"))
    fetch.add_argument("--no-extract", action="store_true")

    checksum = subcommands.add_parser(
        "checksum", help="write the checksum list of a dataset directory"
    )
    checksum.add_argument("source", type=Path, help="e.g. data/raw/wisard-full")
    checksum.add_argument(
        "--output",
        type=Path,
        default=checksums.committed_path(),
        help="default: the committed list, under src/aerial_search/data/checksums/",
    )
    check_data = subcommands.add_parser(
        "check-data", help="check a dataset directory against the committed list"
    )
    check_data.add_argument("source", type=Path, help="e.g. data/raw/wisard-full")
    check_data.add_argument("--list", type=Path, default=checksums.committed_path())
    check_data.add_argument(
        "--directory",
        action="append",
        metavar="NAME",
        help="check only this directory (repeat for several); default: all",
    )
    fetch_directory = subcommands.add_parser(
        "fetch-directory",
        help="fetch a WiSARD directory from S3 if absent, then verify it",
    )
    fetch_directory.add_argument("name")
    fetch_directory.add_argument(
        "--data-root", type=Path, default=Path("data/raw/wisard-full")
    )

    prepare = subcommands.add_parser("prepare", help="prepare WiSARD manifests")
    prepare.add_argument("source", type=Path)
    prepare.add_argument(
        "--output", type=Path, default=Path("data/manifests/wisard-sample")
    )
    prepare.add_argument(
        "--collection",
        action="append",
        metavar="ID",
        help="prepare only this collection (repeat for several); default: all",
    )

    prepare.add_argument(
        "--scratch",
        action="store_true",
        help="debugging: allowed from a dirty tree or off main; never quotable",
    )

    folds = subcommands.add_parser(
        "folds", help="write leave-one-site-day-out folds to <manifests>/folds"
    )
    check = subcommands.add_parser(
        "check-folds", help="check <manifests>/folds for leaks between splits"
    )
    for command in (folds, check):
        command.add_argument("source", type=Path, help="raw images, for image sizes")
        command.add_argument("manifests", type=Path, help="output of prepare")
    folds.add_argument("--seed", type=int, default=FOLD_SEED)

    train = subcommands.add_parser("train-ssl", help="run the paired SSL experiment")
    train.add_argument("--data-root", type=Path, default=Path("data/raw/wisard-sample"))
    train.add_argument(
        "--manifests", type=Path, default=Path("data/manifests/wisard-sample")
    )
    train.add_argument("--epochs", type=int, default=10)
    train.add_argument("--batch-size", type=int, default=16)
    _add_fold_flag(train)
    _add_run_flags(train)

    detect = subcommands.add_parser("train-detector", help="run a detection baseline")
    detect.add_argument("modality", choices=["rgb", "thermal"])
    detect.add_argument("initialization", choices=["scratch", "ssl"])
    detect.add_argument(
        "--data-root", type=Path, default=Path("data/raw/wisard-sample")
    )
    detect.add_argument(
        "--manifests", type=Path, default=Path("data/manifests/wisard-sample")
    )
    detect.add_argument("--epochs", type=int, default=5)
    detect.add_argument("--ssl-checkpoint", type=Path)
    _add_fold_flag(detect)
    _add_run_flags(detect)

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

    if args.command == "checksum":
        entries = checksums.hash_tree(args.source, progress=checksums.print_progress)
        checksums.write_list(entries, args.output)
        print(f"{len(entries):,} files, root hash {checksums.root_hash(entries)}")
        print(args.output)
        return

    if args.command == "check-data":
        expected = checksums.read_list(args.list)
        differences = checksums.check_tree(
            args.source, expected, args.directory, checksums.print_progress
        )
        if differences:
            for line in differences.lines():
                print(line)
            print(f"FAIL {args.source} differs from {args.list}")
            raise SystemExit(1)
        root = checksums.root_hash(expected)
        print(f"OK   {args.source} matches {args.list} (root hash {root})")
        return

    if args.command == "fetch-directory":
        try:
            print(checksums.ensure_directory(args.name, args.data_root))
        except (checksums.DataMismatchError, ValueError) as error:
            raise SystemExit(f"FAIL {error}") from error
        return

    if args.command == "prepare":
        collections = (
            select_collections(args.collection)
            if args.collection
            else WISARD_COLLECTIONS
        )
        from aerial_search import run

        try:
            state = run.code_state(scratch=args.scratch)
        except run.ProvenanceError as error:
            raise SystemExit(f"refusing to prepare: {error}") from error
        provenance: dict[str, object] = {
            "commit": state["commit"],
            "scratch": args.scratch,
        }
        if args.scratch:
            provenance["dirty"] = state.get("dirty")
        counts = prepare_manifests(
            args.source, args.output, collections=collections, provenance=provenance
        )
        print(", ".join(f"{name}: {count}" for name, count in counts.items()))
        return

    if args.command == "folds":
        summary = write_folds(
            args.manifests,
            args.manifests / "folds",
            _image_size(args.source),
            seed=args.seed,
        )
        print(fold_table(summary))
        return

    if args.command == "check-folds":
        report = check_folds(
            args.manifests, args.manifests / "folds", _image_size(args.source)
        )
        if report.problems:
            # The summary lines describe a check that did not pass; printing
            # them beside the failures would read as passes.
            for problem in report.problems:
                print(f"FAIL {problem}")
            raise SystemExit(1)
        for line in report.lines:
            print(f"OK   {line}")
        return

    if args.command == "train-detector":
        directory = _start_run(args, f"detector-{args.modality}-{args.initialization}")
        from aerial_search.experiments.detection_experiment import (
            run_detection_experiment,
        )

        try:
            result = run_detection_experiment(
                args.data_root,
                _fold_manifests(args),
                directory,
                modality=args.modality,
                initialization=args.initialization,
                ssl_checkpoint=args.ssl_checkpoint,
                epochs=args.epochs,
                seed=SEED,
            )
        except BaseException as error:
            _finish(directory, error)
            raise
        _finish(directory)
        print(json.dumps(asdict(result), indent=2))
        return

    from aerial_search.experiments.ssl_experiment import run_experiment

    directory = _start_run(args, "ssl")
    try:
        result = run_experiment(
            args.data_root,
            _fold_manifests(args),
            directory,
            epochs=args.epochs,
            batch_size=args.batch_size,
            seed=SEED,
        )
    except BaseException as error:
        _finish(directory, error)
        raise
    _finish(directory)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
