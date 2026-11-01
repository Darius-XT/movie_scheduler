from collections.abc import Iterator
from datetime import datetime

import pytest
from pytest import MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from movie_scheduler.core.db import Base, database_manager
from movie_scheduler.features.backup.repository import BackupWriteData


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch: MonkeyPatch) -> Iterator[None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(database_manager, "engine", engine)
    monkeypatch.setattr(database_manager, "session_factory", sessionmaker(bind=engine, expire_on_commit=False))
    monkeypatch.setattr(database_manager, "_initialized", True)
    yield
    engine.dispose()


@pytest.fixture
def sample_records() -> BackupWriteData:
    timestamp = datetime(2026, 11, 2, 10, 20, 30, 123456)
    movie: dict[str, object] = {
        "id": 123,
        "title": "电影 & 中文",
        "score": "8.5",
        "douban_url": "https://example.test/movie",
        "genres": "剧情",
        "actors": "演员",
        "release_date": "2026-11-02",
        "is_showing": True,
        "is_wished": True,
        "is_skipped": False,
        "is_watched": False,
        "channels": ["bilibili"],
        "viewing_location": "cinema",
        "director": "导演",
        "country": "中国",
        "language": "中文",
        "duration": "120分钟",
        "description": "简介",
        "first_showing_at": timestamp,
        "updated_at": timestamp,
        "shows_updated_at": timestamp,
    }
    manual: dict[str, object] = {
        **movie,
        "id": -9007199254740990,
        "title": "手动电影",
        "is_showing": False,
        "is_wished": False,
        "is_watched": True,
        "channels": [],
        "viewing_location": None,
        "updated_at": None,
        "first_showing_at": None,
        "shows_updated_at": None,
    }
    return {
        "cinemas": [
            {"id": 11, "name": "影院", "address": "地址", "price": None, "allow_refund": None, "updated_at": None}
        ],
        "movies": [manual, movie],
        "movie_shows": [
            {
                "id": 42,
                "movie_id": 123,
                "cinema_id": 11,
                "cinema_name": "影院",
                "date": "2026-11-03",
                "time": "18:00",
                "price": "35",
                "created_at": timestamp,
            }
        ],
        "planning_items": [
            {
                "id": 52,
                "show_key": "manual-52",
                "movie_id": 0,
                "movie_title": "手动行程",
                "date": "2026-11-04",
                "time": "20:00",
                "cinema_id": 0,
                "cinema_name": "自定地点",
                "price": None,
                "duration_minutes": 90,
                "purchased": True,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        ],
    }
