"""豆瓣电影补充信息的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DoubanMovieSearchItem:
    """豆瓣 API 返回的电影候选项。"""

    title: str
    rating: str
    cover_link: str
    year: str
    country: str
    actors: list[str]


@dataclass(slots=True)
class DoubanMovieSupplement:
    """补充后的豆瓣评分与详情链接。"""

    score: str
    douban_url: str | None

