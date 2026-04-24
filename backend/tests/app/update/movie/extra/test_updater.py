from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import cast

import pytest

from app.models.movie import MovieWriteData
from app.repositories.movie import movie_repository
from app.update.movie.extra.client import MovieExtraInfoClient
from app.update.movie.extra.entities import MovieExtraInfo
from app.update.movie.extra.updater import MovieExtraInfoUpdater


@dataclass
class FakeMovie:
    id: int
    title: str


class FakeClient:
    def __init__(self) -> None:
        self.active_requests = 0
        self.max_active_requests = 0
        self.lock = threading.Lock()

    def fetch_details(self, movie_id: int) -> MovieExtraInfo:
        with self.lock:
            self.active_requests += 1
            self.max_active_requests = max(self.max_active_requests, self.active_requests)
        time.sleep(0.05)
        with self.lock:
            self.active_requests -= 1
        return MovieExtraInfo(
            id=movie_id,
            director="导演",
            country="中国大陆",
            language="汉语普通话",
            duration="120min",
            description="简介",
        )


def test_extra_info_updater_returns_zero_when_no_movies(monkeypatch: pytest.MonkeyPatch) -> None:
    def get_movies_without_details() -> list[FakeMovie]:
        return []

    monkeypatch.setattr(movie_repository, "get_movies_without_details", get_movies_without_details)
    updater = MovieExtraInfoUpdater()

    result = asyncio.run(updater.update_all_movie_extra_info())

    assert result == 0


def test_extra_info_updater_processes_all_movies(monkeypatch: pytest.MonkeyPatch) -> None:
    movies = [FakeMovie(id=index, title=f"电影{index}") for index in range(1, 7)]

    def get_movies_without_details() -> list[FakeMovie]:
        return movies

    saved_movie_ids: list[int] = []

    def save_movie(movie_data: MovieWriteData) -> bool:
        saved_movie_ids.append(movie_data["id"])
        return True

    monkeypatch.setattr(movie_repository, "get_movies_without_details", get_movies_without_details)
    monkeypatch.setattr(movie_repository, "save_movie", save_movie)

    fake_client = FakeClient()
    updater = MovieExtraInfoUpdater()
    updater.client = cast(MovieExtraInfoClient, fake_client)

    result = asyncio.run(updater.update_all_movie_extra_info())

    assert result == 6
    assert len(saved_movie_ids) == 6
    assert set(saved_movie_ids) == {1, 2, 3, 4, 5, 6}
    assert fake_client.max_active_requests >= 1
