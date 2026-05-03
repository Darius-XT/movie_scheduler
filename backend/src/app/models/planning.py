"""单用户排片计划数据模型。"""

from __future__ import annotations

from typing import NotRequired, Required, TypedDict

from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.models import Base


class PlanningItemWriteData(TypedDict, total=False):
    """排片计划持久化写入数据。"""

    list_type: Required[str]
    show_key: Required[str]
    movie_id: Required[int]
    movie_title: Required[str]
    date: Required[str]
    time: Required[str]
    cinema_id: Required[int]
    cinema_name: Required[str]
    price: NotRequired[str | None]
    duration_minutes: NotRequired[int | None]
    purchased: NotRequired[bool]


class PlanningItem(Base):
    """单用户想看与行程条目。"""

    __tablename__ = "planning_items"
    __table_args__ = (
        UniqueConstraint("list_type", "show_key", name="uq_planning_items_list_type_show_key"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="计划条目ID")
    list_type = Column(String(20), nullable=False, index=True, comment="列表类型：wish 或 schedule")
    show_key = Column(String(255), nullable=False, comment="前端场次唯一键")
    movie_id = Column(Integer, nullable=False, index=True, comment="电影ID")
    movie_title = Column(String(200), nullable=False, comment="电影标题")
    date = Column(String(20), nullable=False, index=True, comment="放映日期")
    time = Column(String(20), nullable=False, comment="放映时间")
    cinema_id = Column(Integer, nullable=False, index=True, comment="影院ID")
    cinema_name = Column(String(200), nullable=False, comment="影院名称")
    price = Column(String(20), nullable=True, comment="票价")
    duration_minutes = Column(Integer, nullable=True, comment="片长分钟数")
    purchased = Column(Boolean, nullable=False, server_default="0", comment="是否已购票")
    created_at = Column(
        DateTime,
        server_default=func.datetime("now", "+8 hours"),
        nullable=False,
        comment="创建时间（北京时间）",
    )
    updated_at = Column(
        DateTime,
        server_default=func.datetime("now", "+8 hours"),
        onupdate=func.datetime("now", "+8 hours"),
        nullable=False,
        comment="更新时间（北京时间）",
    )

    @classmethod
    def from_dict(cls, data: PlanningItemWriteData) -> PlanningItem:
        """从写入字典创建计划条目。"""
        return cls(
            list_type=data["list_type"],
            show_key=data["show_key"],
            movie_id=data["movie_id"],
            movie_title=data["movie_title"],
            date=data["date"],
            time=data["time"],
            cinema_id=data["cinema_id"],
            cinema_name=data["cinema_name"],
            price=data.get("price"),
            duration_minutes=data.get("duration_minutes"),
            purchased=bool(data.get("purchased", False)),
        )
