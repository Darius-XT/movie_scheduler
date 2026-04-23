"""电影筛选结果构建器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


# * slots=True 表示不允许动态添加属性
@dataclass(slots=True)
class MovieSelectionItem:
    """电影筛选结果项。"""

    id: int | None
    title: str | None
    score: str | None
    douban_url: str | None
    genres: str | None
    actors: str | None
    release_date: str | None
    is_showing: bool
    director: str | None
    country: str | None
    language: str | None
    duration: str | None
    description: str | None
    first_seen_at: str | None


class MovieRecord(Protocol):
    """电影选择用例需要的电影记录视图。"""

    id: int | None
    title: str | None
    score: str | None
    douban_url: str | None
    genres: str | None
    actors: str | None
    release_date: str | None
    is_showing: bool
    director: str | None
    country: str | None
    language: str | None
    duration: str | None
    description: str | None
    first_seen_at: object


class MovieSelectionResultBuilder:
    """负责把电影实体转换为用例输出结构。"""

    def build_movie(self, movie: MovieRecord) -> MovieSelectionItem:
        """将电影记录转换为统一的电影筛选结果结构。"""
        return MovieSelectionItem(
            id=int(movie.id) if movie.id is not None else None,
            title=movie.title,
            score=movie.score,
            douban_url=movie.douban_url,
            genres=movie.genres,
            actors=movie.actors,
            release_date=movie.release_date,
            is_showing=movie.is_showing,
            director=movie.director,
            country=movie.country,
            language=movie.language,
            duration=movie.duration,
            description=movie.description,
            first_seen_at=str(movie.first_seen_at) if movie.first_seen_at else None,
        )


movie_selection_result_builder = MovieSelectionResultBuilder()
