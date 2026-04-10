"""V1 路由基础测试。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import RepositoryError
from app.main import app
from app.services.city_service import CityInfo, city_service
from app.services.movie_service import movie_service
from app.services.show_service import StreamCompleteEvent, show_service
from app.services.update_service import update_service
from app.use_cases.movie_selection.movie_selection_result_builder import MovieSelectionItem
from app.use_cases.update.models import UpdateProgressEvent
from app.use_cases.update.update_result_builder import (
    UpdateCinemaResult,
    UpdateMovieBaseInfoResult,
    UpdateMovieDoubanInfoResult,
    UpdateMovieExtraInfoResult,
    UpdateMovieInputStatsResult,
    UpdateMovieResult,
    UpdateMovieResultStatsResult,
)

client = TestClient(app, raise_server_exceptions=False)

UpdateProgressCallback = Callable[[UpdateProgressEvent], None]


def test_city_endpoint_returns_city_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """城市接口应返回城市列表。"""

    def list_city() -> list[CityInfo]:
        return [CityInfo(name="上海", id=10)]

    monkeypatch.setattr(city_service, "list_city", list_city)
    response = client.get("/api/v1/cities")

    assert response.status_code == 200
    assert response.json() == {"cities": [{"name": "上海", "id": 10}]}


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
    with client.stream("GET", "/api/v1/update/cinema-stream?city_id=10") as response:
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
            douban_info=UpdateMovieDoubanInfoResult(updated_count=2),
        )

    monkeypatch.setattr(update_service, "update_movie", update_movie)
    with client.stream("GET", "/api/v1/update/movie-stream?city_id=10&force_update_all=false") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"type":"progress"' in body
    assert '"message":"正在抓取电影列表"' in body
    assert '"type":"complete"' in body
    assert '"added_movie_ids":[1001]' in body
    assert '"douban_info":{"updated_count":2}' in body


def test_select_movie_endpoint_returns_movie_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """电影筛选接口应返回电影列表。"""

    async def select_movie(selection_mode: str = "all") -> list[MovieSelectionItem]:
        assert selection_mode == "showing"
        return [
            MovieSelectionItem(
                id=1,
                title="测试电影",
                score=None,
                douban_url=None,
                genres=None,
                actors=None,
                release_date=None,
                is_showing=True,
                director=None,
                country=None,
                language=None,
                duration=None,
                description=None,
            )
        ]

    monkeypatch.setattr(movie_service, "select_movie", select_movie)
    response = client.post("/api/v1/movies/select", json={"selection_mode": "showing"})

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {
            "movies": [
                {
                    "id": 1,
                    "title": "测试电影",
                    "score": None,
                    "douban_url": None,
                    "genres": None,
                    "actors": None,
                    "release_date": None,
                    "is_showing": True,
                    "director": None,
                    "country": None,
                    "language": None,
                    "duration": None,
                    "description": None,
                }
            ]
        },
    }


def test_fetch_show_stream_endpoint_uses_v1_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """流式接口应挂载到 V1 路径。"""

    async def stream_show(
        movie_ids: list[int],
        city_id: int | None = None,
    ) -> AsyncIterator[StreamCompleteEvent]:
        assert movie_ids == [1, 2]
        assert city_id == 10
        yield StreamCompleteEvent(type="complete", data=[])

    monkeypatch.setattr(show_service, "stream_show", stream_show)

    with client.stream("GET", "/api/v1/shows/fetch-stream?movie_ids=1,2&city_id=10") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"type":"complete"' in body


def test_select_movie_endpoint_uses_global_exception_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    """接口异常应由统一异常处理器返回标准响应。"""

    async def select_movie(selection_mode: str = "all") -> list[MovieSelectionItem]:
        del selection_mode
        raise RuntimeError("boom")

    monkeypatch.setattr(movie_service, "select_movie", select_movie)
    response = client.post("/api/v1/movies/select", json={"selection_mode": "showing"})

    assert response.status_code == 500
    assert response.json() == {"success": False, "error": "服务器内部错误"}


def test_select_movie_endpoint_maps_repository_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """数据库访问失败应映射为稳定的 500 响应。"""

    async def select_movie(selection_mode: str = "all") -> list[MovieSelectionItem]:
        del selection_mode
        raise RepositoryError("底层数据库错误")

    monkeypatch.setattr(movie_service, "select_movie", select_movie)
    response = client.post("/api/v1/movies/select", json={"selection_mode": "showing"})

    assert response.status_code == 500
    assert response.json() == {"success": False, "error": "数据库访问失败，请稍后重试"}


def test_fetch_show_stream_endpoint_masks_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """SSE 错误事件不应直接暴露内部异常原文。"""

    async def stream_show(
        movie_ids: list[int],
        city_id: int | None = None,
    ) -> AsyncIterator[StreamCompleteEvent]:
        del movie_ids, city_id
        raise RepositoryError("底层数据库错误")
        yield StreamCompleteEvent(type="complete", data=[])

    monkeypatch.setattr(show_service, "stream_show", stream_show)

    with client.stream("GET", "/api/v1/shows/fetch-stream?movie_ids=1&city_id=10") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert '"type":"error"' in body
    assert "数据库访问失败，请稍后重试" in body
