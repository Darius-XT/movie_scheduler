"""场次抓取领域的内部数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FetchedShowItem:
    """上游抓取到的单条原始场次。"""

    movie_id: int | None
    movie_name: str
    show_date: str
    show_time: str
    price: str
    cinema_id: int | None
    cinema_name: str
