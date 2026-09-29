"""Load synchronized RGB and thermal samples from WiSARD."""

from __future__ import annotations

import json
import random
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict


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


class CollectionCounts(TypedDict):
    """How the frames of one collection were paired."""

    rgb_dir: str
    thermal_dir: str
    rgb_frames: int
    thermal_frames: int
    pairs: int
    labelled_pairs: int
    rgb_only_frames: int
    thermal_only_frames: int


class PairingReport(TypedDict):
    """How the image directories under a dataset root were paired."""

    collections: dict[str, CollectionCounts]
    missing_collections: list[str]
    unpaired_directories: list[str]


# VIS and IR directories that were recorded together, keyed by collection id.
#
# Only these directories are paired. Every entry was checked against the images:
# camera motion between frames agrees across the two directories at equal frame
# numbers (to within two frames), and contact sheets of start, middle, and end
# pairs show the same scene. See docs/wisard-pairing-review.md.
#
# The Mavic 2 Enterprise Advanced writes the VIS and IR video of one recording
# as consecutive DJI file numbers, so VIS n goes with IR n+1. Directories not
# listed here are not paired, and are reported as unpaired. In particular the
# 210327 Airfield FLIR directories are left out: their VIS and IR frame numbers
# run at different rates, so equal numbers are not the same moment.
Collections = Mapping[str, tuple[str, str]]

WISARD_COLLECTIONS: Collections = {
    "210417_MtErie_Enterprise_0003": (
        "210417_MtErie_Enterprise_VIS_0003",
        "210417_MtErie_Enterprise_IR_0004",
    ),
    "210417_MtErie_Enterprise_0005": (
        "210417_MtErie_Enterprise_VIS_0005",
        "210417_MtErie_Enterprise_IR_0006",
    ),
    "210417_MtErie_Enterprise_0007": (
        "210417_MtErie_Enterprise_VIS_0007",
        "210417_MtErie_Enterprise_IR_0008",
    ),
    "210529_Carnation_Enterprise_0023": (
        "210529_Carnation_Enterprise_VIS_0023",
        "210529_Carnation_Enterprise_IR_0024",
    ),
    "210529_Carnation_Enterprise_0025": (
        "210529_Carnation_Enterprise_VIS_0025",
        "210529_Carnation_Enterprise_IR_0026",
    ),
    "210812_Hannegan_Enterprise_0053": (
        "210812_Hannegan_Enterprise_VIS_0053",
        "210812_Hannegan_Enterprise_IR_0054",
    ),
    "210812_Hannegan_Enterprise_0055": (
        "210812_Hannegan_Enterprise_VIS_0055",
        "210812_Hannegan_Enterprise_IR_0056",
    ),
    **{
        f"210924_FHL_Enterprise_{vis:04d}": (
            f"210924_FHL_Enterprise_VIS_{vis:04d}",
            f"210924_FHL_Enterprise_IR_{vis + 1:04d}",
        )
        for vis in (126, 134, 401, 403, 405, 407, 409, 564, 566)
    },
    # Recorded as DJI_0582 (VIS) and DJI_0583 (IR). IR_2 (DJI_0585) has no VIS.
    "220109_Baker_Enterprise_1": (
        "220109_Baker_Enterprise_VIS_1",
        "220109_Baker_Enterprise_IR_1",
    ),
}

# A listed pair must share at least this fraction of the smaller directory's
# frame numbers. Less than that means the two directories number their frames
# differently, and equal numbers cannot be trusted to mean the same moment.
MIN_SHARED_FRAMES = 0.95

_FRAME_NUMBER = re.compile(r"[_ ](\d+)\.(?:jpg|jpeg)$", re.IGNORECASE)


def _extract_frame_index(path: Path) -> int:
    """Return the frame number at the end of a WiSARD image filename.

    The number follows the last underscore or space, and may have any number of
    digits:
    - 210327_Airfield_FLIR_VIS_1_00000075.jpg → 75
    - DJI_0402.mp4_00000.jpg → 0
    - 20200929_134258_IR 127.jpg → 127

    Raises ValueError if the name has no frame number, so that a file is never
    paired on a guess.
    """
    match = _FRAME_NUMBER.search(path.name)
    if match is None:
        raise ValueError(f"No frame number in image filename: {path}")
    return int(match.group(1))


def _frames_by_index(directory: Path) -> dict[int, Path]:
    """Map frame number to image for every JPEG in a directory.

    Raises ValueError if two images share a frame number.
    """
    frames: dict[int, Path] = {}
    for image in sorted(directory.iterdir()):
        if image.suffix.lower() not in {".jpg", ".jpeg"}:
            continue
        index = _extract_frame_index(image)
        if index in frames:
            raise ValueError(
                f"Duplicate frame {index} in {directory}: "
                f"{frames[index].name} and {image.name}"
            )
        frames[index] = image
    return frames


def _group_collections(
    root: Path, collections: Collections = WISARD_COLLECTIONS
) -> dict[str, tuple[Path, Path]]:
    """Return the listed VIS/IR directory pairs that exist under root."""
    grouped = {}
    for cid, (rgb_name, thermal_name) in collections.items():
        rgb_dir, thermal_dir = root / rgb_name, root / thermal_name
        if rgb_dir.is_dir() and thermal_dir.is_dir():
            grouped[cid] = (rgb_dir, thermal_dir)
    return grouped


def _pair_collection(
    rgb_dir: Path, thermal_dir: Path, collection_id: str
) -> tuple[list[ImagePair], CollectionCounts]:
    """Pair the images of one collection by equal frame number.

    Returns every pair, labelled or not, and counts of frames in each
    directory, of pairs, and of frames that have no partner.
    """
    rgb_by_frame = _frames_by_index(rgb_dir)
    thermal_by_frame = _frames_by_index(thermal_dir)
    if not rgb_by_frame or not thermal_by_frame:
        raise ValueError(
            f"Expected non-empty RGB and thermal collections for "
            f"{collection_id}, got {len(rgb_by_frame)} RGB and "
            f"{len(thermal_by_frame)} thermal"
        )

    common_frames = sorted(set(rgb_by_frame) & set(thermal_by_frame))
    smaller = min(len(rgb_by_frame), len(thermal_by_frame))
    if len(common_frames) < MIN_SHARED_FRAMES * smaller:
        raise ValueError(
            f"{collection_id}: only {len(common_frames)} of {smaller} frame "
            f"numbers appear in both {rgb_dir.name} and {thermal_dir.name}; "
            f"the directories do not share a frame numbering"
        )

    pairs = []
    for frame in common_frames:
        rgb_image = rgb_by_frame[frame]
        thermal_image = thermal_by_frame[frame]
        pairs.append(
            ImagePair(
                collection_id,
                rgb_image,
                thermal_image,
                rgb_image.with_suffix(".txt"),
                thermal_image.with_suffix(".txt"),
            )
        )
    counts: CollectionCounts = {
        "rgb_dir": rgb_dir.name,
        "thermal_dir": thermal_dir.name,
        "rgb_frames": len(rgb_by_frame),
        "thermal_frames": len(thermal_by_frame),
        "pairs": len(pairs),
        "labelled_pairs": sum(_is_labelled(pair) for pair in pairs),
        "rgb_only_frames": len(rgb_by_frame) - len(common_frames),
        "thermal_only_frames": len(thermal_by_frame) - len(common_frames),
    }
    return pairs, counts


def _is_labelled(pair: ImagePair) -> bool:
    return pair.rgb_labels.exists() and pair.thermal_labels.exists()


def load_pairs(
    root: Path,
    stats: dict[str, int] | None = None,
    *,
    labelled_only: bool = True,
    collections: Collections = WISARD_COLLECTIONS,
) -> list[ImagePair]:
    """Return synchronized pairs from the listed collections under root.

    With labelled_only, pairs without a label file in both modalities are left
    out, and counted in stats["frames_skipped"] if stats is given.
    """
    pairs: list[ImagePair] = []
    for cid, (rgb_dir, thermal_dir) in _group_collections(root, collections).items():
        for pair in _pair_collection(rgb_dir, thermal_dir, cid)[0]:
            if labelled_only and not _is_labelled(pair):
                if stats is not None:
                    stats["frames_skipped"] = stats.get("frames_skipped", 0) + 1
                continue
            pairs.append(pair)
    return pairs


def pairing_report(
    root: Path, collections: Collections = WISARD_COLLECTIONS
) -> PairingReport:
    """Describe how the image directories under root were paired.

    Gives counts per collection, the listed collections whose directories are
    missing, and every image directory that was not paired.
    """
    grouped = _group_collections(root, collections)
    per_collection = {
        cid: _pair_collection(rgb_dir, thermal_dir, cid)[1]
        for cid, (rgb_dir, thermal_dir) in grouped.items()
    }
    used = {path.name for dirs in grouped.values() for path in dirs}
    unpaired = sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and path.name not in used and any(path.glob("*.jp*g"))
    )
    return {
        "collections": per_collection,
        "missing_collections": sorted(set(collections) - set(grouped)),
        "unpaired_directories": unpaired,
    }


def load_boxes(path: Path, stats: dict[str, int] | None = None) -> list[BoundingBox]:
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
            stats["boxes_clamped"] = stats.get("boxes_clamped", 0) + 1
        boxes.append(BoundingBox(*clamped))
    return boxes


def load_pairs_by_collection(
    root: Path,
    stats: dict[str, int] | None = None,
    *,
    collections: Collections = WISARD_COLLECTIONS,
) -> dict[str, list[ImagePair]]:
    """Return labelled pairs grouped by collection_id."""
    grouped: dict[str, list[ImagePair]] = {}
    for pair in load_pairs(root, stats=stats, collections=collections):
        grouped.setdefault(pair.collection_id, []).append(pair)
    return grouped


def prepare_manifests(
    source: Path,
    destination: Path,
    *,
    train_fraction: float = 0.7,
    validation_fraction: float = 0.15,
    seed: int = 7,
    collections: Collections = WISARD_COLLECTIONS,
) -> dict[str, int]:
    """Write all-pairs manifest + labeled-only splits.

    Steps:
    1. Pair every listed collection and write all_pairs.jsonl
    2. Keep the labelled pairs and write full.jsonl
    3. Split labeled pairs via seeded greedy bin-filling, write train/validation/test
    4. Write data_quality.json with counts per collection and the directories
       that were not paired

    Note: all_pairs.jsonl includes frames without annotations (good for SSL).
    full.jsonl includes only labeled frames (for detection fine-tuning).
    """
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must leave a test split")

    destination.mkdir(parents=True, exist_ok=True)

    # First: write all pairs (labeled + unlabeled) for SSL
    all_pairs_unlabeled = load_pairs(
        source, labelled_only=False, collections=collections
    )
    all_pairs_manifest = destination / "all_pairs.jsonl"
    with all_pairs_manifest.open("w") as output:
        for pair in all_pairs_unlabeled:
            output.write(
                json.dumps(
                    {
                        "collection_id": pair.collection_id,
                        "rgb_image": str(pair.rgb_image.relative_to(source)),
                        "thermal_image": str(pair.thermal_image.relative_to(source)),
                    }
                )
                + "\n"
            )
    print(f"Wrote {len(all_pairs_unlabeled):,} pairs to all_pairs.jsonl")

    # Second: write labeled pairs only for detection
    stats: dict[str, int] = {}
    all_pairs = [pair for pair in all_pairs_unlabeled if _is_labelled(pair)]
    stats["frames_skipped"] = len(all_pairs_unlabeled) - len(all_pairs)
    by_collection: dict[str, list[ImagePair]] = {}
    for pair in all_pairs:
        by_collection.setdefault(pair.collection_id, []).append(pair)

    # Write full labeled dataset manifest
    full_manifest = destination / "full.jsonl"
    with full_manifest.open("w") as output:
        for pair in all_pairs:
            output.write(json.dumps(_pair_record(pair, source, stats=stats)) + "\n")
    print(f"Wrote {len(all_pairs):,} labelled pairs to full.jsonl")

    # Then split labeled pairs for train/validation/test
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

    for name, split_pairs in splits.items():
        manifest = destination / f"{name}.jsonl"
        with manifest.open("w") as output:
            for pair in split_pairs:
                output.write(json.dumps(_pair_record(pair, source, stats=stats)) + "\n")

    # Write data quality log
    report = pairing_report(source, collections)
    quality_log = destination / "data_quality.json"
    with quality_log.open("w") as f:
        json.dump(
            {
                "total_pairs": len(all_pairs_unlabeled),
                "labeled_pairs": len(all_pairs),
                "frames_skipped": stats["frames_skipped"],
                "boxes_clamped": stats.get("boxes_clamped", 0),
                **report,
            },
            f,
            indent=2,
        )

    return {name: len(split_pairs) for name, split_pairs in splits.items()}


def _pair_record(
    pair: ImagePair, source: Path, stats: dict[str, int] | None = None
) -> dict[str, object]:
    return {
        "collection_id": pair.collection_id,
        "rgb_image": str(pair.rgb_image.relative_to(source)),
        "thermal_image": str(pair.thermal_image.relative_to(source)),
        "rgb_boxes": [box.__dict__ for box in load_boxes(pair.rgb_labels, stats=stats)],
        "thermal_boxes": [
            box.__dict__ for box in load_boxes(pair.thermal_labels, stats=stats)
        ],
    }
