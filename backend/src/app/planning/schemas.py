"""排片计划 API 数据契约。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import SuccessEnvelope


class PlanningItem(BaseModel):
    """前端排片计划条目。"""

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

    wish_pool: list[PlanningItem]
    schedule_items: list[PlanningItem]


class PlanningResponse(SuccessEnvelope):
    """读取排片计划响应。"""

    data: PlanningData


class ReplacePlanningRequest(BaseModel):
    """全量替换排片计划请求。"""

    wish_pool: list[PlanningItem] = []
    schedule_items: list[PlanningItem] = []


PlanningListType = Literal["wish", "schedule"]
