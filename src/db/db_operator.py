"""数据库操作器 - 负责数据库的CRUD操作, 动态的部分"""

from typing import List, Dict, Optional, Type
from types import TracebackType
from sqlalchemy.exc import SQLAlchemyError
from src.db.db_models.movie import Movie
from src.db.db_connector import DBConnector, db_connector
from src.logger import logger


class DBOperator:
    """数据库操作器类 - 提供电影数据的CRUD操作"""

    def __init__(self, initializer: Optional[DBConnector] = None):
        """初始化数据库操作器

        Args:
            connector: 数据库连接器实例，如果为None则使用默认的全局实例
        """
        self.connector = db_connector
        self.session = self.connector.session_factory()  # 会话实例: 用于执行数据库操作

    def __enter__(self) -> "DBOperator":
        """支持 with 语句的进入方法"""
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> Optional[bool]:
        """支持 with 语句的退出方法，保证会话正确关闭。

        - 若发生异常则回滚事务；否则保持调用方自行提交的语义。
        - 无论是否异常，都会关闭会话以释放资源。
        """
        try:
            if exc_type is not None:
                # 出现异常，回滚本会话中的未提交变更
                try:
                    self.session.rollback()
                except Exception:
                    pass
        finally:
            try:
                self.session.close()
            except Exception:
                pass
        # 返回 None 让异常（若有）继续向外传播
        return None

    def save_movie(self, movie_data: Dict) -> bool:
        """保存单个电影数据"""
        try:
            # 检查电影是否已存在
            existing_movie = (
                self.session.query(Movie).filter(Movie.id == movie_data["id"]).first()
            )

            if existing_movie:
                # 更新已存在的电影
                for key, value in movie_data.items():
                    if hasattr(existing_movie, key):
                        setattr(existing_movie, key, value)
                logger.info(
                    f"更新电影: {movie_data.get('title', 'Unknown')} (ID: {movie_data['id']})"
                )
            else:
                # 创建新电影
                movie = Movie.from_dict(movie_data)
                self.session.add(movie)
                logger.info(
                    f"添加新电影: {movie_data.get('title', 'Unknown')} (ID: {movie_data['id']})"
                )

            self.session.commit()
            return True

        except SQLAlchemyError as e:
            logger.error(f"保存电影数据失败: {e}")
            self.session.rollback()
            return False

    def save_movies_batch(self, movies_data: List[Dict]) -> tuple[int, int]:
        """批量保存电影数据

        Returns:
            tuple[int, int]: (成功保存数量, 失败数量)
        """
        logger.debug("批量保存电影数据")
        success_count = 0
        failure_count = 0

        try:
            for movie_data in movies_data:
                if self.save_movie(movie_data):
                    success_count += 1
                else:
                    failure_count += 1

            logger.info(
                f"批量保存完成: 成功 {success_count} 部，失败 {failure_count} 部\n"
            )
            return success_count, failure_count

        except Exception as e:
            logger.error(f"批量保存电影数据失败: {e}")
            return success_count, failure_count

    def get_movie_by_id(self, movie_id: int) -> Optional[Movie]:
        """根据ID获取电影"""
        try:
            return self.session.query(Movie).filter(Movie.id == movie_id).first()
        except SQLAlchemyError as e:
            logger.error(f"根据ID获取电影失败: {e}")
            return None

    def get_movies_by_title(self, title: str) -> List[Movie]:
        """根据标题搜索电影"""
        try:
            return self.session.query(Movie).filter(Movie.title.contains(title)).all()
        except SQLAlchemyError as e:
            logger.error(f"根据标题搜索电影失败: {e}")
            return []

    def get_all_movies(self, limit: Optional[int] = None) -> List[Movie]:
        """获取所有电影"""
        try:
            query = self.session.query(Movie)
            if limit:
                query = query.limit(limit)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"获取所有电影失败: {e}")
            return []

    def get_movies_count(self) -> int:
        """获取电影总数"""
        try:
            return self.session.query(Movie).count()
        except SQLAlchemyError as e:
            logger.error(f"获取电影数量失败: {e}")
            return 0

    def get_movies_without_details(self) -> List[Movie]:
        """获取既没有导演也没有国家信息的电影（新增的电影）"""
        try:
            return (
                self.session.query(Movie)
                .filter(
                    ((Movie.director.is_(None)) | (Movie.director == ""))
                    & ((Movie.country.is_(None)) | (Movie.country == ""))
                )
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(f"获取没有详细信息的电影失败: {e}")
            return []

    def delete_movie(self, movie_id: int) -> bool:
        """删除电影"""
        try:
            movie = self.get_movie_by_id(movie_id)
            if movie:
                self.session.delete(movie)
                self.session.commit()
                logger.info(f"电影删除成功: ID {movie_id}")
                return True
            else:
                logger.warning(f"未找到要删除的电影: ID {movie_id}")
                return False
        except SQLAlchemyError as e:
            logger.error(f"删除电影失败: {e}")
            self.session.rollback()
            return False

    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        try:
            total_movies = self.get_movies_count()
            logger.info(f"数据库中总电影数: {total_movies}")

            # 可以添加更多统计信息
            stats = {
                "total_movies": total_movies,
            }

            return stats
        except SQLAlchemyError as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
