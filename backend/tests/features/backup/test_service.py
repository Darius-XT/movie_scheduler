import asyncio
from unittest.mock import Mock

import pytest
from pytest import MonkeyPatch

from movie_scheduler.core.exceptions import AppError
from movie_scheduler.features.backup.repository import BackupWriteData, backup_repository
from movie_scheduler.features.backup.schemas import BackupResponse, RestoreBackupRequest
from movie_scheduler.features.backup.service import backup_service


def test_json_round_trip_preserves_all_data(sample_records: BackupWriteData) -> None:
    backup_repository.replace_all(sample_records)
    exported = asyncio.run(backup_service.export_backup())
    data = exported.data.model_dump()
    for name, rows in sample_records.items():
        assert data[name] == rows
    backup_repository.replace_all({"cinemas": [], "movies": [], "movie_shows": [], "planning_items": []})
    parsed = BackupResponse.model_validate_json(exported.model_dump_json())
    counts = asyncio.run(backup_service.restore_backup(RestoreBackupRequest(backup=parsed, confirm_replace=True)))
    restored = asyncio.run(backup_service.export_backup())
    assert restored.data.model_dump(exclude={"exported_at"}) == exported.data.model_dump(exclude={"exported_at"})
    assert counts.model_dump() == {"cinemas": 1, "movies": 2, "movie_shows": 1, "planning_items": 1}


@pytest.mark.parametrize(
    "problem",
    ["confirmation", "success", "movie_id", "cinema_id", "show_id", "plan_id", "show_key", "show_slot", "labels"],
)
def test_invalid_backup_never_reaches_write(
    monkeypatch: MonkeyPatch,
    sample_records: BackupWriteData,
    problem: str,
) -> None:
    backup_repository.replace_all(sample_records)
    backup = asyncio.run(backup_service.export_backup())
    confirm = problem != "confirmation"
    if problem == "success":
        backup.success = False
    elif problem == "movie_id":
        backup.data.movies.append(backup.data.movies[0])
    elif problem == "cinema_id":
        backup.data.cinemas.append(backup.data.cinemas[0])
    elif problem in {"show_id", "show_slot"}:
        duplicate = backup.data.movie_shows[0].model_copy()
        if problem == "show_slot":
            duplicate.id += 1
        backup.data.movie_shows.append(duplicate)
    elif problem in {"plan_id", "show_key"}:
        duplicate_plan = backup.data.planning_items[0].model_copy()
        if problem == "show_key":
            duplicate_plan.id += 1
        backup.data.planning_items.append(duplicate_plan)
    elif problem == "labels":
        backup.data.movies[0].is_wished = True
        backup.data.movies[0].is_skipped = True
    write = Mock()
    monkeypatch.setattr(backup_repository, "replace_all", write)
    with pytest.raises(AppError):
        asyncio.run(backup_service.restore_backup(RestoreBackupRequest(backup=backup, confirm_replace=confirm)))
    write.assert_not_called()
