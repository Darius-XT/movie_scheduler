"""电影筛选领域的内部数据结构与外部行为协议。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


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
    first_showing_at: str | None


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
    first_showing_at: object


class SupportsMovieSelectionGateway(Protocol):
    """电影筛选用例依赖的网关协议。"""

    def get_all_movies(self) -> Sequence[MovieRecord]: ...


class SupportsMovieSelectionResultBuilder(Protocol):
    """电影筛选结果构建器协议。"""

    def build_movie(self, movie: MovieRecord) -> MovieSelectionItem: ...
