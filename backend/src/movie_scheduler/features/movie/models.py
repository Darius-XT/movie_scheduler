"""电影数据模型。"""

from __future__ import annotations

from datetime import date, datetime
from typing import NotRequired, Required, TypedDict

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from movie_scheduler.core.db import Base


class MovieWriteData(TypedDict, total=False):
    """电影持久化写入数据。"""

    id: Required[int]
    title: NotRequired[str | None]
    score: NotRequired[str | None]
    douban_url: NotRequired[str | None]
    genres: NotRequired[str | None]
    actors: NotRequired[str | None]
    release_date: NotRequired[str | None]
    is_showing: NotRequired[bool]
    director: NotRequired[str | None]
    country: NotRequired[str | None]
    language: NotRequired[str | None]
    duration: NotRequired[str | None]
    description: NotRequired[str | None]
    first_showing_at: NotRequired[date | datetime | None]
    is_wished: NotRequired[bool]
    shows_updated_at: NotRequired[datetime | None]


class Movie(Base):
    """电影数据模型。"""

    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, comment="电影ID")
    title = Column(String(200), nullable=False, comment="电影标题")

    score = Column(String(10), nullable=True, comment="完整评分")
    douban_url = Column(String(255), nullable=True, comment="豆瓣详情链接")

    genres = Column(Text, nullable=True, comment="电影类型")
    actors = Column(Text, nullable=True, comment="主演")
    release_date = Column(String(20), nullable=True, comment="上映日期")
    is_showing = Column(Boolean, nullable=False, server_default="0", comment="是否正在热映")
    is_wished = Column(Boolean, nullable=False, server_default="0", comment="是否加入想看")

    director = Column(Text, nullable=True, comment="导演")
    country = Column(String(100), nullable=True, comment="制片国家")
    language = Column(String(100), nullable=True, comment="语言")
    duration = Column(String(20), nullable=True, comment="时长")
    description = Column(Text, nullable=True, comment="剧情简介")

    first_showing_at = Column(
        DateTime,
        nullable=True,
        comment="最近一次进入正在热映状态的时间(北京时间)",
    )
    updated_at = Column(
        DateTime,
        server_default=func.datetime("now", "+8 hours"),
        onupdate=func.datetime("now", "+8 hours"),
        comment="更新时间(北京时间)",
    )
    shows_updated_at = Column(
        DateTime,
        nullable=True,
        comment="场次最近一次刷新完成时间(北京时间)",
    )

    def __repr__(self):
        return f"<Movie(id={self.id}, title='{self.title}', score='{self.score}')>"

    @classmethod
    def from_dict(cls, data: MovieWriteData) -> Movie:
        return cls(
            id=data.get("id"),
            title=data.get("title"),
            score=data.get("score"),
            douban_url=data.get("douban_url"),
            genres=data.get("genres"),
            actors=data.get("actors"),
            release_date=data.get("release_date"),
            is_showing=bool(data.get("is_showing", False)),
            director=data.get("director"),
            country=data.get("country"),
            language=data.get("language"),
            duration=data.get("duration"),
            description=data.get("description"),
            first_showing_at=data.get("first_showing_at"),
            is_wished=bool(data.get("is_wished", False)),
            shows_updated_at=data.get("shows_updated_at"),
        )
