from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import movie_scheduler.features.movie.repository as repository_module
from movie_scheduler.core.db import Base, database_manager
from movie_scheduler.features.movie.models import Movie
from movie_scheduler.features.movie.repository import MovieRepository


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
