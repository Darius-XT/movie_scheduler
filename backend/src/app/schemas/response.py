"""API 响应体定义。"""

from __future__ import annotations

from pydantic import BaseModel


class CityItem(BaseModel):
    """城市项。"""

    name: str
    id: int


class CityListResponse(BaseModel):
    """城市列表响应。"""

    cities: list[CityItem]


class SuccessEnvelope(BaseModel):
    """通用成功响应包装。"""

    success: bool = True


class MovieSelectionItem(BaseModel):
    """电影筛选条目。"""

    id: int | None = None
    title: str | None = None
    score: str | None = None
    douban_url: str | None = None
    genres: str | None = None
    actors: str | None = None
    release_date: str | None = None
    is_showing: bool = False
    director: str | None = None
    country: str | None = None
    language: str | None = None
    duration: str | None = None
    description: str | None = None
    first_seen_at: str | None = None


class MovieSelectionData(BaseModel):
    """电影筛选结果数据。"""

    movies: list[MovieSelectionItem]


class MovieSelectionResponse(SuccessEnvelope):
    """电影筛选响应。"""

    data: MovieSelectionData


class UpdateCinemaData(BaseModel):
    """影院更新结果数据。"""

    success_count: int
    failure_count: int


class UpdateCinemaResponse(SuccessEnvelope):
    """影院更新响应。"""

    data: UpdateCinemaData


class UpdateMovieInputStats(BaseModel):
    """电影基础信息抓取输入统计。"""

    scraped_total: int
    showing: int
    upcoming: int
    duplicate: int
    deduplicated_total: int


class UpdateMovieResultStats(BaseModel):
    """电影基础信息更新结果统计。"""

    existing: int
    added: int
    added_movie_ids: list[int]
    updated: int
    updated_movie_ids: list[int]
    removed: int
    total: int


class UpdateMovieBaseInfo(BaseModel):
    """电影基础信息更新统计。"""

    input_stats: UpdateMovieInputStats
    result_stats: UpdateMovieResultStats


class UpdateMovieExtraInfo(BaseModel):
    """电影额外信息更新统计。"""

    updated_count: int


class UpdateMovieData(BaseModel):
    """电影更新结果数据。"""

    base_info: UpdateMovieBaseInfo
    extra_info: UpdateMovieExtraInfo


class UpdateMovieResponse(SuccessEnvelope):
    """电影更新响应。"""

    data: UpdateMovieData
