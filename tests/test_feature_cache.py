import json
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image
from transformers import Siglip2ImageProcessor, Siglip2VisionConfig, Siglip2VisionModel

from aerial_search.experiments import feature_cache as fc
from aerial_search.models.backbone import NaflexExtractor, pool2

SETTINGS = fc.CacheSettings(
    model="fake",
    repo="fake/fake",
    weights_sha256={"model.safetensors": "aa"},
    token_budget=64,
    pooling=2,
    dtype="float16",
)


class FakeExtractor:
    """Features that depend on the pixels, so a stale file is detectable."""

    def __init__(self) -> None:
        self.calls = 0

    def prepare(self, image: Image.Image) -> float:  # runs in a worker thread
        return float(np.asarray(image.convert("RGB"), dtype=np.float32).mean())

    def extract(self, prepared: float) -> np.ndarray:
        self.calls += 1
        return np.full((2, 3, 4), prepared, dtype=np.float16)


def make_frames(root: Path, names: dict[str, str]) -> list[fc.Frame]:
    frames = []
    for i, (path, camera) in enumerate(names.items()):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (32, 18), (10 * (i + 1),) * 3).save(root / path)
        frames.append(fc.Frame(path, camera, "c1", f"sha{i}"))
    return frames


@pytest.fixture
def frames(tmp_path: Path) -> list[fc.Frame]:
    return make_frames(
        tmp_path / "raw",
        {"VIS_1/a_0.jpeg": "rgb", "VIS_1/a_1.jpeg": "rgb", "IR_2/b_0.jpeg": "thermal"},
    )


def build(tmp_path, frames, extractor, settings=SETTINGS, **kw):
    return fc.build_cache(
        tmp_path / "cache",
        settings,
        frames,
        extractor,
        tmp_path / "raw",
        run="r1",
        commit="abc",
        **kw,
    )


def test_writes_fp16_features_per_image_with_camera_and_provenance(tmp_path, frames):
    summary = build(tmp_path, frames, FakeExtractor())

    assert summary.computed == 3
    cache = tmp_path / "cache"
    array = fc.read_features(cache, "VIS_1/a_0.jpeg")
    assert array.dtype == np.float16 and array.shape == (2, 3, 4)
    index = fc.read_index(cache)
    assert index["IR_2/b_0.jpeg"]["camera"] == "thermal"
    entry = index["VIS_1/a_0.jpeg"]
    assert entry["grid"] == [2, 3] and entry["sha256"] == "sha0"
    assert entry["run"] == "r1" and entry["commit"] == "abc"
    assert json.loads((cache / "cache.json").read_text())["settings"]["model"] == "fake"


def test_second_run_skips_finished_images_and_computes_the_rest(tmp_path, frames):
    build(tmp_path, frames[:2], FakeExtractor())
    again = FakeExtractor()

    summary = build(tmp_path, frames, again, verify=0)

    assert (summary.skipped, summary.computed) == (2, 1)
    assert again.calls == 1


def test_resume_recomputes_a_sample_of_finished_images(tmp_path, frames):
    build(tmp_path, frames, FakeExtractor())
    again = FakeExtractor()

    summary = build(tmp_path, frames, again, verify=2)

    assert summary.verified == 2 and summary.computed == 0
    assert again.calls == 2


def test_resume_refuses_when_a_finished_file_no_longer_matches(tmp_path, frames):
    build(tmp_path, frames, FakeExtractor())
    path = tmp_path / "cache" / "features" / "VIS_1" / "a_0.npy"
    np.save(path, np.zeros((2, 3, 4), dtype=np.float16))

    with pytest.raises(fc.CacheError, match="a_0"):
        build(tmp_path, frames, FakeExtractor(), verify=3)


def test_a_crash_between_file_and_index_is_recomputed(tmp_path, frames):
    build(tmp_path, frames, FakeExtractor())
    index = tmp_path / "cache" / "index.jsonl"
    lines = index.read_text().splitlines()
    index.write_text("\n".join(lines[:-1]) + "\n" + lines[-1][:10])  # torn last line

    summary = build(tmp_path, frames, FakeExtractor(), verify=0)

    assert summary.computed == 1 and summary.skipped == 2
    assert set(fc.read_index(tmp_path / "cache")) == {f.path for f in frames}


@pytest.mark.parametrize(
    "change",
    [
        {"token_budget": 128},
        {"pooling": 1},
        {"dtype": "float32"},
        {"weights_sha256": {"model.safetensors": "bb"}},
        {"repo": "other/model"},
    ],
)
def test_a_cache_refuses_settings_that_differ(tmp_path, frames, change):
    build(tmp_path, frames, FakeExtractor())
    other = fc.CacheSettings(**{**SETTINGS.__dict__, **change})

    with pytest.raises(fc.CacheError, match="different settings"):
        build(tmp_path, frames, FakeExtractor(), settings=other)
    with pytest.raises(fc.CacheError, match="different settings"):
        fc.check_settings(tmp_path / "cache", other)


def test_select_frames_by_camera_collection_and_limit(tmp_path):
    rows = [
        {"collection_id": "c1", "rgb_image": "V/1.jpeg", "thermal_image": "I/1.jpeg"},
        {"collection_id": "c1", "rgb_image": "V/2.jpeg", "thermal_image": "I/2.jpeg"},
        {"collection_id": "c2", "rgb_image": "V/3.jpeg", "thermal_image": "I/1.jpeg"},
    ]
    manifest = tmp_path / "all_pairs.jsonl"
    manifest.write_text("\n".join(json.dumps(r) for r in rows))
    pinned = {"V/1.jpeg": "h1", "V/3.jpeg": "h3", "I/1.jpeg": "hi1"}

    rgb = fc.select_frames(manifest, "rgb", pinned)
    assert [f.path for f in rgb] == ["V/1.jpeg", "V/2.jpeg", "V/3.jpeg"]
    assert rgb[0].sha256 == "h1" and rgb[1].sha256 is None
    thermal = fc.select_frames(manifest, "thermal", pinned)
    assert [f.path for f in thermal] == ["I/1.jpeg", "I/2.jpeg"]  # de-duplicated
    assert thermal[0].camera == "thermal"
    only = fc.select_frames(manifest, "rgb", pinned, collections=["c2"], limit=5)
    assert [f.path for f in only] == ["V/3.jpeg"]
    assert len(fc.select_frames(manifest, "rgb", pinned, limit=2)) == 2
    with pytest.raises(fc.CacheError, match="no-such"):
        fc.select_frames(manifest, "rgb", pinned, collections=["no-such"])


def test_parts_split_the_frames_into_contiguous_chunks_that_cover_all(tmp_path):
    rows = [
        {"collection_id": "c", "rgb_image": f"V/{i}.jpeg", "thermal_image": "I/0.jpeg"}
        for i in range(7)
    ]
    manifest = tmp_path / "all_pairs.jsonl"
    manifest.write_text("\n".join(json.dumps(r) for r in rows))

    parts = [fc.select_frames(manifest, "rgb", {}, part=(k, 3)) for k in (1, 2, 3)]

    assert [len(p) for p in parts] == [3, 3, 1]
    assert [f.path for p in parts for f in p] == [f"V/{i}.jpeg" for i in range(7)]
    with pytest.raises(fc.CacheError, match="part"):
        fc.select_frames(manifest, "rgb", {}, part=(4, 3))


def test_naflex_extractor_returns_a_pooled_fp16_grid_for_either_camera():
    config = Siglip2VisionConfig(
        hidden_size=32,
        intermediate_size=64,
        num_hidden_layers=1,
        num_attention_heads=2,
        patch_size=16,
        num_patches=64,
    )
    model = Siglip2VisionModel(config).eval()
    processor = Siglip2ImageProcessor(patch_size=16)
    extractor = NaflexExtractor(model, processor, token_budget=64, pooling=2)
    rgb = Image.new("RGB", (160, 90), (200, 30, 30))
    thermal = Image.new("L", (160, 90), 128)  # a one-channel frame

    out = extractor(rgb)
    assert out.dtype == np.float16
    assert out.shape == (3, 5, 32)  # a 6 x 10 grid pooled 2 x 2
    assert extractor(thermal).shape == out.shape
    # thermal goes in as three identical channels
    same = extractor(Image.merge("RGB", [thermal] * 3))
    assert np.array_equal(extractor(thermal), same)


def test_pool2_drops_the_odd_last_row_and_column():
    x = torch.arange(3 * 5 * 2, dtype=torch.float32).reshape(3, 5, 2)
    assert pool2(x, 2).shape == (1, 2, 2)
    assert pool2(x, 1) is x


@pytest.fixture
def dataset(tmp_path: Path):
    """Raw frames and an all_pairs manifest."""
    raw = tmp_path / "data" / "raw"
    names = {"V_1/a_0.jpeg": "rgb", "V_1/a_1.jpeg": "rgb", "I_2/b_0.jpeg": "thermal"}
    make_frames(raw, names)
    manifests = tmp_path / "data" / "manifests"
    manifests.mkdir(parents=True)
    T = "I_2/b_0.jpeg"
    rows = [
        {"collection_id": "c1", "rgb_image": "V_1/a_0.jpeg", "thermal_image": T},
        {"collection_id": "c1", "rgb_image": "V_1/a_1.jpeg", "thermal_image": T},
    ]
    (manifests / "all_pairs.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    return raw, manifests


def fake_loader(budget: int, pooling: int) -> FakeExtractor:
    return FakeExtractor()


def run_features(
    tmp_path,
    dataset,
    session="s1",
    pooling=2,
    limit=None,
    scratch=True,
    weights=lambda repo: {"model.safetensors": "aa"},
):
    raw, manifests = dataset
    (tmp_path / "repo").mkdir(exist_ok=True)
    return fc.cache_features(
        model="siglip2-base-naflex",
        camera="rgb",
        data_root=raw,
        manifests=manifests,
        collections=None,
        limit=limit,
        token_budget=1024,
        pooling=pooling,
        verify=8,
        scratch=scratch,
        session=session,
        repo=tmp_path / "repo",
        load_extractor=fake_loader,
        weights=weights,
    )


def test_a_run_writes_the_cache_and_a_run_record_inside_it(tmp_path, dataset):
    summary = run_features(tmp_path, dataset)

    cache = tmp_path / "repo/outputs/scratch-features/siglip2-base-naflex-1024tok"
    assert summary.computed == 2
    record = json.loads((cache / "runs/s1/run.json").read_text())
    assert record["status"] == "completed" and record["scratch"] is True
    assert record["config"]["settings"]["token_budget"] == 1024
    assert record["config"]["settings"]["weights_sha256"] == {"model.safetensors": "aa"}
    assert record["config"]["camera"] == "rgb"
    assert fc.read_index(cache)["V_1/a_1.jpeg"]["run"] == "s1"
    assert not list(dataset[1].glob("*.npy"))  # the manifests were only read


def test_a_run_with_other_settings_refuses_before_starting_a_run(tmp_path, dataset):
    run_features(tmp_path, dataset)
    cache = tmp_path / "repo/outputs/scratch-features/siglip2-base-naflex-1024tok"

    with pytest.raises(fc.CacheError, match="different settings"):
        run_features(tmp_path, dataset, session="s2", pooling=1)
    with pytest.raises(fc.CacheError, match="different settings"):
        other = {"model.safetensors": "zz"}
        run_features(tmp_path, dataset, session="s3", weights=lambda repo: other)
    assert sorted(p.name for p in (cache / "runs").iterdir()) == ["s1"]


def test_a_limit_needs_a_scratch_run(tmp_path, dataset):
    with pytest.raises(fc.CacheError, match="scratch"):
        run_features(tmp_path, dataset, limit=1, scratch=False)
    assert run_features(tmp_path, dataset, limit=1).computed == 1
