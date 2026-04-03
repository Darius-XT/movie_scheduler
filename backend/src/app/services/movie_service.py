"""电影业务服务。"""

from __future__ import annotations

import asyncio
from typing import Literal

from app.core.exceptions import AppError
from app.use_cases.movie_selection.movie_selection_result_builder import MovieSelectionItem
from app.use_cases.movie_selection.movie_selector import movie_selector

SelectionMode = Literal["showing", "upcoming", "all"]


class MovieService:
    """提供电影相关业务能力。"""

    async def select_movie(self, selection_mode: SelectionMode = "all") -> list[MovieSelectionItem]:
        """按上映状态异步筛选电影。"""
        normalized_selection_mode = self._normalize_selection_mode(selection_mode)
        return await asyncio.to_thread(movie_selector.select_movie, normalized_selection_mode)

    def _normalize_selection_mode(self, selection_mode: SelectionMode) -> SelectionMode:
        """规范化上映状态筛选值。"""
        if selection_mode not in {"showing", "upcoming", "all"}:
            raise AppError("无效的上映状态筛选值", status_code=422)
        return selection_mode


movie_service = MovieService()
