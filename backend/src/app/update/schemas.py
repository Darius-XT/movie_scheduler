"""更新领域 API 数据契约。"""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas import SuccessEnvelope


class UpdateCinemaRequest(BaseModel):
    """更新影院信息请求。"""

    city_id: int


class UpdateCinemaData(BaseModel):
    """影院更新结果数据。"""

    success_count: int
    failure_count: int


class UpdateCinemaResponse(SuccessEnvelope):
    """影院更新响应。"""

    data: UpdateCinemaData


class MovieUpdateStatusData(BaseModel):
    """电影定时更新状态。"""

    last_updated_at: str | None


class MovieUpdateStatusResponse(SuccessEnvelope):
    """电影定时更新状态响应。"""

    data: MovieUpdateStatusData


class FetchMovieDoubanData(BaseModel):
    """单部电影豆瓣信息抓取结果数据。"""

    score: str | None
    douban_url: str | None


class FetchMovieDoubanResponse(SuccessEnvelope):
    """单部电影豆瓣信息抓取响应。"""

    data: FetchMovieDoubanData
