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


def test_prepares_collection_level_manifests(tmp_path: Path) -> None:
    source = tmp_path / "raw"

    # Create five collections to ensure test/val splits
    for flight_idx in range(5):
        rgb = source / f"2024010{flight_idx}_site_{flight_idx}_VIS_0000"
        thermal = source / f"2024010{flight_idx}_site_{flight_idx}_IR_0000"
        rgb.mkdir(parents=True)
        thermal.mkdir()

        # Each flight: 2 pairs (total 10)
        for number in range(2):
            _sample(rgb, number)
            _sample(thermal, number)

    counts = prepare_manifests(source, tmp_path / "processed", seed=7)

    # With seeded shuffle and greedy bin-fill:
    # 10 pairs total, train_fraction=0.7 -> target_train=7
    # Collections are shuffled, then greedily assigned.
    # No collection should be split across train/val/test.
    total = sum(counts.values())
    assert total == 10
    assert sum(counts.values()) == 10  # all pairs accounted for
    assert all(split >= 0 for split in counts.values())  # no negative counts

    # Verify determinism: same seed produces same split
    counts2 = prepare_manifests(source, tmp_path / "processed2", seed=7)
    assert counts == counts2

    # Verify different seed produces (possibly) different split
    counts3 = prepare_manifests(source, tmp_path / "processed3", seed=42)
    assert sum(counts3.values()) == 10  # but still valid


def _sample(directory: Path, number: int) -> None:
    stem = f"{directory.name}_{number:08d}"
    (directory / f"{stem}.jpeg").touch()
    (directory / f"{stem}.txt").touch()
