"""场次抓取用例的内部数据结构。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


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


@dataclass(slots=True)
class DatesFoundProgress:
    """已发现排片日期的进度事件。"""

    type: str
    movie_id: int
    dates: list[str]


@dataclass(slots=True)
class ProcessingDateProgress:
    """正在处理日期的进度事件。"""

    type: str
    movie_id: int
    date: str
    date_idx: int
    total_dates: int


@dataclass(slots=True)
class ProcessingCinemaProgress:
    """正在处理影院的进度事件。"""

    type: str
    movie_id: int
    date: str
    cinema_idx: int
    total_cinemas: int
    cinema_id: int


@dataclass(slots=True)
class MovieCompleteProgress:
    """单部电影抓取完成的进度事件。"""

    type: str
    movie_id: int
    has_shows: bool


ShowFetchProgressEvent: TypeAlias = (
    DatesFoundProgress | ProcessingDateProgress | ProcessingCinemaProgress | MovieCompleteProgress
)
