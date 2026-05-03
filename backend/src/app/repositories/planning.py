"""排片计划仓储。"""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from app.core.database import database_manager
from app.core.exceptions import RepositoryError
from app.core.logger import logger
from app.models.planning import PlanningItem, PlanningItemWriteData


class PlanningRepository:
    """封装单用户排片计划的数据访问。"""

    def list_items(self) -> list[PlanningItem]:
        """读取全部计划条目。"""
        try:
            with database_manager.session() as session:
                return (
                    session.query(PlanningItem)
                    .order_by(PlanningItem.date.asc(), PlanningItem.time.asc(), PlanningItem.id.asc())
                    .all()
                )
        except SQLAlchemyError as error:
            logger.error("读取排片计划失败: %s", error)
            raise RepositoryError("读取排片计划失败") from error

    def replace_all(self, items: list[PlanningItemWriteData]) -> list[PlanningItem]:
        """全量替换计划条目。"""
        try:
            with database_manager.transaction() as session:
                session.query(PlanningItem).delete()
                models = [PlanningItem.from_dict(item) for item in items]
                session.add_all(models)
                session.flush()
                for item in models:
                    session.refresh(item)
                return list(models)
        except SQLAlchemyError as error:
            logger.error("保存排片计划失败: %s", error)
            raise RepositoryError("保存排片计划失败") from error


planning_repository = PlanningRepository()
