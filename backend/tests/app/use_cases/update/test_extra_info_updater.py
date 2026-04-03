from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import cast

import pytest

from app.models.movie import MovieWriteData
from app.repositories.movie_repository import movie_repository
from app.use_cases.update.movie_info.extra_info.extra_info_parser import MovieExtraInfoParser
from app.use_cases.update.movie_info.extra_info.extra_info_scraper import MovieExtraInfoScraper
from app.use_cases.update.movie_info.extra_info.extra_info_updater import MovieExtraInfoUpdater
from app.use_cases.update.movie_info.extra_info.models import MovieExtraInfo


@dataclass
class FakeMovie:
    id: int
    title: str


class FakeScraper:
    def __init__(self) -> None:
        self.active_requests = 0
        self.max_active_requests = 0
        self.lock = threading.Lock()

    def scrape_details(self, movie_id: int) -> tuple[bool, str]:
        with self.lock:
            self.active_requests += 1
            self.max_active_requests = max(self.max_active_requests, self.active_requests)
        time.sleep(0.05)
        with self.lock:
            self.active_requests -= 1
        return True, str(movie_id)


class FakeParser:
    def parse_details(self, content: str) -> MovieExtraInfo:
        return MovieExtraInfo(
            id=int(content),
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

    fake_scraper = FakeScraper()
    updater = MovieExtraInfoUpdater()
    updater.scraper = cast(MovieExtraInfoScraper, fake_scraper)
    updater.parser = cast(MovieExtraInfoParser, FakeParser())

    result = asyncio.run(updater.update_all_movie_extra_info())

    assert result == 6
    assert len(saved_movie_ids) == 6
    assert set(saved_movie_ids) == {1, 2, 3, 4, 5, 6}
    assert fake_scraper.max_active_requests >= 1
