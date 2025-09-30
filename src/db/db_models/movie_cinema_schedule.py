"""电影-影院放映场次关系表模型"""

from sqlalchemy import Column, Integer, String, DateTime
from src.db.db_models import Base
from sqlalchemy.sql import func


class MovieCinemaSchedule(Base):
    """电影-影院放映场次关系表"""

    __tablename__ = "movie_cinema_schedules"

    # 主键
    id = Column(Integer, primary_key=True, comment="场次ID")

    # 电影信息
    movie_id = Column(Integer, nullable=False, comment="电影ID")
    movie_title = Column(String(200), nullable=False, comment="电影名称")

    # 影院信息（方案B：先占位，后续补充）
    cinema_id = Column(Integer, nullable=True, comment="影院ID")
    cinema_name = Column(String(200), nullable=True, comment="影院名称")

    # 放映信息
    show_date = Column(String(20), nullable=False, comment="放映日期")
    show_time = Column(String(20), nullable=True, comment="放映时间")

    updated_at = Column(
        DateTime,
        server_default=func.datetime("now", "+8 hours"),
        onupdate=func.datetime("now", "+8 hours"),
        comment="更新时间（北京时间）",
    )

    def __repr__(self):
        return f"<MovieCinemaSchedule(id={self.id}, movie_id={self.movie_id}, cinema_id={self.cinema_id}, show_date='{self.show_date}')>"

    @classmethod
    def from_dict(cls, data: dict) -> "MovieCinemaSchedule":
        """从字典便捷地创建MovieCinemaSchedule实例"""
        return cls(
            movie_id=data.get("movie_id"),
            movie_title=data.get("movie_title"),
            cinema_id=data.get("cinema_id"),
            cinema_name=data.get("cinema_name"),
            show_date=data.get("show_date"),
            show_time=data.get("show_time"),
        )
