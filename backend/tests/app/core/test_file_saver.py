from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import config_manager
from app.core.file_saver import FileSaver


def test_file_saver_save_example_uses_fixed_filename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_manager, "result_dir", str(tmp_path))
    saver = FileSaver()

    saved = saver.save_example("示例内容", "example.json")

    assert saved is True
    assert (tmp_path / "example.json").read_text(encoding="utf-8") == "示例内容"
