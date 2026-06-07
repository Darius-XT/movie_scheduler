"""场次领域 API 数据契约。"""

from __future__ import annotations

from pydantic import BaseModel

from movie_scheduler.shared.types import SuccessEnvelope


class ShowItemSchema(BaseModel):
    """单条场次。"""

    cinema_id: int
    cinema_name: str
    date: str
    time: str
    price: str | None = None


class MovieShowGroup(BaseModel):
    """单部电影的场次列表。"""

    movie_id: int
    shows: list[ShowItemSchema]


class ShowsData(BaseModel):
    """想看电影的全部场次数据。"""

    movies: list[MovieShowGroup]
    last_fetched_at: str | None = None


class ShowsResponse(SuccessEnvelope):
    """场次读取响应。"""

    data: ShowsData
