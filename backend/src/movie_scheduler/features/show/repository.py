"""电影场次仓储。"""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from movie_scheduler.core.db import database_manager
from movie_scheduler.core.exceptions import RepositoryError
from movie_scheduler.core.logging import logger
from movie_scheduler.features.show.models import MovieShow, MovieShowWriteData


class MovieShowRepository:
    """封装电影场次表的数据访问。"""

    def list_for_movies(self, movie_ids: list[int]) -> list[MovieShow]:
        """读取指定电影的全部场次,按 date/time 升序。"""
        if not movie_ids:
            return []
        try:
            with database_manager.session() as session:
                return (
                    session.query(MovieShow)
                    .filter(MovieShow.movie_id.in_(movie_ids))
                    .order_by(MovieShow.date.asc(), MovieShow.time.asc(), MovieShow.cinema_id.asc())
                    .all()
                )
        except SQLAlchemyError as error:
            logger.error("读取场次失败: %s", error)
            raise RepositoryError("读取场次失败") from error

    def replace_for_movie(self, movie_id: int, shows: list[MovieShowWriteData]) -> int:
        """覆盖某部电影的场次(事务内 DELETE + bulk insert),返回写入数量。"""
        try:
            with database_manager.transaction() as session:
                session.query(MovieShow).filter(MovieShow.movie_id == movie_id).delete(
                    synchronize_session=False
                )
                models = [MovieShow.from_dict(show) for show in shows]
                if models:
                    session.add_all(models)
            return len(shows)
        except SQLAlchemyError as error:
            logger.error("写入场次失败: %s", error)
            raise RepositoryError("写入场次失败") from error

    def delete_for_movie(self, movie_id: int) -> int:
        """删除某部电影的全部场次,返回删除行数。"""
        try:
            with database_manager.transaction() as session:
                deleted = (
                    session.query(MovieShow)
                    .filter(MovieShow.movie_id == movie_id)
                    .delete(synchronize_session=False)
                )
            return int(deleted)
        except SQLAlchemyError as error:
            logger.error("删除场次失败: %s", error)
            raise RepositoryError("删除场次失败") from error


movie_show_repository = MovieShowRepository()
