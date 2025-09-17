"""电影数据库操作"""

from typing import List, Dict
from sqlalchemy.exc import SQLAlchemyError
from src.base.movie import Movie
from src.processor.database.connection import get_db_connection
from src.base.logger import setup_logger

logger = setup_logger()


class MovieOperations:
    """电影数据库操作类"""

    def __init__(self):
        self.db = get_db_connection().session
        self._should_close_db = False  # 如果是自己创建的session，需要关闭

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_db:
            self.db.close()

    # 传入单个电影数据的字典, 保存到数据库
    def save_movie(self, movie_data: Dict) -> bool:
        """保存单个电影数据"""
        try:
            # 检查电影是否已存在
            existing_movie = (
                self.db.query(Movie).filter(Movie.id == movie_data["id"]).first()
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
                self.db.add(movie)
                logger.info(
                    f"添加新电影: {movie_data.get('title', 'Unknown')} (ID: {movie_data['id']})"
                )

            self.db.commit()
            return True

        except SQLAlchemyError as e:
            logger.error(f"保存电影数据失败: {e}")
            self.db.rollback()
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

    def get_movies_count(self) -> int:
        """获取电影总数"""
        try:
            return self.db.query(Movie).count()
        except SQLAlchemyError as e:
            logger.error(f"获取电影数量失败: {e}")
            return 0

    def get_statistics(self) -> Dict:
        """获取总的数据库统计信息"""
        try:
            total_movies = self.get_movies_count()

            return {
                "total_movies": total_movies,
            }
        except SQLAlchemyError as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
