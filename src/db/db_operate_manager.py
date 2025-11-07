"""数据库操作器 - 负责数据库的CRUD操作, 动态的部分"""

from typing import List, Dict, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from src.db.db_models.movie import Movie
from src.db.db_models.cinema import Cinema
from src.db.db_models import Base
from src.config_manager import config_manager
from src.utils.logger import logger


class DBOperateManager:
    """数据库操作器类 - 提供电影数据的CRUD操作"""

    def __init__(self, db_path: Optional[str] = None):
        """初始化数据库操作器

        Args:
            db_path (Optional[str]): 数据库文件路径。
                如果为 None，则使用配置文件中的路径。
                示例值: None, "data/movies.db"
        """
        # 初始化数据库连接
        self.db_path = db_path or config_manager.database_path
        self.database_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(self.database_url)
        self.session_factory = sessionmaker(bind=self.engine)

        # 自动创建所有表
        try:
            Base.metadata.create_all(self.engine)
            logger.debug(f"数据库连接器创建完成并已建表: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库建表失败: {e}")
            raise

        # 创建会话实例
        self.session = self.session_factory()

    def save_movie(self, movie_data: Dict) -> bool:
        """保存单个电影数据（如果已存在则更新，否则创建）

        Args:
            movie_data (Dict): 电影数据字典，包含以下字段：
                - id (int): 电影ID，例如: 123456
                - title (str): 电影标题，例如: "肖申克的救赎"
                - score (str, 可选): 评分，例如: "9.7" 或 "暂无评分"
                - genres (str, 可选): 类型，例如: "剧情/犯罪"
                - actors (str, 可选): 主演，例如: "蒂姆·罗宾斯/摩根·弗里曼"
                - release_year (str, 可选): 上映年份，例如: "1994"
                - director (str, 可选): 导演，例如: "弗兰克·德拉邦特"
                - country (str, 可选): 制片国家，例如: "美国"
                - language (str, 可选): 语言，例如: "英语"
                - duration (int, 可选): 时长（分钟），例如: 142
                - description (str, 可选): 剧情简介
                示例值: {
                    "id": 123456,
                    "title": "肖申克的救赎",
                    "score": "9.7",
                    "genres": "剧情/犯罪",
                    "actors": "蒂姆·罗宾斯/摩根·弗里曼",
                    "release_year": "1994",
                    "director": "弗兰克·德拉邦特",
                    "country": "美国",
                    "language": "英语",
                    "duration": 142
                }

        Returns:
            bool: 保存是否成功。
                True 表示保存成功（新增或更新成功），
                False 表示保存失败（数据库错误）。
        """
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
                logger.debug(
                    f"更新电影: {movie_data.get('title', 'Unknown')} (ID: {movie_data['id']})"
                )
            else:
                # 创建新电影
                movie = Movie.from_dict(movie_data)
                self.session.add(movie)
                logger.debug(
                    f"添加新电影: {movie_data.get('title', 'Unknown')} (ID: {movie_data['id']})"
                )

            self.session.commit()
            return True

        except SQLAlchemyError as e:
            logger.error(f"保存电影数据失败: {e}")
            self.session.rollback()
            return False

    def get_movie_by_id(self, movie_id: int) -> Optional[Movie]:
        """根据ID获取电影

        Args:
            movie_id (int): 电影ID。
                示例值: 123456

        Returns:
            Optional[Movie]: 如果找到电影，返回 Movie 对象；否则返回 None。
                Movie 对象包含所有电影字段（id, title, score, genres, actors, release_year, director, country, language, duration, description 等）。
        """
        try:
            return self.session.query(Movie).filter(Movie.id == movie_id).first()
        except SQLAlchemyError as e:
            logger.error(f"根据ID获取电影失败: {e}")
            return None

    def get_all_movies(self, limit: Optional[int] = None) -> List[Movie]:
        """获取所有电影

        Args:
            limit (Optional[int]): 限制返回的电影数量。如果为 None，返回所有电影。
                示例值: None, 10, 100

        Returns:
            List[Movie]: 电影列表，每个元素是 Movie 对象。
                如果数据库为空，返回空列表 []。
                示例返回值: [Movie(...), Movie(...), ...]
        """
        try:
            query = self.session.query(Movie)
            if limit:
                query = query.limit(limit)
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"获取所有电影失败: {e}")
            return []

    def get_movies_count(self) -> int:
        """获取电影总数

        Returns:
            int: 数据库中的电影总数。
                例如: 150 表示数据库中有150部电影。
        """
        try:
            return self.session.query(Movie).count()
        except SQLAlchemyError as e:
            logger.error(f"获取电影数量失败: {e}")
            return 0

    def get_movies_without_details(self) -> List[Movie]:
        """获取既没有导演也没有国家信息的电影（新增的电影，需要补充详情）

        Returns:
            List[Movie]: 缺少详细信息的电影列表，每个元素是 Movie 对象。
                这些电影的 director 和 country 字段为空或空字符串。
                如果所有电影都有详细信息，返回空列表 []。
                示例返回值: [Movie(id=123456, title="新电影", director=None, country=None, ...)]
        """
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
        """删除电影

        Args:
            movie_id (int): 要删除的电影ID。
                示例值: 123456

        Returns:
            bool: 删除是否成功。
                True 表示删除成功，
                False 表示删除失败（电影不存在或数据库错误）。
        """
        try:
            movie = self.get_movie_by_id(movie_id)
            if movie:
                self.session.delete(movie)
                self.session.commit()
                logger.debug(f"电影删除成功: ID {movie_id}")
                return True
            else:
                logger.warning(f"未找到要删除的电影: ID {movie_id}")
                return False
        except SQLAlchemyError as e:
            logger.error(f"删除电影失败: {e}")
            self.session.rollback()
            return False

    def print_statistics(self) -> None:
        """获取数据库统计信息"""
        try:
            total_movies = self.get_movies_count()
            total_cinemas = self.get_cinemas_count()
            logger.info(f"数据库中总电影数: {total_movies}, 总影院数: {total_cinemas}")

        except SQLAlchemyError as e:
            logger.error(f"获取统计信息失败: {e}")

    # 影院相关操作
    def save_cinema(self, cinema_data: Dict) -> bool:
        """保存单个影院数据（如果已存在则更新，否则创建）

        Args:
            cinema_data (Dict): 影院数据字典，包含以下字段：
                - id (int): 影院ID，例如: 1001
                - name (str): 影院名称，例如: "万达影城（上海店）"
                - address (str): 影院地址，例如: "上海市黄浦区南京东路100号"
                - price (str, 可选): 票价，例如: "35元起"
                - allow_refund (bool, 可选): 是否允许退票，例如: True
                示例值: {
                    "id": 1001,
                    "name": "万达影城（上海店）",
                    "address": "上海市黄浦区南京东路100号",
                    "price": "35元起",
                    "allow_refund": True
                }

        Returns:
            bool: 保存是否成功。
                True 表示保存成功（新增或更新成功），
                False 表示保存失败（数据库错误）。
        """
        try:
            # 检查影院是否已存在
            existing_cinema = (
                self.session.query(Cinema)
                .filter(Cinema.id == cinema_data["id"])
                .first()
            )

            if existing_cinema:
                # 更新已存在的影院
                for key, value in cinema_data.items():
                    if hasattr(existing_cinema, key):
                        setattr(existing_cinema, key, value)
                logger.debug(
                    f"更新影院: {cinema_data.get('name', 'Unknown')} (ID: {cinema_data['id']})"
                )
            else:
                # 创建新影院
                cinema = Cinema.from_dict(cinema_data)
                self.session.add(cinema)
                logger.debug(
                    f"添加新影院: {cinema_data.get('name', 'Unknown')} (ID: {cinema_data['id']})"
                )

            self.session.commit()
            return True

        except SQLAlchemyError as e:
            logger.error(f"保存影院数据失败: {e}")
            self.session.rollback()
            return False

    def save_cinemas_batch(self, cinemas_data: List[Dict]) -> tuple[int, int]:
        """批量保存影院数据

        Args:
            cinemas_data (List[Dict]): 影院数据列表，每个字典格式同 save_cinema 的 cinema_data 参数。
                示例值: [
                    {
                        "id": 1001,
                        "name": "万达影城（上海店）",
                        "address": "上海市黄浦区南京东路100号",
                        "price": "35元起"
                    },
                    {
                        "id": 1002,
                        "name": "CGV影城（北京店）",
                        "address": "北京市朝阳区三里屯",
                        "price": "40元起"
                    }
                ]

        Returns:
            tuple[int, int]: (成功保存数量, 失败数量)
                第一个元素是成功保存的影院数量，例如: 25
                第二个元素是保存失败的影院数量，例如: 0
                示例返回值: (25, 0)
        """
        logger.debug("批量保存影院数据")
        success_count = 0
        failure_count = 0

        try:
            for cinema_data in cinemas_data:
                if self.save_cinema(cinema_data):
                    success_count += 1
                else:
                    failure_count += 1

            logger.debug(
                f"批量保存影院完成: 成功 {success_count} 家，失败 {failure_count} 家\n"
            )
            return success_count, failure_count

        except Exception as e:
            logger.error(f"批量保存影院数据失败: {e}")
            return success_count, failure_count

    def get_cinemas_count(self) -> int:
        """获取影院总数

        Returns:
            int: 数据库中的影院总数。
                例如: 50 表示数据库中有50家影院。
        """
        try:
            return self.session.query(Cinema).count()
        except SQLAlchemyError as e:
            logger.error(f"获取影院数量失败: {e}")
            return 0


# 全局数据库操作器实例
db_operate_manager = DBOperateManager()
