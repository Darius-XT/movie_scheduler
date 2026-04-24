"""电影全量更新前的重置辅助。"""

from __future__ import annotations

from app.core.logger import logger
from app.repositories.movie import movie_repository


class MovieUpdateResetHelper:
    """负责在全量更新前清理旧电影数据。"""

    def reset_movies_if_needed(self, force_update_all: bool) -> None:
        """按需清理旧数据。"""
        if not force_update_all:
            return

        logger.info("强制完全更新模式：正在删除所有现有电影数据")
        if movie_repository.delete_all_movies():
            logger.info("所有电影数据已删除，开始重新抓取")
            return
        logger.warning("删除所有电影数据失败，但将继续执行更新操作")
