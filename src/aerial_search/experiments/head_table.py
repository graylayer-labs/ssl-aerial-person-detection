"""The results table of the detection-head runs (#66).

Reads every `run.json` under a directory, refuses any that is scratch or not
completed, and reports per camera and label fraction: each fold's test score,
and the mean and sample standard deviation over folds. `ap_iou50` is always
shown beside `ap_iou25` (docs/evaluation-metric-review.md).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from aerial_search.evaluation.detection import METRICS_FILENAME, SIZE_BUCKETS

FPPI = ("0.1", "1.0")
METRICS = ("ap_iou25", "ap_iou50", *(f"recall_at_{f}fppi" for f in FPPI))


class TableError(Exception):
    """A run cannot be quoted, or two runs claim the same cell."""


def _scores(metrics: dict[str, Any]) -> dict[str, float]:
    def value(v: Any) -> float:
        return math.nan if v is None else float(v)

    out = {
        "ap_iou25": value(metrics["ap_iou25"]),
        "ap_iou50": value(metrics["ap_iou50"]),
    }
    for f in FPPI:
        out[f"recall_at_{f}fppi"] = value(metrics["recall_at_fppi"].get(f))
    return out


def collect(root: Path) -> list[dict[str, Any]]:
    """Every run under `root`, with its test scores. Raises `TableError` on a
    scratch or unfinished run, or a completed run without its report."""
    runs = []
    for path in sorted(root.rglob("run.json")):
        record = json.loads(path.read_text())
        name = str(path.parent.relative_to(root))
        if record.get("scratch") is not False:
            raise TableError(f"{name} is a scratch run; it cannot be quoted")
        if record.get("status") != "completed":
            raise TableError(
                f"{name} has status {record.get('status')!r}, not completed"
            )
        report = path.parent / METRICS_FILENAME
        if not report.exists():
            raise TableError(f"{name} is completed but has no {METRICS_FILENAME}")
        metrics = json.loads(report.read_text())
        config = record["config"]
        runs.append(
            {
                "name": name,
                "camera": config["camera"],
                "fold": config["fold"],
                "percent": str(config["percent"]),
                "commit": record.get("commit"),
                "overall": _scores(metrics["overall"]),
                "by_size": {k: _scores(m) for k, m in metrics["by_size"].items()},
            }
        )
    return runs


def _spread(values: list[float]) -> tuple[float, float]:
    finite = [v for v in values if not math.isnan(v)]
    mean = float(np.mean(finite)) if finite else math.nan
    std = float(np.std(finite, ddof=1)) if len(finite) > 1 else math.nan
    return mean, std


def summarise(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """camera -> percent -> folds, mean, std, n_folds (and the same by size)."""
    cells: dict[tuple[str, str], dict[str, dict]] = {}
    for run in runs:
        folds = cells.setdefault((run["camera"], run["percent"]), {})
        if run["fold"] in folds:
            raise TableError(
                f"{run['camera']} fold {run['fold']} at {run['percent']}% appears "
                f"twice ({folds[run['fold']]['name']} and {run['name']})"
            )
        folds[run["fold"]] = run
    summary: dict[str, Any] = {}
    for (camera, percent), folds in sorted(cells.items()):
        entry: dict[str, Any] = {
            "folds": {f: r["overall"] for f, r in sorted(folds.items())},
            "n_folds": len(folds),
            "commits": sorted({str(r["commit"]) for r in folds.values()}),
            "mean": {},
            "std": {},
            "by_size": {},
        }
        for metric in METRICS:
            entry["mean"][metric], entry["std"][metric] = _spread(
                [r["overall"][metric] for r in folds.values()]
            )
        for bucket in SIZE_BUCKETS:
            per_fold = [
                r["by_size"][bucket] for r in folds.values() if bucket in r["by_size"]
            ]
            entry["by_size"][bucket] = {
                metric: _spread([s[metric] for s in per_fold])
                for metric in ("ap_iou25", "ap_iou50")
            }
        summary.setdefault(camera, {})[percent] = entry
    return summary


def _fmt(value: float) -> str:
    return "n/a" if math.isnan(value) else f"{value:.3f}"


def _pm(mean: float, std: float) -> str:
    return f"{_fmt(mean)} ± {_fmt(std)}"


def markdown(summary: dict[str, Any]) -> str:
    """One table per camera, then one of mean ap by person size."""
    lines: list[str] = []
    for camera, by_percent in summary.items():
        percents = sorted(by_percent, key=int)
        folds = sorted({f for e in by_percent.values() for f in e["folds"]})
        lines += [
            f"### {camera}: test ap_iou25 / ap_iou50 per fold, mean ± sd over folds",
            "",
            "| labels | "
            + " | ".join(folds)
            + " | ap_iou25 | ap_iou50 | recall @0.1 FPPI | recall @1 FPPI | folds |",
            "|---" * (len(folds) + 6) + "|",
        ]
        for percent in percents:
            e = by_percent[percent]
            cells = [
                f"{_fmt(e['folds'][f]['ap_iou25'])} / {_fmt(e['folds'][f]['ap_iou50'])}"
                if f in e["folds"]
                else "-"
                for f in folds
            ]
            mean, std = e["mean"], e["std"]
            stats = [_pm(mean[m], std[m]) for m in METRICS]
            lines.append(
                f"| {percent}% | "
                + " | ".join([*cells, *stats, str(e["n_folds"])])
                + " |"
            )
        lines += [
            "",
            f"### {camera}: test ap_iou25 / ap_iou50 by person size, mean over folds",
            "",
            "| labels | " + " | ".join(SIZE_BUCKETS) + " |",
            "|---" * (len(SIZE_BUCKETS) + 1) + "|",
        ]
        for percent in percents:
            sizes = by_percent[percent]["by_size"]
            cells = [
                f"{_fmt(sizes[b]['ap_iou25'][0])} / {_fmt(sizes[b]['ap_iou50'][0])}"
                for b in SIZE_BUCKETS
            ]
            lines.append(f"| {percent}% | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)
