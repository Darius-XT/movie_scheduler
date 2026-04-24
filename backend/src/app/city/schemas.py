"""城市领域 API 数据契约。"""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas import SuccessEnvelope


class CityItem(BaseModel):
    """城市项。"""

    name: str
    id: int


class CityListData(BaseModel):
    """城市列表数据。"""

    cities: list[CityItem]


class CityListResponse(SuccessEnvelope):
    """城市列表响应。"""

    data: CityListData
