from pathlib import Path

import pytest
from pytest import MonkeyPatch

from movie_scheduler.config import ConfigManager


@pytest.mark.parametrize("value,expected", [(None, 0.2), ("", 0.2), ("1", 1.0), ("2", 2.0), ("0.2", 0.2)])
def test_maoyan_qps_defaults_and_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path, value: str | None, expected: float,
) -> None:
    manager = ConfigManager()
    manager.env_path = tmp_path / ".env"
    if value is None:
        monkeypatch.delenv("MOVIE_SCHEDULER_MAOYAN_QPS", raising=False)
    else:
        monkeypatch.setenv("MOVIE_SCHEDULER_MAOYAN_QPS", value)
    manager.reload_from_env()
    assert manager.maoyan_qps == expected


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf", "invalid"])
def test_maoyan_qps_rejects_invalid_limits(monkeypatch: MonkeyPatch, tmp_path: Path, value: str) -> None:
    manager = ConfigManager()
    manager.env_path = tmp_path / ".env"
    monkeypatch.setenv("MOVIE_SCHEDULER_MAOYAN_QPS", value)
    with pytest.raises(ValueError):
        manager.reload_from_env()
