"""电影数据模型"""

from __future__ import annotations

from typing import NotRequired, Required, TypedDict

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models import Base


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


# 对应数据库中的 movies 表
class Movie(Base):
    """电影数据模型"""

    __tablename__ = "movies"

    # 基本信息
    id = Column(Integer, primary_key=True, comment="电影ID")
    title = Column(String(200), nullable=False, comment="电影标题")

    # 评分信息
    score = Column(String(10), nullable=True, comment="完整评分")
    douban_url = Column(String(255), nullable=True, comment="豆瓣详情链接")

    # 电影详情
    genres = Column(Text, nullable=True, comment="电影类型")
    actors = Column(Text, nullable=True, comment="主演")
    release_date = Column(String(20), nullable=True, comment="上映日期")
    is_showing = Column(Boolean, nullable=False, server_default="0", comment="是否正在热映")

    # 详细信息（从电影详情API获取）
    director = Column(Text, nullable=True, comment="导演")
    country = Column(String(100), nullable=True, comment="制片国家")
    language = Column(String(100), nullable=True, comment="语言")
    duration = Column(String(20), nullable=True, comment="时长(例如: 120min 或 暂无时长)")
    description = Column(Text, nullable=True, comment="剧情简介")

    # 时间戳（东八区北京时间）
    updated_at = Column(
        DateTime,
        server_default=func.datetime("now", "+8 hours"),
        onupdate=func.datetime("now", "+8 hours"),
        comment="更新时间（北京时间）",
    )

    # 设置直接 print 对象时会打印的输出
    def __repr__(self):
        return f"<Movie(id={self.id}, title='{self.title}', score='{self.score}')>"

    @classmethod
    # 从字典便捷地创建Movie实例
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
        )
