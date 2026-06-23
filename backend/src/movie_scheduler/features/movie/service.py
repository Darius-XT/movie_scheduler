"""电影业务服务: 筛选、想看、信息更新编排(包括多数据源)。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from typing import Literal, cast

from movie_scheduler.config import config_manager
from movie_scheduler.core.exceptions import AppError, RepositoryError
from movie_scheduler.core.logging import logger
from movie_scheduler.features.movie.models import Movie
from movie_scheduler.features.movie.repository import movie_repository
from movie_scheduler.features.movie.update_base.service import (
    BaseInfoUpdateStats,
    UpdateBaseProgressEvent,
    update_base_service,
)
from movie_scheduler.features.movie.update_douban.service import (
    DoubanMovieSupplement,
    update_douban_service,
)
from movie_scheduler.features.movie.update_extra.service import update_extra_service
from movie_scheduler.features.show.service import show_service
from movie_scheduler.shared.sse import stream_with_progress

SelectionMode = Literal["showing", "upcoming", "all"]


class MovieService:
    """聚合电影筛选 / 想看 / 更新编排能力。"""

    # ---------- 对外: 筛选与想看 ----------

    async def select_movie(self, selection_mode: SelectionMode = "all") -> list[dict[str, object]]:
        """按上映状态异步筛选电影。"""
        normalized = self._normalize_selection_mode(selection_mode)
        return await asyncio.to_thread(self._select_sync, normalized)

    async def list_wished_movies(self) -> list[dict[str, object]]:
        return await asyncio.to_thread(self._list_wished_sync)

    async def set_movie_wished(self, movie_id: int, is_wished: bool) -> dict[str, object]:
        """更新单部电影的想看状态。"""
        ok = await asyncio.to_thread(movie_repository.set_movie_wished, movie_id, is_wished)
        if not ok:
            raise AppError(f"电影不存在: {movie_id}", status_code=404)
        if is_wished:
            asyncio.create_task(show_service.refresh_movie_shows(movie_id))
        else:
            # 移出想看: 同步清场次, 避免孤儿
            from movie_scheduler.features.show.repository import movie_show_repository
            await asyncio.to_thread(movie_show_repository.delete_for_movie, movie_id)
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        if movie is None:
            raise AppError(f"电影不存在: {movie_id}", status_code=404)
        return self._build_movie_item(movie)

    # ---------- 对外: 更新编排 ----------

    async def get_movies_last_updated_at(self) -> datetime | None:
        return await asyncio.to_thread(movie_repository.get_movies_last_updated_at)

    async def update_movies(
        self,
        city_id: int | None = None,
        progress_callback: Callable[[UpdateBaseProgressEvent], None] | None = None,
    ) -> BaseInfoUpdateStats:
        """更新所有电影信息(增量): 基础列表 → 额外详情。返回基础信息阶段的统计。"""
        normalized_city_id = self._normalize_city_id(city_id)
        logger.info("开始更新所有电影信息, city_id=%s", normalized_city_id)
        stats = await asyncio.to_thread(
            update_base_service.update_all, normalized_city_id, progress_callback,
        )
        await update_extra_service.update_all(progress_callback=progress_callback)
        if progress_callback is not None:
            progress_callback(UpdateBaseProgressEvent(
                message="正在汇总电影更新结果", stage="finalizing_movie_update",
            ))
        logger.info("所有电影信息更新完成")
        return stats

    async def refresh_all_movies(self) -> None:
        """定时任务入口: 更新电影信息(增量), 失败时只记日志不抛。

        无论本轮是否真的有字段变化, 都单独记录一次电影信息任务完成时间。
        """
        try:
            await self.update_movies(city_id=None)
            await asyncio.to_thread(movie_repository.touch_movies_last_updated_at)
            logger.info("电影定时更新完成")
        except Exception as error:  # noqa: BLE001
            logger.error("电影定时更新失败: %s", error)

    async def stream_movie_update(self, city_id: int) -> AsyncIterator[str]:
        """将电影更新过程编码为 SSE 文本帧。"""

        async def run(push_progress: Callable[[dict[str, object]], None]) -> dict[str, object]:
            def forward(event: UpdateBaseProgressEvent) -> None:
                push_progress({
                    "stage": event.stage,
                    "message": event.message,
                    "current": event.current,
                    "total": event.total,
                    "city_id": event.city_id,
                    "page": event.page,
                })

            stats = await self.update_movies(city_id=city_id, progress_callback=forward)
            # 与定时任务一致, 手动更新也单独记录电影信息任务完成时间。
            await asyncio.to_thread(movie_repository.touch_movies_last_updated_at)
            last_updated_at = await asyncio.to_thread(movie_repository.get_movies_last_updated_at)
            return {
                "added": stats.result_stats.added,
                "updated": stats.result_stats.updated,
                "removed": stats.result_stats.removed,
                "last_updated_at": last_updated_at.isoformat() if last_updated_at else None,
            }

        async for frame in stream_with_progress(run, map_error=self._map_stream_error):
            yield frame

    async def update_movie_douban(self, movie_id: int) -> DoubanMovieSupplement:
        """为单部电影抓取豆瓣评分与详情链接并持久化。"""
        movie = await asyncio.to_thread(movie_repository.get_movie_by_id, movie_id)
        if movie is None:
            raise AppError(f"电影不存在: {movie_id}", status_code=404)
        return await update_douban_service.update_one(movie)

    # ---------- 内部: 同步实现 ----------

    def _select_sync(self, selection_mode: SelectionMode) -> list[dict[str, object]]:
        logger.debug("开始按上映状态筛选电影: %s", selection_mode)
        all_movies = movie_repository.get_all_movies()
        if not all_movies:
            logger.warning("数据库中没有电影数据")
            return []
        selected = [
            self._build_movie_item(movie)
            for movie in all_movies
            if self._matches(movie, selection_mode)
        ]
        selected.sort(
            key=lambda m: (m["first_showing_at"] is not None, m["first_showing_at"] or ""),
            reverse=True,
        )
        logger.debug("筛选完成, 共找到 %s 部电影", len(selected))
        return selected

    def _list_wished_sync(self) -> list[dict[str, object]]:
        movies = movie_repository.list_wished_movies()
        return [self._build_movie_item(m) for m in movies]

    def _matches(self, movie: Movie, selection_mode: SelectionMode) -> bool:
        if selection_mode == "all":
            return True
        if selection_mode == "showing":
            return bool(movie.is_showing)
        return not bool(movie.is_showing)

    def _build_movie_item(self, movie: Movie) -> dict[str, object]:
        movie_id = cast(int | None, getattr(movie, "id", None))
        first_showing_at = cast(object, getattr(movie, "first_showing_at", None))
        return {
            "id": int(movie_id) if movie_id is not None else None,
            "title": movie.title,
            "score": movie.score,
            "douban_url": movie.douban_url,
            "genres": movie.genres,
            "actors": movie.actors,
            "release_date": movie.release_date,
            "is_showing": bool(movie.is_showing),
            "is_wished": bool(movie.is_wished),
            "director": movie.director,
            "country": movie.country,
            "language": movie.language,
            "duration": movie.duration,
            "description": movie.description,
            "first_showing_at": str(first_showing_at) if first_showing_at else None,
        }

    def _normalize_selection_mode(self, selection_mode: SelectionMode) -> SelectionMode:
        if selection_mode not in {"showing", "upcoming", "all"}:
            raise AppError("无效的上映状态筛选值", status_code=422)
        return selection_mode

    def _normalize_city_id(self, city_id: int | None) -> int:
        normalized = city_id if city_id is not None else config_manager.city_id
        if normalized <= 0:
            raise AppError("city_id 必须是正整数", status_code=422)
        if normalized not in config_manager.city_mapping.values():
            raise AppError("city_id 不在当前支持的城市范围内", status_code=422)
        return normalized

    def _map_stream_error(self, error: Exception) -> str:
        if isinstance(error, AppError):
            return error.message
        if isinstance(error, RepositoryError):
            return "数据库访问失败,请稍后重试"
        return "更新失败,请稍后重试"


movie_service = MovieService()
