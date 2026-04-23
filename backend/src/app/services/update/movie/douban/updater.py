"""豆瓣信息更新器。"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import cast

from app.core.logger import logger
from app.models.movie import MovieWriteData
from app.repositories.movie import movie_repository
from app.services.update.entities import UpdateProgressEvent
from app.services.update.movie.douban.enricher import (
    DoubanInfoEnricher,
    SupportsDoubanMatchingMovie,
    douban_info_enricher,
)


class MovieDoubanInfoUpdater:
    """负责补充电影的豆瓣评分与详情链接。"""

    def __init__(self, enricher: DoubanInfoEnricher | None = None) -> None:
        self.enricher = enricher or douban_info_enricher

    async def update_all_movie_douban_info(
        self,
        force_update_all: bool = False,
        progress_callback: Callable[[UpdateProgressEvent], None] | None = None,
    ) -> int:
        """更新电影豆瓣信息，并返回成功数量。"""
        if force_update_all:
            logger.info("开始强制更新所有电影的豆瓣信息")
            movies_to_update = await asyncio.to_thread(movie_repository.get_all_movies)
        else:
            logger.info("开始获取待补充豆瓣信息的电影")
            movies_to_update = await asyncio.to_thread(movie_repository.get_movies_without_douban_info)

        if not movies_to_update:
            logger.info("没有需要更新豆瓣信息的电影")
            return 0

        total_movies = len(movies_to_update)
        tasks = [
            self._process_single_movie(
                movie=movie,
                index=idx,
                total_movies=total_movies,
                progress_callback=progress_callback,
            )
            for idx, movie in enumerate(movies_to_update, start=1)
        ]
        results = await asyncio.gather(*tasks)

        success_count = sum(1 for success in results if success)
        failure_count = len(results) - success_count
        logger.info(
            "豆瓣电影信息更新统计: 成功=%d, 失败=%d, 总计=%d",
            success_count,
            failure_count,
            success_count + failure_count,
        )
        return success_count

    async def _process_single_movie(
        self,
        *,
        movie: object,
        index: int,
        total_movies: int,
        progress_callback: Callable[[UpdateProgressEvent], None] | None,
    ) -> bool:
        movie_id = cast(int, getattr(movie, "id"))
        movie_title = cast(str | None, getattr(movie, "title", None))
        logger.debug("正在获取电影豆瓣信息: %s (ID: %s)", movie_title, movie_id)

        if progress_callback is not None:
            progress_callback(
                UpdateProgressEvent(
                    message=f"正在补充豆瓣信息 ({index}/{total_movies})",
                    stage="fetching_movie_douban_info",
                    current=index,
                    total=total_movies,
                )
            )

        try:
            supplement = await asyncio.to_thread(
                self.enricher.fetch_movie_supplement,
                cast(SupportsDoubanMatchingMovie, movie),
            )
            save_success = await asyncio.to_thread(
                movie_repository.save_movie,
                cast(
                    MovieWriteData,
                    {
                        "id": movie_id,
                        "score": supplement.score,
                        "douban_url": supplement.douban_url,
                    },
                ),
            )
            if save_success:
                logger.debug("成功更新电影豆瓣信息: %s (ID: %s)", movie_title, movie_id)
                return True

            logger.error("保存电影豆瓣信息失败: %s (ID: %s)", movie_title, movie_id)
            return False
        except Exception as error:
            logger.error("处理电影 %s (ID: %s) 的豆瓣信息时发生异常: %s", movie_title, movie_id, error)
            return False


movie_douban_info_updater = MovieDoubanInfoUpdater()
