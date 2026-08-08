from pathlib import Path

import pytest

from aerial_search.data.wisard import load_boxes, load_pairs, prepare_manifests


def test_loads_pairs_in_capture_order(tmp_path: Path) -> None:
    rgb = tmp_path / "flight_VIS_0001"
    thermal = tmp_path / "flight_IR_0002"
    rgb.mkdir()
    thermal.mkdir()
    _sample(rgb, 1)
    _sample(rgb, 0)
    _sample(thermal, 2)
    _sample(thermal, 1)

    pairs = load_pairs(tmp_path)

    assert len(pairs) == 2
    assert pairs[0].rgb_image.name.endswith("00000000.jpeg")
    assert pairs[0].thermal_image.name.endswith("00000001.jpeg")


def test_rejects_missing_annotation(tmp_path: Path) -> None:
    rgb = tmp_path / "flight_VIS_0001"
    thermal = tmp_path / "flight_IR_0002"
    rgb.mkdir()
    thermal.mkdir()
    _sample(rgb, 0)
    (thermal / "flight_IR_0002_00000001.jpeg").touch()

    with pytest.raises(ValueError, match="matching annotation"):
        load_pairs(tmp_path)


def test_loads_normalized_person_boxes(tmp_path: Path) -> None:
    labels = tmp_path / "labels.txt"
    labels.write_text("0 0.5 0.4 0.1 0.2\n")

    boxes = load_boxes(labels)

    assert len(boxes) == 1
    assert boxes[0].width == 0.1


def test_prepares_sequential_manifests(tmp_path: Path) -> None:
    source = tmp_path / "raw"
    rgb = source / "flight_VIS_0001"
    thermal = source / "flight_IR_0002"
    rgb.mkdir(parents=True)
    thermal.mkdir()
    for number in range(10):
        _sample(rgb, number)
        _sample(thermal, number + 1)

    counts = prepare_manifests(source, tmp_path / "processed")

    assert counts == {"train": 7, "validation": 1, "test": 2}
    train_lines = (tmp_path / "processed" / "train.jsonl").read_text().splitlines()
    assert len(train_lines) == 7


def _sample(directory: Path, number: int) -> None:
    stem = f"{directory.name}_{number:08d}"
    (directory / f"{stem}.jpeg").touch()
    (directory / f"{stem}.txt").touch()
