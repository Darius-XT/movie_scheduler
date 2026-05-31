"""排片计划 API 数据契约。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas import SuccessEnvelope


class ScheduleItem(BaseModel):
    """前端行程条目(场次维度)。"""

    key: str
    movie_id: int = Field(alias="movieId")
    movie_title: str = Field(alias="movieTitle")
    date: str
    time: str
    cinema_id: int = Field(alias="cinemaId")
    cinema_name: str = Field(alias="cinemaName")
    price: str | None = None
    duration_minutes: int | None = Field(default=None, alias="durationMinutes")
    purchased: bool = False

    model_config = {"populate_by_name": True}


class PlanningData(BaseModel):
    """排片计划列表数据。"""

    schedule_items: list[ScheduleItem]


class PlanningResponse(SuccessEnvelope):
    """读取排片计划响应。"""

    data: PlanningData


class ReplaceScheduleItemsRequest(BaseModel):
    """全量替换行程请求。"""

    schedule_items: list[ScheduleItem] = []
