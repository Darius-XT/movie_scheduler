"""电影仓储。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from movie_scheduler.core.db import database_manager
from movie_scheduler.core.exceptions import RepositoryError
from movie_scheduler.core.logging import logger
from movie_scheduler.features.movie.models import Movie, MovieWriteData


class MovieRepository:
    """封装电影表的数据访问操作。"""

    def save_movie(self, movie_data: MovieWriteData) -> bool:
        try:
            with database_manager.transaction() as session:
                existing_movie = session.query(Movie).filter(Movie.id == movie_data["id"]).first()
                if existing_movie:
                    for key, value in movie_data.items():
                        if hasattr(existing_movie, key):
                            setattr(existing_movie, key, value)
                    display_title = movie_data.get("title") or getattr(existing_movie, "title", None) or "Unknown"
                    logger.debug("更新电影: %s (ID: %s)", display_title, movie_data["id"])
                else:
                    session.add(Movie.from_dict(movie_data))
                    logger.debug("添加新电影: %s (ID: %s)", movie_data.get("title", "Unknown"), movie_data["id"])
            return True
        except SQLAlchemyError as error:
            logger.error("保存电影数据失败: %s", error)
            raise RepositoryError("保存电影数据失败") from error

    def get_movie_by_id(self, movie_id: int) -> Movie | None:
        try:
            with database_manager.session() as session:
                return session.query(Movie).filter(Movie.id == movie_id).first()
        except SQLAlchemyError as error:
            logger.error("根据 ID 获取电影失败: %s", error)
            raise RepositoryError("读取电影数据失败") from error

    def get_all_movies(self, limit: int | None = None) -> list[Movie]:
        try:
            with database_manager.session() as session:
                query = session.query(Movie)
                if limit:
                    query = query.limit(limit)
                return query.all()
        except SQLAlchemyError as error:
            logger.error("获取所有电影失败: %s", error)
            raise RepositoryError("读取电影列表失败") from error

    def list_wished_movies(self) -> list[Movie]:
        try:
            with database_manager.session() as session:
                return (
                    session.query(Movie)
                    .filter(Movie.is_wished.is_(True))
                    .order_by(Movie.first_showing_at.desc().nullslast(), Movie.id.desc())
                    .all()
                )
        except SQLAlchemyError as error:
            logger.error("获取想看电影列表失败: %s", error)
            raise RepositoryError("读取想看电影列表失败") from error

    def set_movie_wished(self, movie_id: int, is_wished: bool) -> bool:
        try:
            with database_manager.transaction() as session:
                movie = session.query(Movie).filter(Movie.id == movie_id).first()
                if movie is None:
                    logger.warning("设置想看状态失败,电影不存在: ID %s", movie_id)
                    return False
                setattr(movie, "is_wished", bool(is_wished))
                if is_wished:
                    setattr(movie, "shows_updated_at", None)
            return True
        except SQLAlchemyError as error:
            logger.error("设置电影想看状态失败: %s", error)
            raise RepositoryError("设置电影想看状态失败") from error

    def touch_shows_updated_at(self, movie_id: int) -> bool:
        try:
            with database_manager.transaction() as session:
                updated = (
                    session.query(Movie)
                    .filter(Movie.id == movie_id)
                    .update(
                        {Movie.shows_updated_at: func.datetime("now", "+8 hours")},
                        synchronize_session=False,
                    )
                )
            return bool(updated)
        except SQLAlchemyError as error:
            logger.error("刷新电影场次更新时间失败: %s", error)
            raise RepositoryError("刷新电影场次更新时间失败") from error

    def get_latest_shows_updated_at(self, movie_ids: list[int]) -> datetime | None:
        if not movie_ids:
            return None
        try:
            with database_manager.session() as session:
                return (
                    session.query(func.max(Movie.shows_updated_at))
                    .filter(Movie.id.in_(movie_ids))
                    .scalar()
                )
        except SQLAlchemyError as error:
            logger.error("读取电影场次更新时间失败: %s", error)
            raise RepositoryError("读取电影场次更新时间失败") from error

    def get_movies_count(self) -> int:
        try:
            with database_manager.session() as session:
                return session.query(Movie).count()
        except SQLAlchemyError as error:
            logger.error("获取电影数量失败: %s", error)
            raise RepositoryError("读取电影数量失败") from error

    def get_movies_last_updated_at(self) -> datetime | None:
        try:
            with database_manager.session() as session:
                return (
                    session.query(Movie.updated_at)
                    .filter(Movie.updated_at.is_not(None))
                    .order_by(Movie.updated_at.desc())
                    .limit(1)
                    .scalar()
                )
        except SQLAlchemyError as error:
            logger.error("读取电影最新更新时间失败: %s", error)
            raise RepositoryError("读取电影最新更新时间失败") from error

    def touch_movies_last_updated_at(self) -> None:
        """Record movie-info task completion time on movie rows explicitly."""
        try:
            with database_manager.transaction() as session:
                session.query(Movie).update(
                    {Movie.updated_at: func.datetime("now", "+8 hours")},
                    synchronize_session=False,
                )
        except SQLAlchemyError as error:
            logger.error("刷新电影信息更新时间失败: %s", error)
            raise RepositoryError("刷新电影信息更新时间失败") from error

    def touch_all_updated_at(self) -> None:
        """Backward-compatible wrapper for movie-info task completion time."""
        self.touch_movies_last_updated_at()

    def get_movies_without_details(self) -> list[Movie]:
        try:
            with database_manager.session() as session:
                return (
                    session.query(Movie)
                    .filter(
                        ((Movie.director.is_(None)) | (Movie.director == ""))
                        | ((Movie.country.is_(None)) | (Movie.country == ""))
                        | ((Movie.language.is_(None)) | (Movie.language == ""))
                        | ((Movie.duration.is_(None)) | (Movie.duration == ""))
                        | ((Movie.description.is_(None)) | (Movie.description == ""))
                    )
                    .all()
                )
        except SQLAlchemyError as error:
            logger.error("获取没有详细信息的电影失败: %s", error)
            raise RepositoryError("读取待补充详情电影失败") from error

    def get_movies_without_douban_info(self) -> list[Movie]:
        try:
            with database_manager.session() as session:
                return (
                    session.query(Movie)
                    .filter(
                        ((Movie.score.is_(None)) | (Movie.score == "") | (Movie.score == "无豆瓣评分"))
                        | ((Movie.douban_url.is_(None)) | (Movie.douban_url == ""))
                    )
                    .all()
                )
        except SQLAlchemyError as error:
            logger.error("获取没有豆瓣信息的电影失败: %s", error)
            raise RepositoryError("读取待补充豆瓣信息电影失败") from error

    def delete_movie(self, movie_id: int) -> bool:
        try:
            with database_manager.transaction() as session:
                movie = session.query(Movie).filter(Movie.id == movie_id).first()
                if movie is None:
                    logger.warning("未找到要删除的电影: ID %s", movie_id)
                    return False
                session.delete(movie)
                logger.debug("电影删除成功: ID %s", movie_id)
            return True
        except SQLAlchemyError as error:
            logger.error("删除电影失败: %s", error)
            raise RepositoryError("删除电影失败") from error


movie_repository = MovieRepository()
