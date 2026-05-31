"""更新接口测试。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.update.entities import UpdateProgressEvent
from app.update.result_builder import UpdateCinemaResult
from app.update.service import update_service

client = TestClient(app, raise_server_exceptions=False)

UpdateProgressCallback = Callable[[UpdateProgressEvent], None]


def test_update_cinema_stream_endpoint_returns_progress_and_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """影院更新流式接口应输出进度事件与最终结果。"""

    async def update_cinema(
        city_id: int,
        progress_callback: UpdateProgressCallback | None = None,
    ) -> UpdateCinemaResult:
        assert city_id == 10
        assert progress_callback is not None
        progress_callback(
            UpdateProgressEvent(
                message="正在更新城市 10 的影院信息，第 1 页",
                stage="fetching_cinema_page",
                city_id=10,
                page=1,
            )
        )
        return UpdateCinemaResult(success_count=2, failure_count=0)

    monkeypatch.setattr(update_service, "update_cinema", update_cinema)
    with client.stream("GET", "/api/update/cinema-stream?city_id=10") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"type":"progress"' in body
    assert '"message":"正在更新城市 10 的影院信息，第 1 页"' in body
    assert '"type":"complete"' in body
    assert '"success_count":2' in body


def test_movie_update_status_returns_last_updated_at(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """status 接口应返回 movies.updated_at 的最大值。"""

    async def fake_last_updated_at() -> datetime:
        return datetime(2026, 6, 1, 12, 30, 0)

    monkeypatch.setattr(update_service, "get_movies_last_updated_at", fake_last_updated_at)

    response = client.get("/api/update/movies/status")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["last_updated_at"] == "2026-06-01T12:30:00"


def test_movie_update_status_returns_null_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """没有任何电影时 last_updated_at 应为 null。"""

    async def fake_last_updated_at() -> None:
        return None

    monkeypatch.setattr(update_service, "get_movies_last_updated_at", fake_last_updated_at)

    response = client.get("/api/update/movies/status")

    assert response.status_code == 200
    assert response.json()["data"]["last_updated_at"] is None
