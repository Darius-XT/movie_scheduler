"""电影筛选服务。"""

from __future__ import annotations

import asyncio
from typing import Literal

from app.core.exceptions import AppError
from app.core.logger import logger
from app.movie.entities import (
    MovieRecord,
    MovieSelectionItem,
    SupportsMovieSelectionGateway,
    SupportsMovieSelectionResultBuilder,
)
from app.movie.gateway import movie_gateway
from app.movie.result_builder import movie_result_builder

SelectionMode = Literal["showing", "upcoming", "all"]


class MovieSelector:
    """负责执行电影筛选规则（同步）。"""

    def __init__(
        self,
        gateway: SupportsMovieSelectionGateway | None = None,
        result_builder: SupportsMovieSelectionResultBuilder | None = None,
    ) -> None:
        self.gateway: SupportsMovieSelectionGateway = gateway or movie_gateway
        self.result_builder: SupportsMovieSelectionResultBuilder = (
            result_builder or movie_result_builder
        )

    def select_movie(self, selection_mode: SelectionMode = "all") -> list[MovieSelectionItem]:
        """根据上映状态筛选电影，按首次抓取时间降序排列。"""
        logger.debug("开始按上映状态筛选电影: %s", selection_mode)
        all_movies = self.gateway.get_all_movies()
        if not all_movies:
            logger.warning("数据库中没有电影数据")
            return []
        logger.debug("数据库中总共存在 %s 部电影", len(all_movies))
        selected = [
            self.result_builder.build_movie(movie)
            for movie in all_movies
            if self._matches(movie, selection_mode)
        ]
        selected.sort(
            key=lambda m: (m.first_showing_at is not None, m.first_showing_at or ""),
            reverse=True,
        )
        logger.debug("筛选完成，共找到 %s 部电影", len(selected))
        return selected

    def _matches(self, movie: MovieRecord, selection_mode: SelectionMode) -> bool:
        if selection_mode == "all":
            return True
        if selection_mode == "showing":
            return bool(movie.is_showing)
        return not bool(movie.is_showing)


class MovieService:
    """提供电影筛选业务能力（异步，含输入校验）。"""

    def __init__(self, selector: MovieSelector | None = None) -> None:
        self.selector = selector or MovieSelector()

    async def select_movie(self, selection_mode: SelectionMode = "all") -> list[MovieSelectionItem]:
        """按上映状态异步筛选电影。"""
        normalized = self._normalize_selection_mode(selection_mode)
        return await asyncio.to_thread(self.selector.select_movie, normalized)

    def _normalize_selection_mode(self, selection_mode: SelectionMode) -> SelectionMode:
        if selection_mode not in {"showing", "upcoming", "all"}:
            raise AppError("无效的上映状态筛选值", status_code=422)
        return selection_mode


movie_service = MovieService()
