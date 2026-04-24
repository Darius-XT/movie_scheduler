"""更新接口测试。"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.update.entities import UpdateProgressEvent
from app.update.result_builder import (
    UpdateCinemaResult,
    UpdateMovieBaseInfoResult,
    UpdateMovieExtraInfoResult,
    UpdateMovieInputStatsResult,
    UpdateMovieResult,
    UpdateMovieResultStatsResult,
)
from app.update.service import update_service

client = TestClient(app, raise_server_exceptions=False)

UpdateProgressCallback = Callable[[UpdateProgressEvent], None]


def test_update_cinema_stream_endpoint_returns_progress_and_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """影院更新流式接口应输出进度事件与最终结果。"""

    async def update_cinema(
        city_id: int,
        force_update_all: bool = False,
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


def test_update_movie_stream_endpoint_returns_progress_and_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """电影更新流式接口应输出进度事件与最终结果。"""

    async def update_movie(
        city_id: int,
        force_update_all: bool = False,
        progress_callback: UpdateProgressCallback | None = None,
    ) -> UpdateMovieResult:
        assert city_id == 10
        assert force_update_all is False
        assert progress_callback is not None
        progress_callback(
            UpdateProgressEvent(
                message="正在抓取电影列表",
                stage="fetching_movie_list",
                page=1,
            )
        )
        return UpdateMovieResult(
            base_info=UpdateMovieBaseInfoResult(
                input_stats=UpdateMovieInputStatsResult(
                    scraped_total=12,
                    showing=5,
                    upcoming=6,
                    duplicate=1,
                    deduplicated_total=11,
                ),
                result_stats=UpdateMovieResultStatsResult(
                    existing=9,
                    added=1,
                    added_movie_ids=[1001],
                    updated=4,
                    updated_movie_ids=[2, 3, 4, 5],
                    removed=0,
                    total=10,
                ),
            ),
            extra_info=UpdateMovieExtraInfoResult(updated_count=1),
        )

    monkeypatch.setattr(update_service, "update_movie", update_movie)
    with client.stream(
        "GET", "/api/update/movie-stream?city_id=10&force_update_all=false"
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"type":"progress"' in body
    assert '"message":"正在抓取电影列表"' in body
    assert '"type":"complete"' in body
    assert '"added_movie_ids":[1001]' in body
