"""电影筛选用例测试。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass

import pytest

from app.core.exceptions import RepositoryError
from app.use_cases.movie_selection.movie_selection_result_builder import MovieRecord, MovieSelectionItem
from app.use_cases.movie_selection.movie_selector import MovieSelector


@dataclass(slots=True)
class FakeMovie:
    id: int | None
    title: str | None
    country: str | None
    release_date: str | None
    score: str | None = None
    douban_url: str | None = None
    genres: str | None = None
    actors: str | None = None
    is_showing: bool = False
    director: str | None = None
    language: str | None = None
    duration: str | None = None
    description: str | None = None


class FakeMovieSelectionGateway:
    """用于测试的电影筛选网关。"""

    def __init__(self, movies: list[FakeMovie]) -> None:
        self._movies = movies

    def get_all_movies(self) -> Sequence[MovieRecord]:
        return self._movies


class FakeMovieSelectionResultBuilder:
    """用于测试的电影结果构建器。"""

    def build_movie(self, movie: MovieRecord) -> MovieSelectionItem:
        return MovieSelectionItem(
            id=movie.id,
            title=movie.title,
            score=None,
            douban_url=None,
            genres=None,
            actors=None,
            release_date=None,
            is_showing=movie.is_showing,
            director=None,
            country=None,
            language=None,
            duration=None,
            description=None,
        )


def test_movie_selector_filters_showing_movies() -> None:
    """应只返回正在上映的电影。"""
    movies = [
        FakeMovie(id=1, title="正在上映", country="中国大陆", release_date="2025-01-01", is_showing=True),
        FakeMovie(id=2, title="即将上映", country="中国大陆", release_date="2025-05-01", is_showing=False),
    ]
    selector = MovieSelector(
        gateway=FakeMovieSelectionGateway(movies),
        result_builder=FakeMovieSelectionResultBuilder(),
    )

    result = selector.select_movie(selection_mode="showing")

    assert [asdict(item) for item in result] == [
        {
            "id": 1,
            "title": "正在上映",
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


def test_movie_selector_filters_upcoming_movies() -> None:
    """应只返回即将上映的电影。"""
    movies = [
        FakeMovie(id=1, title="正在上映", country="中国大陆", release_date="2025-01-01", is_showing=True),
        FakeMovie(id=2, title="即将上映", country="中国大陆", release_date="2025-05-01", is_showing=False),
    ]
    selector = MovieSelector(
        gateway=FakeMovieSelectionGateway(movies),
        result_builder=FakeMovieSelectionResultBuilder(),
    )

    result = selector.select_movie(selection_mode="upcoming")

    assert [asdict(item) for item in result] == [
        {
            "id": 2,
            "title": "即将上映",
            "score": None,
            "douban_url": None,
            "genres": None,
            "actors": None,
            "release_date": None,
            "is_showing": False,
            "director": None,
            "country": None,
            "language": None,
            "duration": None,
            "description": None,
        }
    ]


def test_movie_selector_returns_all_movies_for_all_mode() -> None:
    """全部模式应返回所有电影。"""
    movies = [
        FakeMovie(id=1, title="正在上映", country="中国大陆", release_date="2025-01-01", is_showing=True),
        FakeMovie(id=2, title="即将上映", country="中国大陆", release_date="2025-05-01", is_showing=False),
    ]
    selector = MovieSelector(
        gateway=FakeMovieSelectionGateway(movies),
        result_builder=FakeMovieSelectionResultBuilder(),
    )

    result = selector.select_movie(selection_mode="all")

    assert [item.id for item in result] == [1, 2]


def test_movie_selector_returns_empty_list_when_no_movies() -> None:
    """没有电影数据时应返回空列表。"""
    selector = MovieSelector(
        gateway=FakeMovieSelectionGateway([]),
        result_builder=FakeMovieSelectionResultBuilder(),
    )

    assert selector.select_movie(selection_mode="all") == []


def test_movie_selector_propagates_gateway_error() -> None:
    """网关读取失败时不应被静默吞掉。"""

    class FailingMovieSelectionGateway:
        def get_all_movies(self) -> Sequence[MovieRecord]:
            raise RepositoryError("读取电影列表失败")

    selector = MovieSelector(
        gateway=FailingMovieSelectionGateway(),
        result_builder=FakeMovieSelectionResultBuilder(),
    )

    with pytest.raises(RepositoryError):
        selector.select_movie(selection_mode="all")
