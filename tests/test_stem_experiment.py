"""Arm C of the thermal input ablation (#68), on a tiny random tower."""

import json
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image
from transformers import Siglip2ImageProcessor, Siglip2VisionConfig, Siglip2VisionModel

from aerial_search.experiments import stem_experiment as se
from aerial_search.experiments.feature_cache import CacheError
from aerial_search.models.backbone import SPECS

SPEC = SPECS["siglip2-base-naflex"]
FOLD, OTHER = "220109_Baker", "210417_MtErie"
SIZE = (160, 128)
BUDGET = 64


def tiny_tower() -> Siglip2VisionModel:
    torch.manual_seed(0)
    config = Siglip2VisionConfig(
        hidden_size=16,
        intermediate_size=32,
        num_hidden_layers=1,
        num_attention_heads=2,
        patch_size=16,
        num_patches=BUDGET,
    )
    return Siglip2VisionModel(config).eval()


def record(site: str, name: str, boxes: list) -> dict:
    return {
        "image": f"{site}_Enterprise_IR_1/{name}.png",
        "site_day": site,
        "collection_id": f"{site}_Enterprise_IR_1",
        "camera": "thermal",
        "size": list(SIZE),
        "boxes": boxes,
    }


def write(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")


def setup(tmp_path: Path, input_handling: str | None = None, grid_shift: int = 0):
    """Raw frames, fold manifests and a replicate cache index to match."""
    rng = np.random.default_rng(1)
    processor = Siglip2ImageProcessor(patch_size=16)
    raw = tmp_path / "raw"

    def frames(site: str, n: int) -> list[dict]:
        out = []
        for k in range(n):
            grey = rng.integers(0, 255, (SIZE[1], SIZE[0]), dtype=np.uint8)
            rgb = np.stack([grey] * 3, axis=-1)
            x, y = rng.uniform(0.2, 0.8, 2)
            person = [{"x_center": x, "y_center": y, "width": 0.05, "height": 0.08}]
            rec = record(site, str(k), person if k % 2 else [])
            (raw / rec["image"]).parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(rgb).save(raw / rec["image"])
            out.append(rec)
        return out

    train, validation, test = frames(OTHER, 4), frames(OTHER, 2), frames(FOLD, 2)
    view = tmp_path / "manifests" / "folds" / FOLD / "thermal"
    write(view / "train_100pct.jsonl", train)
    write(view / "validation.jsonl", validation)
    write(view / "test.jsonl", test)

    shapes = processor(
        images=[Image.new("RGB", SIZE)], return_tensors="pt", max_num_patches=BUDGET
    )["spatial_shapes"][0]
    ph, pw = int(shapes[0]) + grid_shift, int(shapes[1])
    cache = tmp_path / "outputs" / "features" / "m-64tok"
    (cache / "runs" / "s1").mkdir(parents=True)
    settings = {
        "model": "siglip2-base-naflex",
        "repo": SPEC.repo,
        "revision": SPEC.revision,
        "weights_sha256": {"model.safetensors": "aa"},
        "token_budget": BUDGET,
        "pooling": 2,
        **({} if input_handling is None else {"input_handling": input_handling}),
    }
    (cache / "cache.json").write_text(json.dumps({"settings": settings}))
    (cache / "runs" / "s1" / "run.json").write_text(
        json.dumps({"scratch": True, "status": "completed"})
    )
    lines = []
    for r in [*train, *validation, *test]:
        entry = {
            "camera": "thermal",
            "image_size": list(SIZE),
            "resized_size": [pw * 16, ph * 16],
            "patch_grid": [ph, pw],
            "pooling": 2,
            "grid": [(ph + 1) // 2, (pw + 1) // 2],
            "dim": 16,
            "path": r["image"],
            "run": "s1",
        }
        lines.append(json.dumps(entry))
        feature = cache / "features" / Path(r["image"]).with_suffix(".npy")
        feature.parent.mkdir(parents=True, exist_ok=True)
        np.save(feature, np.zeros((1, 1, 1), dtype="f2"))
    (cache / "index.jsonl").write_text("\n".join(lines) + "\n")
    return cache


def run(tmp_path: Path, cache: Path, tower, **recipe):
    return se.run_stem_head(
        cache_dir=cache,
        manifests=tmp_path / "manifests",
        data_root=tmp_path / "raw",
        fold=FOLD,
        camera="thermal",
        percent=100,
        seed=7,
        recipe=se.StemRecipe(
            steps=4,
            batch_size=4,
            micro_batch=2,
            eval_every=2,
            hidden=8,
            stem_hidden=4,
            eval_batch=2,
            **recipe,
        ),
        scratch=True,
        run_name="stem-test",
        device=torch.device("cpu"),
        repo=tmp_path / "repo",
        argv=["aerial-search", "train-head"],
        load_backbone=lambda name, device: (
            tower,
            Siglip2ImageProcessor(patch_size=16),
        ),
        weights=lambda repo, revision: {"model.safetensors": "aa"},
    )


def test_a_scratch_run_trains_the_stem_and_head_and_leaves_the_tower_alone(tmp_path):
    cache = setup(tmp_path)
    tower = tiny_tower()
    before = [p.detach().clone() for p in tower.parameters()]

    summary = run(tmp_path, cache, tower)

    directory = tmp_path / "repo" / "outputs" / "scratch-stem-test"
    record = json.loads((directory / "run.json").read_text())
    assert record["status"] == "completed" and record["scratch"] is True
    assert record["config"]["input_handling"] == "stem"
    assert record["config"]["recipe"]["micro_batch"] == 2
    metrics = json.loads((directory / "detection_metrics.json").read_text())
    assert metrics["overall"]["n_images"] == 2  # the test site-day only
    assert summary["skipped_steps"] == 0
    assert all(
        torch.equal(a, b) for a, b in zip(before, tower.parameters(), strict=True)
    )
    assert all(not p.requires_grad for p in tower.parameters())
    stem = torch.load(directory / "stem.pt")
    assert stem["out.weight"].abs().sum() > 0  # moved off the identity
    training = json.loads((directory / "training.json").read_text())
    assert len(training["loss"]) == 4 and training["best_step"] in (2, 4)
    assert len(training["step_seconds"]) == 4


def test_the_stem_arm_refuses_a_cache_that_is_not_the_replicate_one(tmp_path):
    cache = setup(tmp_path, input_handling="equalise")

    with pytest.raises(CacheError, match="replicate"):
        run(tmp_path, cache, tiny_tower())


def test_a_frame_whose_grid_disagrees_with_the_cache_index_is_refused(tmp_path):
    cache = setup(tmp_path, grid_shift=1)

    with pytest.raises(CacheError, match="patch grid"):
        run(tmp_path, cache, tiny_tower())
    record = json.loads(
        (tmp_path / "repo" / "outputs" / "scratch-stem-test" / "run.json").read_text()
    )
    assert record["status"] == "failed"


def test_the_stem_arm_is_for_thermal_only(tmp_path):
    cache = setup(tmp_path)

    with pytest.raises(ValueError, match="thermal"):
        se.run_stem_head(
            cache_dir=cache,
            manifests=tmp_path / "manifests",
            data_root=tmp_path / "raw",
            fold=FOLD,
            camera="rgb",
            percent=100,
            seed=7,
            recipe=se.StemRecipe(),
            scratch=True,
            run_name="x",
            device=torch.device("cpu"),
            repo=tmp_path / "repo",
        )


def test_weights_that_are_not_the_caches_are_refused(tmp_path):
    cache = setup(tmp_path)

    with pytest.raises(CacheError, match="weights"):
        se.run_stem_head(
            cache_dir=cache,
            manifests=tmp_path / "manifests",
            data_root=tmp_path / "raw",
            fold=FOLD,
            camera="thermal",
            percent=100,
            seed=7,
            recipe=se.StemRecipe(),
            scratch=True,
            run_name="x",
            device=torch.device("cpu"),
            repo=tmp_path / "repo",
            load_backbone=lambda n, d: (tiny_tower(), None),
            weights=lambda repo, revision: {"model.safetensors": "zz"},
        )
