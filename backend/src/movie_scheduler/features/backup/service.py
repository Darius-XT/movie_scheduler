"""备份导出和恢复校验。"""

import asyncio
from collections.abc import Hashable, Iterable
from datetime import datetime
from zoneinfo import ZoneInfo

from movie_scheduler.core.exceptions import AppError
from movie_scheduler.features.backup.repository import BackupWriteData, backup_repository
from movie_scheduler.features.backup.schemas import (
    BackupCounts,
    BackupData,
    BackupResponse,
    CinemaBackup,
    MovieBackup,
    MovieShowBackup,
    PlanningItemBackup,
    RestoreBackupRequest,
)


class BackupService:
    async def export_backup(self) -> BackupResponse:
        records = await asyncio.to_thread(backup_repository.read_all)
        return BackupResponse(
            data=BackupData(
                application="movie-scheduler",
                format_version=1,
                exported_at=datetime.now(ZoneInfo("Asia/Shanghai")),
                cinemas=[CinemaBackup.model_validate(row) for row in records["cinemas"]],
                movies=[MovieBackup.model_validate(row) for row in records["movies"]],
                movie_shows=[MovieShowBackup.model_validate(row) for row in records["movie_shows"]],
                planning_items=[PlanningItemBackup.model_validate(row) for row in records["planning_items"]],
            )
        )

    async def restore_backup(self, request: RestoreBackupRequest) -> BackupCounts:
        if not request.confirm_replace:
            raise AppError("请明确确认覆盖现有后端数据")
        if not request.backup.success:
            raise AppError("文件不是成功导出的备份")
        data = request.backup.data
        self._validate_records(data)
        records: BackupWriteData = {
            "cinemas": [row.model_dump() for row in data.cinemas],
            "movies": [row.model_dump() for row in data.movies],
            "movie_shows": [row.model_dump() for row in data.movie_shows],
            "planning_items": [row.model_dump() for row in data.planning_items],
        }
        await asyncio.to_thread(backup_repository.replace_all, records)
        return BackupCounts(
            cinemas=len(data.cinemas),
            movies=len(data.movies),
            movie_shows=len(data.movie_shows),
            planning_items=len(data.planning_items),
        )

    def _validate_records(self, data: BackupData) -> None:
        for name, records in (
            ("影院", data.cinemas),
            ("电影", data.movies),
            ("场次", data.movie_shows),
            ("行程", data.planning_items),
        ):
            self._validate_unique((row.id for row in records), f"{name} ID")
        self._validate_unique((row.show_key for row in data.planning_items), "行程唯一键")
        self._validate_unique(
            ((row.movie_id, row.cinema_id, row.date, row.time) for row in data.movie_shows),
            "电影/影院/日期/时间组合",
        )
        for movie in data.movies:
            if sum((movie.is_wished, movie.is_skipped, movie.is_watched)) > 1:
                raise AppError("备份中的想看、不看、看过标签不能同时启用")

    def _validate_unique(self, values: Iterable[Hashable], label: str) -> None:
        seen: set[Hashable] = set()
        for value in values:
            if value in seen:
                raise AppError(f"备份包含重复的{label}")
            seen.add(value)


backup_service = BackupService()
