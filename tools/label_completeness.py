"""Estimate how many visible people have no label in WiSARD.

Two steps, both deterministic given the seed.

    # 1. draw the sample and write one review sheet per frame, plus tally.json
    uv run python tools/label_completeness.py sample data/raw/wisard-full \
        data/manifests/wisard-full outputs/label-check --seed 37

    # 2. after review.json is filled in, compute the estimates
    uv run python tools/label_completeness.py summarise \
        data/manifests/wisard-full outputs/label-check

The sample takes the same number of frames from every (camera, clip) stratum,
chosen at random, empty label files included. Each sheet shows the whole frame
with its boxes in red, and below it a zoomed crop of each quarter.

`review.json` is written by the reviewer, not by this script, and is never
overwritten here. It maps a frame's image path to
`{"missed": int, "confidence": "sure" | "unsure", "note": str}`, where `missed`
is the number of visible people with no box (for an unsure frame, the number
of candidates).
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

CAMERAS = ("rgb", "thermal")
PANEL_WIDTH = 1536  # width of the overview and of the 2x2 grid of quarters
HEADER = 36


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default)."""
    if n == 0:
        return (math.nan, math.nan)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def load_labelled(manifests: Path, camera: str) -> dict[str, list[dict]]:
    """Frames of one camera by clip, sorted by image path."""
    clips: dict[str, list[dict]] = defaultdict(list)
    for line in (manifests / f"{camera}_labelled.jsonl").read_text().splitlines():
        record = json.loads(line)
        clips[record["collection_id"]].append(record)
    return {clip: sorted(f, key=lambda r: r["image"]) for clip, f in clips.items()}


def draw_sample(
    manifests: Path, seed: int, per_stratum: int
) -> list[dict[str, object]]:
    """Simple random sample of `per_stratum` frames from every camera and clip."""
    sample: list[dict[str, object]] = []
    for camera in CAMERAS:
        for clip, frames in sorted(load_labelled(manifests, camera).items()):
            rng = random.Random(f"{seed}/{camera}/{clip}")
            for record in rng.sample(frames, min(per_stratum, len(frames))):
                sample.append(
                    {
                        "id": f"{camera}_{len(sample):03d}",
                        "camera": camera,
                        "clip": clip,
                        "image": record["image"],
                        "n_boxes": len(record["boxes"]),
                        "boxes": record["boxes"],
                        "clip_frames": len(frames),
                    }
                )
    return sample


def make_sheet(source: Path, entry: dict, out: Path) -> None:
    image = Image.open(source / entry["image"]).convert("RGB")
    w, h = image.size
    scale = PANEL_WIDTH / w
    # Upscale first for thermal (640 px wide): crops are cut from this canvas.
    canvas = image.resize((PANEL_WIDTH, round(h * scale)), Image.LANCZOS)
    cw, ch = canvas.size
    draw = ImageDraw.Draw(canvas)
    for b in entry["boxes"]:
        x0 = (b["x_center"] - b["width"] / 2) * cw
        y0 = (b["y_center"] - b["height"] / 2) * ch
        x1 = (b["x_center"] + b["width"] / 2) * cw
        y1 = (b["y_center"] + b["height"] / 2) * ch
        draw.rectangle((x0, y0, x1, y1), outline=(255, 0, 0), width=2)

    # Quarters are cut from the original pixels so that no detail is lost, then
    # drawn with boxes at the same scale as the overview.
    qw, qh = cw // 2, ch // 2
    sheet = Image.new("RGB", (cw, HEADER + ch + ch), (30, 30, 30))
    sheet.paste(canvas, (0, HEADER))
    for i, (qx, qy) in enumerate([(0, 0), (1, 0), (0, 1), (1, 1)]):
        sx0, sy0 = round(qx * w / 2), round(qy * h / 2)
        crop = image.crop((sx0, sy0, round((qx + 1) * w / 2), round((qy + 1) * h / 2)))
        crop = crop.resize((qw, qh), Image.LANCZOS)
        cd = ImageDraw.Draw(crop)
        for b in entry["boxes"]:
            x0 = (b["x_center"] - b["width"] / 2) * w
            y0 = (b["y_center"] - b["height"] / 2) * h
            x1 = (b["x_center"] + b["width"] / 2) * w
            y1 = (b["y_center"] + b["height"] / 2) * h
            k = qw / (w / 2)
            cd.rectangle(
                ((x0 - sx0) * k, (y0 - sy0) * k, (x1 - sx0) * k, (y1 - sy0) * k),
                outline=(255, 0, 0),
                width=2,
            )
        sheet.paste(crop, (qx * qw, HEADER + ch + qy * qh))
    ImageDraw.Draw(sheet).text(
        (8, 10),
        f"{entry['id']}  {entry['clip']}  {entry['n_boxes']} boxes (red)  "
        f"{entry['image'].rsplit('/', 1)[-1]}",
        fill=(255, 255, 255),
    )
    sheet.save(out, quality=90)


def cmd_sample(args: argparse.Namespace) -> None:
    sample = draw_sample(args.manifests, args.seed, args.per_stratum)
    args.output.mkdir(parents=True, exist_ok=True)
    for entry in sample:
        make_sheet(args.source, entry, args.output / f"{entry['id']}.jpg")
    tally = {
        "seed": args.seed,
        "per_stratum": args.per_stratum,
        "n_frames": len(sample),
        "frames": sample,
    }
    (args.output / "tally.json").write_text(json.dumps(tally, indent=1))
    print(f"{len(sample)} sheets and tally.json in {args.output}")


def summarise_camera(
    frames: list[dict], review: dict[str, dict], clip_sizes: dict[str, int]
) -> dict[str, object]:
    sure = [f for f in frames if review[f["image"]]["confidence"] == "sure"]
    unsure = [f for f in frames if review[f["image"]]["confidence"] != "sure"]
    with_miss = sum(1 for f in sure if review[f["image"]]["missed"] > 0)
    missed = sum(review[f["image"]]["missed"] for f in sure)
    labelled = sum(f["n_boxes"] for f in sure)
    lo, hi = wilson(with_miss, len(sure))
    p_lo, p_hi = wilson(missed, missed + labelled)

    # Sensitivity: every unsure frame counted as clean, or as having a miss.
    n = len(frames)
    all_clean = wilson(with_miss, n)
    all_miss = wilson(with_miss + len(unsure), n)

    # Clip-size weighted share (the sample takes equal numbers per clip).
    weights, shares = [], []
    for clip in sorted({f["clip"] for f in sure}):
        cf = [f for f in sure if f["clip"] == clip]
        shares.append(
            sum(1 for f in cf if review[f["image"]]["missed"] > 0) / len(cf)
        )
        weights.append(clip_sizes[clip])
    weighted = sum(w * s for w, s in zip(weights, shares)) / sum(weights)

    per_clip = {}
    for clip in sorted({f["clip"] for f in frames}):
        cf = [f for f in frames if f["clip"] == clip]
        cs = [f for f in cf if review[f["image"]]["confidence"] == "sure"]
        per_clip[clip] = {
            "frames": len(cf),
            "unsure": len(cf) - len(cs),
            "sure_with_miss": sum(1 for f in cs if review[f["image"]]["missed"] > 0),
            "missed": sum(review[f["image"]]["missed"] for f in cs),
            "labelled": sum(f["n_boxes"] for f in cs),
        }
    return {
        "frames_sampled": n,
        "frames_empty_label": sum(1 for f in frames if f["n_boxes"] == 0),
        "frames_unsure": len(unsure),
        "frames_sure": len(sure),
        "sure_frames_with_miss": with_miss,
        "frame_share": with_miss / len(sure) if sure else math.nan,
        "frame_share_ci95_wilson": [lo, hi],
        "frame_share_weighted_by_clip_size": weighted,
        "frame_share_if_unsure_all_clean_ci95": list(all_clean),
        "frame_share_if_unsure_all_missed_ci95": list(all_miss),
        "people_missed": missed,
        "people_labelled": labelled,
        "people_missing_share": missed / (missed + labelled)
        if missed + labelled
        else math.nan,
        "people_missing_share_ci95_wilson_naive": [p_lo, p_hi],
        "per_clip": per_clip,
    }


def cmd_summarise(args: argparse.Namespace) -> None:
    tally = json.loads((args.output / "tally.json").read_text())
    review = json.loads((args.output / "review.json").read_text())
    missing = [f["image"] for f in tally["frames"] if f["image"] not in review]
    if missing:
        raise SystemExit(f"{len(missing)} sampled frames have no review entry")
    result = {"seed": tally["seed"]}
    for camera in CAMERAS:
        frames = [f for f in tally["frames"] if f["camera"] == camera]
        sizes = {c: len(v) for c, v in load_labelled(args.manifests, camera).items()}
        result[camera] = summarise_camera(frames, review, sizes)
    (args.output / "summary.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sample", help="draw the sample and write the sheets")
    s.add_argument("source", type=Path, help="dataset root, e.g. data/raw/wisard-full")
    s.add_argument("manifests", type=Path, help="e.g. data/manifests/wisard-full")
    s.add_argument("output", type=Path, help="directory for sheets and tally.json")
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--per-stratum", type=int, default=9, help="frames per camera+clip")
    s.set_defaults(func=cmd_sample)
    t = sub.add_parser("summarise", help="compute estimates from review.json")
    t.add_argument("manifests", type=Path)
    t.add_argument("output", type=Path, help="directory holding tally.json")
    t.set_defaults(func=cmd_summarise)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
