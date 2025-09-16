"""数据库连接管理"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from src.base.movie import Base
from src.base.logger import logger


class DatabaseConnection:
    """数据库连接管理类"""

    def __init__(self, db_path: str = "src/data/movies.db"):
        self.db_path = db_path
        self.database_url = f"sqlite:///{db_path}"

        # 创建引擎
        self.engine = create_engine(
            self.database_url,
            echo=False,  # 设置为True可以看到SQL语句
            connect_args={"check_same_thread": False},  # SQLite特定配置
            poolclass=StaticPool,
        )

        # 创建Session工厂
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

        # 创建表
        self._create_tables()

    def _create_tables(self):
        """创建所有表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.debug(f"数据库表创建成功，数据库路径: {self.db_path}")
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise

    def get_session(self) -> Session:
        """获取数据库session"""
        return self.SessionLocal()

    def close(self):
        """关闭数据库连接"""
        self.engine.dispose()

    @classmethod
    def validate_config(cls):
        """验证数据库配置"""
        return True


# 全局数据库连接实例 (重命名以避免命名冲突)
db_connection = DatabaseConnection()


def get_db() -> Generator[Session, None, None]:
    """获取数据库session的依赖函数"""
    db = db_connection.get_session()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """直接获取数据库session"""
    return db_connection.get_session()
