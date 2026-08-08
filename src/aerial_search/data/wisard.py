"""Load synchronized RGB and thermal samples from WiSARD."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImagePair:
    """Paths for one synchronized RGB–thermal observation."""

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
    """Return synchronized pairs ordered by capture sequence."""
    rgb_dir = _find_collection(root, "VIS")
    thermal_dir = _find_collection(root, "IR")
    rgb_images = sorted(rgb_dir.glob("*.jpeg"))
    thermal_images = sorted(thermal_dir.glob("*.jpeg"))

    if not rgb_images or len(rgb_images) != len(thermal_images):
        raise ValueError("Expected equal, non-empty RGB and thermal collections")

    pairs = []
    for rgb_image, thermal_image in zip(rgb_images, thermal_images, strict=True):
        rgb_labels = rgb_image.with_suffix(".txt")
        thermal_labels = thermal_image.with_suffix(".txt")
        if not rgb_labels.exists() or not thermal_labels.exists():
            raise ValueError("Every image must have a matching annotation file")
        pairs.append(ImagePair(rgb_image, thermal_image, rgb_labels, thermal_labels))
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


def prepare_manifests(
    source: Path,
    destination: Path,
    *,
    train_fraction: float = 0.7,
    validation_fraction: float = 0.15,
) -> dict[str, int]:
    """Write sequential JSONL splits for the single-flight development sample."""
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must leave a test split")

    pairs = load_pairs(source)
    train_end = int(len(pairs) * train_fraction)
    validation_end = train_end + int(len(pairs) * validation_fraction)
    splits = {
        "train": pairs[:train_end],
        "validation": pairs[train_end:validation_end],
        "test": pairs[validation_end:],
    }

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


def _find_collection(root: Path, marker: str) -> Path:
    matches = [
        path
        for path in root.iterdir()
        if path.is_dir() and marker in path.name.split("_")
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one {marker} collection, found {len(matches)}")
    return matches[0]
