"""Score person detections for search and rescue.

The metric choice is explained in ``docs/evaluation-metric-review.md``.

Input format
    Boxes are ``(x1, y1, x2, y2)`` in pixels, origin at the top-left corner of
    the image, in continuous coordinates: the far edge is exclusive, so a box
    covering pixel columns 5 to 9 is ``x1=5, x2=10`` and has width 5. Labels
    stored as inclusive pixel indices must add 1 to ``x2`` and ``y2``.

Matching (pycocotools, computed per image and per IoU threshold)
    Detections are taken in descending score order. Each takes the unmatched
    person with the highest IoU, provided that IoU is at least the threshold
    (equal counts). A person can be matched once, so a second detection of the
    same person is a false alarm. Equal IoU goes to the person listed later.

Ties in score
    Average precision follows pycocotools: a stable sort, so equal scores keep
    image order, then the order detections were given in. Recall at false
    alarms per image treats equal scores as one operating point, because no
    score threshold can separate them.
"""

from __future__ import annotations

import io
import json
import math
from collections.abc import Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import ArrayLike
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

PRIMARY_IOU = 0.25
COCO_IOUS = tuple(round(0.5 + 0.05 * i, 2) for i in range(10))
IOU_THRESHOLDS = (PRIMARY_IOU, *COCO_IOUS)
FPPI_POINTS = (0.01, 0.1, 1.0)
# Buckets on sqrt(box area) in pixels, half-open [low, high). The edges follow
# AI-TOD; the first starts at 0 and the last is open so no person is dropped.
SIZE_BUCKETS: dict[str, tuple[float, float]] = {
    "very_tiny": (0.0, 8.0),
    "tiny": (8.0, 16.0),
    "small": (16.0, 32.0),
    "medium_plus": (32.0, math.inf),
}
METRICS_FILENAME = "detection_metrics.json"

# Exact k/100. pycocotools' default np.linspace grid is off by one ulp at ten
# levels (0.35, 0.41, ...), so a recall of exactly 0.7 would miss level 0.70.
_RECALL_LEVELS = np.arange(101) / 100
_ALL = "all"
_PERSON = 1


def _as_boxes(boxes: Any) -> np.ndarray:
    array = np.asarray(boxes, dtype=np.float64)
    if array.size == 0:
        return np.zeros((0, 4))
    if array.ndim != 2 or array.shape[1] != 4:
        raise ValueError(f"boxes must have shape (N, 4), got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError("every box coordinate must be finite")
    if not ((array[:, 2] > array[:, 0]) & (array[:, 3] > array[:, 1])).all():
        raise ValueError("every box needs x2 > x1 and y2 > y1")
    return array


def _areas(boxes: ArrayLike) -> np.ndarray:
    b = np.asarray(boxes)
    return (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])


@dataclass(frozen=True, eq=False)
class GroundTruth:
    """The people in one image. An image with no people has no boxes.

    ``boxes`` is stored as a float64 array of shape (N, 4).
    """

    image_id: str
    boxes: ArrayLike
    modality: str
    flight: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "boxes", _as_boxes(self.boxes))
        if not self.modality or not self.flight:
            raise ValueError(f"image {self.image_id!r} needs a modality and flight")


@dataclass(frozen=True, eq=False)
class Prediction:
    """A model's detections for one image, one score per box.

    Stored as float64 arrays: ``boxes`` (N, 4) and ``scores`` (N,).
    """

    image_id: str
    boxes: ArrayLike
    scores: ArrayLike

    def __post_init__(self) -> None:
        boxes = _as_boxes(self.boxes)
        scores = np.asarray(self.scores, dtype=np.float64).reshape(-1)
        if scores.shape[0] != boxes.shape[0]:
            raise ValueError(
                f"image {self.image_id!r}: {boxes.shape[0]} boxes but "
                f"{scores.shape[0]} scores"
            )
        if not np.isfinite(scores).all():
            raise ValueError(f"image {self.image_id!r}: scores must be finite")
        object.__setattr__(self, "boxes", boxes)
        object.__setattr__(self, "scores", scores)


@dataclass(frozen=True)
class DetectionMetrics:
    """Scores for one group of images. NaN means undefined: no people."""

    n_images: int
    n_images_with_people: int
    n_ground_truth: int
    n_predictions: int
    ap_iou25: float
    ap_iou50: float
    ap_coco: float
    recall_at_fppi: dict[float, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_images": self.n_images,
            "n_images_with_people": self.n_images_with_people,
            "n_ground_truth": self.n_ground_truth,
            "n_predictions": self.n_predictions,
            "ap_iou25": _finite_or_none(self.ap_iou25),
            "ap_iou50": _finite_or_none(self.ap_iou50),
            "ap_coco": _finite_or_none(self.ap_coco),
            "recall_at_fppi": {
                str(f): _finite_or_none(r) for f, r in self.recall_at_fppi.items()
            },
        }


@dataclass(frozen=True)
class DetectionReport:
    """Scores overall and broken down by modality, flight, and person size."""

    overall: DetectionMetrics
    by_modality: dict[str, DetectionMetrics]
    by_flight: dict[str, DetectionMetrics]
    by_size: dict[str, DetectionMetrics]
    config: dict[str, Any] = field(default_factory=lambda: _config())

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "overall": self.overall.to_dict(),
            "by_modality": {k: m.to_dict() for k, m in self.by_modality.items()},
            "by_flight": {k: m.to_dict() for k, m in self.by_flight.items()},
            "by_size": {k: m.to_dict() for k, m in self.by_size.items()},
        }

    def write_json(self, run_dir: Path) -> Path:
        """Write the report to ``run_dir/detection_metrics.json``."""
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / METRICS_FILENAME
        path.write_text(json.dumps(self.to_dict(), indent=2, allow_nan=False) + "\n")
        return path


def _finite_or_none(value: float) -> float | None:
    return None if math.isnan(value) else value


def _config() -> dict[str, Any]:
    return {
        "primary_iou": PRIMARY_IOU,
        "iou_thresholds": list(IOU_THRESHOLDS),
        "fppi_points": list(FPPI_POINTS),
        "fppi_iou": PRIMARY_IOU,
        "size_buckets_sqrt_area_px": {
            name: [low, None if math.isinf(high) else high]
            for name, (low, high) in SIZE_BUCKETS.items()
        },
        "box_format": "x1,y1,x2,y2 pixels, top-left origin, far edge exclusive",
        "ap_interpolation": "COCO 101-point, recall levels k/100",
        "pycocotools": version("pycocotools"),
    }


def evaluate_detections(
    truths: Sequence[GroundTruth], predictions: Sequence[Prediction]
) -> DetectionReport:
    """Score predictions against ground truth.

    ``truths`` defines the images evaluated and must list every image, with or
    without people. An image missing from ``predictions`` has no detections.
    """
    images: dict[str, GroundTruth] = {}
    for gt in truths:
        if gt.image_id in images:
            raise ValueError(f"image {gt.image_id!r} appears more than once")
        images[gt.image_id] = gt
    detections: dict[str, Prediction] = {}
    for pred in predictions:
        if pred.image_id not in images:
            raise ValueError(f"image {pred.image_id!r} is not in the ground truth")
        if pred.image_id in detections:
            raise ValueError(f"predictions for {pred.image_id!r} given more than once")
        detections[pred.image_id] = pred

    scorer = _Scorer(list(images.values()), detections)
    by_bucket = scorer.score(list(images))
    return DetectionReport(
        overall=by_bucket.pop(_ALL),
        by_modality=scorer.score_groups(lambda gt: gt.modality),
        by_flight=scorer.score_groups(lambda gt: gt.flight),
        by_size=by_bucket,
    )


class _Scorer:
    """Holds the pycocotools view of the data and scores subsets of images."""

    def __init__(self, truths: list[GroundTruth], preds: dict[str, Prediction]):
        self.truths = {gt.image_id: gt for gt in truths}
        self.preds = preds
        # COCO ids must start at 1: pycocotools uses a match id of 0 for "none".
        self.coco_ids = {gt.image_id: n for n, gt in enumerate(truths, start=1)}
        images = [{"id": n} for n in self.coco_ids.values()]
        gt_anns, dt_anns = [], []
        for image_id, n in self.coco_ids.items():
            gt_anns += _annotations(self.truths[image_id].boxes, n)
            if image_id in preds:
                pred = preds[image_id]
                dt_anns += _annotations(pred.boxes, n, pred.scores)
        for ann_id, ann in enumerate(gt_anns + dt_anns, start=1):
            ann["id"] = ann_id
        self.coco_gt = _coco(images, gt_anns)
        self.coco_dt = _coco(images, dt_anns)
        # No per-image cap: pycocotools would silently drop detections past it.
        self.max_dets = max([1, *(np.asarray(p.scores).size for p in preds.values())])

    def score_groups(self, key: Any) -> dict[str, DetectionMetrics]:
        groups: dict[str, list[str]] = {}
        for image_id, gt in self.truths.items():
            groups.setdefault(key(gt), []).append(image_id)
        return {name: self.score(ids)[_ALL] for name, ids in sorted(groups.items())}

    def score(self, image_ids: list[str]) -> dict[str, DetectionMetrics]:
        buckets = {_ALL: (0.0, math.inf), **SIZE_BUCKETS}
        ev = COCOeval(self.coco_gt, self.coco_dt, iouType="bbox")
        p = ev.params
        p.imgIds = [self.coco_ids[i] for i in image_ids]
        p.catIds = [_PERSON]
        p.iouThrs = np.array(IOU_THRESHOLDS)
        p.recThrs = _RECALL_LEVELS
        p.maxDets = [self.max_dets]
        # pycocotools keeps areas in [low, high] inclusive; stepping the upper
        # edge down one ulp makes each bucket half-open, [low, high).
        p.areaRng = [
            [low**2, math.inf if math.isinf(high) else np.nextafter(high**2, 0.0)]
            for low, high in buckets.values()
        ]
        p.areaRngLbl = list(buckets)
        with redirect_stdout(io.StringIO()):
            ev.evaluate()
            ev.accumulate()

        results = {}
        for a, (name, (low, high)) in enumerate(buckets.items()):
            ap = [_average_precision(ev, t, a) for t in range(len(IOU_THRESHOLDS))]
            gt_counts = [_count_in(self.truths[i].boxes, low, high) for i in image_ids]
            results[name] = DetectionMetrics(
                n_images=len(image_ids),
                n_images_with_people=sum(c > 0 for c in gt_counts),
                n_ground_truth=sum(gt_counts),
                n_predictions=sum(
                    _count_in(self.preds[i].boxes, low, high)
                    for i in image_ids
                    if i in self.preds
                ),
                ap_iou25=ap[IOU_THRESHOLDS.index(PRIMARY_IOU)],
                ap_iou50=ap[IOU_THRESHOLDS.index(0.5)],
                ap_coco=float(
                    np.mean([ap[IOU_THRESHOLDS.index(t)] for t in COCO_IOUS])
                ),
                recall_at_fppi=_recall_at_fppi(
                    ev, IOU_THRESHOLDS.index(PRIMARY_IOU), a, len(image_ids)
                ),
            )
        return results


def _annotations(
    boxes: ArrayLike, image: int, scores: ArrayLike | None = None
) -> list[dict[str, Any]]:
    anns = []
    for k, (x1, y1, x2, y2) in enumerate(np.asarray(boxes).tolist()):
        w, h = x2 - x1, y2 - y1
        ann = {
            "image_id": image,
            "category_id": _PERSON,
            "bbox": [x1, y1, w, h],
            "area": w * h,
            "iscrowd": 0,
        }
        if scores is not None:
            ann["score"] = float(np.asarray(scores)[k])
        anns.append(ann)
    return anns


def _coco(images: list[dict], annotations: list[dict]) -> COCO:
    coco = COCO()
    coco.dataset = {
        "images": images,
        "categories": [{"id": _PERSON, "name": "person"}],
        "annotations": annotations,
    }
    with redirect_stdout(io.StringIO()):
        coco.createIndex()
    return coco


def _count_in(boxes: ArrayLike, low: float, high: float) -> int:
    areas = _areas(boxes)
    return int(np.count_nonzero((areas >= low**2) & (areas < high**2)))


def _average_precision(ev: COCOeval, t: int, a: int) -> float:
    precision = np.asarray(ev.eval["precision"])[t, :, 0, a, 0]
    if (precision < 0).all():  # pycocotools writes -1 when there are no people
        return math.nan
    return float(np.mean(precision))


def _recall_at_fppi(ev: COCOeval, t: int, a: int, n_images: int) -> dict[float, float]:
    """Best recall at each false-alarm budget, from pycocotools' own matches."""
    n = len(ev.params.imgIds)
    per_image = [e for e in ev.evalImgs[a * n : (a + 1) * n] if e is not None]
    n_people = sum(int(np.count_nonzero(e["gtIgnore"] == 0)) for e in per_image)
    if n_people == 0:
        return {f: math.nan for f in FPPI_POINTS}

    scores = np.concatenate([[], *(e["dtScores"] for e in per_image)])
    hits = np.concatenate([[], *(e["dtMatches"][t] > 0 for e in per_image)])
    ignored = np.concatenate([[], *(e["dtIgnore"][t] for e in per_image)])
    keep = ignored == 0
    scores, hits = scores[keep], hits[keep].astype(bool)

    order = np.argsort(-scores, kind="stable")
    scores, hits = scores[order], hits[order]
    # Only the last detection of each run of equal scores is a real cutoff.
    cutoff = np.append(scores[1:] != scores[:-1], True)[: len(scores)]
    recall = np.append(0.0, np.cumsum(hits)[cutoff] / n_people)
    fppi = np.append(0.0, np.cumsum(~hits)[cutoff] / n_images)
    return {f: float(recall[fppi <= f].max()) for f in FPPI_POINTS}
