"""更新服务测试。"""

from __future__ import annotations

import pytest

from app.core.exceptions import AppError
from app.services.update_service import update_service


def test_update_service_accepts_known_city_id() -> None:
    """已配置的城市 ID 应通过校验。"""
    assert update_service._normalize_city_id(10) == 10  # pyright: ignore[reportPrivateUsage]


def test_update_service_rejects_unknown_city_id() -> None:
    """未配置的城市 ID 应被拒绝。"""
    with pytest.raises(AppError):
        update_service._normalize_city_id(999999)  # pyright: ignore[reportPrivateUsage]
