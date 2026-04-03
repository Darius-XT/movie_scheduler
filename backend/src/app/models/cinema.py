"""影院数据模型"""

from __future__ import annotations

from typing import NotRequired, Required, TypedDict

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models import Base


class CinemaWriteData(TypedDict, total=False):
    """影院持久化写入数据。"""

    id: Required[int]
    name: NotRequired[str | None]
    address: NotRequired[str | None]
    price: NotRequired[str | None]
    allow_refund: NotRequired[bool | None]
    allow_endorse: NotRequired[bool]


class Cinema(Base):
    """影院数据模型"""

    __tablename__ = "cinemas"

    # 基本信息
    id = Column(Integer, primary_key=True, comment="影院ID")
    name = Column(String(200), nullable=False, comment="影院名称")
    address = Column(String(500), nullable=False, comment="影院地址")
    price = Column(String(20), nullable=True, comment="票价")
    allow_refund = Column(Boolean, nullable=True, comment="是否允许退票")

    # 时间戳（东八区北京时间）
    updated_at = Column(
        DateTime,
        server_default=func.datetime("now", "+8 hours"),
        onupdate=func.datetime("now", "+8 hours"),
        comment="更新时间（北京时间）",
    )

    def __repr__(self):
        return f"<Cinema(id={self.id}, name='{self.name}', address='{self.address}')>"

    @classmethod
    def from_dict(cls, data: CinemaWriteData) -> Cinema:
        """从字典便捷地创建Cinema实例"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            address=data.get("address"),
            price=data.get("price"),
            allow_refund=data.get("allow_refund"),
        )
