"""电影基础信息更新用例的内部数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ScrapedMovieBaseInfo:
    """抓取到的单部电影基础信息。"""

    id: int
    title: str | None
    score: str
    genres: str
    actors: str
    release_date: str | None = None
    is_showing: bool = False


@dataclass(slots=True)
class MovieBaseInfoInputStats:
    """电影基础信息抓取输入统计。"""

    scraped_total: int
    showing: int
    upcoming: int
    duplicate: int
    deduplicated_total: int


@dataclass(slots=True)
class MovieBaseInfoResultStats:
    """电影基础信息更新结果统计。"""

    existing: int
    added: int
    added_movie_ids: list[int]
    updated: int
    updated_movie_ids: list[int]
    removed: int
    total: int


@dataclass(slots=True)
class MovieBaseInfoUpdateStats:
    """电影基础信息更新统计。"""

    input_stats: MovieBaseInfoInputStats
    result_stats: MovieBaseInfoResultStats
