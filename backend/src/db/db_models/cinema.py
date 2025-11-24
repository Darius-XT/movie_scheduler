"""影院数据模型"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from src.db.db_models import Base
from sqlalchemy.sql import func


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
    def from_dict(cls, data: dict) -> "Cinema":
        """从字典便捷地创建Cinema实例"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            address=data.get("address"),
            price=data.get("price"),
            allow_refund=data.get("allow_refund"),
        )