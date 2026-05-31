"""场次接口测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.core.exceptions import RepositoryError
from app.show.service import show_service

client = TestClient(app, raise_server_exceptions=False)


def test_get_shows_endpoint_returns_movies_and_last_fetched_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/shows 应返回想看电影的场次和最近一次抓取完成时间。"""

    async def fake_payload() -> dict[str, object]:
        return {
            "movies": [
                {
                    "movie_id": 1,
                    "shows": [
                        {
                            "cinema_id": 10,
                            "cinema_name": "影院A",
                            "date": "2026-06-01",
                            "time": "19:30",
                            "price": "39.9",
                        }
                    ],
                }
            ],
            "last_fetched_at": "2026-06-01T08:00:00",
        }

    monkeypatch.setattr(show_service, "get_shows_for_wished_movies", fake_payload)

    response = client.get("/api/shows")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["last_fetched_at"] == "2026-06-01T08:00:00"
    assert body["data"]["movies"][0]["movie_id"] == 1
    assert body["data"]["movies"][0]["shows"][0]["cinema_name"] == "影院A"


def test_get_shows_endpoint_maps_repository_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """底层数据库异常应被统一异常处理器映射。"""

    async def fake_payload() -> dict[str, object]:
        raise RepositoryError("底层数据库错误")

    monkeypatch.setattr(show_service, "get_shows_for_wished_movies", fake_payload)

    response = client.get("/api/shows")

    assert response.status_code == 500
    assert response.json() == {"success": False, "error": "数据库访问失败，请稍后重试"}
