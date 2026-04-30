"""豆瓣信息更新器测试。"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import cast

import pytest

from app.models.movie import MovieWriteData
from app.repositories.movie import movie_repository
from app.update.movie.douban.enricher import DoubanInfoEnricher
from app.update.movie.douban.entities import DoubanMovieSupplement
from app.update.movie.douban.updater import MovieDoubanInfoUpdater


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
            douban_url=f"https://m.douban.com/movie/subject/{movie.id}/",
        )


class SlowConcurrentFakeEnricher:
    def __init__(self) -> None:
        self.active_requests = 0
        self.max_active_requests = 0
        self.lock = threading.Lock()

    def fetch_movie_supplement(self, movie: FakeMovie) -> DoubanMovieSupplement:
        with self.lock:
            self.active_requests += 1
            self.max_active_requests = max(self.max_active_requests, self.active_requests)
        time.sleep(0.05)
        with self.lock:
            self.active_requests -= 1
        return DoubanMovieSupplement(
            score=f"豆瓣{movie.id}",
            douban_url=f"https://m.douban.com/movie/subject/{movie.id}/",
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
        assert douban_url is not None and douban_url.startswith("https://m.douban.com/movie/subject/")
        return True

    monkeypatch.setattr(movie_repository, "get_movies_without_douban_info", lambda: movies)
    monkeypatch.setattr(movie_repository, "save_movie", save_movie)

    updater = MovieDoubanInfoUpdater(enricher=cast(DoubanInfoEnricher, FakeEnricher()))
    result = asyncio.run(updater.update_all_movie_douban_info())

    assert result == 2
    assert set(saved_movie_ids) == {1, 2}


def test_douban_info_updater_limits_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    movies = [FakeMovie(id=index, title=f"电影{index}") for index in range(1, 6)]

    monkeypatch.setattr(movie_repository, "get_movies_without_douban_info", lambda: movies)
    monkeypatch.setattr(movie_repository, "save_movie", lambda movie_data: True)

    enricher = SlowConcurrentFakeEnricher()
    updater = MovieDoubanInfoUpdater(enricher=cast(DoubanInfoEnricher, enricher))
    result = asyncio.run(updater.update_all_movie_douban_info())

    assert result == 5
    assert enricher.max_active_requests <= 2
