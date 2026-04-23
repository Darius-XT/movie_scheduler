"""信息更新服务。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast

from app.core.config import config_manager
from app.core.exceptions import AppError
from app.models.movie import MovieWriteData
from app.repositories.movie import movie_repository
from app.services.update.cinema.updater import CinemaInfoUpdater
from app.services.update.entities import UpdateProgressEvent
from app.services.update.movie.douban.enricher import DoubanInfoEnricher, SupportsDoubanMatchingMovie, douban_info_enricher
from app.services.update.movie.douban.entities import DoubanMovieSupplement
from app.services.update.movie.updater import MovieInfoUpdater
from app.services.update.result_builder import UpdateCinemaResult, UpdateMovieResult, UpdateResultBuilder


class UpdateService:
    """聚合电影与影院更新能力。"""

    def __init__(
        self,
        result_builder: UpdateResultBuilder | None = None,
        enricher: DoubanInfoEnricher | None = None,
    ) -> None:
        self.movie_info_updater = MovieInfoUpdater()
        self.cinema_info_updater = CinemaInfoUpdater()
        self.result_builder = result_builder or UpdateResultBuilder()
        self.enricher = enricher or douban_info_enricher

    async def update_movie(
        self,
        city_id: int | None,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> UpdateMovieResult:
        """异步更新电影信息。"""
        return await self.movie_info_updater.update_all_movie_info(
            city_id=self._normalize_city_id(city_id),
            force_update_all=force_update_all,
            progress_callback=progress_callback,
        )

    async def update_cinema(
        self,
        city_id: int | None,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> UpdateCinemaResult:
        """异步更新影院信息。"""
        normalized_city_id = self._normalize_city_id(city_id)
        success_count, failure_count = await asyncio.to_thread(
            self.cinema_info_updater.update_all_cinema_info,
            normalized_city_id,
            force_update_all,
            progress_callback,
        )
        return self.result_builder.build_cinema_update_result(
            success_count=success_count,
            failure_count=failure_count,
        )

    async def fetch_douban_for_movie(self, movie_id: int) -> DoubanMovieSupplement:
        """为单部电影抓取豆瓣评分与详情链接并持久化。

        Raises:
            AppError: 电影不存在（status_code=404）。
        """
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        if movie is None:
            raise AppError(f"电影不存在: {movie_id}", status_code=404)

        supplement = await asyncio.to_thread(
            self.enricher.fetch_movie_supplement,
            cast(SupportsDoubanMatchingMovie, movie),
        )
        write_data: MovieWriteData = {
            "id": movie_id,
            "title": cast(str | None, getattr(movie, "title", None)),
            "score": supplement.score,
            "douban_url": supplement.douban_url,
        }
        await asyncio.to_thread(movie_repository.save_movie, write_data)
        return supplement

    def _normalize_city_id(self, city_id: int | None) -> int:
        """校验并补全城市 ID。"""
        normalized = city_id if city_id is not None else config_manager.city_id
        if normalized <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized


update_service = UpdateService()
