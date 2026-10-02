"""A cache of frozen-backbone features, one file per image (#65).

Layout of a cache directory `outputs/features/<model>-<budget>tok/`:

    cache.json         the settings that define the cache; never changed
    index.jsonl        one line per finished image, appended as work proceeds
    features/<clip dir>/<stem>.npy
                       h x w x d float16 array, readable with mmap

One file per image, mirroring the dataset's clip directories, because a write
is then one atomic rename, a crash loses at most the image in flight, and a
fold or a single image is read by opening only the files it names. The cost is
about 30,000 files of a few hundred kilobytes each, which the filesystem
handles without trouble. `index.jsonl` says which images are done and, for
each, the camera, the grid, the SHA-256 of the source image (from the pinned
dataset list), and the run and commit that wrote it.

The settings are the identity of the cache: model, weights, token budget,
pooling and dtype. A second run with any of them different refuses to write
into it. A resumed run skips finished images and recomputes a sample of them
to prove the weights and code still give the same features.
"""

from __future__ import annotations

import json
import os
import random
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

# A recomputed feature may differ from the stored one by float noise: the
# largest difference, relative to the largest stored value, must stay below this.
VERIFY_TOLERANCE = 0.02


class CacheError(Exception):
    """The cache cannot be written or trusted."""


class Extractor(Protocol):
    def __call__(self, image: Image.Image) -> np.ndarray:
        """An h x w x d float16 array of features for one image."""
        ...


@dataclass(frozen=True)
class CacheSettings:
    """What makes two caches interchangeable. All of it is part of the key."""

    model: str  # alias, for example "siglip2-base-naflex"
    repo: str  # model identifier on the hub
    weights_sha256: dict[str, str]  # per weight file
    token_budget: int
    pooling: int  # k of a k x k average pool; 1 is none
    dtype: str

    def name(self) -> str:
        return f"{self.model}-{self.token_budget}tok"


@dataclass(frozen=True)
class Frame:
    path: str  # relative to the data root
    camera: str  # "rgb" or "thermal"
    collection_id: str
    sha256: str | None  # from the pinned list, None if not listed


@dataclass
class Summary:
    requested: int = 0
    computed: int = 0
    skipped: int = 0
    verified: int = 0
    seconds: float = 0.0


def select_frames(
    manifest: Path,
    camera: str,
    pinned: Mapping[str, str],
    collections: Sequence[str] | None = None,
    limit: int | None = None,
) -> list[Frame]:
    """The distinct images of one camera in a pair manifest, in manifest order."""
    key = "rgb_image" if camera == "rgb" else "thermal_image"
    rows = [json.loads(line) for line in manifest.read_text().splitlines() if line]
    if collections:
        known = {row["collection_id"] for row in rows}
        missing = sorted(set(collections) - known)
        if missing:
            raise CacheError(f"not in {manifest}: {', '.join(missing)}")
        rows = [row for row in rows if row["collection_id"] in collections]
    frames: dict[str, Frame] = {}
    for row in rows:
        path = row[key]
        frames.setdefault(
            path, Frame(path, camera, row["collection_id"], pinned.get(path))
        )
    selected = list(frames.values())
    return selected[:limit] if limit else selected


def _read_record(cache_dir: Path) -> dict | None:
    try:
        return json.loads((cache_dir / "cache.json").read_text())
    except FileNotFoundError:
        return None


def check_settings(cache_dir: Path, settings: CacheSettings) -> None:
    """Raise `CacheError` if the cache exists with other settings."""
    record = _read_record(cache_dir)
    if record is None:
        return
    stored, wanted = record["settings"], asdict(settings)
    differ = sorted(k for k in wanted if stored.get(k) != wanted[k])
    if differ:
        raise CacheError(
            f"{cache_dir} was made with different settings ({', '.join(differ)}); "
            "refusing to mix them. Use another cache, or delete this one."
        )


def _feature_path(cache_dir: Path, image_path: str) -> Path:
    return cache_dir / "features" / Path(image_path).with_suffix(".npy")


def read_index(cache_dir: Path) -> dict[str, dict]:
    """Finished images by path. An unreadable line (a torn write) is skipped."""
    entries: dict[str, dict] = {}
    try:
        text = (cache_dir / "index.jsonl").read_text()
    except FileNotFoundError:
        return entries
    for line in text.splitlines():
        try:
            entry = json.loads(line)
            entries[entry["path"]] = entry
        except (ValueError, KeyError):
            continue
    return entries


def read_features(cache_dir: Path, image_path: str) -> np.ndarray:
    """The h x w x d float16 features of one image, memory-mapped."""
    return np.load(_feature_path(cache_dir, image_path), mmap_mode="r")


def _save_atomic(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, array)
    os.replace(temporary, path)


def _open(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.copy()


def _verify(
    cache_dir: Path,
    done: list[Frame],
    extractor: Extractor,
    data_root: Path,
    count: int,
    seed: int,
) -> int:
    sample = random.Random(seed).sample(done, min(count, len(done)))
    for frame in sample:
        stored = np.asarray(read_features(cache_dir, frame.path), dtype=np.float32)
        fresh = np.asarray(extractor(_open(data_root / frame.path)), dtype=np.float32)
        if stored.shape != fresh.shape:
            raise CacheError(
                f"{frame.path}: stored grid {stored.shape} but recomputed "
                f"{fresh.shape}; the cache does not match this code or weights"
            )
        scale = max(float(np.abs(stored).max()), 1.0)
        worst = float(np.abs(stored - fresh).max()) / scale
        if worst > VERIFY_TOLERANCE:
            raise CacheError(
                f"{frame.path}: recomputed features differ from the stored ones "
                f"by {worst:.3f} of their scale (limit {VERIFY_TOLERANCE}); the "
                "cache does not match this code or weights"
            )
    return len(sample)


def build_cache(
    cache_dir: Path,
    settings: CacheSettings,
    frames: Sequence[Frame],
    extractor: Extractor,
    data_root: Path,
    *,
    run: str,
    commit: str | None,
    verify: int = 8,
    seed: int = 0,
    progress: Callable[[int, int, float], None] | None = None,
) -> Summary:
    """Write features for the frames not yet in the cache, after verifying a
    sample of those that are. Returns what was done.

    Raises `CacheError` if the cache has other settings or a verified image no
    longer matches. Safe to repeat after a crash.
    """
    check_settings(cache_dir, settings)
    cache_dir.mkdir(parents=True, exist_ok=True)
    if _read_record(cache_dir) is None:
        record = {"settings": asdict(settings), "format": 1}
        (cache_dir / "cache.json").write_text(json.dumps(record, indent=2) + "\n")

    started = time.perf_counter()
    index = read_index(cache_dir)
    done = [
        f
        for f in frames
        if f.path in index and _feature_path(cache_dir, f.path).exists()
    ]
    finished = {f.path for f in done}
    todo = [f for f in frames if f.path not in finished]
    summary = Summary(requested=len(frames), skipped=len(done))
    summary.verified = _verify(cache_dir, done, extractor, data_root, verify, seed)

    index_path = cache_dir / "index.jsonl"
    tail = index_path.read_bytes() if index_path.exists() else b""
    if tail and not tail.endswith(b"\n"):
        with index_path.open("ab") as handle:  # close off a torn last line
            handle.write(b"\n")
    with index_path.open("a") as handle:
        for n, frame in enumerate(todo, 1):
            array = extractor(_open(data_root / frame.path))
            if array.dtype != np.dtype(settings.dtype):
                raise CacheError(
                    f"{frame.path}: extractor gave {array.dtype}, the cache "
                    f"settings say {settings.dtype}"
                )
            _save_atomic(_feature_path(cache_dir, frame.path), array)
            entry = {
                "path": frame.path,
                "camera": frame.camera,
                "collection_id": frame.collection_id,
                "grid": list(array.shape[:2]),
                "dim": int(array.shape[2]),
                "sha256": frame.sha256,
                "run": run,
                "commit": commit,
            }
            handle.write(json.dumps(entry) + "\n")
            handle.flush()
            summary.computed += 1
            if progress:
                progress(n, len(todo), time.perf_counter() - started)
    summary.seconds = time.perf_counter() - started
    return summary


SEED = 7  # picks which finished images a resumed run recomputes


def cache_features(
    *,
    model: str,
    camera: str,
    data_root: Path,
    manifests: Path,
    collections: Sequence[str] | None,
    limit: int | None,
    token_budget: int,
    pooling: int,
    verify: int,
    scratch: bool,
    session: str | None = None,
    repo: Path | None = None,
    load_extractor: Callable[[int, int], Extractor] | None = None,
    weights: Callable[[str], dict[str, str]] | None = None,
    argv: list[str] | None = None,
) -> Summary:
    """One session of the feature cache: one camera, optionally some collections.

    The cache is `outputs/features/<model>-<budget>tok/` (`outputs/scratch-features/`
    for a scratch run) and each session is a run under its `runs/<session>/`
    with the usual `run.json`, which records the settings, the weight checksums
    and the data verification. A cache with other settings is refused before
    any run is started. `load_extractor` and `weights` are for tests.
    """
    from aerial_search import run as run_module
    from aerial_search.data import checksums
    from aerial_search.models import backbone
    from aerial_search.models.components import get_device

    if limit and not scratch:
        raise CacheError("--limit builds a partial cache; use it with --scratch only")
    spec = backbone.SPECS[model]
    settings = CacheSettings(
        model=model,
        repo=spec.repo,
        weights_sha256=(weights or backbone.weight_checksums)(spec.repo),
        token_budget=token_budget,
        pooling=pooling,
        dtype="float16",
    )
    top = "scratch-features" if scratch else "features"
    outputs = run_module.outputs_dir(scratch=scratch, repo=repo)
    cache_dir = outputs / top / settings.name()
    check_settings(cache_dir, settings)

    manifest = manifests / "all_pairs.jsonl"
    pinned = {e.path: e.sha256 for e in checksums.committed_list()}
    frames = select_frames(manifest, camera, pinned, collections, limit)
    if session is None:
        stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
        session = "-".join([camera, *(collections or []), stamp])
    config = {
        "settings": asdict(settings),
        "camera": camera,
        "collections": list(collections or []),
        "limit": limit,
        "verify": verify,
        "images": len(frames),
        "cache_dir": str(cache_dir),
        "preprocessing": "image.convert('RGB'), then the NaFlex processor at "
        "max_num_patches=token_budget; a one-channel thermal frame becomes "
        "three identical channels; features are the last hidden state",
    }
    directory = run_module.start_run(
        f"features/{settings.name()}/runs/{session}",
        config,
        SEED,
        device=str(get_device()),
        scratch=scratch,
        argv=argv,
        repo=repo,
        inputs=[manifest],
        manifests=manifests,
        data_root=data_root,
    )
    try:
        if directory.parent.parent.resolve() != cache_dir.resolve():
            raise CacheError(f"run {directory} is not inside the cache {cache_dir}")
        record = json.loads((directory / "run.json").read_text())
        extractor = (load_extractor or _load_naflex(model))(token_budget, pooling)
        summary = build_cache(
            cache_dir,
            settings,
            frames,
            extractor,
            data_root,
            run=directory.name,
            commit=record.get("commit"),
            verify=verify,
            seed=SEED,
            progress=_print_progress,
        )
        (directory / "summary.json").write_text(
            json.dumps(asdict(summary), indent=2) + "\n"
        )
    except BaseException as error:
        run_module.finish_run(directory, error)
        raise
    run_module.finish_run(directory)
    return summary


def _load_naflex(model: str) -> Callable[[int, int], Extractor]:
    def load(token_budget: int, pooling: int) -> Extractor:
        from transformers import AutoImageProcessor

        from aerial_search.models import backbone
        from aerial_search.models.components import get_device

        spec = backbone.SPECS[model]
        return backbone.NaflexExtractor(
            backbone.load(spec, str(get_device())),
            AutoImageProcessor.from_pretrained(spec.repo),
            token_budget,
            pooling,
        )

    return load


def _print_progress(done: int, total: int, seconds: float) -> None:
    if done % 200 == 0 or done == total:
        rate = done / seconds if seconds else 0.0
        left = (total - done) / rate / 60 if rate else 0.0
        print(f"{done}/{total} images, {rate:.1f}/s, {left:.1f} min left", flush=True)
