"""Measure how fast neighbouring frames of a clip stop looking alike.

Used to choose the gap between training and validation frames inside one clip
(docs/site-folds-review.md). Each frame is shrunk to a 64x36 grey thumbnail,
centred, and scaled to unit length; the similarity of two frames is the dot
product of their thumbnails (a correlation, 1 for identical frames). For each
lag k, the table gives the mean similarity of frames k apart in the clip. Two
reference rows: random pairs of frames from the same clip, and random pairs
from two different site-days.

    uv run python tools/frame_similarity_lags.py data/raw/wisard-full \
        data/manifests/wisard-full/all_pairs.jsonl

Takes about a minute on an M4 laptop.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image

LAGS = (1, 2, 5, 10, 25, 50, 100, 150, 200, 250, 300)
CLIPS = (
    "220109_Baker_Enterprise_1",
    "210529_Carnation_Enterprise_0023",
    "210417_MtErie_Enterprise_0005",
    "210924_FHL_Enterprise_0401",
)
SAMPLES = 2000
SEED = 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path)
    parser.add_argument("all_pairs", type=Path)
    args = parser.parse_args()

    images: dict[tuple[str, str], list[str]] = {}
    for line in args.all_pairs.read_text().splitlines():
        record = json.loads(line)
        if record["collection_id"] in CLIPS:
            for camera in ("rgb", "thermal"):
                key = (record["collection_id"], camera)
                images.setdefault(key, []).append(record[f"{camera}_image"])

    rng = random.Random(SEED)
    print("| Clip | Camera | Frames | " + " | ".join(f"{k}" for k in LAGS), end="")
    print(" | Random pair, same clip |")
    print("|---" * (len(LAGS) + 4) + "|")
    thumbs = {}
    for (clip, camera), paths in images.items():
        stack = np.stack([_thumbnail(args.source / p) for p in paths])
        thumbs[clip, camera] = stack
        cells = [
            f"{np.mean(np.sum(stack[:-k] * stack[k:], axis=1)):.2f}"
            if k < len(stack)
            else "-"
            for k in LAGS
        ]
        same = _random_pairs(stack, stack, rng)
        print(f"| {clip} | {camera} | {len(stack)} | " + " | ".join(cells), end="")
        print(f" | {same:.2f} |")
    for camera in ("rgb", "thermal"):
        other = _random_pairs(thumbs[CLIPS[0], camera], thumbs[CLIPS[1], camera], rng)
        print(f"Random pair, {CLIPS[0]} with {CLIPS[1]}, {camera}: {other:.2f}")


def _thumbnail(path: Path) -> np.ndarray:
    image = Image.open(path)
    image.draft("L", (160, 90))
    grey = np.asarray(image.convert("L").resize((64, 36)), dtype=np.float64).ravel()
    grey -= grey.mean()
    return grey / (np.linalg.norm(grey) + 1e-9)


def _random_pairs(a: np.ndarray, b: np.ndarray, rng: random.Random) -> float:
    picks = [(rng.randrange(len(a)), rng.randrange(len(b))) for _ in range(SAMPLES)]
    return float(np.mean([a[i] @ b[j] for i, j in picks]))


if __name__ == "__main__":
    main()
