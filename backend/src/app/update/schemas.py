"""更新领域 API 数据契约。"""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas import SuccessEnvelope


class UpdateCinemaRequest(BaseModel):
    """更新影院信息请求。"""

    city_id: int


class UpdateMovieRequest(BaseModel):
    """更新电影信息请求。"""

    city_id: int
    force_update_all: bool = False


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


class FetchMovieDoubanData(BaseModel):
    """单部电影豆瓣信息抓取结果数据。"""

    score: str | None
    douban_url: str | None


class FetchMovieDoubanResponse(SuccessEnvelope):
    """单部电影豆瓣信息抓取响应。"""

    data: FetchMovieDoubanData
