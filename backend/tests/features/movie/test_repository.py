from __future__ import annotations

from pathlib import Path
import pytest

from pytest import MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import movie_scheduler.features.movie.repository as repository_module
from movie_scheduler.core.db import Base, database_manager
from movie_scheduler.features.movie.models import Movie
from movie_scheduler.features.movie.repository import MovieRepository


def test_viewing_location_persists_independently(monkeypatch: MonkeyPatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database_manager, "session_factory", sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(database_manager, "_initialized", True)
    repository = MovieRepository()
    repository.save_movie({"id": 1, "title": "电影", "is_wished": True, "channels": ["bilibili"]})
    for location in ["home", "cinema", None]:
        saved = repository.set_movie_viewing_location({"id": 1, "viewing_location": location})
        assert saved is not None and bool(saved.is_wished)
        assert getattr(saved, "channels") == ["bilibili"]
        repository.save_movie({"id": 1, "title": "更新电影信息"})
        loaded = repository.get_movie_by_id(1)
        assert loaded is not None and getattr(loaded, "viewing_location") == location
    assert repository.set_movie_viewing_location({"id": 999, "viewing_location": "home"}) is None


def test_movie_channels_persist_without_changing_labels(monkeypatch: MonkeyPatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database_manager, "session_factory", sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(database_manager, "_initialized", True)
    repository = MovieRepository()
    repository.save_movie({"id": 1, "title": "老片", "is_wished": True})
    saved = repository.set_movie_channels({"id": 1, "channels": ["bilibili"]})
    assert saved is not None and bool(saved.is_wished)
    repository.save_movie({"id": 1, "title": "更新信息"})
    loaded = repository.get_movie_by_id(1)
    assert loaded is not None
    assert getattr(loaded, "channels") == ["bilibili"]
    cleared = repository.set_movie_channels({"id": 1, "channels": []})
    assert cleared is not None and getattr(cleared, "channels") == []
    assert repository.set_movie_channels({"id": 999, "channels": []}) is None


@pytest.mark.parametrize("initial", ["none", "wished", "skipped", "watched"])
@pytest.mark.parametrize("target", ["none", "wished", "skipped", "watched"])
def test_label_transitions_are_persisted_and_exclusive(
    monkeypatch: MonkeyPatch, initial: str, target: str,
) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database_manager, "session_factory", sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(database_manager, "_initialized", True)
    repository = MovieRepository()
    repository.save_movie({"id": 123, "title": "电影", "is_wished": initial == "wished", "is_skipped": initial == "skipped", "is_watched": initial == "watched"})
    assert repository.set_movie_label({"id": 123, "is_wished": target == "wished", "is_skipped": target == "skipped", "is_watched": target == "watched"})
    movie = repository.get_movie_by_id(123)
    assert movie is not None
    assert bool(movie.is_wished) == (target == "wished")
    assert bool(movie.is_skipped) == (target == "skipped")
    assert bool(movie.is_watched) == (target == "watched")
    assert len(repository.list_wished_movies()) == int(target == "wished")
    repository.save_movie({"id": 123, "title": "更新片名"})
    updated = repository.get_movie_by_id(123)
    assert updated is not None
    assert bool(updated.is_skipped) == (target == "skipped")
    assert bool(updated.is_watched) == (target == "watched")
    assert repository.set_movie_label({"id": 999, "is_skipped": True}) is False
    assert repository.set_movie_wished(123, True)
    restored = repository.get_movie_by_id(123)
    assert restored is not None and bool(restored.is_wished) and not bool(restored.is_skipped)
    assert not bool(restored.is_watched)


def test_manual_movie_persists_and_can_be_removed_from_wishes(monkeypatch: MonkeyPatch) -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database_manager, "session_factory", sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(database_manager, "_initialized", True)
    repository = MovieRepository()
    movie = repository.create_manual_movie({"id": -123, "title": "手动电影", "is_wished": True})
    assert getattr(movie, "title") == "手动电影"
    assert [item.id for item in repository.list_wished_movies()] == [-123]
    assert repository.set_movie_wished(-123, False)
    assert repository.list_wished_movies() == []
    assert repository.get_movie_by_id(-123) is not None


def test_movie_update_status_is_independent_from_show_update_timestamp(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setattr(database_manager, "engine", engine)
    monkeypatch.setattr(database_manager, "session_factory", session_factory)
    monkeypatch.setattr(database_manager, "_initialized", True)

    repository = MovieRepository()
    with database_manager.transaction() as session:
        session.add(Movie(id=1, title="Movie A", is_wished=True))

    assert repository.get_movies_last_updated_at() is None

    repository.touch_movies_last_updated_at()
    movie_last_updated_at = repository.get_movies_last_updated_at()

    assert movie_last_updated_at is not None

    repository.save_movie({"id": 1, "title": "Movie A Updated"})
    assert repository.get_movies_last_updated_at() == movie_last_updated_at

    repository.touch_shows_updated_at(1)

    assert repository.get_movies_last_updated_at() == movie_last_updated_at
    assert repository.get_latest_shows_updated_at([1]) is not None


def test_save_movie_logs_existing_title_when_partial_update_has_no_title(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    messages: list[tuple[str, tuple[object, ...]]] = []

    def record_debug(message: str, *args: object) -> None:
        messages.append((message, args))

    monkeypatch.setattr(database_manager, "engine", engine)
    monkeypatch.setattr(database_manager, "session_factory", session_factory)
    monkeypatch.setattr(database_manager, "_initialized", True)
    monkeypatch.setattr(repository_module.logger, "debug", record_debug)

    repository = MovieRepository()
    with database_manager.transaction() as session:
        session.add(Movie(id=1, title="Movie A", is_wished=True))

    repository.save_movie({"id": 1, "duration": "100min"})

    assert messages[-1][1] == ("Movie A", 1)
