"""场次服务测试。"""

from __future__ import annotations

import pytest

from app.core.exceptions import AppError
from app.services.show_fetching.service import show_service


def test_show_service_normalizes_movie_ids() -> None:
    """应去重并保留原始顺序。"""
    assert show_service._normalize_movie_ids([3, 1, 3, 2, 1]) == [3, 1, 2]  # pyright: ignore[reportPrivateUsage]


def test_show_service_rejects_empty_movie_ids() -> None:
    """空电影 ID 列表应被拒绝。"""
    with pytest.raises(AppError):
        show_service._normalize_movie_ids([])  # pyright: ignore[reportPrivateUsage]


def test_show_service_rejects_invalid_movie_id() -> None:
    """非法电影 ID 应被拒绝。"""
    with pytest.raises(AppError):
        show_service._normalize_movie_ids([1, 0])  # pyright: ignore[reportPrivateUsage]


def test_show_service_uses_default_city_id_when_missing() -> None:
    """未传城市时应回退到默认城市。"""
    assert show_service._normalize_city_id(None) == 10  # pyright: ignore[reportPrivateUsage]


def test_show_service_rejects_unsupported_city_id() -> None:
    """不支持的城市 ID 应被拒绝。"""
    with pytest.raises(AppError):
        show_service._normalize_city_id(999)  # pyright: ignore[reportPrivateUsage]
