"""Fine-tune an off-the-shelf detector on the same labels as the head (#67).

The supervised baseline: a torchvision detector with COCO weights, trained on
the same fold, camera, label fraction and seed as `train-head`, selected on the
fold's validation split and scored on its test site-day through
`aerial_search.evaluation.detection`. Which frames it sees comes from
`head_experiment.select_records`, the function the head uses, and the score is
the same `evaluate_detections`, so the two sit in one table
(`head_table.markdown_compare`).
"""

from __future__ import annotations

import copy
import json
import math
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torchvision.transforms.v2.functional as vision
from torch.utils.data import DataLoader, Dataset
from torchvision.io import ImageReadMode, decode_image

from aerial_search.evaluation.detection import (
    DetectionReport,
    GroundTruth,
    Prediction,
    evaluate_detections,
)
from aerial_search.experiments.head_experiment import record_boxes, select_records

ARCHITECTURES = (
    "fasterrcnn_resnet50_fpn",
    "retinanet_resnet50_fpn",
    "fcos_resnet50_fpn",
)

# The model input of the frozen backbone's cache (docs/detection-head-design.md):
# every image is stretched to this, whatever its source size. "cache" gives the
# baseline the same pixels the head's features were computed from.
CACHE_INPUT = {"rgb": (672, 384), "thermal": (560, 448)}
INPUTS = ("cache", "native")
# One anchor size per feature-pyramid level (default 32 to 512): the smallest
# people are 4 px wide at the head's input size.
ANCHORS = (8, 16, 32, 64, 128)


@dataclass(frozen=True)
class BaselineRecipe:
    """Everything that defines how the baseline is built, trained and decoded."""

    arch: str = "fasterrcnn_resnet50_fpn"
    input: str = "cache"  # "cache": the head's model input; "native": no resize
    steps: int = 600
    batch_size: int = 8
    learning_rate: float = 0.01
    momentum: float = 0.9
    weight_decay: float = 1e-4
    warmup_steps: int = 50
    eval_every: int = 150
    val_frames: int = 200  # validation frames used to pick the step (0: all)
    top_k: int = 100
    score_floor: float = 0.001  # keep low-scoring boxes: AP needs the whole curve
    workers: int = 4


def input_size(camera: str, mode: str) -> tuple[int, int] | None:
    """(width, height) the images are stretched to, or None for native."""
    if mode == "native":
        return None
    if mode == "cache":
        return CACHE_INPUT[camera]
    raise ValueError(f"input must be one of {INPUTS}, not {mode!r}")


def subsample(records: Sequence[dict], limit: int) -> list[dict]:
    """`limit` records spread evenly through the list (all if limit is 0)."""
    if limit <= 0 or len(records) <= limit:
        return list(records)
    picks = np.linspace(0, len(records) - 1, limit).round().astype(int)
    return [records[i] for i in picks]


# --- model ----------------------------------------------------------------------


def build_model(
    arch: str,
    *,
    pretrained: bool,
    anchor_sizes: Sequence[int] = (),
    score_floor: float = 0.001,
    top_k: int = 100,
):
    """A torchvision detector with one person class (plus background).

    `pretrained` loads COCO weights and replaces the final classifier; tests
    pass False and load nothing. The internal resize is switched off: images
    are resized by the dataset, so the model never rescales them and its
    boxes come back in the pixels it was given. `anchor_sizes` replaces the
    default anchors (32 to 512 px), which cannot match a person 4 pixels
    wide, with one size per feature level; it is only for Faster R-CNN.
    """
    from torchvision.models import detection

    if arch not in ARCHITECTURES:
        raise ValueError(f"arch must be one of {ARCHITECTURES}, not {arch!r}")
    ctor = getattr(detection, arch)
    kwargs: dict[str, Any] = {}
    if pretrained:
        kwargs["weights"] = "COCO_V1"
    else:
        kwargs["weights"] = None
        kwargs["weights_backbone"] = None
    if arch == "fasterrcnn_resnet50_fpn":
        model = ctor(
            **kwargs, box_detections_per_img=top_k, box_score_thresh=score_floor
        )
        if anchor_sizes:
            from torchvision.models.detection.anchor_utils import AnchorGenerator

            ratios = ((0.5, 1.0, 2.0),) * len(anchor_sizes)
            model.rpn.anchor_generator = AnchorGenerator(
                tuple((s,) for s in anchor_sizes), ratios
            )
        from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

        model.roi_heads.box_predictor = FastRCNNPredictor(
            model.roi_heads.box_predictor.cls_score.in_features, 2
        )
    elif arch == "retinanet_resnet50_fpn":
        model = ctor(**kwargs, detections_per_img=top_k, score_thresh=score_floor)
        from torchvision.models.detection.retinanet import RetinaNetClassificationHead

        old = model.head.classification_head
        model.head.classification_head = RetinaNetClassificationHead(
            old.cls_logits.in_channels, old.num_anchors, 2
        )
    else:
        model = ctor(**kwargs, detections_per_img=top_k, score_thresh=score_floor)
        from torchvision.models.detection.fcos import FCOSClassificationHead

        old = model.head.classification_head
        model.head.classification_head = FCOSClassificationHead(
            old.cls_logits.in_channels, old.num_anchors, 2
        )
    model.transform.resize = lambda image, target=None: (image, target)
    return model


# --- data -----------------------------------------------------------------------


class Frames(Dataset):
    """Frames of one split: the image stretched to the input size, its boxes
    scaled with it (one label, "person"), and the scale back to source pixels."""

    def __init__(
        self, records: Sequence[dict], data_root: Path, size: tuple[int, int] | None
    ):
        self.records = list(records)
        self.data_root = data_root
        self.size = size

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int):
        record = self.records[index]
        image = decode_image(
            str(self.data_root / record["image"]), mode=ImageReadMode.RGB
        )
        height, width = image.shape[-2:]
        if [width, height] != list(record["size"]):
            raise ValueError(
                f"{record['image']} is {width}x{height} on disk, "
                f"{record['size']} in the manifest"
            )
        sx = sy = 1.0
        if self.size is not None:
            sx, sy = self.size[0] / width, self.size[1] / height
            image = vision.resize(image, [self.size[1], self.size[0]], antialias=True)
        boxes = torch.as_tensor(
            record_boxes(record) * [sx, sy, sx, sy], dtype=torch.float32
        )
        keep = (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
        target = {
            "boxes": boxes[keep],
            "labels": torch.ones(int(keep.sum()), dtype=torch.int64),
        }
        return image.float() / 255, target, torch.tensor([sx, sy])


def _collate(batch):
    return tuple(zip(*batch, strict=True))


class BatchSteps:
    """The head's batching, for `steps` steps: consecutive slices of a running
    order of frames, a fresh shuffle appended whenever fewer than a batch
    remain, so a split smaller than a batch gives batches of the whole split."""

    def __init__(self, n: int, batch_size: int, steps: int, seed: int):
        self.n, self.batch_size, self.steps, self.seed = n, batch_size, steps, seed

    def __len__(self) -> int:
        return self.steps

    def __iter__(self):
        rng = np.random.default_rng(self.seed)
        order: list[int] = []
        for _ in range(self.steps):
            if len(order) < self.batch_size:
                order += rng.permutation(self.n).tolist()
            yield sorted(order[: self.batch_size])
            del order[: self.batch_size]


# --- training and scoring ---------------------------------------------------------


def _lr_factor(step: int, recipe: BaselineRecipe) -> float:
    if step <= recipe.warmup_steps:
        return step / recipe.warmup_steps
    progress = (step - recipe.warmup_steps) / max(recipe.steps - recipe.warmup_steps, 1)
    return 0.5 * (1 + math.cos(math.pi * min(progress, 1.0)))


def train_baseline(
    model,
    frames: Frames,
    recipe: BaselineRecipe,
    *,
    device: torch.device,
    validate: Callable[[], float] | None = None,
    seed: int = 0,
) -> dict[str, Any]:
    """SGD with momentum, linear warm-up and cosine decay for `recipe.steps`.

    Batches follow `batch_order`. Every `eval_every` steps (and at the end)
    `validate` scores the model; the best-scoring weights are restored at the
    end (the earlier step wins a tie; NaN never wins).
    """
    model.to(device)
    optimiser = torch.optim.SGD(
        [p for p in model.parameters() if p.requires_grad],
        lr=recipe.learning_rate,
        momentum=recipe.momentum,
        weight_decay=recipe.weight_decay,
    )
    schedule = torch.optim.lr_scheduler.LambdaLR(
        optimiser, lambda s: _lr_factor(s + 1, recipe)
    )
    loader = DataLoader(
        frames,
        batch_sampler=BatchSteps(len(frames), recipe.batch_size, recipe.steps, seed),
        num_workers=recipe.workers,
        collate_fn=_collate,
        persistent_workers=recipe.workers > 0,
    )
    history: dict[str, Any] = {"loss": [], "validation": [], "best_step": None}
    best, best_state = -math.inf, None
    for step, (images, targets, _) in enumerate(loader, start=1):
        model.train()
        images = [im.to(device) for im in images]
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
        loss = sum(model(images, targets).values())
        if not torch.isfinite(loss):
            raise FloatingPointError(f"loss {loss.item()} at step {step}")
        optimiser.zero_grad()
        loss.backward()
        optimiser.step()
        schedule.step()
        history["loss"].append(float(loss.item()))
        if validate is not None and (
            step % recipe.eval_every == 0 or step == recipe.steps
        ):
            score = validate()
            history["validation"].append({"step": step, "ap_iou25": score})
            print(
                f"step {step}: loss {loss.item():.4f}, val ap_iou25 {score:.4f}",
                flush=True,
            )
            if score > best:
                best, best_state = score, copy.deepcopy(model.state_dict())
                history["best_step"] = step
    if best_state is not None:
        model.load_state_dict(best_state)
    return history


@torch.no_grad()
def predict(
    model,
    frames: Frames,
    device: torch.device,
    *,
    batch_size: int = 8,
    workers: int = 0,
) -> list[Prediction]:
    """Detections in source pixels (the dataset's scale undone) per frame."""
    model.to(device).eval()
    loader = DataLoader(
        frames, batch_size=batch_size, num_workers=workers, collate_fn=_collate
    )
    out: list[Prediction] = []
    n = 0
    for images, _, scales in loader:
        outputs = model([im.to(device) for im in images])
        for o, scale in zip(outputs, scales, strict=True):
            boxes = o["boxes"].cpu().numpy().astype(np.float64)
            boxes = boxes / np.tile(scale.numpy().astype(np.float64), 2)
            width, height = frames.records[n]["size"]
            boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, width)
            boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, height)
            out.append(
                Prediction(
                    str(frames.records[n]["image"]),
                    boxes,
                    o["scores"].cpu().numpy().astype(np.float64),
                )
            )
            n += 1
    return out


def evaluate(
    model, frames: Frames, device: torch.device, *, workers: int = 0
) -> DetectionReport:
    """Score on a split with the same module and camera/flight grouping as the head."""
    truths = [
        GroundTruth(
            str(r["image"]), record_boxes(r), str(r["camera"]), str(r["collection_id"])
        )
        for r in frames.records
    ]
    return evaluate_detections(truths, predict(model, frames, device, workers=workers))


# --- one run ----------------------------------------------------------------------


def default_run_name(
    recipe: BaselineRecipe, camera: str, fold: str, percent: int, seed: int
):
    return (
        f"detection-baseline/{recipe.arch}-{recipe.input}/"
        f"{camera}-{fold}-{percent}pct-seed{seed}"
    )


def run_baseline(
    *,
    manifests: Path,
    data_root: Path,
    fold: str,
    camera: str,
    percent: int,
    seed: int,
    recipe: BaselineRecipe,
    scratch: bool,
    run_name: str | None,
    device: torch.device,
    repo: Path | None = None,
    argv: list[str] | None = None,
    limit_frames: int = 0,
) -> dict[str, Any]:
    """One run: fine-tune at `percent`, select on validation, score on test.

    `limit_frames` (scratch only) keeps that many frames of each split, for a
    timing or pipeline check. Writes `run.json`, `detection_metrics.json`
    (test) and `training.json` into the run directory.
    """
    from aerial_search import run as run_module

    if limit_frames and not scratch:
        raise ValueError("limit_frames needs a scratch run")
    paths, records = select_records(manifests, fold, camera, percent)
    if limit_frames:
        records = {r: subsample(rs, limit_frames) for r, rs in records.items()}
    size = input_size(camera, recipe.input)
    config = {
        "method": f"baseline:{recipe.arch}@{recipe.input}",
        "camera": camera,
        "fold": fold,
        "percent": percent,
        "recipe": asdict(recipe),
        "input_size": size,
        "weights": "torchvision COCO_V1",
        "images": {role: len(rs) for role, rs in records.items()},
        "limit_frames": limit_frames,
    }
    directory = run_module.start_run(
        run_name or default_run_name(recipe, camera, fold, percent, seed),
        config,
        seed,
        device=str(device),
        scratch=scratch,
        argv=argv,
        repo=repo,
        inputs=list(paths.values()),
        fold=fold,
        view=camera,
        manifests=manifests,
        data_root=data_root,
    )
    try:
        torch.manual_seed(seed)
        model = build_model(
            recipe.arch,
            pretrained=True,
            anchor_sizes=ANCHORS if recipe.arch == "fasterrcnn_resnet50_fpn" else (),
            score_floor=recipe.score_floor,
            top_k=recipe.top_k,
        )
        train = Frames(records["train"], data_root, size)
        val = Frames(
            subsample(records["validation"], recipe.val_frames), data_root, size
        )
        test = Frames(records["test"], data_root, size)

        def validate() -> float:
            return evaluate(model, val, device, workers=recipe.workers).overall.ap_iou25

        history = train_baseline(
            model, train, recipe, device=device, validate=validate, seed=seed
        )
        report = evaluate(model, test, device, workers=recipe.workers)
        report.write_json(directory)
        history["validation_frames"] = len(val)
        history["test_predictions_tied"] = report.overall.n_predictions_tied
        (directory / "training.json").write_text(
            json.dumps(history, indent=2, allow_nan=True) + "\n"
        )
    except BaseException as error:
        run_module.finish_run(directory, error)
        raise
    run_module.finish_run(directory)
    return {
        "run": str(directory),
        "best_step": history["best_step"],
        "test": report.overall.to_dict(),
        "by_size": {k: m.to_dict() for k, m in report.by_size.items()},
    }
