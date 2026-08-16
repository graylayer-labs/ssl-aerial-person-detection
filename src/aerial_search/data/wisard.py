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


def load_pairs(
    root: Path, stats: dict[str, int] | None = None
) -> list[ImagePair]:
    """Return synchronized pairs from all flight collections.

    If stats dict provided, it's filled with counters for pragmatic pairing decisions.
    """
    pairs: list[ImagePair] = []
    for cid, (rgb_dir, thermal_dir) in _group_collections(
        root, stats=stats
    ).items():
        pairs.extend(
            _pair_collection(rgb_dir, thermal_dir, cid, stats=stats)
        )
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


def _group_collections(
    root: Path, stats: dict[str, int] | None = None
) -> dict[str, tuple[Path, Path]]:
    """Pair VIS/IR directories, skipping unpaired locations.

    Real-world datasets may have:
    - Locations with only VIS (no thermal)
    - Locations with multiple VIS/IR shots (variants)
    - Locations with both

    This groups by normalized location name and pairs exactly one VIS with one IR.
    Locations without both modalities are skipped silently.

    If stats dict provided, increments 'flights_multi_variant' when num_pairs > 1.
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
    # Real-world datasets often have multiple variants per location.
    # Strategy: pair as many as possible using min(vis_count, ir_count)
    # This ensures every paired directory has a corresponding modality.
    pairs = {}
    for loc in sorted(set(vis_by_location) & set(ir_by_location)):
        vis_dirs = sorted(vis_by_location[loc])
        ir_dirs = sorted(ir_by_location[loc])
        # Pair up to the minimum count (e.g., 3 VIS with 7 IR → 3 pairs)
        num_pairs = min(len(vis_dirs), len(ir_dirs))
        if num_pairs > 1 and stats is not None:
            stats['flights_multi_variant'] = stats.get('flights_multi_variant', 0) + 1
        for i in range(num_pairs):
            # Use collection_id with an index if multiple pairs per location
            pair_id = f"{loc}_{i}" if num_pairs > 1 else loc
            pairs[pair_id] = (vis_dirs[i], ir_dirs[i])

    return pairs


def _pair_collection(
    rgb_dir: Path,
    thermal_dir: Path,
    collection_id: str,
    stats: dict[str, int] | None = None,
) -> list[ImagePair]:
    """Pair images within a single flight collection.

    Real-world datasets may have mismatched image counts (e.g., RGB captured
    more frames than thermal due to sensor differences). Pairs up to min(count).

    If stats dict provided, increments 'frames_skipped' when annotations are missing.
    """
    # Handle both .jpeg and .jpg extensions
    rgb_images = sorted(rgb_dir.glob("*.jpg")) + sorted(
        rgb_dir.glob("*.jpeg")
    )
    rgb_images = sorted(set(rgb_images))  # Remove duplicates and re-sort
    thermal_images = sorted(thermal_dir.glob("*.jpg")) + sorted(
        thermal_dir.glob("*.jpeg")
    )
    thermal_images = sorted(set(thermal_images))  # Remove duplicates and re-sort

    if not rgb_images or not thermal_images:
        raise ValueError(
            f"Expected non-empty RGB and thermal collections for "
            f"{collection_id}, got {len(rgb_images)} RGB and "
            f"{len(thermal_images)} thermal"
        )

    # Pair up to min(count) - accept real-world mismatch silently
    num_pairs = min(len(rgb_images), len(thermal_images))

    pairs = []
    for rgb_image, thermal_image in zip(
        rgb_images[:num_pairs], thermal_images[:num_pairs], strict=False
    ):
        rgb_labels = rgb_image.with_suffix(".txt")
        thermal_labels = thermal_image.with_suffix(".txt")
        # Skip pairs without annotations (real datasets often have partial labeling)
        if not rgb_labels.exists() or not thermal_labels.exists():
            if stats is not None:
                stats['frames_skipped'] = stats.get('frames_skipped', 0) + 1
            continue
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


def load_boxes(
    path: Path, stats: dict[str, int] | None = None
) -> list[BoundingBox]:
    """Load normalized person boxes from a WiSARD annotation file.

    If stats dict provided, increments 'boxes_clamped' when coordinates are
    out-of-range.
    """
    boxes = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        fields = line.split()
        if len(fields) != 5 or fields[0] != "0":
            raise ValueError(f"Invalid person annotation at {path}:{line_number}")
        # Parse coordinates; clamp to [0, 1] to handle annotation errors
        values = [float(v) for v in fields[1:]]
        clamped = [max(0.0, min(1.0, v)) for v in values]
        if stats is not None and any(
            clamped[i] != values[i] for i in range(len(values))
        ):
            stats['boxes_clamped'] = stats.get('boxes_clamped', 0) + 1
        boxes.append(BoundingBox(*clamped))
    return boxes


def load_pairs_by_collection(
    root: Path, stats: dict[str, int] | None = None
) -> dict[str, list[ImagePair]]:
    """Return pairs grouped by collection_id.

    If stats dict provided, it's filled with counters from load_pairs.
    """
    grouped: dict[str, list[ImagePair]] = {}
    for pair in load_pairs(root, stats=stats):
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
    """Write collection-level JSONL splits via seeded greedy bin-filling.

    Also writes data_quality.json with counts of pragmatic pairing decisions.
    """
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must leave a test split")

    stats: dict[str, int] = {}
    by_collection = load_pairs_by_collection(source, stats=stats)
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
                output.write(json.dumps(_pair_record(pair, source, stats=stats)) + "\n")

    # Write data quality log
    quality_log = destination / "data_quality.json"
    with quality_log.open("w") as f:
        json.dump({
            "frames_skipped": stats.get("frames_skipped", 0),
            "boxes_clamped": stats.get("boxes_clamped", 0),
            "flights_multi_variant": stats.get("flights_multi_variant", 0),
        }, f, indent=2)

    return {name: len(split_pairs) for name, split_pairs in splits.items()}


def _pair_record(
    pair: ImagePair, source: Path, stats: dict[str, int] | None = None
) -> dict[str, object]:
    return {
        "collection_id": pair.collection_id,
        "rgb_image": str(pair.rgb_image.relative_to(source)),
        "thermal_image": str(pair.thermal_image.relative_to(source)),
        "rgb_boxes": [
            box.__dict__
            for box in load_boxes(pair.rgb_labels, stats=stats)
        ],
        "thermal_boxes": [
            box.__dict__
            for box in load_boxes(pair.thermal_labels, stats=stats)
        ],
    }
