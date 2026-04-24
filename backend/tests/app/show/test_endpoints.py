"""场次接口测试。"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.core.exceptions import RepositoryError
from app.show.service import StreamCompleteEvent, show_service

client = TestClient(app, raise_server_exceptions=False)


def test_fetch_show_stream_endpoint_streams_complete_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """流式接口应输出完成事件。"""

    async def stream_show(
        movie_ids: list[int],
        city_id: int | None = None,
    ) -> AsyncIterator[StreamCompleteEvent]:
        assert movie_ids == [1, 2]
        assert city_id == 10
        yield StreamCompleteEvent(type="complete", data=[])

    monkeypatch.setattr(show_service, "stream_show", stream_show)

    with client.stream("GET", "/api/shows/fetch-stream?movie_ids=1,2&city_id=10") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"type":"complete"' in body


def test_fetch_show_stream_endpoint_masks_internal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SSE 错误事件不应直接暴露内部异常原文。"""

    async def stream_show(
        movie_ids: list[int],
        city_id: int | None = None,
    ) -> AsyncIterator[StreamCompleteEvent]:
        del movie_ids, city_id
        raise RepositoryError("底层数据库错误")
        yield StreamCompleteEvent(type="complete", data=[])

    monkeypatch.setattr(show_service, "stream_show", stream_show)

    with client.stream("GET", "/api/shows/fetch-stream?movie_ids=1&city_id=10") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"type":"error"' in body
    assert "数据库访问失败，请稍后重试" in body
