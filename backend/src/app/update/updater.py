"""信息更新用例入口（聚合电影与影院更新能力的纯用例对象）。"""

from __future__ import annotations

from collections.abc import Callable

from app.update.cinema.updater import CinemaInfoUpdater
from app.update.entities import UpdateProgressEvent
from app.update.movie.updater import MovieInfoUpdater
from app.update.result_builder import (
    UpdateCinemaResult,
    UpdateMovieResult,
    UpdateResultBuilder,
)


class InfoUpdateUseCase:
    """聚合电影与影院更新用例。"""

    def __init__(self, result_builder: UpdateResultBuilder | None = None) -> None:
        self.movie_info_updater = MovieInfoUpdater()
        self.cinema_info_updater = CinemaInfoUpdater()
        self.result_builder = result_builder or UpdateResultBuilder()

    async def update_movie_info(
        self,
        city_id: int,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> UpdateMovieResult:
        """仅更新电影信息。"""
        return await self.movie_info_updater.update_all_movie_info(
            city_id=city_id,
            force_update_all=force_update_all,
            progress_callback=progress_callback,
        )

    def update_cinema_info(
        self,
        city_id: int,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> UpdateCinemaResult:
        """仅更新影院信息。"""
        success_count, failure_count = self.cinema_info_updater.update_all_cinema_info(
            city_id=city_id,
            force_update_all=force_update_all,
            progress_callback=progress_callback,
        )
        return self.result_builder.build_cinema_update_result(
            success_count=success_count,
            failure_count=failure_count,
        )


info_update_use_case = InfoUpdateUseCase()
