"""更新所有电影信息。"""

from __future__ import annotations

from collections.abc import Callable

from app.core.logger import logger
from app.use_cases.update.models import UpdateProgressEvent
from app.use_cases.update.movie_info.base_info.base_info_updater import movie_base_info_updater
from app.use_cases.update.movie_info.extra_info.extra_info_updater import movie_extra_info_updater
from app.use_cases.update.movie_update_reset_helper import MovieUpdateResetHelper
from app.use_cases.update.update_result_builder import UpdateMovieResult, UpdateResultBuilder


class MovieInfoUpdater:
    """负责编排电影基础信息和额外信息更新。"""

    def __init__(
        self,
        reset_helper: MovieUpdateResetHelper | None = None,
        result_builder: UpdateResultBuilder | None = None,
    ) -> None:
        self.base_info_updater = movie_base_info_updater
        self.extra_info_updater = movie_extra_info_updater
        self.reset_helper = reset_helper or MovieUpdateResetHelper()
        self.result_builder = result_builder or UpdateResultBuilder()

    async def update_all_movie_info(
        self,
        city_id: int,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> UpdateMovieResult:
        """更新所有电影信息。"""
        logger.info(
            "开始更新所有电影信息，city_id=%s, force_update_all=%s",
            city_id,
            force_update_all,
        )

        self.reset_helper.reset_movies_if_needed(force_update_all)
        base_info_stats = self.base_info_updater.update_all_movie_base_info(
            city_id,
            progress_callback=progress_callback,
        )
        extra_info_updated_count = await self.extra_info_updater.update_all_movie_extra_info(
            force_update_all=force_update_all,
            progress_callback=progress_callback,
        )

        result = self.result_builder.build_movie_update_result(
            base_info_stats=base_info_stats,
            extra_info_updated_count=extra_info_updated_count,
        )
        logger.info("所有电影信息更新完成")
        return result


movie_info_updater = MovieInfoUpdater()
