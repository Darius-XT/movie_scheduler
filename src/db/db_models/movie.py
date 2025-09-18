"""电影数据模型"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from src.db.db_models import Base
from sqlalchemy.sql import func


# 对应数据库中的 movies 表
class Movie(Base):
    """电影数据模型"""

    __tablename__ = "movies"

    # 基本信息
    id = Column(Integer, primary_key=True, comment="电影ID")
    title = Column(String(200), nullable=False, comment="电影标题")
    url = Column(Text, nullable=True, comment="电影链接")
    cinemas_url = Column(Text, nullable=True, comment="影院上映信息链接")

    # 评分信息
    score = Column(String(10), nullable=True, comment="完整评分")

    # 电影详情
    genres = Column(Text, nullable=True, comment="电影类型")
    actors = Column(Text, nullable=True, comment="主演")
    release_date = Column(String(50), nullable=True, comment="上映时间")

    # 时间戳
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
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
            url=data.get("url"),
            cinemas_url=data.get("cinemas_url"),
            score=data.get("score"),
            genres=data.get("genres"),
            actors=data.get("actors"),
            release_date=data.get("release_date"),
        )
