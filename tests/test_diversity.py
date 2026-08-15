from pathlib import Path

from PIL import Image

from aerial_search.data.diversity import (
    build_diversity_report,
    compute_collection_stats,
    extract_thumbnails,
    parse_collection_metadata,
)
from aerial_search.data.wisard import ImagePair


def test_parse_collection_metadata() -> None:
    date, site, platform = parse_collection_metadata(
        "20240104_SiteName_Platform_VIS_0001"
    )
    assert date == "20240104"
    assert site == "SiteName"
    assert platform == "Platform"

    date, site, platform = parse_collection_metadata("invalid")
    assert date is None
    assert site is None
    assert platform is None


def test_compute_collection_stats_empty() -> None:
    stats = compute_collection_stats("empty", [])
    assert stats.collection_id == "empty"
    assert stats.num_pairs == 0
    assert stats.total_rgb_boxes == 0
    assert stats.mean_rgb_brightness == 0.0


def test_compute_collection_stats_with_images(tmp_path: Path) -> None:
    # Create synthetic RGB and thermal images
    collection_dir = tmp_path / "test_coll"
    collection_dir.mkdir()

    # Make a bright RGB image
    rgb_path = collection_dir / "rgb_00000000.jpeg"
    rgb_img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    rgb_img.save(rgb_path)

    # Make a darker thermal image
    thermal_path = collection_dir / "thermal_00000000.jpeg"
    thermal_img = Image.new("L", (100, 100), color=50)
    thermal_img.save(thermal_path)

    # Create matching label files (empty for simplicity)
    (collection_dir / "rgb_00000000.txt").write_text("")
    (collection_dir / "thermal_00000000.txt").write_text("")

    pair = ImagePair(
        collection_id="test_coll",
        rgb_image=rgb_path,
        thermal_image=thermal_path,
        rgb_labels=collection_dir / "rgb_00000000.txt",
        thermal_labels=collection_dir / "thermal_00000000.txt",
    )

    stats = compute_collection_stats("test_coll", [pair])
    assert stats.num_pairs == 1
    assert stats.mean_rgb_brightness > 150  # bright
    assert stats.mean_thermal_brightness < 100  # dark


def test_extract_thumbnails(tmp_path: Path) -> None:
    # Create dummy images
    collection_dir = tmp_path / "test_coll"
    collection_dir.mkdir()

    rgb_path = collection_dir / "rgb_00000000.jpeg"
    rgb_img = Image.new("RGB", (640, 480), color=(100, 100, 100))
    rgb_img.save(rgb_path)

    thermal_path = collection_dir / "thermal_00000000.jpeg"
    thermal_img = Image.new("L", (640, 480), color=(50,))
    thermal_img.save(thermal_path)

    (collection_dir / "rgb_00000000.txt").write_text("")
    (collection_dir / "thermal_00000000.txt").write_text("")

    pair = ImagePair(
        collection_id="test_coll",
        rgb_image=rgb_path,
        thermal_image=thermal_path,
        rgb_labels=collection_dir / "rgb_00000000.txt",
        thermal_labels=collection_dir / "thermal_00000000.txt",
    )

    thumb_dir = tmp_path / "thumbnails"
    paths = extract_thumbnails(
        "test_coll", [pair], thumb_dir, count=1, max_dimension=100, quality=70
    )

    assert len(paths) == 2  # 1 RGB + 1 thermal
    for path in paths:
        assert path.exists()
        assert path.stat().st_size < 50000  # should be small


def test_build_diversity_report(tmp_path: Path) -> None:
    # Create minimal synthetic data
    root_dir = tmp_path / "raw"
    root_dir.mkdir()

    coll_rgb = root_dir / "20240101_Site_Platform_VIS_0000"
    coll_thermal = root_dir / "20240101_Site_Platform_IR_0000"
    coll_rgb.mkdir()
    coll_thermal.mkdir()

    # One dummy pair
    rgb_path = coll_rgb / "img_00000000.jpeg"
    thermal_path = coll_thermal / "img_00000000.jpeg"
    Image.new("RGB", (100, 100), (150, 150, 150)).save(rgb_path)
    Image.new("L", (100, 100), (50,)).save(thermal_path)
    (coll_rgb / "img_00000000.txt").write_text("")
    (coll_thermal / "img_00000000.txt").write_text("")

    report_path = tmp_path / "reports" / "diversity.md"
    thumb_dir = tmp_path / "thumbnails"

    build_diversity_report(root_dir, report_path, thumb_dir)

    assert report_path.exists()
    content = report_path.read_text()
    assert "WiSARD Dataset Diversity Report" in content
    assert "20240101_Site_Platform" in content
