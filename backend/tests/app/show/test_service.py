"""场次服务测试。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from app.core.exceptions import AppError
from app.show.result_builder import CinemaShowData, FinalMovieShowData, ShowItem
from app.show.service import show_service


@dataclass(slots=True)
class FakeMovie:
    id: int
    is_wished: bool
    shows_updated_at: datetime | None = None


@dataclass(slots=True)
class FakeShow:
    movie_id: int
    cinema_id: int
    cinema_name: str
    date: str
    time: str
    price: str | None = None


def test_show_service_uses_default_city_id_when_missing() -> None:
    """未传城市时应回退到默认城市。"""
    assert show_service._normalize_city_id(None) == 10  # pyright: ignore[reportPrivateUsage]


def test_show_service_rejects_unsupported_city_id() -> None:
    """不支持的城市 ID 应被拒绝。"""
    with pytest.raises(AppError):
        show_service._normalize_city_id(999)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.anyio
async def test_refresh_movie_shows_touches_timestamp_when_result_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """单片刷新即使没有场次,也应清空旧场次并刷新电影场次更新时间。"""
    replaced: list[tuple[int, list[object]]] = []
    touched: list[int] = []

    def get_movie_by_id(movie_id: int) -> FakeMovie:
        return FakeMovie(id=movie_id, is_wished=True)

    async def fetch_shows_for_selected_movies(movie_ids: list[int], city_id: int) -> list[FinalMovieShowData]:
        assert movie_ids == [1]
        assert city_id == 10
        return []

    def replace_for_movie(movie_id: int, shows: list[object]) -> int:
        replaced.append((movie_id, shows))
        return len(shows)

    def touch_shows_updated_at(movie_id: int) -> None:
        touched.append(movie_id)

    monkeypatch.setattr("app.show.service.movie_repository.get_movie_by_id", get_movie_by_id)
    monkeypatch.setattr("app.show.service.show_fetcher.fetch_shows_for_selected_movies", fetch_shows_for_selected_movies)
    monkeypatch.setattr("app.show.service.movie_show_repository.replace_for_movie", replace_for_movie)
    monkeypatch.setattr("app.show.service.movie_repository.touch_shows_updated_at", touch_shows_updated_at)

    result = await show_service.refresh_movie_shows(1)

    assert result == 0
    assert replaced == [(1, [])]
    assert touched == [1]


@pytest.mark.anyio
async def test_refresh_movie_shows_deletes_when_movie_was_removed_from_wish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """抓取结束后若电影已移出想看,不应写回场次。"""
    states = [True, False]
    deleted: list[int] = []
    replaced: list[int] = []
    touched: list[int] = []

    def get_movie_by_id(movie_id: int) -> FakeMovie:
        return FakeMovie(id=movie_id, is_wished=states.pop(0))

    async def fetch_shows_for_selected_movies(movie_ids: list[int], city_id: int) -> list[FinalMovieShowData]:
        del city_id
        return [
            FinalMovieShowData(
                movie_id=movie_ids[0],
                cinemas=[
                    CinemaShowData(
                        cinema_id=10,
                        cinema_name="影院A",
                        shows=[ShowItem(date="2026-06-02", time="19:30", price="39")],
                    )
                ],
            )
        ]

    def delete_for_movie(movie_id: int) -> None:
        deleted.append(movie_id)

    def replace_for_movie(movie_id: int, shows: list[object]) -> None:
        del shows
        replaced.append(movie_id)

    def touch_shows_updated_at(movie_id: int) -> None:
        touched.append(movie_id)

    monkeypatch.setattr("app.show.service.movie_repository.get_movie_by_id", get_movie_by_id)
    monkeypatch.setattr("app.show.service.show_fetcher.fetch_shows_for_selected_movies", fetch_shows_for_selected_movies)
    monkeypatch.setattr("app.show.service.movie_show_repository.delete_for_movie", delete_for_movie)
    monkeypatch.setattr("app.show.service.movie_show_repository.replace_for_movie", replace_for_movie)
    monkeypatch.setattr("app.show.service.movie_repository.touch_shows_updated_at", touch_shows_updated_at)

    result = await show_service.refresh_movie_shows(1)

    assert result == 0
    assert deleted == [1]
    assert replaced == []
    assert touched == []


@pytest.mark.anyio
async def test_get_single_movie_shows_returns_only_requested_movie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET shows 的单片分支只返回指定电影场次和该电影刷新时间。"""
    updated_at = datetime(2026, 6, 2, 12, 30, 0)

    def get_movie_by_id(movie_id: int) -> FakeMovie:
        assert movie_id == 2
        return FakeMovie(id=2, is_wished=True, shows_updated_at=updated_at)

    def list_for_movies(movie_ids: list[int]) -> list[FakeShow]:
        assert movie_ids == [2]
        return [
            FakeShow(
                movie_id=2,
                cinema_id=10,
                cinema_name="影院A",
                date="2026-06-02",
                time="19:30",
                price="39",
            )
        ]

    monkeypatch.setattr("app.show.service.movie_repository.get_movie_by_id", get_movie_by_id)
    monkeypatch.setattr("app.show.service.movie_show_repository.list_for_movies", list_for_movies)

    result = await show_service.get_shows_for_wished_movies(movie_id=2)

    assert result == {
        "movies": [
            {
                "movie_id": 2,
                "shows": [
                    {
                        "cinema_id": 10,
                        "cinema_name": "影院A",
                        "date": "2026-06-02",
                        "time": "19:30",
                        "price": "39",
                    }
                ],
            }
        ],
        "last_fetched_at": "2026-06-02T12:30:00",
    }


@pytest.mark.anyio
async def test_get_single_movie_shows_returns_empty_when_movie_is_not_wished(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """单片查询遇到非想看电影时应返回空列表。"""

    def get_movie_by_id(movie_id: int) -> FakeMovie:
        return FakeMovie(id=movie_id, is_wished=False)

    monkeypatch.setattr("app.show.service.movie_repository.get_movie_by_id", get_movie_by_id)

    result = await show_service.get_shows_for_wished_movies(movie_id=2)

    assert result == {"movies": [], "last_fetched_at": None}
