"""排片计划接口测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.core.exceptions import RepositoryError
from app.planning.schemas import PlanningData
from app.planning.service import planning_service

client = TestClient(app, raise_server_exceptions=False)


def _payload() -> dict[str, object]:
    item = {
        "key": "1-10-2026-05-03-19:30",
        "movieId": 1,
        "movieTitle": "测试电影",
        "date": "2026-05-03",
        "time": "19:30",
        "cinemaId": 10,
        "cinemaName": "测试影院",
        "price": "39.9",
        "durationMinutes": 120,
        "purchased": True,
    }
    return {"wish_pool": [item], "schedule_items": [item]}


def test_planning_endpoints_replace_and_get() -> None:
    """接口应支持全量保存并读取计划。"""
    put_response = client.put("/api/planning", json=_payload())
    get_response = client.get("/api/planning")

    assert put_response.status_code == 200
    assert put_response.json()["success"] is True
    assert "movieId" in put_response.json()["data"]["wish_pool"][0]
    assert get_response.status_code == 200
    assert get_response.json()["data"]["wish_pool"][0]["purchased"] is False
    assert get_response.json()["data"]["schedule_items"][0]["purchased"] is True


def test_get_planning_endpoint_maps_repository_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """数据库异常应由统一异常处理器处理。"""

    async def get_planning() -> PlanningData:
        raise RepositoryError("底层数据库错误")

    monkeypatch.setattr(planning_service, "get_planning", get_planning)
    response = client.get("/api/planning")

    assert response.status_code == 500
    assert response.json() == {"success": False, "error": "数据库访问失败，请稍后重试"}
