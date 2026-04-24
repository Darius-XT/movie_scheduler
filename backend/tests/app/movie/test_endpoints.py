"""电影接口测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.app import app
from app.core.exceptions import RepositoryError
from app.movie.entities import MovieSelectionItem
from app.movie.service import movie_service

client = TestClient(app, raise_server_exceptions=False)


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
                first_seen_at=None,
            )
        ]

    monkeypatch.setattr(movie_service, "select_movie", select_movie)
    response = client.post("/api/movies/select", json={"selection_mode": "showing"})

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
                    "first_seen_at": None,
                }
            ]
        },
    }


def test_select_movie_endpoint_uses_global_exception_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """接口异常应由统一异常处理器返回标准响应。"""

    async def select_movie(selection_mode: str = "all") -> list[MovieSelectionItem]:
        del selection_mode
        raise RuntimeError("boom")

    monkeypatch.setattr(movie_service, "select_movie", select_movie)
    response = client.post("/api/movies/select", json={"selection_mode": "showing"})

    assert response.status_code == 500
    assert response.json() == {"success": False, "error": "服务器内部错误"}


def test_select_movie_endpoint_maps_repository_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """数据库访问失败应映射为稳定的 500 响应。"""

    async def select_movie(selection_mode: str = "all") -> list[MovieSelectionItem]:
        del selection_mode
        raise RepositoryError("底层数据库错误")

    monkeypatch.setattr(movie_service, "select_movie", select_movie)
    response = client.post("/api/movies/select", json={"selection_mode": "showing"})

    assert response.status_code == 500
    assert response.json() == {"success": False, "error": "数据库访问失败，请稍后重试"}
