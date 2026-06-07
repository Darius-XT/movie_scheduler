"""电影领域 API 数据契约。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from movie_scheduler.shared.types import SuccessEnvelope


class SelectMovieRequest(BaseModel):
    """筛选电影请求。"""

    selection_mode: Literal["showing", "upcoming", "all"] = "all"


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
    is_wished: bool = False
    director: str | None = None
    country: str | None = None
    language: str | None = None
    duration: str | None = None
    description: str | None = None
    first_showing_at: str | None = None


class MovieSelectionData(BaseModel):
    movies: list[MovieSelectionItem]


class MovieSelectionResponse(SuccessEnvelope):
    data: MovieSelectionData


class WishedMoviesData(BaseModel):
    movies: list[MovieSelectionItem]


class WishedMoviesResponse(SuccessEnvelope):
    data: WishedMoviesData


class SetMovieWishedRequest(BaseModel):
    is_wished: bool


class MovieDetailData(BaseModel):
    movie: MovieSelectionItem


class MovieDetailResponse(SuccessEnvelope):
    data: MovieDetailData


class MovieUpdateStatusData(BaseModel):
    """电影定时更新状态。"""

    last_updated_at: str | None


class MovieUpdateStatusResponse(SuccessEnvelope):
    data: MovieUpdateStatusData


class UpdateMovieDoubanData(BaseModel):
    """单部电影豆瓣信息抓取结果。"""

    score: str | None
    douban_url: str | None


class UpdateMovieDoubanResponse(SuccessEnvelope):
    data: UpdateMovieDoubanData
