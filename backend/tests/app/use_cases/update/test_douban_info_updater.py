"""豆瓣信息更新器测试。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import cast

import pytest

from app.models.movie import MovieWriteData
from app.repositories.movie_repository import movie_repository
from app.use_cases.update.movie_info.douban.douban_info_enricher import DoubanInfoEnricher
from app.use_cases.update.movie_info.douban.douban_info_updater import MovieDoubanInfoUpdater
from app.use_cases.update.movie_info.douban.models import DoubanMovieSupplement


@dataclass
class FakeMovie:
    id: int
    title: str
    release_date: str | None = None
    actors: str | None = None


class FakeEnricher:
    def fetch_movie_supplement(self, movie: FakeMovie) -> DoubanMovieSupplement:
        return DoubanMovieSupplement(
            score=f"豆瓣{movie.id}",
            douban_url=f"https://movie.douban.com/subject/{movie.id}/",
        )


def test_douban_info_updater_returns_zero_when_no_movies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(movie_repository, "get_movies_without_douban_info", lambda: cast(list[FakeMovie], []))
    updater = MovieDoubanInfoUpdater()

    result = asyncio.run(updater.update_all_movie_douban_info())

    assert result == 0


def test_douban_info_updater_processes_all_movies(monkeypatch: pytest.MonkeyPatch) -> None:
    movies = [FakeMovie(id=1, title="电影1"), FakeMovie(id=2, title="电影2")]
    saved_movie_ids: list[int] = []

    def save_movie(movie_data: MovieWriteData) -> bool:
        saved_movie_ids.append(movie_data["id"])
        score = movie_data.get("score")
        douban_url = movie_data.get("douban_url")
        assert score is not None and score.startswith("豆瓣")
        assert douban_url is not None and douban_url.startswith("https://movie.douban.com/subject/")
        return True

    monkeypatch.setattr(movie_repository, "get_movies_without_douban_info", lambda: movies)
    monkeypatch.setattr(movie_repository, "save_movie", save_movie)

    updater = MovieDoubanInfoUpdater(enricher=cast(DoubanInfoEnricher, FakeEnricher()))
    result = asyncio.run(updater.update_all_movie_douban_info())

    assert result == 2
    assert saved_movie_ids == [1, 2]
