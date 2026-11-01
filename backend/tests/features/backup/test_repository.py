from typing import cast

import pytest
from pytest import MonkeyPatch
from sqlalchemy import Table
from sqlalchemy.exc import SQLAlchemyError

from movie_scheduler.core.db import database_manager
from movie_scheduler.core.exceptions import RepositoryError
from movie_scheduler.features.backup.repository import BackupWriteData, backup_repository
from movie_scheduler.features.cinema.models import Cinema
from movie_scheduler.features.movie.models import Movie
from movie_scheduler.features.plan.models import PlanningItem
from movie_scheduler.features.show.models import MovieShow


def test_read_and_replace_every_column(sample_records: BackupWriteData) -> None:
    backup_repository.replace_all(sample_records)
    saved = backup_repository.read_all()
    for model, rows, expected in (
        (Cinema, saved["cinemas"], sample_records["cinemas"]),
        (Movie, saved["movies"], sample_records["movies"]),
        (MovieShow, saved["movie_shows"], sample_records["movie_shows"]),
        (PlanningItem, saved["planning_items"], sample_records["planning_items"]),
    ):
        columns = cast(Table, getattr(model, "__table__")).columns.keys()
        assert [{name: getattr(row, name) for name in columns} for row in rows] == expected
    backup_repository.replace_all({"cinemas": [], "movies": [], "movie_shows": [], "planning_items": []})
    assert all(not rows for rows in backup_repository.read_all().values())


def test_failed_restore_rolls_back_all_tables(sample_records: BackupWriteData) -> None:
    backup_repository.replace_all(sample_records)
    broken: BackupWriteData = {
        **sample_records,
        "movies": [{**row, "title": "不应保存"} for row in sample_records["movies"]],
        "planning_items": [*sample_records["planning_items"], *sample_records["planning_items"]],
    }
    with pytest.raises(RepositoryError):
        backup_repository.replace_all(broken)
    saved = backup_repository.read_all()
    assert [getattr(row, "title") for row in saved["movies"]] == [row["title"] for row in sample_records["movies"]]
    assert len(saved["cinemas"]) == len(saved["movie_shows"]) == len(saved["planning_items"]) == 1
    assert getattr(saved["planning_items"][0], "purchased") is True


def test_read_failure_is_repository_error(monkeypatch: MonkeyPatch) -> None:
    def fail_session() -> None:
        raise SQLAlchemyError("unavailable")

    monkeypatch.setattr(database_manager, "session", fail_session)
    with pytest.raises(RepositoryError, match="读取备份失败"):
        backup_repository.read_all()
