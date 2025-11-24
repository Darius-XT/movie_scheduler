"""电影数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from src.db.db_models import Base
from sqlalchemy.sql import func


# 对应数据库中的 movies 表
class Movie(Base):
    """电影数据模型"""

    __tablename__ = "movies"

    # 基本信息
    id = Column(Integer, primary_key=True, comment="电影ID")
    title = Column(String(200), nullable=False, comment="电影标题")

    # 评分信息
    score = Column(String(10), nullable=True, comment="完整评分")

    # 电影详情
    genres = Column(Text, nullable=True, comment="电影类型")
    actors = Column(Text, nullable=True, comment="主演")
    release_year = Column(String(10), nullable=True, comment="上映年份")
    is_showing = Column(
        Boolean, nullable=False, server_default="0", comment="是否正在热映"
    )

    # 详细信息（从电影详情API获取）
    director = Column(Text, nullable=True, comment="导演")
    country = Column(String(100), nullable=True, comment="制片国家")
    language = Column(String(100), nullable=True, comment="语言")
    duration = Column(
        String(20), nullable=True, comment="时长(例如: 120min 或 暂无时长)"
    )
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
    def from_dict(cls, data: dict) -> "Movie":
        return cls(
            id=data.get("id"),
            title=data.get("title"),
            score=data.get("score"),
            genres=data.get("genres"),
            actors=data.get("actors"),
            release_year=data.get("release_year"),
            is_showing=bool(data.get("is_showing", False)),
            director=data.get("director"),
            country=data.get("country"),
            language=data.get("language"),
            duration=data.get("duration"),
            description=data.get("description"),
        )
