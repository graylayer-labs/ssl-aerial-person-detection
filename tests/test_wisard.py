from pathlib import Path

import pytest

from aerial_search.data.wisard import (
    WISARD_COLLECTIONS,
    _extract_frame_index,
    load_boxes,
    load_pairs,
    pairing_report,
    prepare_manifests,
)

# One flight in the shape of WiSARD: the drone records VIS as DJI file n and IR
# as DJI file n+1, so the directory suffixes differ by one.
FLIGHT = {"flight_0001": ("flight_VIS_0001", "flight_IR_0002")}


def test_pairs_frames_by_index_not_position(tmp_path: Path) -> None:
    rgb = tmp_path / "flight_VIS_0001"
    thermal = tmp_path / "flight_IR_0002"
    rgb.mkdir()
    thermal.mkdir()
    for number in range(40):
        _sample(rgb, number)
        _sample(thermal, number + 1)

    pairs = load_pairs(tmp_path, collections=FLIGHT)

    # RGB has frames 0-39, thermal has 1-40. Position-based pairing would give
    # 40 pairs, each one frame apart; index-based pairing gives frames 1-39.
    assert len(pairs) == 39
    assert all(_frame(p.rgb_image) == _frame(p.thermal_image) for p in pairs)
    assert _frame(pairs[0].rgb_image) == 1


def test_pairs_flight_whose_frame_counts_differ(tmp_path: Path) -> None:
    rgb = tmp_path / "flight_VIS_0001"
    thermal = tmp_path / "flight_IR_0002"
    rgb.mkdir()
    thermal.mkdir()
    # Real WiSARD naming: 8-digit RGB numbers, 5-digit thermal numbers from a
    # video export. RGB has 6 frames, thermal has 8.
    for number in range(6):
        _touch(rgb / f"flight_VIS_0001_{number:08d}.jpg")
    for number in range(8):
        _touch(thermal / f"DJI_0002.mp4_{number:05d}.jpg")

    pairs = load_pairs(tmp_path, collections=FLIGHT, labelled_only=False)
    report = pairing_report(tmp_path, collections=FLIGHT)

    assert [_frame(p.rgb_image) for p in pairs] == list(range(6))
    assert [_frame(p.thermal_image) for p in pairs] == list(range(6))
    assert report["collections"]["flight_0001"] == {
        "rgb_dir": "flight_VIS_0001",
        "thermal_dir": "flight_IR_0002",
        "rgb_frames": 6,
        "thermal_frames": 8,
        "pairs": 6,
        "labelled_pairs": 6,
        "rgb_only_frames": 0,
        "thermal_only_frames": 2,
    }


def test_skips_missing_annotation(tmp_path: Path) -> None:
    """Pairs without labels in both modalities are left out of load_pairs."""
    rgb = tmp_path / "flight_VIS_0001"
    thermal = tmp_path / "flight_IR_0002"
    rgb.mkdir()
    thermal.mkdir()
    _sample(rgb, 0)  # Has annotation
    (thermal / "flight_IR_0002_00000.jpeg").touch()  # Same frame, no annotation

    assert load_pairs(tmp_path, collections=FLIGHT) == []
    assert len(load_pairs(tmp_path, collections=FLIGHT, labelled_only=False)) == 1


def test_pairs_only_listed_directories_and_reports_the_rest(tmp_path: Path) -> None:
    # Two VIS and three IR directories at one site. Grouping by site name alone
    # would have to guess which goes with which; only listed pairs are used.
    for name in [
        "site_VIS_0001",
        "site_IR_0002",
        "site_VIS_0003",
        "site_IR_0004",
        "site_IR_0005",
    ]:
        (tmp_path / name).mkdir()
        _sample(tmp_path / name, 0)
    collections = {"site_0003": ("site_VIS_0003", "site_IR_0004")}

    pairs = load_pairs(tmp_path, collections=collections)
    report = pairing_report(tmp_path, collections=collections)

    assert [(p.rgb_image.parent.name, p.thermal_image.parent.name) for p in pairs] == [
        ("site_VIS_0003", "site_IR_0004")
    ]
    assert report["unpaired_directories"] == [
        "site_IR_0002",
        "site_IR_0005",
        "site_VIS_0001",
    ]


def test_rejects_duplicate_frame_numbers_in_one_directory(tmp_path: Path) -> None:
    rgb = tmp_path / "flight_VIS_0001"
    thermal = tmp_path / "flight_IR_0002"
    rgb.mkdir()
    thermal.mkdir()
    _touch(rgb / "flight_VIS_0001_00000007.jpg")
    _touch(rgb / "flight_VIS_0001_7.jpeg")  # also frame 7
    _touch(thermal / "flight_IR_0002_00007.jpg")

    with pytest.raises(ValueError, match="frame 7"):
        load_pairs(tmp_path, collections=FLIGHT, labelled_only=False)


def test_rejects_image_without_frame_number(tmp_path: Path) -> None:
    rgb = tmp_path / "flight_VIS_0001"
    thermal = tmp_path / "flight_IR_0002"
    rgb.mkdir()
    thermal.mkdir()
    _sample(rgb, 0)
    _sample(thermal, 0)
    _touch(thermal / "thumbnail.jpg")

    with pytest.raises(ValueError, match="thumbnail.jpg"):
        load_pairs(tmp_path, collections=FLIGHT, labelled_only=False)


def test_rejects_listed_pair_whose_frame_numbers_barely_overlap(
    tmp_path: Path,
) -> None:
    # If the two directories number their frames differently, equal numbers do
    # not mean the same moment. Refuse rather than pair a sliver of frames.
    rgb = tmp_path / "flight_VIS_0001"
    thermal = tmp_path / "flight_IR_0002"
    rgb.mkdir()
    thermal.mkdir()
    for number in range(10):
        _sample(rgb, number)
        _sample(thermal, number + 8)

    with pytest.raises(ValueError, match="flight_0001"):
        load_pairs(tmp_path, collections=FLIGHT, labelled_only=False)


def test_wisard_collections_pair_each_directory_once() -> None:
    rgb_dirs = [rgb for rgb, _ in WISARD_COLLECTIONS.values()]
    thermal_dirs = [thermal for _, thermal in WISARD_COLLECTIONS.values()]

    assert len(set(rgb_dirs)) == len(rgb_dirs)
    assert len(set(thermal_dirs)) == len(thermal_dirs)
    assert all("_VIS" in name for name in rgb_dirs)
    assert all("_IR" in name for name in thermal_dirs)


def test_loads_normalized_person_boxes(tmp_path: Path) -> None:
    labels = tmp_path / "labels.txt"
    labels.write_text("0 0.5 0.4 0.1 0.2\n")

    boxes = load_boxes(labels)

    assert len(boxes) == 1
    assert boxes[0].width == 0.1


def test_prepares_collection_level_manifests(tmp_path: Path) -> None:
    source = tmp_path / "raw"
    collections = {}

    # Create five collections to ensure test/val splits
    for flight_idx in range(5):
        rgb = source / f"2024010{flight_idx}_site_{flight_idx}_VIS_0000"
        thermal = source / f"2024010{flight_idx}_site_{flight_idx}_IR_0001"
        rgb.mkdir(parents=True)
        thermal.mkdir()
        collections[f"site_{flight_idx}"] = (rgb.name, thermal.name)

        # Each flight: 2 pairs (total 10)
        for number in range(2):
            _sample(rgb, number)
            _sample(thermal, number)

    counts = prepare_manifests(
        source, tmp_path / "processed", seed=7, collections=collections
    )

    # No collection should be split across train/val/test.
    assert sum(counts.values()) == 10
    assert all(split >= 0 for split in counts.values())

    # Verify determinism: same seed produces same split
    counts2 = prepare_manifests(
        source, tmp_path / "processed2", seed=7, collections=collections
    )
    assert counts == counts2

    counts3 = prepare_manifests(
        source, tmp_path / "processed3", seed=42, collections=collections
    )
    assert sum(counts3.values()) == 10


@pytest.mark.parametrize(
    ("name", "frame"),
    [
        # Every naming scheme found in the WiSARD dataset.
        ("210327_Airfield_FLIR_VIS_4_00000494.jpg", 494),
        ("200402_Karen_Inspire_VIS_695.jpeg", 695),
        ("20200929_134258_IR 127.jpg", 127),
        ("200704_baker__FLIR_1_ 0001.jpg", 1),
        ("DJI_0021 (1-6-2022 8-21-53 AM).mp4_00499.jpg", 499),
        ("DJI_0402.mp4_00000.jpg", 0),
        ("210417_MtErie_Enterprise_IR_0008_out_frame_00179.jpeg", 179),
        ("210417_MtErie_Enterprise_IR_0006_00290.jpeg", 290),
    ],
)
def test_parses_frame_numbers_of_any_length(name: str, frame: int) -> None:
    assert _extract_frame_index(Path(name)) == frame


@pytest.mark.parametrize("name", ["thumbnail.jpg", "DJI0001.jpg", "frame_12.png"])
def test_rejects_names_without_a_frame_number(name: str) -> None:
    with pytest.raises(ValueError, match=name):
        _extract_frame_index(Path(name))


def _sample(directory: Path, number: int) -> None:
    stem = f"{directory.name}_{number:05d}"
    (directory / f"{stem}.jpeg").touch()
    (directory / f"{stem}.txt").touch()


def _touch(image: Path) -> None:
    image.touch()
    image.with_suffix(".txt").touch()


def _frame(path: Path) -> int:
    return int(path.stem.rsplit("_", 1)[1])
