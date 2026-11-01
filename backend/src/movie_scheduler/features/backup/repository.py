"""跨业务表的一致性快照与原子恢复。"""

from typing import TypedDict, cast

from sqlalchemy import Table, text
from sqlalchemy.exc import SQLAlchemyError

from movie_scheduler.core.db import database_manager
from movie_scheduler.core.exceptions import RepositoryError
from movie_scheduler.core.logging import logger
from movie_scheduler.features.cinema.models import Cinema
from movie_scheduler.features.movie.models import Movie
from movie_scheduler.features.plan.models import PlanningItem
from movie_scheduler.features.show.models import MovieShow


class BackupReadData(TypedDict):
    cinemas: list[Cinema]
    movies: list[Movie]
    movie_shows: list[MovieShow]
    planning_items: list[PlanningItem]


class BackupWriteData(TypedDict):
    cinemas: list[dict[str, object]]
    movies: list[dict[str, object]]
    movie_shows: list[dict[str, object]]
    planning_items: list[dict[str, object]]


class BackupRepository:
    def read_all(self) -> BackupReadData:
        try:
            with database_manager.session() as session:
                session.execute(text("BEGIN"))
                return {
                    "cinemas": session.query(Cinema).order_by(Cinema.id).all(),
                    "movies": session.query(Movie).order_by(Movie.id).all(),
                    "movie_shows": session.query(MovieShow).order_by(MovieShow.id).all(),
                    "planning_items": session.query(PlanningItem).order_by(PlanningItem.id).all(),
                }
        except SQLAlchemyError as error:
            logger.error("读取备份失败: %s", error)
            raise RepositoryError("读取备份失败") from error

    def replace_all(self, data: BackupWriteData) -> None:
        try:
            with database_manager.transaction() as session:
                session.execute(text("BEGIN IMMEDIATE"))
                for model in (PlanningItem, MovieShow, Movie, Cinema):
                    session.query(model).delete(synchronize_session=False)
                for model, records in (
                    (Cinema, data["cinemas"]),
                    (Movie, data["movies"]),
                    (MovieShow, data["movie_shows"]),
                    (PlanningItem, data["planning_items"]),
                ):
                    if records:
                        table = cast(Table, getattr(model, "__table__"))
                        session.execute(table.insert(), records)
        except SQLAlchemyError as error:
            logger.error("恢复备份失败，事务已回滚: %s", error)
            raise RepositoryError("恢复备份失败") from error


backup_repository = BackupRepository()
