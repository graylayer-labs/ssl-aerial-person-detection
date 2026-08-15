"""Analyze dataset diversity and generate exploration reports."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from aerial_search.data.wisard import (
    ImagePair,
    load_boxes,
    load_pairs_by_collection,
)


@dataclass(frozen=True)
class CollectionStats:
    """Statistics for one flight collection."""

    collection_id: str
    date: str | None
    site: str | None
    platform: str | None
    num_pairs: int
    total_rgb_boxes: int
    total_thermal_boxes: int
    mean_rgb_boxes_per_image: float
    mean_thermal_boxes_per_image: float
    box_count_agreement_rate: float
    mean_rgb_brightness: float
    mean_thermal_brightness: float


def parse_collection_metadata(
    collection_id: str,
) -> tuple[str | None, str | None, str | None]:
    """Extract date, site, platform from collection_id.

    Expects format like '20240104_SiteName_Platform'.
    Returns (date, site, platform) or (None, None, None) if parsing fails.
    """
    parts = collection_id.split("_")
    if len(parts) < 1:
        return None, None, None
    date = parts[0] if len(parts[0]) == 8 and parts[0].isdigit() else None
    site = parts[1] if len(parts) > 1 else None
    platform = parts[2] if len(parts) > 2 else None
    return date, site, platform


def compute_collection_stats(
    collection_id: str,
    pairs: list[ImagePair],
    *,
    sample_size: int = 20,
    seed: int = 7,
) -> CollectionStats:
    """Compute statistics for a single collection from a seeded sample of pairs."""
    if not pairs:
        return CollectionStats(
            collection_id=collection_id,
            date=None,
            site=None,
            platform=None,
            num_pairs=0,
            total_rgb_boxes=0,
            total_thermal_boxes=0,
            mean_rgb_boxes_per_image=0.0,
            mean_thermal_boxes_per_image=0.0,
            box_count_agreement_rate=0.0,
            mean_rgb_brightness=0.0,
            mean_thermal_brightness=0.0,
        )

    date, site, platform = parse_collection_metadata(collection_id)

    rng = random.Random(seed)
    sample = rng.sample(pairs, min(sample_size, len(pairs)))

    rgb_brightness = []
    thermal_brightness = []
    rgb_box_counts = []
    thermal_box_counts = []
    agreement_count = 0

    for pair in sample:
        # Load brightness from images
        try:
            rgb_img = Image.open(pair.rgb_image).convert("L")
            rgb_brightness.append(float(np.asarray(rgb_img).mean()))
        except Exception:
            pass

        try:
            thermal_img = Image.open(pair.thermal_image).convert("L")
            thermal_brightness.append(float(np.asarray(thermal_img).mean()))
        except Exception:
            pass

        # Load box counts
        try:
            rgb_boxes = load_boxes(pair.rgb_labels)
            thermal_boxes = load_boxes(pair.thermal_labels)
            rgb_count = len(rgb_boxes)
            thermal_count = len(thermal_boxes)
            rgb_box_counts.append(rgb_count)
            thermal_box_counts.append(thermal_count)
            if rgb_count == thermal_count:
                agreement_count += 1
        except Exception:
            pass

    # Aggregate across entire collection
    total_rgb_boxes = sum(
        len(load_boxes(pair.rgb_labels))
        for pair in pairs
        if pair.rgb_labels.exists()
    )
    total_thermal_boxes = sum(
        len(load_boxes(pair.thermal_labels))
        for pair in pairs
        if pair.thermal_labels.exists()
    )

    return CollectionStats(
        collection_id=collection_id,
        date=date,
        site=site,
        platform=platform,
        num_pairs=len(pairs),
        total_rgb_boxes=total_rgb_boxes,
        total_thermal_boxes=total_thermal_boxes,
        mean_rgb_boxes_per_image=total_rgb_boxes / len(pairs) if pairs else 0.0,
        mean_thermal_boxes_per_image=total_thermal_boxes / len(pairs) if pairs else 0.0,
        box_count_agreement_rate=(agreement_count / len(sample)) if sample else 0.0,
        mean_rgb_brightness=(
            np.mean(rgb_brightness) if rgb_brightness else 0.0
        ),
        mean_thermal_brightness=(
            np.mean(thermal_brightness) if thermal_brightness else 0.0
        ),
    )


def extract_thumbnails(
    collection_id: str,
    pairs: list[ImagePair],
    output_dir: Path,
    *,
    count: int = 2,
    max_dimension: int = 320,
    quality: int = 70,
) -> list[Path]:
    """Extract evenly-spaced representative image pairs as small thumbnails."""
    if not pairs:
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    collection_dir = output_dir / collection_id
    collection_dir.mkdir(exist_ok=True)

    # Pick evenly-spaced pairs (deterministic, not random)
    indices = [int(i * len(pairs) / count) for i in range(count)]
    indices = [min(idx, len(pairs) - 1) for idx in indices]

    saved_paths = []
    for idx, pair_idx in enumerate(indices):
        pair = pairs[pair_idx]
        try:
            # RGB thumbnail
            rgb_img = Image.open(pair.rgb_image)
            rgb_img.thumbnail((max_dimension, max_dimension))
            rgb_path = collection_dir / f"{idx:02d}_rgb.jpg"
            rgb_img.save(rgb_path, quality=quality, optimize=True)
            saved_paths.append(rgb_path)

            # Thermal thumbnail
            thermal_img = Image.open(pair.thermal_image)
            thermal_img.thumbnail((max_dimension, max_dimension))
            thermal_path = collection_dir / f"{idx:02d}_thermal.jpg"
            thermal_img.save(thermal_path, quality=quality, optimize=True)
            saved_paths.append(thermal_path)
        except Exception:
            pass

    return saved_paths


def build_diversity_report(
    root: Path,
    report_path: Path,
    thumbnails_dir: Path,
    *,
    samples_per_collection: int = 20,
    thumbnails_per_collection: int = 2,
    seed: int = 7,
) -> None:
    """Generate a Markdown diversity report for the dataset."""
    by_collection = load_pairs_by_collection(root)

    if not by_collection:
        report_path.write_text("# WiSARD Diversity Report\n\nNo collections found.\n")
        return

    stats_list: list[CollectionStats] = []
    for collection_id in sorted(by_collection.keys()):
        pairs = by_collection[collection_id]
        stats = compute_collection_stats(
            collection_id, pairs, sample_size=samples_per_collection, seed=seed
        )
        stats_list.append(stats)
        extract_thumbnails(
            collection_id,
            pairs,
            thumbnails_dir,
            count=thumbnails_per_collection,
        )

    # Build Markdown report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# WiSARD Dataset Diversity Report",
        "",
        "## Overview",
        "",
        f"- **Total collections**: {len(stats_list)}",
        f"- **Total image pairs**: {sum(s.num_pairs for s in stats_list)}",
        f"- **Total RGB boxes**: {sum(s.total_rgb_boxes for s in stats_list)}",
        f"- **Total thermal boxes**: {sum(s.total_thermal_boxes for s in stats_list)}",
        "",
        "## Collection Details",
        "",
        (
            "| Collection ID | Date | Site | Platform | Pairs | RGB Boxes | "
            "Thermal Boxes | RGB/Image | Thermal/Image | Agreement | "
            "RGB Brightness | Thermal Brightness |"
        ),
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for stats in stats_list:
        date_str = stats.date or "N/A"
        site_str = stats.site or "N/A"
        platform_str = stats.platform or "N/A"
        lines.append(
            f"| `{stats.collection_id}` | {date_str} | {site_str} | "
            f"{platform_str} | {stats.num_pairs} | {stats.total_rgb_boxes} | "
            f"{stats.total_thermal_boxes} | {stats.mean_rgb_boxes_per_image:.2f} | "
            f"{stats.mean_thermal_boxes_per_image:.2f} | "
            f"{stats.box_count_agreement_rate:.1%} | {stats.mean_rgb_brightness:.1f} | "
            f"{stats.mean_thermal_brightness:.1f} |"
        )

    # Aggregate row
    total_pairs = sum(s.num_pairs for s in stats_list)
    total_rgb_boxes = sum(s.total_rgb_boxes for s in stats_list)
    total_thermal_boxes = sum(s.total_thermal_boxes for s in stats_list)
    mean_rgb_per_image = total_rgb_boxes / total_pairs if total_pairs else 0
    mean_thermal_per_image = total_thermal_boxes / total_pairs if total_pairs else 0
    avg_agreement = np.mean([s.box_count_agreement_rate for s in stats_list])
    avg_rgb_brightness = np.mean([s.mean_rgb_brightness for s in stats_list])
    avg_thermal_brightness = np.mean([s.mean_thermal_brightness for s in stats_list])

    lines.append(
        f"| **Total** | — | — | — | {total_pairs} | {total_rgb_boxes} | "
        f"{total_thermal_boxes} | {mean_rgb_per_image:.2f} | "
        f"{mean_thermal_per_image:.2f} | {avg_agreement:.1%} | "
        f"{avg_rgb_brightness:.1f} | {avg_thermal_brightness:.1f} |"
    )

    # Sample images section
    lines.extend(
        [
            "",
            "## Sample Images",
            "",
            "Representative synchronized RGB–thermal pairs from each collection:",
            "",
        ]
    )

    for stats in stats_list:
        collection_thumbnails_dir = thumbnails_dir / stats.collection_id
        if collection_thumbnails_dir.exists():
            lines.append(f"### {stats.collection_id}")
            lines.append("")
            for thumb_idx in range(thumbnails_per_collection):
                rgb_thumb = collection_thumbnails_dir / f"{thumb_idx:02d}_rgb.jpg"
                thermal_thumb = (
                    collection_thumbnails_dir / f"{thumb_idx:02d}_thermal.jpg"
                )
                if rgb_thumb.exists() and thermal_thumb.exists():
                    # Compute relative path with walk_up=True for siblings
                    rgb_rel = rgb_thumb.relative_to(report_path.parent, walk_up=True)
                    thermal_rel = thermal_thumb.relative_to(
                        report_path.parent, walk_up=True
                    )
                    lines.append(f"**Frame {thumb_idx}**")
                    lines.append("")
                    lines.append("| RGB | Thermal |")
                    lines.append("|---|---|")
                    lines.append(f"| ![RGB]({rgb_rel}) | ![Thermal]({thermal_rel}) |")
                    lines.append("")

    report_path.write_text("\n".join(lines))
