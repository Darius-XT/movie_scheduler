"""影院更新用例的内部数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CinemaUpsertData:
    """影院保存数据。"""

    id: int | None
    name: str
    address: str
    price: str
    allow_refund: bool
    allow_endorse: bool
