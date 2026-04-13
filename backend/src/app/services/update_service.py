"""信息更新服务。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.core.config import config_manager
from app.core.exceptions import AppError
from app.use_cases.update.info_update_use_case import info_update_use_case
from app.use_cases.update.models import UpdateProgressEvent
from app.use_cases.update.update_result_builder import UpdateCinemaResult, UpdateMovieResult


class UpdateService:
    """聚合电影与影院更新能力。"""

    async def update_movie(
        self,
        city_id: int | None,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> UpdateMovieResult:
        """异步更新电影信息。"""
        normalized_city_id = self._normalize_city_id(city_id)
        return await info_update_use_case.update_movie_info(
            normalized_city_id,
            force_update_all,
            progress_callback,
        )

    async def update_cinema(
        self,
        city_id: int | None,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> UpdateCinemaResult:
        """异步更新影院信息。"""
        normalized_city_id = self._normalize_city_id(city_id)
        return await asyncio.to_thread(
            info_update_use_case.update_cinema_info,
            normalized_city_id,
            force_update_all,
            progress_callback,
        )

    def _normalize_city_id(self, city_id: int | None) -> int:
        """校验并补全城市 ID。"""
        normalized_city_id = city_id if city_id is not None else config_manager.city_id
        if normalized_city_id <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized_city_id not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized_city_id


update_service = UpdateService()
