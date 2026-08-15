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


def _normalize_collection_name(name: str, marker: str) -> str:
    """Extract flight identifier from collection directory name.

    Handles various naming patterns:
    - 200910_Carnation_FLIR_IR_1 → 200910_Carnation_FLIR
    - 210417_MtErie_Enterprise_IR_0004 → 210417_MtErie_Enterprise
    - 200426_SkookumCreek_Mavic_Mini_VIS_0006 → 200426_SkookumCreek_Mavic_Mini
    """
    parts = name.split("_")
    marker_idx = parts.index(marker)
    return "_".join(parts[:marker_idx])


def _group_collections(root: Path) -> dict[str, tuple[Path, Path]]:
    """Pair VIS/IR directories, skipping unpaired locations.

    Real-world datasets may have:
    - Locations with only VIS (no thermal)
    - Locations with multiple VIS/IR shots (variants)
    - Locations with both

    This groups by normalized location name and pairs exactly one VIS with one IR.
    Locations without both modalities are skipped silently.
    """
    vis_dirs = {p.name: p for p in _find_collections(root, "VIS")}
    ir_dirs = {p.name: p for p in _find_collections(root, "IR")}

    # Group by normalized name (location without modality suffix)
    vis_by_location = {}
    ir_by_location = {}

    for name in vis_dirs:
        loc = _normalize_collection_name(name, "VIS")
        if loc not in vis_by_location:
            vis_by_location[loc] = []
        vis_by_location[loc].append(vis_dirs[name])

    for name in ir_dirs:
        loc = _normalize_collection_name(name, "IR")
        if loc not in ir_by_location:
            ir_by_location[loc] = []
        ir_by_location[loc].append(ir_dirs[name])

    # Pair: locations that have both VIS and IR
    # Only pair if each location has exactly one of each modality (to ensure alignment)
    # Locations with multiple variants are skipped
    pairs = {}
    for loc in sorted(set(vis_by_location) & set(ir_by_location)):
        if len(vis_by_location[loc]) == 1 and len(ir_by_location[loc]) == 1:
            pairs[loc] = (vis_by_location[loc][0], ir_by_location[loc][0])
        # else: skip locations with multiple VIS/IR variants (misaligned data)

    return pairs


def _pair_collection(
    rgb_dir: Path, thermal_dir: Path, collection_id: str
) -> list[ImagePair]:
    """Pair images within a single flight collection."""
    # Handle both .jpeg and .jpg extensions
    rgb_images = sorted(rgb_dir.glob("*.jpg")) + sorted(rgb_dir.glob("*.jpeg"))
    rgb_images = sorted(set(rgb_images))  # Remove duplicates and re-sort
    thermal_images = sorted(thermal_dir.glob("*.jpg")) + sorted(thermal_dir.glob("*.jpeg"))
    thermal_images = sorted(set(thermal_images))  # Remove duplicates and re-sort

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
