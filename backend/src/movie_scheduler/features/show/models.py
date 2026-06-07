"""电影场次数据模型。"""

from __future__ import annotations

from typing import NotRequired, Required, TypedDict

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from movie_scheduler.core.db import Base


class MovieShowWriteData(TypedDict, total=False):
    """场次持久化写入数据。"""

    movie_id: Required[int]
    cinema_id: Required[int]
    cinema_name: Required[str]
    date: Required[str]
    time: Required[str]
    price: NotRequired[str | None]


class MovieShow(Base):
    """单部电影在某影院某日某时刻的场次。"""

    __tablename__ = "movie_shows"
    __table_args__ = (
        UniqueConstraint(
            "movie_id", "cinema_id", "date", "time",
            name="uq_movie_shows_movie_cinema_date_time",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="场次ID")
    movie_id = Column(Integer, nullable=False, index=True, comment="电影ID")
    cinema_id = Column(Integer, nullable=False, index=True, comment="影院ID")
    cinema_name = Column(String(200), nullable=False, comment="影院名称(快照)")
    date = Column(String(20), nullable=False, index=True, comment="放映日期")
    time = Column(String(20), nullable=False, comment="放映时间")
    price = Column(String(20), nullable=True, comment="票价")
    created_at = Column(
        DateTime,
        server_default=func.datetime("now", "+8 hours"),
        nullable=False,
        comment="创建时间(北京时间)",
    )

    @classmethod
    def from_dict(cls, data: MovieShowWriteData) -> MovieShow:
        return cls(
            movie_id=data["movie_id"],
            cinema_id=data["cinema_id"],
            cinema_name=data["cinema_name"],
            date=data["date"],
            time=data["time"],
            price=data.get("price"),
        )
