"""电影仓储。"""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from app.core.database import database_manager
from app.core.exceptions import RepositoryError
from app.core.logger import logger
from app.models.movie import Movie, MovieWriteData


class MovieRepository:
    """封装电影表的数据访问操作。"""

    def save_movie(self, movie_data: MovieWriteData) -> bool:
        """保存单个电影数据。"""
        try:
            with database_manager.transaction() as session:
                existing_movie = session.query(Movie).filter(Movie.id == movie_data["id"]).first()

                if existing_movie:
                    for key, value in movie_data.items():
                        if hasattr(existing_movie, key):
                            setattr(existing_movie, key, value)
                    logger.debug("更新电影: %s (ID: %s)", movie_data.get("title", "Unknown"), movie_data["id"])
                else:
                    session.add(Movie.from_dict(movie_data))
                    logger.debug("添加新电影: %s (ID: %s)", movie_data.get("title", "Unknown"), movie_data["id"])
            return True
        except SQLAlchemyError as error:
            logger.error("保存电影数据失败: %s", error)
            raise RepositoryError("保存电影数据失败") from error

    def get_movie_by_id(self, movie_id: int) -> Movie | None:
        """根据 ID 获取电影。"""
        try:
            with database_manager.session() as session:
                return session.query(Movie).filter(Movie.id == movie_id).first()
        except SQLAlchemyError as error:
            logger.error("根据 ID 获取电影失败: %s", error)
            raise RepositoryError("读取电影数据失败") from error

    def get_all_movies(self, limit: int | None = None) -> list[Movie]:
        """获取全部电影。"""
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
        """获取全部想看电影,按首次上映时间倒序。"""
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
        """更新电影的想看状态,电影不存在时返回 False。"""
        try:
            with database_manager.transaction() as session:
                movie = session.query(Movie).filter(Movie.id == movie_id).first()
                if movie is None:
                    logger.warning("设置想看状态失败,电影不存在: ID %s", movie_id)
                    return False
                movie.is_wished = bool(is_wished)
            return True
        except SQLAlchemyError as error:
            logger.error("设置电影想看状态失败: %s", error)
            raise RepositoryError("设置电影想看状态失败") from error

    def get_movies_count(self) -> int:
        """获取电影总数。"""
        try:
            with database_manager.session() as session:
                return session.query(Movie).count()
        except SQLAlchemyError as error:
            logger.error("获取电影数量失败: %s", error)
            raise RepositoryError("读取电影数量失败") from error

    def get_movies_without_details(self) -> list[Movie]:
        """获取缺少详情的电影。"""
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
        """获取缺少豆瓣信息的电影。"""
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
        """删除单部电影。"""
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
