"""电影筛选器。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol

from app.core.logger import logger
from app.use_cases.movie_selection.movie_selection_gateway import movie_selection_gateway
from app.use_cases.movie_selection.movie_selection_result_builder import (
    MovieRecord,
    MovieSelectionItem,
    movie_selection_result_builder,
)

SelectionMode = Literal["showing", "upcoming", "all"]


class SupportsMovieSelectionGateway(Protocol):
    """电影筛选用例依赖的网关协议。"""

    def get_all_movies(self) -> Sequence[MovieRecord]:
        """读取全部电影记录。"""
        ...


class SupportsMovieSelectionResultBuilder(Protocol):
    """电影筛选结果构建器协议。"""

    def build_movie(self, movie: MovieRecord) -> MovieSelectionItem:
        """构建电影筛选结果项。"""
        ...


class MovieSelector:
    """负责执行电影筛选规则。"""

    def __init__(
        self,
        gateway: SupportsMovieSelectionGateway | None = None,
        result_builder: SupportsMovieSelectionResultBuilder | None = None,
    ) -> None:
        self.gateway: SupportsMovieSelectionGateway = gateway or movie_selection_gateway
        self.result_builder: SupportsMovieSelectionResultBuilder = result_builder or movie_selection_result_builder

    def select_movie(self, selection_mode: SelectionMode = "all") -> list[MovieSelectionItem]:
        """根据上映状态筛选电影。"""
        logger.debug("开始按上映状态筛选电影: %s", selection_mode)

        all_movies = self.gateway.get_all_movies()
        if not all_movies:
            logger.warning("数据库中没有电影数据")
            return []

        logger.debug("数据库中总共存在 %s 部电影", len(all_movies))
        selected_movies: list[MovieSelectionItem] = []

        for movie in all_movies:
            if self._matches_selection_mode(movie, selection_mode):
                selected_movie = self.result_builder.build_movie(movie)
                selected_movies.append(selected_movie)
                logger.debug("选中电影: %s (ID: %s)", movie.title, movie.id)

        logger.debug("筛选完成，共找到 %s 部电影", len(selected_movies))
        return selected_movies

    def _matches_selection_mode(self, movie: MovieRecord, selection_mode: SelectionMode) -> bool:
        """判断电影是否符合上映状态筛选条件。"""
        if selection_mode == "all":
            return True
        if selection_mode == "showing":
            return bool(movie.is_showing)
        return not bool(movie.is_showing)


movie_selector = MovieSelector()
