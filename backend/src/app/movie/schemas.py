"""电影领域 API 数据契约。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas import SuccessEnvelope


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
    director: str | None = None
    country: str | None = None
    language: str | None = None
    duration: str | None = None
    description: str | None = None
    first_showing_at: str | None = None


class MovieSelectionData(BaseModel):
    """电影筛选结果数据。"""

    movies: list[MovieSelectionItem]


class MovieSelectionResponse(SuccessEnvelope):
    """电影筛选响应。"""

    data: MovieSelectionData
