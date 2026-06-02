"""电影服务测试。"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.core.exceptions import AppError
from app.movie.entities import MovieSelectionItem
from app.movie.service import movie_service


@dataclass(slots=True)
class FakeMovieRecord:
    id: int
    is_wished: bool
    title: str = "测试电影"
    score: str | None = None
    douban_url: str | None = None
    genres: str | None = None
    actors: str | None = None
    release_date: str | None = None
    is_showing: bool = True
    director: str | None = None
    country: str | None = None
    language: str | None = None
    duration: str | None = None
    description: str | None = None
    first_showing_at: object = None


@pytest.mark.anyio
async def test_movie_service_uses_default_selection_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """未传上映状态时应回退到全部模式。"""

    def select_all(selection_mode: str) -> list[MovieSelectionItem]:
        assert selection_mode == "all"
        return [
            MovieSelectionItem(
                id=1, title=None, score=None, douban_url=None, genres=None, actors=None,
                release_date=None, is_showing=False, is_wished=False, director=None, country=None,
                language=None, duration=None, description=None, first_showing_at=None,
            )
        ]

    monkeypatch.setattr(movie_service.selector, "select_movie", select_all)
    result = await movie_service.select_movie()

    assert len(result) == 1
    assert result[0].id == 1


def test_movie_service_rejects_invalid_selection_mode() -> None:
    """无效的上映状态筛选值应被拒绝。"""
    with pytest.raises(AppError):
        movie_service._normalize_selection_mode("invalid")  # pyright: ignore[reportPrivateUsage, reportArgumentType]


@pytest.mark.anyio
async def test_set_movie_wished_schedules_single_movie_show_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """加入想看后应调度单片场次后台刷新。"""
    scheduled: list[int] = []

    def set_movie_wished(movie_id: int, is_wished: bool) -> bool:
        assert movie_id == 1
        assert is_wished is True
        return True

    def get_movie_by_id(movie_id: int) -> FakeMovieRecord:
        return FakeMovieRecord(id=movie_id, is_wished=True)

    def schedule_movie_show_refresh(movie_id: int) -> None:
        scheduled.append(movie_id)

    monkeypatch.setattr("app.movie.service.movie_repository.set_movie_wished", set_movie_wished)
    monkeypatch.setattr("app.movie.service.movie_repository.get_movie_by_id", get_movie_by_id)
    monkeypatch.setattr(movie_service, "_schedule_movie_show_refresh", schedule_movie_show_refresh)

    result = await movie_service.set_movie_wished(1, True)

    assert result.id == 1
    assert result.is_wished is True
    assert scheduled == [1]


@pytest.mark.anyio
async def test_set_movie_unwished_deletes_shows_without_scheduling_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """移出想看后应删除场次,且不调度后台刷新。"""
    deleted: list[int] = []

    def set_movie_wished(movie_id: int, is_wished: bool) -> bool:
        del movie_id, is_wished
        return True

    def get_movie_by_id(movie_id: int) -> FakeMovieRecord:
        return FakeMovieRecord(id=movie_id, is_wished=False)

    def delete_for_movie(movie_id: int) -> None:
        deleted.append(movie_id)

    def schedule_movie_show_refresh(movie_id: int) -> None:
        del movie_id
        raise AssertionError("不应调度刷新")

    monkeypatch.setattr("app.movie.service.movie_repository.set_movie_wished", set_movie_wished)
    monkeypatch.setattr("app.movie.service.movie_repository.get_movie_by_id", get_movie_by_id)
    monkeypatch.setattr("app.movie.service.movie_show_repository.delete_for_movie", delete_for_movie)
    monkeypatch.setattr(movie_service, "_schedule_movie_show_refresh", schedule_movie_show_refresh)

    result = await movie_service.set_movie_wished(1, False)

    assert result.id == 1
    assert result.is_wished is False
    assert deleted == [1]
