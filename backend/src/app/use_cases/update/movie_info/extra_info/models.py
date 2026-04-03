"""电影额外信息更新用例的内部数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MovieExtraInfo:
    """电影额外信息保存数据。"""

    id: int | None
    director: str
    country: str
    language: str
    duration: str
    description: str
