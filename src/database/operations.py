from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.core.movie import Movie
from src.database.connection import get_db_session
from src.core.logger import logger


class MovieOperations:
    """电影数据库操作类"""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or get_db_session()
        self._should_close_db = db is None  # 如果是自己创建的session，需要关闭

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
                f"批量保存完成: 成功 {success_count} 部，失败 {failure_count} 部"
            )
            return success_count, failure_count

        except Exception as e:
            logger.error(f"批量保存电影数据失败: {e}")
            return success_count, failure_count

    def get_movie_by_id(self, movie_id: int) -> Optional[Movie]:
        """根据ID获取电影"""
        try:
            return self.db.query(Movie).filter(Movie.id == movie_id).first()
        except SQLAlchemyError as e:
            logger.error(f"查询电影失败: {e}")
            return None

    def get_movies_by_title(self, title: str, exact_match: bool = False) -> List[Movie]:
        """根据标题搜索电影"""
        try:
            if exact_match:
                return self.db.query(Movie).filter(Movie.title == title).all()
            else:
                return self.db.query(Movie).filter(Movie.title.like(f"%{title}%")).all()
        except SQLAlchemyError as e:
            logger.error(f"搜索电影失败: {e}")
            return []

    def get_all_movies(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[Movie]:
        """获取所有电影"""
        try:
            query = self.db.query(Movie).offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"获取电影列表失败: {e}")
            return []

    def get_movies_count(self) -> int:
        """获取电影总数"""
        try:
            return self.db.query(Movie).count()
        except SQLAlchemyError as e:
            logger.error(f"获取电影数量失败: {e}")
            return 0

    def get_movies_by_score_range(
        self, min_score: Optional[float] = None, max_score: Optional[float] = None
    ) -> List[Movie]:
        """根据评分范围获取电影"""
        try:
            query = self.db.query(Movie)

            if min_score is not None:
                # 注意：score字段是字符串，需要转换
                query = query.filter(Movie.score.isnot(None))
                # 这里简化处理，实际可能需要更复杂的数字字符串比较

            if max_score is not None:
                query = query.filter(Movie.score.isnot(None))

            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"按评分范围查询电影失败: {e}")
            return []

    def get_movies_by_genre(self, genre: str) -> List[Movie]:
        """根据类型获取电影"""
        try:
            return self.db.query(Movie).filter(Movie.genres.like(f"%{genre}%")).all()
        except SQLAlchemyError as e:
            logger.error(f"按类型查询电影失败: {e}")
            return []

    def delete_movie(self, movie_id: int) -> bool:
        """删除电影"""
        try:
            movie = self.db.query(Movie).filter(Movie.id == movie_id).first()
            if movie:
                self.db.delete(movie)
                self.db.commit()
                logger.info(f"删除电影成功: {movie.title} (ID: {movie_id})")
                return True
            else:
                logger.warning(f"未找到要删除的电影: ID {movie_id}")
                return False
        except SQLAlchemyError as e:
            logger.error(f"删除电影失败: {e}")
            self.db.rollback()
            return False

    def export_to_dict(self, movies: Optional[List[Movie]] = None) -> List[Dict]:
        """导出电影数据为字典列表"""
        if movies is None:
            movies = self.get_all_movies()

        return [movie.to_dict() for movie in movies]

    def get_statistics(self) -> Dict:
        """获取数据库统计信息"""
        try:
            total_movies = self.get_movies_count()

            return {
                "total_movies": total_movies,
            }
        except SQLAlchemyError as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
