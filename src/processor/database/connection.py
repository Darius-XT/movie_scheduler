"""数据库连接管理"""

from singleton_decorator import singleton
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.base.movie import Base
from src.base.logger import setup_logger
from src.config import settings


class DatabaseConnection:
    """数据库连接管理类"""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or settings.database_path
        self.database_url = settings.database_url

        # 创建引擎
        self.engine = create_engine(
            self.database_url,
        )

        # 创建session(具体的工作单元)
        self.session = sessionmaker(bind=self.engine)()

        # 创建表
        self._create_tables()

    def _create_tables(self):
        """创建所有表"""
        logger = setup_logger()
        try:
            # 扫描所有继承自 Base 的模型类, 并据此创建表
            Base.metadata.create_all(bind=self.engine)
            logger.debug(f"数据库表创建成功，数据库路径: {self.db_path}")
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise


# 单例工厂函数, 用于创建数据库连接实例
@singleton
def get_db_connection() -> DatabaseConnection:
    """获取数据库连接实例"""
    return DatabaseConnection()
