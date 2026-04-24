"""城市接口测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.city.service import CityInfo, city_service

client = TestClient(app, raise_server_exceptions=False)


def test_city_endpoint_returns_city_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """城市接口应返回城市列表。"""

    def list_city() -> list[CityInfo]:
        return [CityInfo(name="上海", id=10)]

    monkeypatch.setattr(city_service, "list_city", list_city)
    response = client.get("/api/cities")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"cities": [{"name": "上海", "id": 10}]},
    }
