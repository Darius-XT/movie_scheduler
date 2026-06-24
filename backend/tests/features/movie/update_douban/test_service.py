from __future__ import annotations

import asyncio
from types import SimpleNamespace

from pytest import MonkeyPatch

import movie_scheduler.features.movie.update_douban.service as douban_module
from movie_scheduler.features.movie.update_douban.service import DoubanMovieSupplement, UpdateDoubanService


def test_update_douban_updates_changed_existing_info(monkeypatch: MonkeyPatch) -> None:
    service = UpdateDoubanService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(id=1522535, title="Normandie", score="7.9", douban_url="https://old.example")

    def fake_get_all_movies() -> list[object]:
        return [movie]

    def fake_save_movie(row: dict[str, object]) -> bool:
        saved.append(row)
        return True

    def fake_fetch_movie_supplement(_movie: object) -> DoubanMovieSupplement:
        return DoubanMovieSupplement(score="8.2", douban_url="https://new.example")

    monkeypatch.setattr(douban_module.movie_repository, "get_all_movies", fake_get_all_movies)
    monkeypatch.setattr(douban_module.movie_repository, "save_movie", fake_save_movie)
    monkeypatch.setattr(
        service,
        "fetch_movie_supplement",
        fake_fetch_movie_supplement,
    )

    result = asyncio.run(service.update_all())

    assert result == 1
    assert saved == [{"id": 1522535, "score": "8.2", "douban_url": "https://new.example"}]


def test_update_douban_skips_unchanged_info(monkeypatch: MonkeyPatch) -> None:
    service = UpdateDoubanService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(id=1522535, title="Normandie", score="8.2", douban_url="https://new.example")

    def fake_get_all_movies() -> list[object]:
        return [movie]

    def fake_save_movie(row: dict[str, object]) -> bool:
        saved.append(row)
        return True

    def fake_fetch_movie_supplement(_movie: object) -> DoubanMovieSupplement:
        return DoubanMovieSupplement(score="8.2", douban_url="https://new.example")

    monkeypatch.setattr(douban_module.movie_repository, "get_all_movies", fake_get_all_movies)
    monkeypatch.setattr(douban_module.movie_repository, "save_movie", fake_save_movie)
    monkeypatch.setattr(
        service,
        "fetch_movie_supplement",
        fake_fetch_movie_supplement,
    )

    result = asyncio.run(service.update_all())

    assert result == 0
    assert saved == []


def test_update_douban_does_not_clear_meaningful_info_on_no_match(monkeypatch: MonkeyPatch) -> None:
    service = UpdateDoubanService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(id=1522535, title="Normandie", score="8.2", douban_url="https://new.example")

    def fake_get_all_movies() -> list[object]:
        return [movie]

    def fake_save_movie(row: dict[str, object]) -> bool:
        saved.append(row)
        return True

    def fake_fetch_movie_supplement(_movie: object) -> DoubanMovieSupplement:
        return DoubanMovieSupplement(score="无豆瓣评分", douban_url=None)

    monkeypatch.setattr(douban_module.movie_repository, "get_all_movies", fake_get_all_movies)
    monkeypatch.setattr(douban_module.movie_repository, "save_movie", fake_save_movie)
    monkeypatch.setattr(
        service,
        "fetch_movie_supplement",
        fake_fetch_movie_supplement,
    )

    result = asyncio.run(service.update_all())

    assert result == 0
    assert saved == []
