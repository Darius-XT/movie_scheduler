"""更新用例的内部数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UpdateProgressEvent:
    """更新流程中的进度事件。"""

    message: str
    stage: str
    current: int | None = None
    total: int | None = None
    city_id: int | None = None
    page: int | None = None
