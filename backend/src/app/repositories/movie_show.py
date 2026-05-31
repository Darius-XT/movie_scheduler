"""电影场次仓储。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from app.core.database import database_manager
from app.core.exceptions import RepositoryError
from app.core.logger import logger
from app.models.movie_show import MovieShow, MovieShowWriteData, ShowFetchRun


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


class ShowFetchRunRepository:
    """封装场次抓取任务元信息表的数据访问。"""

    def create_started(self, started_at: datetime, movie_count: int) -> int:
        """记录任务开始,返回 run id。"""
        try:
            with database_manager.transaction() as session:
                run = ShowFetchRun(
                    started_at=started_at,
                    movie_count=movie_count,
                )
                session.add(run)
                session.flush()
                return int(run.id)  # type: ignore[arg-type]
        except SQLAlchemyError as error:
            logger.error("记录场次抓取任务开始失败: %s", error)
            raise RepositoryError("记录场次抓取任务失败") from error

    def mark_finished(
        self,
        run_id: int,
        finished_at: datetime,
        success_count: int,
        error: str | None = None,
    ) -> None:
        """更新任务为完成状态。"""
        try:
            with database_manager.transaction() as session:
                run = session.query(ShowFetchRun).filter(ShowFetchRun.id == run_id).first()
                if run is None:
                    return
                run.finished_at = finished_at
                run.success_count = success_count
                run.error = error
        except SQLAlchemyError as error_db:
            logger.error("记录场次抓取任务完成失败: %s", error_db)
            raise RepositoryError("记录场次抓取任务失败") from error_db

    def get_latest_finished(self) -> ShowFetchRun | None:
        """返回最近一次已完成的任务记录(用于前端展示)。"""
        try:
            with database_manager.session() as session:
                return (
                    session.query(ShowFetchRun)
                    .filter(ShowFetchRun.finished_at.isnot(None))
                    .order_by(ShowFetchRun.finished_at.desc())
                    .first()
                )
        except SQLAlchemyError as error:
            logger.error("读取最近一次场次抓取任务失败: %s", error)
            raise RepositoryError("读取场次抓取任务失败") from error


movie_show_repository = MovieShowRepository()
show_fetch_run_repository = ShowFetchRunRepository()
