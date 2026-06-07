"""影院领域 API 数据契约。"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(slots=True)
class CinemaUpsertData:
    """影院抓取与保存的中间数据(内部使用)。"""

    id: int | None
    name: str
    address: str
    price: str
    allow_refund: bool
    allow_endorse: bool


@dataclass(slots=True)
class CinemaUpdateResult:
    """影院更新结果(内部使用)。"""

    success_count: int
    failure_count: int


class UpdateCinemaStreamData(BaseModel):
    """SSE 完成事件中携带的影院更新结果数据。"""

    success_count: int
    failure_count: int
