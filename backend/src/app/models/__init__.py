"""数据库模型导出。"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# 这里必须在 Base 创建后再导入具体模型，才能完成 metadata 注册。
from app.models.cinema import Cinema  # noqa: E402
from app.models.movie import Movie  # noqa: E402
from app.models.planning import PlanningItem  # noqa: E402

__all__ = ["Base", "Movie", "Cinema", "PlanningItem"]
