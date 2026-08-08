from pathlib import Path

import pytest

from aerial_search.cli import main


def test_inspect_counts_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "rgb").mkdir()
    (tmp_path / "rgb" / "frame.jpg").touch()
    (tmp_path / "labels.txt").touch()

    main(["inspect", str(tmp_path)])

    assert capsys.readouterr().out == f"{tmp_path}: 2 files\n"


def test_inspect_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="Data path does not exist"):
        main(["inspect", str(tmp_path / "missing")])
