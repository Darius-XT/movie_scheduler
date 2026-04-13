"""影院仓储。"""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from app.core.database import database_manager
from app.core.exceptions import RepositoryError
from app.core.logger import logger
from app.models.cinema import Cinema, CinemaWriteData


class CinemaRepository:
    """封装影院表的数据访问操作。"""

    def save_cinema(self, cinema_data: CinemaWriteData) -> bool:
        """保存单个影院数据。"""
        try:
            with database_manager.transaction() as session:
                existing_cinema = session.query(Cinema).filter(Cinema.id == cinema_data["id"]).first()

                if existing_cinema:
                    for key, value in cinema_data.items():
                        if hasattr(existing_cinema, key):
                            setattr(existing_cinema, key, value)
                    logger.debug("更新影院: %s (ID: %s)", cinema_data.get("name", "Unknown"), cinema_data["id"])
                else:
                    session.add(Cinema.from_dict(cinema_data))
                    logger.debug("添加新影院: %s (ID: %s)", cinema_data.get("name", "Unknown"), cinema_data["id"])
            return True
        except SQLAlchemyError as error:
            logger.error("保存影院数据失败: %s", error)
            raise RepositoryError("保存影院数据失败") from error

    def save_cinema_batch(self, cinemas_data: list[CinemaWriteData]) -> tuple[int, int]:
        """批量保存影院数据。"""
        logger.debug("批量保存影院数据")
        success_count = 0
        failure_count = 0

        for cinema_data in cinemas_data:
            try:
                self.save_cinema(cinema_data)
                success_count += 1
            except RepositoryError:
                failure_count += 1

        logger.debug("批量保存影院完成: 成功 %s 家，失败 %s 家", success_count, failure_count)
        return success_count, failure_count

    def delete_all_cinemas(self) -> bool:
        """删除全部影院。"""
        try:
            with database_manager.transaction() as session:
                deleted_count = session.query(Cinema).delete()
                logger.info("已删除所有影院，共 %s 家", deleted_count)
            return True
        except SQLAlchemyError as error:
            logger.error("删除所有影院失败: %s", error)
            raise RepositoryError("删除所有影院失败") from error

    def get_cinemas_count(self) -> int:
        """获取影院总数。"""
        try:
            with database_manager.session() as session:
                return session.query(Cinema).count()
        except SQLAlchemyError as error:
            logger.error("获取影院数量失败: %s", error)
            raise RepositoryError("读取影院数量失败") from error


cinema_repository = CinemaRepository()
