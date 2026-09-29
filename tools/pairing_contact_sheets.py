"""Draw contact sheets that show whether RGB-thermal pairs are aligned.

One JPEG per collection: pairs sampled from the start, middle, and end of the
collection, RGB beside thermal, label boxes drawn, filenames printed under
each pair. Look at them before trusting a manifest.

    # every collection in a manifest
    uv run python tools/pairing_contact_sheets.py \
        data/raw/wisard-full data/manifests/wisard-full/all_pairs.jsonl \
        outputs/pairing-check

    # one VIS/IR directory pair matched on equal frame numbers (e.g. to see why
    # a flight was excluded)
    uv run python tools/pairing_contact_sheets.py data/raw/wisard-full \
        --pair 210327_Airfield_FLIR_VIS_4 210327_Airfield_FLIR_IR_4 \
        outputs/pairing-check
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

from aerial_search.data.wisard import _frames_by_index

ROW_HEIGHT = 240
CAPTION = 34
SAMPLES_PER_PART = 2  # two pairs each from start, middle, end


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="dataset root, e.g. data/raw/...")
    parser.add_argument("manifest", type=Path, nargs="?", help="all_pairs.jsonl")
    parser.add_argument("output", type=Path, help="directory for the sheets")
    parser.add_argument("--pair", nargs=2, metavar=("VIS_DIR", "IR_DIR"))
    args = parser.parse_args()

    collections: dict[str, list[tuple[Path, Path]]] = defaultdict(list)
    if args.pair:
        rgb = _frames_by_index(args.source / args.pair[0])
        thermal = _frames_by_index(args.source / args.pair[1])
        name = f"UNVERIFIED_{args.pair[0]}__{args.pair[1]}"
        collections[name] = [
            (rgb[i], thermal[i]) for i in sorted(set(rgb) & set(thermal))
        ]
    elif args.manifest:
        for line in args.manifest.read_text().splitlines():
            record = json.loads(line)
            collections[record["collection_id"]].append(
                (
                    args.source / record["rgb_image"],
                    args.source / record["thermal_image"],
                )
            )
    else:
        parser.error("give a manifest or --pair")

    args.output.mkdir(parents=True, exist_ok=True)
    for name, pairs in sorted(collections.items()):
        sheet = _sheet(_sample(pairs))
        path = args.output / f"{name}.jpg"
        sheet.save(path, quality=80)
        print(f"{path}  ({len(pairs)} pairs)")


def _sample(pairs: list[tuple[Path, Path]]) -> list[tuple[Path, Path]]:
    """Pick pairs from the start, middle, and end, preferring ones with boxes."""
    n = len(pairs)
    chosen: list[tuple[Path, Path]] = []
    for part in range(3):
        lo, hi = part * n // 3, (part + 1) * n // 3
        window = pairs[lo:hi]
        with_boxes = [p for p in window if _boxes(p[0]) and _boxes(p[1])]
        pool = with_boxes if len(with_boxes) >= SAMPLES_PER_PART else window
        if part == 0:
            picks = pool[:SAMPLES_PER_PART]
        elif part == 2:
            picks = pool[-SAMPLES_PER_PART:]
        else:
            mid = len(pool) // 2
            picks = pool[mid : mid + SAMPLES_PER_PART]
        chosen.extend(picks)
    return chosen


def _sheet(pairs: list[tuple[Path, Path]]) -> Image.Image:
    rows = [_row(rgb, thermal) for rgb, thermal in pairs]
    width = max(row.width for row in rows)
    sheet = Image.new("RGB", (width, sum(row.height for row in rows)), "white")
    y = 0
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height
    return sheet


def _row(rgb: Path, thermal: Path) -> Image.Image:
    left, right = _panel(rgb), _panel(thermal)
    row = Image.new(
        "RGB", (left.width + right.width + 6, ROW_HEIGHT + CAPTION), "white"
    )
    row.paste(left, (0, 0))
    row.paste(right, (left.width + 6, 0))
    draw = ImageDraw.Draw(row)
    draw.text((2, ROW_HEIGHT + 2), f"RGB: {rgb.parent.name}/{rgb.name}", fill="black")
    draw.text(
        (2, ROW_HEIGHT + 17),
        f"IR:  {thermal.parent.name}/{thermal.name}",
        fill="black",
    )
    return row


def _panel(path: Path) -> Image.Image:
    image = Image.open(path)
    image.draft("RGB", (image.width // 4, image.height // 4))
    image = image.convert("RGB")
    width = round(image.width * ROW_HEIGHT / image.height)
    image = image.resize((width, ROW_HEIGHT))
    draw = ImageDraw.Draw(image)
    for x, y, w, h in _boxes(path):
        draw.rectangle(
            [
                ((x - w / 2) * width, (y - h / 2) * ROW_HEIGHT),
                ((x + w / 2) * width, (y + h / 2) * ROW_HEIGHT),
            ],
            outline=(255, 0, 0),
            width=2,
        )
    return image


def _boxes(image: Path) -> list[tuple[float, float, float, float]]:
    labels = image.with_suffix(".txt")
    if not labels.exists():
        return []
    boxes = []
    for line in labels.read_text().splitlines():
        fields = line.split()
        if len(fields) == 5:
            x, y, w, h = (float(v) for v in fields[1:])
            boxes.append((x, y, w, h))
    return boxes


if __name__ == "__main__":
    main()
