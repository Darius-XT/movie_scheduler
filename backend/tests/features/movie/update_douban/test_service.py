from __future__ import annotations

import asyncio
from types import SimpleNamespace

import movie_scheduler.features.movie.update_douban.service as douban_module
from movie_scheduler.features.movie.update_douban.service import DoubanMovieSupplement, UpdateDoubanService


def test_update_douban_updates_changed_existing_info(monkeypatch) -> None:
    service = UpdateDoubanService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(id=1522535, title="Normandie", score="7.9", douban_url="https://old.example")

    monkeypatch.setattr(douban_module.movie_repository, "get_all_movies", lambda: [movie])
    monkeypatch.setattr(douban_module.movie_repository, "save_movie", lambda row: saved.append(row) or True)
    monkeypatch.setattr(
        service,
        "fetch_movie_supplement",
        lambda _movie: DoubanMovieSupplement(score="8.2", douban_url="https://new.example"),
    )

    result = asyncio.run(service.update_all())

    assert result == 1
    assert saved == [{"id": 1522535, "score": "8.2", "douban_url": "https://new.example"}]


def test_update_douban_skips_unchanged_info(monkeypatch) -> None:
    service = UpdateDoubanService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(id=1522535, title="Normandie", score="8.2", douban_url="https://new.example")

    monkeypatch.setattr(douban_module.movie_repository, "get_all_movies", lambda: [movie])
    monkeypatch.setattr(douban_module.movie_repository, "save_movie", lambda row: saved.append(row) or True)
    monkeypatch.setattr(
        service,
        "fetch_movie_supplement",
        lambda _movie: DoubanMovieSupplement(score="8.2", douban_url="https://new.example"),
    )

    result = asyncio.run(service.update_all())

    assert result == 0
    assert saved == []


def test_update_douban_does_not_clear_meaningful_info_on_no_match(monkeypatch) -> None:
    service = UpdateDoubanService()
    saved: list[dict[str, object]] = []
    movie = SimpleNamespace(id=1522535, title="Normandie", score="8.2", douban_url="https://new.example")

    monkeypatch.setattr(douban_module.movie_repository, "get_all_movies", lambda: [movie])
    monkeypatch.setattr(douban_module.movie_repository, "save_movie", lambda row: saved.append(row) or True)
    monkeypatch.setattr(
        service,
        "fetch_movie_supplement",
        lambda _movie: DoubanMovieSupplement(score="无豆瓣评分", douban_url=None),
    )

    result = asyncio.run(service.update_all())

    assert result == 0
    assert saved == []
