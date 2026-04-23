"""电影额外信息更新器。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import asdict
from typing import cast

from app.core.logger import logger
from app.models.movie import MovieWriteData
from app.repositories.movie import movie_repository
from app.services.update.entities import UpdateProgressEvent
from app.services.update.movie.extra.client import MovieExtraInfoClient


class MovieExtraInfoUpdater:
    """负责补充电影的额外详情。"""

    def __init__(self) -> None:
        self.client = MovieExtraInfoClient()

    async def update_all_movie_extra_info(
        self,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> int:
        """更新电影额外详情，并返回成功数量。"""
        if force_update_all:
            logger.info("开始强制更新所有电影的详情信息")
            movies_to_update = await asyncio.to_thread(movie_repository.get_all_movies)
        else:
            logger.info("开始获取电影详情信息")
            movies_to_update = await asyncio.to_thread(movie_repository.get_movies_without_details)

        if not movies_to_update:
            logger.info("没有需要更新详情的电影")
            return 0

        total_movies = len(movies_to_update)
        tasks = [
            self._process_single_movie(
                movie=movie, index=idx, total_movies=total_movies,
                progress_callback=progress_callback,
            )
            for idx, movie in enumerate(movies_to_update, start=1)
        ]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for s in results if s)
        logger.info("额外电影信息更新统计: 成功=%d, 失败=%d, 总计=%d",
                    success_count, len(results) - success_count, len(results))
        return success_count

    async def _process_single_movie(
        self,
        *,
        movie: object,
        index: int,
        total_movies: int,
        progress_callback: Callable[[UpdateProgressEvent], None] | None,
    ) -> bool:
        """处理单部电影的详情抓取与保存。"""
        movie_id = cast(int, getattr(movie, "id"))
        movie_title = cast(str | None, getattr(movie, "title", None))
        logger.debug("正在获取电影详情: %s (ID: %s)", movie_title, movie_id)

        if progress_callback is not None:
            progress_callback(UpdateProgressEvent(
                message=f"正在补充详细信息 ({index}/{total_movies})",
                stage="fetching_movie_details",
                current=index,
                total=total_movies,
            ))

        try:
            movie_details = await self._fetch_and_validate(movie_id, movie_title)
            if movie_details is None:
                return False
            return await self._persist_details(movie_details, movie_id, movie_title)
        except Exception as error:
            logger.error("处理电影 %s (ID: %s) 时发生异常: %s", movie_title, movie_id, error)
            return False

    async def _fetch_and_validate(self, movie_id: int, movie_title: str | None) -> object | None:
        """抓取并解析电影详情，返回解析结果或 None。"""
        movie_details = await asyncio.to_thread(self.client.fetch_details, movie_id)
        if movie_details is None:
            logger.warning("获取或解析电影详情失败: %s (ID: %s)", movie_title, movie_id)
            return None
        return movie_details

    async def _persist_details(self, movie_details: object, movie_id: int, movie_title: str | None) -> bool:
        """将电影详情保存到数据库。"""
        save_success = await asyncio.to_thread(
            movie_repository.save_movie,
            cast(MovieWriteData, asdict(movie_details)),  # type: ignore[call-overload]
        )
        if save_success:
            logger.debug("成功更新电影详情: %s (ID: %s)", movie_title, movie_id)
            return True
        logger.error("保存电影详情失败: %s (ID: %s)", movie_title, movie_id)
        return False


movie_extra_info_updater = MovieExtraInfoUpdater()
