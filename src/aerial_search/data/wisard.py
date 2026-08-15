"""Load synchronized RGB and thermal samples from WiSARD."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImagePair:
    """Paths for one synchronized RGB–thermal observation."""

    collection_id: str
    rgb_image: Path
    thermal_image: Path
    rgb_labels: Path
    thermal_labels: Path


@dataclass(frozen=True)
class BoundingBox:
    """A normalized YOLO person bounding box."""

    x_center: float
    y_center: float
    width: float
    height: float


def load_pairs(root: Path) -> list[ImagePair]:
    """Return synchronized pairs from all flight collections."""
    pairs: list[ImagePair] = []
    for collection_id, (rgb_dir, thermal_dir) in _group_collections(root).items():
        pairs.extend(_pair_collection(rgb_dir, thermal_dir, collection_id))
    return pairs


def _find_collections(root: Path, marker: str) -> list[Path]:
    """Find all directories under root containing marker token."""
    return sorted(
        path for path in root.iterdir()
        if path.is_dir() and marker in path.name.split("_")
    )


def _flight_key(name: str, marker: str) -> str:
    """Extract shared flight prefix by removing marker and everything after it."""
    parts = name.split("_")
    return "_".join(parts[: parts.index(marker)])


def _group_collections(root: Path) -> dict[str, tuple[Path, Path]]:
    """Pair VIS/IR directories by flight key, raising on ambiguity or mismatch."""
    vis_dirs = _find_collections(root, "VIS")
    ir_dirs = _find_collections(root, "IR")

    vis_by_key = {_flight_key(p.name, "VIS"): p for p in vis_dirs}
    ir_by_key = {_flight_key(p.name, "IR"): p for p in ir_dirs}

    if len(vis_by_key) != len(vis_dirs) or len(ir_by_key) != len(ir_dirs):
        raise ValueError("Ambiguous VIS/IR collections share a flight key")

    missing = sorted(set(vis_by_key) ^ set(ir_by_key))
    if missing:
        raise ValueError(f"Unmatched VIS/IR flight collections: {missing}")

    return {k: (vis_by_key[k], ir_by_key[k]) for k in sorted(vis_by_key)}


def _pair_collection(
    rgb_dir: Path, thermal_dir: Path, collection_id: str
) -> list[ImagePair]:
    """Pair images within a single flight collection."""
    rgb_images = sorted(rgb_dir.glob("*.jpeg"))
    thermal_images = sorted(thermal_dir.glob("*.jpeg"))

    if not rgb_images or len(rgb_images) != len(thermal_images):
        raise ValueError(
            f"Expected equal, non-empty RGB and thermal collections for "
            f"{collection_id}, got {len(rgb_images)} RGB and "
            f"{len(thermal_images)} thermal"
        )

    pairs = []
    for rgb_image, thermal_image in zip(rgb_images, thermal_images, strict=True):
        rgb_labels = rgb_image.with_suffix(".txt")
        thermal_labels = thermal_image.with_suffix(".txt")
        if not rgb_labels.exists() or not thermal_labels.exists():
            raise ValueError(
                f"Every image must have a matching annotation file in {collection_id}"
            )
        pairs.append(
            ImagePair(
                collection_id,
                rgb_image,
                thermal_image,
                rgb_labels,
                thermal_labels,
            )
        )
    return pairs


def load_boxes(path: Path) -> list[BoundingBox]:
    """Load normalized person boxes from a WiSARD annotation file."""
    boxes = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5 or fields[0] != "0":
            raise ValueError(f"Invalid person annotation at {path}:{line_number}")
        coordinates = [float(value) for value in fields[1:]]
        if any(not 0 <= value <= 1 for value in coordinates):
            raise ValueError(f"Invalid normalized box at {path}:{line_number}")
        boxes.append(BoundingBox(*coordinates))
    return boxes


def load_pairs_by_collection(root: Path) -> dict[str, list[ImagePair]]:
    """Return pairs grouped by collection_id."""
    grouped: dict[str, list[ImagePair]] = {}
    for pair in load_pairs(root):
        grouped.setdefault(pair.collection_id, []).append(pair)
    return grouped


def prepare_manifests(
    source: Path,
    destination: Path,
    *,
    train_fraction: float = 0.7,
    validation_fraction: float = 0.15,
    seed: int = 7,
) -> dict[str, int]:
    """Write collection-level JSONL splits via seeded greedy bin-filling."""
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must leave a test split")

    by_collection = load_pairs_by_collection(source)
    collection_ids = list(by_collection)
    random.Random(seed).shuffle(collection_ids)

    total = sum(len(p) for p in by_collection.values())
    target_train = total * train_fraction
    target_validation = total * validation_fraction

    splits: dict[str, list[ImagePair]] = {"train": [], "validation": [], "test": []}
    counts = {"train": 0, "validation": 0, "test": 0}

    for cid in collection_ids:
        name = (
            "train"
            if counts["train"] < target_train
            else "validation"
            if counts["validation"] < target_validation
            else "test"
        )
        splits[name].extend(by_collection[cid])
        counts[name] += len(by_collection[cid])

    destination.mkdir(parents=True, exist_ok=True)
    for name, split_pairs in splits.items():
        manifest = destination / f"{name}.jsonl"
        with manifest.open("w") as output:
            for pair in split_pairs:
                output.write(json.dumps(_pair_record(pair, source)) + "\n")
    return {name: len(split_pairs) for name, split_pairs in splits.items()}


def _pair_record(pair: ImagePair, source: Path) -> dict[str, object]:
    return {
        "rgb_image": str(pair.rgb_image.relative_to(source)),
        "thermal_image": str(pair.thermal_image.relative_to(source)),
        "rgb_boxes": [box.__dict__ for box in load_boxes(pair.rgb_labels)],
        "thermal_boxes": [box.__dict__ for box in load_boxes(pair.thermal_labels)],
    }
